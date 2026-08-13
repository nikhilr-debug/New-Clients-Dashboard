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
    page_title="Operations | MOE Command Center",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── ULTRA PREMIUM LINEAR/VERCEL THEME ────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');
  
  /* Force Dark Mode & Background Grid */
  html, body, [class*="css"], .stApp { 
      font-family: 'Inter', -apple-system, sans-serif !important; 
      background-color: #09090b !important; /* Deep Zinc */
      color: #ededed !important;
  }
  
  /* Vercel-style subtle background grid */
  .stApp {
      background-image: linear-gradient(to right, rgba(255,255,255,0.03) 1px, transparent 1px),
                        linear-gradient(to bottom, rgba(255,255,255,0.03) 1px, transparent 1px);
      background-size: 40px 40px;
  }

  /* Hide Streamlit default UI elements */
  header[data-testid="stHeader"] { background: transparent !important; }
  .stDeployButton { display: none; }
  
  /* Premium Glassmorphic Card */
  .premium-card {
      background: linear-gradient(145deg, rgba(24, 24, 27, 0.9) 0%, rgba(9, 9, 11, 0.95) 100%);
      border-radius: 16px;
      padding: 32px;
      margin-bottom: 2rem;
      border: 1px solid rgba(255, 255, 255, 0.08);
      box-shadow: 
        0 0 0 1px rgba(0, 0, 0, 0.5), 
        0 20px 40px -10px rgba(0, 0, 0, 0.7),
        inset 0 1px 0 rgba(255, 255, 255, 0.05);
      backdrop-filter: blur(12px);
      position: relative;
      overflow: hidden;
  }

  /* Table Reset & Setup */
  .moe-table { 
      border-collapse: collapse; 
      width: 100%; 
      font-size: 14px; 
      margin-top: 12px;
  }

  /* Header Typography & Styling */
  .moe-table thead tr th {
      color: #a1a1aa;
      font-weight: 600;
      text-align: right;
      padding: 16px 24px;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  }
  .moe-table thead tr th:first-child {
      text-align: left;
  }
  
  /* Glowing Window Columns */
  .moe-table thead tr.date-row th.window-header,
  .moe-table thead tr.label-row th.window-header {
      color: #38bdf8;
      background: rgba(56, 189, 248, 0.03);
  }

  /* Data Rows */
  .moe-table tbody tr {
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  }
  .moe-table tbody tr:last-child {
      border-bottom: none;
  }
  .moe-table tbody tr td {
      padding: 18px 24px;
      text-align: right;
      color: #f8fafc;
      /* JetBrains Mono for perfect tabular alignment & elite dev look */
      font-family: 'JetBrains Mono', monospace;
      font-weight: 500;
      font-size: 14px;
      letter-spacing: -0.02em;
  }
  .moe-table tbody tr td.metric-name {
      text-align: left;
      font-family: 'Inter', sans-serif;
      font-weight: 600;
      color: #e4e4e7;
      white-space: nowrap;
      font-size: 14px;
  }
  
  /* Numbers Highlight */
  .moe-table tbody tr td:not(.metric-name) {
      color: #60a5fa; /* Electric Blue for numbers */
      text-shadow: 0 0 12px rgba(96, 165, 250, 0.2);
  }
  .moe-table tbody tr td.window-data {
      background: rgba(56, 189, 248, 0.02);
      color: #38bdf8;
  }

  /* Hover Effects */
  .moe-table tbody tr:hover { 
      background: rgba(255, 255, 255, 0.03);
      transform: scale(1.002);
      border-radius: 8px;
  }
  .moe-table tbody tr:hover td.metric-name {
      color: #ffffff;
  }
  
  /* Titles & Typography */
  .gradient-title {
      font-size: 32px; 
      font-weight: 800; 
      margin-bottom: 4px;
      letter-spacing: -0.04em;
      background: linear-gradient(135deg, #ffffff 0%, #a1a1aa 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      display: inline-block;
  }
  .dash-sub {
      font-size: 13px; 
      color: #71717a;
      margin-bottom: 32px;
      display: flex;
      align-items: center;
      gap: 12px;
      font-weight: 500;
  }

  /* Neon Pill Badges */
  .badge {
      display: inline-flex;
      align-items: center;
      padding: 4px 12px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      box-shadow: 0 0 10px rgba(0,0,0,0.5);
  }
  .badge-pronto  { background: rgba(59, 130, 246, 0.1); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.4); text-shadow: 0 0 8px rgba(96, 165, 250, 0.5); }
  .badge-snabbit { background: rgba(236, 72, 153, 0.1); color: #f472b6; border: 1px solid rgba(236, 72, 153, 0.4); text-shadow: 0 0 8px rgba(244, 114, 182, 0.5); }
  
  /* Sidebar Customization */
  [data-testid="stSidebar"] {
      background-color: #09090b !important;
      border-right: 1px solid rgba(255,255,255,0.05) !important;
  }
</style>
""", unsafe_allow_html=True)


# ─── FETCH RAW DATA ───────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner="Decrypting live data stream…")
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

        if is_today: mask = lead["milestone_date"] == today
        elif is_yesterday: mask = lead["milestone_date"] == (today - timedelta(1))
        else: mask = lead["milestone_date"] >= cutoff

        w = lead[mask]

        results["VL Count (App Download)"][label]  = w[w["has_app_dl"] == 1]["assignee_id"].nunique()
        results["Lead Count"][label]               = w["phone_number"].nunique()
        results["App Download"][label]             = w[w["has_app_dl"] == 1]["phone_number"].nunique()
        results["App Download (Unique)"][label]    = w[w["has_app_dl"] == 1]["phone_number"].nunique()
        results["Training Completed"][label]       = w[w["has_training"] == 1]["phone_number"].nunique()
        results["FT Done"][label]                  = w[w["has_fod"] == 1]["phone_number"].nunique()

        vl_mask = vl["first_referral_date"] == today if is_today else (vl["first_referral_date"] == (today - timedelta(1)) if is_yesterday else vl["first_referral_date"] >= cutoff)
        results["New VL Count (Leads)"][label] = vl[vl_mask]["assignee_id"].nunique()

        vl_fod = vl.dropna(subset=["first_fod_date"])
        vl_fod_mask = vl_fod["first_fod_date"] == today if is_today else (vl_fod["first_fod_date"] == (today - timedelta(1)) if is_yesterday else vl_fod["first_fod_date"] >= cutoff)
        results["New VL Count (PLs)"][label] = vl_fod[vl_fod_mask]["assignee_id"].nunique()

    return results, list(windows.keys())


# ─── RENDER TABLE ─────────────────────────────────────────────────────────────
def render_table(results: dict, window_labels: list, title: str):
    today = date.today()
    yesterday = today - timedelta(1)

    # HTML strictly left-aligned to prevent markdown block parsing
    header_date_row = f"""<tr class='date-row'>
<th rowspan='2' style='text-align: left; vertical-align: bottom; border-bottom: none;'>Command Metrics</th>
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
        body += "<tr>\n"
        body += f"<td class='metric-name'>{metric}</td>\n"
        
        for idx, label in enumerate(window_labels):
            v = vals.get(label, 0)
            # Display explicitly as 0 if missing/null, with a subtle dim to keep it clean
            formatted_val = f"{v:,}" if v > 0 else "<span style='opacity: 0.4;'>0</span>"
            css_class = "window-data" if idx >= 2 else ""
            body += f"<td class='{css_class}'>{formatted_val}</td>\n"
        
        body += "</tr>\n"

    html = f"""<div class='premium-card'>
<div class='gradient-title'>{title}</div>
<div style='overflow-x: auto; margin-top: 24px;'>
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

    # Premium Hero Banner
    st.markdown(f"""
<div style='margin-bottom: 2.5rem; padding-left: 8px;'>
    <div style='font-size: 36px; font-weight: 800; letter-spacing: -0.05em; color: #ffffff;'>
        Operations Performance
    </div>
    <div class='dash-sub' style='margin-top: 8px;'>
        <span class='badge badge-pronto'>Pronto</span>
        <span class='badge badge-snabbit'>Snabbit</span>
        <span style='color: #3f3f46;'>|</span>
        <span style='color: #a1a1aa;'>Live Projection &bull; {today.strftime('%B %d, %Y')}</span>
    </div>
</div>
""", unsafe_allow_html=True)

    # ── Sidebar Controls ──
    with st.sidebar:
        st.markdown("<h3 style='font-weight: 700; letter-spacing: -0.03em; color: #ffffff;'>Global Filters</h3>", unsafe_allow_html=True)
        
        clients = st.multiselect(
            "Target Organizations", 
            ["pronto", "snabbit"], 
            default=["pronto", "snabbit"],
            format_func=lambda x: x.upper()
        )
        
        view = st.radio(
            "Display Layout", 
            ["Combined Stream", "Pronto Isolated", "Snabbit Isolated"]
        )
        
        st.divider()
        if st.button("⚡ Force Sync Redash", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
            
        st.markdown(
            f"<div style='font-size: 11px; color: #52525b; margin-top: 16px; text-align: center; font-weight: 600;'>"
            f"SYSTEM CLOCK: {pd.Timestamp.now().strftime('%H:%M:%S IST')}</div>", 
            unsafe_allow_html=True
        )

    # ── Fetch Data ──
    try:
        df_raw = fetch_redash()
    except Exception as e:
        st.error("⚠️ Connection Refused. Failed to sync with Vahan telemetry.")
        st.stop()

    if df_raw.empty:
        st.warning("No operational data matrix found for the current configuration.")
        st.stop()

    # ── Render Views ──
    if view == "Combined Stream":
        results, labels = compute_metrics(df_raw, clients)
        render_table(results, labels, "Combined Fleet Intelligence")

    elif view == "Pronto Isolated":
        results, labels = compute_metrics(df_raw, ["pronto"])
        render_table(results, labels, "Pronto Telemetry")

    else:
        results, labels = compute_metrics(df_raw, ["snabbit"])
        render_table(results, labels, "Snabbit Telemetry")

    # Footer
    st.markdown(
        f"<div style='text-align: right; font-size: 11px; font-weight: 600; color: #52525b; margin-top: 2rem; padding-right: 8px; letter-spacing: 0.05em;'>"
        f"CACHE CYCLE: 5M &nbsp;|&nbsp; NEXT REFRESH PENDING</div>", 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
