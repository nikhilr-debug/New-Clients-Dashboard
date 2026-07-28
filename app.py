import json
import re
import pandas as pd
import requests
import streamlit as st

# ==========================================
# CONFIGURATION & CONSTANTS
# ==========================================
REDASH_URL = "https://redash.vahan.co/api/queries/18000/results"
API_KEY = "4aFm2iOoyx8I91svQccdeZr0jmaiUsMFSRinZcmu"

st.set_page_config(
    page_title="Vahan Onboarding Analytics Dashboard",
    page_icon="📊",
    layout="wide",
)


# ==========================================
# JSON KEY NORMALIZATION & MERGING LOGIC
# ==========================================
def normalize_key(key: str) -> str:
    """Standardizes JSON keys by handling casing, camelCase, punctuation, and separators.

    Examples:
    'candidatePhoneNo'      -> 'candidate_phone_no'
    'Candidate_Phone-No'    -> 'candidate_phone_no'
    'CANDIDATE PHONE NO'    -> 'candidate_phone_no'
    """
    if not isinstance(key, str):
        key = str(key)

    # Insert underscore between lower-to-upper transition (camelCase / PascalCase)
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", key)
    s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)

    # Replace non-alphanumeric characters with underscores
    clean_key = re.sub(r"[^a-zA-Z0-9]+", "_", s2)

    # Lowercase, trim extra underscores, and collapse multiple underscores
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
    """
    meta_dict = parse_json_safely(row.get("metaData"))
    pre_meta_dict = parse_json_safely(row.get("preOnboardingMetaData"))

    merged = {}

    # 1. Process preOnboardingMetaData first
    for k, v in pre_meta_dict.items():
        norm_k = normalize_key(k)
        if v is not None and str(v).strip() != "":
            merged[norm_k] = v

    # 2. Process metaData (overwrites or supplements preOnboardingMetaData)
    for k, v in meta_dict.items():
        norm_k = normalize_key(k)
        if v is not None and str(v).strip() != "":
            # Prefer metaData if both exist and non-empty
            merged[norm_k] = v

    return merged


# ==========================================
# DATA FETCHING & PROCESSING
# ==========================================
@st.cache_data(ttl=600)  # Caches data for 10 minutes
def fetch_and_process_data():
    """Fetches data from Redash and expands/normalizes JSON columns."""
    try:
        response = requests.get(
            REDASH_URL, params={"api_key": API_KEY}, timeout=30
        )
        response.raise_for_status()
        res_json = response.json()

        # Redash results structure parsing
        rows = res_json.get("query_result", {}).get("data", {}).get("rows", [])
        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)

        # Ensure createdAt is datetime
        if "createdAt" in df.columns:
            df["createdAt"] = pd.to_datetime(df["createdAt"])

        # Extract and merge normalized JSON keys for every row
        merged_json_series = df.apply(extract_and_merge_json, axis=1)

        # Expand merged JSON dictionary into a separate DataFrame
        json_expanded_df = pd.json_normalize(merged_json_series)

        # Concatenate normalized JSON columns back to the primary DataFrame
        final_df = pd.concat(
            [df.reset_index(drop=True), json_expanded_df.reset_index(drop=True)],
            axis=1,
        )

        return final_df

    except Exception as e:
        st.error(f"Error fetching data from Redash: {e}")
        return pd.DataFrame()


# ==========================================
# STREAMLIT DASHBOARD UI
# ==========================================
st.title("🚀 Vahan Onboarding Analytics Dashboard")
st.caption("Live dashboard powered by Redash Query Results API")

with st.spinner("Fetching and expanding JSON dataset..."):
    df = fetch_and_process_data()

if df.empty:
    st.warning("No data retrieved from the Redash endpoint.")
    st.stop()

# --- SIDEBAR FILTERS ---
st.sidebar.header("🔍 Filter Options")

# Client Filter
clients = (
    ["All"] + sorted(df["Report_Client"].dropna().unique().tolist())
    if "Report_Client" in df.columns
    else ["All"]
)
selected_client = st.sidebar.selectbox("Select Report Client", clients)

# VL Name Filter
vl_names = (
    ["All"] + sorted(df["vl_name"].dropna().unique().tolist())
    if "vl_name" in df.columns
    else ["All"]
)
selected_vl = st.sidebar.selectbox("Select VL Name", vl_names)

# Date Filter
if "createdAt" in df.columns and not df["createdAt"].isna().all():
    min_date = df["createdAt"].min().date()
    max_date = df["createdAt"].max().date()
    date_range = st.sidebar.date_input(
        "Created At Date Range", [min_date, max_date]
    )
else:
    date_range = []

# Apply Filters
filtered_df = df.copy()

if selected_client != "All":
    filtered_df = filtered_df[filtered_df["Report_Client"] == selected_client]

if selected_vl != "All":
    filtered_df = filtered_df[filtered_df["vl_name"] == selected_vl]

if len(date_range) == 2:
    start_date, end_date = date_range
    filtered_df = filtered_df[
        (filtered_df["createdAt"].dt.date >= start_date)
        & (filtered_df["createdAt"].dt.date <= end_date)
    ]

# --- KPI METRICS ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Funnel Records", f"{len(filtered_df):,}")

with col2:
    unique_phones = (
        filtered_df["candidate_phone_no"].nunique()
        if "candidate_phone_no" in filtered_df.columns
        else 0
    )
    st.metric("Unique Candidates", f"{unique_phones:,}")

with col3:
    unique_clients = (
        filtered_df["Report_Client"].nunique()
        if "Report_Client" in filtered_df.columns
        else 0
    )
    st.metric("Active Clients", unique_clients)

with col4:
    unique_vls = (
        filtered_df["vl_name"].nunique()
        if "vl_name" in filtered_df.columns
        else 0
    )
    st.metric("Active VLs", unique_vls)

st.markdown("---")

# --- CHARTS & VISUALIZATIONS ---
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

# --- EXPANDED DATA TABLE ---
st.subheader("📋 Parsed & Normalized Data Table")
st.write(
    f"Displaying **{len(filtered_df)}** records with normalized JSON keys expanded into columns."
)

# Option to toggle raw JSON columns
show_raw_json = st.checkbox("Show raw metaData / preOnboardingMetaData columns", value=False)
display_df = filtered_df.copy()

if not show_raw_json:
    display_df = display_df.drop(
        columns=["metaData", "preOnboardingMetaData"], errors="ignore"
    )

st.dataframe(display_df, use_container_width=True)

# --- DOWNLOAD BUTTON ---
csv_data = display_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="📥 Download Expanded CSV",
    data=csv_data,
    file_name="vahan_parsed_funnel_data.csv",
    mime="text/csv",
)
