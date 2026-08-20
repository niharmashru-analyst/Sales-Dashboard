import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
from datetime import datetime

st.set_page_config(page_title="MT Channel Sales Dashboard", layout="wide", page_icon="📊")

# Branded splash — shown while THIS script runs (data load, enrich, etc.)
# Note: this can't cover Render's own cold-start gap (~30-60s) before your app
# process has even started — that part is controlled by Render's infrastructure,
# not by any code here, so nothing renders in the browser during it. This splash
# covers the moment right after your app wakes up and starts running.
_splash = st.empty()
_splash.markdown("""
<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
            height:60vh;gap:14px;">
  <div style="font-size:2.2rem;">📊</div>
  <div style="font-size:1.1rem;color:#e0a3c4;font-weight:600;">Loading MT Sales Dashboard…</div>
  <div style="font-size:0.85rem;color:#b8a3ae;">Pulling your latest data together</div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# THEME — Black & Plum
# ============================================================
COLORS = {
    "bg": "#0e0a0d",
    "bg_secondary": "#181117",
    "card": "#1f1620",
    "border": "#3a2530",
    "plum_deep": "#4a1f38",
    "plum": "#7a3457",
    "plum_light": "#a85c85",
    "plum_accent": "#e0a3c4",
    "text": "#f3ecf0",
    "text_muted": "#b8a3ae",
    "green": "#5fd68f",
    "red": "#f0668c",
    "amber": "#f0c169",
}

PLUM_SEQUENCE = ["#e0a3c4", "#a85c85", "#f0c169", "#7a3457", "#5fd68f",
                  "#c98cae", "#f0668c", "#4a1f38", "#8ecae6", "#d1859f"]

import plotly.io as pio
pio.templates.default = "plotly_dark"
px.defaults.color_discrete_sequence = PLUM_SEQUENCE
px.defaults.color_continuous_scale = ["#3a2530", "#7a3457", "#a85c85", "#e0a3c4"]

# Dark-friendly gradient for dataframe cell highlighting — pure Python, no
# matplotlib needed (avoids it as a deploy dependency entirely). Interpolates
# between dark card color and plum accent based on each value's percentile.
def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def _lerp_color(c1, c2, t):
    r = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
    return f"#{r[0]:02x}{r[1]:02x}{r[2]:02x}"

def dark_gradient(series, low="#241a22", high="#e0a3c4"):
    """Return a list of 'background-color: #xxxxxx' CSS strings, one per value,
    for use with Styler.apply(..., subset=[...]). Drop-in alternative to
    Styler.background_gradient() that doesn't require matplotlib."""
    c1, c2 = _hex_to_rgb(low), _hex_to_rgb(high)
    vals = pd.to_numeric(series, errors="coerce")
    vmin, vmax = vals.min(), vals.max()
    styles = []
    for v in vals:
        if pd.isna(v) or vmax == vmin:
            styles.append("")
        else:
            t = (v - vmin) / (vmax - vmin)
            styles.append(f"background-color: {_lerp_color(c1, c2, t)}; color: #f3ecf0;")
    return styles

st.markdown(f"""
<style>
    .stApp {{
        background-color: {COLORS['bg']};
        color: {COLORS['text']};
    }}
    section[data-testid="stSidebar"] {{
        background-color: {COLORS['bg_secondary']};
        border-right: 1px solid {COLORS['border']};
    }}
    section[data-testid="stSidebar"] * {{
        color: {COLORS['text']} !important;
    }}
    h1, h2, h3, h4, h5, h6 {{
        color: {COLORS['text']} !important;
        font-weight: 600;
    }}
    h1 {{
        background: linear-gradient(90deg, {COLORS['plum_accent']}, {COLORS['plum_light']});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        padding-bottom: 4px;
    }}
    p, span, label, div {{
        color: {COLORS['text']};
    }}
    [data-testid="stMetric"] {{
        background-color: {COLORS['card']};
        border: 1px solid {COLORS['border']};
        border-left: 3px solid {COLORS['plum_light']};
        border-radius: 10px;
        padding: 16px 18px;
    }}
    [data-testid="stMetricLabel"] {{
        color: {COLORS['text_muted']} !important;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }}
    [data-testid="stMetricValue"] {{
        color: {COLORS['plum_accent']} !important;
        font-weight: 700;
    }}
    /* Sidebar page navigation (radio list) */
    section[data-testid="stSidebar"] div[role="radiogroup"] {{
        gap: 2px;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label {{
        background-color: transparent;
        border-radius: 8px;
        padding: 8px 10px;
        margin: 0;
        width: 100%;
        transition: background-color 0.15s ease;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{
        background-color: {COLORS['card']} !important;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] {{
        background-color: {COLORS['plum']} !important;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] input[type="radio"] {{
        accent-color: {COLORS['plum_accent']};
    }}
    .stButton > button {{
        background-color: {COLORS['plum']};
        color: {COLORS['text']};
        border: 1px solid {COLORS['plum_light']};
        border-radius: 8px;
        font-weight: 500;
    }}
    .stButton > button:hover {{
        background-color: {COLORS['plum_light']};
        border-color: {COLORS['plum_accent']};
        color: {COLORS['bg']};
    }}
    .stDataFrame {{
        border: 1px solid {COLORS['border']};
        border-radius: 10px;
        overflow: hidden;
    }}
    div[data-baseweb="select"] > div {{
        background-color: {COLORS['card']};
        border-color: {COLORS['border']};
    }}
    .stExpander {{
        border: 1px solid {COLORS['border']} !important;
        border-radius: 10px !important;
        background-color: {COLORS['card']};
    }}
    hr {{
        border-color: {COLORS['border']};
    }}
    .block-container {{
        padding-top: 2rem;
    }}
    .stAlert {{
        background-color: {COLORS['card']};
        border: 1px solid {COLORS['border']};
        border-radius: 10px;
    }}
    /* Text / number / date inputs */
    .stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea {{
        background-color: {COLORS['card']} !important;
        color: {COLORS['text']} !important;
        border: 1px solid {COLORS['border']} !important;
        border-radius: 8px !important;
    }}
    .stTextInput input:focus, .stNumberInput input:focus {{
        border-color: {COLORS['plum_accent']} !important;
        box-shadow: 0 0 0 1px {COLORS['plum_accent']} !important;
    }}
    /* File uploader */
    [data-testid="stFileUploaderDropzone"] {{
        background-color: {COLORS['card']} !important;
        border: 1px dashed {COLORS['border']} !important;
        border-radius: 10px !important;
    }}
    [data-testid="stFileUploaderDropzone"] * {{
        color: {COLORS['text_muted']} !important;
    }}
    [data-testid="stFileUploaderDropzone"] button {{
        background-color: {COLORS['plum']} !important;
        color: {COLORS['text']} !important;
        border: 1px solid {COLORS['plum_light']} !important;
    }}
    [data-testid="stFileUploaderFile"] {{
        background-color: {COLORS['bg_secondary']} !important;
        color: {COLORS['text']} !important;
    }}
    /* Multiselect / selectbox chips & menus */
    [data-baseweb="tag"] {{
        background-color: {COLORS['plum']} !important;
        color: {COLORS['text']} !important;
    }}
    [data-baseweb="popover"] li {{
        background-color: {COLORS['card']} !important;
        color: {COLORS['text']} !important;
    }}
    [data-baseweb="menu"] {{
        background-color: {COLORS['card']} !important;
    }}
    /* Slider */
    [data-testid="stSlider"] [role="slider"] {{
        background-color: {COLORS['plum_accent']} !important;
    }}
    .stSlider [data-baseweb="slider"] > div > div {{
        background: {COLORS['plum']} !important;
    }}
    /* Dataframe header */
    [data-testid="stDataFrame"] div[role="columnheader"] {{
        background-color: {COLORS['bg_secondary']} !important;
        color: {COLORS['plum_accent']} !important;
    }}
    /* Tabs overflow scroller arrow buttons */
    .stTabs button[kind="header"] {{
        background-color: {COLORS['card']} !important;
        color: {COLORS['text']} !important;
    }}
    /* Cards get subtle shadow + hover lift */
    [data-testid="stMetric"], .stExpander, [data-testid="stFileUploaderDropzone"] {{
        box-shadow: 0 2px 10px rgba(0,0,0,0.35);
    }}
    /* Top decorative bar */
    div[data-testid="stDecoration"] {{
        background: linear-gradient(90deg, {COLORS['plum_deep']}, {COLORS['plum_light']}, {COLORS['plum_deep']});
    }}
    /* Checkbox */
    .stCheckbox svg {{
        color: {COLORS['plum_accent']} !important;
    }}
</style>
""", unsafe_allow_html=True)


def style_fig(fig):
    fig.update_layout(
        paper_bgcolor=COLORS["bg"],
        plot_bgcolor=COLORS["bg"],
        font_color=COLORS["text"],
        colorway=PLUM_SEQUENCE,
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=40, l=10, r=10, b=10),
    )
    fig.update_xaxes(gridcolor=COLORS["border"], zerolinecolor=COLORS["border"])
    fig.update_yaxes(gridcolor=COLORS["border"], zerolinecolor=COLORS["border"])
    return fig


# ============================================================
# PERSISTENT MONTHLY DATA STORE
# ============================================================
DATA_DIR = "data"
MASTER_PATH = os.path.join(DATA_DIR, "mt_master_data.csv")
os.makedirs(DATA_DIR, exist_ok=True)

REQUIRED_COLS = [
    "Chain Code", "Chain Name", "Outlet Code", "Outlet Name", "SKU Code",
    "SKU Name", "Category", "Net Qty", "Net Sales", "Last Year Sales",
    "This Year Sales", "Primary Sales", "Tertiary Sales", "Closing Stock",
]


def validate(df):
    return [c for c in REQUIRED_COLS if c not in df.columns]


def load_master():
    if os.path.exists(MASTER_PATH):
        return pd.read_csv(MASTER_PATH)
    return pd.DataFrame()


def save_master(df):
    df.to_csv(MASTER_PATH, index=False)


def add_month_to_master(new_df, month_label):
    new_df = new_df.copy()
    new_df["Month"] = month_label
    new_df["Uploaded At"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    master = load_master()
    if not master.empty:
        master = master[master["Month"] != month_label]  # replace if re-uploaded
        master = pd.concat([master, new_df], ignore_index=True)
    else:
        master = new_df
    save_master(master)
    return master


def delete_month(month_label):
    master = load_master()
    master = master[master["Month"] != month_label]
    save_master(master)
    return master


def read_uploaded_excel(uploaded, sales_sheet="Sales Data", mrp_sheet="MRP Master"):
    xls = pd.ExcelFile(uploaded)
    sales_sheet_actual = sales_sheet if sales_sheet in xls.sheet_names else xls.sheet_names[0]
    df = pd.read_excel(xls, sheet_name=sales_sheet_actual)
    mrp_df = None
    if mrp_sheet in xls.sheet_names:
        mrp_df = pd.read_excel(xls, sheet_name=mrp_sheet)
    elif len(xls.sheet_names) > 1:
        mrp_df = pd.read_excel(xls, sheet_name=xls.sheet_names[1])
    if mrp_df is not None and "SKU Code" in mrp_df.columns and "MRP" in mrp_df.columns:
        df = df.merge(mrp_df[["SKU Code", "MRP"]], on="SKU Code", how="left")
    return df


def enrich(df):
    df = df.copy()
    for c in ["Net Qty", "Net Sales", "Last Year Sales", "This Year Sales",
              "Primary Sales", "Tertiary Sales", "Closing Stock"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    df["YoY Growth %"] = np.where(
        df["Last Year Sales"] > 0,
        (df["This Year Sales"] - df["Last Year Sales"]) / df["Last Year Sales"] * 100,
        np.nan,
    )
    df["Sell-Through %"] = np.where(
        df["Primary Sales"] > 0, df["Tertiary Sales"] / df["Primary Sales"] * 100, np.nan
    )
    df["Primary-Tertiary Gap"] = df["Primary Sales"] - df["Tertiary Sales"]
    df["Realized Price"] = np.where(df["Net Qty"] > 0, df["Net Sales"] / df["Net Qty"], np.nan)

    if "MRP" in df.columns:
        df["MRP"] = pd.to_numeric(df["MRP"], errors="coerce")
        df["Discount %"] = np.where(
            df["MRP"] > 0, (df["MRP"] - df["Realized Price"]) / df["MRP"] * 100, np.nan
        )
        df["Stock Value (MRP)"] = df["Closing Stock"] * df["MRP"]
    avg_daily = df["Net Sales"] / 365
    df["Stock Cover (Days)"] = np.where(avg_daily > 0, df["Closing Stock"] * df["Realized Price"] / avg_daily, np.nan)
    return df


def fmt_inr(x):
    if pd.isna(x):
        return "—"
    if abs(x) >= 1e7:
        return f"₹{x/1e7:.2f} Cr"
    if abs(x) >= 1e5:
        return f"₹{x/1e5:.2f} L"
    return f"₹{x:,.0f}"


def fetch_live_excel(url, month_label=None):
    """Read an Excel file directly from a public link (Google Sheets 'publish as .xlsx',
    OneDrive/Dropbox direct-download link, or any other direct .xlsx URL)."""
    df = read_uploaded_excel(url)
    if month_label:
        df["Month"] = month_label
    return df


# ============================================================
# SIDEBAR — MONTHLY DATA MANAGER
# ============================================================
st.sidebar.title("📊 MT Sales Dashboard")

with st.sidebar.expander("📥 Add / Manage Monthly Data", expanded=False):
    ADMIN_PASSWORD = st.secrets.get("admin_password", "changeme123") if hasattr(st, "secrets") else "changeme123"

    if "admin_unlocked" not in st.session_state:
        st.session_state.admin_unlocked = False

    if not st.session_state.admin_unlocked:
        st.caption("🔒 This section is restricted to admins.")
        pw_input = st.text_input("Enter admin password", type="password", key="admin_pw_input")
        if st.button("Unlock"):
            if pw_input == ADMIN_PASSWORD:
                st.session_state.admin_unlocked = True
                st.rerun()
            else:
                st.error("Incorrect password.")
    else:
        if st.button("🔓 Lock admin section"):
            st.session_state.admin_unlocked = False
            st.rerun()

        st.caption("Add each month's data below — it's appended to a running history, old months are kept.")

        add_mode = st.radio("Add this month's data via:", ["📎 Upload file", "🔗 Live Excel link"], horizontal=False)
        month_pick = st.text_input("Month label (e.g. Aug 2026)", value=datetime.now().strftime("%b %Y"))

        new_df = None
        if add_mode == "📎 Upload file":
            monthly_file = st.file_uploader("Upload this month's .xlsx", type=["xlsx"], key="monthly_upload")
            if monthly_file is not None:
                try:
                    new_df = read_uploaded_excel(monthly_file)
                except Exception as e:
                    st.error(f"Could not read file: {e}")
        else:
            st.caption("Paste a direct link to a live Excel file — a Google Sheet published as .xlsx "
                       "(File → Share → Publish to web → .xlsx), or a OneDrive/Dropbox direct-download link.")
            live_url = st.text_input("Live Excel link", key="live_url_input")
            if live_url and st.button("⬇️ Fetch from link"):
                try:
                    new_df = read_uploaded_excel(live_url)
                    st.session_state["_fetched_df"] = new_df
                    st.success(f"Fetched {len(new_df):,} rows. Review below, then click 'Add to database'.")
                except Exception as e:
                    st.error(f"Could not fetch that link: {e}")
            new_df = st.session_state.get("_fetched_df")

        if new_df is not None and st.button("➕ Add to database"):
            try:
                missing = validate(new_df)
                if missing:
                    st.error(f"Missing required columns: {missing}")
                elif not month_pick.strip():
                    st.error("Please give this upload a month label first.")
                else:
                    add_month_to_master(new_df, month_pick.strip())
                    st.success(f"Added {len(new_df):,} rows for '{month_pick.strip()}' to the database.")
                    st.session_state.pop("_fetched_df", None)
                    st.cache_data.clear()
            except Exception as e:
                st.error(f"Could not process data: {e}")

        st.markdown("---")
        master_preview = load_master()
        if not master_preview.empty:
            month_summary = master_preview.groupby("Month").size().reset_index(name="Rows")
            st.caption("**Months currently stored:**")
            st.dataframe(month_summary, use_container_width=True, hide_index=True)

            del_month = st.selectbox("Remove a month", ["—"] + sorted(master_preview["Month"].unique().tolist()))
            if del_month != "—" and st.button("🗑️ Delete this month's data"):
                delete_month(del_month)
                st.success(f"Deleted '{del_month}'.")
                st.cache_data.clear()
                st.rerun()

            csv_bytes = master_preview.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download full history (backup)", csv_bytes,
                                file_name="mt_master_data_backup.csv", mime="text/csv")
            st.caption("⚠️ **On Render's Free plan, this saved history does NOT survive the app going to "
                       "sleep** — free instances wipe their local disk every time they spin down from "
                       "inactivity (not just on redeploys). Two ways around it: (1) upgrade to a paid "
                       "Render instance + attach a Persistent Disk, so this file survives, or (2) use the "
                       "'🔗 Live Excel link' option above each time instead of uploads, and keep your true "
                       "master copy in a Google Sheet — that way the data always lives outside Render and "
                       "nothing is lost on sleep. Either way, download a backup here regularly as a safety net.")

            restore_file = st.file_uploader("Restore from a backup .csv", type=["csv"], key="restore_upload")

            if restore_file is not None and st.button("♻️ Restore this backup"):
                restored = pd.read_csv(restore_file)
                save_master(restored)
                st.success("Restored from backup.")
                st.cache_data.clear()
                st.rerun()
        else:
            st.info("No data stored yet — upload your first month's file above.")

# ============================================================
# LOAD DATA FROM STORE
# ============================================================
master_df = load_master()

if master_df.empty:
    _splash.empty()
    st.title("Modern Trade (MT) Channel — Sales & Distribution Dashboard")
    st.info("👈 No data yet. Open **'Add / Manage Monthly Data'** in the sidebar and upload your first "
            "month's Excel file to get started.")
    st.stop()

missing_cols = validate(master_df)
if missing_cols:
    _splash.empty()
    st.error(f"Stored data is missing required columns: {missing_cols}")
    st.stop()

df = enrich(master_df)
has_mrp = "MRP" in df.columns and df["MRP"].notna().any()
has_chain_type = "Chain Type" in df.columns and df["Chain Type"].notna().any()

# ============================================================
# SIDEBAR — PAGE NAVIGATION (replaces top tabs)
# ============================================================
tab_labels = ["🏠 Executive Summary"]
if has_chain_type:
    tab_labels.append("⚖️ Grocery vs Beauty/Pharma")
tab_labels += [
    "🏢 Chain Performance",
    "🏪 Outlet Performance",
    "📦 Category & SKU",
    "🔄 Distribution Health",
    "📊 Inventory & Stock",
    "💰 Pricing & Discount" if has_mrp else "💰 Pricing (needs MRP)",
    "🔍 Diagnostics & Exceptions",
]
_off = 1 if has_chain_type else 0

st.sidebar.markdown("### 📑 Pages")
page = st.sidebar.radio("Navigate", tab_labels, label_visibility="collapsed")

# ============================================================
# SIDEBAR — FILTERS
# ============================================================
st.sidebar.markdown("### Filters")

months_sorted = sorted(df["Month"].unique().tolist())
months_sel = st.sidebar.multiselect("Month", months_sorted, default=months_sorted)
df_f = df[df["Month"].isin(months_sel)] if months_sel else df

if has_chain_type:
    ctype_sel = st.sidebar.multiselect("Chain Type", sorted(df_f["Chain Type"].unique()), default=None)
    df_f = df_f[df_f["Chain Type"].isin(ctype_sel)] if ctype_sel else df_f

chains_sel = st.sidebar.multiselect("Chain", sorted(df_f["Chain Name"].unique()), default=None)
df_f = df_f[df_f["Chain Name"].isin(chains_sel)] if chains_sel else df_f

outlet_opts = sorted(df_f["Outlet Name"].unique())
outlets_sel = st.sidebar.multiselect("Outlet", outlet_opts, default=None)
df_f = df_f[df_f["Outlet Name"].isin(outlets_sel)] if outlets_sel else df_f

cat_opts = sorted(df_f["Category"].unique())
cats_sel = st.sidebar.multiselect("Category", cat_opts, default=None)
df_f = df_f[df_f["Category"].isin(cats_sel)] if cats_sel else df_f

if df_f.empty:
    _splash.empty()
    st.warning("No data matches the selected filters.")
    st.stop()

st.sidebar.markdown("---")
st.sidebar.caption(f"Rows loaded: {len(df):,} | After filters: {len(df_f):,} | Months stored: {len(months_sorted)}")

# ============================================================
# HEADER
# ============================================================
_splash.empty()
st.title("Modern Trade (MT) Channel — Sales & Distribution Dashboard")
st.caption(f"Chain → Outlet → SKU level performance, distribution health, inventory & pricing  •  **{page}**")

# ------------------------------------------------------------
# PAGE: EXECUTIVE SUMMARY
# ------------------------------------------------------------
if page == tab_labels[0]:
    total_sales = df_f["Net Sales"].sum()
    total_qty = df_f["Net Qty"].sum()
    ly_total = df_f["Last Year Sales"].sum()
    ty_total = df_f["This Year Sales"].sum()
    yoy = (ty_total - ly_total) / ly_total * 100 if ly_total else np.nan
    sell_through = df_f["Tertiary Sales"].sum() / df_f["Primary Sales"].sum() * 100 if df_f["Primary Sales"].sum() else np.nan
    avg_cover = df_f["Stock Cover (Days)"].replace([np.inf, -np.inf], np.nan).mean()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Net Sales", fmt_inr(total_sales))
    c2.metric("Net Qty", f"{total_qty:,.0f}")
    c3.metric("YoY Growth", f"{yoy:,.1f}%" if pd.notna(yoy) else "—")
    c4.metric("Sell-Through Rate", f"{sell_through:,.1f}%" if pd.notna(sell_through) else "—")
    c5.metric("Avg Stock Cover", f"{avg_cover:,.0f} days" if pd.notna(avg_cover) else "—")

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Sales by Chain")
        chain_sales = df_f.groupby("Chain Name", as_index=False)["Net Sales"].sum().sort_values("Net Sales", ascending=False)
        fig = px.bar(chain_sales, x="Chain Name", y="Net Sales", text_auto=".2s", color="Chain Name")
        fig.update_layout(showlegend=False, yaxis_title="Net Sales")
        st.plotly_chart(style_fig(fig), use_container_width=True)
    with col2:
        st.subheader("Sales Mix by Category")
        cat_sales = df_f.groupby("Category", as_index=False)["Net Sales"].sum()
        fig = px.pie(cat_sales, names="Category", values="Net Sales", hole=0.45)
        st.plotly_chart(style_fig(fig), use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.subheader("Monthly Sales Trend")
        month_trend = df_f.groupby("Month", as_index=False)["Net Sales"].sum()
        fig = px.line(month_trend, x="Month", y="Net Sales", markers=True)
        fig.update_traces(line_color=COLORS["plum_accent"])
        st.plotly_chart(style_fig(fig), use_container_width=True)
    with col4:
        st.subheader("Top 5 / Bottom 5 Chains by YoY Growth")
        chain_yoy = df_f.groupby("Chain Name").agg(
            LY=("Last Year Sales", "sum"), TY=("This Year Sales", "sum")
        ).reset_index()
        chain_yoy["YoY %"] = (chain_yoy["TY"] - chain_yoy["LY"]) / chain_yoy["LY"] * 100
        chain_yoy = chain_yoy.sort_values("YoY %", ascending=False)
        fig = px.bar(chain_yoy, x="YoY %", y="Chain Name", orientation="h", color="YoY %",
                     color_continuous_scale=["#f0668c", "#3a2530", "#5fd68f"])
        st.plotly_chart(style_fig(fig), use_container_width=True)

# ------------------------------------------------------------
# TAB (optional): CHAIN TYPE COMPARISON
# ------------------------------------------------------------
if has_chain_type:
    if page == tab_labels[1]:
        st.subheader("Grocery MT vs Beauty & Pharma MT — Side by Side")
        ct_tbl = df_f.groupby("Chain Type").agg(
            Chains=("Chain Code", "nunique"), Outlets=("Outlet Code", "nunique"),
            Net_Sales=("Net Sales", "sum"), Net_Qty=("Net Qty", "sum"),
            LY_Sales=("Last Year Sales", "sum"), TY_Sales=("This Year Sales", "sum"),
            Primary=("Primary Sales", "sum"), Tertiary=("Tertiary Sales", "sum"),
            Closing_Stock=("Closing Stock", "sum"),
        ).reset_index()
        ct_tbl["YoY %"] = (ct_tbl["TY_Sales"] - ct_tbl["LY_Sales"]) / ct_tbl["LY_Sales"] * 100
        ct_tbl["Sell-Through %"] = ct_tbl["Tertiary"] / ct_tbl["Primary"] * 100
        ct_tbl["Avg Sales / Outlet"] = ct_tbl["Net_Sales"] / ct_tbl["Outlets"]
        if has_mrp:
            ct_disc = df_f.groupby("Chain Type")["Discount %"].mean()
            ct_tbl["Avg Discount %"] = ct_tbl["Chain Type"].map(ct_disc)

        cols = st.columns(len(ct_tbl))
        for i, row in ct_tbl.iterrows():
            with cols[i]:
                st.markdown(f"#### {row['Chain Type']}")
                st.metric("Net Sales", fmt_inr(row["Net_Sales"]))
                st.metric("YoY Growth", f"{row['YoY %']:.1f}%")
                st.metric("Sell-Through", f"{row['Sell-Through %']:.1f}%")
                if has_mrp:
                    st.metric("Avg Discount", f"{row['Avg Discount %']:.1f}%")

        st.markdown("---")
        fmt_map = {
            "Net_Sales": "{:,.0f}", "Net_Qty": "{:,.0f}", "LY_Sales": "{:,.0f}", "TY_Sales": "{:,.0f}",
            "Primary": "{:,.0f}", "Tertiary": "{:,.0f}", "Closing_Stock": "{:,.0f}",
            "YoY %": "{:.1f}%", "Sell-Through %": "{:.1f}%", "Avg Sales / Outlet": "{:,.0f}",
        }
        if has_mrp:
            fmt_map["Avg Discount %"] = "{:.1f}%"
        st.dataframe(ct_tbl.style.format(fmt_map), use_container_width=True, hide_index=True)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Net Sales: Grocery vs Beauty/Pharma")
            fig = px.bar(ct_tbl, x="Chain Type", y="Net_Sales", color="Chain Type", text_auto=".2s")
            fig.update_layout(showlegend=False)
            st.plotly_chart(style_fig(fig), use_container_width=True)
        with col2:
            st.subheader("YoY Growth % Comparison")
            fig = px.bar(ct_tbl, x="Chain Type", y="YoY %", color="Chain Type", text_auto=".1f")
            fig.update_layout(showlegend=False)
            st.plotly_chart(style_fig(fig), use_container_width=True)

        col3, col4 = st.columns(2)
        with col3:
            st.subheader("Sell-Through Rate Comparison")
            fig = px.bar(ct_tbl, x="Chain Type", y="Sell-Through %", color="Chain Type", text_auto=".1f")
            fig.add_hline(y=100, line_dash="dash", line_color=COLORS["text_muted"])
            fig.update_layout(showlegend=False)
            st.plotly_chart(style_fig(fig), use_container_width=True)
        with col4:
            st.subheader("Category Mix by Chain Type")
            mix = df_f.groupby(["Chain Type", "Category"])["Net Sales"].sum().reset_index()
            fig = px.bar(mix, x="Chain Type", y="Net Sales", color="Category", barmode="stack")
            st.plotly_chart(style_fig(fig), use_container_width=True)

        st.subheader("Same SKU, Different Channel — Performance Comparison")
        st.caption("Pick a SKU sold in both chain types to compare how it performs across Grocery vs Beauty/Pharma MT.")
        common_skus = df_f.groupby("SKU Name")["Chain Type"].nunique()
        common_skus = common_skus[common_skus > 1].index.tolist()
        if common_skus:
            sku_pick2 = st.selectbox("Select SKU (sold in both channel types)", sorted(common_skus), key="ct_sku_pick")
            sku_ct = df_f[df_f["SKU Name"] == sku_pick2].groupby("Chain Type").agg(
                Net_Sales=("Net Sales", "sum"), Net_Qty=("Net Qty", "sum"),
                Sell_Through=("Sell-Through %", "mean"), YoY=("YoY Growth %", "mean"),
            ).reset_index()
            st.dataframe(sku_ct.style.format({
                "Net_Sales": "{:,.0f}", "Net_Qty": "{:,.0f}", "Sell_Through": "{:.1f}%", "YoY": "{:.1f}%",
            }), use_container_width=True, hide_index=True)
        else:
            st.info("No common SKUs found across both chain types in the current filter selection.")

# ------------------------------------------------------------
# TAB 2: CHAIN PERFORMANCE
# ------------------------------------------------------------
if page == tab_labels[1 + _off]:
    st.subheader("Chain-wise Scorecard")
    chain_tbl = df_f.groupby(["Chain Code", "Chain Name"]).agg(
        Outlets=("Outlet Code", "nunique"), Net_Sales=("Net Sales", "sum"), Net_Qty=("Net Qty", "sum"),
        LY_Sales=("Last Year Sales", "sum"), TY_Sales=("This Year Sales", "sum"),
        Primary=("Primary Sales", "sum"), Tertiary=("Tertiary Sales", "sum"),
    ).reset_index()
    chain_tbl["YoY %"] = (chain_tbl["TY_Sales"] - chain_tbl["LY_Sales"]) / chain_tbl["LY_Sales"] * 100
    chain_tbl["Sell-Through %"] = chain_tbl["Tertiary"] / chain_tbl["Primary"] * 100
    chain_tbl["Avg Sales / Outlet"] = chain_tbl["Net_Sales"] / chain_tbl["Outlets"]
    chain_tbl = chain_tbl.sort_values("Net_Sales", ascending=False)

    st.dataframe(
        chain_tbl.style.format({
            "Net_Sales": "{:,.0f}", "Net_Qty": "{:,.0f}", "LY_Sales": "{:,.0f}", "TY_Sales": "{:,.0f}",
            "Primary": "{:,.0f}", "Tertiary": "{:,.0f}", "YoY %": "{:.1f}%",
            "Sell-Through %": "{:.1f}%", "Avg Sales / Outlet": "{:,.0f}",
        }).apply(dark_gradient, subset=["YoY %"]),
        use_container_width=True, hide_index=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Chain Growth vs Value Quadrant")
        fig = px.scatter(
            chain_tbl, x="Net_Sales", y="YoY %", size="Outlets", color="Chain Name",
            text="Chain Name", labels={"Net_Sales": "Net Sales (Value)", "YoY %": "YoY Growth %"},
        )
        fig.add_hline(y=chain_tbl["YoY %"].mean(), line_dash="dash", line_color=COLORS["text_muted"])
        fig.add_vline(x=chain_tbl["Net_Sales"].mean(), line_dash="dash", line_color=COLORS["text_muted"])
        fig.update_traces(textposition="top center")
        st.plotly_chart(style_fig(fig), use_container_width=True)
    with col2:
        st.subheader("Category Penetration by Chain")
        pen = df_f.groupby(["Chain Name", "Category"])["Net Sales"].sum().reset_index()
        fig = px.treemap(pen, path=["Chain Name", "Category"], values="Net Sales")
        st.plotly_chart(style_fig(fig), use_container_width=True)

# ------------------------------------------------------------
# TAB 3: OUTLET PERFORMANCE
# ------------------------------------------------------------
if page == tab_labels[2 + _off]:
    st.subheader("Outlet Scorecard")
    out_tbl = df_f.groupby(["Chain Name", "Outlet Code", "Outlet Name"]).agg(
        Net_Sales=("Net Sales", "sum"), LY_Sales=("Last Year Sales", "sum"), TY_Sales=("This Year Sales", "sum"),
        Primary=("Primary Sales", "sum"), Tertiary=("Tertiary Sales", "sum"),
        Stock_Cover=("Stock Cover (Days)", "mean"), SKUs=("SKU Code", "nunique"),
    ).reset_index()
    out_tbl["YoY %"] = (out_tbl["TY_Sales"] - out_tbl["LY_Sales"]) / out_tbl["LY_Sales"] * 100
    out_tbl["Sell-Through %"] = out_tbl["Tertiary"] / out_tbl["Primary"] * 100

    def segment(row):
        if row["YoY %"] >= 15 and row["Sell-Through %"] >= 85:
            return "⭐ Star"
        elif row["YoY %"] >= 0:
            return "📈 Growing"
        elif row["Sell-Through %"] < 70:
            return "⚠️ At Risk"
        else:
            return "📉 Declining"

    out_tbl["Segment"] = out_tbl.apply(segment, axis=1)
    out_tbl = out_tbl.sort_values("Net_Sales", ascending=False)

    seg_filter = st.multiselect("Filter by segment", out_tbl["Segment"].unique().tolist())
    show_tbl = out_tbl[out_tbl["Segment"].isin(seg_filter)] if seg_filter else out_tbl

    st.dataframe(
        show_tbl.style.format({
            "Net_Sales": "{:,.0f}", "LY_Sales": "{:,.0f}", "TY_Sales": "{:,.0f}",
            "Primary": "{:,.0f}", "Tertiary": "{:,.0f}", "YoY %": "{:.1f}%",
            "Sell-Through %": "{:.1f}%", "Stock_Cover": "{:.0f} days",
        }).apply(dark_gradient, subset=["YoY %"]),
        use_container_width=True, hide_index=True, height=400,
    )

    st.subheader("Segment Distribution")
    seg_count = out_tbl["Segment"].value_counts().reset_index()
    seg_count.columns = ["Segment", "Outlets"]
    fig = px.bar(seg_count, x="Segment", y="Outlets", color="Segment", text_auto=True)
    st.plotly_chart(style_fig(fig), use_container_width=True)

# ------------------------------------------------------------
# TAB 4: CATEGORY & SKU
# ------------------------------------------------------------
if page == tab_labels[3 + _off]:
    st.subheader("Category Performance")
    cat_tbl = df_f.groupby("Category").agg(
        Net_Sales=("Net Sales", "sum"), LY_Sales=("Last Year Sales", "sum"),
        TY_Sales=("This Year Sales", "sum"), Primary=("Primary Sales", "sum"), Tertiary=("Tertiary Sales", "sum"),
    ).reset_index()
    cat_tbl["YoY %"] = (cat_tbl["TY_Sales"] - cat_tbl["LY_Sales"]) / cat_tbl["LY_Sales"] * 100
    cat_tbl["Sell-Through %"] = cat_tbl["Tertiary"] / cat_tbl["Primary"] * 100
    cat_tbl["Share %"] = cat_tbl["Net_Sales"] / cat_tbl["Net_Sales"].sum() * 100
    cat_tbl = cat_tbl.sort_values("Net_Sales", ascending=False)
    st.dataframe(
        cat_tbl.style.format({
            "Net_Sales": "{:,.0f}", "LY_Sales": "{:,.0f}", "TY_Sales": "{:,.0f}",
            "Primary": "{:,.0f}", "Tertiary": "{:,.0f}", "YoY %": "{:.1f}%",
            "Sell-Through %": "{:.1f}%", "Share %": "{:.1f}%",
        }), use_container_width=True, hide_index=True,
    )

    st.markdown("---")
    st.subheader("SKU Pareto (80/20) — Top SKUs by Sales")
    sku_tbl = df_f.groupby(["SKU Code", "SKU Name", "Category"]).agg(
        Net_Sales=("Net Sales", "sum"), Net_Qty=("Net Qty", "sum"),
        LY_Sales=("Last Year Sales", "sum"), TY_Sales=("This Year Sales", "sum"), Outlets=("Outlet Code", "nunique"),
    ).reset_index().sort_values("Net_Sales", ascending=False)
    sku_tbl["YoY %"] = (sku_tbl["TY_Sales"] - sku_tbl["LY_Sales"]) / sku_tbl["LY_Sales"] * 100
    sku_tbl["Cum Share %"] = sku_tbl["Net_Sales"].cumsum() / sku_tbl["Net_Sales"].sum() * 100

    fig = go.Figure()
    fig.add_bar(x=sku_tbl["SKU Name"], y=sku_tbl["Net_Sales"], name="Net Sales", marker_color=COLORS["plum_light"])
    fig.add_trace(go.Scatter(x=sku_tbl["SKU Name"], y=sku_tbl["Cum Share %"], name="Cumulative %",
                              yaxis="y2", line=dict(color=COLORS["amber"])))
    fig.update_layout(
        yaxis=dict(title="Net Sales"),
        yaxis2=dict(title="Cumulative %", overlaying="y", side="right", range=[0, 105]),
        xaxis=dict(tickangle=-45), height=450,
    )
    st.plotly_chart(style_fig(fig), use_container_width=True)

    st.subheader("SKU Movement: Growing vs Declining")
    def move_seg(v):
        if pd.isna(v): return "No LY data"
        if v > 10: return "Growing"
        if v < -10: return "Declining"
        return "Stable"
    sku_tbl["Movement"] = sku_tbl["YoY %"].apply(move_seg)
    move_count = sku_tbl["Movement"].value_counts().reset_index()
    move_count.columns = ["Movement", "SKU Count"]
    fig = px.pie(move_count, names="Movement", values="SKU Count", hole=0.45, color="Movement",
                 color_discrete_map={"Growing": COLORS["green"], "Declining": COLORS["red"],
                                      "Stable": COLORS["text_muted"], "No LY data": COLORS["border"]})
    st.plotly_chart(style_fig(fig), use_container_width=True)

    with st.expander("Full SKU table"):
        st.dataframe(sku_tbl.style.format({
            "Net_Sales": "{:,.0f}", "Net_Qty": "{:,.0f}", "LY_Sales": "{:,.0f}",
            "TY_Sales": "{:,.0f}", "YoY %": "{:.1f}%",
        }), use_container_width=True, hide_index=True)

# ------------------------------------------------------------
# TAB 5: DISTRIBUTION HEALTH
# ------------------------------------------------------------
if page == tab_labels[4 + _off]:
    st.subheader("Primary vs Tertiary Sales")
    p_total = df_f["Primary Sales"].sum()
    t_total = df_f["Tertiary Sales"].sum()
    gap = p_total - t_total
    st_rate = t_total / p_total * 100 if p_total else np.nan

    c1, c2, c3 = st.columns(3)
    c1.metric("Primary Sales", fmt_inr(p_total))
    c2.metric("Tertiary Sales", fmt_inr(t_total))
    c3.metric("Sell-Through Rate", f"{st_rate:.1f}%" if pd.notna(st_rate) else "—",
              delta=f"Gap: {fmt_inr(gap)}", delta_color="inverse")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Sell-Through Rate by Chain")
        chain_st = df_f.groupby("Chain Name").agg(P=("Primary Sales", "sum"), T=("Tertiary Sales", "sum")).reset_index()
        chain_st["Sell-Through %"] = chain_st["T"] / chain_st["P"] * 100
        fig = px.bar(chain_st.sort_values("Sell-Through %"), x="Sell-Through %", y="Chain Name",
                     orientation="h", color="Sell-Through %", color_continuous_scale=["#f0668c", "#3a2530", "#5fd68f"])
        fig.add_vline(x=100, line_dash="dash", line_color=COLORS["text_muted"])
        st.plotly_chart(style_fig(fig), use_container_width=True)
    with col2:
        st.subheader("Sell-Through Rate by Category")
        cat_st = df_f.groupby("Category").agg(P=("Primary Sales", "sum"), T=("Tertiary Sales", "sum")).reset_index()
        cat_st["Sell-Through %"] = cat_st["T"] / cat_st["P"] * 100
        fig = px.bar(cat_st.sort_values("Sell-Through %"), x="Sell-Through %", y="Category",
                     orientation="h", color="Sell-Through %", color_continuous_scale=["#f0668c", "#3a2530", "#5fd68f"])
        fig.add_vline(x=100, line_dash="dash", line_color=COLORS["text_muted"])
        st.plotly_chart(style_fig(fig), use_container_width=True)

    st.subheader("⚠️ Channel Stuffing Watch — High Primary, Low Sell-Through")
    st.caption("Outlets/SKUs where a lot of stock is being pushed in but not sold out. Investigate for over-supply.")
    stuff = df_f[(df_f["Primary Sales"] > df_f["Primary Sales"].median()) & (df_f["Sell-Through %"] < 70)]
    stuff = stuff[["Chain Name", "Outlet Name", "SKU Name", "Category", "Primary Sales", "Tertiary Sales", "Sell-Through %", "Closing Stock"]]
    stuff = stuff.sort_values("Primary Sales", ascending=False)
    st.dataframe(stuff.style.format({"Primary Sales": "{:,.0f}", "Tertiary Sales": "{:,.0f}",
                                      "Sell-Through %": "{:.1f}%", "Closing Stock": "{:,.0f}"}),
                 use_container_width=True, hide_index=True, height=300)

# ------------------------------------------------------------
# TAB 6: INVENTORY & STOCK
# ------------------------------------------------------------
if page == tab_labels[5 + _off]:
    st.subheader("Inventory Health Overview")
    total_stock_qty = df_f["Closing Stock"].sum()
    avg_cover = df_f["Stock Cover (Days)"].replace([np.inf, -np.inf], np.nan).mean()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Closing Stock (units)", f"{total_stock_qty:,.0f}")
    c2.metric("Avg Stock Cover", f"{avg_cover:,.0f} days" if pd.notna(avg_cover) else "—")
    if has_mrp:
        c3.metric("Inventory Value (at MRP)", fmt_inr(df_f["Stock Value (MRP)"].sum()))

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Stock Cover Distribution")
        fig = px.histogram(df_f, x="Stock Cover (Days)", nbins=30, color_discrete_sequence=[COLORS["plum_light"]])
        fig.add_vline(x=60, line_dash="dash", line_color=COLORS["red"], annotation_text="60-day threshold")
        st.plotly_chart(style_fig(fig), use_container_width=True)
    with col2:
        st.subheader("Closing Stock by Category")
        stock_cat = df_f.groupby("Category", as_index=False)["Closing Stock"].sum()
        fig = px.bar(stock_cat.sort_values("Closing Stock", ascending=False), x="Category", y="Closing Stock", color="Category")
        fig.update_layout(showlegend=False)
        st.plotly_chart(style_fig(fig), use_container_width=True)

    st.subheader("🔴 Dead Stock Report — Low/No Sell-out, Stock Sitting")
    dead = df_f[(df_f["Tertiary Sales"] < df_f["Tertiary Sales"].quantile(0.1)) & (df_f["Closing Stock"] > 0)]
    dead_cols = ["Chain Name", "Outlet Name", "SKU Name", "Category", "Tertiary Sales", "Closing Stock"]
    if has_mrp:
        dead_cols.append("Stock Value (MRP)")
    dead = dead[dead_cols].sort_values("Closing Stock", ascending=False)
    fmt_dict = {"Tertiary Sales": "{:,.0f}", "Closing Stock": "{:,.0f}"}
    if has_mrp:
        fmt_dict["Stock Value (MRP)"] = "{:,.0f}"
    st.dataframe(dead.style.format(fmt_dict), use_container_width=True, hide_index=True, height=300)

    st.subheader("🟡 Stockout Risk — High Sell-Through, Low Cover")
    risk = df_f[(df_f["Sell-Through %"] > 90) & (df_f["Stock Cover (Days)"] < 15)]
    risk = risk[["Chain Name", "Outlet Name", "SKU Name", "Category", "Sell-Through %", "Stock Cover (Days)", "Closing Stock"]]
    risk = risk.sort_values("Stock Cover (Days)")
    st.dataframe(risk.style.format({"Sell-Through %": "{:.1f}%", "Stock Cover (Days)": "{:.0f}", "Closing Stock": "{:,.0f}"}),
                 use_container_width=True, hide_index=True, height=300)

# ------------------------------------------------------------
# TAB 7: PRICING & DISCOUNT
# ------------------------------------------------------------
if page == tab_labels[6 + _off]:
    if not has_mrp:
        st.warning(
            "No MRP data found. Add an 'MRP Master' sheet with columns 'SKU Code' and 'MRP', "
            "or include an 'MRP' column in your Sales Data sheet, to unlock this tab."
        )
    else:
        st.subheader("Realized Price vs MRP")
        avg_disc = df_f["Discount %"].mean()
        c1, c2 = st.columns(2)
        c1.metric("Avg Realized Price", fmt_inr(df_f["Realized Price"].mean()))
        c2.metric("Avg Discount %", f"{avg_disc:.1f}%" if pd.notna(avg_disc) else "—")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Discount % by Chain")
            chain_disc = df_f.groupby("Chain Name", as_index=False)["Discount %"].mean().sort_values("Discount %", ascending=False)
            fig = px.bar(chain_disc, x="Chain Name", y="Discount %", color="Discount %",
                         color_continuous_scale=["#3a2530", "#e0a3c4"])
            st.plotly_chart(style_fig(fig), use_container_width=True)
        with col2:
            st.subheader("Discount % by Category")
            cat_disc = df_f.groupby("Category", as_index=False)["Discount %"].mean().sort_values("Discount %", ascending=False)
            fig = px.bar(cat_disc, x="Category", y="Discount %", color="Discount %",
                         color_continuous_scale=["#3a2530", "#e0a3c4"])
            st.plotly_chart(style_fig(fig), use_container_width=True)

        st.subheader("Price-Volume-Mix (PVM) — YoY Sales Variance Bridge")
        st.caption("Decomposes the YoY sales change into Volume+Mix effect and Discount effect (since MRP is static).")
        ly, ty = df_f["Last Year Sales"].sum(), df_f["This Year Sales"].sum()
        potential_ty_at_mrp = (df_f["Net Qty"] * df_f["MRP"]).sum()
        discount_effect = potential_ty_at_mrp - ty
        volume_effect = potential_ty_at_mrp - ly if pd.notna(potential_ty_at_mrp) else 0
        fig = go.Figure(go.Waterfall(
            orientation="v",
            measure=["absolute", "relative", "relative", "total"],
            x=["Last Year Sales", "Volume + Mix Effect", "Discount Effect", "This Year Sales"],
            y=[ly, volume_effect, -discount_effect, ty],
            connector={"line": {"color": COLORS["border"]}},
            decreasing={"marker": {"color": COLORS["red"]}},
            increasing={"marker": {"color": COLORS["green"]}},
            totals={"marker": {"color": COLORS["plum_light"]}},
        ))
        fig.update_layout(height=450, yaxis_title="Net Sales (₹)")
        st.plotly_chart(style_fig(fig), use_container_width=True)
        st.caption(
            "Volume + Mix Effect = extra sales if everything sold at full MRP (captures more units sold and "
            "shift toward higher/lower-MRP SKUs). Discount Effect = value given up by selling below MRP."
        )

        st.subheader("High Discount Outliers (>25%)")
        outliers = df_f[df_f["Discount %"] > 25][["Chain Name", "Outlet Name", "SKU Name", "MRP", "Realized Price", "Discount %"]]
        outliers = outliers.sort_values("Discount %", ascending=False)
        st.dataframe(outliers.style.format({"MRP": "{:,.0f}", "Realized Price": "{:,.0f}", "Discount %": "{:.1f}%"}),
                     use_container_width=True, hide_index=True, height=300)

# ------------------------------------------------------------
# TAB 8: DIAGNOSTICS & EXCEPTIONS
# ------------------------------------------------------------
if page == tab_labels[7 + _off]:
    st.subheader("🔍 Outlier Detection — Abnormal YoY Swings")
    threshold = st.slider("Flag SKU-outlet combinations with |YoY change| greater than (%)", 20, 200, 50)
    outliers = df_f[df_f["YoY Growth %"].abs() > threshold].copy()
    outliers = outliers[["Chain Name", "Outlet Name", "SKU Name", "Category", "Last Year Sales", "This Year Sales", "YoY Growth %"]]
    outliers = outliers.sort_values("YoY Growth %", ascending=False)
    st.dataframe(outliers.style.format({"Last Year Sales": "{:,.0f}", "This Year Sales": "{:,.0f}", "YoY Growth %": "{:.1f}%"})
                 .apply(dark_gradient, subset=["YoY Growth %"]),
                 use_container_width=True, hide_index=True, height=350)

    st.markdown("---")
    st.subheader("Cross-Chain SKU Benchmarking")
    st.caption("Compare the same SKU's performance across different chains — isolates product issues vs chain/execution issues.")
    sku_pick = st.selectbox("Select SKU", sorted(df_f["SKU Name"].unique()))
    sku_data = df_f[df_f["SKU Name"] == sku_pick]
    bench = sku_data.groupby("Chain Name").agg(
        Net_Sales=("Net Sales", "sum"), Sell_Through=("Sell-Through %", "mean"),
        YoY=("YoY Growth %", "mean"), Stock_Cover=("Stock Cover (Days)", "mean"),
    ).reset_index().sort_values("Net_Sales", ascending=False)
    st.dataframe(bench.style.format({"Net_Sales": "{:,.0f}", "Sell_Through": "{:.1f}%", "YoY": "{:.1f}%", "Stock_Cover": "{:.0f} days"}),
                 use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("New vs Lost — Zero Last Year or Zero This Year")
    new_skus = df_f[(df_f["Last Year Sales"] == 0) & (df_f["This Year Sales"] > 0)]
    lost_skus = df_f[(df_f["Last Year Sales"] > 0) & (df_f["This Year Sales"] == 0)]
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**New this year** ({len(new_skus)} rows)")
        st.dataframe(new_skus[["Chain Name", "Outlet Name", "SKU Name", "This Year Sales"]].sort_values("This Year Sales", ascending=False),
                     use_container_width=True, hide_index=True, height=250)
    with c2:
        st.markdown(f"**Lost this year** ({len(lost_skus)} rows)")
        st.dataframe(lost_skus[["Chain Name", "Outlet Name", "SKU Name", "Last Year Sales"]].sort_values("Last Year Sales", ascending=False),
                     use_container_width=True, hide_index=True, height=250)

st.markdown("---")
st.caption("Built for MT channel reporting. Add each month's file via the sidebar to keep history growing.")
