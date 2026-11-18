"use client";
import { useEffect, useRef } from "react";
import { createChart, type IChartApi, type ISeriesApi, type UTCTimestamp } from "lightweight-charts";

interface Props {
  ticker: string | null;
  data: { t: number; v: number }[];
}

export default function MainChart({ ticker, data }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = createChart(ref.current, {
      autoSize: true,
      layout: { background: { color: "transparent" }, textColor: "#8b98ad", fontSize: 11 },
      grid: { vertLines: { color: "#1a2230" }, horzLines: { color: "#1a2230" } },
      rightPriceScale: { borderColor: "#263142" },
      timeScale: { borderColor: "#263142", timeVisible: true, secondsVisible: true },
      crosshair: { mode: 1 },
    });
    seriesRef.current = chart.addAreaSeries({
      lineColor: "#209dd7",
      topColor: "rgba(32,157,215,0.35)",
      bottomColor: "rgba(32,157,215,0.02)",
      lineWidth: 2,
    });
    chartRef.current = chart;
    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    seriesRef.current?.setData(data.map((p) => ({ time: p.t as UTCTimestamp, value: p.v })));
  }, [data, ticker]);

  useEffect(() => {
    chartRef.current?.timeScale().fitContent();
  }, [ticker]);

  const last = data[data.length - 1]?.v;
  return (
    <section className="panel flex flex-col min-h-0 h-full" aria-label="Main chart">
      <header className="flex items-baseline justify-between px-3 py-2 border-b border-line">
        <h2 className="panel-title">
          Chart <span className="text-accent ml-1 text-[13px]">{ticker ?? ""}</span>
        </h2>
        <span className="num text-slate-300">{last != null ? last.toFixed(2) : ""}</span>
      </header>
      <div className="relative flex-1 min-h-[160px]">
        <div ref={ref} className="absolute inset-0" data-testid="main-chart" />
        {!ticker && (
          <p className="absolute inset-0 flex items-center justify-center text-slate-500">
            Select a ticker in the watchlist.
          </p>
        )}
      </div>
    </section>
  );
}
