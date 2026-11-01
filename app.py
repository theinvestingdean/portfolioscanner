"""
TID Portfolio Web & Mobile Dashboard
================================================================================
Institutional Quantitative Decision Support Terminal
Branded in The Investing Dean (TID) Heat Map aesthetic.

1. Signature Pill Navigation Switcher (100% Bright White Inactive, Solid Brand Yellow Active)
2. 17-Stock Master Portfolio Scanner (Auto-sorted by DCA Score + 1D Today/Yest + CVD Flow)
3. Interactive Clickable Category Filters (Click any summary metric to filter the table!)
4. Tactical Action Guide with forced 1-line exact fit
5. Full DCA Efficiency Dashboard v2.0 (High-Contrast Macro Valuation + Execution Engine)
6. TID - Optimised Trend Live Webhook Alert Stream & Signal Log
7. Mobile Touch Card Interface
================================================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import time

from tid_engine import (
    PORTFOLIO_TICKERS, 
    fetch_portfolio_data, 
    fetch_single_asset_detail
)
from db import (
    log_alert, 
    get_recent_alerts, 
    clear_alerts
)
from webhook_receiver import start_webhook_server

# 1. Page Configuration
st.set_page_config(
    page_title="The Investing Dean | Portfolio Scanner & DCA Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Start background webhook server on port 8000
@st.cache_resource
def ensure_webhook_server_running(port: int = 8000):
    return start_webhook_server(port=port)

webhook_running, webhook_msg = ensure_webhook_server_running(port=8000)

# Initialize Session State Filter
if "filter_status" not in st.session_state:
    st.session_state.filter_status = "ALL"

# ============================================================================
# 2. BRANDING & HIGH-CONTRAST INSTITUTIONAL CSS (THE INVESTING DEAN HEAT MAP STYLE)
# ============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Roboto+Condensed:wght@600;700;800&display=swap');

    /* Global Root Background - Deep Matte Black (#080808) */
    html, body, .stApp {
        background-color: #080808 !important;
        color: #FFFFFF !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }

    /* Streamlit block container max width & generous breathing room */
    .block-container,
    div[data-testid="stAppViewBlockContainer"],
    section.main > div.block-container {
        max-width: 1760px !important;
        width: 100% !important;
        padding-top: 1.5rem !important;
        padding-bottom: 3rem !important;
        padding-left: 24px !important;
        padding-right: 24px !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }

    /* Main Branding Header (The Investing Dean Heat Map) */
    .main-title {
        margin: 10px 0 0 0 !important;
        font-size: 2.3rem !important;
        font-weight: 800 !important;
        color: #FFFFFF !important;
        letter-spacing: -0.5px !important;
        line-height: 1.15 !important;
        text-align: center;
    }
    .title-line-1 {
        color: #FFFFFF;
    }
    .title-line-2 {
        color: #FACC15; /* Bright Gold Accent */
        margin-left: 0.25em;
    }
    .main-subtitle {
        margin: 6px 0 16px 0 !important;
        color: #A1A1AA !important;
        font-size: 0.82rem !important;
        letter-spacing: 2px !important;
        font-weight: 600 !important;
        line-height: 1.35 !important;
        text-align: center;
    }
    .sub-line-1 {
        color: #A1A1AA;
    }
    .sub-line-2 {
        color: #FACC15;
        font-weight: 700;
        margin-left: 0.25em;
    }

    /* Sub-Bar Badges */
    .sub-bar-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 12px;
        background: #121214;
        border: 1px solid #27272A;
        border-radius: 8px;
        padding: 10px 18px;
        margin-bottom: 22px;
    }
    .badge-yellow {
        background-color: #FACC15;
        color: #000000;
        font-weight: 800;
        font-size: 0.74rem;
        padding: 4px 9px;
        border-radius: 4px;
        letter-spacing: 0.5px;
        display: inline-block;
    }
    .badge-dark-pill {
        background-color: #18181B;
        border: 1px solid #27272A;
        color: #FFFFFF;
        font-weight: 700;
        font-size: 0.78rem;
        padding: 4px 12px;
        border-radius: 4px;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }

    /* =========================================================
       SIGNATURE THE INVESTING DEAN NAVIGATION BAR (PILL SWITCHER)
       Replaces problematic st.tabs with 100% reliable styled pills!
       Inactive: Solid Dark Pill, Bright White (#FFFFFF) Bold Text
       Active: Solid Signature Yellow (#FACC15), Bold Black Text
       ========================================================= */
    div[data-testid="stRadio"],
    div.stRadio {
        width: 100% !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        margin-left: auto !important;
        margin-right: auto !important;
        text-align: center !important;
        margin-bottom: 20px !important;
    }
    div[data-testid="stRadio"] > label,
    div[data-testid="stRadio"] [data-testid="stWidgetLabel"] {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    div[data-testid="stRadioGroup"],
    div[data-testid="stRadio"] > div[role="radiogroup"],
    div.stRadio > div[role="radiogroup"] {
        display: flex !important;
        flex-direction: row !important;
        justify-content: center !important;
        align-items: center !important;
        gap: 8px !important;
        background-color: #121214 !important;
        padding: 6px 8px !important;
        border-radius: 8px !important;
        border: 1px solid #26262B !important;
        width: 100% !important;
        max-width: 980px !important;
        margin: 0 auto !important;
        box-sizing: border-box !important;
    }
    div[data-testid="stRadioGroup"] > div {
        flex: 1 1 0 !important;
        display: flex !important;
        justify-content: center !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    /* Inactive State - Bright Crisp White Text on Dark Pill */
    div[data-testid="stRadioOption"],
    div[data-testid="stRadioGroup"] label {
        background-color: #18181B !important;
        border: 1.5px solid #2E2E34 !important;
        border-radius: 6px !important;
        padding: 10px 14px !important;
        margin: 0 !important;
        cursor: pointer !important;
        transition: all 0.2s ease-in-out !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        width: 100% !important;
        box-sizing: border-box !important;
    }
    div[data-testid="stRadioOption"]:hover,
    div[data-testid="stRadioGroup"] label:hover {
        border-color: #FACC15 !important;
    }
    div[data-testid="stRadioOption"] [data-testid="stMarkdownContainer"],
    div[data-testid="stRadioOption"] p,
    div[data-testid="stRadioGroup"] label p {
        color: #FFFFFF !important; /* PURE CRISP WHITE TEXT */
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        white-space: nowrap !important;
        text-align: center !important;
        margin: 0 !important;
        padding: 0 !important;
        opacity: 1 !important;
        -webkit-text-fill-color: #FFFFFF !important;
    }
    /* Hide Radio Circles & Markings */
    div[data-testid="stRadioOption"] input[type="radio"],
    div[data-testid="stRadioOption"] svg,
    div[data-testid="stRadio"] [aria-hidden="true"],
    div[data-testid="stRadio"] input[type="radio"] + div {
        display: none !important;
        width: 0 !important;
        height: 0 !important;
        visibility: hidden !important;
    }
    /* Active State - Solid Signature Yellow with Bold Black Text */
    div[data-testid="stRadioGroup"] > div:has(input:checked) [data-testid="stRadioOption"],
    div[data-testid="stRadioOption"]:has(input:checked),
    div[data-testid="stRadioGroup"] label:has(input:checked) {
        background-color: #FACC15 !important;
        background: #FACC15 !important;
        border-color: #EAB308 !important;
        box-shadow: 0 0 14px rgba(250, 204, 21, 0.45) !important;
    }
    div[data-testid="stRadioGroup"] > div:has(input:checked) [data-testid="stRadioOption"] p,
    div[data-testid="stRadioOption"]:has(input:checked) p,
    div[data-testid="stRadioGroup"] label:has(input:checked) p {
        color: #000000 !important; /* BOLD BLACK TEXT ON YELLOW */
        font-weight: 900 !important;
        font-size: 0.95rem !important;
        -webkit-text-fill-color: #000000 !important;
    }

    /* =========================================================================
       NATIVE ACTION BUTTONS - Solid Branded Yellow (#FACC15) with Black Bold Text
       ========================================================================= */
    .stButton button,
    div[data-testid="stButton"] button {
        background-color: #FACC15 !important;
        color: #000000 !important;
        border: 1px solid #EAB308 !important;
        border-radius: 6px !important;
        font-weight: 800 !important;
        font-size: 0.92rem !important;
        padding: 8px 18px !important;
        transition: all 0.2s ease !important;
        cursor: pointer !important;
    }
    .stButton button:hover,
    div[data-testid="stButton"] button:hover {
        background-color: #EAB308 !important;
        color: #000000 !important;
        box-shadow: 0 0 12px rgba(250, 204, 21, 0.45) !important;
        border-color: #FACC15 !important;
    }

    /* High-Contrast Selectbox & Inputs (Fixes Grey on Black) */
    div[data-baseweb="select"] > div,
    div[data-baseweb="select"] * {
        background-color: #18181B !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        border-color: #3F3F46 !important;
    }
    div[data-baseweb="popover"],
    div[data-baseweb="menu"],
    ul[role="listbox"],
    li[role="option"] {
        background-color: #18181B !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        border: 1px solid #3F3F46 !important;
    }
    li[role="option"]:hover,
    li[aria-selected="true"] {
        background-color: #FACC15 !important;
        color: #000000 !important;
    }
    label[data-testid="stWidgetLabel"] p {
        color: #FFFFFF !important;
        font-weight: 700 !important;
        font-size: 0.98rem !important;
    }

    /* =========================================================================
       MASTER WATCHLIST TABLE - HIGH-CONTRAST BORDERS BETWEEN EVERY CELL
       ========================================================================= */
    .tid-table-wrapper {
        width: 100%;
        overflow-x: auto;
        border: 2px solid #4B5563 !important;
        border-radius: 8px;
        background-color: #101012;
        margin-bottom: 20px;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.4);
    }
    .tid-table {
        width: 100%;
        border-collapse: collapse !important;
        font-family: 'Inter', sans-serif;
        font-size: 13.5px;
        color: #FFFFFF;
    }
    .tid-table th {
        background-color: #1F1F24 !important;
        color: #FACC15 !important; /* Gold header text */
        font-weight: 800;
        font-size: 12.5px;
        letter-spacing: 0.8px;
        padding: 13px 16px;
        border: 1.5px solid #4B5563 !important; /* High-contrast cell border */
        border-bottom: 2.5px solid #FACC15 !important;
        text-align: left;
        white-space: nowrap;
    }
    .tid-table td {
        padding: 12px 16px;
        border: 1.5px solid #4B5563 !important; /* High-contrast cell border between every row & column */
        white-space: nowrap;
        font-weight: 600;
    }
    /* Alternating High-Contrast Zebra Striping for Easy Row-by-Row Tracking */
    .tid-table tr:nth-child(even) td {
        background-color: #0E0E11 !important;
    }
    .tid-table tr:nth-child(odd) td {
        background-color: #18181D !important;
    }
    .tid-table tr:hover td {
        background-color: #272730 !important; /* Row hover highlight */
    }

    /* Status Badges */
    .badge-confirmed {
        background-color: #00E676;
        color: #000000;
        font-weight: 900;
        padding: 5px 12px;
        border-radius: 4px;
        font-size: 11.5px;
        letter-spacing: 0.5px;
        display: inline-block;
        white-space: nowrap;
    }
    .badge-ghost {
        background-color: #FF8C00;
        color: #000000;
        font-weight: 900;
        padding: 5px 12px;
        border-radius: 4px;
        font-size: 11.5px;
        display: inline-block;
        white-space: nowrap;
    }
    .badge-knife {
        background-color: #FFB300;
        color: #000000;
        font-weight: 900;
        padding: 5px 12px;
        border-radius: 4px;
        font-size: 11.5px;
        display: inline-block;
        white-space: nowrap;
    }
    .badge-value {
        background-color: #2ea043;
        color: #FFFFFF;
        font-weight: 800;
        padding: 5px 12px;
        border-radius: 4px;
        font-size: 11.5px;
        display: inline-block;
        white-space: nowrap;
    }
    .badge-fair {
        background-color: #27272A;
        color: #E4E4E7;
        border: 1px solid #3F3F46;
        font-weight: 700;
        padding: 5px 12px;
        border-radius: 4px;
        font-size: 11.5px;
        display: inline-block;
        white-space: nowrap;
    }
    .badge-wait {
        background-color: #E53935;
        color: #FFFFFF;
        font-weight: 800;
        padding: 5px 12px;
        border-radius: 4px;
        font-size: 11.5px;
        display: inline-block;
        white-space: nowrap;
    }

    /* CVD Badges */
    .cvd-bullish {
        background-color: rgba(0, 230, 118, 0.16);
        color: #00E676;
        border: 1px solid #00E676;
        font-weight: 800;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 11.5px;
        white-space: nowrap;
    }
    .cvd-weakening {
        background-color: rgba(255, 140, 0, 0.16);
        color: #FF8C00;
        border: 1px solid #FF8C00;
        font-weight: 800;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 11.5px;
        white-space: nowrap;
    }
    .cvd-recovering {
        background-color: rgba(255, 140, 0, 0.16);
        color: #FF8C00;
        border: 1px solid #FF8C00;
        font-weight: 800;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 11.5px;
        white-space: nowrap;
    }
    .cvd-bearish {
        background-color: rgba(229, 57, 53, 0.16);
        color: #FF5252;
        border: 1px solid #FF5252;
        font-weight: 800;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 11.5px;
        white-space: nowrap;
    }

    /* Score Badges - Master DCA Efficiency Dashboard Colors */
    .dca-pill-10 { background-color: #00E676; color: #000; font-weight: 900; padding: 4px 10px; border-radius: 4px; font-size: 13px; }
    .dca-pill-8  { background-color: #00E676; color: #000; font-weight: 900; padding: 4px 10px; border-radius: 4px; font-size: 13px; }
    .dca-pill-6  { background-color: #9AE63C; color: #000; font-weight: 900; padding: 4px 10px; border-radius: 4px; font-size: 13px; }
    .dca-pill-4  { background-color: #FACC15; color: #000; font-weight: 900; padding: 4px 10px; border-radius: 4px; font-size: 13px; }
    .dca-pill-low{ background-color: #E53935; color: #fff; font-weight: 900; padding: 4px 10px; border-radius: 4px; font-size: 13px; }

    /* Summary & Action Cards */
    .tid-card {
        background-color: #121214;
        border: 1.5px solid #27272A;
        border-radius: 8px;
        padding: 16px 18px;
        margin-bottom: 20px;
    }
    .tid-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background-color: #18181B;
        padding: 11px 14px;
        border-radius: 6px;
        font-weight: 800;
        font-size: 12.5px;
        color: #FACC15;
        margin-bottom: 14px;
        border: 1px solid #27272A;
    }

    /* =========================================================================
       TACTICAL ACTION GUIDE - FORCED EXACT 1-LINE FIT (NO WRAPPING)
       ========================================================================= */
    .guide-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 12px;
        border-bottom: 1px solid #1E1E22;
        white-space: nowrap !important;
        gap: 14px;
    }
    .guide-text {
        font-size: 12.5px;
        color: #E4E4E7;
        white-space: nowrap !important;
        text-align: right;
        overflow: visible;
        font-weight: 500;
    }

    /* High-Contrast Large Deep-Dive Cards */
    .deepdive-panel {
        background-color: #121214;
        border: 1.5px solid #27272A;
        border-radius: 8px;
        padding: 22px 24px;
        margin-bottom: 24px;
    }
    .deepdive-header {
        font-size: 14.5px;
        font-weight: 800;
        color: #FACC15;
        letter-spacing: 0.8px;
        border-bottom: 2px solid #27272A;
        padding-bottom: 12px;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .metric-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 10px;
        border-bottom: 1px solid #1E1E22;
        font-size: 14.5px;
    }
    .metric-row:last-child {
        border-bottom: none;
    }
    .metric-lbl {
        color: #FFFFFF !important;
        font-weight: 600;
    }
    .metric-val-bold {
        font-size: 15.5px;
        font-weight: 800;
        color: #FFFFFF;
        text-align: right;
    }

    /* Big HUD Banner */
    .hud-banner-box {
        border-radius: 8px;
        padding: 22px 30px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 24px;
        border: 1px solid rgba(255,255,255,0.12);
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# 3. HEADER & SUB-BAR (THE INVESTING DEAN BRANDING)
# ============================================================================
st.markdown("""
<div style="text-align: center; margin-bottom: 18px;">
    <h1 class="main-title">
        <span class="title-line-1">The Investing Dean</span>
        <span class="title-line-2">Portfolio Dashboard</span>
    </h1>
    <p class="main-subtitle">
        <span class="sub-line-1">REAL-TIME QUANTITATIVE</span>
        <span class="sub-line-2">DECISION SUPPORT & DCA ENGINE</span>
    </p>
</div>
""", unsafe_allow_html=True)


# ============================================================================
# 4. 3-MINUTE AUTO-REFRESH LIVE FRAGMENT (Streamlit Native WebSocket Polling)
# ============================================================================
@st.fragment(run_every='180s')
def render_live_dashboard():
    now_str = datetime.utcnow().strftime("%b %d, %H:%M:%S UTC")
    st_col1, st_col2 = st.columns([3, 2])

    with st_col1:
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
            <span class="badge-yellow">EQUITIES & STOCKS</span>
            <span class="badge-dark-pill">17 ASSETS</span>
            <span class="badge-yellow">SNAPSHOT</span>
            <span class="badge-dark-pill">{now_str} (Live Sync)</span>
        </div>
        """, unsafe_allow_html=True)

    with st_col2:
        st.markdown(f"""
        <div style="display: flex; justify-content: flex-end; align-items: center; gap: 8px; flex-wrap: wrap;">
            <span class="badge-dark-pill" style="border-color: #00E676; color: #00E676;">
                <span style="font-size: 13px;">\u25cf</span> Auto-Refresh: 3 Min (Active)
            </span>
            <span class="badge-dark-pill" style="border-color: #00E676;">
                <span style="color: #00E676; font-size: 13px;">\u25cf</span> Webhook: Port 8000 (Active)
            </span>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    # Load portfolio data with caching
    @st.cache_data(ttl=180)
    def load_all_portfolio():
        return fetch_portfolio_data()

    with st.spinner("Fetching live market data and calculating quantitative scores..."):
        portfolio_data = load_all_portfolio()

    # Compute summary stats
    cnt_conf = sum(1 for x in portfolio_data if x["status"] == "CONFIRMED BUY")
    cnt_ghost = sum(1 for x in portfolio_data if x["status"] == "GHOST CAP")
    cnt_val = sum(1 for x in portfolio_data if x["status"] == "VALUE ZONE")
    cnt_fair = sum(1 for x in portfolio_data if x["status"] == "FAIR VALUE")
    cnt_wait = sum(1 for x in portfolio_data if x["status"] == "WAIT")
    cnt_knife = sum(1 for x in portfolio_data if x["status"] == "SCALE IN (SELLING)")

    # ============================================================================
    # 4. SIGNATURE HEAT MAP PILL NAVIGATION SWITCHER
    # (Guarantees 100% Crisp White Inactive Text & Solid Gold Active Highlight)
    # ============================================================================
    TAB_OPTIONS = [
        "📊 17-Stock Master Scanner", 
        "🎯 DCA Efficiency Dashboard v2.0", 
        "🔔 Optimised Trend Alert Log", 
        "📱 Mobile View"
    ]

    active_tab = st.radio(
        "Navigation",
        options=TAB_OPTIONS,
        horizontal=True,
        label_visibility="collapsed",
        key="nav_tab_radio"
    )

    # ============================================================================
    # VIEW 1: 17-STOCK MASTER SCANNER
    # ============================================================================
    if active_tab == "📊 17-Stock Master Scanner":
        col_main, col_side = st.columns([6.4, 3.6])

        with col_main:
            active_filter = st.session_state.filter_status
            if active_filter != "ALL":
                display_data = [x for x in portfolio_data if x["status"] == active_filter]
            else:
                display_data = portfolio_data

            # Filter Banner Header
            if active_filter != "ALL":
                c_f_info, c_f_btn = st.columns([4, 1.5])
                with c_f_info:
                    st.markdown(f"""
                    <div style="background-color: #18181B; border: 1.5px solid #FACC15; border-radius: 6px; padding: 10px 16px; margin-bottom: 12px; display: flex; align-items: center; gap: 12px;">
                        <span style="background-color: #FACC15; color: #000; font-weight: 900; font-size: 11px; padding: 3px 8px; border-radius: 4px;">ACTIVE FILTER</span>
                        <span style="color: #FFFFFF; font-weight: 800; font-size: 14px;">Showing {len(display_data)} Stocks matching: <strong>{active_filter}</strong></span>
                    </div>
                    """, unsafe_allow_html=True)
                with c_f_btn:
                    if st.button("✕ Show All 17", key="btn_clear_filter", use_container_width=True):
                        st.session_state.filter_status = "ALL"
                        st.rerun()
            else:
                st.markdown("<h4 style='margin-bottom: 14px; color: #FFFFFF; font-weight: 800; font-size: 1.2rem;'>Portfolio Watchlist (Auto-Sorted by Highest DCA Score)</h4>", unsafe_allow_html=True)

            # Build clean, zero-indent HTML table rows with cell borders & zebra striping
            rows = []
            for item in display_data:
                sc = item["dca_score"]
                sc_cls = "dca-pill-8" if sc >= 8.0 else ("dca-pill-6" if sc >= 6.0 else ("dca-pill-4" if sc >= 4.5 else "dca-pill-low"))

                td_col = "#00E676" if item["today_chg"] > 0 else ("#FF5252" if item["today_chg"] < 0 else "#FFFFFF")
                ys_col = "#00E676" if item["yest_chg"] > 0 else ("#FF5252" if item["yest_chg"] < 0 else "#FFFFFF")
                td_str = f"{item['today_chg']:+.1f}%"
                ys_str = f"{item['yest_chg']:+.1f}%"

                st_text = item["status"]
                if st_text == "CONFIRMED BUY":
                    st_badge = f'<span class="badge-confirmed">{st_text}</span>'
                elif st_text == "GHOST CAP":
                    st_badge = f'<span class="badge-ghost">{st_text}</span>'
                elif st_text == "SCALE IN (SELLING)":
                    st_badge = f'<span class="badge-knife">{st_text}</span>'
                elif st_text == "VALUE ZONE":
                    st_badge = f'<span class="badge-value">{st_text}</span>'
                elif st_text == "FAIR VALUE":
                    st_badge = f'<span class="badge-fair">{st_text}</span>'
                else:
                    st_badge = f'<span class="badge-wait">{st_text}</span>'

                cvd = item["cvd_state"]
                cvd_badge = f'<span class="cvd-{cvd.lower()}">{cvd}</span>'

                z_val = item["z_score"]
                z_col = "#00E676" if z_val <= -1.2 else ("#FF5252" if z_val >= 1.2 else "#FFFFFF")
                z_str = f"{z_val:+.1f} SD"

                rsi_val = item["rsi"]
                rsi_col = "#00E676" if rsi_val <= 30 else ("#9ae63c" if rsi_val <= 40 else ("#FF5252" if rsi_val >= 70 else "#FFFFFF"))

                p_str = f"${item['price']:,.2f}" if item['price'] >= 100 else f"${item['price']:.2f}"

                row_html = (
                    f'<tr>'
                    f'<td style="font-weight: 800; color: #FFFFFF; font-size: 14.5px;">{item["display"]}</td>'
                    f'<td style="font-weight: 700; color: #FFFFFF;">{p_str}</td>'
                    f'<td style="font-weight: 800; color: {td_col};">{td_str}</td>'
                    f'<td style="font-weight: 800; color: {ys_col};">{ys_str}</td>'
                    f'<td style="text-align: center;"><span class="{sc_cls}">{sc:.1f}</span></td>'
                    f'<td style="font-weight: 700; color: {z_col};">{z_str}</td>'
                    f'<td style="font-weight: 700; color: {rsi_col};">{rsi_val:.1f}</td>'
                    f'<td>{cvd_badge}</td>'
                    f'<td style="text-align: center;">{st_badge}</td>'
                    f'</tr>'
                )
                rows.append(row_html)

            body_html = "".join(rows)
            full_table_html = (
                f'<div class="tid-table-wrapper">'
                f'<table class="tid-table">'
                f'<thead>'
                f'<tr>'
                f'<th>TICKER</th>'
                f'<th>PRICE</th>'
                f'<th>TODAY 1D</th>'
                f'<th>YEST 1D</th>'
                f'<th style="text-align: center;">DCA</th>'
                f'<th>Z-SCORE</th>'
                f'<th>RSI</th>'
                f'<th>CVD ORDER FLOW</th>'
                f'<th style="text-align: center;">STATUS</th>'
                f'</tr>'
                f'</thead>'
                f'<tbody>{body_html}</tbody>'
                f'</table>'
                f'</div>'
            )

            st.markdown(full_table_html, unsafe_allow_html=True)

            # Branded Yellow Refresh Button
            c_btn1, c_btn2 = st.columns([2.5, 7.5])
            with c_btn1:
                if st.button("🔄 Refresh Market Data", use_container_width=True):
                    st.cache_data.clear()
                    st.rerun()
            with c_btn2:
                st.markdown("<div style='color: #A1A1AA; font-size: 12.5px; padding-top: 10px;'>Auto-syncs live every 3 minutes. Click 'Refresh Market Data' anytime to force an instant update. Auto-sort prioritizes highest statistical DCA value.</div>", unsafe_allow_html=True)

        with col_side:
            # INTERACTIVE CLICKABLE PORTFOLIO SUMMARY FILTERS
            st.markdown("""
            <div class="tid-card">
                <div class="tid-card-header">
                    <span>PORTFOLIO SUMMARY (CLICK TO FILTER)</span>
                    <span style="color: #FACC15;">17 ASSETS</span>
                </div>
            """, unsafe_allow_html=True)

            filter_items = [
                {"label": "Confirmed Buy Reversals", "count": f"{cnt_conf} Active", "status": "CONFIRMED BUY", "active_color": "#00E676"},
                {"label": "Ghost Capitulation Dips", "count": f"{cnt_ghost} Active", "status": "GHOST CAP", "active_color": "#FF8C00"},
                {"label": "Value Zone Assets", "count": f"{cnt_val} Stocks", "status": "VALUE ZONE", "active_color": "#2ea043"},
                {"label": "Fair Value Assets", "count": f"{cnt_fair} Stocks", "status": "FAIR VALUE", "active_color": "#FACC15"},
                {"label": "Falling Knife Protections", "count": f"{cnt_knife} Stocks", "status": "SCALE IN (SELLING)", "active_color": "#FFB300"},
                {"label": "Overbought / Extended", "count": f"{cnt_wait} Stocks", "status": "WAIT", "active_color": "#E53935"},
            ]

            for idx, fi in enumerate(filter_items):
                is_selected = (st.session_state.filter_status == fi["status"])

                c_lbl, c_act = st.columns([3.1, 1.5])
                with c_lbl:
                    lbl_color = fi["active_color"] if is_selected else "#FFFFFF"
                    check_mark = "▶ " if is_selected else ""
                    st.markdown(f"<div style='padding-top: 7px; font-weight: {800 if is_selected else 600}; color: {lbl_color}; font-size: 13.5px;'>{check_mark}{fi['label']}</div>", unsafe_allow_html=True)
                with c_act:
                    btn_txt = f"✓ {fi['count']}" if is_selected else fi["count"]
                    if st.button(btn_txt, key=f"btn_f_{idx}_{fi['status']}", use_container_width=True):
                        if st.session_state.filter_status == fi["status"]:
                            st.session_state.filter_status = "ALL"
                        else:
                            st.session_state.filter_status = fi["status"]
                        st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

            # STATUS BADGE & TACTICAL ACTION GUIDE - STRICT 1-LINE FIT
            st.markdown("""
            <div class="tid-card">
                <div class="tid-card-header">
                    <span>STATUS BADGE</span>
                    <span>TACTICAL ACTION GUIDE</span>
                </div>
                <div class="guide-row">
                    <span class="badge-confirmed">CONFIRMED BUY</span>
                    <span class="guide-text">Reversal bottom confirmed. Primary DCA entry.</span>
                </div>
                <div class="guide-row">
                    <span class="badge-ghost">GHOST CAP</span>
                    <span class="guide-text">Pierced -2.2 Sigma. Extreme capitulation scale-in.</span>
                </div>
                <div class="guide-row">
                    <span class="badge-knife">SCALE IN (SELLING)</span>
                    <span class="guide-text">Falling Knife active. Heavy selling. Scale in 25-50%.</span>
                </div>
                <div class="guide-row">
                    <span class="badge-value">VALUE ZONE</span>
                    <span class="guide-text">DCA Score 8-10 & Z &lt; -1.2. Prime accumulation.</span>
                </div>
                <div class="guide-row">
                    <span class="badge-fair">FAIR VALUE</span>
                    <span class="guide-text">DCA Score 6-7.9. Neutral routine accumulation.</span>
                </div>
                <div class="guide-row" style="border-bottom: none;">
                    <span class="badge-wait">WAIT</span>
                    <span class="guide-text">DCA Score &lt; 6 or Z &gt; 0. Overextended. Hold capital.</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ============================================================================
    # VIEW 2: DCA EFFICIENCY DASHBOARD v2.0 (ASSET DEEP-DIVE)
    # ============================================================================
    elif active_tab == "🎯 DCA Efficiency Dashboard v2.0":
        alphabetical_stocks = sorted(portfolio_data, key=lambda x: x["display"])
        dropdown_options = [f"{x['display']}  •  {x['name']}" for x in alphabetical_stocks]

        selected_option = st.selectbox(
            "Select Watchlist Asset (Alphabetical A-Z):",
            options=dropdown_options,
            index=next((i for i, x in enumerate(alphabetical_stocks) if x["display"] == "TSLA"), 0)
        )

        selected_ticker = selected_option.split("  •  ")[0].strip()
        asset = next(x for x in portfolio_data if x["display"] == selected_ticker)

        # Master DCA Strategy Banner Colors from TID - DCA Efficiency Dashboard v2.0:
        # color scoreColor = knifeActive ? color.rgb(255, 179, 0) : (totalScore >= 8.0 ? color.lime : totalScore >= 6.0 ? color.rgb(154, 230, 60) : totalScore >= 4.5 ? color.yellow : color.red)
        if asset["knife_active"]:
            banner_bg = "#FFB300"  # color.rgb(255, 179, 0) - SCALE IN (SELLING)
            banner_txt = "#000000"
        elif asset["dca_score"] >= 8.0:
            banner_bg = "#00E676"  # color.lime - AGGRESSIVE BUY / MAX VALUE BUY
            banner_txt = "#000000"
        elif asset["dca_score"] >= 6.0:
            banner_bg = "#9AE63C"  # color.rgb(154, 230, 60) - STANDARD DCA (Light Green!)
            banner_txt = "#000000"
        elif asset["dca_score"] >= 4.5:
            banner_bg = "#FACC15"  # color.yellow - LIGHT NIBBLE
            banner_txt = "#000000"
        else:
            banner_bg = "#E53935"  # color.red - HOLD / WAIT
            banner_txt = "#FFFFFF"

        st.markdown(f"""
        <div class="hud-banner-box" style="background-color: {banner_bg}; color: {banner_txt};">
            <div>
                <div style="font-size: 13.5px; font-weight: 800; letter-spacing: 1.5px; opacity: 0.95;">
                    DCA STRATEGY &nbsp;|&nbsp; {asset['name'].upper()} ({asset['display']})
                </div>
                <div style="font-size: 32px; font-weight: 900; letter-spacing: 0.5px; margin-top: 4px;">
                    {asset['strategy_banner']}
                </div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 13.5px; font-weight: 800; letter-spacing: 1px; opacity: 0.95;">SCORE / 10</div>
                <div style="font-size: 46px; font-weight: 900; line-height: 1; margin-top: 2px;">
                    {asset['dca_score']:.1f}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 2 Wide Panels with spacious high-contrast layout & authentic DCA Dashboard HUD Badges
        col_macro, col_exec = st.columns([1, 1])

        with col_macro:
            # Trend Direction
            sma200_val = asset.get("sma200")
            has_200 = False
            if sma200_val is not None and asset.get("symbol") != "SKHY":
                try:
                    f_val = float(sma200_val)
                    has_200 = not np.isnan(f_val) and f_val > 0
                except (ValueError, TypeError):
                    has_200 = False
            if not has_200:
                trend_lbl = "BULLISH (50D)" if asset["price"] > asset["sma50"] else "BEARISH (50D)"
            else:
                trend_lbl = asset["trend_dir"]

            if "BULLISH" in trend_lbl:
                trend_bg, trend_txt = "#00E676", "#000000"
            elif "BEARISH" in trend_lbl:
                trend_bg, trend_txt = "#E53935", "#FFFFFF"
            else:
                trend_bg, trend_txt = "#FFBF00", "#000000"

            # Market Momentum
            mom = asset["mkt_mom"]
            if mom == "BULLISH":
                mom_bg, mom_txt = "#00E676", "#000000"
            elif mom == "BEARISH":
                mom_bg, mom_txt = "#E53935", "#FFFFFF"
            else:
                mom_bg, mom_txt = "#FF8C00", "#FFFFFF"

            # RSI Level
            rsi_v = asset["rsi"]
            if rsi_v >= 70:
                rsi_bg, rsi_txt = "#E53935", "#FFFFFF"
            elif rsi_v >= 60:
                rsi_bg, rsi_txt = "#FF8C00", "#FFFFFF"
            elif rsi_v > 35:
                rsi_bg, rsi_txt = "#FFBF00", "#000000"
            else:
                rsi_bg, rsi_txt = "#00E676", "#000000"

            # Standard Deviation (Z-Score)
            zv = asset["z_score"]
            if zv >= 1.2:
                z_bg, z_txt = "#E53935", "#FFFFFF"
            elif zv <= -1.2:
                z_bg, z_txt = "#00E676", "#000000"
            else:
                z_bg, z_txt = "#FFBF00", "#000000"

            # 50 SMA Distance
            d50 = asset["dist50"]
            if d50 > 10.0:
                s50_bg, s50_txt = "#E53935", "#FFFFFF"
            elif d50 <= 0.0:
                s50_bg, s50_txt = "#00E676", "#000000"
            else:
                s50_bg, s50_txt = "#FFBF00", "#000000"

            # 200 SMA Distance
            d200 = asset["dist200"]
            if not has_200:
                s200_str = "N/A"
                s200_bg, s200_txt = "#4B5563", "#FFFFFF"
            elif d200 > 25.0:
                s200_str = f"{d200:+.1f}%"
                s200_bg, s200_txt = "#E53935", "#FFFFFF"
            elif d200 <= 0.0:
                s200_str = f"{d200:+.1f}%"
                s200_bg, s200_txt = "#00E676", "#000000"
            else:
                s200_str = f"{d200:+.1f}%"
                s200_bg, s200_txt = "#FFBF00", "#000000"

            # Distance from ATH
            d_ath = asset["dist_ath"]
            if d_ath >= -10.0:
                ath_bg, ath_txt = "#E53935", "#FFFFFF"
            elif d_ath >= -25.0:
                ath_bg, ath_txt = "#FFBF00", "#000000"
            else:
                ath_bg, ath_txt = "#00E676", "#000000"

            st.markdown(f"""
            <div class="deepdive-panel">
                <div class="deepdive-header">
                    <span>▼ MACRO VALUATION (1D • 3-PILLAR)</span>
                </div>
                <div class="metric-row">
                    <span class="metric-lbl">Trend Direction (50/200 SMA)</span>
                    <span style="background-color: {trend_bg}; color: {trend_txt}; font-weight: 800; padding: 4px 12px; border-radius: 4px; font-size: 12.5px;">{trend_lbl}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-lbl">Market Momentum (MACD Hist)</span>
                    <span style="background-color: {mom_bg}; color: {mom_txt}; font-weight: 800; padding: 4px 12px; border-radius: 4px; font-size: 12.5px;">{asset['mkt_mom']}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-lbl">RSI Level (14 Daily)</span>
                    <span style="background-color: {rsi_bg}; color: {rsi_txt}; font-weight: 800; padding: 4px 12px; border-radius: 4px; font-size: 12.5px;">{asset['rsi']:.1f}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-lbl">Standard Deviation (Z-Score)</span>
                    <span style="background-color: {z_bg}; color: {z_txt}; font-weight: 800; padding: 4px 12px; border-radius: 4px; font-size: 12.5px;">{asset['z_score']:+.1f}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-lbl">50 SMA Distance</span>
                    <span style="background-color: {s50_bg}; color: {s50_txt}; font-weight: 800; padding: 4px 12px; border-radius: 4px; font-size: 12.5px;">{asset['dist50']:+.1f}%</span>
                </div>
                <div class="metric-row">
                    <span class="metric-lbl">200 SMA Distance</span>
                    <span style="background-color: {s200_bg}; color: {s200_txt}; font-weight: 800; padding: 4px 12px; border-radius: 4px; font-size: 12.5px;">{s200_str}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-lbl">Distance from Peak (ATH)</span>
                    <span style="background-color: {ath_bg}; color: {ath_txt}; font-weight: 800; padding: 4px 12px; border-radius: 4px; font-size: 12.5px;">{asset['dist_ath']:+.1f}%</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col_exec:
            # Order Flow (1D CVD)
            cvd = asset["cvd_state"]
            if cvd == "BULLISH":
                cvd_bg, cvd_txt = "#00E676", "#000000"
            elif cvd == "BEARISH":
                cvd_bg, cvd_txt = "#E53935", "#FFFFFF"
            else:
                cvd_bg, cvd_txt = "#FF8C00", "#FFFFFF"

            # Institutional Volume (1D)
            vol = asset["vol_state"]
            if vol == "HEAVY BUYING":
                vol_bg, vol_txt = "#00E676", "#000000"
            elif vol == "HEAVY SELLING":
                vol_bg, vol_txt = "#E53935", "#FFFFFF"
            else:
                vol_bg, vol_txt = "#3F3F46", "#FFFFFF"

            # Falling Knife Guard
            if asset["knife_active"]:
                knife_lbl = "ACTIVE PROTECTION (Scale in 25-50%)"
                knife_bg, knife_txt = "#FFB300", "#000000"
            else:
                knife_lbl = "CLEAR (No Liquidation Spike)"
                knife_bg, knife_txt = "#00E676", "#000000"

            # Tactical Recommendation
            st_text = asset["status"]
            if st_text == "CONFIRMED BUY":
                tact_bg, tact_txt = "#00E676", "#000000"
            elif st_text == "GHOST CAP":
                tact_bg, tact_txt = "#FF8C00", "#000000"
            elif st_text == "SCALE IN (SELLING)":
                tact_bg, tact_txt = "#FFB300", "#000000"
            elif st_text == "VALUE ZONE":
                tact_bg = "#2EA043", "#FFFFFF"
            elif st_text == "FAIR VALUE":
                tact_bg = "#27272A", "#E4E4E7"
            else:
                tact_bg = "#E53935", "#FFFFFF"

            td_c = "#00E676" if asset["today_chg"] > 0 else ("#FF5252" if asset["today_chg"] < 0 else "#FFFFFF")
            ys_c = "#00E676" if asset["yest_chg"] > 0 else ("#FF5252" if asset["yest_chg"] < 0 else "#FFFFFF")

            st.markdown(f"""
            <div class="deepdive-panel">
                <div class="deepdive-header">
                    <span>▼ EXECUTION ENGINE (1D TF • LIVE SYNC)</span>
                </div>
                <div class="metric-row">
                    <span class="metric-lbl">Order Flow (1D CVD)</span>
                    <span style="background-color: {cvd_bg}; color: {cvd_txt}; font-weight: 800; padding: 4px 12px; border-radius: 4px; font-size: 12.5px;">{asset['cvd_state']}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-lbl">Institutional Volume (1D)</span>
                    <span style="background-color: {vol_bg}; color: {vol_txt}; font-weight: 800; padding: 4px 12px; border-radius: 4px; font-size: 12.5px;">{asset['vol_state']}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-lbl">Falling Knife Guard</span>
                    <span style="background-color: {knife_bg}; color: {knife_txt}; font-weight: 800; padding: 4px 12px; border-radius: 4px; font-size: 12.5px;">{knife_lbl}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-lbl">Today's 1D Change</span>
                    <span class="metric-val-bold" style="color: {td_c};">{asset['today_chg']:+.1f}%</span>
                </div>
                <div class="metric-row">
                    <span class="metric-lbl">Yesterday's 1D Change</span>
                    <span class="metric-val-bold" style="color: {ys_c};">{asset['yest_chg']:+.1f}%</span>
                </div>
                <div class="metric-row">
                    <span class="metric-lbl">Current Price</span>
                    <span class="metric-val-bold">${asset['price']:,.2f}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-lbl">Tactical Recommendation</span>
                    <span style="background-color: {tact_bg}; color: {tact_txt}; font-weight: 800; padding: 4px 12px; border-radius: 4px; font-size: 12.5px;">{asset['status']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # High-Definition Interactive Chart
        st.markdown(f"<h4 style='color: #FFFFFF; font-weight: 800; font-size: 1.2rem; margin-top: 10px;'>{asset['display']} Interactive Chart (Price • 50/200 SMA • ±2.2σ Envelope • CVD)</h4>", unsafe_allow_html=True)
        df = asset["df"]

        fig = make_subplots(
            rows=2, cols=1, 
            shared_xaxes=True,
            vertical_spacing=0.06,
            row_heights=[0.74, 0.26],
            subplot_titles=("", "Cumulative Volume Delta (CVD) Order Flow")
        )

        # Price Candlestick
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name="Price",
            increasing_line_color='#00E676',
            decreasing_line_color='#FF5252'
        ), row=1, col=1)

        # 50 SMA (Electric Blue) & 200 SMA (Yellow)
        if 'SMA50' in df:
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], mode='lines', name='50 SMA (Daily Pulse)', line=dict(color='#0084FF', width=2.5)), row=1, col=1)
        if 'SMA200' in df and not df['SMA200'].dropna().empty:
            fig.add_trace(go.Scatter(x=df.index, y=df['SMA200'], mode='lines', name='200 SMA (Daily Floor)', line=dict(color='#FACC15', width=2.5)), row=1, col=1)

        # ±2.2 Sigma Bands
        if 'ConfUpper' in df and 'ConfLower' in df:
            fig.add_trace(go.Scatter(x=df.index, y=df['ConfUpper'], mode='lines', name='+2.2σ Upper Band', line=dict(color='#9CA3AF', width=1.3, dash='dot')), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['ConfLower'], mode='lines', name='-2.2σ Lower Band', line=dict(color='#9CA3AF', width=1.3, dash='dot')), row=1, col=1)

        # Markers for Confirmed Buys and Ghost Buys
        conf_buys = df[df['ConfBuy']]
        if not conf_buys.empty:
            fig.add_trace(go.Scatter(
                x=conf_buys.index,
                y=conf_buys['Low'] * 0.98,
                mode='markers',
                name='Confirmed Buy',
                marker=dict(symbol='triangle-up', size=13, color='#00E676', line=dict(width=1, color='#FFFFFF'))
            ), row=1, col=1)

        ghost_buys = df[df['GhostBuy'] & ~df['ConfBuy']]
        if not ghost_buys.empty:
            fig.add_trace(go.Scatter(
                x=ghost_buys.index,
                y=ghost_buys['Low'] * 0.98,
                mode='markers',
                name='Ghost Capitulation',
                marker=dict(symbol='triangle-up', size=11, color='#FF8C00', line=dict(width=1, color='#FFFFFF'))
            ), row=1, col=1)

        # Subplot: CVD Line & Signal
        fig.add_trace(go.Scatter(x=df.index, y=df['rCVD'], mode='lines', name='CVD Order Flow', line=dict(color='#00E676', width=2)), row=2, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['CVDSig'], mode='lines', name='CVD Signal (14 SMA)', line=dict(color='#FF5252', width=1.8)), row=2, col=1)

        # Subplot Title Styling (Gold font for CVD header)
        for annotation in fig['layout']['annotations']:
            annotation['font'] = dict(size=12.5, color='#FACC15', family='Inter')

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#101012",
            plot_bgcolor="#080808",
            margin=dict(l=25, r=25, t=55, b=25),
            xaxis_rangeslider_visible=False,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.03,
                xanchor="center",
                x=0.5,
                bgcolor="#18181B",
                bordercolor="#4B5563",
                borderwidth=1.5,
                font=dict(color="#FFFFFF", size=12.5, family="Inter")
            ),
            font=dict(family="Inter", color="#FFFFFF"),
            height=720
        )

        fig.update_xaxes(
            gridcolor="#222226", 
            tickfont=dict(color="#D4D4D8", size=11, family="Inter"),
            linecolor="#4B5563"
        )
        fig.update_yaxes(
            gridcolor="#222226", 
            tickfont=dict(color="#D4D4D8", size=11, family="Inter"),
            linecolor="#4B5563"
        )

        st.plotly_chart(fig, use_container_width=True)

    # ============================================================================
    # VIEW 3: TRADINGVIEW ALERT LOG & WEBHOOK SETUP
    # ============================================================================
    elif active_tab == "🔔 Optimised Trend Alert Log":
        st.markdown("<h4 style='color: #FFFFFF; font-weight: 800; font-size: 1.2rem;'>TID - Optimised Trend Live Webhook Alert Stream</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color: #A1A1AA; font-size: 13px; margin-bottom: 16px;'>This table displays real signals transmitted from your live TradingView alerts. (Any test signals used during setup have been cleared).</div>", unsafe_allow_html=True)

        col_w1, col_w2 = st.columns([2, 1])
        with col_w1:
            st.markdown("""
            <div class="tid-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-weight: 800; color: #FFFFFF;">📡 Webhook Listener Endpoint:</span>
                    <span style="background-color: #18181B; color: #00E676; padding: 5px 12px; border-radius: 4px; font-family: monospace; font-size: 13.5px; border: 1px solid #27272A;">
                        http://localhost:8000/webhook
                    </span>
                </div>
                <div style="font-size: 12.5px; color: #A1A1AA; margin-top: 8px;">
                    TradingView will send live alerts from <strong>TID - Optimised Trend v1.1</strong> and <strong>IA13 Master Scanner</strong> directly to this endpoint.
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col_w2:
            st.markdown("""
            <div class="tid-card">
                <div style="font-weight: 800; color: #FFFFFF; margin-bottom: 8px;">🧪 Webhook Test Simulator</div>
            """, unsafe_allow_html=True)
            if st.button("Send Test Alert (NVDA)", use_container_width=True):
                log_alert(
                    ticker="NVDA", 
                    signal_type="CONFIRMED BUY", 
                    price=204.64, 
                    timeframe="1D", 
                    raw_message="TID Confirmed Reversal BUY on NASDAQ:NVDA (1D)", 
                    action="BUY"
                )
                st.success("Test alert logged to database!")
                time.sleep(0.5)
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # Filter alerts
        alphabetical_tickers = sorted(list(set([t["display"] for t in portfolio_data])))
        filter_ticker = st.selectbox("Filter Alert Feed by Ticker (A-Z):", options=["ALL"] + alphabetical_tickers)
        recent_alerts = get_recent_alerts(limit=50, ticker=None if filter_ticker == "ALL" else filter_ticker)

        if recent_alerts:
            rows = []
            for a in recent_alerts:
                px_val = f"${a['price']:.2f}" if a["price"] else "N/A"
                sig_col = "#00E676" if "BUY" in a["signal_type"] else ("#FF8C00" if "GHOST" in a["signal_type"] else "#FFFFFF")
                row_html = (
                    f'<tr>'
                    f'<td style="color: #A1A1AA; font-size: 12.5px;">{a["timestamp"]}</td>'
                    f'<td style="font-weight: 800; color: #FFFFFF;">{a["ticker"]}</td>'
                    f'<td style="font-weight: 800; color: {sig_col};">{a["signal_type"]}</td>'
                    f'<td style="font-weight: 700; color: #00E676;">{a["action"]}</td>'
                    f'<td style="font-weight: 700; color: #FFFFFF;">{px_val}</td>'
                    f'<td style="color: #A1A1AA;">{a["timeframe"]}</td>'
                    f'<td style="font-family: monospace; font-size: 12px; color: #D4D4D8;">{a["raw_message"]}</td>'
                    f'</tr>'
                )
                rows.append(row_html)

            body_html = "".join(rows)
            alert_table_html = (
                f'<div class="tid-table-wrapper">'
                f'<table class="tid-table">'
                f'<thead>'
                f'<tr>'
                f'<th>TIMESTAMP</th>'
                f'<th>TICKER</th>'
                f'<th>SIGNAL TYPE</th>'
                f'<th>ACTION</th>'
                f'<th>PRICE</th>'
                f'<th>TIMEFRAME</th>'
                f'<th>RAW MESSAGE</th>'
                f'</tr>'
                f'</thead>'
                f'<tbody>{body_html}</tbody>'
                f'</table>'
                f'</div>'
            )
            st.markdown(alert_table_html, unsafe_allow_html=True)

            if st.button("🗑️ Clear Alert History"):
                clear_alerts()
                st.rerun()
        else:
            st.info("No incoming alerts logged yet. Webhook listener is waiting on port 8000. When TradingView triggers an alert, it will immediately appear here.")

    # VIEW 4: MOBILE VIEW
    # ============================================================================
    elif active_tab == "📱 Mobile View":
        st.markdown("<h4 style='color: #FFFFFF; font-weight: 800; font-size: 1.15rem; margin-bottom: 4px;'>📱 Mobile Portfolio Table (DCA Column 3rd)</h4>", unsafe_allow_html=True)
        st.markdown("<div style='color: #A1A1AA; font-size: 12.5px; margin-bottom: 12px;'>Optimized for mobile screens. Swipe horizontally to view all metrics.</div>", unsafe_allow_html=True)

        # Build Mobile-Optimized Table with DCA strictly in the 3rd column
        m_rows = []
        for item in portfolio_data:
            sc = item["dca_score"]
            sc_cls = "dca-pill-8" if sc >= 8.0 else ("dca-pill-6" if sc >= 6.0 else ("dca-pill-4" if sc >= 4.5 else "dca-pill-low"))

            td_col = "#00E676" if item["today_chg"] > 0 else ("#FF5252" if item["today_chg"] < 0 else "#FFFFFF")
            ys_col = "#00E676" if item["yest_chg"] > 0 else ("#FF5252" if item["yest_chg"] < 0 else "#FFFFFF")

            td_str = f"{item['today_chg']:+.1f}%"
            ys_str = f"{item['yest_chg']:+.1f}%"

            st_text = item["status"]
            if st_text == "CONFIRMED BUY":
                st_badge = f'<span class="badge-confirmed">{st_text}</span>'
            elif st_text == "GHOST CAP":
                st_badge = f'<span class="badge-ghost">{st_text}</span>'
            elif st_text == "SCALE IN (SELLING)":
                st_badge = f'<span class="badge-knife">{st_text}</span>'
            elif st_text == "VALUE ZONE":
                st_badge = f'<span class="badge-value">{st_text}</span>'
            elif st_text == "FAIR VALUE":
                st_badge = f'<span class="badge-fair">{st_text}</span>'
            else:
                st_badge = f'<span class="badge-wait">{st_text}</span>'

            cvd = item["cvd_state"]
            cvd_badge = f'<span class="cvd-{cvd.lower()}">{cvd}</span>'

            z_val = item["z_score"]
            z_col = "#00E676" if z_val <= -1.2 else ("#FF5252" if z_val >= 1.2 else "#FFFFFF")
            z_str = f"{z_val:+.1f} SD"

            rsi_val = item["rsi"]
            rsi_col = "#00E676" if rsi_val <= 30 else ("#9ae63c" if rsi_val <= 40 else ("#FF5252" if rsi_val >= 70 else "#FFFFFF"))

            p_str = f"${item['price']:,.2f}" if item['price'] >= 100 else f"${item['price']:.2f}"

            # Exact sequence: TICKER, PRICE, DCA (3rd), TODAY 1D, YEST 1D, STATUS, CVD FLOW, Z-SCORE, RSI
            row_html = (
                f'<tr>'
                f'<td style="font-weight: 800; color: #FFFFFF; font-size: 14px; position: sticky; left: 0; background-color: #121214; z-index: 2;">{item["display"]}</td>'
                f'<td style="font-weight: 700; color: #FFFFFF;">{p_str}</td>'
                f'<td style="text-align: center;"><span class="{sc_cls}">{sc:.1f}</span></td>'
                f'<td style="font-weight: 800; color: {td_col};">{td_str}</td>'
                f'<td style="font-weight: 800; color: {ys_col};">{ys_str}</td>'
                f'<td style="text-align: center;">{st_badge}</td>'
                f'<td>{cvd_badge}</td>'
                f'<td style="font-weight: 700; color: {z_col};">{z_str}</td>'
                f'<td style="font-weight: 700; color: {rsi_col};">{rsi_val:.1f}</td>'
                f'</tr>'
            )
            m_rows.append(row_html)

        m_body_html = "".join(m_rows)
        m_full_table = (
            f'<div class="tid-table-wrapper" style="overflow-x: auto; margin-bottom: 24px;">'
            f'<table class="tid-table" style="min-width: 680px;">'
            f'<thead>'
            f'<tr>'
            f'<th style="position: sticky; left: 0; background-color: #161618; z-index: 3;">TICKER</th>'
            f'<th>PRICE</th>'
            f'<th style="text-align: center; color: #00E676;">DCA</th>'
            f'<th>TODAY 1D</th>'
            f'<th>YEST 1D</th>'
            f'<th style="text-align: center;">STATUS</th>'
            f'<th>CVD FLOW</th>'
            f'<th>Z-SCORE</th>'
            f'<th>RSI</th>'
            f'</tr>'
            f'</thead>'
            f'<tbody>{m_body_html}</tbody>'
            f'</table>'
            f'</div>'
        )
        st.markdown(m_full_table, unsafe_allow_html=True)

        st.markdown("<h4 style='color: #FFFFFF; font-weight: 800; font-size: 1.15rem; margin-top: 16px; margin-bottom: 12px;'>📱 Quick Touch Cards</h4>", unsafe_allow_html=True)

        for item in portfolio_data:
            sc = item["dca_score"]
            sc_cls = "dca-pill-8" if sc >= 8.0 else ("dca-pill-6" if sc >= 6.0 else ("dca-pill-4" if sc >= 4.5 else "dca-pill-low"))

            td_col = "#00E676" if item["today_chg"] > 0 else ("#FF5252" if item["today_chg"] < 0 else "#FFFFFF")
            ys_col = "#00E676" if item["yest_chg"] > 0 else ("#FF5252" if item["yest_chg"] < 0 else "#FFFFFF")

            st_text = item["status"]
            if st_text == "CONFIRMED BUY":
                st_badge = f'<span class="badge-confirmed">{st_text}</span>'
            elif st_text == "GHOST CAP":
                st_badge = f'<span class="badge-ghost">{st_text}</span>'
            elif st_text == "SCALE IN (SELLING)":
                st_badge = f'<span class="badge-knife">{st_text}</span>'
            elif st_text == "VALUE ZONE":
                st_badge = f'<span class="badge-value">{st_text}</span>'
            elif st_text == "FAIR VALUE":
                st_badge = f'<span class="badge-fair">{st_text}</span>'
            else:
                st_badge = f'<span class="badge-wait">{st_text}</span>'

            cvd = item["cvd_state"]
            cvd_badge = f'<span class="cvd-{cvd.lower()}">{cvd}</span>'

            # 3-item top bar: Ticker (1st), Price (2nd), DCA (3rd)
            st.markdown(f"""
            <div style="background-color: #121214; border: 1.5px solid #27272A; border-radius: 8px; padding: 14px 16px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; border-bottom: 1px solid #1E1E22; padding-bottom: 8px;">
                    <div>
                        <span style="font-size: 19px; font-weight: 800; color: #FFFFFF;">{item['display']}</span>
                        <span style="font-size: 11.5px; color: #A1A1AA; margin-left: 4px;">{item['name']}</span>
                    </div>
                    <div style="font-size: 18px; font-weight: 800; color: #FFFFFF;">${item['price']:,.2f}</div>
                    <div><span class="{sc_cls}" style="font-size: 13.5px; font-weight: 900; padding: 4px 10px;">DCA {sc:.1f}</span></div>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <div>{st_badge}</div>
                    <div>{cvd_badge}</div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; background-color: #080808; padding: 10px 12px; border-radius: 6px; font-size: 13px; border: 1px solid #1E1E22;">
                    <div>Today 1D: <strong style="color: {td_col};">{item['today_chg']:+.1f}%</strong></div>
                    <div>Yest 1D: <strong style="color: {ys_col};">{item['yest_chg']:+.1f}%</strong></div>
                    <div>Z-Score: <strong>{item['z_score']:+.1f} SD</strong></div>
                    <div>RSI 14: <strong>{item['rsi']:.1f}</strong></div>
                    <div style="grid-column: span 2;">Vol Regime: <strong style="color: #FFFFFF;">{item['vol_state']}</strong></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# Run the live auto-refreshing dashboard
render_live_dashboard()
