import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="MT Channel Sales Dashboard", layout="wide", page_icon="📊")

# ============================================================
# DATA LOADING
# ============================================================
REQUIRED_COLS = [
    "Chain Code", "Chain Name", "Outlet Code", "Outlet Name", "SKU Code",
    "SKU Name", "Category", "Net Qty", "Net Sales", "Last Year Sales",
    "This Year Sales", "Primary Sales", "Tertiary Sales", "Closing Stock",
]


@st.cache_data(show_spinner=False)
def load_from_file(file_bytes_or_path, sales_sheet="Sales Data", mrp_sheet="MRP Master"):
    xls = pd.ExcelFile(file_bytes_or_path)
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


@st.cache_data(show_spinner=False)
def load_from_url(url):
    # Works for direct Excel links or a Google Sheets "export?format=xlsx" link
    return load_from_file(url)


def validate(df):
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    return missing


def enrich(df):
    df = df.copy()
    df["Net Qty"] = pd.to_numeric(df["Net Qty"], errors="coerce").fillna(0)
    df["Net Sales"] = pd.to_numeric(df["Net Sales"], errors="coerce").fillna(0)
    df["Last Year Sales"] = pd.to_numeric(df["Last Year Sales"], errors="coerce").fillna(0)
    df["This Year Sales"] = pd.to_numeric(df["This Year Sales"], errors="coerce").fillna(0)
    df["Primary Sales"] = pd.to_numeric(df["Primary Sales"], errors="coerce").fillna(0)
    df["Tertiary Sales"] = pd.to_numeric(df["Tertiary Sales"], errors="coerce").fillna(0)
    df["Closing Stock"] = pd.to_numeric(df["Closing Stock"], errors="coerce").fillna(0)

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


# ============================================================
# SIDEBAR — DATA SOURCE
# ============================================================
st.sidebar.title("📊 MT Sales Dashboard")
st.sidebar.markdown("### Data Source")
source_mode = st.sidebar.radio(
    "Choose data source",
    ["Use sample data", "Upload Excel file", "Live link (Google Sheet / OneDrive)"],
    index=0,
)

df_raw = None
load_error = None

if source_mode == "Use sample data":
    try:
        df_raw = load_from_file("MT_Sales_Dummy_Data.xlsx")
    except Exception as e:
        load_error = str(e)

elif source_mode == "Upload Excel file":
    uploaded = st.sidebar.file_uploader("Upload your .xlsx file", type=["xlsx"])
    if uploaded is not None:
        try:
            df_raw = load_from_file(uploaded)
        except Exception as e:
            load_error = str(e)
    else:
        st.sidebar.info("Upload a file, or switch to 'Use sample data'.")

elif source_mode == "Live link (Google Sheet / OneDrive)":
    st.sidebar.caption(
        "Paste a direct download link. For Google Sheets: File → Share → Publish to web → "
        "choose xlsx, then paste that link here."
    )
    url = st.sidebar.text_input("Excel file URL")
    if url:
        try:
            df_raw = load_from_url(url)
        except Exception as e:
            load_error = str(e)

if st.sidebar.button("🔄 Refresh data"):
    st.cache_data.clear()
    st.rerun()

if load_error:
    st.error(f"Could not load data: {load_error}")
    st.stop()

if df_raw is None:
    st.info("👈 Choose a data source in the sidebar to load the dashboard.")
    st.stop()

missing_cols = validate(df_raw)
if missing_cols:
    st.error(f"Your file is missing required columns: {missing_cols}")
    st.caption(f"Required columns: {REQUIRED_COLS}")
    st.stop()

df = enrich(df_raw)
has_mrp = "MRP" in df.columns and df["MRP"].notna().any()
has_chain_type = "Chain Type" in df.columns and df["Chain Type"].notna().any()

# ============================================================
# SIDEBAR — FILTERS
# ============================================================
st.sidebar.markdown("### Filters")
df_f = df
if has_chain_type:
    ctype_sel = st.sidebar.multiselect("Chain Type", sorted(df["Chain Type"].unique()), default=None)
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
    st.warning("No data matches the selected filters.")
    st.stop()

st.sidebar.markdown("---")
st.sidebar.caption(f"Rows loaded: {len(df):,} | After filters: {len(df_f):,}")

# ============================================================
# HEADER
# ============================================================
st.title("Modern Trade (MT) Channel — Sales & Distribution Dashboard")
st.caption("Chain → Outlet → SKU level performance, distribution health, inventory & pricing")

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
tabs = st.tabs(tab_labels)

# Index offset: if Chain Type comparison tab exists, all subsequent indices shift by 1
_off = 1 if has_chain_type else 0

# ------------------------------------------------------------
# TAB 1: EXECUTIVE SUMMARY
# ------------------------------------------------------------
with tabs[0]:
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
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("Sales Mix by Category")
        cat_sales = df_f.groupby("Category", as_index=False)["Net Sales"].sum()
        fig = px.pie(cat_sales, names="Category", values="Net Sales", hole=0.45)
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.subheader("This Year vs Last Year")
        yr_df = pd.DataFrame({"Period": ["Last Year", "This Year"], "Sales": [ly_total, ty_total]})
        fig = px.bar(yr_df, x="Period", y="Sales", text_auto=".2s", color="Period",
                     color_discrete_map={"Last Year": "#94a3b8", "This Year": "#2563eb"})
        st.plotly_chart(fig, use_container_width=True)
    with col4:
        st.subheader("Top 5 / Bottom 5 Chains by YoY Growth")
        chain_yoy = df_f.groupby("Chain Name").agg(
            LY=("Last Year Sales", "sum"), TY=("This Year Sales", "sum")
        ).reset_index()
        chain_yoy["YoY %"] = (chain_yoy["TY"] - chain_yoy["LY"]) / chain_yoy["LY"] * 100
        chain_yoy = chain_yoy.sort_values("YoY %", ascending=False)
        fig = px.bar(chain_yoy, x="YoY %", y="Chain Name", orientation="h", color="YoY %",
                     color_continuous_scale="RdYlGn")
        st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------
# TAB (optional): CHAIN TYPE COMPARISON (Grocery vs Beauty/Pharma)
# ------------------------------------------------------------
if has_chain_type:
    with tabs[1]:
        st.subheader("Grocery MT vs Beauty & Pharma MT — Side by Side")

        ct_tbl = df_f.groupby("Chain Type").agg(
            Chains=("Chain Code", "nunique"),
            Outlets=("Outlet Code", "nunique"),
            Net_Sales=("Net Sales", "sum"),
            Net_Qty=("Net Qty", "sum"),
            LY_Sales=("Last Year Sales", "sum"),
            TY_Sales=("This Year Sales", "sum"),
            Primary=("Primary Sales", "sum"),
            Tertiary=("Tertiary Sales", "sum"),
            Closing_Stock=("Closing Stock", "sum"),
        ).reset_index()
        ct_tbl["YoY %"] = (ct_tbl["TY_Sales"] - ct_tbl["LY_Sales"]) / ct_tbl["LY_Sales"] * 100
        ct_tbl["Sell-Through %"] = ct_tbl["Tertiary"] / ct_tbl["Primary"] * 100
        ct_tbl["Avg Sales / Outlet"] = ct_tbl["Net_Sales"] / ct_tbl["Outlets"]
        if has_mrp:
            ct_disc = df_f.groupby("Chain Type")["Discount %"].mean()
            ct_tbl["Avg Discount %"] = ct_tbl["Chain Type"].map(ct_disc)

        # KPI cards side by side
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
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.subheader("YoY Growth % Comparison")
            fig = px.bar(ct_tbl, x="Chain Type", y="YoY %", color="Chain Type", text_auto=".1f")
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        col3, col4 = st.columns(2)
        with col3:
            st.subheader("Sell-Through Rate Comparison")
            fig = px.bar(ct_tbl, x="Chain Type", y="Sell-Through %", color="Chain Type", text_auto=".1f")
            fig.add_hline(y=100, line_dash="dash", line_color="black")
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        with col4:
            st.subheader("Category Mix by Chain Type")
            mix = df_f.groupby(["Chain Type", "Category"])["Net Sales"].sum().reset_index()
            fig = px.bar(mix, x="Chain Type", y="Net Sales", color="Category", barmode="stack")
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Same SKU, Different Channel — Performance Comparison")
        st.caption("Pick a SKU sold in both chain types to compare how it performs across Grocery vs Beauty/Pharma MT.")
        common_skus = (
            df_f.groupby("SKU Name")["Chain Type"].nunique()
        )
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
with tabs[1 + _off]:
    st.subheader("Chain-wise Scorecard")
    chain_tbl = df_f.groupby(["Chain Code", "Chain Name"]).agg(
        Outlets=("Outlet Code", "nunique"),
        Net_Sales=("Net Sales", "sum"),
        Net_Qty=("Net Qty", "sum"),
        LY_Sales=("Last Year Sales", "sum"),
        TY_Sales=("This Year Sales", "sum"),
        Primary=("Primary Sales", "sum"),
        Tertiary=("Tertiary Sales", "sum"),
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
        }).background_gradient(subset=["YoY %"], cmap="RdYlGn"),
        use_container_width=True, hide_index=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Chain Growth vs Value Quadrant")
        fig = px.scatter(
            chain_tbl, x="Net_Sales", y="YoY %", size="Outlets", color="Chain Name",
            text="Chain Name", labels={"Net_Sales": "Net Sales (Value)", "YoY %": "YoY Growth %"},
        )
        fig.add_hline(y=chain_tbl["YoY %"].mean(), line_dash="dash", line_color="gray")
        fig.add_vline(x=chain_tbl["Net_Sales"].mean(), line_dash="dash", line_color="gray")
        fig.update_traces(textposition="top center")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("Category Penetration by Chain")
        pen = df_f.groupby(["Chain Name", "Category"])["Net Sales"].sum().reset_index()
        fig = px.treemap(pen, path=["Chain Name", "Category"], values="Net Sales")
        st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------
# TAB 3: OUTLET PERFORMANCE
# ------------------------------------------------------------
with tabs[2 + _off]:
    st.subheader("Outlet Scorecard")
    out_tbl = df_f.groupby(["Chain Name", "Outlet Code", "Outlet Name"]).agg(
        Net_Sales=("Net Sales", "sum"),
        LY_Sales=("Last Year Sales", "sum"),
        TY_Sales=("This Year Sales", "sum"),
        Primary=("Primary Sales", "sum"),
        Tertiary=("Tertiary Sales", "sum"),
        Stock_Cover=("Stock Cover (Days)", "mean"),
        SKUs=("SKU Code", "nunique"),
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
        }).background_gradient(subset=["YoY %"], cmap="RdYlGn"),
        use_container_width=True, hide_index=True, height=400,
    )

    st.subheader("Segment Distribution")
    seg_count = out_tbl["Segment"].value_counts().reset_index()
    seg_count.columns = ["Segment", "Outlets"]
    fig = px.bar(seg_count, x="Segment", y="Outlets", color="Segment", text_auto=True)
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------
# TAB 4: CATEGORY & SKU
# ------------------------------------------------------------
with tabs[3 + _off]:
    st.subheader("Category Performance")
    cat_tbl = df_f.groupby("Category").agg(
        Net_Sales=("Net Sales", "sum"), LY_Sales=("Last Year Sales", "sum"),
        TY_Sales=("This Year Sales", "sum"), Primary=("Primary Sales", "sum"),
        Tertiary=("Tertiary Sales", "sum"),
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
        }),
        use_container_width=True, hide_index=True,
    )

    st.markdown("---")
    st.subheader("SKU Pareto (80/20) — Top SKUs by Sales")
    sku_tbl = df_f.groupby(["SKU Code", "SKU Name", "Category"]).agg(
        Net_Sales=("Net Sales", "sum"), Net_Qty=("Net Qty", "sum"),
        LY_Sales=("Last Year Sales", "sum"), TY_Sales=("This Year Sales", "sum"),
        Outlets=("Outlet Code", "nunique"),
    ).reset_index().sort_values("Net_Sales", ascending=False)
    sku_tbl["YoY %"] = (sku_tbl["TY_Sales"] - sku_tbl["LY_Sales"]) / sku_tbl["LY_Sales"] * 100
    sku_tbl["Cum Share %"] = sku_tbl["Net_Sales"].cumsum() / sku_tbl["Net_Sales"].sum() * 100

    fig = go.Figure()
    fig.add_bar(x=sku_tbl["SKU Name"], y=sku_tbl["Net_Sales"], name="Net Sales")
    fig.add_trace(go.Scatter(x=sku_tbl["SKU Name"], y=sku_tbl["Cum Share %"], name="Cumulative %",
                              yaxis="y2", line=dict(color="red")))
    fig.update_layout(
        yaxis=dict(title="Net Sales"),
        yaxis2=dict(title="Cumulative %", overlaying="y", side="right", range=[0, 105]),
        xaxis=dict(tickangle=-45), height=450,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("SKU Movement: Growing vs Declining")
    def move_seg(v):
        if pd.isna(v): return "No LY data"
        if v > 10: return "Growing"
        if v < -10: return "Declining"
        return "Stable"
    sku_tbl["Movement"] = sku_tbl["YoY %"].apply(move_seg)
    move_count = sku_tbl["Movement"].value_counts().reset_index()
    move_count.columns = ["Movement", "SKU Count"]
    fig = px.pie(move_count, names="Movement", values="SKU Count", hole=0.45,
                 color="Movement", color_discrete_map={"Growing": "#22c55e", "Declining": "#ef4444", "Stable": "#94a3b8", "No LY data": "#e2e8f0"})
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Full SKU table"):
        st.dataframe(sku_tbl.style.format({
            "Net_Sales": "{:,.0f}", "Net_Qty": "{:,.0f}", "LY_Sales": "{:,.0f}",
            "TY_Sales": "{:,.0f}", "YoY %": "{:.1f}%",
        }), use_container_width=True, hide_index=True)

# ------------------------------------------------------------
# TAB 5: DISTRIBUTION HEALTH (Primary vs Tertiary)
# ------------------------------------------------------------
with tabs[4 + _off]:
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
                     orientation="h", color="Sell-Through %", color_continuous_scale="RdYlGn")
        fig.add_vline(x=100, line_dash="dash", line_color="black")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("Sell-Through Rate by Category")
        cat_st = df_f.groupby("Category").agg(P=("Primary Sales", "sum"), T=("Tertiary Sales", "sum")).reset_index()
        cat_st["Sell-Through %"] = cat_st["T"] / cat_st["P"] * 100
        fig = px.bar(cat_st.sort_values("Sell-Through %"), x="Sell-Through %", y="Category",
                     orientation="h", color="Sell-Through %", color_continuous_scale="RdYlGn")
        fig.add_vline(x=100, line_dash="dash", line_color="black")
        st.plotly_chart(fig, use_container_width=True)

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
with tabs[5 + _off]:
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
        fig = px.histogram(df_f, x="Stock Cover (Days)", nbins=30)
        fig.add_vline(x=60, line_dash="dash", line_color="red", annotation_text="60-day threshold")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("Closing Stock by Category")
        stock_cat = df_f.groupby("Category", as_index=False)["Closing Stock"].sum()
        fig = px.bar(stock_cat.sort_values("Closing Stock", ascending=False), x="Category", y="Closing Stock", color="Category")
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

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
with tabs[6 + _off]:
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
            fig = px.bar(chain_disc, x="Chain Name", y="Discount %", color="Discount %", color_continuous_scale="Reds")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.subheader("Discount % by Category")
            cat_disc = df_f.groupby("Category", as_index=False)["Discount %"].mean().sort_values("Discount %", ascending=False)
            fig = px.bar(cat_disc, x="Category", y="Discount %", color="Discount %", color_continuous_scale="Reds")
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Price-Volume-Mix (PVM) — YoY Sales Variance Bridge")
        st.caption("Decomposes the YoY sales change into Volume effect, Mix effect, and Discount effect (since MRP is static).")
        ly, ty = df_f["Last Year Sales"].sum(), df_f["This Year Sales"].sum()
        total_delta = ty - ly
        # Simplified attribution using qty-weighted MRP potential vs actual
        potential_ty_at_mrp = (df_f["Net Qty"] * df_f["MRP"]).sum()
        discount_effect = potential_ty_at_mrp - ty
        volume_mix_effect = potential_ty_at_mrp - ly - discount_effect + discount_effect  # placeholder structure below

        # Cleaner bridge: LY -> (LY * volume growth) -> at-MRP TY -> actual TY (post-discount)
        qty_ly_equiv = ly / df_f["Realized Price"].replace(0, np.nan).mean() if df_f["Realized Price"].mean() else np.nan
        volume_effect = potential_ty_at_mrp - ly if pd.notna(potential_ty_at_mrp) else 0
        fig = go.Figure(go.Waterfall(
            orientation="v",
            measure=["absolute", "relative", "relative", "total"],
            x=["Last Year Sales", "Volume + Mix Effect", "Discount Effect", "This Year Sales"],
            y=[ly, volume_effect, -discount_effect, ty],
            connector={"line": {"color": "gray"}},
            decreasing={"marker": {"color": "#ef4444"}},
            increasing={"marker": {"color": "#22c55e"}},
            totals={"marker": {"color": "#2563eb"}},
        ))
        fig.update_layout(height=450, yaxis_title="Net Sales (₹)")
        st.plotly_chart(fig, use_container_width=True)
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
with tabs[7 + _off]:
    st.subheader("🔍 Outlier Detection — Abnormal YoY Swings")
    threshold = st.slider("Flag SKU-outlet combinations with |YoY change| greater than (%)", 20, 200, 50)
    outliers = df_f[df_f["YoY Growth %"].abs() > threshold].copy()
    outliers = outliers[["Chain Name", "Outlet Name", "SKU Name", "Category", "Last Year Sales", "This Year Sales", "YoY Growth %"]]
    outliers = outliers.sort_values("YoY Growth %", ascending=False)
    st.dataframe(outliers.style.format({"Last Year Sales": "{:,.0f}", "This Year Sales": "{:,.0f}", "YoY Growth %": "{:.1f}%"})
                 .background_gradient(subset=["YoY Growth %"], cmap="RdYlGn"),
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
st.caption("Built for MT channel reporting. Update your Excel and use the sidebar Upload/Refresh to see new numbers.")
