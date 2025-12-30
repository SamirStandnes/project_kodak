import streamlit as st
import pandas as pd
import os
import sqlite3
import sys

# Ensure project root is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

from scripts.analysis.generate_summary_report import generate_summary_report

@st.cache_data(ttl=300)
def load_summary_data():
    df, summary, unpriced = generate_summary_report(verbose=False)
    return df, summary, unpriced

@st.cache_data(ttl=60)
def check_staging_status():
    db_file = os.path.join(project_root, 'database', 'portfolio.db')
    conn = sqlite3.connect(db_file)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM transactions_staging")
        count = cursor.fetchone()[0]
    except sqlite3.OperationalError:
        count = 0
    conn.close()
    return count

def render_sidebar():
    """Renders the common sidebar status and freshness info."""
    with st.sidebar:
        st.header("📊 System Status")
        
        # We need data to show status, so we load it here.
        # Since it's cached, it won't be slow on subsequent reloads/page changes
        try:
            _, summary_data, unpriced_securities = load_summary_data()
            staging_count = check_staging_status()
            
            if staging_count > 0:
                st.warning(f"**Staging:** {staging_count} pending review")
            else:
                st.success("**Staging:** Clean")

            if unpriced_securities:
                st.error(f"**Pricing:** {len(unpriced_securities)} missing prices")
                with st.expander("View Unpriced"):
                    for item in unpriced_securities:
                        st.write(f"- {item}")
            else:
                st.success("**Pricing:** All updated")

            st.markdown("---")
            st.subheader("🕒 Data Freshness")
            if summary_data.get('last_trade_dates_by_source'):
                # Create a small dataframe for a cleaner sidebar table
                freshness_df = pd.DataFrame([
                    {"Source": k, "Last Trade": v} 
                    for k, v in summary_data['last_trade_dates_by_source'].items()
                ])
                st.table(freshness_df.set_index("Source"))
                
        except Exception as e:
            st.error(f"Error loading sidebar status: {e}")
