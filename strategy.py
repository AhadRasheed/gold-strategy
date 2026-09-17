import pandas as pd
from dataclasses import dataclass

@dataclass
class Setup:
    direction: str
    entry: float
    stop: float
    target: float
    signal_time: pd.Timestamp
    entry_time: pd.Timestamp
    reason: str

def is_green(row):
    return row["close"] > row["open"]

def is_red(row):
    return row["close"] < row["open"]

def build_previous_day_levels(df):
    """
    Calculate previous calendar day's high/low from the 5M data.
    The CSV datetime timezone/session should match the intended broker data.
    """
    x = df.copy()
    x["date"] = x["datetime"].dt.date

    daily = (
        x.groupby("date", sort=True)
         .agg(day_high=("high", "max"), day_low=("low", "min"))
         .reset_index()
    )
    daily["prev_high"] = daily["day_high"].shift(1)
    daily["prev_low"] = daily["day_low"].shift(1)

    x = x.merge(
        daily[["date", "prev_high", "prev_low"]],
        on="date",
        how="left"
    )
    return x

def find_setups(df):
    """
    Implements the first deterministic interpretation of the user's rules.

    LONG:
      - price trades below previous-day low
      - green reversal candle appears below PDL
      - later candle breaks reversal candle high
      - SL = reversal candle low
      - TP = 2R

    SHORT:
      - price trades above previous-day high
      - green candle appears above PDH
      - red reversal candle follows
      - later candle breaks red reversal candle low
      - SL = red reversal candle high
      - TP = 2R

    Entry is at the level being broken, adjusted by configured slippage later.
    """
    setups = []
    state = None

    for i in range(1, len(df)):
        r = df.iloc[i]

        if pd.isna(r["prev_high"]) or pd.isna(r["prev_low"]):
            continue

        # Reset setup after crossing back inside the previous day's range.
        if state is not None:
            if state["direction"] == "LONG" and r["close"] >= r["prev_low"]:
                state = None
            elif state["direction"] == "SHORT" and r["close"] <= r["prev_high"]:
                state = None

        # Detect move outside PDH/PDL.
        if state is None:
            if r["low"] < r["prev_low"]:
                state = {
                    "direction": "LONG_WAIT",
                    "move_extreme": r["low"],
                    "reversal": None,
                    "created_i": i,
                    "prev_low": r["prev_low"],
                    "prev_high": r["prev_high"],
                }
                continue

            if r["high"] > r["prev_high"]:
                state = {
                    "direction": "SHORT_WAIT_GREEN",
                    "move_extreme": r["high"],
                    "reversal": None,
                    "created_i": i,
                    "prev_low": r["prev_low"],
                    "prev_high": r["prev_high"],
                }
                continue

        if state is None:
            continue

        # LONG: wait for green reversal candle below PDL.
        if state["direction"] == "LONG_WAIT":
            # A green candle is the reversal candle.
            if is_green(r) and r["close"] < r["prev_low"]:
                state["direction"] = "LONG_BREAK"
                state["reversal"] = r
                continue

            # Keep the lowest point of the move as possible structural SL.
            state["move_extreme"] = min(state["move_extreme"], r["low"])

        # LONG: break the reversal candle high.
        elif state["direction"] == "LONG_BREAK":
            rev = state["reversal"]

            # If price returns inside/above PDL before breaking the reversal high,
            # the setup is invalidated.
            if r["close"] >= r["prev_low"] and r["high"] < rev["high"]:
                state = None
                continue

            if r["high"] > rev["high"]:
                entry = rev["high"]
                stop = state["move_extreme"]  # last move low
                if stop < entry:
                    risk = entry - stop
                    target = entry + 2.0 * risk
                    setups.append(Setup(
                        "LONG", entry, stop, target,
                        rev["datetime"], r["datetime"],
                        "Below PDL -> green reversal -> break green high"
                    ))
                state = None

        # SHORT: wait for green candle above PDH, then red reversal candle.
        elif state["direction"] == "SHORT_WAIT_GREEN":
            if is_green(r) and r["close"] > r["prev_high"]:
                state["direction"] = "SHORT_WAIT_RED"
                state["green"] = r
                continue

            state["move_extreme"] = max(state["move_extreme"], r["high"])

        elif state["direction"] == "SHORT_WAIT_RED":
            # Red candle is the reversal candle.
            if is_red(r) and r["close"] > r["prev_high"]:
                state["direction"] = "SHORT_BREAK"
                state["reversal"] = r
                continue

            state["move_extreme"] = max(state["move_extreme"], r["high"])

        # SHORT: break red reversal candle low.
        elif state["direction"] == "SHORT_BREAK":
            rev = state["reversal"]

            if r["low"] < rev["low"]:
                entry = rev["low"]
                stop = state["move_extreme"]  # last move high
                if stop > entry:
                    risk = stop - entry
                    target = entry - 2.0 * risk
                    setups.append(Setup(
                        "SHORT", entry, stop, target,
                        rev["datetime"], r["datetime"],
                        "Above PDH -> green -> red reversal -> break red low"
                    ))
                state = None

    return setups
