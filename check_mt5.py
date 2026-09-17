import MetaTrader5 as mt5

# Connect to the running MT5 terminal
if not mt5.initialize():
    print("MT5 initialization failed")
    print("Error:", mt5.last_error())
    quit()

print("MT5 connected successfully!")

# Check XAUUSD
symbol = "XAUUSD"

info = mt5.symbol_info(symbol)

if info is None:
    print("XAUUSD was NOT found.")
else:
    print("Symbol found:", info.name)
    print("Bid:", info.bid)
    print("Ask:", info.ask)

mt5.shutdown()