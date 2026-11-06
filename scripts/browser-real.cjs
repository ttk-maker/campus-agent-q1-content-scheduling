const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const fs = require("node:fs");
const path = require("node:path");
(async () => {
  const output = path.resolve("examples/browser-real");
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1100 },
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("http://127.0.0.1:8765/");
  await page.waitForFunction(() =>
    document.querySelector("#notice").textContent.includes("已连接"),
  );
  await page.selectOption("#scenario", "conflict");
  await page.selectOption("#mode", "real");
  await page.click("#new-id");
  const id = await page.inputValue("#request-id");
  await page.click("#submit");
  await page.waitForFunction(
    () => !document.querySelector("#submit").disabled,
    {},
    { timeout: 600000 },
  );
  const jobId = await page.evaluate(() =>
    localStorage.getItem("content-agent-job"),
  );
  const job = await (
    await page.request.get("http://127.0.0.1:8765/api/jobs/" + jobId)
  ).json();
  fs.writeFileSync(path.join(output, "job.json"), JSON.stringify(job, null, 2));
  await page.screenshot({
    path: path.join(output, "real-workbench.png"),
    fullPage: true,
  });
  const passed =
    job.state === "done" &&
    job.result.mode === "real" &&
    job.result.items[0].status === "needs_confirmation" &&
    job.result.published === false;
  fs.writeFileSync(
    path.join(output, "report.json"),
    JSON.stringify(
      { timestamp: new Date().toISOString(), request_id: id, passed, errors },
      null,
      2,
    ),
  );
  await browser.close();
  console.log(
    JSON.stringify({ passed, steps: job.result?.steps_used, errors }),
  );
  if (!passed) process.exit(1);
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
