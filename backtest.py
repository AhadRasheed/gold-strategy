import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from config import (
    INITIAL_BALANCE, RISK_PERCENT, RR,
    ENTRY_SLIPPAGE, FIXED_COST_PER_TRADE,
    ONE_POSITION_AT_A_TIME, CONSERVATIVE_SAME_BAR
)
from strategy import build_previous_day_levels, find_setups

def load_data(path):
    df = pd.read_csv(path)
    required = ["datetime", "open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df["datetime"] = pd.to_datetime(df["datetime"])
    for c in ["open", "high", "low", "close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=required).sort_values("datetime").drop_duplicates("datetime")
    df = df.reset_index(drop=True)
    return df

def simulate_trade(df, setup, balance):
    direction = setup.direction
    raw_entry = setup.entry

    # Simple adverse entry slippage.
    if direction == "LONG":
        entry = raw_entry + ENTRY_SLIPPAGE
    else:
        entry = raw_entry - ENTRY_SLIPPAGE

    stop = setup.stop
    risk_per_unit = abs(entry - stop)

    if risk_per_unit <= 0:
        return None

    risk_money = balance * (RISK_PERCENT / 100.0)
    units = risk_money / risk_per_unit

    # Find the first candle AFTER the entry candle.
    start = df.index[df["datetime"] == setup.entry_time]
    if len(start) == 0:
        return None
    start = int(start[0]) + 1

    target = (
        entry + RR * risk_per_unit
        if direction == "LONG"
        else entry - RR * risk_per_unit
    )

    for j in range(start, len(df)):
        row = df.iloc[j]

        if direction == "LONG":
            hit_sl = row["low"] <= stop
            hit_tp = row["high"] >= target
        else:
            hit_sl = row["high"] >= stop
            hit_tp = row["low"] <= target

        if hit_sl and hit_tp:
            if CONSERVATIVE_SAME_BAR:
                result = "LOSS"
                exit_price = stop
                r_mult = -1.0
            else:
                result = "WIN"
                exit_price = target
                r_mult = RR
            exit_time = row["datetime"]
            break

        if hit_sl:
            result = "LOSS"
            exit_price = stop
            r_mult = -1.0
            exit_time = row["datetime"]
            break

        if hit_tp:
            result = "WIN"
            exit_price = target
            r_mult = RR
            exit_time = row["datetime"]
            break
    else:
        # Close at final available price if neither SL nor TP is reached.
        row = df.iloc[-1]
        exit_time = row["datetime"]
        exit_price = row["close"]
        if direction == "LONG":
            r_mult = (exit_price - entry) / risk_per_unit
        else:
            r_mult = (entry - exit_price) / risk_per_unit
        result = "OPEN_AT_END"

    gross_pnl = risk_money * r_mult
    net_pnl = gross_pnl - FIXED_COST_PER_TRADE

    return {
        "signal_time": setup.signal_time,
        "entry_time": setup.entry_time,
        "exit_time": exit_time,
        "direction": direction,
        "entry": entry,
        "stop": stop,
        "target": target,
        "risk_price": risk_per_unit,
        "risk_money": risk_money,
        "units": units,
        "result": result,
        "R": r_mult,
        "gross_pnl": gross_pnl,
        "net_pnl": net_pnl,
        "reason": setup.reason,
    }

def run_backtest(df):
    df = build_previous_day_levels(df)
    setups = find_setups(df)

    balance = INITIAL_BALANCE
    rows = []
    last_exit = None

    for setup in setups:
        if ONE_POSITION_AT_A_TIME and last_exit is not None:
            if setup.entry_time <= last_exit:
                continue

        trade = simulate_trade(df, setup, balance)
        if trade is None:
            continue

        balance += trade["net_pnl"]
        trade["balance_after"] = balance
        rows.append(trade)

        if trade["result"] != "OPEN_AT_END":
            last_exit = trade["exit_time"]

    trades = pd.DataFrame(rows)

    if trades.empty:
        return trades, balance

    trades["equity"] = trades["balance_after"]
    return trades, balance

def max_drawdown(equity):
    peak = equity.cummax()
    dd = equity - peak
    dd_pct = dd / peak.replace(0, np.nan) * 100
    return dd.min(), dd_pct.min()

def make_report(trades, final_balance, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    if trades.empty:
        report = "No trades were generated. Check your data and strategy rules.\n"
        with open(os.path.join(output_dir, "backtest_report.txt"), "w", encoding="utf-8") as f:
            f.write(report)
        return

    wins = (trades["net_pnl"] > 0).sum()
    losses = (trades["net_pnl"] < 0).sum()
    total = len(trades)
    win_rate = wins / total * 100

    gross_profit = trades.loc[trades["net_pnl"] > 0, "net_pnl"].sum()
    gross_loss = abs(trades.loc[trades["net_pnl"] < 0, "net_pnl"].sum())
    profit_factor = gross_profit / gross_loss if gross_loss else float("inf")

    avg_r = trades["R"].mean()
    dd_money, dd_pct = max_drawdown(trades["equity"])

    # Consecutive losses
    max_loss_streak = 0
    streak = 0
    for r in trades["net_pnl"]:
        if r < 0:
            streak += 1
            max_loss_streak = max(max_loss_streak, streak)
        else:
            streak = 0

    report = f"""
========================================
          XAUUSD BACKTEST REPORT
========================================

Initial balance:       ${INITIAL_BALANCE:,.2f}
Final balance:         ${final_balance:,.2f}
Net profit:            ${final_balance - INITIAL_BALANCE:,.2f}

Total trades:          {total}
Winning trades:        {wins}
Losing trades:         {losses}
Win rate:              {win_rate:.2f}%

Profit factor:         {profit_factor:.3f}
Average R/trade:       {avg_r:.3f}R

Maximum drawdown:      ${dd_money:,.2f}
Maximum drawdown %:    {dd_pct:.2f}%

Max consecutive losses:{max_loss_streak}

Risk per trade:        {RISK_PERCENT:.2f}%
Risk/Reward:           1:{RR:.1f}

========================================
NOTE:
These results depend on the exact broker data,
timezone, spread, slippage and the formalized
interpretation of the strategy.
========================================
"""

    with open(os.path.join(output_dir, "backtest_report.txt"), "w", encoding="utf-8") as f:
        f.write(report.strip())

    trades.to_csv(os.path.join(output_dir, "trades.csv"), index=False)

    equity = trades[["exit_time", "equity"]].copy()
    equity.to_csv(os.path.join(output_dir, "equity_curve.csv"), index=False)

    plt.figure(figsize=(12, 5))
    plt.plot(equity["exit_time"], equity["equity"])
    plt.title("XAUUSD Strategy Equity Curve")
    plt.xlabel("Date")
    plt.ylabel("Account Balance")
    plt.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "equity_curve.png"), dpi=150)
    plt.close()
