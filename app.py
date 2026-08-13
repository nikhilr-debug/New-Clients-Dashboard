import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta

# ─── CONFIG (HIDDEN FROM UI) ──────────────────────────────────────────────────
REDASH_BASE_URL = "https://redash.vahan.co"
REDASH_API_KEY  = "4aFm2iOoyx8I91svQccdeZr0jmaiUsMFSRinZcmu"       
QUERY_ID        = 18055                                          

# ─── CLIENT & MILESTONE DEFINITIONS ───────────────────────────────────────────
CLIENT_MILESTONES = {
    "big basket": [
        "activation_date",
        "first_date_of_work",
        "marked_unique",
        "onboarding_eligibility",
    ],
    "porter": [
        "activation_date",
        "document_successfully_uploaded_date",
        "first_date_of_work",
        "marked_unique",
        "mitra_app_download",
        "onboarding_eligibility",
    ],
    "rapido": [
        "first_date_of_work",
        "marked_unique",
        "mitra_app_download",
        "profile_pic_uploaded",
        "signup_date",
    ],
    "uber": [
        "first_date_of_work",
        "marked_unique",
        "mitra_app_download",
        "signup_date",
    ],
    "pronto": [
        "mitra_app_download",
        "training_completed",
        "first_date_of_work",
    ],
    "snabbit": [
        "mitra_app_download",
        "training_completed",
        "first_date_of_work",
    ],
}

MILESTONE_DISPLAY_NAMES = {
    "activation_date": "Activation Date",
    "document_successfully_uploaded_date": "Document Uploaded",
    "first_date_of_work": "First Date of Work (FT)",
    "marked_unique": "Marked Unique",
    "mitra_app_download": "Mitra App Download",
    "onboarding_eligibility": "Onboarding Eligibility",
    "profile_pic_uploaded": "Profile Pic Uploaded",
    "signup_date": "Signup Date",
    "training_completed": "Training Completed",
}

# ─── PAGE SETUP ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Operations | Multi-Client MOE Dashboard",
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
      background-color: #09090b !important;
      color: #ededed !important;
  }
  
  /* Vercel-style background grid */
  .stApp {
      background-image: linear-gradient(to right, rgba(255,255,255,0.03) 1px, transparent 1px),
                        linear-gradient(to bottom, rgba(255,255,255,0.03) 1px, transparent 1px);
      background-size: 40px 40px;
  }

  /* Hide Streamlit default header elements */
  header[data-testid="stHeader"] { background: transparent !important; }
  .stDeployButton { display: none; }
  
  /* Premium Glassmorphic Card */
  .premium-card {
      background: linear-gradient(145deg, rgba(24, 24, 27, 0.9) 0%, rgba(9, 9, 11, 0.95) 100%);
      border-radius: 16px;
      padding: 28px;
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
      padding: 14px 20px;
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
      padding: 16px 20px;
      text-align: right;
      color: #f8fafc;
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
      color: #60a5fa;
      text-shadow: 0 0 12px rgba(96, 165, 250, 0.2);
  }
  .moe-table tbody tr td.window-data {
      background: rgba(56, 189, 248, 0.02);
      color: #38bdf8;
  }

  /* Hover Effects */
  .moe-table tbody tr:hover { 
      background: rgba(255, 255, 255, 0.03);
      transform: scale(1.001);
  }
  .moe-table tbody tr:hover td.metric-name {
      color: #ffffff;
  }
  
  /* Titles & Typography */
  .card-title {
      font-size: 22px; 
      font-weight: 800; 
      margin-bottom: 4px;
      letter-spacing: -0.03em;
      color: #ffffff;
      display: flex;
      align-items: center;
      gap: 10px;
  }
  .dash-sub {
      font-size: 13px; 
      color: #71717a;
      margin-bottom: 24px;
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      font-weight: 500;
  }

  /* Neon Pill Badges */
  .badge {
      display: inline-flex;
      align-items: center;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      box-shadow: 0 0 10px rgba(0,0,0,0.5);
  }
  .badge-client { background: rgba(59, 130, 246, 0.1); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.4); }
  
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


# ─── COMPUTE CLIENT METRICS ───────────────────────────────────────────────────
def compute_client_metrics(df: pd.DataFrame, client_name: str) -> tuple:
    today = date.today()

    df_client = df[df["client"].astype(str).str.lower().str.strip() == client_name.lower().strip()].copy()

    if df_client.empty:
        return {}, []

    df_client["milestone_date"] = pd.to_datetime(df_client["milestone_date"]).dt.date

    windows = {
        f"{today.strftime('%Y-%m-%d')}":       today,
        f"{(today - timedelta(1)).strftime('%Y-%m-%d')}": today - timedelta(1),
        f"L3D ({(today-timedelta(3)).strftime('%m-%d')})": today - timedelta(3),
        f"L7D ({(today-timedelta(7)).strftime('%m-%d')})": today - timedelta(7),
    }

    client_key = client_name.lower().strip()
    if client_key in CLIENT_MILESTONES:
        milestones = CLIENT_MILESTONES[client_key]
    else:
        milestones = sorted(df_client["milestone_name"].dropna().unique().tolist())

    results = {}
    results["Total Leads"] = {}

    for m in milestones:
        display_name = MILESTONE_DISPLAY_NAMES.get(m, m.replace('_', ' ').title())
        results[display_name] = {}

    for label, cutoff in windows.items():
        is_today = label.startswith(str(today))
        is_yesterday = label.startswith(str(today - timedelta(1)))

        if is_today:
            w = df_client[df_client["milestone_date"] == today]
        elif is_yesterday:
            w = df_client[df_client["milestone_date"] == (today - timedelta(1))]
        else:
            w = df_client[df_client["milestone_date"] >= cutoff]

        results["Total Leads"][label] = w["phone_number"].nunique() if "phone_number" in w.columns else len(w)

        for m in milestones:
            display_name = MILESTONE_DISPLAY_NAMES.get(m, m.replace('_', ' ').title())
            m_df = w[w["milestone_name"].astype(str).str.lower().str.strip() == m.lower().strip()]
            results[display_name][label] = m_df["phone_number"].nunique() if "phone_number" in m_df.columns else len(m_df)

    return results, list(windows.keys())


# ─── RENDER TABLE ─────────────────────────────────────────────────────────────
def render_table(results: dict, window_labels: list, title: str):
    if not results:
        st.info(f"No active milestone data found for **{title}**.")
        return

    today = date.today()
    yesterday = today - timedelta(1)

    header_date_row = f"""<tr class='date-row'>
<th rowspan='2' style='text-align: left; vertical-align: bottom; border-bottom: none;'>Milestone / Metric</th>
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
            formatted_val = f"{v:,}" if v > 0 else "<span style='opacity: 0.4;'>0</span>"
            css_class = "window-data" if idx >= 2 else ""
            body += f"<td class='{css_class}'>{formatted_val}</td>\n"
        
        body += "</tr>\n"

    html = f"""<div class='premium-card'>
<div class='card-title'><span>🏢</span> {title}</div>
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

    all_available_clients = ["big basket", "porter", "rapido", "uber", "pronto", "snabbit"]

    st.markdown(f"""
<div style='margin-bottom: 2rem; padding-left: 4px;'>
    <div style='font-size: 34px; font-weight: 800; letter-spacing: -0.04em; color: #ffffff;'>
        Operations Command Center
    </div>
    <div class='dash-sub' style='margin-top: 8px;'>
        {' '.join([f"<span class='badge badge-client'>{c.title()}</span>" for c in all_available_clients])}
        <span style='color: #3f3f46;'>|</span>
        <span style='color: #a1a1aa;'>Live Data Stream &bull; {today.strftime('%B %d, %Y')}</span>
    </div>
</div>
""", unsafe_allow_html=True)

    # ── Sidebar Controls ──
    with st.sidebar:
        st.markdown("<h3 style='font-weight: 700; letter-spacing: -0.03em; color: #ffffff;'>Filters</h3>", unsafe_allow_html=True)
        
        selected_clients = st.multiselect(
            "Select Clients to Display", 
            all_available_clients, 
            default=all_available_clients,
            format_func=lambda x: x.title()
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

    if not selected_clients:
        st.warning("Please select at least one client from the sidebar.")
        st.stop()

    # ── Client Tabs View ──
    tab_titles = ["All Clients Overview"] + [c.title() for c in selected_clients]
    tabs = st.tabs(tab_titles)

    # Tab 1: All Selected Clients Stacked
    with tabs[0]:
        for client in selected_clients:
            results, labels = compute_client_metrics(df_raw, client)
            render_table(results, labels, f"{client.title()} Performance")

    # Tabs 2+: Individual Client Tables
    for idx, client in enumerate(selected_clients):
        with tabs[idx + 1]:
            results, labels = compute_client_metrics(df_raw, client)
            render_table(results, labels, f"{client.title()} Performance")

    # Footer
    st.markdown(
        f"<div style='text-align: right; font-size: 11px; font-weight: 600; color: #52525b; margin-top: 2rem; padding-right: 8px; letter-spacing: 0.05em;'>"
        f"CACHE CYCLE: 5M &nbsp;|&nbsp; REFRESH PENDING</div>", 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
