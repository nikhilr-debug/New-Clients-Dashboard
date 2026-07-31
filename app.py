import json
import re
import pandas as pd
import requests
import streamlit as st

# ==========================================
# CONFIGURATION & CONSTANTS
# ==========================================
API_KEY = "4aFm2iOoyx8I91svQccdeZr0jmaiUsMFSRinZcmu"

QUERY_A_URL = "https://redash.vahan.co/api/queries/18054/results"  # candidates + VL names
QUERY_B_URL = "https://redash.vahan.co/api/queries/18055/results"  # UJF metadata

st.set_page_config(
    page_title="Vahan Onboarding Analytics Dashboard",
    page_icon="📊",
    layout="wide",
)


# ==========================================
# JSON KEY NORMALIZATION & MERGING LOGIC
# ==========================================
def normalize_key(key: str) -> str:
    """Standardizes JSON keys by handling casing, camelCase, punctuation, and separators."""
    if not isinstance(key, str):
        key = str(key)
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", key)
    s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
    clean_key = re.sub(r"[^a-zA-Z0-9]+", "_", s2)
    clean_key = clean_key.lower().strip("_")
    return re.sub(r"_+", "_", clean_key)


def parse_json_safely(val):
    """Safely parses JSON strings into dictionaries."""
    if pd.isna(val) or val is None or val == "":
        return {}
    if isinstance(val, dict):
        return val
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return {}


def extract_and_merge_json(row):
    """Parses metaData and preOnboardingMetaData, normalizes keys,
    and merges entries so each normalized key exists only once.
    preOnboardingMetaData is applied first; metaData overwrites/supplements it.
    """
    meta_dict = parse_json_safely(row.get("metaData"))
    pre_meta_dict = parse_json_safely(row.get("preOnboardingMetaData"))

    merged = {}

    for k, v in pre_meta_dict.items():
        norm_k = normalize_key(k)
        if v is not None and str(v).strip() != "":
            merged[norm_k] = v

    for k, v in meta_dict.items():
        norm_k = normalize_key(k)
        if v is not None and str(v).strip() != "":
            merged[norm_k] = v

    return merged


# ==========================================
# DATA FETCHING
# ==========================================
def fetch_redash(url: str, label: str) -> pd.DataFrame:
    """Fetches rows from a Redash query results endpoint."""
    try:
        response = requests.get(url, params={"api_key": API_KEY}, timeout=60)
        response.raise_for_status()
        rows = (
            response.json()
            .get("query_result", {})
            .get("data", {})
            .get("rows", [])
        )
        if not rows:
            st.warning(f"No rows returned from {label}.")
            return pd.DataFrame()
        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"Error fetching {label}: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=600)
def fetch_and_process_data() -> pd.DataFrame:
    """
    Fetches Pull A (candidates + VL names) and Pull B (UJF metadata) separately,
    merges them on ujf_id in pandas, then expands normalized JSON columns.
    """
    df_a = fetch_redash(QUERY_A_URL, "Pull A (candidates + VL names)")
    df_b = fetch_redash(QUERY_B_URL, "Pull B (UJF metadata)")

    if df_a.empty or df_b.empty:
        return pd.DataFrame()

    # Normalize join key column names defensively
    # Pull A is expected to have: ujf_id, referral_date, vl_phone_number, vl_name
    # Pull B is expected to have: ujf_id, preOnboardingMetaData, metaData
    if "ujf_id" not in df_a.columns or "ujf_id" not in df_b.columns:
        st.error(
            "Join key `ujf_id` missing in one of the query results. "
            f"Pull A columns: {list(df_a.columns)} | Pull B columns: {list(df_b.columns)}"
        )
        return pd.DataFrame()

    # Cast ujf_id to string on both sides to avoid UUID vs String type mismatch
    df_a["ujf_id"] = df_a["ujf_id"].astype(str).str.strip()
    df_b["ujf_id"] = df_b["ujf_id"].astype(str).str.strip()

    # Inner join — only rows that exist in both queries
    df = df_a.merge(df_b, on="ujf_id", how="inner")

    if df.empty:
        st.warning("Merge returned 0 rows — ujf_id values may not be overlapping between the two queries.")
        return pd.DataFrame()

    # Parse datetime columns
    for col in ["referral_date", "createdAt"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Expand and normalize metaData + preOnboardingMetaData
    merged_json_series = df.apply(extract_and_merge_json, axis=1)
    json_expanded_df = pd.json_normalize(merged_json_series)

    final_df = pd.concat(
        [df.reset_index(drop=True), json_expanded_df.reset_index(drop=True)],
        axis=1,
    )

    # Deduplicate columns — keep original base columns if keys overlap
    final_df = final_df.loc[:, ~final_df.columns.duplicated(keep="first")]

    return final_df


# ==========================================
# STREAMLIT DASHBOARD UI
# ==========================================
st.title("🚀 Vahan Onboarding Analytics Dashboard")
st.caption("Live dashboard powered by Redash — dual-query fetch merged on ujf_id")

with st.spinner("Fetching Pull A & Pull B from Redash and merging..."):
    df = fetch_and_process_data()

if df.empty:
    st.warning("No data to display. Check Redash query results or ujf_id overlap.")
    st.stop()

# --- SIDEBAR FILTERS ---
st.sidebar.header("🔍 Filter Options")

# Client Filter
clients = (
    ["All"] + sorted(df["Report_Client"].dropna().astype(str).unique().tolist())
    if "Report_Client" in df.columns
    else ["All"]
)
selected_client = st.sidebar.selectbox("Select Report Client", clients)

# VL Name Filter
vl_names = (
    ["All"] + sorted(df["vl_name"].dropna().astype(str).unique().tolist())
    if "vl_name" in df.columns
    else ["All"]
)
selected_vl = st.sidebar.selectbox("Select VL Name", vl_names)

# Date Filter — use referral_datei as primary, fall back to createdAt
date_col = "referral_date" if "referral_date" in df.columns else "createdAt"
if date_col in df.columns and not df[date_col].isna().all():
    min_date = df[date_col].min().date()
    max_date = df[date_col].max().date()
    date_range = st.sidebar.date_input(
        f"Date Range ({date_col})", [min_date, max_date]
    )
else:
    date_range = []

# Apply Filters
filtered_df = df.copy()

if selected_client != "All" and "Report_Client" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["Report_Client"] == selected_client]

if selected_vl != "All" and "vl_name" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["vl_name"] == selected_vl]

if len(date_range) == 2 and date_col in filtered_df.columns:
    start_date, end_date = date_range
    filtered_df = filtered_df[
        (filtered_df[date_col].dt.date >= start_date)
        & (filtered_df[date_col].dt.date <= end_date)
    ]

# --- KPI METRICS ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Funnel Records", f"{len(filtered_df):,}")

with col2:
    unique_phones = (
        int(filtered_df["candidate_phone_no"].nunique())
        if "candidate_phone_no" in filtered_df.columns
        else 0
    )
    st.metric("Unique Candidates", f"{unique_phones:,}")

with col3:
    unique_clients = (
        int(filtered_df["Report_Client"].nunique())
        if "Report_Client" in filtered_df.columns
        else 0
    )
    st.metric("Active Clients", f"{unique_clients:,}")

with col4:
    unique_vls = (
        int(filtered_df["vl_name"].nunique())
        if "vl_name" in filtered_df.columns
        else 0
    )
    st.metric("Active VLs", f"{unique_vls:,}")

st.markdown("---")

# --- CHARTS ---
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("Client Distribution")
    if "Report_Client" in filtered_df.columns:
        client_counts = filtered_df["Report_Client"].value_counts()
        st.bar_chart(client_counts)

with chart_col2:
    st.subheader("Top 10 VL Performance")
    if "vl_name" in filtered_df.columns:
        vl_counts = filtered_df["vl_name"].value_counts().head(10)
        st.bar_chart(vl_counts)

# --- DATA TABLE ---
st.subheader("📋 Parsed & Normalized Data Table")
st.write(
    f"Displaying **{len(filtered_df):,}** records with normalized JSON keys expanded into columns."
)

show_raw_json = st.checkbox(
    "Show raw metaData / preOnboardingMetaData columns", value=False
)
display_df = filtered_df.copy()

if not show_raw_json:
    display_df = display_df.drop(
        columns=["metaData", "preOnboardingMetaData"], errors="ignore"
    )

st.dataframe(display_df, use_container_width=True)

# --- DOWNLOAD ---
csv_data = display_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="📥 Download Expanded CSV",
    data=csv_data,
    file_name="vahan_parsed_funnel_data.csv",
    mime="text/csv",
)
