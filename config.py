# Backtest configuration

DATA_FILE = "data/XAUUSD_5M.csv"

# Initial account balance in USD
INITIAL_BALANCE = 10000.0

# Risk percentage of current balance per trade
RISK_PERCENT = 1.0

# Strategy risk/reward
RR = 2.0

# Estimated spread/slippage in price units.
# Example: 0.20 means subtract/add 0.20 from entry depending on direction.
# Set to 0 if your CSV already represents executable prices.
ENTRY_SLIPPAGE = 0.0

# Estimated round-trip fixed cost in account currency.
# Set to 0 if not applicable.
FIXED_COST_PER_TRADE = 0.0

# Prevent multiple simultaneous positions
ONE_POSITION_AT_A_TIME = True

# If a candle touches both SL and TP, choose SL first (conservative).
CONSERVATIVE_SAME_BAR = True
