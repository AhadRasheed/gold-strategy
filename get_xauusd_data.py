from datetime import datetime, timezone
import MetaTrader5 as mt5
import pandas as pd


# ==============================
# SETTINGS
# ==============================

SYMBOL = "XAUUSD"

START_DATE = datetime(
    2023, 9, 1,
    tzinfo=timezone.utc
)

END_DATE = datetime(
    2026, 9, 18,
    tzinfo=timezone.utc
)

OUTPUT_FILE = "XAUUSD_5M.csv"


# ==============================
# CONNECT TO MT5
# ==============================

if not mt5.initialize():
    print("MT5 initialization failed")
    print("Error:", mt5.last_error())
    quit()

print("MT5 connected successfully.")


# ==============================
# CHECK SYMBOL
# ==============================

symbol_info = mt5.symbol_info(SYMBOL)

if symbol_info is None:
    print(f"\nSymbol '{SYMBOL}' was not found.")
    print("Check the exact Gold symbol name in Market Watch.")
    mt5.shutdown()
    quit()

print(f"Symbol found: {SYMBOL}")


# Make sure the symbol is visible
if not symbol_info.visible:
    print("Symbol is hidden. Trying to enable it...")

    if not mt5.symbol_select(SYMBOL, True):
        print("Could not enable symbol.")
        mt5.shutdown()
        quit()


# ==============================
# DOWNLOAD 5-MINUTE DATA
# ==============================

print("\nDownloading XAUUSD M5 data...")
print("Start:", START_DATE)
print("End:  ", END_DATE)

rates = mt5.copy_rates_range(
    SYMBOL,
    mt5.TIMEFRAME_M5,
    START_DATE,
    END_DATE
)


# ==============================
# CHECK DATA
# ==============================

if rates is None or len(rates) == 0:

    print("\nNo data received.")

    print("MT5 error:")
    print(mt5.last_error())

    mt5.shutdown()
    quit()


print(f"\nReceived {len(rates):,} candles.")


# ==============================
# CONVERT TO DATAFRAME
# ==============================

df = pd.DataFrame(rates)

df["time"] = pd.to_datetime(
    df["time"],
    unit="s",
    utc=True
)


# ==============================
# RENAME COLUMNS
# ==============================

df = df.rename(
    columns={
        "time": "datetime",
        "tick_volume": "volume"
    }
)


# Keep the columns our backtester needs
df = df[
    [
        "datetime",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "spread",
        "real_volume"
    ]
]


# ==============================
# REMOVE DUPLICATES
# ==============================

df = df.drop_duplicates(
    subset="datetime"
)

df = df.sort_values(
    "datetime"
)

df = df.reset_index(
    drop=True
)


# ==============================
# SAVE CSV
# ==============================

df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ==============================
# SHOW INFORMATION
# ==============================

print("\n================================")
print("DATA EXTRACTION COMPLETE")
print("================================")

print("File:", OUTPUT_FILE)
print("Candles:", f"{len(df):,}")

print(
    "First candle:",
    df["datetime"].iloc[0]
)

print(
    "Last candle:",
    df["datetime"].iloc[-1]
)

print("\nFirst 5 candles:")
print(df.head())

print("\nLast 5 candles:")
print(df.tail())


# ==============================
# CLOSE MT5
# ==============================

mt5.shutdown()

print("\nMT5 connection closed.")