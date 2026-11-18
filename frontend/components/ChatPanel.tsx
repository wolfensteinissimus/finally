"use client";
import { useEffect, useRef, useState } from "react";
import type { ChatResponse } from "@/lib/types";
import { num, usd } from "@/lib/format";

export interface ChatEntry {
  id: number;
  role: "user" | "assistant";
  content: string;
  response?: ChatResponse;
  error?: boolean;
}

interface Props {
  onSend: (message: string) => Promise<ChatResponse>;
}

export function Actions({ response }: { response: ChatResponse }) {
  const trades = response.trades ?? [];
  const wl = response.watchlist_changes ?? [];
  if (!trades.length && !wl.length) return null;
  return (
    <ul className="mt-2 space-y-1" data-testid="chat-actions">
      {trades.map((t, i) => {
        const failed = t.status !== "executed" && t.status !== "ok" && t.status !== "success";
        return (
          <li
            key={`t${i}`}
            data-testid="chat-trade"
            className={`num text-[12px] px-2 py-1 border-l-2 ${
              failed ? "border-down bg-down/10 text-down" : "border-up bg-up/10 text-up"
            }`}
          >
            {failed
              ? `Trade failed: ${t.side} ${num(t.quantity, 4)} ${t.ticker}${t.error ? ` (${t.error})` : ""}`
              : `${t.side === "buy" ? "Bought" : "Sold"} ${num(t.quantity, 4)} ${t.ticker}${
                  t.price != null ? ` @ ${usd(t.price)}` : ""
                }`}
          </li>
        );
      })}
      {wl.map((w, i) => {
        const failed = w.status !== "executed" && w.status !== "ok" && w.status !== "success";
        return (
          <li
            key={`w${i}`}
            data-testid="chat-watchlist-change"
            className={`text-[12px] px-2 py-1 border-l-2 ${
              failed ? "border-down bg-down/10 text-down" : "border-primary bg-primary/10 text-primary"
            }`}
          >
            {failed
              ? `Watchlist change failed: ${w.action} ${w.ticker}${w.error ? ` (${w.error})` : ""}`
              : `${w.action === "add" ? "Added" : "Removed"} ${w.ticker} ${w.action === "add" ? "to" : "from"} watchlist`}
          </li>
        );
      })}
    </ul>
  );
}

export default function ChatPanel({ onSend }: Props) {
  const [open, setOpen] = useState(true);
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const idRef = useRef(0);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ block: "end" });
  }, [entries, loading]);

  const send = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setEntries((es) => [...es, { id: ++idRef.current, role: "user", content: text }]);
    setLoading(true);
    try {
      const res = await onSend(text);
      setEntries((es) => [...es, { id: ++idRef.current, role: "assistant", content: res.message, response: res }]);
    } catch (err) {
      setEntries((es) => [
        ...es,
        {
          id: ++idRef.current,
          role: "assistant",
          content: err instanceof Error ? err.message : "The assistant could not respond. Try again.",
          error: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (!open) {
    return (
      <button
        data-testid="chat-toggle"
        onClick={() => setOpen(true)}
        aria-label="Open AI chat"
        className="panel h-full w-9 flex items-start justify-center pt-3 text-accent hover:bg-ink-700"
      >
        <span className="text-[11px] font-semibold" style={{ writingMode: "vertical-rl" }}>
          AI assistant
        </span>
      </button>
    );
  }

  return (
    <section className="panel flex flex-col min-h-0 h-full w-[340px] max-lg:w-[280px]" aria-label="AI chat">
      <header className="flex items-center justify-between px-3 py-2 border-b border-line">
        <h2 className="panel-title">
          <span className="text-accent">FinAlly</span> assistant
        </h2>
        <button
          data-testid="chat-toggle"
          onClick={() => setOpen(false)}
          aria-label="Collapse AI chat"
          className="text-slate-500 hover:text-slate-200 px-1"
        >
          &raquo;
        </button>
      </header>
      <div className="flex-1 overflow-y-auto p-3 space-y-3" data-testid="chat-log">
        {entries.length === 0 && (
          <p className="text-slate-500">
            Ask about your portfolio, or tell me what to trade. For example: &ldquo;Buy 5 shares of NVDA&rdquo;.
          </p>
        )}
        {entries.map((m) => (
          <div key={m.id} data-testid="chat-message" data-role={m.role} className={m.role === "user" ? "text-right" : ""}>
            <div
              className={`inline-block max-w-[92%] text-left px-3 py-2 rounded-sm whitespace-pre-wrap ${
                m.role === "user"
                  ? "bg-secondary/40 text-slate-100"
                  : m.error
                    ? "bg-down/10 text-down border border-down/30"
                    : "bg-ink-700 text-slate-200"
              }`}
            >
              {m.content}
              {m.response && <Actions response={m.response} />}
            </div>
          </div>
        ))}
        {loading && (
          <div data-testid="chat-loading" className="typing text-accent text-lg leading-none" aria-label="Assistant is thinking" role="status">
            <span>.</span><span>.</span><span>.</span>
          </div>
        )}
        <div ref={endRef} />
      </div>
      <form onSubmit={send} className="flex gap-1.5 p-2 border-t border-line">
        <input
          data-testid="chat-input"
          aria-label="Message"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Message FinAlly"
          className="flex-1 min-w-0 bg-ink-900 border border-line rounded-sm px-2 py-1.5 text-slate-100 placeholder:text-slate-600 focus:border-primary"
        />
        <button
          type="submit"
          data-testid="chat-send"
          disabled={loading || !input.trim()}
          className="px-3 py-1.5 rounded-sm bg-secondary text-white font-semibold hover:brightness-125 disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </section>
  );
}
