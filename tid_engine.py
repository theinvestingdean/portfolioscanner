"""
TID Quantitative Decision Support Engine
Translates exact Pine Script algorithms from:
- TID_IA13_Portfolio_Master_Scanner.pine
- TID_DCA_Efficiency_Dashboard_v2.0.pine
- IA_Optimized_Trend.pine
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Dict, List, Any, Optional, Tuple

UK_TZ = ZoneInfo("Europe/London")

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

def compute_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates all Pine indicators: RSI, SMAs, Z-Score, ATR, Envelope, CVD, Signals."""
    df = df.copy()
    c = df['Close']
    h = df['High']
    l = df['Low']
    o = df['Open']
    v = df['Volume']

    # 1. SMAs & Standard Deviation (confLen = 50)
    df['SMA50'] = c.rolling(50).mean()
    df['STDEV50'] = c.rolling(50).std(ddof=0)
    df['ZScore'] = (c - df['SMA50']) / df['STDEV50'].replace(0, np.nan)
    df['ZScoreLow'] = (l - df['SMA50']) / df['STDEV50'].replace(0, np.nan)
    df['SMA200'] = c.rolling(200).mean()
    
    # Envelope ±2.2 Sigma
    df['ConfLower'] = df['SMA50'] - (df['STDEV50'] * 2.2)
    df['ConfUpper'] = df['SMA50'] + (df['STDEV50'] * 2.2)

    # 2. RSI 14 & RSI Fast 5 (Wilder's Smoothing)
    delta = c.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    avg_gain14 = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss14 = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs14 = avg_gain14 / avg_loss14.replace(0, np.nan)
    df['RSI14'] = 100 - (100 / (1 + rs14))

    avg_gain5 = gain.ewm(alpha=1/5, min_periods=5, adjust=False).mean()
    avg_loss5 = loss.ewm(alpha=1/5, min_periods=5, adjust=False).mean()
    rs5 = avg_gain5 / avg_loss5.replace(0, np.nan)
    df['RSIFast'] = 100 - (100 / (1 + rs5))

    # 3. True Range & ATR 14
    prev_close = c.shift(1)
    tr1 = h - l
    tr2 = (h - prev_close).abs()
    tr3 = (l - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['ATR14'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()

    # 4. Adaptive Trend Baseline (EMA 10 & EMA 16)
    df['FastEMA'] = c.ewm(span=10, adjust=False).mean()
    df['SlowEMA'] = c.ewm(span=16, adjust=False).mean()
    df['IsBull'] = df['FastEMA'] > df['SlowEMA']
    df['RibbonSlope'] = (df['SlowEMA'] - df['SlowEMA'].shift(3)) / df['ATR14'].replace(0, 1.0)

    # 5. Distances
    df['Dist50'] = ((c - df['SMA50']) / df['SMA50']) * 100.0
    df['Dist200'] = ((c - df['SMA200']) / df['SMA200']) * 100.0
    df['ATH'] = h.cummax()
    df['DistATH'] = ((c - df['ATH']) / df['ATH']) * 100.0

    # 6. MACD (12, 26, 9)
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = macd_line - signal_line

    # 7. Smart Order Flow (CVD) & Institutional Volume
    range_hl = (h - l).replace(0, 1.0)
    df['BuyVol'] = v * ((c - l) / range_hl)
    df['SellVol'] = v * ((h - c) / range_hl)
    df['NetDelta'] = df['BuyVol'] - df['SellVol']
    df['rCVD'] = df['NetDelta'].rolling(30).sum()
    df['CVDSig'] = df['rCVD'].rolling(14).mean()
    df['CVDSlope'] = df['rCVD'].diff()
    df['AvgVol'] = v.rolling(20).mean()

    # Institutional Volume Spikes (Daily = 1.5x)
    df['InstSpike'] = v > (df['AvgVol'] * 1.5)
    df['InstBuying'] = (df['NetDelta'] >= 0) & df['InstSpike'] & (df['rCVD'] > df['CVDSig'])
    df['InstSelling'] = (df['NetDelta'] < 0) & df['InstSpike'] & (df['rCVD'] < df['CVDSig'])

    # 8. Ghost Capitulation & Confirmed Bottom Signals
    # Pierced lower envelope within 6 bars or Z <= -2.2*0.88
    minZ6 = df['ZScoreLow'].rolling(6).min()
    minRsi6 = df['RSI14'].rolling(6).min()
    lowestLow6 = l.rolling(6).min()
    confLowerDist6 = (l - df['ConfLower']).rolling(6).min()
    
    piercedLower = (confLowerDist6 <= (df['ATR14'] * 0.20)) | (minZ6 <= -2.2 * 0.88)
    
    # Raw Ghost:
    lowerWick = (c - l) / range_hl
    rawGhost = ((l <= df['ConfLower']) | (df['ZScoreLow'] <= -2.2 * 0.88)) & \
               ((df['RSI14'] <= 42.0) | (df['RSIFast'] <= 30.0)) & \
               ((c <= o) | (lowerWick >= 0.45))
    df['GhostBuy'] = rawGhost

    # Confirmed Bottom Reversal Buy:
    bullPA = ((c > o) & (c > prev_close)) | ((lowerWick >= 0.55) & (c > prev_close))
    bullMom = (df['ZScore'].diff() > 0) & (df['RSIFast'] > df['RSIFast'].shift(1))
    trendOk = df['IsBull'] | (df['RibbonSlope'] > -0.35) | (lowestLow6 <= (df['ConfLower'] + df['ATR14'] * 0.05)) | (minZ6 <= -2.0)
    df['ConfBuy'] = piercedLower & ((minRsi6 <= 42.0) | (minZ6 <= -2.1)) & bullPA & bullMom & trendOk

    return df


NY_TZ = ZoneInfo("America/New_York")


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

                    c_hist = df_daily["Close"].iloc[:loc]
                    delta = c_hist.diff()
                    g = delta.clip(lower=0)
                    ls = -delta.clip(upper=0)
                    ag14_prev = float(g.ewm(alpha=1/14, min_periods=14, adjust=False).mean().iloc[-1])
                    al14_prev = float(ls.ewm(alpha=1/14, min_periods=14, adjust=False).mean().iloc[-1])
                    ag5_prev = float(g.ewm(alpha=1/5, min_periods=5, adjust=False).mean().iloc[-1])
                    al5_prev = float(ls.ewm(alpha=1/5, min_periods=5, adjust=False).mean().iloc[-1])

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
                            conf_lower = sma50 - 2.2 * std50
                            z_low = (run_l - sma50) / std50

                            chg = bc - prev_c
                            gn = max(chg, 0.0)
                            lo = max(-chg, 0.0)
                            ag14 = (ag14_prev * 13.0 + gn) / 14.0
                            al14 = (al14_prev * 13.0 + lo) / 14.0
                            rsi14 = 100.0 if al14 == 0 else (100.0 - 100.0 / (1.0 + ag14 / al14))

                            ag5 = (ag5_prev * 4.0 + gn) / 5.0
                            al5 = (al5_prev * 4.0 + lo) / 5.0
                            rsi5 = 100.0 if al5 == 0 else (100.0 - 100.0 / (1.0 + ag5 / al5))

                            rng = max(run_h - run_l, 1e-6)
                            lower_wick = (bc - run_l) / rng

                            if (run_l <= conf_lower or z_low <= -2.2 * 0.88) and (rsi14 <= 42.0 or rsi5 <= 30.0) and (bc <= open_d or lower_wick >= 0.45):
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
    """Fetches and computes full metrics for all 17 portfolio tickers, including UK signal timestamps."""
    symbols = [t["symbol"] for t in PORTFOLIO_TICKERS]
    
    # Download 1y daily batch data
    batch = yf.download(symbols, period="1y", group_by="ticker", threads=True, progress=False)

    # Download 60d 15m intraday batch data to pinpoint exact UK time of Ghost Cap / Confirmed Buy flashes
    intra_batch = None
    try:
        intra_batch = yf.download(symbols, period="60d", interval="15m", group_by="ticker", threads=True, progress=False)
    except Exception:
        intra_batch = None
    
    results = []
    
    for item in PORTFOLIO_TICKERS:
        sym = item["symbol"]
        try:
            if len(symbols) > 1 and sym in batch:
                df = batch[sym].dropna(how="all")
            else:
                df = yf.Ticker(sym).history(period="1y")
            
            if df.empty or len(df) < 15:
                continue

            df_intra = None
            if intra_batch is not None:
                try:
                    if len(symbols) > 1 and sym in intra_batch:
                        df_intra = intra_batch[sym].dropna(how="all")
                    elif len(symbols) == 1:
                        df_intra = intra_batch.dropna(how="all")
                except Exception:
                    df_intra = None
                
            df = compute_technical_indicators(df)
            
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
            
            # Status resolution (Strictly 1:1 with TradingView scanner on the active candle)
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

            # Resolve latest Ghost Cap flash date & UK time, plus historical signal events
            ghost_rows = df[df["GhostBuy"]]
            if not ghost_rows.empty:
                last_gb_ts = ghost_rows.index[-1]
                _, last_ghost_short, last_ghost_full = _resolve_uk_signal_time(
                    df, df_intra, last_gb_ts, sig_type="GHOST", market=item["market"]
                )
                last_ghost_days_ago = (df.index[-1].date() - last_gb_ts.date()).days
            else:
                last_ghost_short = "—"
                last_ghost_full = "No Ghost Cap (1Y)"
                last_ghost_days_ago = 9999

            # Collect Confirmed Buy & Ghost Cap events across the 1Y window for the Optimised Trend Alert Log
            signal_events = []
            sig_mask = df["ConfBuy"] | df["GhostBuy"]
            for sig_ts, srow in df[sig_mask].iterrows():
                is_conf = bool(srow["ConfBuy"])
                stype = "CONFIRMED BUY" if is_conf else "GHOST CAP"
                s_mode = "CONFIRMED" if is_conf else "GHOST"
                sort_ep, uk_short, uk_full = _resolve_uk_signal_time(
                    df, df_intra, sig_ts, sig_type=s_mode, market=item["market"]
                )
                sig_px = float(srow["Close"])
                sig_z = float(srow["ZScore"]) if not np.isnan(srow["ZScore"]) else 0.0
                sig_rsi = float(srow["RSI14"]) if not np.isnan(srow["RSI14"]) else 50.0
                ret_pct = ((price - sig_px) / sig_px) * 100.0 if sig_px > 0 else 0.0
                if is_conf:
                    action_lbl = "PRIMARY BUY"
                    summary_msg = f"Confirmed reversal bounce ({sig_z:+.1f} SD | RSI {sig_rsi:.1f})"
                else:
                    action_lbl = "SCALE IN"
                    summary_msg = f"Pierced -2.2 Std. Dev. band ({sig_z:+.1f} SD | RSI {sig_rsi:.1f})"

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
                    "std_dev": sig_z,
                    "rsi": sig_rsi,
                    "timeframe": "1D",
                    "raw_message": summary_msg,
                    "is_active_bar": bool(sig_ts == df.index[-1]),
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
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Combines automatically detected Confirmed Buy & Ghost Cap signals across all 17 stocks
    with any logged TradingView webhook alerts, formatted in UK Time (Europe/London)
    and sorted newest-first.
    """
    combined: List[Dict[str, Any]] = []
    seen_keys = set()

    for item in portfolio_data:
        for ev in item.get("signal_events", []):
            key = (ev["ticker"], ev["date_key"], ev["signal_type"])
            seen_keys.add(key)
            combined.append(ev)

    # Also merge any custom incoming webhook alerts from SQLite
    if webhook_alerts:
        price_lookup = {x["display"]: x["price"] for x in portfolio_data}
        name_lookup = {x["display"]: x["name"] for x in portfolio_data}
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
            except Exception:
                date_key = raw_ts[:10]
                uk_full = raw_ts
                sort_ep = 0.0

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
                "std_dev": None,
                "rsi": None,
                "timeframe": str(wa.get("timeframe", "1D")),
                "raw_message": str(wa.get("raw_message", "")),
                "is_active_bar": False,
            })

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
