import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { usePrices } from "@/hooks/usePrices";

class FakeES {
  static last: FakeES;
  readyState = 0;
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  close = vi.fn();
  constructor(public url: string) { FakeES.last = this; }
}

describe("usePrices", () => {
  beforeEach(() => { (globalThis as any).EventSource = FakeES; });

  it("tracks status and accumulates prices/history", () => {
    const { result } = renderHook(() => usePrices("/api/stream/prices"));
    expect(result.current.status).toBe("reconnecting");
    act(() => FakeES.last.onopen!());
    expect(result.current.status).toBe("connected");
    act(() => FakeES.last.onmessage!({ data: JSON.stringify({ AAPL: { ticker: "AAPL", price: 190, previous_price: 189 } }) }));
    expect(result.current.prices.AAPL.price).toBe(190);
    expect(result.current.history.AAPL).toHaveLength(1);
    act(() => { FakeES.last.readyState = 0; FakeES.last.onerror!(); });
    expect(result.current.status).toBe("reconnecting");
    act(() => { FakeES.last.readyState = 2; FakeES.last.onerror!(); });
    expect(result.current.status).toBe("disconnected");
  });

  it("closes on unmount", () => {
    const { unmount } = renderHook(() => usePrices());
    const es = FakeES.last;
    unmount();
    expect(es.close).toHaveBeenCalled();
  });
});
