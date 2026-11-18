"use client";
import { useState } from "react";
import type { PriceUpdate, WatchlistItem } from "@/lib/types";
import { pct, pnlClass } from "@/lib/format";
import PriceCell from "./PriceCell";
import Sparkline from "./Sparkline";

interface Props {
  items: WatchlistItem[];
  prices: Record<string, PriceUpdate>;
  history: Record<string, { t: number; v: number }[]>;
  selected: string | null;
  onSelect: (ticker: string) => void;
  onAdd: (ticker: string) => Promise<void>;
  onRemove: (ticker: string) => Promise<void>;
}

export default function Watchlist({ items, prices, history, selected, onSelect, onAdd, onRemove }: Props) {
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const t = value.trim().toUpperCase();
    if (!t) return;
    try {
      await onAdd(t);
      setValue("");
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not add ticker");
    }
  };

  return (
    <section className="panel flex flex-col min-h-0 h-full" aria-label="Watchlist">
      <header className="flex items-center justify-between px-3 py-2 border-b border-line">
        <h2 className="panel-title">Watchlist</h2>
        <span className="num text-[11px] text-slate-500">{items.length}</span>
      </header>
      <div className="grid grid-cols-[1fr_auto_auto_auto] gap-x-2 px-3 py-1 text-[11px] text-slate-500 border-b border-line/60">
        <span>Ticker</span>
        <span className="w-[72px] text-center">Trend</span>
        <span className="text-right w-[76px]">Price</span>
        <span className="text-right w-[58px]">Chg</span>
      </div>
      <ul className="flex-1 overflow-y-auto">
        {items.map((it) => {
          const live = prices[it.ticker];
          const price = live?.price ?? it.price;
          const h = history[it.ticker] ?? [];
          const base = h.length ? h[0].v : null;
          const chg =
            base && price != null && h.length > 1 ? ((price - base) / base) * 100 : it.change_pct;
          const isSel = selected === it.ticker;
          return (
            <li
              key={it.ticker}
              data-testid={`watchlist-row-${it.ticker}`}
              onClick={() => onSelect(it.ticker)}
              className={`group grid grid-cols-[1fr_auto_auto_auto] gap-x-2 items-center px-3 py-1.5 cursor-pointer border-b border-line/40 border-l-2 ${
                isSel ? "bg-primary/10 border-l-primary" : "border-l-transparent hover:bg-ink-700/60"
              }`}
            >
              <span className="flex items-center gap-1.5 font-semibold tracking-wide text-slate-100">
                {it.ticker}
                <button
                  type="button"
                  data-testid={`watchlist-remove-${it.ticker}`}
                  aria-label={`Remove ${it.ticker}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    onRemove(it.ticker).catch(() => {});
                  }}
                  className="opacity-0 group-hover:opacity-100 focus:opacity-100 text-slate-500 hover:text-down text-[11px] leading-none px-1"
                >
                  x
                </button>
              </span>
              <span className="w-[72px]">
                <Sparkline data={h.map((p) => p.v)} />
              </span>
              <span className="text-right w-[76px]">
                <PriceCell price={price} testId={`price-${it.ticker}`} className="text-slate-100" />
              </span>
              <span className={`num text-right w-[58px] ${pnlClass(chg)}`}>{pct(chg)}</span>
            </li>
          );
        })}
        {items.length === 0 && (
          <li className="px-3 py-6 text-center text-slate-500">Add a ticker below to start watching it.</li>
        )}
      </ul>
      <form onSubmit={submit} className="flex gap-1.5 p-2 border-t border-line">
        <input
          data-testid="watchlist-add-input"
          aria-label="Add ticker"
          value={value}
          onChange={(e) => setValue(e.target.value.toUpperCase())}
          placeholder="Add ticker"
          maxLength={8}
          className="num flex-1 min-w-0 bg-ink-900 border border-line rounded-sm px-2 py-1 text-slate-100 placeholder:text-slate-600 focus:border-primary"
        />
        <button
          type="submit"
          data-testid="watchlist-add-btn"
          className="px-3 py-1 rounded-sm bg-ink-600 text-slate-200 hover:bg-primary/30"
        >
          Add
        </button>
      </form>
      {error && <p role="alert" className="px-3 pb-2 text-down text-[12px]">{error}</p>}
    </section>
  );
}
