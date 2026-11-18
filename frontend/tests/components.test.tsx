import { describe, it, expect, vi } from "vitest";
import { render, screen, act, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PriceCell from "@/components/PriceCell";
import Watchlist from "@/components/Watchlist";
import PositionsTable from "@/components/PositionsTable";
import Heatmap from "@/components/Heatmap";
import Header from "@/components/Header";
import TradeBar from "@/components/TradeBar";
import ChatPanel from "@/components/ChatPanel";
import Sparkline from "@/components/Sparkline";
import { layoutTreemap } from "@/lib/treemap";
import { toSeries } from "@/components/PnlChart";
import type { Position, PriceUpdate, WatchlistItem } from "@/lib/types";

const pos = (ticker: string, mv: number, pnl_pct: number): Position => ({
  ticker, quantity: 2, avg_cost: 100, current_price: mv / 2, market_value: mv,
  unrealized_pnl: mv - 200, pnl_pct,
});

describe("PriceCell", () => {
  it("flashes up then down on price change", () => {
    vi.useFakeTimers();
    const { rerender } = render(<PriceCell price={100} testId="price-X" />);
    expect(screen.getByTestId("price-X")).not.toHaveAttribute("data-flash");
    rerender(<PriceCell price={101} testId="price-X" />);
    expect(screen.getByTestId("price-X")).toHaveClass("flash-up");
    rerender(<PriceCell price={100} testId="price-X" />);
    expect(screen.getByTestId("price-X")).toHaveClass("flash-down");
    act(() => { vi.advanceTimersByTime(600); });
    expect(screen.getByTestId("price-X")).not.toHaveClass("flash-down");
    vi.useRealTimers();
  });
});

describe("Watchlist", () => {
  const items: WatchlistItem[] = [
    { ticker: "AAPL", price: 190, previous_price: 189, change_pct: 0.5 },
    { ticker: "MSFT", price: null, previous_price: null, change_pct: null },
  ];
  const prices = { AAPL: { ticker: "AAPL", price: 191.5 } as PriceUpdate };

  it("renders rows with live prices and handles select/add/remove", async () => {
    const onSelect = vi.fn(), onAdd = vi.fn().mockResolvedValue(undefined), onRemove = vi.fn().mockResolvedValue(undefined);
    render(<Watchlist items={items} prices={prices} history={{}} selected="AAPL" onSelect={onSelect} onAdd={onAdd} onRemove={onRemove} />);
    expect(screen.getByTestId("price-AAPL")).toHaveTextContent("191.50");
    expect(screen.getByTestId("price-MSFT")).toHaveTextContent("--");
    await userEvent.click(screen.getByTestId("watchlist-row-MSFT"));
    expect(onSelect).toHaveBeenCalledWith("MSFT");
    await userEvent.type(screen.getByTestId("watchlist-add-input"), "pypl");
    await userEvent.click(screen.getByTestId("watchlist-add-btn"));
    expect(onAdd).toHaveBeenCalledWith("PYPL");
    await userEvent.click(screen.getByTestId("watchlist-remove-AAPL"));
    expect(onRemove).toHaveBeenCalledWith("AAPL");
    expect(onSelect).toHaveBeenCalledTimes(1);
  });

  it("shows an error when add fails", async () => {
    const onAdd = vi.fn().mockRejectedValue(new Error("Unknown ticker"));
    render(<Watchlist items={[]} prices={{}} history={{}} selected={null} onSelect={vi.fn()} onAdd={onAdd} onRemove={vi.fn()} />);
    await userEvent.type(screen.getByTestId("watchlist-add-input"), "zzz");
    await userEvent.click(screen.getByTestId("watchlist-add-btn"));
    expect(await screen.findByRole("alert")).toHaveTextContent("Unknown ticker");
  });
});

describe("Portfolio display", () => {
  it("positions table shows rows and P&L colors", () => {
    render(<PositionsTable positions={[pos("AAPL", 300, 50), pos("TSLA", 100, -50)]} />);
    expect(screen.getByTestId("positions-row-AAPL")).toHaveTextContent("+50.00%");
    expect(screen.getByTestId("positions-row-TSLA").querySelector(".text-down")).not.toBeNull();
  });
  it("positions table empty state", () => {
    render(<PositionsTable positions={[]} />);
    expect(screen.getByText(/No open positions/)).toBeInTheDocument();
  });
  it("heatmap renders a cell per position", () => {
    render(<Heatmap positions={[pos("AAPL", 300, 5), pos("TSLA", 100, -5)]} />);
    expect(screen.getByTestId("heatmap")).toBeInTheDocument();
    expect(screen.getByTestId("heatmap-cell-AAPL")).toBeInTheDocument();
    expect(screen.getByTestId("heatmap-cell-TSLA")).toBeInTheDocument();
  });
  it("header shows value, cash and connection state", () => {
    render(<Header totalValue={10500} cash={9000} pnl={500} status="reconnecting" />);
    expect(screen.getByTestId("header-total-value")).toHaveTextContent("$10,500.00");
    expect(screen.getByTestId("header-cash")).toHaveTextContent("$9,000.00");
    expect(screen.getByTestId("connection-status")).toHaveAttribute("data-status", "reconnecting");
  });
});

describe("helpers", () => {
  it("treemap areas sum to the box and are proportional", () => {
    const r = layoutTreemap([{ key: "a", value: 3 }, { key: "b", value: 1 }], 100, 100);
    const areas = Object.fromEntries(r.map((x) => [x.key, x.w * x.h]));
    expect(areas.a + areas.b).toBeCloseTo(10000, 3);
    expect(areas.a / areas.b).toBeCloseTo(3, 3);
  });
  it("toSeries dedupes and sorts ascending", () => {
    const s = toSeries([
      { recorded_at: "2025-01-01T00:00:00Z", total_value: 1 },
      { recorded_at: "2025-01-01T00:00:00Z", total_value: 2 },
      { recorded_at: "2025-01-01T00:00:30+00:00", total_value: 3 },
    ]);
    expect(s).toHaveLength(2);
    expect(s[0].value).toBe(2);
  });
  it("sparkline renders a polyline when enough data", () => {
    const { rerender } = render(<Sparkline data={[1]} />);
    expect(screen.getByTestId("sparkline-empty")).toBeInTheDocument();
    rerender(<Sparkline data={[1, 2, 3]} />);
    expect(screen.getByTestId("sparkline").querySelector("polyline")).not.toBeNull();
  });
});

describe("TradeBar", () => {
  it("submits buy and sell, shows errors", async () => {
    const onTrade = vi.fn().mockResolvedValueOnce(undefined).mockRejectedValueOnce(new Error("Insufficient cash"));
    render(<TradeBar selected={null} onTrade={onTrade} />);
    await userEvent.type(screen.getByTestId("trade-ticker"), "aapl");
    await userEvent.type(screen.getByTestId("trade-quantity"), "3");
    await userEvent.click(screen.getByTestId("trade-buy"));
    expect(onTrade).toHaveBeenCalledWith("AAPL", 3, "buy");
    await userEvent.type(screen.getByTestId("trade-quantity"), "5");
    await userEvent.click(screen.getByTestId("trade-sell"));
    expect(await screen.findByRole("alert")).toHaveTextContent("Insufficient cash");
  });
  it("validates empty quantity", async () => {
    const onTrade = vi.fn();
    render(<TradeBar selected="AAPL" onTrade={onTrade} />);
    await userEvent.click(screen.getByTestId("trade-buy"));
    expect(onTrade).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});

describe("ChatPanel", () => {
  it("shows loading, messages and inline confirmations", async () => {
    let resolve!: (v: any) => void;
    const onSend = vi.fn(() => new Promise((r) => { resolve = r; }));
    render(<ChatPanel onSend={onSend as any} />);
    await userEvent.type(screen.getByTestId("chat-input"), "buy 1 AAPL");
    await userEvent.click(screen.getByTestId("chat-send"));
    expect(screen.getByTestId("chat-loading")).toBeInTheDocument();
    await act(async () => {
      resolve({
        message: "Done.",
        trades: [{ ticker: "AAPL", side: "buy", quantity: 1, price: 190, status: "executed" }, { ticker: "TSLA", side: "buy", quantity: 99999, status: "failed", error: "Insufficient cash" }],
        watchlist_changes: [{ ticker: "PYPL", action: "add", status: "executed" }],
      });
    });
    expect(screen.queryByTestId("chat-loading")).toBeNull();
    expect(screen.getAllByTestId("chat-message")).toHaveLength(2);
    const trades = screen.getAllByTestId("chat-trade");
    expect(trades[0]).toHaveTextContent("Bought 1 AAPL @ $190.00");
    expect(trades[1]).toHaveTextContent("Trade failed");
    expect(screen.getByTestId("chat-watchlist-change")).toHaveTextContent("Added PYPL to watchlist");
  });

  it("shows an error message and can collapse", async () => {
    render(<ChatPanel onSend={vi.fn().mockRejectedValue(new Error("boom"))} />);
    await userEvent.type(screen.getByTestId("chat-input"), "hi");
    fireEvent.submit(screen.getByTestId("chat-input").closest("form")!);
    await waitFor(() => expect(screen.getByText("boom")).toBeInTheDocument());
    await userEvent.click(screen.getByTestId("chat-toggle"));
    expect(screen.queryByTestId("chat-input")).toBeNull();
  });
});
