import os
import json
from io import BytesIO
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st


# ============================================================
# PAGE / THEME
# ============================================================
st.set_page_config(
    page_title="MT Command Center",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

COLORS = {
    "bg": "#07090D",
    "panel": "#0D1118",
    "panel2": "#111722",
    "border": "#202938",
    "text": "#F3F4F6",
    "muted": "#8B95A7",
    "violet": "#8B5CF6",
    "cyan": "#06B6D4",
    "green": "#22C55E",
    "amber": "#F59E0B",
    "red": "#EF4444",
    "pink": "#EC4899",
}

CHART_SEQUENCE = [
    COLORS["violet"], COLORS["cyan"], COLORS["green"],
    COLORS["amber"], COLORS["red"], COLORS["pink"],
    "#3B82F6", "#A855F7",
]

st.markdown(
    f"""
<style>
.stApp {{
    background:
      radial-gradient(circle at 10% 0%, rgba(139,92,246,.13), transparent 28%),
      radial-gradient(circle at 90% 5%, rgba(6,182,212,.08), transparent 25%),
      {COLORS["bg"]};
    color: {COLORS["text"]};
}}
section[data-testid="stSidebar"] {{
    background: #090C12;
    border-right: 1px solid {COLORS["border"]};
}}
section[data-testid="stSidebar"] {{
    min-width: 320px !important;
    width: 320px !important;
    transform: none !important;
    visibility: visible !important;
}}
section[data-testid="stSidebar"][aria-expanded="false"] {{
    min-width: 320px !important;
    width: 320px !important;
    margin-left: 0 !important;
    transform: none !important;
    visibility: visible !important;
}}
[data-testid="stSidebarCollapseButton"] {{
    display: none !important;
}}
section[data-testid="stSidebar"] > div:first-child {{
    width: 320px !important;
}}
section[data-testid="stSidebar"] * {{ color: #E5E7EB; }}
h1,h2,h3 {{ letter-spacing: -.02em; }}
.mt-brand {{
    padding: 18px 4px 22px;
    border-bottom: 1px solid {COLORS["border"]};
    margin-bottom: 14px;
}}
.mt-brand-mark {{
    display:inline-flex; width:38px; height:38px; border-radius:12px;
    align-items:center; justify-content:center;
    background: linear-gradient(135deg,#8B5CF6,#06B6D4);
    color:white; font-weight:900; font-size:20px;
    box-shadow: 0 10px 30px rgba(139,92,246,.25);
}}
.mt-brand-title {{ font-size:20px; font-weight:800; margin-top:10px; }}
.mt-brand-sub {{ color:#8B95A7; font-size:12px; margin-top:3px; }}
.mt-hero {{
    padding: 28px 30px;
    border: 1px solid #242C3B;
    border-radius: 22px;
    background: linear-gradient(135deg, rgba(17,23,34,.96), rgba(11,14,21,.94));
    box-shadow: 0 20px 60px rgba(0,0,0,.25);
    margin-bottom: 22px;
}}
.mt-kicker {{ color:#A78BFA; font-size:11px; font-weight:800; letter-spacing:.16em; }}
.mt-hero-title {{ font-size:34px; font-weight:900; margin-top:5px; }}
.mt-hero-sub {{ color:#98A2B3; margin-top:6px; }}
[data-testid="stMetric"] {{
    background: linear-gradient(145deg,#0F141D,#0A0E14);
    border: 1px solid #222B3A;
    padding: 16px;
    border-radius: 16px;
}}
div.stButton > button {{
    border-radius: 11px;
    border: 1px solid #303A4C;
    background: #121925;
    color: #F3F4F6;
    font-weight: 700;
}}
div.stButton > button:hover {{
    border-color: #8B5CF6;
    color: white;
    box-shadow: 0 0 22px rgba(139,92,246,.16);
}}
div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {{
    background:#0D121A;
    border-color:#293345;
}}
.mt-card {{
    padding:18px; border:1px solid #202938; border-radius:16px;
    background:#0D1118; height:100%;
}}
.mt-card-label {{ color:#8B95A7; font-size:12px; }}
.mt-card-value {{ font-size:27px; font-weight:850; margin-top:4px; }}
.mt-ok {{ color:#22C55E; font-weight:700; }}
.mt-warn {{ color:#F59E0B; font-weight:700; }}
.mt-bad {{ color:#EF4444; font-weight:700; }}
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# CONFIG
# ============================================================
MONTHS = [
    "Apr", "May", "Jun", "Jul", "Aug", "Sep",
    "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"
]

SOURCE_TYPES = ["Primary", "Tertiary", "Stock"]

DEFAULT_SOURCES = {
    month: {source: "" for source in SOURCE_TYPES}
    for month in MONTHS
}

CONFIG_FILE = os.path.join("data", "data_sources.json")
CACHE_DIR = os.path.join("data", "cache")
os.makedirs("data", exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)


def load_source_config():
    # Prefer Streamlit secrets if provided.
    try:
        raw = st.secrets.get("data_sources")
        if raw:
            cfg = json.loads(raw) if isinstance(raw, str) else dict(raw)
            return normalize_source_config(cfg)
    except Exception:
        pass

    env_raw = os.getenv("DATA_SOURCES_JSON", "").strip()
    if env_raw:
        try:
            return normalize_source_config(json.loads(env_raw))
        except Exception:
            pass

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return normalize_source_config(json.load(f))
        except Exception:
            pass

    return DEFAULT_SOURCES.copy()


def normalize_source_config(cfg):
    out = {m: {s: "" for s in SOURCE_TYPES} for m in MONTHS}
    for m in MONTHS:
        if isinstance(cfg.get(m), dict):
            for s in SOURCE_TYPES:
                out[m][s] = str(cfg[m].get(s, "") or "").strip()
    return out


def save_source_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(normalize_source_config(cfg), f, indent=2)


SOURCES = load_source_config()


# ============================================================
# DATA DOWNLOAD
# ============================================================
def is_excel_bytes(content):
    return bool(content) and (
        content[:2] == b"PK" or content[:4] == b"\xD0\xCF\x11\xE0"
    )


def request_url(url, timeout=90):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/151 Safari/537.36"
        ),
        "Accept": "*/*",
    }
    try:
        return requests.get(
            url, headers=headers, timeout=timeout,
            allow_redirects=True
        )
    except requests.RequestException as exc:
        raise ValueError(f"Could not connect to source: {exc}") from exc


def sharepoint_candidates(url):
    from urllib.parse import quote

    candidates = []
    sep = "&" if "?" in url else "?"
    candidates.append(url + sep + "download=1")

    low = url.lower()
    if "sharepoint.com" in low:
        if "/_layouts/15/doc.aspx" in low:
            prefix = url.split("/_layouts/15/Doc.aspx", 1)[0]
            candidates.append(
                prefix + "/_layouts/15/download.aspx?SourceUrl="
                + quote(url, safe="")
            )
        if "/:x:/r/" in low:
            base = url.split("?", 1)[0]
            candidates.append(base + "?download=1")

    if "1drv.ms" in low or "onedrive.live.com" in low:
        candidates.append(url + sep + "download=1")

    return list(dict.fromkeys(candidates))


def download_excel(url):
    url = str(url).strip()
    if not url:
        raise ValueError("The source link is empty.")

    # Direct / SharePoint / OneDrive
    if any(x in url.lower() for x in [
        "sharepoint.com", "1drv.ms", "onedrive.live.com"
    ]):
        statuses = []
        for candidate in sharepoint_candidates(url):
            r = request_url(candidate)
            statuses.append(r.status_code)
            if r.status_code == 200 and is_excel_bytes(r.content):
                return BytesIO(r.content)
        raise ValueError(
            "Microsoft returned a webpage instead of the Excel workbook. "
            f"HTTP attempts: {statuses}. Make sure the link is "
            "'Anyone with the link - Can view' and allows download."
        )

    # Google Sheets
    if "docs.google.com/spreadsheets" in url.lower():
        import re
        match = re.search(r"/spreadsheets/d/([A-Za-z0-9_-]+)", url)
        if not match:
            raise ValueError("Invalid Google Sheets URL.")
        url = (
            f"https://docs.google.com/spreadsheets/d/"
            f"{match.group(1)}/export?format=xlsx"
        )

    r = request_url(url)
    if r.status_code != 200:
        raise ValueError(f"Source returned HTTP {r.status_code}.")
    if not is_excel_bytes(r.content):
        raise ValueError(
            "The URL returned a webpage instead of an Excel workbook."
        )
    return BytesIO(r.content)


# ============================================================
# EXCEL NORMALIZATION
# ============================================================
ALIASES = {
    "chain code": "Chain Code",
    "chain name": "Chain Name",
    "outlet code": "Outlet Code",
    "store code": "Outlet Code",
    "outlet name": "Outlet Name",
    "store name": "Outlet Name",
    "sku code": "SKU Code",
    "sku name": "SKU Name",
    "product name": "SKU Name",
    "category": "Category",
    "net qty": "Net Qty",
    "quantity": "Net Qty",
    "qty": "Net Qty",
    "net sales": "Net Sales",
    "sales": "Net Sales",
    "last year sales": "Last Year Sales",
    "ly sales": "Last Year Sales",
    "this year sales": "This Year Sales",
    "ty sales": "This Year Sales",
    "primary sales": "Primary Sales",
    "primary": "Primary Sales",
    "tertiary sales": "Tertiary Sales",
    "tertiary": "Tertiary Sales",
    "closing stock": "Closing Stock",
    "stock": "Closing Stock",
    "mrp": "MRP",
    "target": "Target",
    "sales target": "Target",
}


def clean_columns(df):
    df = df.copy()
    df.columns = [
        str(c).strip().replace("\n", " ") for c in df.columns
    ]
    rename = {}
    for c in df.columns:
        key = c.lower().strip()
        if key in ALIASES:
            rename[c] = ALIASES[key]
    return df.rename(columns=rename)


def choose_sheet(xls, preferred):
    names = xls.sheet_names
    low = {str(n).strip().lower(): n for n in names}
    if preferred.lower() in low:
        return low[preferred.lower()]
    for n in names:
        if preferred.lower() in str(n).lower():
            return n
    return names[0] if names else None


def read_workbook(url, source_type):
    file_obj = download_excel(url)
    xls = pd.ExcelFile(file_obj)

    # We support common workbook naming:
    # Primary, Primary Sales, Tertiary, Tertiary Sales, Stock.
    preferred = {
        "Primary": ["Primary", "Primary Sales", "Sales Data"],
        "Tertiary": ["Tertiary", "Tertiary Sales", "Sales Data"],
        "Stock": ["Stock", "Inventory", "Stock Data"],
    }[source_type]

    sheet = None
    for p in preferred:
        sheet = choose_sheet(xls, p)
        if sheet:
            # choose_sheet may fall back to first sheet; only accept
            # fallback when there is no better matching sheet.
            if p.lower() in str(sheet).lower() or len(xls.sheet_names) == 1:
                break

    if sheet is None:
        sheet = xls.sheet_names[0]

    df = clean_columns(pd.read_excel(xls, sheet_name=sheet))

    # Target can be a separate sheet in the same workbook.
    target_df = None
    for n in xls.sheet_names:
        if "target" in str(n).lower():
            target_df = clean_columns(pd.read_excel(xls, sheet_name=n))
            break

    return df, target_df, sheet, xls.sheet_names


def normalize_source(df, source_type, month):
    df = clean_columns(df.copy())
    df["Month"] = month
    df["Source"] = source_type

    numeric_candidates = [
        "Net Qty", "Net Sales", "Last Year Sales", "This Year Sales",
        "Primary Sales", "Tertiary Sales", "Closing Stock", "MRP", "Target"
    ]
    for c in numeric_candidates:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    if source_type == "Primary":
        if "Primary Sales" not in df.columns and "Net Sales" in df.columns:
            df["Primary Sales"] = df["Net Sales"]
        if "Target" not in df.columns:
            df["Target"] = 0

    elif source_type == "Tertiary":
        if "Tertiary Sales" not in df.columns and "Net Sales" in df.columns:
            df["Tertiary Sales"] = df["Net Sales"]
        if "Target" not in df.columns:
            df["Target"] = 0

    elif source_type == "Stock":
        if "Closing Stock" not in df.columns and "Net Qty" in df.columns:
            df["Closing Stock"] = df["Net Qty"]

    return df


def merge_target(base, target):
    if target is None or target.empty:
        if "Target" not in base.columns:
            base["Target"] = 0
        return base

    target = clean_columns(target.copy())
    if "Target" not in target.columns:
        return base

    keys = [
        k for k in ["Chain Code", "Chain Name", "Outlet Code",
                    "Outlet Name", "SKU Code", "SKU Name", "Category"]
        if k in base.columns and k in target.columns
    ]

    if not keys:
        # If target is a single total target, distribute only as metadata.
        total_target = pd.to_numeric(
            target["Target"], errors="coerce"
        ).fillna(0).sum()
        base["Target"] = total_target
        return base

    target["Target"] = pd.to_numeric(
        target["Target"], errors="coerce"
    ).fillna(0)

    target = target.groupby(keys, as_index=False)["Target"].sum()
    return base.drop(columns=["Target"], errors="ignore").merge(
        target, on=keys, how="left"
    ).fillna({"Target": 0})


# ============================================================
# CACHE / COMBINED DATA
# ============================================================
def cache_path(month, source):
    safe = f"{month}_{source}".replace(" ", "_")
    return os.path.join(CACHE_DIR, f"{safe}.csv")


def fetch_source(month, source):
    url = SOURCES.get(month, {}).get(source, "").strip()
    if not url:
        raise ValueError(f"No {source} link configured for {month}.")

    df, target, sheet, sheets = read_workbook(url, source)
    df = normalize_source(df, source, month)
    df = merge_target(df, target)
    df["Fetched At"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    path = cache_path(month, source)
    df.to_csv(path, index=False)
    return df, sheet, sheets


def load_cached(month, source):
    path = cache_path(month, source)
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()


def combine_month(month):
    frames = []
    for source in SOURCE_TYPES:
        cached = load_cached(month, source)
        if not cached.empty:
            frames.append(cached)

    if not frames:
        return pd.DataFrame()

    # Keep each source separate at first; then combine by common keys.
    result = frames[0].copy()

    keys = [
        k for k in [
            "Chain Code", "Chain Name", "Outlet Code",
            "Outlet Name", "SKU Code", "SKU Name", "Category", "Month"
        ] if k in result.columns
    ]

    value_cols = [
        "Primary Sales", "Tertiary Sales", "Closing Stock",
        "Target", "Net Qty", "Net Sales", "Last Year Sales", "This Year Sales", "MRP"
    ]

    for nxt in frames[1:]:
        available = [c for c in value_cols if c in nxt.columns]
        join_keys = [k for k in keys if k in nxt.columns]
        if not join_keys:
            continue

        keep = join_keys + available
        nxt2 = nxt[keep].copy()

        # Prevent duplicate metrics during merge.
        duplicates = [c for c in available if c in result.columns and c not in join_keys]
        if duplicates:
            result = result.drop(columns=duplicates)

        result = result.merge(nxt2, on=join_keys, how="outer")

    return result


def build_dataset(months):
    all_months = []
    for month in months:
        d = combine_month(month)
        if not d.empty:
            all_months.append(d)

    if not all_months:
        return pd.DataFrame()

    df = pd.concat(all_months, ignore_index=True, sort=False)

    for c in [
        "Primary Sales", "Tertiary Sales", "Closing Stock",
        "Target", "Net Qty", "Net Sales", "Last Year Sales",
        "This Year Sales", "MRP"
    ]:
        if c not in df.columns:
            df[c] = 0
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    return enrich(df)


def enrich(df):
    df = df.copy()

    # If Net Sales/Qty aren't present, derive a sensible total.
    if "Net Sales" not in df:
        df["Net Sales"] = df["Primary Sales"] + df["Tertiary Sales"]

    df["YoY Growth %"] = np.where(
        df["Last Year Sales"] != 0,
        (df["This Year Sales"] - df["Last Year Sales"])
        / df["Last Year Sales"] * 100,
        np.nan,
    )

    df["Achievement %"] = np.where(
        df["Target"] > 0,
        df["Primary Sales"].add(df["Tertiary Sales"], fill_value=0)
        / df["Target"] * 100,
        np.nan,
    )

    df["Sell-Through %"] = np.where(
        df["Primary Sales"] > 0,
        df["Tertiary Sales"] / df["Primary Sales"] * 100,
        np.nan,
    )

    df["Primary-Tertiary Gap"] = (
        df["Primary Sales"] - df["Tertiary Sales"]
    )

    df["Realized Price"] = np.where(
        df["Net Qty"] > 0,
        df["Net Sales"] / df["Net Qty"],
        np.nan,
    )

    if "MRP" in df.columns:
        df["Discount %"] = np.where(
            df["MRP"] > 0,
            (df["MRP"] - df["Realized Price"]) / df["MRP"] * 100,
            np.nan,
        )
        df["Stock Value (MRP)"] = df["Closing Stock"] * df["MRP"]

    # Approximate cover using monthly sales; this is intentionally
    # labelled as an estimate because daily sales cadence varies.
    monthly_tertiary = df["Tertiary Sales"].abs()
    df["Stock Cover (Days)"] = np.where(
        monthly_tertiary > 0,
        df["Closing Stock"] / monthly_tertiary * 30,
        np.nan,
    )
    return df


def fmt_inr(x):
    if pd.isna(x):
        return "—"
    x = float(x)
    if abs(x) >= 1e7:
        return f"₹{x/1e7:.2f} Cr"
    if abs(x) >= 1e5:
        return f"₹{x/1e5:.2f} L"
    return f"₹{x:,.0f}"


def style_fig(fig):
    fig.update_layout(
        paper_bgcolor=COLORS["bg"],
        plot_bgcolor=COLORS["bg"],
        font_color=COLORS["text"],
        colorway=CHART_SEQUENCE,
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=45, l=10, r=10, b=10),
    )
    fig.update_xaxes(
        gridcolor=COLORS["border"],
        zerolinecolor=COLORS["border"]
    )
    fig.update_yaxes(
        gridcolor=COLORS["border"],
        zerolinecolor=COLORS["border"]
    )
    return fig


# ============================================================
# ADMIN
# ============================================================
def get_admin_password():
    try:
        value = st.secrets.get("admin_password")
        if value:
            return str(value)
    except Exception:
        pass
    return os.getenv("ADMIN_PASSWORD", "changeme123")


def admin_panel():
    with st.sidebar.expander("⚙️ Data Sources", expanded=False):
        password = get_admin_password()

        if not st.session_state.get("admin_unlocked", False):
            pw = st.text_input(
                "Admin password", type="password", key="admin_password"
            )
            if st.button("Unlock", key="unlock_admin"):
                if pw == password:
                    st.session_state.admin_unlocked = True
                    st.rerun()
                else:
                    st.error("Incorrect password.")
            return

        if st.button("Lock", key="lock_admin"):
            st.session_state.admin_unlocked = False
            st.rerun()

        st.caption(
            "Configure one fixed public Excel link per month and source. "
            "After this one-time setup, daily work is simply updating Excel "
            "and clicking Sync."
        )

        for month in MONTHS:
            st.markdown(f"**{month}**")
            for source in SOURCE_TYPES:
                key = f"url_{month}_{source}"
                st.text_input(
                    f"{source} link",
                    value=SOURCES[month][source],
                    key=key,
                    placeholder="SharePoint / OneDrive Excel link"
                )

        if st.button("💾 Save all source links", key="save_sources"):
            cfg = {m: {} for m in MONTHS}
            for month in MONTHS:
                for source in SOURCE_TYPES:
                    cfg[month][source] = st.session_state.get(
                        f"url_{month}_{source}", ""
                    ).strip()
            save_source_config(cfg)
            st.success("Source links saved.")
            st.rerun()


# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.markdown(
    """
<div class="mt-brand">
  <div class="mt-brand-mark">◈</div>
  <div class="mt-brand-title">MT Command Center</div>
  <div class="mt-brand-sub">Modern Trade Analytics</div>
</div>
""",
    unsafe_allow_html=True,
)

admin_panel()

st.sidebar.markdown("### 🔄 Monthly Sync")

sync_month = st.sidebar.selectbox(
    "Month to sync", MONTHS, index=datetime.now().month % 12
)

if st.sidebar.button("↻ Fetch Latest Month", use_container_width=True):
    errors = []
    successes = []
    for source in SOURCE_TYPES:
        try:
            df_sync, sheet, sheets = fetch_source(sync_month, source)
            successes.append(f"{source}: {len(df_sync):,} rows")
        except Exception as exc:
            errors.append(f"{source}: {exc}")

    if successes:
        st.sidebar.success(" • ".join(successes))
        st.cache_data.clear()
    for err in errors:
        st.sidebar.error(err)

if st.sidebar.button("↻ Sync All Configured Months", use_container_width=True):
    progress = st.sidebar.progress(0)
    errors = []
    total = len(MONTHS) * len(SOURCE_TYPES)
    done = 0

    for month in MONTHS:
        for source in SOURCE_TYPES:
            if SOURCES.get(month, {}).get(source, "").strip():
                try:
                    fetch_source(month, source)
                except Exception as exc:
                    errors.append(f"{month} {source}: {exc}")
            done += 1
            progress.progress(done / total)

    st.cache_data.clear()
    if errors:
        for err in errors:
            st.sidebar.error(err)
    else:
        st.sidebar.success("All configured sources synced.")

# ============================================================
# LOAD DATA
# ============================================================
configured_months = [
    m for m in MONTHS
    if any(SOURCES.get(m, {}).get(s, "").strip() for s in SOURCE_TYPES)
]

cached_months = [
    m for m in MONTHS
    if not combine_month(m).empty
]

available_months = [
    m for m in MONTHS
    if m in cached_months
]

if not available_months:
    st.markdown(
        """
<div class="mt-hero">
<div class="mt-kicker">SETUP REQUIRED</div>
<div class="mt-hero-title">Connect your monthly data</div>
<div class="mt-hero-sub">
Open <b>⚙️ Data Sources</b> in the sidebar, enter the fixed
Apr–Mar Primary, Tertiary and Stock links, save them, then click
<b>Fetch Latest Month</b>.
</div>
</div>
""",
        unsafe_allow_html=True,
    )
    st.info(
        "Target should be inside the corresponding Primary/Tertiary workbook. "
        "A Target sheet is automatically detected when present."
    )
    st.stop()

# ============================================================
# NAV + FILTERS
# ============================================================
st.sidebar.markdown("### 📑 Pages")
pages = [
    "🏠 Executive Summary",
    "🎯 Target & Achievement",
    "🚚 Primary Performance",
    "🛍️ Tertiary Performance",
    "📦 Stock & Inventory",
    "🏢 Chain Performance",
    "🏪 Outlet Performance",
    "🔎 SKU / Category",
    "⚠️ Exceptions",
]
page = st.sidebar.radio("Navigate", pages, label_visibility="collapsed")

st.sidebar.markdown("### Filters")
months_sel = st.sidebar.multiselect(
    "Month", available_months, default=available_months
)

df = build_dataset(months_sel or available_months)

for c in ["Chain Name", "Outlet Name", "SKU Name", "Category"]:
    if c not in df.columns:
        df[c] = "Unknown"

chains = st.sidebar.multiselect(
    "Chain", sorted(df["Chain Name"].dropna().astype(str).unique())
)
if chains:
    df = df[df["Chain Name"].isin(chains)]

outlets = st.sidebar.multiselect(
    "Outlet", sorted(df["Outlet Name"].dropna().astype(str).unique())
)
if outlets:
    df = df[df["Outlet Name"].isin(outlets)]

categories = st.sidebar.multiselect(
    "Category", sorted(df["Category"].dropna().astype(str).unique())
)
if categories:
    df = df[df["Category"].isin(categories)]

if df.empty:
    st.warning("No data matches the selected filters.")
    st.stop()

# ============================================================
# HEADER
# ============================================================
st.markdown(
    f"""
<div class="mt-hero">
  <div class="mt-kicker">MT CHANNEL • PERFORMANCE INTELLIGENCE</div>
  <div class="mt-hero-title">Modern Trade Command Center</div>
  <div class="mt-hero-sub">
    Primary • Tertiary • Stock • Target
    &nbsp;|&nbsp; <b style="color:#C4B5FD">{page}</b>
  </div>
</div>
""",
    unsafe_allow_html=True,
)


# ============================================================
# EXECUTIVE
# ============================================================
if page == pages[0]:
    primary = df["Primary Sales"].sum()
    tertiary = df["Tertiary Sales"].sum()
    target = df["Target"].sum()
    stock = df["Closing Stock"].sum()
    achievement = primary / target * 100 if target else np.nan
    sellthrough = tertiary / primary * 100 if primary else np.nan

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Primary Sales", fmt_inr(primary))
    c2.metric("Tertiary Sales", fmt_inr(tertiary))
    c3.metric("Target", fmt_inr(target))
    c4.metric("Achievement", f"{achievement:.1f}%" if pd.notna(achievement) else "—")
    c5.metric("Stock Units", f"{stock:,.0f}")

    st.markdown("### 📈 Primary vs Tertiary")
    trend = (
        df.groupby("Month", as_index=False)[
            ["Primary Sales", "Tertiary Sales", "Target"]
        ].sum()
    )
    fig = px.bar(
        trend, x="Month",
        y=["Primary Sales", "Tertiary Sales", "Target"],
        barmode="group",
    )
    st.plotly_chart(style_fig(fig), use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🏢 Top Chains")
        chain = (
            df.groupby("Chain Name", as_index=False)
            .agg(Primary=("Primary Sales", "sum"),
                 Tertiary=("Tertiary Sales", "sum"))
            .sort_values("Primary", ascending=False)
            .head(15)
        )
        fig = px.bar(chain, x="Primary", y="Chain Name", orientation="h")
        fig.update_layout(height=480)
        st.plotly_chart(style_fig(fig), use_container_width=True)

    with col2:
        st.markdown("### 📦 Category Mix")
        cat = df.groupby("Category", as_index=False)["Primary Sales"].sum()
        fig = px.pie(cat, names="Category", values="Primary Sales", hole=.58)
        fig.update_layout(height=480)
        st.plotly_chart(style_fig(fig), use_container_width=True)


# ============================================================
# TARGET
# ============================================================
elif page == pages[1]:
    target = df["Target"].sum()
    primary = df["Primary Sales"].sum()
    ach = primary / target * 100 if target else np.nan
    gap = primary - target

    c1, c2, c3 = st.columns(3)
    c1.metric("Primary Target", fmt_inr(target))
    c2.metric("Primary Actual", fmt_inr(primary))
    c3.metric("Achievement", f"{ach:.1f}%" if pd.notna(ach) else "—")

    st.metric("Target Gap", fmt_inr(gap))

    by_chain = (
        df.groupby("Chain Name", as_index=False)
        .agg(Target=("Target", "sum"), Actual=("Primary Sales", "sum"))
    )
    by_chain["Achievement %"] = np.where(
        by_chain["Target"] > 0,
        by_chain["Actual"] / by_chain["Target"] * 100,
        np.nan,
    )
    by_chain = by_chain.sort_values("Achievement %")

    fig = px.bar(
        by_chain,
        x="Chain Name",
        y="Achievement %",
        color="Achievement %",
        color_continuous_scale=[
            COLORS["red"], COLORS["amber"], COLORS["green"]
        ],
    )
    fig.add_hline(y=100, line_dash="dash")
    st.plotly_chart(style_fig(fig), use_container_width=True)

    st.dataframe(
        by_chain.style.format({
            "Target": "₹{:,.0f}",
            "Actual": "₹{:,.0f}",
            "Achievement %": "{:.1f}%",
        }),
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# PRIMARY
# ============================================================
elif page == pages[2]:
    primary = df["Primary Sales"].sum()
    target = df["Target"].sum()
    achievement = primary / target * 100 if target else np.nan

    c1, c2, c3 = st.columns(3)
    c1.metric("Primary Sales", fmt_inr(primary))
    c2.metric("Target", fmt_inr(target))
    c3.metric("Achievement", f"{achievement:.1f}%" if pd.notna(achievement) else "—")

    by_chain = (
        df.groupby("Chain Name", as_index=False)["Primary Sales"]
        .sum()
        .sort_values("Primary Sales", ascending=False)
    )
    fig = px.bar(by_chain.head(20), x="Chain Name", y="Primary Sales")
    st.plotly_chart(style_fig(fig), use_container_width=True)

    st.markdown("### Monthly Primary Trend")
    trend = df.groupby("Month", as_index=False)["Primary Sales"].sum()
    fig = px.line(trend, x="Month", y="Primary Sales", markers=True)
    st.plotly_chart(style_fig(fig), use_container_width=True)


# ============================================================
# TERTIARY
# ============================================================
elif page == pages[3]:
    tertiary = df["Tertiary Sales"].sum()
    primary = df["Primary Sales"].sum()
    st.metric(
        "Sell-Through",
        f"{tertiary / primary * 100:.1f}%" if primary else "—"
    )

    by_chain = (
        df.groupby("Chain Name", as_index=False)
        .agg(Primary=("Primary Sales", "sum"),
             Tertiary=("Tertiary Sales", "sum"))
    )
    by_chain["Sell-Through %"] = np.where(
        by_chain["Primary"] > 0,
        by_chain["Tertiary"] / by_chain["Primary"] * 100,
        np.nan,
    )

    fig = px.scatter(
        by_chain,
        x="Primary",
        y="Tertiary",
        size="Tertiary",
        color="Sell-Through %",
        hover_name="Chain Name",
        color_continuous_scale=[COLORS["red"], COLORS["amber"], COLORS["green"]],
    )
    st.plotly_chart(style_fig(fig), use_container_width=True)

    st.dataframe(
        by_chain.style.format({
            "Primary": "₹{:,.0f}",
            "Tertiary": "₹{:,.0f}",
            "Sell-Through %": "{:.1f}%",
        }),
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# STOCK
# ============================================================
elif page == pages[4]:
    stock = df["Closing Stock"].sum()
    primary = df["Primary Sales"].sum()
    tertiary = df["Tertiary Sales"].sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Closing Stock", f"{stock:,.0f}")
    c2.metric("Stock Value", fmt_inr(df.get("Stock Value (MRP)", pd.Series([0])).sum()))
    c3.metric(
        "Sell-Through",
        f"{tertiary / primary * 100:.1f}%" if primary else "—"
    )

    by_cat = (
        df.groupby("Category", as_index=False)["Closing Stock"]
        .sum()
        .sort_values("Closing Stock", ascending=False)
    )
    fig = px.bar(by_cat, x="Category", y="Closing Stock")
    st.plotly_chart(style_fig(fig), use_container_width=True)

    dead = df[
        (df["Closing Stock"] > 0) &
        (df["Tertiary Sales"] <= df["Tertiary Sales"].quantile(.10))
    ].copy()
    dead = dead.sort_values("Closing Stock", ascending=False).head(100)

    st.markdown("### 🔴 Dead / Slow Stock")
    st.dataframe(
        dead[
            ["Chain Name", "Outlet Name", "SKU Name",
             "Category", "Tertiary Sales", "Closing Stock"]
        ].style.format({
            "Tertiary Sales": "{:,.0f}",
            "Closing Stock": "{:,.0f}",
        }),
        use_container_width=True,
        hide_index=True,
        height=350,
    )


# ============================================================
# CHAIN
# ============================================================
elif page == pages[5]:
    chain = (
        df.groupby("Chain Name", as_index=False)
        .agg(
            Primary=("Primary Sales", "sum"),
            Tertiary=("Tertiary Sales", "sum"),
            Target=("Target", "sum"),
            Stock=("Closing Stock", "sum"),
        )
    )
    chain["Achievement %"] = np.where(
        chain["Target"] > 0,
        chain["Primary"] / chain["Target"] * 100,
        np.nan,
    )
    chain["Sell-Through %"] = np.where(
        chain["Primary"] > 0,
        chain["Tertiary"] / chain["Primary"] * 100,
        np.nan,
    )
    chain = chain.sort_values("Primary", ascending=False)

    st.dataframe(
        chain.style.format({
            "Primary": "₹{:,.0f}",
            "Tertiary": "₹{:,.0f}",
            "Target": "₹{:,.0f}",
            "Stock": "{:,.0f}",
            "Achievement %": "{:.1f}%",
            "Sell-Through %": "{:.1f}%",
        }),
        use_container_width=True,
        hide_index=True,
        height=500,
    )


# ============================================================
# OUTLET
# ============================================================
elif page == pages[6]:
    outlet = (
        df.groupby(["Chain Name", "Outlet Name"], as_index=False)
        .agg(
            Primary=("Primary Sales", "sum"),
            Tertiary=("Tertiary Sales", "sum"),
            Target=("Target", "sum"),
            Stock=("Closing Stock", "sum"),
        )
    )
    outlet["Achievement %"] = np.where(
        outlet["Target"] > 0,
        outlet["Primary"] / outlet["Target"] * 100,
        np.nan,
    )
    outlet["Sell-Through %"] = np.where(
        outlet["Primary"] > 0,
        outlet["Tertiary"] / outlet["Primary"] * 100,
        np.nan,
    )

    st.dataframe(
        outlet.sort_values("Primary", ascending=False).style.format({
            "Primary": "₹{:,.0f}",
            "Tertiary": "₹{:,.0f}",
            "Target": "₹{:,.0f}",
            "Stock": "{:,.0f}",
            "Achievement %": "{:.1f}%",
            "Sell-Through %": "{:.1f}%",
        }),
        use_container_width=True,
        hide_index=True,
        height=550,
    )


# ============================================================
# SKU / CATEGORY
# ============================================================
elif page == pages[7]:
    cat = (
        df.groupby("Category", as_index=False)
        .agg(
            Primary=("Primary Sales", "sum"),
            Tertiary=("Tertiary Sales", "sum"),
            Stock=("Closing Stock", "sum"),
        )
    )
    cat["Sell-Through %"] = np.where(
        cat["Primary"] > 0,
        cat["Tertiary"] / cat["Primary"] * 100,
        np.nan,
    )

    fig = px.bar(
        cat.sort_values("Primary", ascending=False),
        x="Category", y="Primary",
        color="Sell-Through %",
        color_continuous_scale=[COLORS["red"], COLORS["amber"], COLORS["green"]],
    )
    st.plotly_chart(style_fig(fig), use_container_width=True)

    sku = (
        df.groupby(["SKU Code", "SKU Name"], as_index=False)
        .agg(
            Primary=("Primary Sales", "sum"),
            Tertiary=("Tertiary Sales", "sum"),
            Stock=("Closing Stock", "sum"),
        )
        .sort_values("Primary", ascending=False)
    )
    sku["Sell-Through %"] = np.where(
        sku["Primary"] > 0,
        sku["Tertiary"] / sku["Primary"] * 100,
        np.nan,
    )

    st.dataframe(
        sku.style.format({
            "Primary": "₹{:,.0f}",
            "Tertiary": "₹{:,.0f}",
            "Stock": "{:,.0f}",
            "Sell-Through %": "{:.1f}%",
        }),
        use_container_width=True,
        hide_index=True,
        height=500,
    )


# ============================================================
# EXCEPTIONS
# ============================================================
elif page == pages[8]:
    st.markdown("### 🔴 High Primary / Low Sell-Through")
    primary_med = df["Primary Sales"].median()
    stuffing = df[
        (df["Primary Sales"] > primary_med) &
        (df["Sell-Through %"] < 70)
    ].copy()

    st.dataframe(
        stuffing.sort_values("Primary Sales", ascending=False).head(100)[
            ["Chain Name", "Outlet Name", "SKU Name", "Category",
             "Primary Sales", "Tertiary Sales", "Sell-Through %",
             "Closing Stock"]
        ].style.format({
            "Primary Sales": "₹{:,.0f}",
            "Tertiary Sales": "₹{:,.0f}",
            "Sell-Through %": "{:.1f}%",
            "Closing Stock": "{:,.0f}",
        }),
        use_container_width=True,
        hide_index=True,
        height=330,
    )

    st.markdown("### 🟠 High Sell-Through / Low Stock")
    risk = df[
        (df["Sell-Through %"] > 90) &
        (df["Closing Stock"] > 0)
    ].copy()
    risk["Stock Cover (Days)"] = np.where(
        risk["Tertiary Sales"] > 0,
        risk["Closing Stock"] / risk["Tertiary Sales"] * 30,
        np.nan,
    )
    risk = risk.sort_values("Stock Cover (Days)")

    st.dataframe(
        risk.head(100)[
            ["Chain Name", "Outlet Name", "SKU Name",
             "Sell-Through %", "Stock Cover (Days)", "Closing Stock"]
        ].style.format({
            "Sell-Through %": "{:.1f}%",
            "Stock Cover (Days)": "{:.1f}",
            "Closing Stock": "{:,.0f}",
        }),
        use_container_width=True,
        hide_index=True,
        height=330,
    )


# ============================================================
# FOOTER
# ============================================================
st.markdown("---")
st.caption(
    "MT Command Center • Primary + Tertiary + Stock + Target • "
    "Fixed monthly SharePoint/OneDrive sources"
)
