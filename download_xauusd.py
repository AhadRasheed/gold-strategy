import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone


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


# ==============================
# CONNECT TO MT5
# ==============================

print("Connecting to MetaTrader 5...")

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
    print(f"{SYMBOL} was not found.")
    mt5.shutdown()
    quit()

print("Symbol:", symbol_info.name)


# Make sure symbol is visible
if not symbol_info.visible:
    print("XAUUSD is not visible. Selecting it...")
    mt5.symbol_select(SYMBOL, True)


# ==============================
# DOWNLOAD M5 DATA
# ==============================

print()
print("Downloading XAUUSD M5 data...")
print("From:", START_DATE)
print("To:", END_DATE)
print()


rates = mt5.copy_rates_range(
    SYMBOL,
    mt5.TIMEFRAME_M5,
    START_DATE,
    END_DATE
)


# ==============================
# CHECK RESULT
# ==============================

if rates is None:
    print("Failed to download data.")
    print("MT5 error:", mt5.last_error())
    mt5.shutdown()
    quit()


print("Download successful!")
print("Number of candles:", len(rates))


# ==============================
# CONVERT TO DATAFRAME
# ==============================

df = pd.DataFrame(rates)

# Convert Unix timestamp to UTC datetime
df["datetime"] = pd.to_datetime(
    df["time"],
    unit="s",
    utc=True
)

# Remove original timestamp
df.drop(columns=["time"], inplace=True)


# Rearrange columns
df = df[
    [
        "datetime",
        "open",
        "high",
        "low",
        "close",
        "tick_volume",
        "spread",
        "real_volume"
    ]
]


# ==============================
# SAVE CSV
# ==============================

filename = "XAUUSD_M5_2023_2026.csv"

df.to_csv(
    filename,
    index=False
)


# ==============================
# SHOW INFORMATION
# ==============================

print()
print("===================================")
print("DATA DOWNLOAD COMPLETE")
print("===================================")

print("Rows:", len(df))

print("First candle:")
print(df.iloc[0])

print()
print("Last candle:")
print(df.iloc[-1])

print()
print("Saved file:")
print(filename)


# ==============================
# CLOSE MT5
# ==============================

mt5.shutdown()

print()
print("MT5 connection closed.")