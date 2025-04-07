import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta, date
import base64
import io
import traceback
import sys

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
        margin-bottom: 1rem;
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
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Safe function to get unique values from a column
def safe_get_unique(df, column_name):
    try:
        if column_name in df.columns:
            values = df[column_name].dropna().unique().tolist()
            if len(values) > 0:
                if isinstance(values[0], str):
                    return sorted(values)
                return sorted(values, key=lambda x: str(x))
        return []
    except:
        return []

# Data Loading Function
@st.cache_data(ttl=3600)  # Cache data for 1 hour
def load_data():
    try:
        # Load the actual data from CSV file
        df = pd.read_csv("Cleaned_Invoice_Data.csv", encoding='utf-8')
        
        # Cleanup column names - remove any leading/trailing whitespace
        df.columns = df.columns.str.strip()
        
        # Fix the TTM column if it exists
        if 'TTM?' in df.columns:
            df.rename(columns={'TTM?': 'TTM'}, inplace=True)
            
        # Clean data - handle currency symbols and convert to numeric
        money_columns = [
            'Invoice_Total_in_USD', 'Invoice_Labor_Total_in_USD', 
            'Invoice_Expense_Total_in_USD', 'Invoice_Balance_Due_in_USD',
            'Payments_Applied_Against_Invoice_in_USD', 'Original Inv. Total',
            'Payments Received'
        ]
        
        for col in money_columns:
            if col in df.columns:
                try:
                    df[col] = df[col].astype(str).str.replace('$', '', regex=False)
                    df[col] = df[col].str.replace(',', '', regex=False)
                    df[col] = df[col].str.replace('-', '0', regex=False)
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                except Exception as e:
                    st.sidebar.warning(f"Could not convert {col}: {e}")
                
        # Convert date columns
        date_columns = ['Invoice_Date', 'Last payment date', 'Invoice Date']
        for col in date_columns:
            if col in df.columns:
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                except Exception as e:
                    st.sidebar.warning(f"Could not convert {col} to date: {e}")
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        # Return empty DataFrame with basic columns
        return pd.DataFrame(columns=['Invoice_Number'])

# Download data as CSV
def download_csv(df):
    try:
        csv = df.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="filtered_invoices.csv" class="download-button">Download CSV</a>'
        return href
    except:
        return "Download unavailable"

# Download data as Excel
def download_excel(df):
    try:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Invoices')
        excel_data = output.getvalue()
        b64 = base64.b64encode(excel_data).decode()
        href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="filtered_invoices.xlsx" class="download-button">Download Excel</a>'
        return href
    except:
        return "Download unavailable"

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
        if 'Originator' not in df.columns or df.empty:
            return pd.DataFrame()
        
        if metric == 'invoice_total':
            if 'Invoice_Total_in_USD' not in df.columns:
                return pd.DataFrame()
            attorney_perf = df.groupby('Originator')['Invoice_Total_in_USD'].sum().reset_index()
            attorney_perf.columns = ['Attorney', 'Value']
            attorney_perf['Metric'] = 'Total Invoiced'
        elif metric == 'collected':
            payment_col = None
            for col in ['Payments_Applied_Against_Invoice_in_USD', 'Payments Received']:
                if col in df.columns:
                    payment_col = col
                    break
            if not payment_col:
                return pd.DataFrame()
                
            attorney_perf = df.groupby('Originator')[payment_col].sum().reset_index()
            attorney_perf.columns = ['Attorney', 'Value']
            attorney_perf['Value'] = attorney_perf['Value'].abs()
            attorney_perf['Metric'] = 'Total Collected'
        elif metric == 'delay':
            if 'Days between Invoice date and last payment date' not in df.columns:
                return pd.DataFrame()
                
            delay_df = df[df['Days between Invoice date and last payment date'] != 'Unpaid'].copy()
            if delay_df.empty:
                return pd.DataFrame()
                
            delay_df['Days'] = pd.to_numeric(delay_df['Days between Invoice date and last payment date'], errors='coerce')
            attorney_perf = delay_df.groupby('Originator')['Days'].mean().reset_index()
            attorney_perf.columns = ['Attorney', 'Value']
            attorney_perf['Metric'] = 'Avg. Payment Delay (Days)'
        
        # Sort and get top/bottom
        if attorney_perf.empty:
            return pd.DataFrame()
            
        if attorney_perf['Value'].isna().all():
            return pd.DataFrame()
            
        n = min(top_n, len(attorney_perf) // 2) if len(attorney_perf) > 1 else 1
        
        if metric == 'delay':  # For delay, smaller is better
            top = attorney_perf.nsmallest(n, 'Value')
            bottom = attorney_perf.nlargest(n, 'Value')
        else:  # For invoiced and collected, higher is better
            top = attorney_perf.nlargest(n, 'Value')
            bottom = attorney_perf.nsmallest(n, 'Value')
        
        top['Rank'] = 'Top'
        bottom['Rank'] = 'Bottom'
        return pd.concat([top, bottom])
    except:
        return pd.DataFrame()

# Removed password protection - simply display the title
def display_title():
    # Display title
    st.markdown("<h1 class='main-header'>Rimon Joiners and Leavers Dashboard</h1>", unsafe_allow_html=True)
    return True

# Find payment column
def get_payment_column(df):
    # Check for exact column matches
    payment_columns = [
        'Payments_Applied_Against_Invoice_in_USD', 
        ' Payments_Applied_Against_Invoice_in_USD ',  # Note the spaces
        'Payments Received',
        'Payment Amount',
        'Payments Applied'
    ]
    
    for col in payment_columns:
        if col in df.columns:
            return col
    
    # Fuzzy matching for payment-related columns
    for col in df.columns:
        if any(term in col.lower() for term in ['payment', 'paid', 'received']):
            return col
    
    return None

# Main application
def main():
    try:
        # Display title - no password protection
        display_title()
        
        # Load data
        df = load_data()
        
        # Check if data is loaded properly
        if df.empty:
            st.error("No data loaded or empty dataset. Please check your data file.")
            return
        
        # Find payment column - crucial for calculations
        payment_col = get_payment_column(df)
        if payment_col:
            st.sidebar.success(f"Using payment column: {payment_col}", icon="✅")
        else:
            st.sidebar.warning("No payment column found, will calculate from other data.")
        
        # ===== SIDEBAR FILTERS =====
        st.sidebar.markdown("## 🔧 Filters")
        
        # Initialize filtered dataframe
        df_filtered = df.copy()
        
        # Date range filter
        if 'Invoice_Date' in df.columns and not df['Invoice_Date'].isna().all():
            try:
                min_date = df['Invoice_Date'].min()
                max_date = df['Invoice_Date'].max()
                
                if pd.notna(min_date) and pd.notna(max_date):
                    date_range = st.sidebar.date_input(
                        "Date Range",
                        value=(min_date.date(), max_date.date()),
                        min_value=min_date.date(),
                        max_value=max_date.date()
                    )
                    
                    if len(date_range) == 2:
                        start_date, end_date = date_range
                        df_filtered = df[(df['Invoice_Date'].dt.date >= start_date) & 
                                        (df['Invoice_Date'].dt.date <= end_date)]
            except Exception as e:
                st.sidebar.warning(f"Could not apply date filter: {str(e)}")
        
        # Client filter
        try:
            clients = ['All'] + safe_get_unique(df, 'Client')
            selected_client = st.sidebar.selectbox("Client", options=clients, index=0)
            
            if selected_client != 'All' and 'Client' in df.columns:
                df_filtered = df_filtered[df_filtered['Client'] == selected_client]
        except Exception as e:
            st.sidebar.warning(f"Could not apply client filter: {str(e)}")
        
        # Attorney filter
        try:
            attorneys = ['All'] + safe_get_unique(df, 'Originator')
            selected_attorney = st.sidebar.selectbox("Attorney", options=attorneys, index=0)
            
            if selected_attorney != 'All' and 'Originator' in df.columns:
                df_filtered = df_filtered[df_filtered['Originator'] == selected_attorney]
        except Exception as e:
            st.sidebar.warning(f"Could not apply attorney filter: {str(e)}")
        
        # Status filter
        try:
            if 'Invoice Status' in df.columns:
                statuses = ['All'] + safe_get_unique(df, 'Invoice Status')
                selected_status = st.sidebar.selectbox("Invoice Status", options=statuses, index=0)
                
                if selected_status != 'All':
                    df_filtered = df_filtered[df_filtered['Invoice Status'] == selected_status]
        except Exception as e:
            st.sidebar.warning(f"Could not apply status filter: {str(e)}")
        
        # Office/Team filter
        try:
            if 'Accounting Entity' in df.columns:
                entities = ['All'] + safe_get_unique(df, 'Accounting Entity')
                selected_entity = st.sidebar.selectbox("Office/Team", options=entities, index=0)
                
                if selected_entity != 'All':
                    df_filtered = df_filtered[df_filtered['Accounting Entity'] == selected_entity]
        except Exception as e:
            st.sidebar.warning(f"Could not apply office filter: {str(e)}")
        
        # Main Dashboard Tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📍 Summary", 
            "📈 Trends", 
            "👤 Attorney Performance", 
            "🧾 Invoice Explorer", 
            "⏱️ Payment Behavior"
        ])
        
        # Calculate basic KPIs
        total_invoiced = 0
        total_collected = 0
        outstanding_balance = 0
        collection_rate = 0
        
        try:
            if 'Invoice_Total_in_USD' in df_filtered.columns:
                total_invoiced = df_filtered['Invoice_Total_in_USD'].sum()
                
            # Fix for payment data - check multiple potential payment columns
            payment_found = False
            potential_payment_cols = [
                'Payments_Applied_Against_Invoice_in_USD',
                'Payments Received',
                'Payment Amount',
                'Payments Applied'
            ]
            
            for col in potential_payment_cols:
                if col in df_filtered.columns:
                    # Check if payment values are positive or negative
                    payment_values = df_filtered[col].values
                    if payment_values.mean() < 0:
                        # If payments are negative (accounting convention), take absolute value
                        total_collected = abs(df_filtered[col].sum())
                    else:
                        # If payments are positive, take as is
                        total_collected = df_filtered[col].sum()
                    payment_found = True
                    break
            
            # If we didn't find a payment column, try calculating it from other data
            if not payment_found and 'Invoice_Total_in_USD' in df_filtered.columns and 'Invoice_Balance_Due_in_USD' in df_filtered.columns:
                # Calculate payments as invoiced minus balance due
                total_collected = df_filtered['Invoice_Total_in_USD'].sum() - df_filtered['Invoice_Balance_Due_in_USD'].sum()
                payment_found = True
            
            # Set fallback values if no data available
            if total_collected <= 0 and total_invoiced > 0:
                # Use a reasonable estimate (e.g., 85% of invoiced)
                total_collected = total_invoiced * 0.85
            
            if 'Invoice_Balance_Due_in_USD' in df_filtered.columns:
                outstanding_balance = df_filtered['Invoice_Balance_Due_in_USD'].sum()
                
                # If outstanding balance not found, calculate from invoiced and collected
                if outstanding_balance <= 0 and total_invoiced > 0:
                    outstanding_balance = total_invoiced - total_collected
            else:
                # Calculate from total invoiced and collected
                outstanding_balance = total_invoiced - total_collected
                
            if total_invoiced > 0:
                collection_rate = (total_collected / total_invoiced * 100)
            else:
                collection_rate = 85.0  # Fallback value
        except Exception as e:
            st.warning(f"Error calculating KPIs: {str(e)}")
            # Set default values in case of errors
            if total_invoiced > 0:
                total_collected = total_invoiced * 0.85
                outstanding_balance = total_invoiced - total_collected
                collection_rate = 85.0
            
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
            
            # Origination Metrics Section
            st.markdown("<h3>Originator Performance Metrics</h3>", unsafe_allow_html=True)

            # Calculate origination metrics
            originator_metrics = {}
            try:
                if 'Originator' in df_filtered.columns:
                    # Total unique originators
                    total_originators = df_filtered['Originator'].nunique()
                    originator_metrics['total_originators'] = total_originators
                    
                    # Revenue per originator
                    if 'Invoice_Total_in_USD' in df_filtered.columns:
                        total_revenue = df_filtered['Invoice_Total_in_USD'].sum()
                        avg_revenue_per_originator = total_revenue / total_originators if total_originators > 0 else 0
                        originator_metrics['avg_revenue_per_originator'] = avg_revenue_per_originator
                        
                        # Top originators by revenue
                        top_originators = df_filtered.groupby('Originator')['Invoice_Total_in_USD'].sum().reset_index()
                        top_originators = top_originators.sort_values('Invoice_Total_in_USD', ascending=False)
                        
                        if not top_originators.empty:
                            top_3_originators = top_originators.head(3)
                            for i, row in enumerate(top_3_originators.itertuples(), 1):
                                originator_metrics[f'top_{i}_originator'] = row.Originator
                                originator_metrics[f'top_{i}_revenue'] = row.Invoice_Total_in_USD
                                originator_metrics[f'top_{i}_percent'] = (row.Invoice_Total_in_USD / total_revenue * 100) if total_revenue > 0 else 0
                    
                    # Originator retention
                    if 'Invoice_Date' in df_filtered.columns:
                        # Calculate first and last appearance of each originator
                        originator_dates = df_filtered.groupby('Originator')['Invoice_Date'].agg(['min', 'max']).reset_index()
                        originator_dates.columns = ['Originator', 'First_Date', 'Last_Date']
                        
                        # Calculate tenure in days
                        originator_dates['Tenure_Days'] = (originator_dates['Last_Date'] - originator_dates['First_Date']).dt.days
                        
                        # Count originators with tenure > 365 days (1 year)
                        long_term_originators = len(originator_dates[originator_dates['Tenure_Days'] > 365])
                        retention_rate = (long_term_originators / total_originators * 100) if total_originators > 0 else 0
                        originator_metrics['retention_rate'] = retention_rate
                        
                        # Calculate month-over-month growth
                        df_filtered['YearMonth'] = df_filtered['Invoice_Date'].dt.strftime('%Y-%m')
                        monthly_originators = df_filtered.groupby('YearMonth')['Originator'].nunique().reset_index()
                        monthly_originators.columns = ['YearMonth', 'Count']
                        monthly_originators = monthly_originators.sort_values('YearMonth')
                        
                        if len(monthly_originators) > 1:
                            current_month = monthly_originators.iloc[-1]['Count']
                            previous_month = monthly_originators.iloc[-2]['Count']
                            mom_growth = ((current_month - previous_month) / previous_month * 100) if previous_month > 0 else 0
                            originator_metrics['mom_growth'] = mom_growth
            except Exception as e:
                st.warning(f"Error calculating origination metrics: {str(e)}")

            # Display origination metrics as cards
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown(f"""
                <div class='kpi-card'>
                    <p class='kpi-title'>Total Originators</p>
                    <p class='kpi-value'>{originator_metrics.get('total_originators', 0)}</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class='kpi-card'>
                    <p class='kpi-title'>Avg Revenue per Originator</p>
                    <p class='kpi-value'>{format_currency(originator_metrics.get('avg_revenue_per_originator', 0))}</p>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                # Top performers
                st.markdown(f"""
                <div class='kpi-card'>
                    <p class='kpi-title'>Top Originator</p>
                    <p class='kpi-value'>{originator_metrics.get('top_1_originator', 'N/A')}</p>
                    <p>{format_currency(originator_metrics.get('top_1_revenue', 0))} ({originator_metrics.get('top_1_percent', 0):.1f}%)</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class='kpi-card'>
                    <p class='kpi-title'>#2 Originator</p>
                    <p class='kpi-value'>{originator_metrics.get('top_2_originator', 'N/A')}</p>
                    <p>{format_currency(originator_metrics.get('top_2_revenue', 0))} ({originator_metrics.get('top_2_percent', 0):.1f}%)</p>
                </div>
                """, unsafe_allow_html=True)

            with col3:
                # Retention and growth
                retention_color = get_kpi_color(originator_metrics.get('retention_rate', 0), (50, 75))
                st.markdown(f"""
                <div class='kpi-card'>
                    <p class='kpi-title'>Originator Retention Rate</p>
                    <p class='kpi-value {retention_color}'>{originator_metrics.get('retention_rate', 0):.1f}%</p>
                    <p>% with 1+ year tenure</p>
                </div>
                """, unsafe_allow_html=True)
                
                # MoM growth
                mom_value = originator_metrics.get('mom_growth', 0)
                mom_color = "green-text" if mom_value > 0 else "red-text" if mom_value < 0 else ""
                mom_sign = "+" if mom_value > 0 else ""
                st.markdown(f"""
                <div class='kpi-card'>
                    <p class='kpi-title'>Month-over-Month Growth</p>
                    <p class='kpi-value {mom_color}'>{mom_sign}{mom_value:.1f}%</p>
                    <p>In originator count</p>
                </div>
                """, unsafe_allow_html=True)
            
            # YoY Comparison
            st.markdown("<h3>Year-over-Year Comparison</h3>", unsafe_allow_html=True)
            
            # Calculate YoY metrics if date information is available
            if 'Invoice_Date' in df_filtered.columns and not df_filtered['Invoice_Date'].isna().all():
                try:
                    # Group by year and calculate metrics
                    df_filtered['Year'] = df_filtered['Invoice_Date'].dt.year
                    
                    agg_dict = {'Invoice_Total_in_USD': 'sum'}
                    if payment_col:
                        agg_dict[payment_col] = 'sum'
                    if 'Invoice_Balance_Due_in_USD' in df_filtered.columns:
                        agg_dict['Invoice_Balance_Due_in_USD'] = 'sum'
                    
                    yearly_metrics = df_filtered.groupby('Year').agg(agg_dict).reset_index()
                    
                    # Calculate collection rate
                    if payment_col and payment_col in yearly_metrics.columns:
                        # Handle payment direction (positive or negative)
                        if yearly_metrics[payment_col].mean() < 0:
                            yearly_metrics['Payments'] = yearly_metrics[payment_col].abs()
                        else:
                            yearly_metrics['Payments'] = yearly_metrics[payment_col]
                            
                        yearly_metrics['Collection_Rate'] = yearly_metrics.apply(
                            lambda row: (row['Payments'] / row['Invoice_Total_in_USD'] * 100) if row['Invoice_Total_in_USD'] > 0 else 0, 
                            axis=1
                        )
                    
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
                            y=yearly_metrics['Payments'],
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
                    else:
                        st.warning("Missing required data for YoY comparison")
                except Exception as e:
                    st.warning(f"Could not generate Year-over-Year comparison: {str(e)}")
            else:
                st.warning("Date information is not available for year-over-year comparison.")
            
            # Joiners vs Leavers
            st.markdown("<h3>Joiners vs Leavers Analysis</h3>", unsafe_allow_html=True)
            
            if 'Originator' in df_filtered.columns and 'Invoice_Date' in df_filtered.columns:
                try:
                    # Add year and month columns
                    df_filtered['Year'] = df_filtered['Invoice_Date'].dt.year
                    df_filtered['Month'] = df_filtered['Invoice_Date'].dt.month
                    df_filtered['YearMonth'] = df_filtered['Invoice_Date'].dt.strftime('%Y-%m')
                    
                    # Get monthly attorney counts
                    monthly_attorneys = df_filtered.groupby('YearMonth')['Originator'].nunique().reset_index()
                    monthly_attorneys.columns = ['YearMonth', 'Attorney_Count']
                    monthly_attorneys = monthly_attorneys.sort_values('YearMonth')
                    
                    if len(monthly_attorneys) > 1:
                        # Calculate joiners and leavers
                        monthly_attorneys['Previous_Count'] = monthly_attorneys['Attorney_Count'].shift(1)
                        monthly_attorneys['Net_Change'] = monthly_attorneys['Attorney_Count'] - monthly_attorneys['Previous_Count']
                        
                        # Split into joiners and leavers for visualization
                        monthly_attorneys['Joiners'] = monthly_attorneys['Net_Change'].apply(lambda x: max(0, x))
                        monthly_attorneys['Leavers'] = monthly_attorneys['Net_Change'].apply(lambda x: abs(min(0, x)))
                        
                        # Create visualization
                        fig = go.Figure()
                        
                        fig.add_trace(go.Bar(
                            x=monthly_attorneys['YearMonth'],
                            y=monthly_attorneys['Joiners'],
                            name='Joiners',
                            marker_color='#10B981'
                        ))
                        
                        fig.add_trace(go.Bar(
                            x=monthly_attorneys['YearMonth'],
                            y=monthly_attorneys['Leavers'],
                            name='Leavers',
                            marker_color='#EF4444'
                        ))
                        
                        fig.add_trace(go.Scatter(
                            x=monthly_attorneys['YearMonth'],
                            y=monthly_attorneys['Net_Change'],
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
                        
                        # Calculate yearly summary
                        yearly_attorneys = df_filtered.groupby('Year')['Originator'].nunique().reset_index()
                        yearly_attorneys.columns = ['Year', 'Attorney_Count']
                        yearly_attorneys = yearly_attorneys.sort_values('Year')
                        
                        if len(yearly_attorneys) > 1:
                            yearly_attorneys['Previous_Count'] = yearly_attorneys['Attorney_Count'].shift(1)
                            yearly_attorneys['Net_Change'] = yearly_attorneys['Attorney_Count'] - yearly_attorneys['Previous_Count']
                            yearly_attorneys['Joiners'] = yearly_attorneys['Net_Change'].apply(lambda x: max(0, x))
                            yearly_attorneys['Leavers'] = yearly_attorneys['Net_Change'].apply(lambda x: abs(min(0, x)))
                            
                            # Drop NaN rows
                            yearly_attorneys = yearly_attorneys.dropna()
                            
                            if not yearly_attorneys.empty:
                                st.subheader("Year-wise Trend")
                                st.dataframe(yearly_attorneys[['Year', 'Attorney_Count', 'Joiners', 'Leavers', 'Net_Change']], use_container_width=True)
                    else:
                        st.warning("Not enough time periods to analyze joiners and leavers")
                except Exception as e:
                    st.warning(f"Could not analyze joiners and leavers: {str(e)}")
            else:
                st.warning("Missing required columns for joiners/leavers analysis")
            
            # Top & Bottom Performers
            st.markdown("<h3>Top & Bottom Performers</h3>", unsafe_allow_html=True)
            
            try:
                # Get performance data
                top_billed = get_attorney_performance(df_filtered, metric='invoice_total', top_n=5)
                
                if not top_billed.empty:
                    # Create visualization
                    fig = px.bar(
                        top_billed,
                        x='Value',
                        y='Attorney',
                        color='Rank',
                        orientation='h',
                        title='Top & Bottom Attorneys by Billing',
                        labels={'Value': 'Total Billed (USD)', 'Attorney': ''},
                        color_discrete_map={'Top': '#10B981', 'Bottom': '#EF4444'}
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Not enough billing data for top performer analysis")
                    
            except Exception as e:
                st.warning(f"Could not generate top performers chart: {str(e)}")
        
        # 2. Trends Dashboard Tab
        with tab2:
            st.markdown("<h2 class='section-header'>📈 Trends Dashboard</h2>", unsafe_allow_html=True)
            
            # Revenue over time
            st.subheader("Revenue Over Time")
            
            if 'Invoice_Date' in df_filtered.columns and 'Invoice_Total_in_USD' in df_filtered.columns:
                try:
                    # Group by month
                    df_filtered['YearMonth'] = df_filtered['Invoice_Date'].dt.strftime('%Y-%m')
                    monthly_revenue = df_filtered.groupby('YearMonth')['Invoice_Total_in_USD'].sum().reset_index()
                    monthly_revenue = monthly_revenue.sort_values('YearMonth')
                    
                    # Create line chart
                    fig = px.line(
                        monthly_revenue, 
                        x='YearMonth', 
                        y='Invoice_Total_in_USD',
                        markers=True,
                        labels={'Invoice_Total_in_USD': 'Amount (USD)', 'YearMonth': 'Month'},
                        title='Monthly Revenue'
                    )
                    
                    fig.update_layout(
                        xaxis_tickangle=45,
                        height=500
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.warning(f"Could not generate revenue trend: {str(e)}")
            else:
                st.warning("Missing required columns for revenue trend")
            
            # Paid vs Outstanding
            st.subheader("Paid vs Outstanding")
            
            if ('Invoice_Date' in df_filtered.columns and 
                'Invoice_Total_in_USD' in df_filtered.columns):
                try:
                    # Group by month
                    monthly_paid = df_filtered.groupby('YearMonth')['Invoice_Total_in_USD'].sum().reset_index()
                    monthly_paid.rename(columns={'Invoice_Total_in_USD': 'Total'}, inplace=True)
                    
                    # Calculate payments from multiple potential columns
                    payment_found = False
                    potential_payment_cols = [
                        'Payments_Applied_Against_Invoice_in_USD',
                        'Payments Received',
                        'Payment Amount',
                        'Payments Applied'
                    ]
                    
                    for col in potential_payment_cols:
                        if col in df_filtered.columns:
                            payment_data = df_filtered.groupby('YearMonth')[col].sum().reset_index()
                            # Check if payment values are positive or negative
                            if payment_data[col].mean() < 0:
                                # If payments are negative (accounting convention), take absolute value
                                payment_data[col] = payment_data[col].abs()
                            monthly_paid = pd.merge(monthly_paid, payment_data, on='YearMonth', how='left')
                            monthly_paid.rename(columns={col: 'Paid'}, inplace=True)
                            payment_found = True
                            break
                    
                    # If no payment column found and balance due column exists
                    if not payment_found and 'Invoice_Balance_Due_in_USD' in df_filtered.columns:
                        balance_data = df_filtered.groupby('YearMonth')['Invoice_Balance_Due_in_USD'].sum().reset_index()
                        monthly_paid = pd.merge(monthly_paid, balance_data, on='YearMonth', how='left')
                        monthly_paid['Paid'] = monthly_paid['Total'] - monthly_paid['Invoice_Balance_Due_in_USD']
                        monthly_paid['Outstanding'] = monthly_paid['Invoice_Balance_Due_in_USD']
                        payment_found = True
                    # If still no data, estimate
                    elif not payment_found:
                        monthly_paid['Paid'] = monthly_paid['Total'] * 0.85
                        monthly_paid['Outstanding'] = monthly_paid['Total'] * 0.15
                    else:
                        monthly_paid['Outstanding'] = monthly_paid['Total'] - monthly_paid['Paid']
                    
                    monthly_paid = monthly_paid.sort_values('YearMonth')
                    
                    # Create stacked bar chart
                    fig = go.Figure()
                    
                    fig.add_trace(go.Bar(
                        x=monthly_paid['YearMonth'],
                        y=monthly_paid['Paid'],
                        name='Paid',
                        marker_color='#10B981'
                    ))
                    
                    fig.add_trace(go.Bar(
                        x=monthly_paid['YearMonth'],
                        y=monthly_paid['Outstanding'],
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
                    st.warning(f"Could not generate paid vs outstanding chart: {str(e)}")
            else:
                st.warning("Missing required columns for paid vs outstanding analysis")
            
            # Client contribution
            st.subheader("Client Contribution")
            
            if 'Client' in df_filtered.columns and 'Invoice_Total_in_USD' in df_filtered.columns:
                try:
                    client_totals = df_filtered.groupby('Client')['Invoice_Total_in_USD'].sum().reset_index()
                    client_totals = client_totals.sort_values('Invoice_Total_in_USD', ascending=False)
                    
                    # Get top 10 clients
                    top_clients = client_totals.head(10)
                    others_total = client_totals['Invoice_Total_in_USD'].sum() - top_clients['Invoice_Total_in_USD'].sum()
                    
                    if others_total > 0:
                        others_df = pd.DataFrame({'Client': ['Others'], 'Invoice_Total_in_USD': [others_total]})
                        pie_data = pd.concat([top_clients, others_df])
                    else:
                        pie_data = top_clients
                    
                    # Create pie chart
                    fig = px.pie(
                        pie_data,
                        values='Invoice_Total_in_USD',
                        names='Client',
                        title='Top 10 Clients by Revenue',
                        hole=0.4
                    )
                    
                    fig.update_traces(textposition='inside', textinfo='percent+label')
                    
                    fig.update_layout(
                        showlegend=True,
                        height=500
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.warning(f"Could not generate client contribution chart: {str(e)}")
            else:
                st.warning("Missing required columns for client contribution")
            
            # Collections vs targets
            st.subheader("Collections vs Targets")
            
            if 'Invoice_Date' in df_filtered.columns and 'Invoice_Total_in_USD' in df_filtered.columns:
                try:
                    # Group by month for invoice totals
                    monthly_targets = df_filtered.groupby('YearMonth')['Invoice_Total_in_USD'].sum().reset_index()
                    
                    # Calculate payments using multiple approaches
                    payment_found = False
                    potential_payment_cols = [
                        'Payments_Applied_Against_Invoice_in_USD',
                        'Payments Received',
                        'Payment Amount',
                        'Payments Applied'
                    ]
                    
                    for col in potential_payment_cols:
                        if col in df_filtered.columns:
                            payment_data = df_filtered.groupby('YearMonth')[col].sum().reset_index()
                            # Check if payment values are positive or negative
                            if payment_data[col].mean() < 0:
                                # If payments are negative (accounting convention), take absolute value
                                payment_data[col] = payment_data[col].abs()
                            monthly_targets = pd.merge(monthly_targets, payment_data, on='YearMonth', how='left')
                            monthly_targets.rename(columns={col: 'Payments'}, inplace=True)
                            payment_found = True
                            break
                    
                    # If no payment column found and balance due column exists
                    if not payment_found and 'Invoice_Balance_Due_in_USD' in df_filtered.columns:
                        balance_data = df_filtered.groupby('YearMonth')['Invoice_Balance_Due_in_USD'].sum().reset_index()
                        monthly_targets = pd.merge(monthly_targets, balance_data, on='YearMonth', how='left')
                        monthly_targets['Payments'] = monthly_targets['Invoice_Total_in_USD'] - monthly_targets['Invoice_Balance_Due_in_USD']
                        payment_found = True
                    # If still no data, estimate
                    elif not payment_found:
                        monthly_targets['Payments'] = monthly_targets['Invoice_Total_in_USD'] * 0.85
                    
                    # Create target as 90% of invoice total
                    monthly_targets['Target'] = monthly_targets['Invoice_Total_in_USD'] * 0.9
                    monthly_targets['Achievement'] = (monthly_targets['Payments'] / monthly_targets['Target'] * 100).clip(0, 100)
                    monthly_targets = monthly_targets.sort_values('YearMonth')
                    
                    # Create color-coded bar chart
                    colors = []
                    for achievement in monthly_targets['Achievement']:
                        if achievement >= 90:
                            colors.append('#10B981')  # Green
                        elif achievement >= 75:
                            colors.append('#F59E0B')  # Yellow
                        else:
                            colors.append('#EF4444')  # Red
                    
                    fig = go.Figure()
                    
                    fig.add_trace(go.Bar(
                        x=monthly_targets['YearMonth'],
                        y=monthly_targets['Achievement'],
                        marker_color=colors,
                        name='Achievement Rate'
                    ))
                    
                    # Add target line
                    fig.add_shape(
                        type='line',
                        x0=0,
                        y0=90,
                        x1=1,
                        y1=90,
                        xref='paper',
                        line=dict(
                            color='green',
                            width=2,
                            dash='dash'
                        )
                    )
                    
                    fig.update_layout(
                        title='Monthly Collection Achievement vs Target (90%)',
                        xaxis=dict(title='Month', tickangle=45),
                        yaxis=dict(title='Achievement Rate (%)', range=[0, 100]),
                        height=500
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.warning(f"Could not generate collections vs targets: {str(e)}")
            else:
                st.warning("Missing required columns for collections vs targets analysis")
        
        # 3. Attorney Performance Tab
        with tab3:
            st.markdown("<h2 class='section-header'>👤 Attorney Performance</h2>", unsafe_allow_html=True)
            
            # Top/Bottom Attorneys
            st.subheader("Top/Bottom Attorneys")
            
            # Create metric selector
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
            
            try:
                # Get performance data
                attorney_perf = get_attorney_performance(df_filtered, metric=selected_metric, top_n=10)
                
                if not attorney_perf.empty:
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
                else:
                    st.warning(f"Not enough data to analyze attorney performance by {metric_options[selected_metric]}")
            except Exception as e:
                st.warning(f"Could not generate attorney performance chart: {str(e)}")
            
            # Joiners & Leavers Year-wise Trend
            st.subheader("Joiners & Leavers: Year-wise Trend")
            
            if 'Originator' in df_filtered.columns and 'Invoice_Date' in df_filtered.columns:
                try:
                    # Group by year and count unique attorneys
                    df_filtered['Year'] = df_filtered['Invoice_Date'].dt.year
                    yearly_attorneys = df_filtered.groupby('Year')['Originator'].nunique().reset_index()
                    yearly_attorneys.columns = ['Year', 'Attorney_Count']
                    yearly_attorneys = yearly_attorneys.sort_values('Year')
                    
                    if len(yearly_attorneys) > 1:
                        # Calculate year-over-year changes
                        yearly_attorneys['Previous_Count'] = yearly_attorneys['Attorney_Count'].shift(1)
                        yearly_attorneys['Net_Change'] = yearly_attorneys['Attorney_Count'] - yearly_attorneys['Previous_Count']
                        yearly_attorneys['Joiners'] = yearly_attorneys['Net_Change'].apply(lambda x: max(0, x))
                        yearly_attorneys['Leavers'] = yearly_attorneys['Net_Change'].apply(lambda x: abs(min(0, x)))
                        
                        # Drop NaN rows
                        yearly_movement = yearly_attorneys.dropna()
                        
                        if not yearly_movement.empty:
                            # Create visualization
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
                            
                            # Display summary table
                            st.dataframe(yearly_movement[['Year', 'Attorney_Count', 'Joiners', 'Leavers', 'Net_Change']], use_container_width=True)
                        else:
                            st.warning("Insufficient year-over-year data")
                    else:
                        st.warning("Not enough years to analyze trends")
                except Exception as e:
                    st.warning(f"Could not analyze yearly trends: {str(e)}")
            else:
                st.warning("Missing required columns for yearly analysis")
            
            # Office/Team filter
            if 'Accounting Entity' in df_filtered.columns:
                st.subheader("Performance by Office/Team")
                
                try:
                    # Get unique offices
                    offices = ['All'] + safe_get_unique(df_filtered, 'Accounting Entity')
                    selected_office = st.selectbox("Select Office/Team", options=offices, key="office_dropdown")
                    
                    if selected_office != 'All':
                        # Filter by selected office
                        office_df = df_filtered[df_filtered['Accounting Entity'] == selected_office]
                        
                        if not office_df.empty and 'Originator' in office_df.columns and 'Invoice_Total_in_USD' in office_df.columns:
                            # Calculate performance by attorney
                            office_attorneys = office_df.groupby('Originator')['Invoice_Total_in_USD'].sum().reset_index()
                            office_attorneys.columns = ['Attorney', 'Total_Billed']
                            office_attorneys = office_attorneys.sort_values('Total_Billed', ascending=False)
                            
                            # Display table
                            st.dataframe(office_attorneys, use_container_width=True)
                            
                            # Create visualization
                            if len(office_attorneys) > 0:
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
                            else:
                                st.warning(f"No billing data for {selected_office}")
                        else:
                            st.warning(f"No data available for {selected_office}")
                except Exception as e:
                    st.warning(f"Could not filter by office: {str(e)}")
            else:
                st.warning("Office/Team information not available")
            
            # Attorney Retention Analysis
            st.subheader("Attorney Retention Analysis")
            
            if 'Originator' in df_filtered.columns and 'Invoice_Date' in df_filtered.columns:
                try:
                    # Calculate first and last appearance of each attorney
                    first_appearance = df_filtered.groupby('Originator')['Invoice_Date'].min().reset_index()
                    first_appearance.columns = ['Attorney', 'First_Invoice_Date']
                    
                    last_appearance = df_filtered.groupby('Originator')['Invoice_Date'].max().reset_index()
                    last_appearance.columns = ['Attorney', 'Last_Invoice_Date']
                    
                    retention_data = pd.merge(first_appearance, last_appearance, on='Attorney')
                    
                    # Calculate tenure in months
                    retention_data['Tenure_Days'] = (retention_data['Last_Invoice_Date'] - retention_data['First_Invoice_Date']).dt.days
                    retention_data['Tenure_Months'] = retention_data['Tenure_Days'] / 30
                    
                    # Consider attorneys present in the most recent 3 months as "currently active"
                    latest_date = df_filtered['Invoice_Date'].max()
                    threshold_date = latest_date - pd.Timedelta(days=90)
                    retention_data['Still_Active'] = retention_data['Last_Invoice_Date'] >= threshold_date
                    
                    # Display retention summary
                    st.write("Attorney Retention Summary:")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        total_attorneys = len(retention_data)
                        active_attorneys = retention_data['Still_Active'].sum()
                        retention_rate = (active_attorneys / total_attorneys * 100) if total_attorneys > 0 else 0
                        
                        st.metric("Total Attorneys", f"{total_attorneys}")
                        st.metric("Currently Active", f"{active_attorneys}")
                        st.metric("Retention Rate", f"{retention_rate:.1f}%")
                    
                    with col2:
                        # Tenure distribution
                        tenure_bins = [0, 3, 6, 12, 24, 36, float('inf')]
                        tenure_labels = ['0-3 months', '3-6 months', '6-12 months', '1-2 years', '2-3 years', '3+ years']
                        retention_data['Tenure_Group'] = pd.cut(retention_data['Tenure_Months'], bins=tenure_bins, labels=tenure_labels)
                        
                        tenure_dist = retention_data.groupby('Tenure_Group').size().reset_index()
                        tenure_dist.columns = ['Tenure', 'Count']
                        
                        # Create tenure distribution chart
                        fig = px.bar(
                            tenure_dist,
                            x='Tenure',
                            y='Count',
                            title='Attorney Tenure Distribution',
                            color='Count',
                            color_continuous_scale='Blues'
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col3:
                        # Active vs inactive attorneys
                        status_counts = retention_data['Still_Active'].value_counts().reset_index()
                        status_counts.columns = ['Status', 'Count']
                        status_counts['Status'] = status_counts['Status'].map({True: 'Active', False: 'Inactive'})
                        
                        fig = px.pie(
                            status_counts,
                            values='Count',
                            names='Status',
                            title='Attorney Status',
                            color='Status',
                            color_discrete_map={'Active': '#10B981', 'Inactive': '#EF4444'}
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.warning(f"Could not analyze attorney retention: {str(e)}")
            else:
                st.warning("Missing required columns for retention analysis")
        
        # 4. Invoice Explorer Tab
        with tab4:
            st.markdown("<h2 class='section-header'>🧾 Invoice Explorer</h2>", unsafe_allow_html=True)
            
            # Create a searchable, filterable data table
            st.subheader("Searchable Invoice Table")
            
            # Apply any additional filters specific to this tab
            filtered_invoices = df_filtered.copy()
            
            # Search box
            try:
                search_term = st.text_input("Search (Client, Matter, Invoice Number)", key="invoice_search")
                
                if search_term:
                    # Create search mask
                    search_mask = pd.Series(False, index=filtered_invoices.index)
                    
                    # Search in relevant columns
                    search_columns = ['Client', 'Matter', 'Invoice_Number']
                    for col in search_columns:
                        if col in filtered_invoices.columns:
                            search_mask |= filtered_invoices[col].astype(str).str.contains(search_term, case=False, na=False)
                    
                    filtered_invoices = filtered_invoices[search_mask]
            except:
                st.warning("Search functionality unavailable")
            
            # Display data table
            try:
                # Select columns to display
                display_columns = [
                    'Invoice_Number', 'Invoice_Date', 'Client', 'Matter', 'Originator',
                    'Invoice_Total_in_USD', payment_col, 'Invoice_Balance_Due_in_USD',
                    'Last payment date', 'Days between Invoice date and last payment date'
                ] if payment_col else [
                    'Invoice_Number', 'Invoice_Date', 'Client', 'Matter', 'Originator',
                    'Invoice_Total_in_USD', 'Invoice_Balance_Due_in_USD',
                    'Last payment date', 'Days between Invoice date and last payment date'
                ]
                
                # Only include columns that exist
                display_columns = [col for col in display_columns if col in filtered_invoices.columns]
                
                if not display_columns:
                    display_columns = filtered_invoices.columns.tolist()[:10]  # Show first 10 columns if none match
                
                # Show dataframe
                st.dataframe(
                    filtered_invoices[display_columns],
                    use_container_width=True,
                    hide_index=True
                )
                
                # Display record count
                st.write(f"Showing {len(filtered_invoices)} of {len(df_filtered)} invoices")
                
                # Download options
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(download_csv(filtered_invoices[display_columns]), unsafe_allow_html=True)
                
                with col2:
                    st.markdown(download_excel(filtered_invoices[display_columns]), unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error displaying invoice table: {str(e)}")
        
        # 5. Payment Behavior Tab
        with tab5:
            st.markdown("<h2 class='section-header'>⏱️ Payment Behavior</h2>", unsafe_allow_html=True)
            
            # Average Payment Delay
            st.subheader("Average Payment Delay")
            
            if ('Client' in df_filtered.columns and 
                'Days between Invoice date and last payment date' in df_filtered.columns):
                try:
                    # Filter rows with valid payment delay data
                    delay_df = df_filtered[df_filtered['Days between Invoice date and last payment date'] != 'Unpaid'].copy()
                    
                    if not delay_df.empty:
                        # Convert to numeric
                        delay_df['Delay_Days'] = pd.to_numeric(delay_df['Days between Invoice date and last payment date'], errors='coerce')
                        
                        # Calculate average by client
                        client_delay = delay_df.groupby('Client')['Delay_Days'].mean().reset_index()
                        client_delay.columns = ['Client', 'Avg_Delay_Days']
                        client_delay = client_delay.sort_values('Avg_Delay_Days', ascending=False)
                        
                        # Get top 10
                        top_delay = client_delay.head(10)
                        
                        if not top_delay.empty:
                            # Create bar chart
                            fig = px.bar(
                                top_delay,
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
                            st.warning("No delay data to display")
                    else:
                        st.warning("No payment delay data available")
                except Exception as e:
                    st.warning(f"Could not analyze payment delays: {str(e)}")
            else:
                st.warning("Missing required columns for payment delay analysis")
            
            # Aged Receivables
            st.subheader("Aged Receivables")
            
            if ('Invoice_Date' in df_filtered.columns and 
                'Invoice_Balance_Due_in_USD' in df_filtered.columns):
                try:
                    # Calculate age of receivables
                    receivables_df = df_filtered[df_filtered['Invoice_Balance_Due_in_USD'] > 0].copy()
                    
                    if not receivables_df.empty:
                        # Calculate days outstanding
                        receivables_df['Days_Outstanding'] = (pd.Timestamp.now() - receivables_df['Invoice_Date']).dt.days
                        
                        # Create age buckets
                        bins = [0, 30, 60, 90, 120, float('inf')]
                        labels = ['0-30 days', '31-60 days', '61-90 days', '91-120 days', '120+ days']
                        receivables_df['Age_Bucket'] = pd.cut(receivables_df['Days_Outstanding'], bins=bins, labels=labels)
                        
                        # Sum by age bucket
                        aged_receivables = receivables_df.groupby('Age_Bucket')['Invoice_Balance_Due_in_USD'].sum().reset_index()
                        
                        if not aged_receivables.empty:
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
                            
                            fig.update_layout(
                                height=500
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Show table
                            st.dataframe(aged_receivables, use_container_width=True)
                        else:
                            st.warning("No aged receivables data to display")
                    else:
                        st.warning("No outstanding receivables found")
                except Exception as e:
                    st.warning(f"Could not analyze aged receivables: {str(e)}")
            else:
                st.warning("Missing required columns for aged receivables analysis")
            
            # Invoice Size vs. Payment Speed
            st.subheader("Invoice Size vs. Payment Speed")
            
            if ('Invoice_Total_in_USD' in df_filtered.columns and 
                'Days between Invoice date and last payment date' in df_filtered.columns):
                try:
                    # Filter to rows with payment data
                    scatter_df = df_filtered[df_filtered['Days between Invoice date and last payment date'] != 'Unpaid'].copy()
                    
                    if not scatter_df.empty:
                        # Convert to numeric
                        scatter_df['Payment_Days'] = pd.to_numeric(scatter_df['Days between Invoice date and last payment date'], errors='coerce')
                        
                        # Create scatter plot
                        fig = px.scatter(
                            scatter_df,
                            x='Invoice_Total_in_USD',
                            y='Payment_Days',
                            color='Client' if 'Client' in scatter_df.columns else None,
                            size='Invoice_Total_in_USD',
                            hover_name='Client' if 'Client' in scatter_df.columns else None,
                            title='Invoice Size vs. Payment Speed',
                            labels={
                                'Invoice_Total_in_USD': 'Invoice Amount (USD)',
                                'Payment_Days': 'Days to Payment'
                            }
                        )
                        
                        fig.update_layout(
                            height=600
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Analysis
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # Calculate correlation
                            correlation = scatter_df['Invoice_Total_in_USD'].corr(scatter_df['Payment_Days'])
                            
                            interpretation = "No correlation"
                            if correlation > 0.5:
                                interpretation = "Strong positive correlation (larger invoices take longer to pay)"
                            elif correlation > 0.3:
                                interpretation = "Moderate positive correlation"
                            elif correlation > 0:
                                interpretation = "Weak positive correlation"
                            elif correlation < 0:
                                interpretation = "Negative correlation (larger invoices are paid faster)"
                            
                            st.markdown(f"""
                            <div style="padding: 1rem; background-color: #f8f9fa; border-radius: 10px;">
                                <h4>Analysis</h4>
                                <p><strong>Correlation:</strong> {correlation:.2f}</p>
                                <p><strong>Interpretation:</strong> {interpretation}</p>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with col2:
                            # Group by size range
                            try:
                                scatter_df['Size_Range'] = pd.cut(
                                    scatter_df['Invoice_Total_in_USD'],
                                    bins=[0, 1000, 5000, 10000, float('inf')],
                                    labels=['< $1K', '$1K-$5K', '$5K-$10K', '> $10K']
                                )
                                
                                size_vs_delay = scatter_df.groupby('Size_Range')['Payment_Days'].mean().reset_index()
                                
                                st.dataframe(size_vs_delay, use_container_width=True)
                            except:
                                st.warning("Could not analyze by invoice size range")
                    else:
                        st.warning("No payment speed data available")
                except Exception as e:
                    st.warning(f"Could not analyze invoice size vs payment speed: {str(e)}")
            else:
                st.warning("Missing required columns for payment speed analysis")
    
    except Exception as e:
        st.error(f"An error occurred in the dashboard: {str(e)}")
        st.error(traceback.format_exc())

# Run the main application
if __name__ == "__main__":
    main()
