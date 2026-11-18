import type { ConnectionStatus } from "@/lib/types";
import { pnlClass, signed, usd } from "@/lib/format";

const STATUS: Record<ConnectionStatus, { color: string; label: string }> = {
  connected: { color: "bg-up", label: "Live" },
  reconnecting: { color: "bg-accent dot-pulse", label: "Reconnecting" },
  disconnected: { color: "bg-down", label: "Disconnected" },
};

interface Props {
  totalValue: number | null;
  cash: number | null;
  pnl: number | null;
  status: ConnectionStatus;
}

export default function Header({ totalValue, cash, pnl, status }: Props) {
  const s = STATUS[status];
  return (
    <header className="flex items-center justify-between gap-4 px-4 h-12 border-b border-line bg-ink-950">
      <div className="flex items-baseline gap-2">
        <span className="text-[18px] font-bold tracking-tight text-slate-100">
          Fin<span className="text-accent">Ally</span>
        </span>
        <span className="text-[11px] text-slate-500 hidden sm:inline">AI trading workstation</span>
      </div>
      <div className="flex items-center gap-6">
        <div className="text-right">
          <div className="text-[10px] text-slate-500">Portfolio value</div>
          <div data-testid="header-total-value" className="num text-[16px] font-semibold text-slate-50">
            {usd(totalValue)}
          </div>
        </div>
        <div className="text-right hidden md:block">
          <div className="text-[10px] text-slate-500">Unrealized P&amp;L</div>
          <div className={`num text-[13px] ${pnlClass(pnl)}`}>{pnl == null ? "--" : signed(pnl)}</div>
        </div>
        <div className="text-right">
          <div className="text-[10px] text-slate-500">Cash</div>
          <div data-testid="header-cash" className="num text-[16px] font-semibold text-primary">
            {usd(cash)}
          </div>
        </div>
        <div className="flex items-center gap-1.5" title={s.label}>
          <span
            data-testid="connection-status"
            data-status={status}
            role="status"
            aria-label={`Connection: ${s.label}`}
            className={`inline-block w-2.5 h-2.5 rounded-full ${s.color}`}
          />
          <span className="text-[11px] text-slate-500 hidden sm:inline">{s.label}</span>
        </div>
      </div>
    </header>
  );
}
