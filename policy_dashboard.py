import streamlit as st
import pandas as pd
import altair as alt

# --- Configuration ---
st.set_page_config(
    page_title="Policy Dimension Explorer",
    page_icon="🛡️",
    layout="wide"
)

# --- Helper Functions ---
def format_mechanism_label(mech_key):
    """Converts 'age_verification' to 'Age Verification'"""
    return mech_key.replace('_', ' ').title()

# --- Data Loading ---
@st.cache_data
def load_data():
    # Load the CSV file
    try:
        df = pd.read_csv('data/bill_classifications_full.csv')
        return df
    except FileNotFoundError:
        st.error("bill_classifications_full.csv not found. Please ensure the data file is in the 'data' directory.")
        return pd.DataFrame()

df = load_data()

# --- Sidebar Filters ---
st.sidebar.header("Filter Legislation")

if not df.empty:
    # 1. Filter by State (using 'state' column)
    all_states = sorted(df['state'].dropna().unique())
    # Default selection is the first few states to show some data initially
    default_states = all_states[:3] if len(all_states) > 0 else []
    
    selected_states = st.sidebar.multiselect("Select States", all_states, default=default_states)

    # 2. Filter by Paradigm (using 'paradigm' column)
    all_paradigms = sorted(df['paradigm'].dropna().unique())
    selected_paradigms = st.sidebar.multiselect("Select Policy Paradigm", all_paradigms, default=all_paradigms)

    # 3. Filter by Mechanisms (Boolean)
    st.sidebar.subheader("Must Include Mechanisms:")
    
    # List matches the columns in the bill data
    mechanism_cols = [
        'age_verification',
        'parental_consent',
        'data_collection_limits',
        'algorithmic_restrictions',
        'duty_of_care',
        'risk_assessment_required',
        'default_privacy_settings',
        'school_based',
        'targets_all_platforms'
    ]
    
    mech_filters = {}
    for mech in mechanism_cols:
        # Check if column exists to avoid errors if CSV schema changes
        if mech in df.columns:
            label = format_mechanism_label(mech)
            mech_filters[mech] = st.sidebar.checkbox(label, value=False)

# --- Filtering Logic ---
if not df.empty:
    # Start with full dataframe
    filtered_df = df.copy()

    # Apply State filter
    if selected_states:
        filtered_df = filtered_df[filtered_df['state'].isin(selected_states)]

    # Apply Paradigm filter
    if selected_paradigms:
        filtered_df = filtered_df[filtered_df['paradigm'].isin(selected_paradigms)]

    # Apply Mechanism filters (AND logic: bill must have ALL selected mechanisms)
    for mech, is_checked in mech_filters.items():
        if is_checked and mech in filtered_df.columns:
            # Ensure boolean comparison works even if data is loaded as 0/1
            filtered_df = filtered_df[filtered_df[mech] == True]

    # --- Main Dashboard ---
    st.title("🛡️ Child Online Safety Legislation Explorer")
    st.markdown("Explore policy paradigms and mechanisms across state bills.")

    # Top Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Bills Found", len(filtered_df))
    col2.metric("States Represented", filtered_df['state'].nunique())
    
    # Calculate most common paradigm in selection
    if not filtered_df.empty:
        top_paradigm = filtered_df['paradigm'].mode()
        top_paradigm_val = top_paradigm[0] if not top_paradigm.empty else "None"
    else:
        top_paradigm_val = "N/A"
    col3.metric("Dominant Paradigm", top_paradigm_val)

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📄 Bill List", "📊 Analytics", "🧩 Mechanism Matrix"])

    with tab1:
        st.subheader("Filtered Bills")
        
        # Prepare columns configuration for st.dataframe
        column_config = {
            "name": st.column_config.TextColumn("Bill Name"),
            "state": st.column_config.TextColumn("State"),
            "paradigm": st.column_config.TextColumn("Policy Paradigm"),
            "description": st.column_config.TextColumn("Description", width="medium"),
        }
        
        for mech in mechanism_cols:
            if mech in df.columns:
                column_config[mech] = st.column_config.CheckboxColumn(
                    format_mechanism_label(mech),
                    disabled=True
                )

        # Select relevant columns to display
        display_cols = ['state', 'name', 'paradigm'] + [m for m in mechanism_cols if m in df.columns]
        
        st.dataframe(
            filtered_df[display_cols],
            column_config=column_config,
            use_container_width=True,
            hide_index=True
        )

    with tab2:
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.subheader("Bills by Paradigm")
            if not filtered_df.empty:
                paradigm_counts = filtered_df['paradigm'].value_counts().reset_index()
                paradigm_counts.columns = ['paradigm', 'count']
                
                chart = alt.Chart(paradigm_counts).mark_bar().encode(
                    x=alt.X('count', axis=alt.Axis(tickMinStep=1), title="Count"),
                    y=alt.Y('paradigm', sort='-x', title="Paradigm"),
                    color=alt.Color('paradigm', legend=None),
                    tooltip=['paradigm', 'count']
                ).properties(height=300)
                st.altair_chart(chart, use_container_width=True)
            else:
                st.info("No data to display.")

        with col_b:
            st.subheader("Mechanism Frequency")
            if not filtered_df.empty:
                # Sum boolean columns to get counts
                valid_mech_cols = [m for m in mechanism_cols if m in filtered_df.columns]
                
                if valid_mech_cols:
                    mech_counts = filtered_df[valid_mech_cols].sum().reset_index()
                    mech_counts.columns = ['mechanism', 'count']
                    # Format labels for the chart
                    mech_counts['label'] = mech_counts['mechanism'].apply(format_mechanism_label)
                    
                    chart_mech = alt.Chart(mech_counts).mark_bar().encode(
                        x=alt.X('count', title="Count"),
                        y=alt.Y('label', sort='-x', title="Mechanism"),
                        color=alt.value('#FFA500'), # Orange color
                        tooltip=['label', 'count']
                    ).properties(height=300)
                    st.altair_chart(chart_mech, use_container_width=True)
                else:
                    st.warning("No mechanism columns found in data.")
            else:
                st.info("No data to display.")

    with tab3:
        st.subheader("Mechanism Heatmap")
        st.markdown("View the overlap of mechanisms across the selected bills.")
        if not filtered_df.empty:
            # Set index to Bill Name (or State - Name for uniqueness)
            heatmap_df = filtered_df.copy()
            heatmap_df['Bill Identifier'] = heatmap_df['state'] + " - " + heatmap_df['name']
            
            valid_mech_cols = [m for m in mechanism_cols if m in heatmap_df.columns]
            
            if valid_mech_cols:
                heatmap_data = heatmap_df.set_index('Bill Identifier')[valid_mech_cols]
                
                # Map boolean values to emojis
                heatmap_display = heatmap_data.applymap(lambda x: "✅" if x else "❌")
                
                # Rename columns in the display dataframe for readability
                heatmap_display.columns = [format_mechanism_label(c) for c in heatmap_display.columns]
                
                st.dataframe(heatmap_display, use_container_width=True)
            else:
                st.warning("No mechanism columns to display.")
        else:
            st.info("No data to display.")

else:
    st.warning("Please ensure 'bills.csv' is in the directory and contains data.")

# --- Footer ---
st.markdown("---")
st.caption("Data classification analysis based on state legislation.")
st.markdown("Original data source: **[Integrity Institute - Technology Policy Tracker](https://www.techpolicytracker.com)**")
