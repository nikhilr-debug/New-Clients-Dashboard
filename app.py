import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta

# ─── CONFIG (HIDDEN FROM UI) ──────────────────────────────────────────────────
REDASH_BASE_URL = "https://redash.vahan.co"
REDASH_API_KEY  = "4aFm2iOoyx8I91svQccdeZr0jmaiUsMFSRinZcmu"       
QUERY_ID        = 18055                                          

# ─── PAGE SETUP ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Pronto & Snabbit – MOE Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── PREMIUM CSS STYLING (THEME RESPONSIVE) ───────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  
  html, body, [class*="css"] { 
      font-family: 'Inter', sans-serif; 
  }
  
  /* Main Container - Uses Streamlit Theme Variables */
  .dashboard-container {
      background: var(--background-color);
      border-radius: 12px;
      padding: 24px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
      border: 1px solid var(--secondary-background-color);
      margin-bottom: 2rem;
  }

  /* Table Wrapper */
  .moe-table { 
      border-collapse: separate; 
      border-spacing: 0;
      width: 100%; 
      font-size: 14px; 
      border-radius: 8px;
      overflow: hidden;
      border: 1px solid var(--secondary-background-color);
  }

  /* Header Styles */
  .moe-table thead tr th {
      background: var(--secondary-background-color);
      color: var(--text-color);
      font-weight: 600;
      text-align: center;
      padding: 12px 16px;
      border-bottom: 1px solid var(--background-color);
      border-right: 1px solid var(--background-color);
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
  }
  .moe-table thead tr th:last-child {
      border-right: none;
  }
  .moe-table thead tr.date-row th.window-header {
      background: rgba(29, 78, 216, 0.15); /* Soft transparent blue */
      color: var(--primary-color);
  }

  /* Data Rows */
  .moe-table tbody tr td {
      padding: 12px 16px;
      border-bottom: 1px solid var(--secondary-background-color);
      border-right: 1px solid var(--secondary-background-color);
      text-align: center;
      color: var(--text-color);
      font-variant-numeric: tabular-nums;
  }
  .moe-table tbody tr td:last-child {
      border-right: none;
  }
  .moe-table tbody tr:last-child td {
      border-bottom: none;
  }
  .moe-table tbody tr td.metric-name {
      text-align: left;
      font-weight: 600;
      color: var(--text-color);
      white-space: nowrap;
      background: var(--secondary-background-color);
      opacity: 0.9;
  }
  
  /* Hover effects */
  .moe-table tbody tr:hover td { 
      background: rgba(128, 128, 128, 0.05); 
  }
  .moe-table tbody tr:hover td.metric-name { 
      background: rgba(128, 128, 128, 0.15); 
  }

  /* Typography */
  .dash-title {
      font-size: 24px; 
      font-weight: 700; 
      color: var(--text-color);
      margin-bottom: 8px;
      letter-spacing: -0.02em;
  }
  .dash-sub {
      font-size: 14px; 
      color: var(--text-color);
      opacity: 0.7;
      margin-bottom: 24px;
      display: flex;
      align-items: center;
      gap: 8px;
  }

  /* Badges */
  .badge {
      display: inline-flex;
      align-items: center;
      padding: 4px 12px;
      border-radius: 9999px;
      font-size: 12px;
      font-weight: 600;
  }
  .badge-pronto  { background: rgba(37, 99, 235, 0.15); color: #3b82f6; border: 1px solid rgba(37, 99, 235, 0.3); }
  .badge-snabbit { background: rgba(219, 39, 119, 0.15); color: #ec4899; border: 1px solid rgba(219, 39, 119, 0.3); }
</style>
""", unsafe_allow_html=True)


# ─── FETCH RAW DATA ───────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner="Syncing with database…")
def fetch_redash() -> pd.DataFrame:
    url = f"{REDASH_BASE_URL}/api/queries/{QUERY_ID}/results"
    resp = requests.get(url, params={"api_key": REDASH_API_KEY}, timeout=60)
    resp.raise_for_status()
    rows = resp.json()["query_result"]["data"]["rows"]
    return pd.DataFrame(rows)


# ─── COMPUTE METRICS ──────────────────────────────────────────────────────────
def compute_metrics(df: pd.DataFrame, client_filter: list) -> tuple:
    today = date.today()

    df["milestone_date"] = pd.to_datetime(df["milestone_date"]).dt.date
    df = df[df["client"].str.lower().isin([c.lower() for c in client_filter])].copy()

    windows = {
        f"{today.strftime('%Y-%m-%d')}":       today,
        f"{(today - timedelta(1)).strftime('%Y-%m-%d')}": today - timedelta(1),
        f"L3D ({(today-timedelta(3)).strftime('%m-%d')})": today - timedelta(3),
        f"L7D ({(today-timedelta(7)).strftime('%m-%d')})": today - timedelta(7),
    }

    lead = (
        df.groupby(["phone_number", "assignee_id", "milestone_date"])
        .apply(lambda g: pd.Series({
            "has_app_dl":   int((g["milestone_name"] == "mitra_app_download").any()),
            "has_training": int((g["milestone_name"] == "training_completed").any()),
            "has_fod":      int((g["milestone_name"] == "first_date_of_work").any()),
        }))
        .reset_index()
    )

    vl_first = (
        df.groupby("assignee_id")["milestone_date"]
        .min()
        .reset_index()
        .rename(columns={"milestone_date": "first_referral_date"})
    )
    fod_rows = df[df["milestone_name"] == "first_date_of_work"]
    vl_first_fod = (
        fod_rows.groupby("assignee_id")["milestone_date"]
        .min()
        .reset_index()
        .rename(columns={"milestone_date": "first_fod_date"})
    )
    vl = vl_first.merge(vl_first_fod, on="assignee_id", how="left")
    lead = lead.merge(vl, on="assignee_id", how="left")

    results = {}
    metric_defs = [
        "VL Count (App Download)",
        "Lead Count",
        "App Download",
        "App Download (Unique)",
        "Training Completed",
        "FT Done",
        "New VL Count (Leads)",
        "New VL Count (PLs)",
    ]

    for metric in metric_defs:
        results[metric] = {}

    for label, cutoff in windows.items():
        is_today = label.startswith(str(today))
        is_yesterday = label.startswith(str(today - timedelta(1)))

        if is_today:
            mask = lead["milestone_date"] == today
        elif is_yesterday:
            mask = lead["milestone_date"] == (today - timedelta(1))
        else:
            mask = lead["milestone_date"] >= cutoff

        w = lead[mask]

        results["VL Count (App Download)"][label]  = w[w["has_app_dl"] == 1]["assignee_id"].nunique()
        results["Lead Count"][label]               = w["phone_number"].nunique()
        results["App Download"][label]             = w[w["has_app_dl"] == 1]["phone_number"].nunique()
        results["App Download (Unique)"][label]    = w[w["has_app_dl"] == 1]["phone_number"].nunique()
        results["Training Completed"][label]       = w[w["has_training"] == 1]["phone_number"].nunique()
        results["FT Done"][label]                  = w[w["has_fod"] == 1]["phone_number"].nunique()

        if is_today:
            vl_mask = vl["first_referral_date"] == today
        elif is_yesterday:
            vl_mask = vl["first_referral_date"] == (today - timedelta(1))
        else:
            vl_mask = vl["first_referral_date"] >= cutoff
        results["New VL Count (Leads)"][label] = vl[vl_mask]["assignee_id"].nunique()

        vl_fod = vl.dropna(subset=["first_fod_date"])
        if is_today:
            vl_fod_mask = vl_fod["first_fod_date"] == today
        elif is_yesterday:
            vl_fod_mask = vl_fod["first_fod_date"] == (today - timedelta(1))
        else:
            vl_fod_mask = vl_fod["first_fod_date"] >= cutoff
        results["New VL Count (PLs)"][label] = vl_fod[vl_fod_mask]["assignee_id"].nunique()

    return results, list(windows.keys())


# ─── RENDER TABLE ─────────────────────────────────────────────────────────────
def render_table(results: dict, window_labels: list, title: str):
    today = date.today()
    yesterday = today - timedelta(1)

    # Note: Intentionally zero-indented HTML to prevent Markdown parser from triggering a code block
    header_date_row = f"""<tr class='date-row'>
<th rowspan='2' class='metric-label' style='text-align: left; vertical-align: bottom;'>Metrics Overview</th>
<th>{today.strftime('%b %d, %Y')}</th>
<th>{yesterday.strftime('%b %d, %Y')}</th>
<th class='window-header'>{(today - timedelta(3)).strftime('%b %d')}</th>
<th class='window-header'>{(today - timedelta(7)).strftime('%b %d')}</th>
</tr>"""

    header_label_row = f"""<tr class='label-row'>
<th>Today</th>
<th>Yesterday</th>
<th class='window-header'>L3D</th>
<th class='window-header'>L7D</th>
</tr>"""

    body = ""
    for metric, vals in results.items():
        body += "<tr>"
        body += f"<td class='metric-name'>{metric}</td>"
        for label in window_labels:
            v = vals.get(label, 0)
            body += f"<td>{v:,}</td>"
        body += "</tr>\n"

    # Fully flushed HTML to bypass markdown code formatting
    html = f"""<div class='dashboard-container'>
<div style='margin-bottom:20px'>
<div class='dash-title'>{title}</div>
</div>
<div style='overflow-x: auto;'>
<table class='moe-table'>
<thead>
{header_date_row}
{header_label_row}
</thead>
<tbody>
{body}
</tbody>
</table>
</div>
</div>"""
    st.markdown(html, unsafe_allow_html=True)


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    today = date.today()

    st.markdown(f"""<div class='dash-title'>🚀 MOE Performance Dashboard</div>
<div class='dash-sub'>
<span class='badge badge-pronto'>Pronto</span>
<span class='badge badge-snabbit'>Snabbit</span>
<span style='opacity: 0.5;'>|</span>
<span>Live as of <b>{today.strftime('%B %d, %Y')}</b></span>
</div>""", unsafe_allow_html=True)

    # ── Sidebar Controls ──
    with st.sidebar:
        st.markdown("### ⚙️ Filters")
        
        clients = st.multiselect(
            "Select Clients", 
            ["pronto", "snabbit"], 
            default=["pronto", "snabbit"],
            format_func=lambda x: x.capitalize()
        )
        
        view = st.radio(
            "Display Mode", 
            ["Combined", "Pronto only", "Snabbit only"]
        )
        
        st.divider()
        if st.button("🔄 Force Data Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # ── Fetch Data ──
    try:
        df_raw = fetch_redash()
    except Exception as e:
        st.error("⚠️ Failed to establish a connection with the database.")
        st.stop()

    if df_raw.empty:
        st.warning("No data found for the current configuration.")
        st.stop()

    # ── Render Views ──
    if view == "Combined":
        results, labels = compute_metrics(df_raw, clients)
        render_table(results, labels, "Pronto + Snabbit (Combined Data)")

    elif view == "Pronto only":
        results, labels = compute_metrics(df_raw, ["pronto"])
        render_table(results, labels, "Pronto Performance")

    else:
        results, labels = compute_metrics(df_raw, ["snabbit"])
        render_table(results, labels, "Snabbit Performance")

    st.markdown(
        f"<div style='text-align: right; font-size:12px; color:var(--text-color); opacity: 0.6; margin-top: 16px;'>"
        f"Data automatically caches for 5 minutes. Last synced: {pd.Timestamp.now().strftime('%H:%M:%S')}</div>", 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
