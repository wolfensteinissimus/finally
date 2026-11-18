import type { Position } from "@/lib/types";
import { num, pct, pnlClass, signed, usd } from "@/lib/format";

export default function PositionsTable({
  positions,
  onSelect,
}: {
  positions: Position[];
  onSelect?: (t: string) => void;
}) {
  return (
    <section className="panel flex flex-col min-h-0 h-full" aria-label="Positions">
      <header className="px-3 py-2 border-b border-line">
        <h2 className="panel-title">Positions</h2>
      </header>
      <div className="flex-1 overflow-auto">
        <table className="w-full text-[12px]">
          <thead className="text-slate-500 text-[11px] sticky top-0 bg-[#111823]">
            <tr>
              <th className="text-left font-medium px-3 py-1">Ticker</th>
              <th className="text-right font-medium px-2">Qty</th>
              <th className="text-right font-medium px-2">Avg cost</th>
              <th className="text-right font-medium px-2">Price</th>
              <th className="text-right font-medium px-2">Unrealized P&amp;L</th>
              <th className="text-right font-medium px-3">Change</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((p) => (
              <tr
                key={p.ticker}
                data-testid={`positions-row-${p.ticker}`}
                onClick={() => onSelect?.(p.ticker)}
                className="border-t border-line/40 hover:bg-ink-700/60 cursor-pointer"
              >
                <td className="px-3 py-1 font-semibold text-slate-100">{p.ticker}</td>
                <td className="num text-right px-2">{num(p.quantity, 4)}</td>
                <td className="num text-right px-2">{usd(p.avg_cost)}</td>
                <td className="num text-right px-2">{usd(p.current_price)}</td>
                <td className={`num text-right px-2 ${pnlClass(p.unrealized_pnl)}`}>{signed(p.unrealized_pnl)}</td>
                <td className={`num text-right px-3 ${pnlClass(p.pnl_pct)}`}>{pct(p.pnl_pct)}</td>
              </tr>
            ))}
            {positions.length === 0 && (
              <tr>
                <td colSpan={6} className="px-3 py-5 text-center text-slate-500">
                  No open positions. Use the trade bar to buy your first shares.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
