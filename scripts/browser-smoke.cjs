/* Run after npm install: node scripts/browser-smoke.cjs [base URL] [output directory] */
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
const fs = require("node:fs");
const path = require("node:path");
(async () => {
  const base = process.argv[2] || "http://127.0.0.1:8765";
  const output = path.resolve(process.argv[3] || "examples/browser");
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({
    channel: process.env.BROWSER_CHANNEL || "chrome",
    headless: true,
  });
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1100 },
  });
  const consoleErrors = [],
    networkErrors = [],
    checks = [];
  page.on("pageerror", (e) => consoleErrors.push(e.message));
  page.on("response", (r) => {
    if (r.status() >= 400)
      networkErrors.push({ url: r.url(), status: r.status() });
  });
  function check(name, value) {
    checks.push({ name, passed: !!value });
    if (!value) throw new Error(name);
  }
  async function run(scenario) {
    await page.selectOption("#scenario", scenario);
    // Distinct request IDs prevent interference with the user's real demo DB.
    await page.click("#new-id");
    // Use an isolated channel for each scenario while keeping its fixture occupancy.
    await page.locator("#advanced").evaluate((n) => (n.open = true));
    const data = JSON.parse(await page.inputValue("#data"));
    const channel = "browser-" + scenario + "-" + Date.now();
    for (const asset of Object.values(data.assets)) asset.channel = channel;
    for (const slot of data.occupied) slot.channel = channel;
    await page.fill("#data", JSON.stringify(data));
    await page.locator("#advanced").evaluate((n) => (n.open = false));
    await page.click("#submit");
    await page.waitForFunction(
      () => document.querySelector("#submit").disabled === false,
    );
  }
  await page.goto(base);
  await page.waitForFunction(() =>
    document.querySelector("#notice").textContent.includes("已连接"),
  );
  check(
    "root page is a usable workbench",
    (await page.locator("h1").innerText()) !== "",
  );
  await run("conflict");
  check(
    "conflict requires explicit confirmation",
    (await page.locator("#results").innerText()).includes("待确认改时"),
  );
  await page.screenshot({
    path: path.join(output, "desktop.png"),
    fullPage: true,
  });
  const firstText = await page.locator("#results").innerText();
  const firstId = firstText.match(/draft-[a-f0-9]+/)[0];
  await page.click("#submit");
  await page.waitForFunction(() => !document.querySelector("#submit").disabled);
  check(
    "repeat reports existing",
    (await page.locator("#results").innerText()).includes("已存在"),
  );
  check(
    "repeat keeps draft ID",
    (await page.locator("#results").innerText()).includes(firstId),
  );
  await page.reload();
  await page.waitForSelector(".confirm-button");
  check(
    "reload restores pending task",
    (await page.locator(".confirm-button").count()) === 1,
  );
  page.once("dialog", (dialog) => dialog.accept());
  await page.click(".confirm-button");
  await page.waitForFunction(() => !document.querySelector("#submit").disabled);
  check(
    "confirm revalidates and keeps draft",
    (await page.locator("#results").innerText()).includes(firstId) &&
      (await page.locator("#results").innerText()).includes("审核完成"),
  );
  for (const [scenario, text] of [
    ["missing", "待补充资料"],
    ["risk", "风险阻断"],
    ["save-failure", "执行失败"],
  ]) {
    await run(scenario);
    check(
      scenario + " has honest state",
      (await page.locator("#results").innerText()).includes(text),
    );
  }
  await page.locator("#advanced").evaluate((n) => (n.open = true));
  await page.fill("#items", "{broken");
  await page.click("#submit");
  check(
    "invalid JSON is actionable",
    (await page.locator("#notice").innerText()).includes("JSON 格式有误"),
  );
  await run("normal");
  check(
    "normal has no publication",
    (await page.locator("#results").innerText()).includes("未发布"),
  );
  const downloadEvent = page.waitForEvent("download");
  await page.click("#download");
  const downloaded = await downloadEvent;
  check(
    "result export downloads JSON",
    downloaded.suggestedFilename().endsWith(".json"),
  );
  check(
    "trace details available",
    (await page.locator("#trace .trace-step").count()) > 0,
  );
  const injected = JSON.parse(await page.inputValue("#data"));
  injected.assets.M01.title = '<img src=x onerror="window.__injected=true">';
  await page.locator("#advanced").evaluate((n) => (n.open = true));
  await page.fill("#data", JSON.stringify(injected));
  await page.click("#new-id");
  await page.click("#submit");
  await page.waitForFunction(() => !document.querySelector("#submit").disabled);
  await page.locator("#trace-panel").evaluate((n) => (n.open = true));
  check(
    "untrusted material is rendered as text",
    await page.evaluate(() => window.__injected !== true),
  );
  await page.locator("#trace-panel").evaluate((n) => (n.open = false));
  // Simulate one in-flight poll of the actual last job, then its real completed response.
  const restoredId = await page.inputValue("#request-id");
  const lastJob = await page.evaluate(() => localStorage.getItem("content-agent-job"));
  const storedJob = await (await page.request.get(base + "/api/jobs/" + lastJob)).json();
  let firstPoll = true;
  await page.route("**/api/jobs/" + lastJob, async (route) => {
    const body = firstPoll ? { ...storedJob, state: "running" } : storedJob;
    firstPoll = false;
    await route.fulfill({ json: body });
  });
  await page.reload();
  await page.waitForFunction(
    (id) => document.querySelector("#request-id").value === id && !document.querySelector("#submit").disabled,
    restoredId,
  );
  check("in-flight refresh (simulated poll) restores original input", await page.inputValue("#request-id") === restoredId);
  await page.unroute("**/api/jobs/" + lastJob);
  await page.locator("#advanced").evaluate((n) => (n.open = false));
  await page.setViewportSize({ width: 390, height: 844 });
  check(
    "mobile has no horizontal overflow",
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  );
  await page.screenshot({
    path: path.join(output, "mobile.png"),
    fullPage: true,
  });
  await page.goto(base + "/manual.html");
  check(
    "manual is reachable",
    (await page.locator("h1").innerText()).includes("一步步"),
  );
  check("no browser JS errors", consoleErrors.length === 0);
  check("no unexpected network failures", networkErrors.length === 0);
  fs.writeFileSync(
    path.join(output, "report.json"),
    JSON.stringify(
      {
        timestamp: new Date().toISOString(),
        base,
        checks,
        consoleErrors,
        networkErrors,
      },
      null,
      2,
    ),
  );
  await browser.close();
  console.log(
    JSON.stringify({ passed: checks.length, consoleErrors, networkErrors }),
  );
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
