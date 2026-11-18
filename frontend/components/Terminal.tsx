"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { Portfolio, Snapshot, WatchlistItem } from "@/lib/types";
import { usePrices } from "@/hooks/usePrices";
import { usePolling } from "@/hooks/usePolling";
import Header from "./Header";
import Watchlist from "./Watchlist";
import MainChart from "./MainChart";
import Heatmap from "./Heatmap";
import PnlChart from "./PnlChart";
import PositionsTable from "./PositionsTable";
import TradeBar from "./TradeBar";
import ChatPanel from "./ChatPanel";

export default function Terminal() {
  const { prices, history, status } = usePrices();
  const wl = usePolling<WatchlistItem[]>(api.watchlist, 10000);
  const pf = usePolling<Portfolio>(api.portfolio, 5000);
  const snaps = usePolling<Snapshot[]>(api.history, 15000);
  const [selected, setSelected] = useState<string | null>(null);

  const items = wl.data ?? [];
  useEffect(() => {
    if (!selected && items.length) setSelected(items[0].ticker);
  }, [items, selected]);

  // Overlay live SSE prices on the portfolio snapshot.
  const live = useMemo(() => {
    if (!pf.data) return null;
    const positions = pf.data.positions.map((p) => {
      const price = prices[p.ticker]?.price ?? p.current_price;
      const market_value = p.quantity * price;
      const unrealized_pnl = market_value - p.quantity * p.avg_cost;
      const cost = p.quantity * p.avg_cost;
      return { ...p, current_price: price, market_value, unrealized_pnl, pnl_pct: cost ? (unrealized_pnl / cost) * 100 : 0 };
    });
    return {
      ...pf.data,
      positions,
      total_value: pf.data.cash + positions.reduce((s, p) => s + p.market_value, 0),
      unrealized_pnl: positions.reduce((s, p) => s + p.unrealized_pnl, 0),
    };
  }, [pf.data, prices]);

  const refreshAll = useCallback(async () => {
    await Promise.all([pf.refresh(), snaps.refresh()]);
  }, [pf, snaps]);

  const onTrade = useCallback(
    async (ticker: string, quantity: number, side: "buy" | "sell") => {
      const res = await api.trade(ticker, quantity, side);
      pf.setData(res);
      snaps.refresh();
    },
    [pf, snaps],
  );

  const onChat = useCallback(
    async (message: string) => {
      const res = await api.chat(message);
      if (res.trades?.length) refreshAll();
      if (res.watchlist_changes?.length) wl.refresh();
      return res;
    },
    [refreshAll, wl],
  );

  const onAdd = useCallback(
    async (t: string) => {
      await api.addTicker(t);
      await wl.refresh();
    },
    [wl],
  );
  const onRemove = useCallback(
    async (t: string) => {
      await api.removeTicker(t);
      await wl.refresh();
    },
    [wl],
  );

  return (
    <div className="h-screen flex flex-col min-h-0">
      <Header
        totalValue={live?.total_value ?? null}
        cash={live?.cash ?? null}
        pnl={live?.unrealized_pnl ?? null}
        status={status}
      />
      <main className="flex-1 min-h-0 grid gap-2 p-2 grid-cols-[300px_minmax(0,1fr)_auto] max-lg:grid-cols-[260px_minmax(0,1fr)_auto]">
        <div className="min-h-0">
          <Watchlist
            items={items}
            prices={prices}
            history={history}
            selected={selected}
            onSelect={setSelected}
            onAdd={onAdd}
            onRemove={onRemove}
          />
        </div>
        <div className="min-h-0 min-w-0 grid gap-2 grid-rows-[minmax(0,1.3fr)_minmax(0,1fr)_auto_minmax(0,0.8fr)]">
          <MainChart ticker={selected} data={selected ? history[selected] ?? [] : []} />
          <div className="grid grid-cols-2 gap-2 min-h-0">
            <Heatmap positions={live?.positions ?? []} />
            <PnlChart history={snaps.data ?? []} />
          </div>
          <TradeBar selected={selected} onTrade={onTrade} />
          <PositionsTable positions={live?.positions ?? []} onSelect={setSelected} />
        </div>
        <div className="min-h-0">
          <ChatPanel onSend={onChat} />
        </div>
      </main>
    </div>
  );
}
