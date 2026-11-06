"use strict";
const $ = (id) => document.getElementById(id);
const state = { bootstrap: null, busy: false, job: null, poll: null };
const labels = {
  completed: "审核完成",
  needs_confirmation: "待确认改时",
  needs_information: "待补充资料",
  blocked: "风险阻断",
  failed: "执行失败",
  budget_exhausted: "未完成 · 达到上限",
  no_available_slot: "暂无可用时段",
  ready: "可用草稿",
  pending_confirmation: "待确认",
  needs_revalidation: "需重新审核",
  passed: "通过",
  insufficient: "资料不足",
  not_checked: "未检查",
  saved: "已保存",
  existing: "已存在 · 未重复保存",
  not_attempted: "未保存",
  rejected: "已拒绝",
};
function el(tag, text, className) {
  const n = document.createElement(tag);
  if (text !== undefined) n.textContent = text;
  if (className) n.className = className;
  return n;
}
function notice(message, error = false) {
  $("notice").textContent = message;
  $("notice").classList.toggle("error", error);
}
function format(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}
async function api(path, body) {
  const r = await fetch(
    path,
    body === undefined
      ? {}
      : {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": state.bootstrap.csrf_token,
          },
          body: JSON.stringify(body),
        },
  );
  const data = await r.json();
  if (!r.ok) throw new Error(data.error || "服务暂时不可用");
  return data;
}
function busy(value) {
  state.busy = value;
  $("progress").hidden = !value;
  document
    .querySelectorAll(
      "#review-form input,#review-form textarea,#review-form select,#review-form button",
    )
    .forEach((n) => (n.disabled = value));
  document
    .querySelectorAll(".confirm-button")
    .forEach((n) => (n.disabled = value));
  $("submit").textContent = value ? "正在审核…" : "审核并生成草稿 →";
}
function syncBasic() {
  let items;
  try {
    items = JSON.parse($("items").value);
  } catch {
    return;
  }
  if (!Array.isArray(items) || !items.length) return;
  items[0] = {
    asset_id: $("asset-id").value,
    requested_at: $("time").value + ":00+08:00",
    hard_time: $("hard-time").checked,
  };
  $("items").value = JSON.stringify(items, null, 2);
}
function scenario() {
  const name = $("scenario").value;
  const request = structuredClone(state.bootstrap.scenarios[name]);
  $("request-id").value = request.request_id;
  $("items").value = JSON.stringify(request.items, null, 2);
  $("asset-id").value = request.items[0].asset_id;
  $("time").value = request.items[0].requested_at.slice(0, 16);
  $("hard-time").checked = request.items[0].hard_time;
  $("data").value = JSON.stringify(state.bootstrap.data, null, 2);
  $("fail-save").checked = name === "save-failure";
  notice(
    "已载入场景。需要保留历史草稿时请复用请求编号；切换全新需求可生成新编号。",
  );
}
function restoreInputs(job) {
  const p = job.payload;
  if (!p) return;
  $("request-id").value = p.request.request_id;
  $("items").value = JSON.stringify(p.request.items, null, 2);
  $("data").value = JSON.stringify(p.data, null, 2);
  $("mode").value = p.mode;
  $("mode").dispatchEvent(new Event("change"));
  $("budget").value = p.max_steps || 24;
  $("fail-save").checked = !!p.fail_save;
  const i = p.request.items[0];
  $("asset-id").value = i.asset_id;
  $("time").value = new Date(new Date(i.requested_at).getTime() + 8 * 3600000)
    .toISOString()
    .slice(0, 16);
  $("hard-time").checked = i.hard_time;
}
async function refreshDrafts() {
  const data = await api("/api/drafts");
  $("drafts").replaceChildren();
  if (!data.drafts.length) {
    const row = el("tr");
    const cell = el("td", "尚无草稿，完成审核后会显示在这里。");
    cell.colSpan = 4;
    row.append(cell);
    $("drafts").append(row);
    return;
  }
  for (const draft of data.drafts) {
    const row = el("tr"),
      identity = el("td", draft.asset_id);
    identity.append(el("small", draft.request_id));
    const badge = el(
      "span",
      labels[draft.status] || draft.status,
      "badge " +
        (draft.status === "pending_confirmation"
          ? "pending"
          : draft.status === "needs_revalidation"
            ? "bad"
            : ""),
    );
    const status = el("td");
    status.append(badge);
    row.append(
      identity,
      el("td", format(draft.suggested_at)),
      status,
      el("td", draft.draft_id),
    );
    $("drafts").append(row);
  }
}
function render(job) {
  state.job = job;
  $("results").replaceChildren();
  $("download").disabled = false;
  if (!job.result) {
    $("results").append(el("p", job.error || "没有运行结果", "issues"));
    return;
  }
  const result = job.result;
  $("result-subtitle").textContent =
    (result.mode === "real"
      ? "真实模型 · " + result.model
      : "离线演练 · 不代表模型决策效果") +
    " · " +
    result.steps_used +
    "/" +
    result.max_steps +
    " 步";
  for (const item of result.items) {
    const card = el("article", undefined, "result-card"),
      top = el("div", undefined, "card-top");
    top.append(
      el("h3", item.asset_id),
      el(
        "span",
        labels[item.status] || item.status,
        "badge " +
          (item.status === "needs_confirmation"
            ? "pending"
            : ["failed", "blocked", "budget_exhausted"].includes(item.status)
              ? "bad"
              : ""),
      ),
    );
    card.append(top);
    const facts = el("dl", undefined, "facts");
    for (const [key, value] of [
      ["审核状态", labels[item.review_status] || item.review_status],
      ["保存状态", labels[item.save_status] || item.save_status],
      ["原定时间", format(item.requested_at)],
      ["建议时间", format(item.suggested_at)],
      ["生效时间", format(item.effective_at)],
      ["发布状态", "未发布 · 仅草稿"],
    ]) {
      const group = el("div");
      group.append(el("dt", key), el("dd", value));
      facts.append(group);
    }
    card.append(facts);
    if (item.pending_confirmations.length) {
      card.append(
        el(
          "div",
          "原定时间保持不变。确认前，建议时间不会生效；确认后会再次检查规则和占用。",
          "pending-note",
        ),
      );
      if (item.confirmation_token) {
        const button = el(
          "button",
          "确认改为 " + format(item.suggested_at) + " 并重新审核",
          "confirm-button",
        );
        button.type = "button";
        button.addEventListener("click", () => confirmItem(job, item));
        card.append(button);
      }
    }
    if (item.missing_fields.length)
      card.append(
        el("p", "待补充：" + item.missing_fields.join("、"), "issues"),
      );
    for (const risk of item.risk_reasons)
      card.append(el("p", risk.reason, "issues"));
    if (item.error) card.append(el("p", "原因：" + item.error, "issues"));
    if (item.draft_id)
      card.append(el("p", "草稿 " + item.draft_id, "save-note"));
    $("results").append(card);
  }
  $("trace-panel").hidden = false;
  $("trace-count").textContent = "（" + job.trace.length + " 步）";
  $("trace").replaceChildren();
  for (const step of job.trace) {
    const n = el("div", undefined, "trace-step");
    n.append(
      el("strong", step.step + ". " + step.action.tool + " · " + step.asset_id),
      el("p", step.action.reason),
      el(
        "pre",
        JSON.stringify(
          {
            参数: step.action.arguments,
            返回: step.observation,
            下一步: step.next_action,
          },
          null,
          2,
        ),
      ),
    );
    $("trace").append(n);
  }
}
async function follow(id) {
  localStorage.setItem("content-agent-job", id);
  busy(true);
  notice("任务已接收，正在处理。真实模型在 CPU 上可能需要数分钟。");
  while (true) {
    let job;
    try {
      job = await api("/api/jobs/" + encodeURIComponent(id));
    } catch (error) {
      busy(false);
      notice(
        error.message +
          "。可刷新页面重新连接；不要在未知保存状态下更换请求编号。",
        true,
      );
      return;
    }
    if (job.state !== "running") {
      render(job);
      busy(false);
      notice(
        job.state === "error"
          ? job.error
          : "审核结束。请核对每项素材状态；需要改时的草稿仍等待你的确认。",
        job.state === "error",
      );
      await refreshDrafts();
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 700));
  }
}
async function confirmItem(job, item) {
  if (state.busy) return;
  const accepted = window.confirm(
    "将 " +
      item.asset_id +
      " 的建议时间确认为北京时间 " +
      format(item.suggested_at) +
      "？\n确认后将重新审核与检查占用，只保存草稿，不发布。",
  );
  if (!accepted) return;
  busy(true);
  try {
    const response = await api("/api/confirm", {
      job_id: job.job_id,
      asset_id: item.asset_id,
      slot: item.suggested_at,
      confirmation_token: item.confirmation_token,
    });
    await follow(response.job_id);
  } catch (error) {
    busy(false);
    notice(error.message, true);
  }
}
$("review-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (state.busy) return;
  try {
    const payload = {
      request: {
        request_id: $("request-id").value,
        items: JSON.parse($("items").value),
      },
      data: JSON.parse($("data").value),
      mode: $("mode").value,
      max_steps: Number($("budget").value),
      fail_save: $("fail-save").checked,
    };
    busy(true);
    const response = await api("/api/jobs", payload);
    await follow(response.job_id);
  } catch (error) {
    busy(false);
    notice(
      error instanceof SyntaxError
        ? "JSON 格式有误，请检查高级资料。"
        : error.message,
      true,
    );
  }
});
$("scenario").addEventListener("change", scenario);
for (const name of ["asset-id", "time", "hard-time"])
  $(name).addEventListener("change", syncBasic);
$("new-id").addEventListener("click", () => {
  $("request-id").value = "web-" + crypto.randomUUID().slice(0, 12);
  notice("已生成新请求编号；已有草稿仍保留，并可能占用时段。");
});
$("mode").addEventListener("change", () => {
  $("mode-hint").textContent =
    $("mode").value === "real"
      ? "使用本机模型进行真实决策；可能需要数分钟。"
      : "离线模式不调用模型，不能证明真实模型的决策效果。";
});
$("refresh").addEventListener("click", () =>
  refreshDrafts().catch((e) => notice(e.message, true)),
);
$("download").addEventListener("click", () => {
  if (!state.job) return;
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(state.job, null, 2)], {
      type: "application/json",
    }),
  );
  const link = el("a");
  link.href = url;
  link.download = "审核记录-" + state.job.job_id + ".json";
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
(async () => {
  try {
    state.bootstrap = await api("/api/bootstrap");
    scenario();
    await refreshDrafts();
    notice("本地服务已连接。先离线演练，或切换真实模型进行审核。");
    const prior =
      state.bootstrap.active_job || localStorage.getItem("content-agent-job");
    if (prior) {
      try {
        const job = await api("/api/jobs/" + encodeURIComponent(prior));
        restoreInputs(job);
        if (job.state === "running") await follow(prior);
        else {
          render(job);
        }
      } catch {
        localStorage.removeItem("content-agent-job");
      }
    }
  } catch (error) {
    notice(
      "连接失败：" + error.message + "。请启动 python -m src.web 后刷新。",
      true,
    );
  }
})();
