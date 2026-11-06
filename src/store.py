"""SQLite owns confirmation, idempotency, conflict checks and commit truth."""
from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
import sqlite3

from .domain import canonical, digest, input_hash, overlaps


class DraftStore:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS drafts (
                    request_id TEXT NOT NULL, asset_id TEXT NOT NULL,
                    input_hash TEXT NOT NULL, asset_hash TEXT NOT NULL,
                    draft_id TEXT NOT NULL UNIQUE, requested_at TEXT NOT NULL,
                    suggested_at TEXT NOT NULL, channel TEXT NOT NULL,
                    duration INTEGER NOT NULL, status TEXT NOT NULL,
                    PRIMARY KEY(request_id, asset_id)
                );
                CREATE TABLE IF NOT EXISTS confirmations (
                    request_id TEXT NOT NULL, asset_id TEXT NOT NULL,
                    fingerprint TEXT NOT NULL, confirmed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(request_id, asset_id)
                );
                CREATE TABLE IF NOT EXISTS occupied (
                    slot_id TEXT PRIMARY KEY, channel TEXT NOT NULL,
                    start TEXT NOT NULL, duration INTEGER NOT NULL
                );
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def initialize_schedule(self, entries):
        """Idempotent fixture import: never silently overwrite an existing occupancy."""
        with self.connect() as db:
            for entry in entries:
                start = canonical(entry["start"])
                duration = entry["duration_minutes"]
                if type(duration) is not int or duration < 1:
                    raise ValueError("invalid schedule duration")
                db.execute("INSERT OR IGNORE INTO occupied VALUES (?, ?, ?, ?)",
                           (entry["id"], entry["channel"], start, duration))

    def occupy(self, slot_id, channel, start, duration):
        with self.connect() as db:
            db.execute("INSERT INTO occupied VALUES (?, ?, ?, ?)",
                       (slot_id, channel, canonical(start), duration))

    def _conflicts(self, db, request_id, asset_id, asset, start):
        found = []
        for row in db.execute("SELECT * FROM occupied WHERE channel = ?", (asset["channel"],)):
            if overlaps(start, asset["duration_minutes"], row["start"], row["duration"]):
                found.append(row["slot_id"])
        for row in db.execute("SELECT * FROM drafts WHERE channel = ? AND status = 'ready'",
                              (asset["channel"],)):
            if (row["request_id"], row["asset_id"]) == (request_id, asset_id):
                continue
            if overlaps(start, asset["duration_minutes"], row["suggested_at"], row["duration"]):
                found.append(row["draft_id"])
        return found

    def conflicts(self, request_id, asset_id, asset, start):
        with self.connect() as db:
            return self._conflicts(db, request_id, asset_id, asset, start)

    @staticmethod
    def fingerprint(row):
        return digest({key: row[key] for key in
                       ("input_hash", "asset_hash", "suggested_at")})

    def confirm(self, request_id, asset_id, suggested_at):
        """Trusted CLI user action. Deliberately absent from the model tool registry."""
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM drafts WHERE request_id = ? AND asset_id = ?",
                             (request_id, asset_id)).fetchone()
            if row is None or row["status"] != "pending_confirmation":
                return {"status": "rejected", "reason": "no pending draft"}
            if canonical(suggested_at) != row["suggested_at"]:
                return {"status": "rejected", "reason": "confirmation must match current suggestion"}
            db.execute("INSERT OR REPLACE INTO confirmations(request_id, asset_id, fingerprint) "
                       "VALUES (?, ?, ?)", (request_id, asset_id, self.fingerprint(row)))
            return {"status": "confirmed", "draft_id": row["draft_id"],
                    "note": "Consent recorded only; rerun to revalidate rules and availability."}

    def get(self, request_id, asset_id):
        with self.connect() as db:
            row = db.execute("SELECT * FROM drafts WHERE request_id = ? AND asset_id = ?",
                             (request_id, asset_id)).fetchone()
            return dict(row) if row else None

    def count(self):
        with self.connect() as db:
            return db.execute("SELECT COUNT(*) FROM drafts").fetchone()[0]

    def save(self, request_id, item, asset, suggested_at, fail=False):
        chosen = canonical(suggested_at)
        row = dict(request_id=request_id, asset_id=item["asset_id"],
                   input_hash=input_hash(item), asset_hash=digest(asset),
                   draft_id="draft-" + digest([request_id, item["asset_id"]])[:20],
                   requested_at=canonical(item["requested_at"]), suggested_at=chosen,
                   channel=asset["channel"], duration=asset["duration_minutes"])
        try:
            with self.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                prior = db.execute("SELECT * FROM drafts WHERE request_id = ? AND asset_id = ?",
                                   (request_id, item["asset_id"])).fetchone()
                if prior and prior["input_hash"] != row["input_hash"]:
                    return {"status": "rejected", "error": "idempotency_conflict"}
                # Never mutate an already reserved draft through an ordinary retry.
                if prior and prior["status"] == "ready":
                    if prior["asset_hash"] != row["asset_hash"] or prior["suggested_at"] != chosen:
                        return {"status": "rejected", "error": "ready_draft_requires_new_request"}
                conflicts = self._conflicts(db, request_id, item["asset_id"], asset, chosen)
                if conflicts:
                    return {"status": "rejected", "error": "slot_conflict", "conflicts": conflicts}
                consent = db.execute("SELECT fingerprint FROM confirmations "
                                     "WHERE request_id = ? AND asset_id = ?",
                                     (request_id, item["asset_id"])).fetchone()
                confirmed = bool(consent and consent["fingerprint"] == self.fingerprint(row))
                row["status"] = ("ready" if chosen == row["requested_at"] or confirmed
                                 else "pending_confirmation")
                if prior and dict(prior) == row:
                    return {"status": "existing", "draft_id": row["draft_id"],
                            "draft_status": row["status"], "suggested_at": chosen}
                db.execute("""
                    INSERT INTO drafts VALUES (
                        :request_id, :asset_id, :input_hash, :asset_hash, :draft_id,
                        :requested_at, :suggested_at, :channel, :duration, :status)
                    ON CONFLICT(request_id, asset_id) DO UPDATE SET
                        asset_hash=excluded.asset_hash, suggested_at=excluded.suggested_at,
                        channel=excluded.channel, duration=excluded.duration, status=excluded.status
                """, row)
                if fail:
                    raise sqlite3.OperationalError("injected write failure before commit")
            # This point is reached only after the context manager committed successfully.
            return {"status": "saved", "draft_id": row["draft_id"],
                    "draft_status": row["status"], "suggested_at": chosen}
        except sqlite3.Error:
            return {"status": "failed", "error": "storage_write_failed"}
