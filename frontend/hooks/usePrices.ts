"use client";
import { useEffect, useRef, useState } from "react";
import type { ConnectionStatus, PriceUpdate } from "@/lib/types";

export const MAX_HISTORY = 600;

export interface PriceState {
  prices: Record<string, PriceUpdate>;
  /** Accumulated price history since page load, per ticker. */
  history: Record<string, { t: number; v: number }[]>;
  status: ConnectionStatus;
}

/** Connects to the SSE price stream and accumulates history. */
export function usePrices(url = "/api/stream/prices"): PriceState {
  const [prices, setPrices] = useState<Record<string, PriceUpdate>>({});
  const [status, setStatus] = useState<ConnectionStatus>("reconnecting");
  const historyRef = useRef<Record<string, { t: number; v: number }[]>>({});
  const [history, setHistory] = useState<Record<string, { t: number; v: number }[]>>({});

  useEffect(() => {
    if (typeof EventSource === "undefined") {
      setStatus("disconnected");
      return;
    }
    const es = new EventSource(url);
    es.onopen = () => setStatus("connected");
    es.onerror = () => {
      // CLOSED means the browser gave up; otherwise it is retrying on its own.
      setStatus(es.readyState === 2 ? "disconnected" : "reconnecting");
    };
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data) as Record<string, PriceUpdate>;
        setStatus("connected");
        const now = Math.floor(Date.now() / 1000);
        const h = historyRef.current;
        for (const [ticker, u] of Object.entries(data)) {
          const arr = h[ticker] ?? (h[ticker] = []);
          const last = arr[arr.length - 1];
          if (last && last.t >= now) {
            last.v = u.price; // collapse multiple updates in the same second
          } else {
            arr.push({ t: now, v: u.price });
            if (arr.length > MAX_HISTORY) arr.shift();
          }
        }
        setPrices((prev) => ({ ...prev, ...data }));
        setHistory({ ...h });
      } catch {
        /* ignore malformed event */
      }
    };
    return () => es.close();
  }, [url]);

  return { prices, history, status };
}
