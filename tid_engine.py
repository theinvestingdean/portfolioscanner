"""
TID Quantitative Decision Support Engine
Translates exact Pine Script algorithms from:
- TID_IA13_Portfolio_Master_Scanner.pine
- TID_DCA_Efficiency_Dashboard_v2.0.pine
- IA_Optimized_Trend.pine
"""

import time
from concurrent.futures import ThreadPoolExecutor
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Dict, List, Any, Optional, Tuple, Set

UK_TZ = ZoneInfo("Europe/London")
NY_TZ = ZoneInfo("America/New_York")

# In-memory cache for quarterly earnings dates (refreshes every 12 hours)
_EARNINGS_CACHE: Dict[str, Tuple[float, Optional[pd.DataFrame]]] = {}
_EARNINGS_TTL_SECONDS = 43200.0

def get_uk_now_str() -> str:
    """Returns current UK date/time string with automatic GMT/BST label."""
    return datetime.now(UK_TZ).strftime("%d %b, %H:%M:%S %Z")

# 17-Stock Portfolio Watchlist Configuration
PORTFOLIO_TICKERS = [
    {"symbol": "ALAB", "display": "ALAB", "name": "Astera Labs", "market": "NASDAQ", "currency": "$"},
    {"symbol": "AMD", "display": "AMD", "name": "Advanced Micro Devices", "market": "NASDAQ", "currency": "$"},
    {"symbol": "ARM", "display": "ARM", "name": "ARM Holdings", "market": "NASDAQ", "currency": "$"},
    {"symbol": "ASML", "display": "ASML", "name": "ASML Holding", "market": "NASDAQ", "currency": "$"},
    {"symbol": "AVGO", "display": "AVGO", "name": "Broadcom", "market": "NASDAQ", "currency": "$"},
    {"symbol": "GOOG", "display": "GOOG", "name": "Alphabet / Google", "market": "NASDAQ", "currency": "$"},
    {"symbol": "MRVL", "display": "MRVL", "name": "Marvell Tech", "market": "NASDAQ", "currency": "$"},
    {"symbol": "MU", "display": "MU", "name": "Micron Tech", "market": "NASDAQ", "currency": "$"},
    {"symbol": "NVDA", "display": "NVDA", "name": "Nvidia", "market": "NASDAQ", "currency": "$"},
    {"symbol": "PLTR", "display": "PLTR", "name": "Palantir Tech", "market": "NASDAQ", "currency": "$"},
    {"symbol": "SKHY", "display": "SKHY", "name": "SK Hynix ADR", "market": "NASDAQ", "currency": "$"},
    {"symbol": "SMSN.IL", "display": "SMSN", "name": "Samsung Electronics GDR", "market": "LSE", "currency": "$"},
    {"symbol": "SPCX", "display": "SPCX", "name": "SpaceX Tech", "market": "NASDAQ", "currency": "$"},
    {"symbol": "TSLA", "display": "TSLA", "name": "Tesla", "market": "NASDAQ", "currency": "$"},
    {"symbol": "TSM", "display": "TSM", "name": "TSMC", "market": "NYSE", "currency": "$"},
    {"symbol": "SMGB.L", "display": "SMGB", "name": "VanEck Semi UCITS", "market": "LSE", "currency": "$"},
    {"symbol": "XNAQ.L", "display": "XNAQ", "name": "Xtrackers NASDAQ 100", "market": "LSE", "currency": "$"}
]

def f_lerp(val: float, x1: float, y1: float, x2: float, y2: float) -> float:
    """Linear interpolation matching Pine Script helper."""
    if x2 == x1:
        return y1
    return y1 + (val - x1) * (y2 - y1) / (x2 - x1)

def f_score_z(z: float) -> float:
    """Pillar 1: 50-Day Standard Deviation Z-Score continuous score (1.0 - 10.0)."""
    if np.isnan(z):
        return 5.5
    if z <= -3.0:
        return 10.0
    elif z <= -2.0:
        return f_lerp(z, -3.0, 10.0, -2.0, 8.8)
    elif z <= -1.2:
        return f_lerp(z, -2.0, 8.8, -1.2, 7.5)
    elif z <= 0.0:
        return f_lerp(z, -1.2, 7.5, 0.0, 5.5)
    elif z <= 1.2:
        return f_lerp(z, 0.0, 5.5, 1.2, 3.2)
    elif z <= 2.2:
        return f_lerp(z, 1.2, 3.2, 2.2, 1.3)
    elif z < 2.6:
        return f_lerp(z, 2.2, 1.3, 2.6, 1.0)
    else:
        return 1.0

def f_score_rsi(r: float) -> float:
    """Pillar 2: Daily 14 RSI continuous score (1.0 - 10.0)."""
    if np.isnan(r):
        return 5.5
    if r <= 25.0:
        return 10.0
    elif r <= 32.0:
        return f_lerp(r, 25.0, 10.0, 32.0, 8.8)
    elif r <= 40.0:
        return f_lerp(r, 32.0, 8.8, 40.0, 7.4)
    elif r <= 50.0:
        return f_lerp(r, 40.0, 7.4, 50.0, 5.5)
    elif r <= 60.0:
        return f_lerp(r, 50.0, 5.5, 60.0, 3.4)
    elif r <= 68.0:
        return f_lerp(r, 60.0, 3.4, 68.0, 1.6)
    elif r < 73.0:
        return f_lerp(r, 68.0, 1.6, 73.0, 1.0)
    else:
        return 1.0

def f_score_sma(d50: float, d200: float, has50: bool, has200: bool) -> float:
    """Pillar 3: 50 & 200 SMA Structural Discount continuous score."""
    s50 = 5.5
    if has50 and not np.isnan(d50):
        if d50 <= -12.0:
            s50 = 10.0
        elif d50 <= -5.0:
            s50 = f_lerp(d50, -12.0, 10.0, -5.0, 8.3)
        elif d50 <= 0.0:
            s50 = f_lerp(d50, -5.0, 8.3, 0.0, 6.5)
        elif d50 <= 8.0:
            s50 = f_lerp(d50, 0.0, 6.5, 8.0, 3.0)
        elif d50 < 15.0:
            s50 = f_lerp(d50, 8.0, 3.0, 15.0, 1.0)
        else:
            s50 = 1.0

    s200 = 5.5
    if has200 and not np.isnan(d200):
        if d200 <= -12.0:
            s200 = 10.0
        elif d200 <= 0.0:
            s200 = f_lerp(d200, -12.0, 10.0, 0.0, 8.5)
        elif d200 <= 10.0:
            s200 = f_lerp(d200, 0.0, 8.5, 10.0, 5.5)
        elif d200 <= 22.0:
            s200 = f_lerp(d200, 10.0, 5.5, 22.0, 2.2)
        elif d200 < 32.0:
            s200 = f_lerp(d200, 22.0, 2.2, 32.0, 1.0)
        else:
            s200 = 1.0

    if has200 and has50:
        return (s50 * 0.60) + (s200 * 0.40)
    elif has50:
        return s50
    return 5.5

def f_score_analyst(upPct: float) -> float:
    """Pillar 4 (Optional): 12M Analyst Upside %."""
    if np.isnan(upPct):
        return 5.0
    if upPct >= 35.0:
        return 10.0
    elif upPct >= 20.0:
        return f_lerp(upPct, 20.0, 8.2, 35.0, 10.0)
    elif upPct >= 10.0:
        return f_lerp(upPct, 10.0, 6.2, 20.0, 8.2)
    elif upPct >= 0.0:
        return f_lerp(upPct, 0.0, 4.0, 10.0, 6.2)
    elif upPct > -15.0:
        return f_lerp(upPct, -15.0, 1.0, 0.0, 4.0)
    else:
        return 1.0

def _fetch_cached_earnings(sym: str) -> Tuple[str, Optional[pd.DataFrame]]:
    """Fetches historical quarterly earnings dates with 12-hour in-memory caching."""
    if sym.endswith(".L") or sym in ("SPCX",):
        return sym, None
    now_t = time.time()
    cached = _EARNINGS_CACHE.get(sym)
    if cached is not None and (now_t - cached[0]) < _EARNINGS_TTL_SECONDS:
        return sym, cached[1]
    try:
        ed = yf.Ticker(sym).get_earnings_dates(limit=16)
    except Exception:
        ed = None
    _EARNINGS_CACHE[sym] = (now_t, ed)
    return sym, ed


def _map_tv_earnings_bar_dates(ed: Optional[pd.DataFrame], trading_dates: pd.DatetimeIndex) -> Set:
    """
    Maps reported quarterly earnings timestamps to TradingView daily bar dates
    (post-market >= 16:00 ET aligns to the next trading session bar, matching lookahead_off).
    """
    er_bar_dates: Set = set()
    if ed is None or ed.empty:
        return er_bar_dates
    try:
        reported = ed[~ed["Reported EPS"].isna()] if "Reported EPS" in ed.columns else ed
        td_list = sorted([ts.date() for ts in trading_dates])
        for ets in reported.index:
            ets_ny = ets.tz_convert(NY_TZ) if ets.tzinfo is not None else ets.tz_localize(NY_TZ)
            edate = ets_ny.date()
            if ets_ny.hour >= 16:
                next_dates = [d for d in td_list if d > edate]
                if next_dates:
                    er_bar_dates.add(next_dates[0])
            else:
                same_or_next = [d for d in td_list if d >= edate]
                if same_or_next:
                    er_bar_dates.add(same_or_next[0])
    except Exception:
        pass
    return er_bar_dates


def _patch_daily_with_intraday(df: pd.DataFrame, df_intra: Optional[pd.DataFrame], market: str) -> pd.DataFrame:
    """
    Patches any trailing NaN daily Close rows (common on LSE ETFs pre-open on Yahoo Finance)
    using 15-minute intraday candles for that session, then drops any remaining empty rows.
    """
    df = df.copy()
    if df_intra is not None and not df_intra.empty and not df.empty:
        try:
            exch_tz = UK_TZ if market == "LSE" else NY_TZ
            intra_idx = df_intra.index
            intra_local = (
                df_intra.tz_localize("UTC").tz_convert(exch_tz)
                if intra_idx.tz is None
                else df_intra.tz_convert(exch_tz)
            )
            for idx_ts in df.index[-3:]:
                if pd.isna(df.loc[idx_ts, "Close"]):
                    d_bars = intra_local[intra_local.index.date == idx_ts.date()].dropna(subset=["Close"])
                    if not d_bars.empty:
                        df.loc[idx_ts, "Open"] = float(d_bars["Open"].iloc[0])
                        df.loc[idx_ts, "High"] = float(d_bars["High"].max())
                        df.loc[idx_ts, "Low"] = float(d_bars["Low"].min())
                        df.loc[idx_ts, "Close"] = float(d_bars["Close"].iloc[-1])
                        if pd.isna(df.loc[idx_ts, "Volume"]) or df.loc[idx_ts, "Volume"] == 0:
                            df.loc[idx_ts, "Volume"] = float(d_bars["Volume"].sum())
        except Exception:
            pass
    return df.dropna(subset=["Close"])


def _is_session_still_open(sig_ts: pd.Timestamp, market: str) -> bool:
    """Returns True only while the signal's daily market session is actively open (not after close)."""
    exch_tz = UK_TZ if market == "LSE" else NY_TZ
    open_hm = (8, 0) if market == "LSE" else (9, 30)
    close_hm = (16, 30) if market == "LSE" else (16, 0)
    d = sig_ts.date()
    session_open = datetime(d.year, d.month, d.day, open_hm[0], open_hm[1], tzinfo=exch_tz).astimezone(UK_TZ)
    session_close = datetime(d.year, d.month, d.day, close_hm[0], close_hm[1], tzinfo=exch_tz).astimezone(UK_TZ)
    now_uk = datetime.now(UK_TZ)
    return session_open <= now_uk < session_close


def compute_technical_indicators(
    df: pd.DataFrame,
    er_bar_dates: Optional[Set] = None
) -> pd.DataFrame:
    """
    Calculates exact 1:1 Pine Script indicators matching:
    - TID - DCA Efficiency Dashboard v2.0 (DCA Score, Std. Dev., RSI 14, 1D CVD Order Flow, Inst. Vol)
    - TID - Optimised Trend v1.1 (IA_Optimized_Trend.pine: Kaufman ER Adaptive Ribbon, Dual Z-Score
      Pre-Shock Envelope, 7-bar Fast RSI, 1.15x Vol Climax, Knife Guard, 10-bar Duplicate Signal
      Suppression, 4-bar Ghost Suppression, and Quarterly Earnings Guard).
    """
    df = df.copy()
    c = df["Close"].astype(float)
    o = df["Open"].astype(float).fillna(c)
    h = df["High"].astype(float).fillna(c)
    l = df["Low"].astype(float).fillna(c)
    v = df["Volume"].astype(float).fillna(0.0)
    n = len(df)
    er_dates = er_bar_dates or set()

    # 1. SMAs & Raw 50-Day Standard Deviation (confLen = 50, confMult = 2.2)
    df["SMA50"] = c.rolling(50).mean()
    df["STDEV50"] = c.rolling(50).std(ddof=0)
    df["ZScore"] = (c - df["SMA50"]) / df["STDEV50"].replace(0, np.nan)
    df["ZScoreLow"] = (l - df["SMA50"]) / df["STDEV50"].replace(0, np.nan)
    df["SMA200"] = c.rolling(200).mean()

    # 2. RSI 14 & RSI Fast 7 (Wilder's Smoothing — matches IA_Optimized_Trend.pine lines 231-232)
    delta = c.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    avg_gain14 = gain.ewm(alpha=1.0 / 14.0, min_periods=14, adjust=False).mean()
    avg_loss14 = loss.ewm(alpha=1.0 / 14.0, min_periods=14, adjust=False).mean()
    rs14 = avg_gain14 / avg_loss14.replace(0, np.nan)
    df["RSI14"] = (100.0 - (100.0 / (1.0 + rs14))).fillna(50.0).where(avg_loss14 != 0, 100.0)

    avg_gain7 = gain.ewm(alpha=1.0 / 7.0, min_periods=7, adjust=False).mean()
    avg_loss7 = loss.ewm(alpha=1.0 / 7.0, min_periods=7, adjust=False).mean()
    rs7 = avg_gain7 / avg_loss7.replace(0, np.nan)
    df["RSIFast"] = (100.0 - (100.0 / (1.0 + rs7))).fillna(50.0).where(avg_loss7 != 0, 100.0)

    # 3. True Range & ATR 14
    prev_close = c.shift(1)
    tr = pd.concat([(h - l), (h - prev_close).abs(), (l - prev_close).abs()], axis=1).max(axis=1)
    df["ATR14"] = tr.ewm(alpha=1.0 / 14.0, min_periods=14, adjust=False).mean()

    # 4. TID - Optimised Trend v1.1 Auto-Optimization Engine (IA_Optimized_Trend.pine lines 66-150)
    net_chg20 = (c - c.shift(20).fillna(c)).abs()
    sum_chg20 = (c - prev_close.fillna(c)).abs().rolling(20).sum()
    raw_er = np.where(sum_chg20 > 0, net_chg20 / sum_chg20, 0.5)
    smooth_er = pd.Series(raw_er, index=df.index).ewm(span=10, adjust=False).mean()

    atr_pct = np.where(c > 0, (df["ATR14"] / c) * 100.0, 1.0)
    base_atr_pct = pd.Series(atr_pct, index=df.index).rolling(100).mean()
    vol_ratio = np.where(base_atr_pct > 0, np.clip(atr_pct / base_atr_pct, 0.6, 1.8), 1.0)

    vol_sma20 = v.rolling(20).mean()
    vol_sma50 = v.rolling(50).mean()
    rel_vol = np.where(vol_sma50 > 0, np.clip(v / vol_sma50, 0.5, 2.5), 1.0)
    vol_boost = pd.Series(rel_vol, index=df.index).ewm(span=5, adjust=False).mean()

    dyn_mod = 1.30 - (0.55 * smooth_er * np.sqrt(vol_boost / vol_ratio))
    calc_fast_len = np.maximum(4.0, 10.0 * dyn_mod)
    calc_slow_len = np.maximum(calc_fast_len + 3.0, calc_fast_len * 1.618)

    raw_opt_fast = np.zeros(n)
    raw_opt_slow = np.zeros(n)
    c_arr = c.values
    f_arr = calc_fast_len.values
    s_arr = calc_slow_len.values
    for i in range(n):
        af = 2.0 / (max(1.0, f_arr[i]) + 1.0) if not np.isnan(f_arr[i]) else (2.0 / 11.0)
        as_ = 2.0 / (max(1.0, s_arr[i]) + 1.0) if not np.isnan(s_arr[i]) else (2.0 / 17.0)
        if i == 0:
            raw_opt_fast[i] = c_arr[i]
            raw_opt_slow[i] = c_arr[i]
        else:
            raw_opt_fast[i] = af * c_arr[i] + (1.0 - af) * raw_opt_fast[i - 1]
            raw_opt_slow[i] = as_ * c_arr[i] + (1.0 - as_) * raw_opt_slow[i - 1]

    chop_damp = np.clip(smooth_er.values / 0.30, 0.25, 1.0)
    opt_mid = (raw_opt_fast + raw_opt_slow) * 0.5
    opt_fast = opt_mid + (raw_opt_fast - opt_mid) * chop_damp
    opt_slow = np.roll(raw_opt_slow, 1)
    if n > 0:
        opt_slow[0] = raw_opt_slow[0]

    deadband = df["ATR14"].fillna(0.0).values * 0.20
    opt_bullish = np.ones(n, dtype=bool)
    bars_since_bear_flip = np.full(n, 100, dtype=int)
    cur_bull = True
    bs_bear = 100
    for i in range(n):
        prev_bear = True if i == 0 else opt_bullish[i - 1]
        if opt_fast[i] > opt_slow[i] + deadband[i]:
            cur_bull = True
        elif opt_fast[i] < opt_slow[i] - deadband[i]:
            cur_bull = False
        opt_bullish[i] = cur_bull
        if (not cur_bull) and prev_bear:
            bs_bear = 0
        else:
            bs_bear += 1
        bars_since_bear_flip[i] = bs_bear

    df["FastEMA"] = opt_fast
    df["SlowEMA"] = opt_slow
    df["IsBull"] = opt_bullish
    opt_slow_s = pd.Series(opt_slow, index=df.index)
    df["RibbonSlope"] = (opt_slow_s - opt_slow_s.shift(3).fillna(opt_slow_s)) / df["ATR14"].replace(0, 1e-6)

    # 5. Distances
    df["Dist50"] = ((c - df["SMA50"]) / df["SMA50"]) * 100.0
    df["Dist200"] = ((c - df["SMA200"]) / df["SMA200"]) * 100.0
    df["ATH"] = h.cummax()
    df["DistATH"] = ((c - df["ATH"]) / df["ATH"]) * 100.0

    # 6. MACD (12, 26, 9)
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    df["MACD_Hist"] = macd_line - signal_line

    # 7. Smart Order Flow (1D CVD) & Institutional Volume
    range_hl = (h - l).replace(0, 1e-6)
    df["BuyVol"] = v * ((c - l) / range_hl)
    df["SellVol"] = v * ((h - c) / range_hl)
    df["NetDelta"] = df["BuyVol"] - df["SellVol"]
    df["rCVD"] = df["NetDelta"].rolling(30).sum()
    df["CVDSig"] = df["rCVD"].rolling(14).mean()
    df["CVDSlope"] = df["rCVD"].diff()
    df["AvgVol"] = vol_sma20

    df["InstSpike"] = v > (df["AvgVol"] * 1.5)
    df["InstBuying"] = (df["NetDelta"] >= 0) & df["InstSpike"] & (df["rCVD"] > df["CVDSig"])
    df["InstSelling"] = (df["NetDelta"] < 0) & df["InstSpike"] & (df["rCVD"] < df["CVDSig"])

    # 8. Exact TID - Optimised Trend v1.1 Envelope, Ghost Cap & Confirmed Reversal Signals
    # (Matches IA_Optimized_Trend.pine lines 199-302 & 360-362)
    conf_basis = df["SMA50"]
    raw_stdev = df["STDEV50"]
    pre_shock_vol = raw_stdev.ewm(span=15, adjust=False).mean().shift(3).fillna(raw_stdev)
    atr_vol_unit = df["ATR14"].rolling(50).mean() * 1.25
    eff_unit = np.minimum(raw_stdev, np.maximum(pre_shock_vol, atr_vol_unit))

    raw_conf_upper = conf_basis + 2.2 * raw_stdev
    raw_conf_lower = conf_basis - 2.2 * raw_stdev
    df["ConfUpper"] = raw_conf_upper.ewm(span=3, adjust=False).mean()
    df["ConfLower"] = raw_conf_lower.ewm(span=3, adjust=False).mean()

    z_close_raw = np.where(raw_stdev > 0, (c - conf_basis) / raw_stdev, 0.0)
    z_low_raw = np.where(raw_stdev > 0, (l - conf_basis) / raw_stdev, 0.0)
    z_low_shock = np.where(eff_unit > 0, (l - conf_basis) / eff_unit, 0.0)
    eff_z_low = pd.Series(np.minimum(z_low_raw, z_low_shock), index=df.index)
    eff_z_close = pd.Series(np.where(eff_unit > 0, (c - conf_basis) / eff_unit, z_close_raw), index=df.index)

    z_smooth = eff_z_close.ewm(span=2, adjust=False).mean()
    z_slope = z_smooth.diff()

    lower_wick = (c - l) / (h - l).clip(lower=1e-6)
    is_vol_spike = (vol_sma20 > 0) & (v >= vol_sma20 * 1.15)

    buy_sigma_thresh = -2.2 * 0.82
    buy_rsi_limit = 42.0
    min_bars_between = 10

    min_z6 = eff_z_low.rolling(6).min()
    min_rsi6 = df["RSI14"].rolling(6).min()
    lowest_low6 = l.rolling(6).min()
    pierced_lower6 = ((l - df["ConfLower"]).rolling(6).min() <= (df["ATR14"] * 0.20)) | (min_z6 <= buy_sigma_thresh)

    raw_ghost_buy = (
        ((l <= df["ConfLower"]) | (eff_z_low <= buy_sigma_thresh))
        & ((df["RSI14"] <= buy_rsi_limit) | (df["RSIFast"] <= 30.0))
        & ((c <= o) | (lower_wick >= 0.45))
    )

    bull_pa = ((c > o) & (c > prev_close)) | ((lower_wick >= 0.55) & (c > prev_close) & is_vol_spike)
    bull_mom = (z_slope > 0) & (df["RSIFast"] > df["RSIFast"].shift(1))
    knife_guard_ok = (bars_since_bear_flip > 4) | (min_z6 <= -2.3) | (l <= (df["ConfLower"] - df["ATR14"] * 0.3))
    trend_buy_ok = (
        df["IsBull"]
        | (df["RibbonSlope"] > -0.35)
        | (lowest_low6 <= (df["ConfLower"] + df["ATR14"] * 0.05))
        | (min_z6 <= -2.0)
    )

    cand_buy = pierced_lower6 & ((min_rsi6 <= buy_rsi_limit) | (min_z6 <= -2.1)) & bull_pa & bull_mom & knife_guard_ok & trend_buy_ok

    # Stateful bar-by-bar evaluation for Duplicate Signal Suppression & Quarterly Earnings Guard
    ghost_arr = np.zeros(n, dtype=bool)
    conf_arr = np.zeros(n, dtype=bool)
    last_ghost_bar = -100
    last_conf_bar = -200
    last_conf_px = 0.0
    last_er_date = None

    for i in range(n):
        bdate = df.index[i].date()
        is_er_bar = bdate in er_dates
        if is_er_bar:
            last_er_date = bdate
        days_since_er = (bdate - last_er_date).days if last_er_date is not None else 0.0
        in_pre_er = ((not is_er_bar) and (85.0 <= days_since_er <= 96.0)) or (is_er_bar and c.iloc[i] >= o.iloc[i])

        gb = False
        if bool(raw_ghost_buy.iloc[i]) and (i - last_ghost_bar >= 4):
            gb = True
            last_ghost_bar = i

        cb = False
        er_warn = False
        if bool(cand_buy.iloc[i]):
            atr_i = float(df["ATR14"].iloc[i]) if not np.isnan(df["ATR14"].iloc[i]) else 0.0
            deeper_flush = (
                (i - last_conf_bar >= 4)
                and (l.iloc[i] < last_conf_px - atr_i * 1.2)
                and (eff_z_low.iloc[i] <= -2.2)
            )
            if (i - last_conf_bar >= min_bars_between) or deeper_flush:
                if in_pre_er:
                    er_warn = True
                else:
                    cb = True
                    last_conf_bar = i
                    last_conf_px = float(l.iloc[i])

        conf_arr[i] = cb
        ghost_arr[i] = gb and (not cb) and (not er_warn)

    df["ConfBuy"] = conf_arr
    df["GhostBuy"] = ghost_arr
    return df


def _resolve_uk_signal_time(
    df_daily: pd.DataFrame,
    df_intra: Optional[pd.DataFrame],
    target_ts: pd.Timestamp,
    sig_type: str = "GHOST",
    market: str = "NASDAQ"
) -> Tuple[float, str, str]:
    """
    Pinpoints the exact UK timezone (GMT/BST) date & time when a daily Ghost Cap
    or Confirmed Buy flashed by scanning 15-minute intraday candles on that date.
    Returns (sort_epoch, short_uk_str, full_uk_str).
    """
    target_date = target_ts.date()
    exch_tz = UK_TZ if market == "LSE" else NY_TZ

    if df_intra is not None and not df_intra.empty:
        try:
            intra_idx = df_intra.index
            if intra_idx.tz is None:
                intra_local = df_intra.tz_localize("UTC").tz_convert(exch_tz)
            else:
                intra_local = df_intra.tz_convert(exch_tz)

            day_bars = intra_local[intra_local.index.date == target_date]
            if not day_bars.empty:
                loc = df_daily.index.get_loc(target_ts)
                if isinstance(loc, int) and loc >= 49:
                    prev_closes = df_daily["Close"].iloc[loc - 49:loc].values
                    prev_c = float(df_daily["Close"].iloc[loc - 1])
                    prev_conf_low = float(df_daily["ConfLower"].iloc[loc - 1]) if not np.isnan(df_daily["ConfLower"].iloc[loc - 1]) else None

                    c_hist = df_daily["Close"].iloc[:loc]
                    delta = c_hist.diff()
                    g = delta.clip(lower=0.0)
                    ls = -delta.clip(upper=0.0)
                    ag14_prev = float(g.ewm(alpha=1.0 / 14.0, min_periods=14, adjust=False).mean().iloc[-1])
                    al14_prev = float(ls.ewm(alpha=1.0 / 14.0, min_periods=14, adjust=False).mean().iloc[-1])
                    ag7_prev = float(g.ewm(alpha=1.0 / 7.0, min_periods=7, adjust=False).mean().iloc[-1])
                    al7_prev = float(ls.ewm(alpha=1.0 / 7.0, min_periods=7, adjust=False).mean().iloc[-1])

                    open_d = float(day_bars["Open"].iloc[0])
                    run_h = -1e18
                    run_l = 1e18

                    if sig_type == "GHOST":
                        for ts, row in day_bars.iterrows():
                            bh, bl, bc = float(row["High"]), float(row["Low"]), float(row["Close"])
                            if np.isnan(bc):
                                continue
                            run_h = max(run_h, bh)
                            run_l = min(run_l, bl)

                            c50 = np.append(prev_closes, bc)
                            sma50 = float(np.mean(c50))
                            std50 = float(np.std(c50, ddof=0))
                            if std50 <= 0:
                                continue
                            raw_cl = sma50 - 2.2 * std50
                            conf_lower = (0.5 * raw_cl + 0.5 * prev_conf_low) if prev_conf_low is not None else raw_cl
                            z_low = (run_l - sma50) / std50

                            chg = bc - prev_c
                            gn = max(chg, 0.0)
                            lo = max(-chg, 0.0)
                            ag14 = (ag14_prev * 13.0 + gn) / 14.0
                            al14 = (al14_prev * 13.0 + lo) / 14.0
                            rsi14 = 100.0 if al14 == 0 else (100.0 - 100.0 / (1.0 + ag14 / al14))

                            ag7 = (ag7_prev * 6.0 + gn) / 7.0
                            al7 = (al7_prev * 6.0 + lo) / 7.0
                            rsi7 = 100.0 if al7 == 0 else (100.0 - 100.0 / (1.0 + ag7 / al7))

                            rng = max(run_h - run_l, 1e-6)
                            lower_wick = (bc - run_l) / rng

                            if (
                                (run_l <= conf_lower or z_low <= -2.2 * 0.82)
                                and (rsi14 <= 42.0 or rsi7 <= 30.0)
                                and (bc <= open_d or lower_wick >= 0.45)
                            ):
                                uk_dt = ts.tz_convert(UK_TZ)
                                return (
                                    uk_dt.timestamp(),
                                    uk_dt.strftime("%d %b, %H:%M %Z"),
                                    uk_dt.strftime("%d %b %Y, %H:%M %Z"),
                                )

                if sig_type == "CONFIRMED":
                    # Confirmed Buy locks on session bar close (or latest 15m bar if session still live)
                    last_bar_end = day_bars.index[-1] + pd.Timedelta(minutes=15)
                    now_uk = pd.Timestamp.now(tz=UK_TZ)
                    uk_dt = last_bar_end.tz_convert(UK_TZ)
                    if uk_dt > now_uk:
                        uk_dt = day_bars.index[-1].tz_convert(UK_TZ)
                    return (
                        uk_dt.timestamp(),
                        uk_dt.strftime("%d %b, %H:%M %Z"),
                        uk_dt.strftime("%d %b %Y, %H:%M %Z"),
                    )

                # Fallback for Ghost Cap within 60d window: exact time of session low
                min_ts = day_bars["Low"].idxmin()
                uk_dt = min_ts.tz_convert(UK_TZ)
                return (
                    uk_dt.timestamp(),
                    uk_dt.strftime("%d %b, %H:%M %Z"),
                    uk_dt.strftime("%d %b %Y, %H:%M %Z"),
                )
        except Exception:
            pass

    # Fallback for signals > 60 days old (beyond 15m intraday retention): exchange close in UK time
    close_hm = (16, 30) if market == "LSE" else (16, 0)
    local_close = datetime(
        target_date.year, target_date.month, target_date.day,
        close_hm[0], close_hm[1], tzinfo=exch_tz
    )
    uk_close = local_close.astimezone(UK_TZ)
    return (
        uk_close.timestamp(),
        target_ts.strftime("%d %b %Y"),
        f"{target_ts.strftime('%d %b %Y')} ({uk_close.strftime('%H:%M %Z')} Close)",
    )


def fetch_portfolio_data() -> List[Dict[str, Any]]:
    """Fetches and computes full metrics for all 17 portfolio tickers, matching TradingView 1:1."""
    symbols = [t["symbol"] for t in PORTFOLIO_TICKERS]

    # Download 3y unadjusted daily batch data (split-adjusted, non-dividend-adjusted — matches TradingView charts
    # and provides full 200-SMA / 100-bar ATR regime warmup across the entire 2-Year signal log)
    batch = yf.download(symbols, period="3y", auto_adjust=False, group_by="ticker", threads=True, progress=False)

    # Download 60d 15m intraday batch data to pinpoint exact UK time of Ghost Cap / Confirmed Buy flashes
    intra_batch = None
    try:
        intra_batch = yf.download(symbols, period="60d", interval="15m", group_by="ticker", threads=True, progress=False)
    except Exception:
        intra_batch = None

    # Fetch quarterly earnings dates in parallel (cached 12h) for the Pre-Earnings Caution Guard
    with ThreadPoolExecutor(max_workers=8) as pool:
        er_raw_map = dict(pool.map(_fetch_cached_earnings, symbols))

    results = []

    for item in PORTFOLIO_TICKERS:
        sym = item["symbol"]
        try:
            if len(symbols) > 1 and sym in batch:
                df_raw = batch[sym]
            else:
                df_raw = yf.Ticker(sym).history(period="3y", auto_adjust=False)

            df_intra = None
            if intra_batch is not None:
                try:
                    if len(symbols) > 1 and sym in intra_batch:
                        df_intra = intra_batch[sym].dropna(how="all")
                    elif len(symbols) == 1:
                        df_intra = intra_batch.dropna(how="all")
                except Exception:
                    df_intra = None

            df = _patch_daily_with_intraday(df_raw, df_intra, item["market"])
            if df.empty or len(df) < 15:
                continue

            er_dates = _map_tv_earnings_bar_dates(er_raw_map.get(sym), df.index)
            df = compute_technical_indicators(df, er_bar_dates=er_dates)

            # Latest bar values
            last = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else last
            prev2 = df.iloc[-3] if len(df) > 2 else prev

            price = float(last["Close"])
            today_chg = ((price - float(prev["Close"])) / float(prev["Close"])) * 100.0
            yest_chg = ((float(prev["Close"]) - float(prev2["Close"])) / float(prev2["Close"])) * 100.0

            z_score = float(last["ZScore"]) if not np.isnan(last["ZScore"]) else 0.0
            rsi14 = float(last["RSI14"]) if not np.isnan(last["RSI14"]) else 50.0

            has50 = not np.isnan(last["SMA50"])
            has200 = not np.isnan(last["SMA200"])
            dist50 = float(last["Dist50"]) if has50 else 0.0
            dist200 = float(last["Dist200"]) if has200 else 0.0
            dist_ath = float(last["DistATH"]) if not np.isnan(last["DistATH"]) else 0.0

            # Continuous DCA score
            sz = f_score_z(z_score)
            sr = f_score_rsi(rsi14)
            ssma = f_score_sma(dist50, dist200, has50, has200)

            dca_score = round((sz * 0.40) + (sr * 0.30) + (ssma * 0.30), 1)
            dca_score = max(1.0, min(10.0, dca_score))

            # CVD Order Flow 4-state engine (1D Daily timeframe)
            rcvd = last["rCVD"]
            cvd_sig = last["CVDSig"]
            cvd_slope = last["CVDSlope"]
            net_delta = last["NetDelta"]
            above_sig = rcvd >= cvd_sig

            if above_sig:
                cvd_state = "BULLISH" if (cvd_slope > 0 and net_delta >= 0) else "WEAKENING"
            else:
                cvd_state = "RECOVERING" if (cvd_slope > 0 and net_delta > 0) else "BEARISH"

            # Institutional Volume State (Recency-aware window of 3 bars)
            recent_sells = df["InstSelling"].iloc[-3:].any()
            recent_buys = df["InstBuying"].iloc[-3:].any()

            if last["InstSelling"]:
                vol_state = "HEAVY SELLING"
            elif last["InstBuying"]:
                vol_state = "HEAVY BUYING"
            elif recent_sells:
                vol_state = "HEAVY SELLING"
            elif recent_buys:
                vol_state = "HEAVY BUYING"
            else:
                vol_state = "NORMAL"

            # Falling Knife Guard
            knife_active = (dca_score >= 8.0) and (vol_state == "HEAVY SELLING")

            # Status resolution (Strictly 1:1 with TradingView on the latest daily candle)
            conf_buy = bool(last["ConfBuy"])
            ghost_buy = bool(last["GhostBuy"])

            if conf_buy:
                status = "CONFIRMED BUY"
            elif ghost_buy:
                status = "GHOST CAP"
            elif knife_active:
                status = "SCALE IN (SELLING)"
            elif dca_score >= 8.0:
                status = "VALUE ZONE"
            elif dca_score >= 6.0:
                status = "FAIR VALUE"
            else:
                status = "WAIT"

            # Keep Tab 1 Ghost Cap recency within trailing 1Y, while storing full 2-Year signal log for Tab 2
            latest_bar_date = df.index[-1].date()
            one_year_cutoff = latest_bar_date - timedelta(days=365)
            two_year_cutoff = latest_bar_date - timedelta(days=731)
            df_1y = df[[ts.date() >= one_year_cutoff for ts in df.index]]
            df_2y = df[[ts.date() >= two_year_cutoff for ts in df.index]]

            ghost_rows = df_1y[df_1y["GhostBuy"]]
            if not ghost_rows.empty:
                last_gb_ts = ghost_rows.index[-1]
                _, last_ghost_short, last_ghost_full = _resolve_uk_signal_time(
                    df, df_intra, last_gb_ts, sig_type="GHOST", market=item["market"]
                )
                last_ghost_days_ago = (latest_bar_date - last_gb_ts.date()).days
            else:
                last_ghost_short = "—"
                last_ghost_full = "No Ghost Cap (1Y)"
                last_ghost_days_ago = 9999

            # Collect Confirmed Buy & Ghost Cap events across the 2Y window for the Optimised Trend Alert Log
            signal_events = []
            total_bars = len(df)
            sig_mask = df_2y["ConfBuy"] | df_2y["GhostBuy"]
            for sig_ts, srow in df_2y[sig_mask].iterrows():
                is_conf = bool(srow["ConfBuy"])
                stype = "CONFIRMED BUY" if is_conf else "GHOST CAP"
                s_mode = "CONFIRMED" if is_conf else "GHOST"
                sort_ep, uk_short, uk_full = _resolve_uk_signal_time(
                    df, df_intra, sig_ts, sig_type=s_mode, market=item["market"]
                )
                sig_px = float(srow["Close"])
                sig_z = float(srow["ZScore"]) if not np.isnan(srow["ZScore"]) else 0.0
                sig_rsi = float(srow["RSI14"]) if not np.isnan(srow["RSI14"]) else 50.0

                # Exact 3-Pillar DCA Score at the time the signal fired
                sig_has50 = not np.isnan(srow["SMA50"])
                sig_has200 = not np.isnan(srow["SMA200"])
                sig_d50 = float(srow["Dist50"]) if sig_has50 else 0.0
                sig_d200 = float(srow["Dist200"]) if sig_has200 else 0.0
                sig_dca = round(
                    (f_score_z(sig_z) * 0.40)
                    + (f_score_rsi(sig_rsi) * 0.30)
                    + (f_score_sma(sig_d50, sig_d200, sig_has50, sig_has200) * 0.30),
                    1,
                )
                sig_dca = max(1.0, min(10.0, sig_dca))

                bar_loc = df.index.get_loc(sig_ts)
                bars_ago = int((total_bars - 1) - bar_loc) if isinstance(bar_loc, int) else 9999
                cal_days_ago = int((latest_bar_date - sig_ts.date()).days)

                ret_pct = ((price - sig_px) / sig_px) * 100.0 if sig_px > 0 else 0.0
                if is_conf:
                    action_lbl = "PRIMARY BUY"
                    summary_msg = f"Confirmed reversal bounce ({sig_z:+.1f} SD | RSI {sig_rsi:.1f})"
                else:
                    action_lbl = "SCALE IN"
                    summary_msg = f"Pierced -2.2 Std. Dev. band ({sig_z:+.1f} SD | RSI {sig_rsi:.1f})"

                is_live_candle = bool(sig_ts == df.index[-1]) and _is_session_still_open(sig_ts, item["market"])

                signal_events.append({
                    "sort_ts": sort_ep,
                    "date_key": sig_ts.strftime("%Y-%m-%d"),
                    "timestamp_uk": uk_full,
                    "timestamp_short": uk_short,
                    "ticker": item["display"],
                    "name": item["name"],
                    "signal_type": stype,
                    "action": action_lbl,
                    "price": sig_px,
                    "current_price": price,
                    "return_pct": ret_pct,
                    "signal_dca": sig_dca,
                    "std_dev": sig_z,
                    "rsi": sig_rsi,
                    "trading_bars_ago": bars_ago,
                    "calendar_days_ago": cal_days_ago,
                    "timeframe": "1D",
                    "raw_message": summary_msg,
                    "is_active_bar": is_live_candle,
                })
                
            # DCA Strategy Banner Text (from Beginner's Guide v2.0)
            if knife_active:
                strategy_banner = "SCALE IN (SELLING)"
                tranche_mult = 1.0
            elif dca_score >= 9.0:
                strategy_banner = "MAX VALUE BUY"
                tranche_mult = 2.0
            elif dca_score >= 8.0:
                strategy_banner = "AGGRESSIVE BUY"
                tranche_mult = 1.5
            elif dca_score >= 6.0:
                strategy_banner = "STANDARD DCA"
                tranche_mult = 1.0
            elif dca_score >= 4.5:
                strategy_banner = "LIGHT NIBBLE"
                tranche_mult = 0.5
            else:
                strategy_banner = "HOLD / WAIT"
                tranche_mult = 0.0

            # Trend Direction
            if has50 and has200:
                if price > last["SMA50"] and price > last["SMA200"]:
                    trend_dir = "BULLISH"
                elif price < last["SMA50"] and price < last["SMA200"]:
                    trend_dir = "BEARISH"
                else:
                    trend_dir = "NEUTRAL"
            elif has50:
                trend_dir = "BULLISH" if price > last["SMA50"] else "BEARISH"
            else:
                trend_dir = "NEUTRAL"

            # Market Momentum (MACD histogram direction)
            hist_curr = last["MACD_Hist"]
            hist_prev = prev["MACD_Hist"]
            if hist_curr >= 0 and hist_curr > hist_prev:
                mkt_mom = "EXPANDING BULLISH"
            elif hist_curr >= 0 and hist_curr <= hist_prev:
                mkt_mom = "WEAKENING"
            elif hist_curr < 0 and hist_curr > hist_prev:
                mkt_mom = "RECOVERING"
            else:
                mkt_mom = "BEARISH"

            results.append({
                "symbol": sym,
                "display": item["display"],
                "name": item["name"],
                "market": item["market"],
                "currency": item["currency"],
                "price": price,
                "today_chg": today_chg,
                "yest_chg": yest_chg,
                "dca_score": dca_score,
                "z_score": z_score,
                "rsi": rsi14,
                "status": status,
                "strategy_banner": strategy_banner,
                "tranche_mult": tranche_mult,
                "cvd_state": cvd_state,
                "vol_state": vol_state,
                "trend_dir": trend_dir,
                "mkt_mom": mkt_mom,
                "dist50": dist50,
                "dist200": dist200,
                "dist_ath": dist_ath,
                "sma50": float(last["SMA50"]) if has50 else None,
                "sma200": float(last["SMA200"]) if has200 else None,
                "conf_lower": float(last["ConfLower"]) if has50 else None,
                "conf_upper": float(last["ConfUpper"]) if has50 else None,
                "conf_buy": conf_buy,
                "ghost_buy": ghost_buy,
                "knife_active": knife_active,
                "last_ghost_short": last_ghost_short,
                "last_ghost_full": last_ghost_full,
                "last_ghost_days_ago": last_ghost_days_ago,
                "signal_events": signal_events,
                "df": df  # Keep for plotting detailed charts
            })
        except Exception as e:
            print(f"Error computing {sym}: {e}")
            continue

    # Auto-sort descending by DCA Score (secondary tie-break: deeper negative Z-score)
    results.sort(key=lambda x: (x["dca_score"], -x["z_score"]), reverse=True)
    return results


def build_optimised_trend_signal_log(
    portfolio_data: List[Dict[str, Any]],
    webhook_alerts: Optional[List[Dict[str, Any]]] = None,
    ticker_filter: Optional[str] = None,
    signal_filter: str = "ALL",
    lookback_window: str = "7D",
    limit: int = 1000
) -> List[Dict[str, Any]]:
    """
    Combines automatically detected Confirmed Buy & Ghost Cap signals across all 17 stocks
    with any logged TradingView webhook alerts, filtered by Lookback Window ('7D', '1M',
    '3M', '1Y', '2Y'), Signal Type, and Ticker, formatted in UK Time and sorted newest-first.
    """
    combined: List[Dict[str, Any]] = []
    seen_keys = set()
    now_uk_date = datetime.now(UK_TZ).date()

    for item in portfolio_data:
        for ev in item.get("signal_events", []):
            key = (ev["ticker"], ev["date_key"], ev["signal_type"])
            seen_keys.add(key)
            combined.append(ev)

    # Also merge any custom incoming webhook alerts from SQLite
    if webhook_alerts:
        price_lookup = {x["display"]: x["price"] for x in portfolio_data}
        name_lookup = {x["display"]: x["name"] for x in portfolio_data}
        dca_lookup = {x["display"]: x["dca_score"] for x in portfolio_data}
        for wa in webhook_alerts:
            tkr = str(wa.get("ticker", "")).upper()
            stype = str(wa.get("signal_type", "ALERT")).upper()
            raw_ts = str(wa.get("timestamp", ""))
            try:
                dt_utc = datetime.strptime(raw_ts, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                dt_uk = dt_utc.astimezone(UK_TZ)
                date_key = dt_uk.strftime("%Y-%m-%d")
                uk_full = dt_uk.strftime("%d %b %Y, %H:%M %Z")
                sort_ep = dt_uk.timestamp()
                cal_days = max(0, (now_uk_date - dt_uk.date()).days)
            except Exception:
                date_key = raw_ts[:10]
                uk_full = raw_ts
                sort_ep = 0.0
                cal_days = 9999

            key = (tkr, date_key, stype)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            sig_px = float(wa["price"]) if wa.get("price") is not None else 0.0
            cur_px = price_lookup.get(tkr, sig_px)
            ret_pct = ((cur_px - sig_px) / sig_px) * 100.0 if sig_px > 0 and cur_px > 0 else 0.0
            combined.append({
                "sort_ts": sort_ep,
                "date_key": date_key,
                "timestamp_uk": uk_full,
                "timestamp_short": uk_full,
                "ticker": tkr,
                "name": name_lookup.get(tkr, tkr),
                "signal_type": stype,
                "action": str(wa.get("action", "BUY")).upper(),
                "price": sig_px,
                "current_price": cur_px,
                "return_pct": ret_pct,
                "signal_dca": dca_lookup.get(tkr),
                "std_dev": None,
                "rsi": None,
                "trading_bars_ago": None,
                "calendar_days_ago": cal_days,
                "timeframe": str(wa.get("timeframe", "1D")),
                "raw_message": str(wa.get("raw_message", "")),
                "is_active_bar": False,
            })

    # Filter by Lookback Window
    if lookback_window == "7D":
        combined = [
            x for x in combined
            if (x.get("trading_bars_ago") is not None and x["trading_bars_ago"] <= 6)
            or (x.get("trading_bars_ago") is None and x.get("calendar_days_ago", 9999) <= 10)
        ]
    elif lookback_window == "1M":
        combined = [x for x in combined if x.get("calendar_days_ago", 9999) <= 31]
    elif lookback_window == "3M":
        combined = [x for x in combined if x.get("calendar_days_ago", 9999) <= 92]
    elif lookback_window == "1Y":
        combined = [x for x in combined if x.get("calendar_days_ago", 9999) <= 365]
    elif lookback_window == "2Y":
        combined = [x for x in combined if x.get("calendar_days_ago", 9999) <= 731]

    if ticker_filter and ticker_filter != "ALL":
        combined = [x for x in combined if x["ticker"] == ticker_filter]

    if signal_filter == "CONFIRMED BUY":
        combined = [x for x in combined if x["signal_type"] == "CONFIRMED BUY"]
    elif signal_filter == "GHOST CAP":
        combined = [x for x in combined if x["signal_type"] == "GHOST CAP"]

    combined.sort(key=lambda x: (x["sort_ts"], 1 if x["signal_type"] == "CONFIRMED BUY" else 0), reverse=True)
    return combined[:limit]

def fetch_single_asset_detail(symbol: str, period: str = "1y", interval: str = "1d") -> Optional[Dict[str, Any]]:
    """Fetches high-detail data for a single asset, including analyst upside and full candle history."""
    try:
        ticker_obj = yf.Ticker(symbol)
        df = ticker_obj.history(period=period, interval=interval)
        if df.empty:
            return None
            
        df = compute_technical_indicators(df)
        
        # Attempt analyst consensus fetch
        analyst_target = None
        analyst_upside = None
        try:
            info = ticker_obj.info
            target = info.get("targetMedianPrice") or info.get("targetMeanPrice")
            if target and target > 0:
                analyst_target = float(target)
                current_p = float(df["Close"].iloc[-1])
                analyst_upside = ((analyst_target - current_p) / current_p) * 100.0
        except Exception:
            pass
            
        return {
            "df": df,
            "analyst_target": analyst_target,
            "analyst_upside": analyst_upside
        }
    except Exception as e:
        print(f"Error fetching detail for {symbol}: {e}")
        return None
