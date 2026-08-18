# MT Channel Sales Dashboard

A Streamlit dashboard covering: Executive Summary, Chain Performance, Outlet
Performance, Category & SKU, Distribution Health (Primary vs Tertiary),
Inventory & Stock, Pricing & Discount (PVM analysis), and Diagnostics &
Exceptions — built on your 12-column schema + SKU-wise MRP.

## Files
- `app.py` — the dashboard
- `MT_Sales_Dummy_Data.xlsx` — dummy sample data (two sheets: `Sales Data`, `MRP Master`)
- `generate_dummy_data.py` — script that made the dummy file (for reference only)
- `requirements.txt` — Python packages needed

## Your real file must follow this shape
**Sheet 1 — "Sales Data"** with exactly these column headers:
`Chain Code, Chain Name, Outlet Code, Outlet Name, SKU Code, SKU Name,
Category, Net Qty, Net Sales, Last Year Sales, This Year Sales,
Primary Sales, Tertiary Sales, Closing Stock`

**Optional column — "Chain Type"** (e.g. `Grocery` / `Beauty & Pharma`):
adding this column unlocks a dedicated "Grocery vs Beauty/Pharma" comparison
tab (side-by-side KPIs, category mix, sell-through, discount %, and a
same-SKU cross-channel comparison). Leave it out and the dashboard works
exactly as before, just without that tab.

**Sheet 2 — "MRP Master"** (optional, unlocks the Pricing tab):
`SKU Code, MRP`

Column order doesn't matter, but names must match exactly (case-sensitive).

---

## Option A — Run it locally first (2 minutes)
```bash
pip install -r requirements.txt
streamlit run app.py
```
Opens at `http://localhost:8501`. Good for testing before you share it.

---

## Option B — Host it online so teammates can open a link (free, ~10 minutes)

**Using Streamlit Community Cloud** (easiest, no server management):

1. Create a free GitHub account if you don't have one, and a new repository
   (e.g. `mt-sales-dashboard`).
2. Upload these files to that repo: `app.py`, `requirements.txt`, and
   `MT_Sales_Dummy_Data.xlsx` (this becomes your default/starter data).
3. Go to **share.streamlit.io**, sign in with GitHub, click **New app**,
   select your repo and `app.py` as the entry point, click **Deploy**.
4. You'll get a public link like `https://mt-sales-dashboard.streamlit.app` —
   share that with your team. Anyone with the link can view it; no login needed
   unless you set the app to private in Streamlit Cloud's settings.

This takes about 2-3 minutes to build after you click Deploy, then it's live.

---

## Keeping the data up to date (three ways — pick one)

**1. Manual upload (simplest, always works)**
In the sidebar, choose **"Upload Excel file"**, upload your latest export.
Every teammate viewing the app would need to do this themselves unless you
also update the "live link" source below — uploads are per-browser-session,
not shared automatically across viewers.

**2. Live link — Google Sheets (recommended for shared auto-updates)**
- Keep your master data in a Google Sheet instead of a local Excel file
  (or keep updating a local file and copy-paste into the Sheet).
- In Google Sheets: **File → Share → Publish to web**, choose the sheet,
  format **Microsoft Excel (.xlsx)**, publish, and copy the link.
- In the dashboard sidebar, choose **"Live link"** and paste that URL.
- Now, whenever the Google Sheet changes, everyone who clicks **🔄 Refresh
  data** (or reloads the page) sees the latest numbers — no re-upload needed.

**3. Live link — OneDrive/SharePoint**
Similar idea: get a direct/embed download link to the `.xlsx` file from
OneDrive ("Share → Copy link", then adjust to a direct-download form) and
paste it the same way. Google Sheets tends to be more reliable for this.

---

## Updating the dashboard itself later
If you want new charts, filters, or metrics added, just update `app.py` and
push the change to GitHub — Streamlit Community Cloud redeploys automatically
within a minute of a push.
