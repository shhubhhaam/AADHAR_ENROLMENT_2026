import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import glob

# -------------------------------------------------------
# Indian number formatting function
# -------------------------------------------------------
def format_indian(num):
    """Format number in Indian numbering system (1,23,45,678)"""
    num = int(num)
    if num < 1000:
        return str(num)
    
    s = str(num)
    result = s[-3:]
    num = int(s[:-3])
    
    while num > 0:
        result = str(num % 100).zfill(2) + ',' + result
        num //= 100
    
    return result.lstrip('0').lstrip(',')

# -------------------------------------------------------
# Age group label mapping function
# -------------------------------------------------------
def format_age_group(col_name):
    """Convert column names to readable age group labels"""
    mapping = {
        'age_0_5': 'Age 0-5',
        'age_5_17': 'Age 5-17',
        'age_18_greater': 'Age 18+',
        'bio_age_5_17': 'Age 5-17',
        'bio_age_17_': 'Age 17+',
        'demo_age_5_17': 'Age 5-17',
        'demo_age_17_': 'Age 17+'
    }
    return mapping.get(col_name, col_name)

# -------------------------------------------------------
# Page config
# -------------------------------------------------------
st.set_page_config(
    page_title="Aadhaar Enrolment Analytics Dashboard",
    layout="wide"
)

st.title("📊 Aadhaar Enrolment Analytics & Insights Dashboard")
st.markdown("Please select analysis level and filters from the sidebar.")

# -------------------------------------------------------
# Load data safely
# -------------------------------------------------------
@st.cache_data
def load_data():
    try:
        # Get the directory where this script is located
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        DATASETS_DIR = os.path.join(BASE_DIR, "Datasets")
        
        # Find all enrolment CSV files
        files = glob.glob(os.path.join(DATASETS_DIR, "DF_ENROLMENT_*.csv"))
        
        if not files:
            st.error(f"No enrolment data files found in {DATASETS_DIR}")
            st.stop()
        
        # Load and concatenate all files
        df_list = []
        for f in files:
            try:
                df_temp = pd.read_csv(f)
                df_list.append(df_temp)
            except Exception as e:
                st.warning(f"Could not load {os.path.basename(f)}: {str(e)}")
        
        if not df_list:
            st.error("No data could be loaded from CSV files")
            st.stop()
        
        df = pd.concat(df_list, ignore_index=True)
        df["date"] = pd.to_datetime(df["date"], errors='coerce')
        df = df.dropna(subset=['date'])  # Remove rows with invalid dates
        df["month"] = df["date"].dt.to_period("M").astype(str)
        
        return df
    
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.stop()

# Load data with error handling
with st.spinner("Loading data..."):
    df = load_data()

if df.empty:
    st.error("No data available to display")
    st.stop()

# -------------------------------------------------------
# Sidebar controls
# -------------------------------------------------------
st.sidebar.header("🔍 Analysis Filters")

level = st.sidebar.selectbox(
    "Select Analysis Level",
    ["National", "State", "District"]
)

state = district = None

if level in ["State", "District"]:
    states = sorted(df["state"].dropna().unique())
    if len(states) > 0:
        state = st.sidebar.selectbox("Select State", states)
    else:
        st.warning("No state data available")
        st.stop()

if level == "District":
    districts = sorted(df[df["state"] == state]["district"].dropna().unique())
    if len(districts) > 0:
        district = st.sidebar.selectbox("Select District", districts)
    else:
        st.warning(f"No district data available for {state}")
        st.stop()

# -------------------------------------------------------
# Filter data
# -------------------------------------------------------
df_region = df.copy()
title_suffix = "India (National Level)"

if level == "State":
    df_region = df_region[df_region["state"] == state]
    title_suffix = f"{state} (State Level)"

elif level == "District":
    df_region = df_region[
        (df_region["state"] == state) &
        (df_region["district"] == district)
    ]
    title_suffix = f"{district}, {state} (District Level)"

if df_region.empty:
    st.warning("No data available for selected filters.")
    st.stop()

# =======================================================
# 1️⃣ Registrations in each month
# =======================================================
st.subheader(f"📅 Monthly Registrations — {title_suffix}")

# Calculate total properly
age_cols = ['age_0_5', 'age_5_17', 'age_18_greater']
available_cols = [col for col in age_cols if col in df_region.columns]

if not available_cols:
    st.error("Required age columns not found in data")
    st.stop()

total_enrol_sum = int(df_region[available_cols].sum().sum() / 2)
st.markdown(f"**Total Enrolment Records Aggregated: {format_indian(total_enrol_sum)}**")

monthly_total = (
    df_region.groupby("month")[available_cols]
    .sum()
    .sum(axis=1)
    .reset_index(name="registrations")
)

fig1, ax1 = plt.subplots(figsize=(12, 7))
sns.barplot(data=monthly_total, x="month", y="registrations", ax=ax1, palette="viridis")

ax1.set_xlabel("Month", fontsize=12)
ax1.set_ylabel("Total Registrations", fontsize=12)
ax1.set_title("Total Registrations per Month", fontsize=14, fontweight='bold')
ax1.bar_label(ax1.containers[0], padding=3, fmt=lambda x: format_indian(int(x)))
ax1.grid(axis='y', alpha=0.3)

plt.xticks(rotation=45)
plt.tight_layout()
st.pyplot(fig1)
plt.close()

# =======================================================
# 2️⃣ Registrations by month across age groups
# =======================================================
st.subheader("👥 Monthly Registrations by Age Group")

monthly_age = (
    df_region.groupby("month")[available_cols]
    .sum()
    .reset_index()
    .melt(id_vars="month", var_name="age_group", value_name="registrations")
)
monthly_age["age_group"] = monthly_age["age_group"].apply(format_age_group)

fig2, ax2 = plt.subplots(figsize=(16, 6))
sns.barplot(
    data=monthly_age,
    y="month",
    x="registrations",
    hue="age_group",
    ax=ax2,
    palette="Set2"
)

ax2.set_ylabel("Month", fontsize=12)
ax2.set_xlabel("Registrations", fontsize=12)
ax2.set_title("Monthly Registrations Across Age Groups", fontsize=14, fontweight='bold')
ax2.legend(title="Age Group")
ax2.grid(axis='x', alpha=0.3)

for container in ax2.containers:
    ax2.bar_label(container, padding=2, fmt=lambda x: format_indian(int(x)) if x > 0 else '')

plt.tight_layout()
st.pyplot(fig2)
plt.close()

# =======================================================
# 3️⃣ Sub-territory registrations
# =======================================================
st.subheader("🗺️ Sub-Territory Registrations")

if level == "District":
    st.info("Pincode-level data displayed as a table due to high cardinality.")

    if 'pincode' in df_region.columns:
        pincode_table = (
            df_region.groupby("pincode")[available_cols]
            .sum()
            .sum(axis=1)
            .reset_index(name="total_registrations")
            .sort_values("total_registrations", ascending=False)
        )
        
        pincode_table['total_registrations'] = pincode_table['total_registrations'].apply(lambda x: format_indian(int(x)))
        st.dataframe(pincode_table, height=400, use_container_width=True)
    else:
        st.warning("Pincode data not available in dataset")

else:
    sub_col = "state" if level == "National" else "district"

    sub_total = (
        df_region.groupby(sub_col)[available_cols]
        .sum()
        .sum(axis=1)
        .reset_index(name="registrations")
        .sort_values("registrations", ascending=False)
    )

    fig3, ax3 = plt.subplots(figsize=(14, max(6, df_region[sub_col].nunique() * 0.5 + 2)))
    sns.barplot(data=sub_total, y=sub_col, x="registrations", ax=ax3, palette="coolwarm")

    ax3.set_ylabel(sub_col.title(), fontsize=12)
    ax3.set_xlabel("Registrations", fontsize=12)
    ax3.set_title(f"Registrations by {sub_col.title()}", fontsize=14, fontweight='bold')
    ax3.bar_label(ax3.containers[0], padding=3, fmt=lambda x: format_indian(int(x)))
    ax3.grid(axis='x', alpha=0.3)

    plt.tight_layout()
    st.pyplot(fig3)
    plt.close()

# =======================================================
# 4️⃣ Sub-territory across age groups
# =======================================================
if level != "District":
    st.subheader("👶🧑 Sub-Territory Registrations by Age Group")

    sub_age = (
        df_region.groupby(sub_col)[available_cols]
        .sum()
        .reset_index()
        .melt(id_vars=sub_col, var_name="age_group", value_name="registrations")
    )
    sub_age["age_group"] = sub_age["age_group"].apply(format_age_group)

    fig4, ax4 = plt.subplots(figsize=(16, max(6, df_region[sub_col].nunique() * 0.5 + 2)))

    sns.barplot(
        data=sub_age,
        y=sub_col,
        x="registrations",
        hue="age_group",
        ax=ax4,
        palette="Set1"
    )

    ax4.set_ylabel(sub_col.title(), fontsize=12)
    ax4.set_xlabel("Registrations", fontsize=12)
    ax4.set_title("Registrations by Sub-Territory and Age Group", fontsize=14, fontweight='bold')
    ax4.legend(title="Age Group")
    ax4.grid(axis='x', alpha=0.3)

    for container in ax4.containers:
        ax4.bar_label(
            container,
            padding=3,
            fmt=lambda x: format_indian(int(x)) if x > 0 else ''
        )

    plt.tight_layout()
    st.pyplot(fig4)
    plt.close()

# =======================================================
# 🔹 A. Cumulative registrations over time
# =======================================================
st.subheader("📈 Cumulative Registrations Over Time")

daily_total = (
    df_region.groupby("date")[available_cols]
    .sum()
    .sum(axis=1)
    .cumsum()
    .reset_index(name="cumulative_registrations")
)

fig5, ax5 = plt.subplots(figsize=(12, 5))
ax5.plot(daily_total["date"], daily_total["cumulative_registrations"], linewidth=2, color='#2E86AB')
ax5.fill_between(daily_total["date"], daily_total["cumulative_registrations"], alpha=0.3, color='#2E86AB')
ax5.set_xlabel("Date", fontsize=12)
ax5.set_ylabel("Cumulative Registrations", fontsize=12)
ax5.set_title("Cumulative Registration Growth", fontsize=14, fontweight='bold')
ax5.grid(axis='y', alpha=0.3)
plt.tight_layout()
st.pyplot(fig5)
plt.close()

# =======================================================
# 🔹 B. Age-group percentage share over time
# =======================================================
st.subheader("📊 Age Group Percentage Share Over Time")

monthly_pct = (
    df_region.groupby("month")[available_cols]
    .sum()
)

monthly_pct = monthly_pct.div(monthly_pct.sum(axis=1), axis=0) * 100
monthly_pct = monthly_pct.reset_index().melt(
    id_vars="month",
    var_name="age_group",
    value_name="percentage"
)
monthly_pct["age_group"] = monthly_pct["age_group"].apply(format_age_group)

fig6, ax6 = plt.subplots(figsize=(14, 6))
sns.lineplot(
    data=monthly_pct,
    x="month",
    y="percentage",
    hue="age_group",
    marker="o",
    ax=ax6,
    linewidth=2.5
)

ax6.set_xlabel("Month", fontsize=12)
ax6.set_ylabel("Percentage Share (%)", fontsize=12)
ax6.set_title("Age Group Contribution Over Time", fontsize=14, fontweight='bold')
plt.xticks(rotation=45)
ax6.legend(title="Age Group", loc='best')
ax6.grid(axis='y', alpha=0.3)
plt.tight_layout()
st.pyplot(fig6)
plt.close()

# Footer
st.markdown("---")
st.markdown("**Dashboard developed for Aadhaar Enrolment Analysis** | Data-driven insights for policy decisions")
