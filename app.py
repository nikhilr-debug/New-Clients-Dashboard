import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta

# ─── CONFIG ───────────────────────────────────────────────────────────────────
REDASH_BASE_URL = "https://redash.vahan.co"
REDASH_API_KEY  = "4aFm2iOoyx8I91svQccdeZr0jmaiUsMFSRinZcmu"       # ← replace
QUERY_ID        = 18055                          # ← replace with your Redash query ID

# ─── PAGE SETUP ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Pronto & Snabbit – MOE Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
  /* ── global ── */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  .block-container { padding: 1.5rem 2rem; }

  /* ── table wrapper ── */
  .moe-table { border-collapse: collapse; width: 100%; font-size: 13px; }

  /* ── header rows ── */
  .moe-table thead tr.date-row th {
    background: #BDD7EE;
    color: #1a2b3c;
    font-weight: 700;
    text-align: center;
    padding: 6px 10px;
    border: 1px solid #9ab8d4;
    font-size: 12px;
  }
  .moe-table thead tr.date-row th.window-header {
    background: #2E75B6;
    color: white;
  }
  .moe-table thead tr.label-row th {
    background: #BDD7EE;
    color: #1a2b3c;
    font-weight: 700;
    text-align: center;
    padding: 6px 10px;
    border: 1px solid #9ab8d4;
    font-size: 12px;
  }
  .moe-table thead tr.label-row th.metric-label {
    text-align: left;
  }

  /* ── data rows ── */
  .moe-table tbody tr td {
    padding: 5px 10px;
    border: 1px solid #d0d0d0;
    text-align: center;
    color: #1a1a1a;
  }
  .moe-table tbody tr td.metric-name {
    text-align: left;
    font-weight: 500;
    color: #1a2b3c;
    white-space: nowrap;
  }
  .moe-table tbody tr:nth-child(even) td { background: #f5f9fd; }
  .moe-table tbody tr:nth-child(odd)  td { background: #ffffff; }
  .moe-table tbody tr:hover td { background: #e8f2fb; }

  /* ── title ── */
  .dash-title {
    font-size: 20px; font-weight: 700; color: #1a2b3c;
    margin-bottom: 4px;
  }
  .dash-sub {
    font-size: 13px; color: #666; margin-bottom: 18px;
  }

  /* ── client badge ── */
  .badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    margin-right: 6px;
  }
  .badge-pronto  { background: #dbeafe; color: #1d4ed8; }
  .badge-snabbit { background: #fce7f3; color: #be185d; }
</style>
""", unsafe_allow_html=True)


# ─── FETCH RAW DATA ───────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner="Fetching data from Redash…")
def fetch_redash(query_id: int, api_key: str) -> pd.DataFrame:
    url = f"{REDASH_BASE_URL}/api/queries/{query_id}/results"
    resp = requests.get(url, params={"api_key": api_key}, timeout=60)
    resp.raise_for_status()
    rows = resp.json()["query_result"]["data"]["rows"]
    return pd.DataFrame(rows)


# ─── COMPUTE METRICS ──────────────────────────────────────────────────────────
def compute_metrics(df: pd.DataFrame, client_filter: list[str]) -> dict:
    """
    Expects columns from milestones_data raw export:
      phone_number, assignee_id, milestone_name, milestone_date, client
    Returns dict: metric_name -> {window_label: value}
    """
    today = date.today()

    df["milestone_date"] = pd.to_datetime(df["milestone_date"]).dt.date
    df = df[df["client"].str.lower().isin([c.lower() for c in client_filter])].copy()

    windows = {
        f"{today.strftime('%Y-%m-%d')}":       today,
        f"{(today - timedelta(1)).strftime('%Y-%m-%d')}": today - timedelta(1),
        f"L3D ({(today-timedelta(3)).strftime('%m-%d')})": today - timedelta(3),
        f"L7D ({(today-timedelta(7)).strftime('%m-%d')})": today - timedelta(7),
    }

    # ── per-lead flags (one row per phone_number × assignee_id × date) ──
    lead = (
        df.groupby(["phone_number", "assignee_id", "milestone_date"])
        .apply(lambda g: pd.Series({
            "has_app_dl":           int((g["milestone_name"] == "mitra_app_download").any()),
            "has_training":         int((g["milestone_name"] == "training_completed").any()),
            "has_fod":              int((g["milestone_name"] == "first_date_of_work").any()),
        }))
        .reset_index()
    )

    # ── VL first dates (for New VL logic) ──
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
        # slice
        is_today     = label.startswith(str(today))
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

        # New VL (Leads) — VLs whose first-ever referral date falls in window
        if is_today:
            vl_mask = vl["first_referral_date"] == today
        elif is_yesterday:
            vl_mask = vl["first_referral_date"] == (today - timedelta(1))
        else:
            vl_mask = vl["first_referral_date"] >= cutoff
        results["New VL Count (Leads)"][label] = vl[vl_mask]["assignee_id"].nunique()

        # New VL (PLs) — VLs whose first-ever FOD falls in window
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
def render_table(results: dict, window_labels: list[str], title: str):
    today     = date.today()
    yesterday = today - timedelta(1)

    # header date labels
    date_headers = [
        ("", ""),                             # metric col
        (str(today),    ""),                  # today
        (str(yesterday),""),                  # yesterday
        (str(today - timedelta(3)), "L3D"),   # L3D anchor date
        (str(today - timedelta(7)), "L7D"),   # L7D anchor date
    ]

    header_date_row = "<tr class='date-row'>"
    header_date_row += "<th rowspan='2' class='metric-label'>Metrics (MOE)</th>"
    header_date_row += f"<th>{today}</th>"
    header_date_row += f"<th>{yesterday}</th>"
    header_date_row += f"<th class='window-header'>{today - timedelta(3)}</th>"
    header_date_row += f"<th class='window-header'>{today - timedelta(7)}</th>"
    header_date_row += "</tr>"

    header_label_row = "<tr class='label-row'>"
    header_label_row += f"<th>{today.strftime('%Y-%m-%d')}</th>"
    header_label_row += f"<th>{yesterday.strftime('%Y-%m-%d')}</th>"
    header_label_row += "<th class='window-header'>L3D</th>"
    header_label_row += "<th class='window-header'>L7D</th>"
    header_label_row += "</tr>"

    body = ""
    for metric, vals in results.items():
        body += "<tr>"
        body += f"<td class='metric-name'>{metric}</td>"
        for label in window_labels:
            v = vals.get(label, 0)
            body += f"<td>{v:,}</td>"
        body += "</tr>"

    html = f"""
    <div style='margin-bottom:24px'>
      <div class='dash-title'>{title}</div>
    </div>
    <table class='moe-table'>
      <thead>
        {header_date_row}
        {header_label_row}
      </thead>
      <tbody>
        {body}
      </tbody>
    </table>
    """
    st.markdown(html, unsafe_allow_html=True)


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    today = date.today()

    st.markdown(f"""
    <div class='dash-title'>📊 Pronto & Snabbit — MOE Dashboard</div>
    <div class='dash-sub'>
      <span class='badge badge-pronto'>Pronto</span>
      <span class='badge badge-snabbit'>Snabbit</span>
      &nbsp;·&nbsp; As of <b>{today}</b>
    </div>
    """, unsafe_allow_html=True)

    # ── sidebar controls ──
    with st.sidebar:
        st.header("Settings")
        api_key  = st.text_input("Redash API Key",  value=REDASH_API_KEY,  type="password")
        query_id = st.number_input("Query ID", value=QUERY_ID, step=1)
        clients  = st.multiselect(
            "Clients", ["pronto", "snabbit"], default=["pronto", "snabbit"]
        )
        refresh  = st.button("🔄 Refresh Data")
        if refresh:
            st.cache_data.clear()

    # ── fetch ──
    try:
        df_raw = fetch_redash(int(query_id), api_key)
    except Exception as e:
        st.error(f"Failed to fetch data from Redash: {e}")
        st.info("Make sure your API key and Query ID are correct in the sidebar.")
        return

    if df_raw.empty:
        st.warning("No data returned from Redash query.")
        return

    # ── split by client or show combined ──
    view = st.radio("View", ["Combined", "Pronto only", "Snabbit only"], horizontal=True)

    if view == "Combined":
        results, labels = compute_metrics(df_raw, clients)
        render_table(results, labels, "Pronto + Snabbit — Combined")

    elif view == "Pronto only":
        results, labels = compute_metrics(df_raw, ["pronto"])
        render_table(results, labels, "Pronto")

    else:
        results, labels = compute_metrics(df_raw, ["snabbit"])
        render_table(results, labels, "Snabbit")

    st.markdown(f"<div style='font-size:11px;color:#999;margin-top:12px'>Data refreshes every 5 min · Last load: {pd.Timestamp.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
