import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.graph_objects as go
import base64

# --- MUST BE FIRST: PAGE CONFIG ---
st.set_page_config(page_title="Despatch KPI Dashboard", layout="wide")

# --- BACKGROUND SETTING FUNCTION ---
def set_background(png_file_path):
    import base64
    with open(png_file_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()

    st.markdown(
        f"""
        <style>
        /* Set background image for main app */
        .stApp {{
            background-image: url("data:image/png;base64,{encoded_string}");
            background-size: contain;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}

        /* Main content area - black text */
        .block-container {{
            background-color: rgba(255, 255, 255, 0.85);
            padding: 2rem;
            border-radius: 10px;
            color: black !important;
        }}

        /* Black text for headings, paragraphs, metrics etc. in main content */
        h1, h2, h3, h4, h5, h6,
        .stMarkdown, .stText, .stMetric,
        div[data-testid="stMetricValue"],
        div[data-testid="stMetricLabel"],
        span, p, label, section,
        .css-10trblm, .css-1v0mbdj {{
            color: black !important;
        }}

        /* Sidebar (menu) text remains white */
        .sidebar-content, .css-1d391kg, .css-1lcbmhc {{
            color: white !important;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# --- SET BACKGROUND LOGO ---
set_background("C:/Users/TAPIWA/Pictures/bakers Inn logo.png")

# --- GOOGLE SHEETS AUTH ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(
    r"C:/Program Files/JetBrains/PyCharm Community Edition 2025.1/tapiwa-460415-0f7e852ffac1.json",
    scope
)
client = gspread.authorize(creds)
spreadsheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1_kxrutaWP9HDHRp5BtYOZloKGSgkeEpm3L16FCctiMI")

# --- LOAD DATA ---
orders_ws = spreadsheet.worksheet("ORDERED")
loadings_ws = spreadsheet.worksheet("LOADED")
orders_df = pd.DataFrame(orders_ws.get_all_records())
loadings_df = pd.DataFrame(loadings_ws.get_all_records())

# --- CLEAN COLUMNS ---
orders_df.columns = [col.strip().upper().replace(" ", "_") for col in orders_df.columns]
loadings_df.columns = [col.strip().upper().replace(" ", "_") for col in loadings_df.columns]

# --- DATE FORMAT ---
orders_df["DATE"] = pd.to_datetime(orders_df["DATE"], errors="coerce")
loadings_df["DATE"] = pd.to_datetime(loadings_df["DATE"], errors="coerce")

# --- CONVERT MUNCHIE_COOKIES TO NUMERIC ---
if "MUNCHIE_COOKIES" in orders_df.columns:
    orders_df["MUNCHIE_COOKIES"] = pd.to_numeric(orders_df["MUNCHIE_COOKIES"], errors="coerce").fillna(0)
if "MUNCHIE_COOKIES" in loadings_df.columns:
    loadings_df["MUNCHIE_COOKIES"] = pd.to_numeric(loadings_df["MUNCHIE_COOKIES"], errors="coerce").fillna(0)

# --- SIDEBAR FILTERS ---
st.sidebar.title("Filters")
with st.sidebar.expander("🔎 Advanced Filters", expanded=False):
    min_date = min(orders_df["DATE"].min(), loadings_df["DATE"].min())
    max_date = max(orders_df["DATE"].max(), loadings_df["DATE"].max())
    date_range = st.date_input("Select Date Range", [min_date, max_date])

    all_routes = sorted(loadings_df["ROUTE"].unique())
    select_all = st.checkbox("✅ Select All Routes", value=True)
    if select_all:
        routes = st.multiselect("Select Routes", options=all_routes, default=all_routes)
    else:
        routes = st.multiselect("Select Routes", options=all_routes)

# --- APPLY FILTERS ---
start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
orders_df = orders_df[(orders_df["DATE"] >= start_date) & (orders_df["DATE"] <= end_date) & (orders_df["ROUTE"].isin(routes))]
loadings_df = loadings_df[(loadings_df["DATE"] >= start_date) & (loadings_df["DATE"] <= end_date) & (loadings_df["ROUTE"].isin(routes))]

# --- KPI METRICS ---
loaf_columns = ["BI_WHITE", "BI_BROWN", "BI_WHOLE_WHEAT", "MR_CHINGWA", "MRS_CHINGWA", "DR_CHINGWA"]
for col in loaf_columns:
    loadings_df[col] = pd.to_numeric(loadings_df[col], errors="coerce").fillna(0)

total_loaded = loadings_df[loaf_columns].sum().sum()
total_orders = orders_df["TOTAL_ORDERS"].sum()
loading_compliance = (loadings_df["LOADING_COMPLIANCE_STATUS"] == "Green").mean() * 100
departure_compliance = (loadings_df["DEPARTURE_COMPLIANCE_STATUS"] == "On-time").mean() * 100

# --- SIDEBAR MENU ---
selected_kpi = st.sidebar.selectbox("📊 Select KPI to Explore", [
    "Summary View",
    "Loaves Loaded",
    "Loading Compliance",
    "Departure Compliance",
    "Munchie Cookies Analysis"
])

# --- DASHBOARD OUTPUT ---
if selected_kpi == "Summary View":
    st.title("📦 Bakers Inn - Despatch KPI Dashboard")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📈 Total Orders", f"{int(total_orders):,}")
    col2.metric("🚚 Loaves Loaded", f"{int(total_loaded):,}")
    col3.metric("✅ Loading Compliance", f"{loading_compliance:.1f}%")
    col4.metric("🕒 Departure Compliance", f"{departure_compliance:.1f}%")

    munchie_ordered = orders_df["MUNCHIE_COOKIES"].sum()
    munchie_loaded = loadings_df["MUNCHIE_COOKIES"].sum()
    col5, col6 = st.columns(2)
    col5.metric("🥠 Munchie Cookies Ordered", f"{int(munchie_ordered):,}")
    col6.metric("🥠 Munchie Cookies Loaded", f"{int(munchie_loaded):,}")

    st.markdown("---")
    st.subheader("📆 Daily Orders Trend")
    if "DATE" in orders_df.columns:
        daily_orders = orders_df.groupby("DATE")["TOTAL_ORDERS"].sum().reset_index()
        st.line_chart(daily_orders.rename(columns={"DATE": "index"}).set_index("index"))

elif selected_kpi == "Loaves Loaded":
    st.subheader("🚚 Loaves Loaded by Route")
    route_totals = loadings_df.groupby("ROUTE")[loaf_columns].sum()
    route_totals["TOTAL_LOADED"] = route_totals.sum(axis=1)
    st.bar_chart(route_totals["TOTAL_LOADED"].sort_values(ascending=False))

elif selected_kpi == "Loading Compliance":
    st.subheader("✅ Loading Compliance Breakdown")
    compliance_counts = loadings_df["LOADING_COMPLIANCE_STATUS"].value_counts()
    colors = ["green" if status == "Green" else "red" for status in compliance_counts.index]
    fig = go.Figure(data=[
        go.Bar(x=compliance_counts.index, y=compliance_counts.values, marker_color=colors)
    ])
    fig.update_layout(title="Loading Compliance Statuses", xaxis_title="Status", yaxis_title="Count")
    st.plotly_chart(fig, use_container_width=True)

elif selected_kpi == "Departure Compliance":
    st.subheader("🕒 Departure Compliance Breakdown")
    dep_counts = loadings_df["DEPARTURE_COMPLIANCE_STATUS"].value_counts()
    color_map = {
        "On-time": "green", "Reasonable": "gold", "Early": "blue", "Late": "red"
    }
    dep_colors = [color_map.get(status, "gray") for status in dep_counts.index]
    fig = go.Figure(data=[
        go.Bar(x=dep_counts.index, y=dep_counts.values, marker_color=dep_colors)
    ])
    fig.update_layout(title="Departure Compliance Statuses", xaxis_title="Status", yaxis_title="Count")
    st.plotly_chart(fig, use_container_width=True)

elif selected_kpi == "Munchie Cookies Analysis":
    st.subheader("🥠 Munchie Cookies Ordered vs Loaded")
    munchie_ordered = orders_df["MUNCHIE_COOKIES"].sum()
    munchie_loaded = loadings_df["MUNCHIE_COOKIES"].sum()
    col1, col2 = st.columns(2)
    col1.metric("🥠 Ordered", f"{int(munchie_ordered):,}")
    col2.metric("🥠 Loaded", f"{int(munchie_loaded):,}")

    chart_type = st.selectbox("Choose chart type", ["Bar Chart", "Pie Chart", "Donut Chart"], key="munchie_chart")

    if chart_type == "Bar Chart":
        fig = go.Figure(data=[
            go.Bar(name="Ordered", x=["Munchie Cookies"], y=[munchie_ordered], marker_color="blue"),
            go.Bar(name="Loaded", x=["Munchie Cookies"], y=[munchie_loaded], marker_color="green")
        ])
        fig.update_layout(barmode='group', title="Munchie Cookies Ordered vs Loaded")
        st.plotly_chart(fig, use_container_width=True)
    else:
        labels = ["Ordered", "Loaded"]
        values = [munchie_ordered, munchie_loaded]
        colors = ["blue", "green"]
        fig = go.Figure(data=[go.Pie(
            labels=labels, values=values, marker_colors=colors,
            hole=0.4 if chart_type == "Donut Chart" else 0
        )])
        fig.update_layout(title="Munchie Cookies Ordered vs Loaded")
        st.plotly_chart(fig, use_container_width=True)

st.markdown("✅ Powered by Google Sheets + Streamlit")
