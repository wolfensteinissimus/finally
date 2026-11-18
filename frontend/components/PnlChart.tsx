"use client";
import { useEffect, useRef } from "react";
import { createChart, type ISeriesApi, type UTCTimestamp } from "lightweight-charts";
import type { Snapshot } from "@/lib/types";

export function toSeries(history: Snapshot[]): { time: UTCTimestamp; value: number }[] {
  const out: { time: UTCTimestamp; value: number }[] = [];
  for (const s of history) {
    const raw = /[zZ]|[+-]\d\d:?\d\d$/.test(s.recorded_at) ? s.recorded_at : s.recorded_at + "Z";
    const t = Math.floor(new Date(raw).getTime() / 1000);
    if (Number.isNaN(t)) continue;
    const last = out[out.length - 1];
    if (last && t <= last.time) {
      if (t === last.time) last.value = s.total_value;
      continue;
    }
    out.push({ time: t as UTCTimestamp, value: s.total_value });
  }
  return out;
}

export default function PnlChart({ history }: { history: Snapshot[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const seriesRef = useRef<ISeriesApi<"Line"> | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = createChart(ref.current, {
      autoSize: true,
      layout: { background: { color: "transparent" }, textColor: "#8b98ad", fontSize: 11 },
      grid: { vertLines: { color: "#1a2230" }, horzLines: { color: "#1a2230" } },
      rightPriceScale: { borderColor: "#263142" },
      timeScale: { borderColor: "#263142", timeVisible: true },
    });
    seriesRef.current = chart.addLineSeries({ color: "#ecad0a", lineWidth: 2 });
    return () => {
      chart.remove();
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    seriesRef.current?.setData(toSeries(history));
  }, [history]);

  return (
    <section className="panel flex flex-col min-h-0 h-full" aria-label="Portfolio value over time">
      <header className="px-3 py-2 border-b border-line">
        <h2 className="panel-title">Portfolio value</h2>
      </header>
      <div className="relative flex-1 min-h-[140px]">
        <div ref={ref} className="absolute inset-0" data-testid="pnl-chart" data-points={history.length} />
      </div>
    </section>
  );
}
