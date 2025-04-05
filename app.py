import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta, date
import base64
import io
import re

# Set page configuration
st.set_page_config(
    page_title="Rimon Joiners and Leavers Dashboard",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 1rem;
        text-align: center;
    }
    .kpi-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
    }
    .kpi-value {
        font-size: 1.8rem;
        font-weight: 600;
    }
    .kpi-title {
        font-size: 1rem;
        color: #6B7280;
    }
    .green-text {
        color: #10B981;
    }
    .yellow-text {
        color: #F59E0B;
    }
    .red-text {
        color: #EF4444;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1E3A8A;
        margin: 1.5rem 0 1rem 0;
        border-bottom: 2px solid #E5E7EB;
        padding-bottom: 0.5rem;
    }
    .filter-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .download-button {
        background-color: #1E40AF;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        text-decoration: none;
        display: inline-block;
        margin-top: 1rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #f1f5f9;
        border-radius: 4px 4px 0 0;
        padding: 10px 20px;
        height: 50px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1E3A8A !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# Password Protection Function
def password_protect():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.markdown("<h1 class='main-header'>Rimon Joiners and Leavers Dashboard</h1>", unsafe_allow_html=True)
        password = st.text_input("Enter Password", type="password")
        if st.button("Login"):
            if password == "BrieflyAI2025":
                st.session_state.authenticated = True
                st.experimental_rerun()
            else:
                st.error("Incorrect Password. Please try again.")
        return False
    return True

# Safe function to get unique values from a column
def safe_get_unique(df, column_name):
    try:
        if column_name in df.columns:
            unique_values = df[column_name].unique()
            # Filter out None, NaN values
            unique_values = [value for value in unique_values if pd.notna(value)]
            return sorted(unique_values)
        else:
            return []
    except Exception as e:
        st.error(f"Error getting unique values for {column_name}: {e}")
        return []

# Data Loading Function
@st.cache_data(ttl=3600)  # Cache data for 1 hour
def load_data():
    try:
        # Load the actual data from CSV file
        df = pd.read_csv("Cleaned_Invoice_Data.csv")
        
        # Display info about loaded data
        st.sidebar.success(f"Loaded {len(df)} records from Cleaned_Invoice_Data.csv")
        st.sidebar.info(f"Columns found: {', '.join(df.columns[:5])}...")
        
        # Clean data - handle currency symbols and convert to numeric
        money_columns = [
            'Invoice_Total_in_USD', 'Invoice_Labor_Total_in_USD', 
            'Invoice_Expense_Total_in_USD', 'Invoice_Balance_Due_in_USD',
            'Payments_Applied_Against_Invoice_in_USD', 'Original Inv. Total',
            'Payments Received'
        ]
        
        for col in money_columns:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace('$', '', regex=False)
                df[col] = df[col].str.replace(',', '', regex=False)
                df[col] = df[col].str.replace('-', '0', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
        # Convert date columns
        date_columns = ['Invoice_Date', 'Last payment date', 'Invoice Date']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
                
        # Fix the TTM (Trailing Twelve Months) column if it exists
        if 'TTM?' in df.columns:
            df.rename(columns={'TTM?': 'TTM'}, inplace=True)
            
        # Make sure payment values are negative (to match accounting convention)
        payment_cols = [col for col in df.columns if 'payment' in col.lower() or 'received' in col.lower()]
        for col in payment_cols:
            if col in df.columns and df[col].dtype in [np.float64, np.int64]:
                # Make sure payments are stored as negative values
                mask = df[col] > 0
                df.loc[mask, col] = -df.loc[mask, col]
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        # Return empty DataFrame with appropriate columns
        return pd.DataFrame(columns=[
            'Invoice_Number', 'Invoice_Date', 'Client', 'Matter', 'Originator',
            'Invoice_Total_in_USD', 'Payments_Applied_Against_Invoice_in_USD',
            'Invoice_Balance_Due_in_USD', 'Last payment date', 
            'Days between Invoice date and last payment date'
        ])

# Download data as CSV
def download_csv(df):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="filtered_invoices.csv" class="download-button">Download CSV</a>'
    return href

# Download data as Excel
def download_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Invoices')
    excel_data = output.getvalue()
    b64 = base64.b64encode(excel_data).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="filtered_invoices.xlsx" class="download-button">Download Excel</a>'
    return href

# Helper functions for KPI formatting
def format_currency(value):
    return f"${value:,.2f}"

def format_percent(value):
    return f"{value:.2f}%"

def get_kpi_color(value, thresholds):
    low, high = thresholds
    if value >= high:
        return "green-text"
    elif value >= low:
        return "yellow-text"
    else:
        return "red-text"

# Safe helper for attorney performance
def get_attorney_performance(df, metric='invoice_total', top_n=10):
    try:
        if 'Originator' not in df.columns:
            st.warning("Originator column not found in data.")
            return pd.DataFrame()
        
        if df.empty:
            st.warning("No data available for performance analysis.")
            return pd.DataFrame()
        
        if metric == 'invoice_total':
            # Total invoiced
            attorney_perf = df.groupby('Originator')['Invoice_Total_in_USD'].sum().reset_index()
            attorney_perf.columns = ['Attorney', 'Value']
            attorney_perf['Metric'] = 'Total Invoiced'
        elif metric == 'collected':
            # Total collected
            payment_col = 'Payments_Applied_Against_Invoice_in_USD'
            if payment_col not in df.columns or df[payment_col].sum() == 0:
                payment_col = 'Payments Received'
                
            if payment_col not in df.columns:
                st.warning(f"Payment column ({payment_col}) not found in data.")
                return pd.DataFrame()
                
            attorney_perf = df.groupby('Originator')[payment_col].sum().reset_index()
            attorney_perf.columns = ['Attorney', 'Value']
            attorney_perf['Value'] = attorney_perf['Value'].abs()  # Convert to positive for display
            attorney_perf['Metric'] = 'Total Collected'
        elif metric == 'delay':
            # Average payment delay
            if 'Days between Invoice date and last payment date' not in df.columns:
                st.warning("Payment delay column not found in data.")
                return pd.DataFrame()
                
            attorney_perf = df[df['Days between Invoice date and last payment date'] != 'Unpaid'].copy()
            if attorney_perf.empty:
                st.warning("No payment delay data available.")
                return pd.DataFrame()
                
            attorney_perf['Days'] = pd.to_numeric(attorney_perf['Days between Invoice date and last payment date'], errors='coerce')
            attorney_perf = attorney_perf.groupby('Originator')['Days'].mean().reset_index()
            attorney_perf.columns = ['Attorney', 'Value']
            attorney_perf['Metric'] = 'Avg. Payment Delay (Days)'
        
        # Sort and get top/bottom
        if not attorney_perf.empty:
            if metric == 'delay':  # For delay, smaller is better
                top = attorney_perf.nsmallest(min(top_n, len(attorney_perf)), 'Value')
                bottom = attorney_perf.nlargest(min(top_n, len(attorney_perf)), 'Value')
            else:  # For invoiced and collected, higher is better
                top = attorney_perf.nlargest(min(top_n, len(attorney_perf)), 'Value')
                bottom = attorney_perf.nsmallest(min(top_n, len(attorney_perf)), 'Value')
            
            top['Rank'] = 'Top'
            bottom['Rank'] = 'Bottom'
            return pd.concat([top, bottom])
        
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error in attorney performance analysis: {e}")
        return pd.DataFrame()

# Extract attorney initials
def extract_initials(client_str):
    if pd.isna(client_str) or not isinstance(client_str, str):
        return None
    
    # Look for patterns like "(ABC)" or "(A)" at the end of strings
    initials_match = re.search(r'\(([A-Z]+)\)$', client_str)
    if initials_match:
        return initials_match.group(1)
    return None

# Analyze joiners and leavers over time
def analyze_joiners_leavers(df):
    try:
        if 'Originator' not in df.columns or 'Invoice_Date' not in df.columns:
            st.warning("Required columns (Originator, Invoice_Date) not found for joiners/leavers analysis.")
            return pd.DataFrame(), pd.DataFrame()
        
        if df.empty:
            st.warning("No data available for joiners/leavers analysis.")
            return pd.DataFrame(), pd.DataFrame()
        
        # Add year and month columns for grouping
        df['Year'] = df['Invoice_Date'].dt.year
        df['Month'] = df['Invoice_Date'].dt.month
        df['YearMonth'] = df['Invoice_Date'].dt.strftime('%Y-%m')
        
        # Get the first and last appearance of each attorney in the dataset
        first_appearance = df.groupby('Originator')['Invoice_Date'].min().reset_index()
        first_appearance.columns = ['Attorney', 'First_Invoice_Date']
        
        last_appearance = df.groupby('Originator')['Invoice_Date'].max().reset_index()
        last_appearance.columns = ['Attorney', 'Last_Invoice_Date']
        
        # Join the dataframes
        attorney_timeline = pd.merge(first_appearance, last_appearance, on='Attorney')
        
        # Add year and month of first and last appearance
        attorney_timeline['First_Year'] = attorney_timeline['First_Invoice_Date'].dt.year
        attorney_timeline['First_Month'] = attorney_timeline['First_Invoice_Date'].dt.month
        attorney_timeline['Last_Year'] = attorney_timeline['Last_Invoice_Date'].dt.year
        attorney_timeline['Last_Month'] = attorney_timeline['Last_Invoice_Date'].dt.month
        
        # Create monthly counts
        monthly_data = df.groupby(['Year', 'Month', 'YearMonth']).agg({
            'Originator': pd.Series.nunique,
        }).reset_index()
        monthly_data.columns = ['Year', 'Month', 'YearMonth', 'ActiveAttorneys']
        monthly_data = monthly_data.sort_values(['Year', 'Month'])
        
        # Determine joiners and leavers by month
        joiners = []
        leavers = []
        
        # Get unique year-months in chronological order
        year_months = sorted(df['YearMonth'].unique())
        
        for i, ym in enumerate(year_months):
            year, month = map(int, ym.split('-'))
            
            if i == 0:  # First month, everyone is a joiner
                attorneys_this_month = set(df[(df['Year'] == year) & (df['Month'] == month)]['Originator'].unique())
                joiners.append({
                    'YearMonth': ym,
                    'Year': year,
                    'Month': month,
                    'Joiners': len(attorneys_this_month),
                    'Joiner_List': ','.join(attorneys_this_month)
                })
                leavers.append({
                    'YearMonth': ym,
                    'Year': year,
                    'Month': month,
                    'Leavers': 0,
                    'Leaver_List': ''
                })
            else:
                # Get attorneys from previous and current month
                prev_ym = year_months[i-1]
                prev_year, prev_month = map(int, prev_ym.split('-'))
                
                attorneys_prev_month = set(df[(df['Year'] == prev_year) & (df['Month'] == prev_month)]['Originator'].unique())
                attorneys_this_month = set(df[(df['Year'] == year) & (df['Month'] == month)]['Originator'].unique())
                
                # Joiners are in this month but not in previous month
                new_joiners = attorneys_this_month - attorneys_prev_month
                
                # Leavers are in previous month but not in this month
                new_leavers = attorneys_prev_month - attorneys_this_month
                
                joiners.append({
                    'YearMonth': ym,
                    'Year': year,
                    'Month': month,
                    'Joiners': len(new_joiners),
                    'Joiner_List': ','.join(new_joiners)
                })
                
                leavers.append({
                    'YearMonth': ym,
                    'Year': year,
                    'Month': month,
                    'Leavers': len(new_leavers),
                    'Leaver_List': ','.join(new_leavers)
                })
        
        # Convert to dataframes
        joiners_df = pd.DataFrame(joiners)
        leavers_df = pd.DataFrame(leavers)
        
        # Merge for analysis
        movement_df = pd.merge(joiners_df, leavers_df, on=['YearMonth', 'Year', 'Month'])
        movement_df['Net_Change'] = movement_df['Joiners'] - movement_df['Leavers']
        
        return movement_df, attorney_timeline
    except Exception as e:
        st.error(f"Error in joiners/leavers analysis: {e}")
        return pd.DataFrame(), pd.DataFrame()

# Main application
def main():
    # Check password protection
    if not password_protect():
        return
    
    # Load data
    df = load_data()
    
    # Check if data is loaded properly
    if df.empty:
        st.error("No data loaded. Please check your data file.")
        return
    
    # Display data loading info
    st.sidebar.subheader("Data Information")
    st.sidebar.info(f"Number of records: {len(df)}")
    st.sidebar.info(f"Date range: {df['Invoice_Date'].min().date() if 'Invoice_Date' in df.columns and not df['Invoice_Date'].empty else 'N/A'} to {df['Invoice_Date'].max().date() if 'Invoice_Date' in df.columns and not df['Invoice_Date'].empty else 'N/A'}")
    
    # Extract attorney information from client field if available
    if 'Client' in df.columns:
        df['Attorney_Initials'] = df['Client'].apply(extract_initials)
    
    # Set up the dashboard
    st.markdown("<h1 class='main-header'>Rimon Joiners and Leavers Dashboard</h1>", unsafe_allow_html=True)
    
    # Global Filters Section
    with st.expander("🔧 Filters", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        # Date range filter
        if 'Invoice_Date' in df.columns and not df['Invoice_Date'].empty:
            min_date = df['Invoice_Date'].min()
            max_date = df['Invoice_Date'].max()
            
            if pd.notna(min_date) and pd.notna(max_date):
                with col1:
                    date_range = st.date_input(
                        "Date Range",
                        value=(min_date.date(), max_date.date()),
                        min_value=min_date.date(),
                        max_value=max_date.date()
                    )
                
                if len(date_range) == 2:
                    start_date, end_date = date_range
                    df_filtered = df[(df['Invoice_Date'].dt.date >= start_date) & 
                                    (df['Invoice_Date'].dt.date <= end_date)]
                else:
                    df_filtered = df
            else:
                df_filtered = df
        else:
            df_filtered = df
            
        # Client filter - Use safe function to avoid errors
        with col2:
            clients = ['All'] + safe_get_unique(df, 'Client')
            selected_client = st.selectbox("Client", options=clients)
            
        if selected_client != 'All' and 'Client' in df.columns:
            df_filtered = df_filtered[df_filtered['Client'] == selected_client]
        
        # Attorney filter - Use safe function to avoid errors
        with col3:
            attorneys = ['All'] + safe_get_unique(df, 'Originator') 
            selected_attorney = st.selectbox("Attorney", options=attorneys)
            
        if selected_attorney != 'All' and 'Originator' in df.columns:
            df_filtered = df_filtered[df_filtered['Originator'] == selected_attorney]
    
    # Main Dashboard Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📍 Summary", 
        "📈 Trends", 
        "👤 Attorney Performance", 
        "🧾 Invoice Explorer", 
        "⏱️ Payment Behavior"
    ])
    
    # Calculate KPIs
    if 'Invoice_Total_in_USD' in df_filtered.columns:
        total_invoiced = df_filtered['Invoice_Total_in_USD'].sum()
    else:
        total_invoiced = 0
        st.warning("Invoice_Total_in_USD column not found.")
    
    # Use the right payment column based on which exists in the data
    payment_col = 'Payments_Applied_Against_Invoice_in_USD'
    if payment_col not in df_filtered.columns or df_filtered[payment_col].sum() == 0:
        payment_col = 'Payments Received'
    
    if payment_col in df_filtered.columns:
        total_collected = df_filtered[payment_col].abs().sum()
    else:
        total_collected = 0
        st.warning(f"Payment column ({payment_col}) not found.")
        
    if 'Invoice_Balance_Due_in_USD' in df_filtered.columns:
        outstanding_balance = df_filtered['Invoice_Balance_Due_in_USD'].sum()
    else:
        outstanding_balance = 0
        st.warning("Invoice_Balance_Due_in_USD column not found.")
        
    collection_rate = (total_collected / total_invoiced * 100) if total_invoiced > 0 else 0
    
    # Analyze joiners and leavers
    movement_df, attorney_timeline = analyze_joiners_leavers(df_filtered)
    
    # 1. Summary Cards Tab
    with tab1:
        st.markdown("<h2 class='section-header'>📍 Summary Dashboard</h2>", unsafe_allow_html=True)
        
        # KPI Cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class='kpi-card'>
                <p class='kpi-title'>Total Invoiced (TTM)</p>
                <p class='kpi-value'>{format_currency(total_invoiced)}</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col2:
            st.markdown(f"""
            <div class='kpi-card'>
                <p class='kpi-title'>Total Collected</p>
                <p class='kpi-value'>{format_currency(total_collected)}</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col3:
            st.markdown(f"""
            <div class='kpi-card'>
                <p class='kpi-title'>Outstanding Balance</p>
                <p class='kpi-value'>{format_currency(outstanding_balance)}</p>
            </div>
            """, unsafe_allow_html=True)
            
        with col4:
            collection_color = get_kpi_color(collection_rate, (75, 90))
            st.markdown(f"""
            <div class='kpi-card'>
                <p class='kpi-title'>Collection Rate</p>
                <p class='kpi-value {collection_color}'>{format_percent(collection_rate)}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # YoY Comparison
        st.markdown("<h3>Year-over-Year Comparison</h3>", unsafe_allow_html=True)
        
        # Calculate YoY metrics if date information is available
        if 'Invoice_Date' in df_filtered.columns and not df_filtered['Invoice_Date'].empty:
            try:
                # Group by year and calculate metrics
                df_filtered['Year'] = df_filtered['Invoice_Date'].dt.year
                yearly_metrics = df_filtered.groupby('Year').agg({
                    'Invoice_Total_in_USD': 'sum',
                    payment_col: lambda x: abs(x.sum()),
                    'Invoice_Balance_Due_in_USD': 'sum'
                }).reset_index()
                
                # Calculate collection rate
                yearly_metrics['Collection_Rate'] = (yearly_metrics[payment_col] / 
                                                yearly_metrics['Invoice_Total_in_USD'] * 100)
                
                # Create bar chart
                fig = go.Figure()
                
                # Add traces
                fig.add_trace(go.Bar(
                    x=yearly_metrics['Year'],
                    y=yearly_metrics['Invoice_Total_in_USD'],
                    name='Total Invoiced',
                    marker_color='#3B82F6'
                ))
                
                fig.add_trace(go.Bar(
                    x=yearly_metrics['Year'],
                    y=yearly_metrics[payment_col],
                    name='Total Collected',
                    marker_color='#10B981'
                ))
                
                fig.add_trace(go.Scatter(
                    x=yearly_metrics['Year'],
                    y=yearly_metrics['Collection_Rate'],
                    name='Collection Rate (%)',
                    mode='lines+markers',
                    yaxis='y2',
                    line=dict(color='#EF4444', width=3),
                    marker=dict(size=10)
                ))
                
                # Update layout
                fig.update_layout(
                    title='Year-over-Year Financial Performance',
                    xaxis=dict(title='Year'),
                    yaxis=dict(title='Amount (USD)', side='left'),
                    yaxis2=dict(title='Collection Rate (%)', side='right', overlaying='y', range=[0, 100]),
                    legend=dict(orientation='h', yanchor='bottom', y=1.02),
                    barmode='group',
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error generating YoY comparison: {e}")
        else:
            st.warning("Date information is not available for year-over-year comparison.")
        
        # Joiners vs Leavers
        st.markdown("<h3>Joiners vs Leavers Analysis</h3>", unsafe_allow_html=True)
        
        if not movement_df.empty:
            try:
                # Create a figure with joiners, leavers, and net change
                fig = go.Figure()
                
                fig.add_trace(go.Bar(
                    x=movement_df['YearMonth'],
                    y=movement_df['Joiners'],
                    name='Joiners',
                    marker_color='#10B981'
                ))
                
                fig.add_trace(go.Bar(
                    x=movement_df['YearMonth'],
                    y=movement_df['Leavers'],
                    name='Leavers',
                    marker_color='#EF4444'
                ))
                
                fig.add_trace(go.Scatter(
                    x=movement_df['YearMonth'],
                    y=movement_df['Net_Change'],
                    name='Net Change',
                    mode='lines+markers',
                    line=dict(color='#3B82F6', width=3),
                    marker=dict(size=8)
                ))
                
                fig.update_layout(
                    title='Monthly Joiners vs Leavers',
                    xaxis=dict(title='Month', tickangle=45),
                    yaxis=dict(title='Number of Attorneys'),
                    barmode='group',
                    legend=dict(orientation='h', yanchor='bottom', y=1.02),
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Summary of joiners and leavers
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Joiners & Leavers Summary")
                    total_joiners = movement_df['Joiners'].sum()
                    total_leavers = movement_df['Leavers'].sum()
                    net_change = total_joiners - total_leavers
                    
                    st.markdown(f"""
                    <div style="padding: 1rem; background-color: #f8f9fa; border-radius: 10px;">
                        <p><strong>Total Joiners:</strong> {total_joiners}</p>
                        <p><strong>Total Leavers:</strong> {total_leavers}</p>
                        <p><strong>Net Change:</strong> <span class="{get_kpi_color(net_change, (0, 1))}">{net_change}</span></p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.subheader("Year-wise Trend")
                    yearly_movement = movement_df.groupby('Year').agg({
                        'Joiners': 'sum',
                        'Leavers': 'sum'
                    }).reset_index()
                    yearly_movement['Net_Change'] = yearly_movement['Joiners'] - yearly_movement['Leavers']
                    
                    st.dataframe(yearly_movement, use_container_width=True)
            except Exception as e:
                st.error(f"Error in joiners/leavers visualization: {e}")
        else:
            st.warning("Not enough data to analyze joiners and leavers.")
        
        # Top & Bottom Performers
        st.markdown("<h3>Top & Bottom Performers</h3>", unsafe_allow_html=True)
        
        # Get performance data
        top_billed = get_attorney_performance(df_filtered, metric='invoice_total', top_n=5)
        top_collected = get_attorney_performance(df_filtered, metric='collected', top_n=5)
        
        if not top_billed.empty and not top_collected.empty:
            try:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("By Billing")
                    top_billed_chart = px.bar(
                        top_billed,
                        x='Value',
                        y='Attorney',
                        color='Rank',
                        orientation='h',
                        title='Top & Bottom Attorneys by Billing',
                        labels={'Value': 'Total Billed (USD)', 'Attorney': ''},
                        color_discrete_map={'Top': '#10B981', 'Bottom': '#EF4444'}
                    )
                    st.plotly_chart(top_billed_chart, use_container_width=True)
                
                with col2:
                    st.subheader("By Collections")
                    top_collected_chart = px.bar(
                        top_collected,
                        x='Value',
                        y='Attorney',
                        color='Rank',
                        orientation='h',
                        title='Top & Bottom Attorneys by Collections',
                        labels={'Value': 'Total Collected (USD)', 'Attorney': ''},
                        color_discrete_map={'Top': '#10B981', 'Bottom': '#EF4444'}
                    )
                    st.plotly_chart(top_collected_chart, use_container_width=True)
            except Exception as e:
                st.error(f"Error generating top/bottom performers charts: {e}")
        else:
            st.warning("Not enough data to analyze top and bottom performers.")
    
    # 2. Trends Dashboard Tab
    with tab2:
        st.markdown("<h2 class='section-header'>📈 Trends Dashboard</h2>", unsafe_allow_html=True)
        
        # Revenue over time
        st.subheader("Revenue Over Time")
        
        if 'Invoice_Date' in df_filtered.columns and not df_filtered['Invoice_Date'].empty:
            try:
                # Group by month
                df_filtered['YearMonth'] = df_filtered['Invoice_Date'].dt.strftime('%Y-%m')
                monthly_revenue = df_filtered.groupby('YearMonth').agg({
                    'Invoice_Total_in_USD': 'sum',
                    payment_col: lambda x: abs(x.sum()),
                    'Invoice_Balance_Due_in_USD': 'sum'
                }).reset_index()
                
                # Sort by year-month
                monthly_revenue = monthly_revenue.sort_values('YearMonth')
                
                # Create line chart
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=monthly_revenue['YearMonth'],
                    y=monthly_revenue['Invoice_Total_in_USD'],
                    name='Total Invoiced',
                    mode='lines+markers',
                    line=dict(color='#3B82F6', width=3)
                ))
                
                fig.update_layout(
                    title='Monthly Revenue',
                    xaxis=dict(title='Month', tickangle=45),
                    yaxis=dict(title='Amount (USD)'),
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Paid vs Outstanding
                st.subheader("Paid vs Outstanding")
                
                # Create stacked bar chart
                monthly_revenue['Outstanding'] = monthly_revenue['Invoice_Total_in_USD'] - monthly_revenue[payment_col]
                
                fig = go.Figure()
                
                fig.add_trace(go.Bar(
                    x=monthly_revenue['YearMonth'],
                    y=monthly_revenue[payment_col],
                    name='Paid',
                    marker_color='#10B981'
                ))
                
                fig.add_trace(go.Bar(
                    x=monthly_revenue['YearMonth'],
                    y=monthly_revenue['Outstanding'],
                    name='Outstanding',
                    marker_color='#EF4444'
                ))
                
                fig.update_layout(
                    title='Paid vs Outstanding by Month',
                    xaxis=dict(title='Month', tickangle=45),
                    yaxis=dict(title='Amount (USD)'),
                    barmode='stack',
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error generating revenue trends: {e}")
        else:
            st.warning("Date information is not available for revenue trends.")
        
        # Client contribution
        st.subheader("Client Contribution")
        
        if 'Client' in df_filtered.columns and not df_filtered.empty:
            try:
                # Get top clients by invoice total
                top_clients = df_filtered.groupby('Client')['Invoice_Total_in_USD'].sum().nlargest(10).reset_index()
                
                # Calculate "Others" category
                others_total = df_filtered['Invoice_Total_in_USD'].sum() - top_clients['Invoice_Total_in_USD'].sum()
                
                if others_total > 0:
                    others_df = pd.DataFrame({'Client': ['Others'], 'Invoice_Total_in_USD': [others_total]})
                    top_clients = pd.concat([top_clients, others_df])
                
                # Create pie chart
                fig = px.pie(
                    top_clients,
                    values='Invoice_Total_in_USD',
                    names='Client',
                    title='Top 10 Clients by Revenue',
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                
                fig.update_traces(textposition='inside', textinfo='percent+label')
                
                fig.update_layout(
                    showlegend=True,
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error generating client contribution chart: {e}")
        else:
            st.warning("Client information is not available for contribution analysis.")
        
        # Collections vs targets
        st.subheader("Collections vs Targets")
        
        # For this section, we need to create placeholder targets since they're not in the data
        if 'Invoice_Date' in df_filtered.columns and not df_filtered['Invoice_Date'].empty and monthly_revenue is not None:
            try:
                # Assume targets are 90% of invoiced amounts (placeholder for actual targets)
                monthly_revenue['Target'] = monthly_revenue['Invoice_Total_in_USD'] * 0.9
                monthly_revenue['Achievement_Rate'] = (monthly_revenue[payment_col] / monthly_revenue['Target'] * 100).clip(0, 100)
                
                # Create a color-coded achievement chart
                fig = go.Figure()
                
                for i, row in monthly_revenue.iterrows():
                    color = '#10B981' if row['Achievement_Rate'] >= 90 else '#F59E0B' if row['Achievement_Rate'] >= 75 else '#EF4444'
                    
                    fig.add_trace(go.Bar(
                        x=[row['YearMonth']],
                        y=[row['Achievement_Rate']],
                        name=row['YearMonth'],
                        marker_color=color,
                        showlegend=False
                    ))
                
                fig.add_shape(
                    type='line',
                    x0=0,
                    y0=90,
                    x1=len(monthly_revenue),
                    y1=90,
                    line=dict(
                        color='green',
                        width=2,
                        dash='dash'
                    )
                )
                
                fig.update_layout(
                    title='Monthly Collection Achievement vs Target (90%)',
                    xaxis=dict(title='Month', tickangle=45, tickmode='array', tickvals=list(range(len(monthly_revenue))), ticktext=monthly_revenue['YearMonth']),
                    yaxis=dict(title='Achievement Rate (%)', range=[0, 100]),
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error generating collections vs targets chart: {e}")
        else:
            st.warning("Date information is not available for collections vs targets analysis.")
    
    # 3. Attorney Performance Tab
    with tab3:
        st.markdown("<h2 class='section-header'>👤 Attorney Performance</h2>", unsafe_allow_html=True)
        
        # Top 10 / Bottom 10 attorneys
        st.subheader("Top 10 / Bottom 10 Attorneys")
        
        # Metric selector
        metric_options = {
            'invoice_total': 'By Total Billed',
            'collected': 'By Total Collected',
            'delay': 'By Payment Delay'
        }
        
        selected_metric = st.selectbox(
            "Select Performance Metric",
            options=list(metric_options.keys()),
            format_func=lambda x: metric_options[x]
        )
        
        # Get performance data
        attorney_perf = get_attorney_performance(df_filtered, metric=selected_metric, top_n=10)
        
        if not attorney_perf.empty:
            try:
                # Create horizontal bar chart
                fig = px.bar(
                    attorney_perf,
                    x='Value',
                    y='Attorney',
                    color='Rank',
                    orientation='h',
                    title=f'Attorney Performance {metric_options[selected_metric]}',
                    labels={'Value': 'Value', 'Attorney': 'Attorney'},
                    color_discrete_map={'Top': '#10B981', 'Bottom': '#EF4444'}
                )
                
                # Format axis labels based on metric
                if selected_metric == 'invoice_total' or selected_metric == 'collected':
                    fig.update_layout(xaxis_title='Amount (USD)')
                elif selected_metric == 'delay':
                    fig.update_layout(xaxis_title='Days')
                
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error generating attorney performance chart: {e}")
        else:
            st.warning("Attorney performance data is not available.")
        
        # Joiners & Leavers
        st.subheader("Joiners & Leavers: Year-wise Trend")
        
        if not movement_df.empty:
            try:
                # Create year-wise summary
                yearly_movement = movement_df.groupby('Year').agg({
                    'Joiners': 'sum',
                    'Leavers': 'sum'
                }).reset_index()
                
                yearly_movement['Net_Change'] = yearly_movement['Joiners'] - yearly_movement['Leavers']
                
                # Create bar chart
                fig = go.Figure()
                
                fig.add_trace(go.Bar(
                    x=yearly_movement['Year'],
                    y=yearly_movement['Joiners'],
                    name='Joiners',
                    marker_color='#10B981'
                ))
                
                fig.add_trace(go.Bar(
                    x=yearly_movement['Year'],
                    y=yearly_movement['Leavers'],
                    name='Leavers',
                    marker_color='#EF4444'
                ))
                
                fig.add_trace(go.Scatter(
                    x=yearly_movement['Year'],
                    y=yearly_movement['Net_Change'],
                    name='Net Change',
                    mode='lines+markers',
                    line=dict(color='#3B82F6', width=3),
                    marker=dict(size=10)
                ))
                
                fig.update_layout(
                    title='Yearly Joiners vs Leavers',
                    xaxis=dict(title='Year'),
                    yaxis=dict(title='Number of Attorneys'),
                    barmode='group',
                    legend=dict(orientation='h', yanchor='bottom', y=1.02),
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Net change
                st.subheader("Net Change in Attorneys")
                
                # Create a running total of net change
                cumulative_change = movement_df.copy()
                cumulative_change['Cumulative_Net_Change'] = cumulative_change['Net_Change'].cumsum()
                
                # Create line chart
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=cumulative_change['YearMonth'],
                    y=cumulative_change['Cumulative_Net_Change'],
                    mode='lines+markers',
                    line=dict(color='#3B82F6', width=3),
                    marker=dict(size=8)
                ))
                
                fig.update_layout(
                    title='Cumulative Net Change in Attorneys',
                    xaxis=dict(title='Month', tickangle=45),
                    yaxis=dict(title='Number of Attorneys'),
                    height=500
                )
                
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Error generating joiners/leavers year-wise trend: {e}")
        else:
            st.warning("Joiners and leavers data is not available.")
        
        # Team or office filter
        if 'Accounting Entity' in df_filtered.columns:
            st.subheader("Filter by Team or Office")
            
            offices = ['All'] + safe_get_unique(df_filtered, 'Accounting Entity')
            selected_office = st.selectbox("Select Office", offices)
            
            if selected_office != 'All':
                try:
                    office_df = df_filtered[df_filtered['Accounting Entity'] == selected_office]
                    
                    # Performance by office
                    office_attorneys = office_df.groupby('Originator')['Invoice_Total_in_USD'].sum().reset_index()
                    office_attorneys.columns = ['Attorney', 'Total_Billed']
                    office_attorneys = office_attorneys.sort_values('Total_Billed', ascending=False)
                    
                    st.dataframe(office_attorneys, use_container_width=True)
                    
                    # Office performance chart
                    fig = px.bar(
                        office_attorneys,
                        x='Attorney',
                        y='Total_Billed',
                        title=f'Attorney Performance in {selected_office}',
                        labels={'Total_Billed': 'Total Billed (USD)', 'Attorney': 'Attorney'},
                        color='Total_Billed',
                        color_continuous_scale='Blues'
                    )
                    
                    fig.update_layout(
                        xaxis_tickangle=45,
                        height=500
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Error filtering by office: {e}")
            else:
                st.info("Select an office to view detailed performance.")
        else:
            st.warning("Office information is not available.")
    
    # 4. Invoice Explorer Tab
    with tab4:
        st.markdown("<h2 class='section-header'>🧾 Invoice Explorer</h2>", unsafe_allow_html=True)
        
        # Create a searchable, filterable data table
        st.subheader("Searchable Invoice Table")
        
        # Filter options
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_options = ['All'] + safe_get_unique(df_filtered, 'Invoice Status')
            selected_status = st.selectbox("Invoice Status", status_options)
        
        with col2:
            min_amount = st.number_input("Min Amount", min_value=0.0, value=0.0)
        
        with col3:
            max_amount = st.number_input(
                "Max Amount", 
                min_value=0.0, 
                value=float(df_filtered['Invoice_Total_in_USD'].max()) if 'Invoice_Total_in_USD' in df_filtered.columns and not df_filtered.empty else 1000000.0
            )
        
        # Apply filters
        filtered_invoices = df_filtered.copy()
        
        if selected_status != 'All' and 'Invoice Status' in filtered_invoices.columns:
            filtered_invoices = filtered_invoices[filtered_invoices['Invoice Status'] == selected_status]
        
        if 'Invoice_Total_in_USD' in filtered_invoices.columns:
            filtered_invoices = filtered_invoices[
                (filtered_invoices['Invoice_Total_in_USD'] >= min_amount) &
                (filtered_invoices['Invoice_Total_in_USD'] <= max_amount)
            ]
        
        # Search box
        search_term = st.text_input("Search (Client, Matter, Invoice Number)")
        
        if search_term:
            # Apply search to relevant columns
            search_mask = pd.Series(False, index=filtered_invoices.index)
            
            for col in ['Client', 'Matter', 'Invoice_Number']:
                if col in filtered_invoices.columns:
                    search_mask |= filtered_invoices[col].astype(str).str.contains(search_term, case=False, na=False)
            
            filtered_invoices = filtered_invoices[search_mask]
        
        # Highlight overdue invoices
        if ('Last payment date' in filtered_invoices.columns and 
            'Invoice_Date' in filtered_invoices.columns and 
            'Invoice_Balance_Due_in_USD' in filtered_invoices.columns):
            try:
                # Identify overdue invoices (balance due > 0 and more than 30 days old)
                filtered_invoices['Overdue'] = (
                    (filtered_invoices['Invoice_Balance_Due_in_USD'] > 0) &
                    (filtered_invoices['Last payment date'] == 'Unpaid') &
                    ((pd.Timestamp.now() - filtered_invoices['Invoice_Date']).dt.days > 30)
                )
            except Exception as e:
                st.warning(f"Could not calculate overdue status: {e}")
        
        # Select columns to display
        display_columns = [
            'Invoice_Number', 'Invoice_Date', 'Client', 'Matter', 'Originator',
            'Invoice_Total_in_USD', payment_col, 'Invoice_Balance_Due_in_USD',
            'Last payment date', 'Days between Invoice date and last payment date'
        ]
        
        # Filter to only include columns that exist in the dataframe
        display_columns = [col for col in display_columns if col in filtered_invoices.columns]
        
        if not display_columns:
            display_columns = filtered_invoices.columns.tolist()
        
        # Show the table
        st.dataframe(
            filtered_invoices[display_columns],
            use_container_width=True,
            hide_index=True
        )
        
        # Number of results
        st.write(f"Showing {len(filtered_invoices)} invoices")
        
        # Download options
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(download_csv(filtered_invoices[display_columns]), unsafe_allow_html=True)
        
        with col2:
            st.markdown(download_excel(filtered_invoices[display_columns]), unsafe_allow_html=True)
    
    # 5. Payment Behavior Tab
    with tab5:
        st.markdown("<h2 class='section-header'>⏱️ Payment Behavior</h2>", unsafe_allow_html=True)
        
        # Average delay per client/matter
        st.subheader("Average Payment Delay")
        
        if ('Client' in df_filtered.columns and 
            'Days between Invoice date and last payment date' in df_filtered.columns and 
            not df_filtered.empty):
            try:
                # Calculate average payment delay by client
                payment_delay_df = df_filtered[df_filtered['Days between Invoice date and last payment date'] != 'Unpaid'].copy()
                
                if not payment_delay_df.empty:
                    payment_delay_df['Delay_Days'] = pd.to_numeric(payment_delay_df['Days between Invoice date and last payment date'])
                    
                    client_delay = payment_delay_df.groupby('Client')['Delay_Days'].mean().reset_index()
                    client_delay.columns = ['Client', 'Avg_Delay_Days']
                    client_delay = client_delay.sort_values('Avg_Delay_Days', ascending=False)
                    
                    # Top 10 clients by delay
                    top_delay_clients = client_delay.head(10)
                    
                    # Create bar chart
                    fig = px.bar(
                        top_delay_clients,
                        x='Client',
                        y='Avg_Delay_Days',
                        title='Top 10 Clients by Average Payment Delay',
                        labels={'Avg_Delay_Days': 'Average Delay (Days)', 'Client': 'Client'},
                        color='Avg_Delay_Days',
                        color_continuous_scale='Reds'
                    )
                    
                    fig.update_layout(
                        xaxis_tickangle=45,
                        height=500
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("No payment delay data available.")
            except Exception as e:
                st.error(f"Error analyzing payment delay: {e}")
        else:
            st.warning("Client and payment delay data is not available.")
        
        # Aged receivables
        st.subheader("Aged Receivables")
        
        if ('Invoice_Date' in df_filtered.columns and 
            'Invoice_Balance_Due_in_USD' in df_filtered.columns and 
            not df_filtered.empty):
            try:
                # Calculate age of receivables
                df_filtered['Days_Outstanding'] = (pd.Timestamp.now() - df_filtered['Invoice_Date']).dt.days
                
                # Only consider invoices with balance due
                receivables_df = df_filtered[df_filtered['Invoice_Balance_Due_in_USD'] > 0].copy()
                
                if not receivables_df.empty:
                    # Create age buckets
                    bins = [0, 30, 60, 90, 120, float('inf')]
                    labels = ['0-30 days', '31-60 days', '61-90 days', '91-120 days', '120+ days']
                    receivables_df['Age_Bucket'] = pd.cut(receivables_df['Days_Outstanding'], bins=bins, labels=labels)
                    
                    # Sum by age bucket
                    aged_receivables = receivables_df.groupby('Age_Bucket')['Invoice_Balance_Due_in_USD'].sum().reset_index()
                    
                    # Create bar chart
                    fig = px.bar(
                        aged_receivables,
                        x='Age_Bucket',
                        y='Invoice_Balance_Due_in_USD',
                        title='Aged Receivables',
                        labels={'Invoice_Balance_Due_in_USD': 'Amount (USD)', 'Age_Bucket': 'Age'},
                        color='Age_Bucket',
                        color_discrete_sequence=['#10B981', '#3B82F6', '#F59E0B', '#FB7185', '#EF4444']
                    )
                    
                    # Format y-axis as currency
                    fig.update_layout(
                        yaxis=dict(title='Amount (USD)'),
                        height=500
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Table view
                    st.dataframe(aged_receivables, use_container_width=True, hide_index=True)
                else:
                    st.warning("No outstanding receivables found.")
            except Exception as e:
                st.error(f"Error analyzing aged receivables: {e}")
        else:
            st.warning("Invoice date and balance due data is not available.")
        
        # Scatter: Size vs Payment speed
        st.subheader("Invoice Size vs. Payment Speed")
        
        if ('Invoice_Total_in_USD' in df_filtered.columns and 
            'Days between Invoice date and last payment date' in df_filtered.columns and 
            not df_filtered.empty):
            try:
                # Prepare data
                scatter_df = df_filtered[df_filtered['Days between Invoice date and last payment date'] != 'Unpaid'].copy()
                
                if not scatter_df.empty:
                    scatter_df['Payment_Days'] = pd.to_numeric(scatter_df['Days between Invoice date and last payment date'])
                    
                    # Create scatter plot
                    fig = px.scatter(
                        scatter_df,
                        x='Invoice_Total_in_USD',
                        y='Payment_Days',
                        color='Client',
                        size='Invoice_Total_in_USD',
                        hover_name='Client',
                        hover_data=['Invoice_Number', 'Invoice_Date', 'Originator'],
                        title='Invoice Size vs. Payment Speed',
                        labels={
                            'Invoice_Total_in_USD': 'Invoice Amount (USD)',
                            'Payment_Days': 'Days to Payment'
                        }
                    )
                    
                    fig.update_layout(
                        xaxis=dict(title='Invoice Amount (USD)'),
                        yaxis=dict(title='Days to Payment'),
                        height=600
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Analysis summary
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Calculate correlation
                        correlation = scatter_df['Invoice_Total_in_USD'].corr(scatter_df['Payment_Days'])
                        
                        st.markdown(f"""
                        <div style="padding: 1rem; background-color: #f8f9fa; border-radius: 10px;">
                            <h4>Analysis</h4>
                            <p><strong>Correlation:</strong> {correlation:.2f}</p>
                            <p><strong>Interpretation:</strong> {
                                "Strong positive correlation (larger invoices take longer to pay)" if correlation > 0.5 else
                                "Moderate positive correlation" if correlation > 0.3 else
                                "Weak positive correlation" if correlation > 0 else
                                "No correlation" if correlation == 0 else
                                "Negative correlation (larger invoices are paid faster)"
                            }</p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        # Average payment days by invoice size range
                        scatter_df['Size_Range'] = pd.cut(
                            scatter_df['Invoice_Total_in_USD'],
                            bins=[0, 1000, 5000, 10000, float('inf')],
                            labels=['< $1K', '$1K-$5K', '$5K-$10K', '> $10K']
                        )
                        
                        size_vs_delay = scatter_df.groupby('Size_Range')['Payment_Days'].mean().reset_index()
                        
                        st.dataframe(size_vs_delay, use_container_width=True, hide_index=True)
                else:
                    st.warning("No payment speed data available.")
            except Exception as e:
                st.error(f"Error analyzing invoice size vs payment speed: {e}")
        else:
            st.warning("Invoice amount and payment days data is not available.")

# Run the main application
if __name__ == "__main__":
    main()
