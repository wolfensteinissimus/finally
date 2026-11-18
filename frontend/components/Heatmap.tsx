import type { Position } from "@/lib/types";
import { layoutTreemap } from "@/lib/treemap";
import { pct } from "@/lib/format";

function colorFor(p: number): string {
  const intensity = Math.min(Math.abs(p) / 10, 1); // saturates at +/-10%
  const a = 0.25 + intensity * 0.6;
  if (p > 0) return `rgba(38, 208, 124, ${a})`;
  if (p < 0) return `rgba(255, 84, 112, ${a})`;
  return "rgba(139, 152, 173, 0.25)";
}

export default function Heatmap({ positions }: { positions: Position[] }) {
  const rects = layoutTreemap(
    positions.map((p) => ({ key: p.ticker, value: Math.abs(p.market_value) })),
    100,
    100,
  );
  const byTicker = Object.fromEntries(positions.map((p) => [p.ticker, p]));
  return (
    <section className="panel flex flex-col min-h-0 h-full" aria-label="Portfolio heatmap">
      <header className="px-3 py-2 border-b border-line">
        <h2 className="panel-title">Portfolio heatmap</h2>
      </header>
      <div className="relative flex-1 min-h-[140px] p-1" data-testid="heatmap">
        <div className="relative w-full h-full">
          {rects.map((r) => {
            const p = byTicker[r.key];
            return (
              <div
                key={r.key}
                data-testid={`heatmap-cell-${r.key}`}
                title={`${r.key}: ${pct(p.pnl_pct)}`}
                className="absolute p-[1px]"
                style={{ left: `${r.x}%`, top: `${r.y}%`, width: `${r.w}%`, height: `${r.h}%` }}
              >
                <div
                  className="w-full h-full flex flex-col items-center justify-center overflow-hidden rounded-sm"
                  style={{ background: colorFor(p.pnl_pct) }}
                >
                  <span className="font-semibold text-slate-50">{r.key}</span>
                  <span className="num text-[11px] text-slate-100/90">{pct(p.pnl_pct)}</span>
                </div>
              </div>
            );
          })}
        </div>
        {rects.length === 0 && (
          <p className="absolute inset-0 flex items-center justify-center text-slate-500 text-center px-4">
            No positions yet. Buy a share to see it here.
          </p>
        )}
      </div>
    </section>
  );
}
