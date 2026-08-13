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

# ─── ULTRA PREMIUM CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  
  html, body, [class*="css"] { 
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; 
  }
  
  /* Hide Streamlit default styling elements for a cleaner look */
  header[data-testid="stHeader"] { background: transparent; }
  
  /* Main Card Container */
  .premium-card {
      background: var(--background-color);
      border-radius: 16px;
      padding: 32px;
      margin-bottom: 2rem;
      /* Soft Apple-style layered shadow for depth */
      box-shadow: 
        0 4px 6px -1px rgba(0, 0, 0, 0.05),
        0 10px 15px -3px rgba(0, 0, 0, 0.025),
        0 25px 50px -12px rgba(0, 0, 0, 0.05);
      border: 1px solid rgba(128, 128, 128, 0.15);
      position: relative;
      overflow: hidden;
  }

  /* Table Reset & Setup */
  .moe-table { 
      border-collapse: collapse; 
      width: 100%; 
      font-size: 14px; 
      margin-top: 8px;
  }

  /* Header Typography & Styling */
  .moe-table thead tr th {
      color: var(--text-color);
      opacity: 0.6;
      font-weight: 600;
      text-align: right;
      padding: 16px 24px;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      border-bottom: 1px solid rgba(128, 128, 128, 0.15);
  }
  .moe-table thead tr th:first-child {
      text-align: left;
  }
  
  /* Special Highlight for Window Columns */
  .moe-table thead tr.date-row th.window-header,
  .moe-table thead tr.label-row th.window-header {
      color: var(--primary-color);
      opacity: 0.9;
      background: rgba(128, 128, 128, 0.03);
  }

  /* Data Rows */
  .moe-table tbody tr {
      transition: all 0.2s ease-in-out;
      border-bottom: 1px solid rgba(128, 128, 128, 0.08);
  }
  .moe-table tbody tr:last-child {
      border-bottom: none;
  }
  .moe-table tbody tr td {
      padding: 16px 24px;
      text-align: right;
      color: var(--text-color);
      opacity: 0.85;
      /* Tabular nums align digits perfectly */
      font-variant-numeric: tabular-nums;
      font-feature-settings: "tnum";
      font-size: 15px;
  }
  .moe-table tbody tr td.metric-name {
      text-align: left;
      font-weight: 500;
      color: var(--text-color);
      opacity: 1;
      white-space: nowrap;
      font-size: 14px;
  }
  
  /* L3D / L7D Column subtle backgrounds */
  .moe-table tbody tr td.window-data {
      background: rgba(128, 128, 128, 0.02);
  }

  /* Hover Effects */
  .moe-table tbody tr:hover { 
      background: var(--secondary-background-color);
      transform: translateY(-1px);
      box-shadow: 0 2px 4px rgba(0,0,0,0.02);
      border-radius: 8px;
  }
  
  /* Title & Subtitle */
  .gradient-title {
      font-size: 28px; 
      font-weight: 800; 
      margin-bottom: 4px;
      letter-spacing: -0.03em;
      /* Premium Stripe-like gradient text */
      background: linear-gradient(135deg, var(--text-color) 0%, var(--primary-color) 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      display: inline-block;
  }
  .dash-sub {
      font-size: 13px; 
      color: var(--text-color);
      opacity: 0.6;
      margin-bottom: 32px;
      display: flex;
      align-items: center;
      gap: 12px;
      font-weight: 500;
  }

  /* Vercel-style Pill Badges */
  .badge {
      display: inline-flex;
      align-items: center;
      padding: 2px 10px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.02em;
      text-transform: uppercase;
  }
  /* Using dynamic RGBA colors to look great in both dark/light modes */
  .badge-pronto  { background: rgba(59, 130, 246, 0.1); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.2); }
  .badge-snabbit { background: rgba(236, 72, 153, 0.1); color: #ec4899; border: 1px solid rgba(236, 72, 153, 0.2); }
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

    # HTML explicitly left-aligned with no indentation to prevent markdown <pre> rendering
    header_date_row = f"""<tr class='date-row'>
<th rowspan='2' style='text-align: left; vertical-align: bottom; border-bottom: none;'>Key Performance Indicator</th>
<th>{today.strftime('%b %d')}</th>
<th>{yesterday.strftime('%b %d')}</th>
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
        
        # Parse through the dates, adding the specific highlight class to L3D/L7D
        for idx, label in enumerate(window_labels):
            v = vals.get(label, 0)
            formatted_val = f"{v:,}" if v > 0 else "<span style='opacity: 0.2;'>-</span>"
            css_class = "window-data" if idx >= 2 else ""
            body += f"<td class='{css_class}'>{formatted_val}</td>"
        
        body += "</tr>\n"

    html = f"""<div class='premium-card'>
<div class='gradient-title'>{title}</div>
<div style='overflow-x: auto; margin-top: 16px;'>
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

    # Premium top banner header
    st.markdown(f"""
<div style='margin-bottom: 2rem; padding-left: 8px;'>
    <div style='font-size: 32px; font-weight: 800; letter-spacing: -0.04em; color: var(--text-color);'>
        MOE Performance
    </div>
    <div class='dash-sub'>
        <span class='badge badge-pronto'>Pronto</span>
        <span class='badge badge-snabbit'>Snabbit</span>
        <span style='opacity: 0.3;'>•</span>
        <span>Live snapshot as of {today.strftime('%B %d, %Y')}</span>
    </div>
</div>
""", unsafe_allow_html=True)

    # ── Sidebar Controls ──
    with st.sidebar:
        st.markdown("<h3 style='font-weight: 700; letter-spacing: -0.02em;'>Configuration</h3>", unsafe_allow_html=True)
        
        clients = st.multiselect(
            "Target Organizations", 
            ["pronto", "snabbit"], 
            default=["pronto", "snabbit"],
            format_func=lambda x: x.capitalize()
        )
        
        view = st.radio(
            "Display Layout", 
            ["Combined Overview", "Pronto Isolated", "Snabbit Isolated"]
        )
        
        st.divider()
        if st.button("⚡ Force Sync Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # ── Fetch Data ──
    try:
        df_raw = fetch_redash()
    except Exception as e:
        st.error("⚠️ Failed to establish a secure connection with the database.")
        st.stop()

    if df_raw.empty:
        st.warning("No operational data found for the current configuration.")
        st.stop()

    # ── Render Views ──
    if view == "Combined Overview":
        results, labels = compute_metrics(df_raw, clients)
        render_table(results, labels, "Combined Intelligence")

    elif view == "Pronto Isolated":
        results, labels = compute_metrics(df_raw, ["pronto"])
        render_table(results, labels, "Pronto Analytics")

    else:
        results, labels = compute_metrics(df_raw, ["snabbit"])
        render_table(results, labels, "Snabbit Analytics")

    # Premium subtle footer
    st.markdown(
        f"<div style='text-align: right; font-size: 12px; font-weight: 500; color: var(--text-color); opacity: 0.4; margin-top: 1rem; padding-right: 8px;'>"
        f"Real-time cache cycle: 5m &nbsp;·&nbsp; Last sync: {pd.Timestamp.now().strftime('%H:%M:%S')}</div>", 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
