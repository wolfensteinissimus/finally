"use client";
import { useEffect, useState } from "react";

interface Props {
  selected: string | null;
  onTrade: (ticker: string, quantity: number, side: "buy" | "sell") => Promise<void>;
}

export default function TradeBar({ selected, onTrade }: Props) {
  const [ticker, setTicker] = useState("");
  const [qty, setQty] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => {
    if (selected) setTicker(selected);
  }, [selected]);

  const submit = async (side: "buy" | "sell") => {
    const t = ticker.trim().toUpperCase();
    const q = parseFloat(qty);
    if (!t) return setMsg({ ok: false, text: "Enter a ticker." });
    if (!(q > 0)) return setMsg({ ok: false, text: "Enter a quantity greater than 0." });
    setBusy(true);
    try {
      await onTrade(t, q, side);
      setMsg({ ok: true, text: `${side === "buy" ? "Bought" : "Sold"} ${q} ${t}` });
      setQty("");
    } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : "Trade failed" });
    } finally {
      setBusy(false);
    }
  };

  const field =
    "num bg-ink-900 border border-line rounded-sm px-2 py-1.5 text-slate-100 placeholder:text-slate-600 focus:border-primary";
  return (
    <section className="panel px-3 py-2 flex flex-wrap items-center gap-2" aria-label="Trade">
      <h2 className="panel-title mr-1">Trade</h2>
      <input
        data-testid="trade-ticker"
        aria-label="Ticker"
        placeholder="Ticker"
        value={ticker}
        maxLength={8}
        onChange={(e) => setTicker(e.target.value.toUpperCase())}
        className={`${field} w-24`}
      />
      <input
        data-testid="trade-quantity"
        aria-label="Quantity"
        placeholder="Quantity"
        type="number"
        min="0"
        step="any"
        value={qty}
        onChange={(e) => setQty(e.target.value)}
        className={`${field} w-28`}
      />
      <button
        data-testid="trade-buy"
        disabled={busy}
        onClick={() => submit("buy")}
        className="px-4 py-1.5 rounded-sm bg-up/20 text-up font-semibold hover:bg-up/30 disabled:opacity-50"
      >
        Buy
      </button>
      <button
        data-testid="trade-sell"
        disabled={busy}
        onClick={() => submit("sell")}
        className="px-4 py-1.5 rounded-sm bg-down/20 text-down font-semibold hover:bg-down/30 disabled:opacity-50"
      >
        Sell
      </button>
      {msg && (
        <span
          data-testid="trade-message"
          role={msg.ok ? "status" : "alert"}
          className={`text-[12px] ${msg.ok ? "text-up" : "text-down"}`}
        >
          {msg.text}
        </span>
      )}
    </section>
  );
}
