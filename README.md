# MT Command Center

Modern black-theme Streamlit dashboard for separate monthly Primary, Tertiary and Stock Excel sources.

## Data model
- Primary workbook: sales + Target sheet
- Tertiary workbook: sales + Target sheet
- Stock workbook
- 12 fixed months: Apr-Mar
- SharePoint/OneDrive public links

## Setup
1. Put `app.py`, `requirements.txt`, `render.yaml`, and `data/data_sources.json` in GitHub.
2. Deploy on Render.
3. Set `ADMIN_PASSWORD` in Render Environment.
4. Open the dashboard -> `Data Sources`.
5. Enter the 12 Primary, 12 Tertiary and 12 Stock links once.
6. Save.
7. Each day/month update Excel and click `Fetch Latest Month`.

Target sheets are detected automatically when a sheet name contains `Target`.
