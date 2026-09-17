import os
from backtest import load_data, run_backtest, make_report
from config import DATA_FILE

def main():
    print("=" * 60)
    print("       XAUUSD 5-MINUTE STRATEGY BACKTESTER")
    print("=" * 60)

    if not os.path.exists(DATA_FILE):
        print(f"\nData file not found:\n{DATA_FILE}")
        print("\nPut your XAUUSD 5-minute CSV in the data folder.")
        print("Required columns: datetime, open, high, low, close")
        return

    print(f"\nLoading: {DATA_FILE}")
    df = load_data(DATA_FILE)
    print(f"Loaded candles: {len(df):,}")
    print(f"From: {df['datetime'].min()}")
    print(f"To:   {df['datetime'].max()}")

    print("\nRunning strategy...")
    trades, final_balance = run_backtest(df)

    output_dir = "results"
    make_report(trades, final_balance, output_dir)

    print("\nBacktest complete.")
    print(f"Results folder: {output_dir}/")

    if trades.empty:
        print("No trades found.")
        return

    wins = (trades["net_pnl"] > 0).sum()
    losses = (trades["net_pnl"] < 0).sum()
    win_rate = wins / len(trades) * 100

    print("\nQuick results")
    print("-" * 40)
    print(f"Trades:       {len(trades)}")
    print(f"Wins:         {wins}")
    print(f"Losses:       {losses}")
    print(f"Win rate:     {win_rate:.2f}%")
    print(f"Final balance:${final_balance:,.2f}")
    print("-" * 40)

if __name__ == "__main__":
    main()
