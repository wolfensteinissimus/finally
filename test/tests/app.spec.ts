import { test, expect, Page, request } from "@playwright/test";

const DEFAULTS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"];
const money = async (page: Page, id: string) => {
  const t = (await page.getByTestId(id).innerText()).replace(/[^0-9.\-]/g, "");
  return parseFloat(t);
};

test.describe.configure({ mode: "serial" });

test.beforeAll(async ({ baseURL }) => {
  // Clean state: remove leftover non-default watchlist tickers/positions is not possible via API for
  // positions; tests are written to be relative and use unique tickers.
  const ctx = await request.newContext({ baseURL });
  const r = await ctx.get("/api/health");
  expect(r.ok()).toBeTruthy();
});

test("fresh start: 10 tickers, $10k, prices streaming", async ({ page }) => {
  await page.goto("/");
  for (const t of DEFAULTS) await expect(page.getByTestId(`watchlist-row-${t}`)).toBeVisible();
  await expect(page.getByTestId("connection-status")).toHaveAttribute("data-status", /^connected$/);
  await expect(page.getByTestId("header-cash")).toContainText("10,000");
  await expect(page.getByTestId("header-total-value")).toContainText("10,000");
  const p = page.getByTestId("price-AAPL");
  await expect(p).toHaveText(/\d+\.\d\d/);
  const first = await p.innerText();
  await expect.poll(async () => p.innerText(), { timeout: 20_000 }).not.toBe(first);
});

test("add and remove a ticker", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("watchlist-add-input").fill("PYPL");
  await page.getByTestId("watchlist-add-btn").click();
  await expect(page.getByTestId("watchlist-row-PYPL")).toBeVisible();
  await expect(page.getByTestId("price-PYPL")).toHaveText(/\d+\.\d\d/);
  await page.reload();
  await expect(page.getByTestId("watchlist-row-PYPL")).toBeVisible();
  await page.getByTestId("watchlist-remove-PYPL").click();
  await expect(page.getByTestId("watchlist-row-PYPL")).toHaveCount(0);
  await page.reload();
  await expect(page.getByTestId("watchlist-row-AAPL")).toBeVisible();
  await expect(page.getByTestId("watchlist-row-PYPL")).toHaveCount(0);
});

test("buy shares: cash decreases, position appears", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("price-MSFT")).toHaveText(/\d+\.\d\d/);
  const cash0 = await money(page, "header-cash");
  await page.getByTestId("trade-ticker").fill("MSFT");
  await page.getByTestId("trade-quantity").fill("5");
  await page.getByTestId("trade-buy").click();
  await expect(page.getByTestId("positions-row-MSFT")).toBeVisible();
  await expect.poll(() => money(page, "header-cash")).toBeLessThan(cash0 - 100);
  await expect(page.getByTestId("header-total-value")).toContainText("$");
  expect(await money(page, "header-total-value")).toBeGreaterThan(9000);
});

test("sell shares: cash increases, position disappears", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("positions-row-MSFT")).toBeVisible();
  const cash0 = await money(page, "header-cash");
  await page.getByTestId("trade-ticker").fill("MSFT");
  await page.getByTestId("trade-quantity").fill("5");
  await page.getByTestId("trade-sell").click();
  await expect(page.getByTestId("positions-row-MSFT")).toHaveCount(0);
  await expect.poll(() => money(page, "header-cash")).toBeGreaterThan(cash0);
});

test("invalid trade (oversell) shows error and changes nothing", async ({ page }) => {
  await page.goto("/");
  const cash0 = await money(page, "header-cash");
  await page.getByTestId("trade-ticker").fill("TSLA");
  await page.getByTestId("trade-quantity").fill("1000");
  await page.getByTestId("trade-sell").click();
  await expect(page.getByTestId("trade-message")).toBeVisible();
  expect(await money(page, "header-cash")).toBe(cash0);
});

test("heatmap and P&L chart render with data", async ({ page, request }) => {
  await page.goto("/");
  await page.getByTestId("trade-ticker").fill("NVDA");
  await page.getByTestId("trade-quantity").fill("2");
  await page.getByTestId("trade-buy").click();
  await expect(page.getByTestId("positions-row-NVDA")).toBeVisible();
  await expect(page.getByTestId("heatmap")).toBeVisible();
  await expect(page.getByTestId("heatmap-cell-NVDA")).toBeVisible();
  const cell = page.getByTestId("heatmap-cell-NVDA").locator("div").first();
  await expect(cell).toHaveCSS("background-color", /rgb/);
  await expect(page.getByTestId("pnl-chart")).toBeVisible();
  await expect(page.getByTestId("pnl-chart").locator("canvas, svg").first()).toBeVisible();
  const h = await request.get("/api/portfolio/history");
  const data = await h.json();
  expect(data.length).toBeGreaterThan(0);
  await expect.poll(async () => Number(await page.getByTestId("pnl-chart").getAttribute("data-points"))).toBeGreaterThan(0);
});

test("mocked AI chat executes a trade and shows it inline", async ({ page }) => {
  await page.goto("/");
  const input = page.getByTestId("chat-input");
  if (!(await input.isVisible())) await page.getByTestId("chat-toggle").click();
  await input.fill("Please buy some AAPL");
  await page.getByTestId("chat-send").click();
  await expect(page.getByTestId("chat-message").filter({ hasText: "Buying 1 share of AAPL" })).toBeVisible();
  await expect(page.getByTestId("chat-trade").first()).toContainText(/Bought.*AAPL/);
  await expect(page.getByTestId("positions-row-AAPL")).toBeVisible();
  // watchlist change via chat
  await input.fill("add PYPL");
  await page.getByTestId("chat-send").click();
  await expect(page.getByTestId("chat-watchlist-change").first()).toContainText("PYPL");
  await expect(page.getByTestId("watchlist-row-PYPL")).toBeVisible();
  await page.getByTestId("watchlist-remove-PYPL").click();
});

test("SSE reconnects after the stream is dropped", async ({ page }) => {
  // First stream request is terminated by the "network" right away (EventSource sees a closed
  // stream and must retry); later requests go to the real server.
  let calls = 0;
  await page.route("**/api/stream/prices", async (route) => {
    calls++;
    if (calls === 1) {
      await route.fulfill({ status: 200, contentType: "text/event-stream", body: "retry: 500\n\n" });
    } else {
      await route.continue();
    }
  });
  await page.goto("/");
  await expect.poll(() => calls, { timeout: 30_000 }).toBeGreaterThanOrEqual(2);
  await expect(page.getByTestId("connection-status")).toHaveAttribute("data-status", /^connected$/, { timeout: 30_000 });
  const p = page.getByTestId("price-AAPL");
  await expect(p).toHaveText(/\d+\.\d\d/);
  const v = await p.innerText();
  await expect.poll(async () => p.innerText(), { timeout: 20_000 }).not.toBe(v);
});
