"""Prompt construction for the FinAlly assistant."""

SYSTEM_PROMPT = """You are FinAlly, an AI trading assistant inside a simulated trading workstation.
The user trades a virtual portfolio with fake money; all orders are market orders filled instantly.

Your job:
- Analyze portfolio composition, risk concentration, and P&L.
- Suggest trades with brief reasoning.
- Execute trades when the user asks or agrees, by including them in "trades".
- Manage the watchlist proactively via "watchlist_changes" (action "add" or "remove").
- Be concise and data-driven.

Always respond with valid JSON only, matching this schema:
{"message": string, "trades": [{"ticker": string, "side": "buy"|"sell", "quantity": number}],
 "watchlist_changes": [{"ticker": string, "action": "add"|"remove"}]}
"trades" and "watchlist_changes" may be empty arrays. Only include a trade when the user wants it
executed. Trades that fail validation (insufficient cash or shares) will be reported back to the user."""


def format_portfolio(portfolio: dict) -> str:
    lines = [
        f"Cash: ${portfolio.get('cash', 0):,.2f}",
        f"Total portfolio value: ${portfolio.get('total_value', 0):,.2f}",
    ]
    if "unrealized_pnl" in portfolio:
        lines.append(f"Unrealized P&L: ${portfolio['unrealized_pnl']:,.2f}")
    positions = portfolio.get("positions") or []
    if positions:
        lines.append("Positions:")
        for p in positions:
            lines.append(
                f"- {p.get('ticker')}: qty {p.get('quantity')}, avg cost {p.get('avg_cost')}, "
                f"price {p.get('current_price')}, P&L {p.get('unrealized_pnl')} "
                f"({p.get('pnl_pct')}%)"
            )
    else:
        lines.append("Positions: none")
    watchlist = portfolio.get("watchlist") or []
    if watchlist:
        lines.append("Watchlist:")
        for w in watchlist:
            if isinstance(w, dict):
                lines.append(f"- {w.get('ticker')}: {w.get('price')}")
            else:
                lines.append(f"- {w}")
    return "\n".join(lines)


def build_messages(message: str, portfolio: dict, history: list[dict]) -> list[dict]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": "Current portfolio state:\n" + format_portfolio(portfolio)},
    ]
    for h in history:
        role = h.get("role")
        if role in ("user", "assistant") and h.get("content"):
            messages.append({"role": role, "content": h["content"]})
    messages.append({"role": "user", "content": message})
    return messages
