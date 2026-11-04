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
    fetch_single_asset_detail,
    get_uk_now_str,
    build_optimised_trend_signal_log
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
        font-size: 12px;
        letter-spacing: 0.6px;
        padding: 11px 12px;
        border: 1.5px solid #4B5563 !important; /* High-contrast cell border */
        border-bottom: 2.5px solid #FACC15 !important;
        text-align: left;
        white-space: nowrap;
    }
    .tid-table td {
        padding: 10px 12px;
        border: 1.5px solid #4B5563 !important; /* High-contrast cell border between every row & column */
        white-space: nowrap;
        font-weight: 600;
        font-size: 13px;
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

    /* Compact Institutional 4-Card Signal Scorecard Strip */
    .tid-kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
        margin: 6px 0 16px 0;
    }
    @media (max-width: 960px) {
        .tid-kpi-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }
    .tid-kpi-card {
        background: linear-gradient(180deg, #16161A 0%, #101013 100%);
        border: 1px solid #2E2E36;
        border-top: 2.5px solid #FACC15;
        border-radius: 7px;
        padding: 11px 15px;
    }
    .tid-kpi-label {
        color: #A1A1AA;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 0.7px;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    .tid-kpi-value {
        color: #FFFFFF;
        font-size: 1.32rem;
        font-weight: 900;
        line-height: 1.2;
        letter-spacing: -0.3px;
    }
    .tid-kpi-sub {
        color: #A1A1AA;
        font-size: 12px;
        font-weight: 600;
        margin-top: 4px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
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
    now_str = get_uk_now_str()
    st_col1, st_col2 = st.columns([3, 2])

    with st_col1:
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
            <span class="badge-yellow">EQUITIES & STOCKS</span>
            <span class="badge-dark-pill">17 ASSETS</span>
            <span class="badge-yellow">SNAPSHOT</span>
            <span class="badge-dark-pill">{now_str} (UK Time • Live Sync)</span>
        </div>
        """, unsafe_allow_html=True)

    with st_col2:
        st.markdown(f"""
        <div style="display: flex; justify-content: flex-end; align-items: center; gap: 8px; flex-wrap: wrap;">
            <span class="badge-dark-pill" style="border-color: #00E676; color: #00E676;">
                <span style="font-size: 13px;">\u25cf</span> Auto-Refresh: 3 Min (Active)
            </span>
            <span class="badge-dark-pill" style="border-color: #00E676; color: #00E676;">
                <span style="font-size: 13px;">\u25cf</span> 1D Engine &amp; Signal Log (Active)
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
        "🔔 Optimised Trend Alert Log"
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
        col_main, col_side = st.columns([6.7, 3.3])

        with col_main:
            active_filter = st.session_state.filter_status
            if active_filter != "ALL":
                display_data = [x for x in portfolio_data if x["status"] == active_filter]
            else:
                display_data = portfolio_data

            # Top Header + Branded Yellow Refresh Button ABOVE the Watchlist Table
            c_hdr1, c_hdr2 = st.columns([7.2, 2.8])
            with c_hdr1:
                st.markdown(
                    "<div style='margin-bottom: 10px;'>"
                    "<h4 style='margin: 0; color: #FFFFFF; font-weight: 800; font-size: 1.2rem;'>Portfolio Watchlist (Auto-Sorted by Highest DCA Score)</h4>"
                    "<div style='color: #A1A1AA; font-size: 12px; margin-top: 3px;'>Auto-syncs live every 3 minutes • All signal timestamps in UK Time (GMT/BST)</div>"
                    "</div>",
                    unsafe_allow_html=True
                )
            with c_hdr2:
                if st.button("🔄 Refresh Market Data", use_container_width=True):
                    st.cache_data.clear()
                    st.rerun()

            # Filter Banner Header (if filtered via Portfolio Summary)
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

                # Ghost Cap flash date & UK time styling
                gb_short = item.get("last_ghost_short", "—")
                gb_days = item.get("last_ghost_days_ago", 9999)
                if item.get("ghost_buy"):
                    gb_cell = f'<span style="color: #FF8C00; font-weight: 800;">⚡ {gb_short}</span>'
                elif gb_days <= 14:
                    gb_cell = f'<span style="color: #E4E4E7; font-weight: 600;">{gb_short}</span>'
                else:
                    gb_cell = f'<span style="color: #9CA3AF; font-weight: 500;">{gb_short}</span>'

                # Column order: TICKER, PRICE, DCA (3rd), TODAY 1D, YEST 1D, Std. Dev., RSI, CVD FLOW (1D), STATUS, GHOST CAP (UK)
                row_html = (
                    f'<tr>'
                    f'<td style="font-weight: 800; color: #FFFFFF; font-size: 14px;">{item["display"]}</td>'
                    f'<td style="font-weight: 700; color: #FFFFFF;">{p_str}</td>'
                    f'<td style="text-align: center;"><span class="{sc_cls}">{sc:.1f}</span></td>'
                    f'<td style="font-weight: 800; color: {td_col};">{td_str}</td>'
                    f'<td style="font-weight: 800; color: {ys_col};">{ys_str}</td>'
                    f'<td style="font-weight: 700; color: {z_col};">{z_str}</td>'
                    f'<td style="font-weight: 700; color: {rsi_col};">{rsi_val:.1f}</td>'
                    f'<td>{cvd_badge}</td>'
                    f'<td style="text-align: center;">{st_badge}</td>'
                    f'<td style="font-size: 12.5px;">{gb_cell}</td>'
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
                f'<th style="text-align: center;">DCA</th>'
                f'<th>TODAY 1D</th>'
                f'<th>YEST 1D</th>'
                f'<th>Std. Dev.</th>'
                f'<th>RSI</th>'
                f'<th>CVD FLOW (1D)</th>'
                f'<th style="text-align: center;">STATUS</th>'
                f'<th>GHOST CAP (UK)</th>'
                f'</tr>'
                f'</thead>'
                f'<tbody>{body_html}</tbody>'
                f'</table>'
                f'</div>'
            )

            st.markdown(full_table_html, unsafe_allow_html=True)

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
                    <span class="guide-text">Pierced -2.2 Std. Dev. Extreme capitulation scale-in.</span>
                </div>
                <div class="guide-row">
                    <span class="badge-knife">SCALE IN (SELLING)</span>
                    <span class="guide-text">Falling Knife active. Heavy selling. Scale in 25-50%.</span>
                </div>
                <div class="guide-row">
                    <span class="badge-value">VALUE ZONE</span>
                    <span class="guide-text">DCA Score 8-10 &amp; Std. Dev. &lt; -1.2. Prime accumulation.</span>
                </div>
                <div class="guide-row">
                    <span class="badge-fair">FAIR VALUE</span>
                    <span class="guide-text">DCA Score 6-7.9. Neutral routine accumulation.</span>
                </div>
                <div class="guide-row" style="border-bottom: none;">
                    <span class="badge-wait">WAIT</span>
                    <span class="guide-text">DCA Score &lt; 6 or Std. Dev. &gt; 0. Overextended. Hold.</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ============================================================================
    # VIEW 2: OPTIMISED TREND ALERT LOG (AUTO-DETECTED + WEBHOOK STREAM)
    # ============================================================================
    elif active_tab == "🔔 Optimised Trend Alert Log":
        c_al_hdr1, c_al_hdr2 = st.columns([7.8, 2.2])
        with c_al_hdr1:
            st.markdown(
                "<h4 style='color: #FFFFFF; font-weight: 800; font-size: 1.2rem; margin: 0;'>🔔 Optimised Trend Signal &amp; Alert Log (UK Time)</h4>"
                "<div style='color: #A1A1AA; font-size: 13px; margin-top: 4px; margin-bottom: 14px;'>"
                "Automatically detects and logs every <strong>Confirmed Buy</strong> reversal and <strong>Ghost Capitulation</strong> flash across all 17 portfolio assets in UK Time (GMT/BST)."
                "</div>",
                unsafe_allow_html=True
            )
        with c_al_hdr2:
            if st.button("🔄 Refresh Signals", use_container_width=True):
                st.cache_data.clear()
                st.rerun()

        # 3-Column Filter Bar: Lookback Window (Default: Last 7 Trading Days) + Signal Type + Ticker (A-Z)
        LOOKBACK_MAP = {
            "Last 7 Trading Days": "7D",
            "Last 1 Month": "1M",
            "Last 3 Months": "3M",
            "Last 1 Year": "1Y",
            "Full 2 Years": "2Y",
        }
        f_col1, f_col2, f_col3 = st.columns([1.05, 1.25, 0.95])
        with f_col1:
            lookback_choice = st.selectbox(
                "Lookback Window:",
                options=list(LOOKBACK_MAP.keys()),
                index=0
            )
        with f_col2:
            sig_type_choice = st.selectbox(
                "Filter by Signal Type:",
                options=["ALL SIGNALS (Confirmed + Ghost Cap)", "CONFIRMED BUY ONLY", "GHOST CAP ONLY"]
            )
        with f_col3:
            alphabetical_tickers = sorted(list(set([t["display"] for t in portfolio_data])))
            filter_ticker = st.selectbox("Filter by Ticker (A-Z):", options=["ALL"] + alphabetical_tickers)

        lookback_arg = LOOKBACK_MAP[lookback_choice]
        if sig_type_choice == "CONFIRMED BUY ONLY":
            sig_filter_arg = "CONFIRMED BUY"
        elif sig_type_choice == "GHOST CAP ONLY":
            sig_filter_arg = "GHOST CAP"
        else:
            sig_filter_arg = "ALL"

        webhook_rows = get_recent_alerts(limit=100, ticker=None if filter_ticker == "ALL" else filter_ticker)
        signal_log = build_optimised_trend_signal_log(
            portfolio_data=portfolio_data,
            webhook_alerts=webhook_rows,
            ticker_filter=filter_ticker,
            signal_filter=sig_filter_arg,
            lookback_window=lookback_arg,
            limit=1000
        )

        if signal_log:
            # ----------------------------------------------------------------
            # Compact Institutional 4-Card Signal Scorecard Strip
            # ----------------------------------------------------------------
            total_sigs = len(signal_log)
            conf_sigs_cnt = sum(1 for s in signal_log if "CONFIRMED BUY" in s.get("signal_type", ""))
            ghost_sigs_cnt = sum(1 for s in signal_log if "GHOST" in s.get("signal_type", ""))

            eval_sigs = [s for s in signal_log if not s.get("is_active_bar")] or signal_log
            wins_cnt = sum(1 for s in eval_sigs if s.get("return_pct", 0.0) > 0)
            win_rate = (wins_cnt / len(eval_sigs)) * 100.0 if eval_sigs else 0.0
            win_col = "#00E676" if win_rate >= 55.0 else ("#FACC15" if win_rate >= 40.0 else "#FF5252")

            avg_ret = sum(s.get("return_pct", 0.0) for s in eval_sigs) / len(eval_sigs) if eval_sigs else 0.0
            avg_ret_col = "#00E676" if avg_ret > 0 else ("#FF5252" if avg_ret < 0 else "#FFFFFF")

            dca_vals = [float(s["signal_dca"]) for s in signal_log if s.get("signal_dca") is not None]
            avg_sig_dca = (sum(dca_vals) / len(dca_vals)) if dca_vals else 0.0

            best_sig = max(eval_sigs, key=lambda x: x.get("return_pct", -9999.0))
            best_ret = best_sig.get("return_pct", 0.0)
            best_col = "#00E676" if best_ret > 0 else ("#FF5252" if best_ret < 0 else "#FFFFFF")
            best_type_lbl = "Confirmed" if "CONFIRMED" in best_sig.get("signal_type", "") else "Ghost Cap"
            best_date_lbl = str(best_sig.get("timestamp_uk", "")).split(",")[0]

            scorecard_html = (
                f'<div class="tid-kpi-grid">'
                f'<div class="tid-kpi-card">'
                f'<div class="tid-kpi-label">Signals ({lookback_choice})</div>'
                f'<div class="tid-kpi-value">{total_sigs} Logged</div>'
                f'<div class="tid-kpi-sub">'
                f'<span style="color: #00E676; font-weight: 700;">{conf_sigs_cnt} Confirmed</span>'
                f' &bull; '
                f'<span style="color: #FF8C00; font-weight: 700;">{ghost_sigs_cnt} Ghost Cap</span>'
                f'</div>'
                f'</div>'
                f'<div class="tid-kpi-card">'
                f'<div class="tid-kpi-label">Win Rate (% In Profit)</div>'
                f'<div class="tid-kpi-value" style="color: {win_col};">{win_rate:.1f}%</div>'
                f'<div class="tid-kpi-sub">{wins_cnt} of {len(eval_sigs)} signals currently green</div>'
                f'</div>'
                f'<div class="tid-kpi-card">'
                f'<div class="tid-kpi-label">Avg Return Since Signal</div>'
                f'<div class="tid-kpi-value" style="color: {avg_ret_col};">{avg_ret:+.1f}%</div>'
                f'<div class="tid-kpi-sub">Avg DCA at Signal: <span style="color: #FACC15; font-weight: 800;">{avg_sig_dca:.1f} / 10</span></div>'
                f'</div>'
                f'<div class="tid-kpi-card">'
                f'<div class="tid-kpi-label">Top Signal In Window</div>'
                f'<div class="tid-kpi-value">{best_sig["ticker"]} <span style="color: {best_col};">{best_ret:+.1f}%</span></div>'
                f'<div class="tid-kpi-sub">{best_date_lbl} &bull; {best_type_lbl}</div>'
                f'</div>'
                f'</div>'
            )
            st.markdown(scorecard_html, unsafe_allow_html=True)

            rows = []
            for a in signal_log:
                px_val = f"${a['price']:,.2f}" if a["price"] >= 100 else (f"${a['price']:.2f}" if a["price"] else "N/A")
                cur_val = f"${a['current_price']:,.2f}" if a["current_price"] >= 100 else f"${a['current_price']:.2f}"
                ret_pct = a.get("return_pct", 0.0)
                ret_col = "#00E676" if ret_pct > 0 else ("#FF5252" if ret_pct < 0 else "#A1A1AA")
                ret_str = "LIVE BAR" if a.get("is_active_bar") else f"{ret_pct:+.1f}% ({cur_val})"
                if a.get("is_active_bar"):
                    ret_col = "#FACC15"

                sig_dca = a.get("signal_dca")
                if sig_dca is not None:
                    sdca_cls = (
                        "dca-pill-8" if sig_dca >= 8.0
                        else ("dca-pill-6" if sig_dca >= 6.0 else ("dca-pill-4" if sig_dca >= 4.5 else "dca-pill-low"))
                    )
                    dca_cell = f'<span class="{sdca_cls}">{sig_dca:.1f}</span>'
                else:
                    dca_cell = '<span style="color: #9CA3AF;">—</span>'

                stype = a["signal_type"]
                if "CONFIRMED BUY" in stype:
                    sig_badge = '<span class="badge-confirmed">CONFIRMED BUY</span>'
                    act_col = "#00E676"
                elif "GHOST" in stype:
                    sig_badge = '<span class="badge-ghost">GHOST CAP</span>'
                    act_col = "#FF8C00"
                else:
                    sig_badge = f'<span class="badge-fair">{stype}</span>'
                    act_col = "#FFFFFF"

                live_dot = '<span style="color: #00E676; font-weight: 900; margin-right: 6px;">●</span>' if a.get("is_active_bar") else ""

                row_html = (
                    f'<tr>'
                    f'<td style="color: #E4E4E7; font-size: 13px; font-weight: 700;">{live_dot}{a["timestamp_uk"]}</td>'
                    f'<td style="font-weight: 800; color: #FFFFFF; font-size: 14px;">{a["ticker"]} <span style="color: #9CA3AF; font-weight: 500; font-size: 12px; margin-left: 4px;">{a["name"]}</span></td>'
                    f'<td style="text-align: center;">{dca_cell}</td>'
                    f'<td style="text-align: center;">{sig_badge}</td>'
                    f'<td style="font-weight: 800; color: {act_col};">{a["action"]}</td>'
                    f'<td style="font-weight: 700; color: #FFFFFF;">{px_val}</td>'
                    f'<td style="font-weight: 700; color: {ret_col};">{ret_str}</td>'
                    f'<td style="color: #D4D4D8; font-size: 12.5px;">{a["raw_message"]}</td>'
                    f'</tr>'
                )
                rows.append(row_html)

            body_html = "".join(rows)
            alert_table_html = (
                f'<div class="tid-table-wrapper">'
                f'<table class="tid-table">'
                f'<thead>'
                f'<tr>'
                f'<th>DATE &amp; TIME (UK)</th>'
                f'<th>TICKER</th>'
                f'<th style="text-align: center;">SIGNAL DCA</th>'
                f'<th style="text-align: center;">SIGNAL TYPE</th>'
                f'<th>ACTION</th>'
                f'<th>SIGNAL PRICE</th>'
                f'<th>SINCE SIGNAL</th>'
                f'<th>SIGNAL METRICS (1D)</th>'
                f'</tr>'
                f'</thead>'
                f'<tbody>{body_html}</tbody>'
                f'</table>'
                f'</div>'
            )
            st.markdown(alert_table_html, unsafe_allow_html=True)
        else:
            st.info(
                f"No Confirmed Buy or Ghost Capitulation signals fired in '{lookback_choice}' for this filter. "
                "Switch 'Lookback Window' to Last 1 Month, Last 1 Year, or Full 2 Years to inspect historical signals."
            )

# Run the live auto-refreshing dashboard
render_live_dashboard()
