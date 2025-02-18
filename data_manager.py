import os

import streamlit as st
import pandas as pd

from datetime import datetime 
from io import BytesIO
from collections import defaultdict, deque

from data_manager_snowflake import save_changed_rows_snowflake


def build_manager_hierarchy(df):
    """Precompute the manager-to-reports relationships."""
    # Normalize email columns for consistent matching
    df['EMAIL_ADDRESS'] = df['EMAIL_ADDRESS'].str.lower().str.strip()
    df['DIRECT_MANAGER_EMAIL'] = df['DIRECT_MANAGER_EMAIL'].str.lower().str.strip()

    # Exclude rows where EMAIL_ADDRESS is '0'
    df = df[df['EMAIL_ADDRESS'] != '0']
    
    # Create a mapping of manager to their direct reports
    manager_to_reports = defaultdict(list)
    for manager_email, employee_email in zip(df['DIRECT_MANAGER_EMAIL'], df['EMAIL_ADDRESS']):
        manager_to_reports[manager_email].append(employee_email)

    return manager_to_reports

def get_all_reports(df, manager_email):
    """Efficiently get all direct and indirect reports for a manager."""
    # Precompute the manager-to-reports hierarchy
    manager_to_reports = build_manager_hierarchy(df)

    # Initialize BFS traversal
    manager_email = manager_email.lower().strip()
    all_reports = set()
    queue = deque([manager_email])

    while queue:
        current_manager = queue.popleft()

        # If this manager was already processed, skip
        if current_manager in all_reports:
            continue

        # Mark the manager as processed
        all_reports.add(current_manager)

        # Add direct reports to the queue if they exist
        direct_reports = set(manager_to_reports.get(current_manager, []))
        queue.extend(direct_reports)

        
    # Remove the manager's own email from the results
    all_reports.discard(manager_email)

    return all_reports

def filter_data_by_role(df, user_role, user_email):
    """Filter data based on user role."""
    if user_role == 'MA':
        # Get all direct and indirect reports
        all_reports = get_all_reports(df, user_email)

        # Filter the DataFrame based on collected emails
        df_filtered = df[df['EMAIL_ADDRESS'].isin(all_reports)]

        if df_filtered.empty:
            st.warning("V hierarchii manažera nebyli nalezeni žádní zaměstnanci.")
            st.stop()
    else:
        df_filtered = df

    return df_filtered


def merge_changed_rows(new_changes):
    """Merge new changes into the existing session_state['changed_rows'] without duplicates."""
    pk_columns = ['USER_ID', 'YEAR', 'EVALUATION']

    if st.session_state['changed_rows'].empty:
        st.session_state['changed_rows'] = new_changes.copy()
    else:
        # Set PK as the index for both DataFrames
        st.session_state['changed_rows'].set_index(pk_columns, inplace=True)
        new_changes.set_index(pk_columns, inplace=True)

        # Update the existing rows with the new changes
        st.session_state['changed_rows'].update(new_changes)

        # Append any new rows that were not present in the existing DataFrame
        st.session_state['changed_rows'] = st.session_state['changed_rows'].combine_first(new_changes)

        # Reset index for further use
        st.session_state['changed_rows'].reset_index(inplace=True)
        new_changes.reset_index(inplace=True)


def mask_dataframe_for_1on1(df, selected_name):
    """Mask the DataFrame for 1-on-1 meetings by replacing other names with '*'."""
    masked_df = df.copy()
    masked_df.loc[masked_df['FULL_NAME'] != selected_name, 'FULL_NAME'] = '*'
    return masked_df


@st.dialog("Stáhnout CSV")
def generate_csv_file_dialog(data):
    df_to_download = pd.DataFrame(data)
    csv_buffer = BytesIO()
    df_to_download.to_csv(csv_buffer, index=False, encoding='utf-8')
    csv_buffer.seek(0)
    st.download_button(label="Stáhnout", data=csv_buffer, file_name='data_ks.csv', mime='text/csv', use_container_width=True, type='primary')


@st.dialog("Potvrdit uzamčení záznamů")
def lock_filtered_rows_dialog(df_orig, client):
        st.error("""Kliknutím na Ano uzamknete hodnocení všech aktuálně vyfiltrovaných záznamů. Manažer nebude mít
                po uzamčení možnost editace. Business Partner bude mít možnost editovat po dobu 30 dní od uzamčení.""")
        ano_col, ne_col = st.columns(2)
        with ano_col:
            if st.button("Ano", use_container_width=True, type='primary'):
                if not st.session_state['rows_to_lock'].empty:
                    locked_rows = st.session_state['rows_to_lock'][['USER_ID', 'YEAR', 'EVALUATION']].copy()
                    locked_rows['IS_LOCKED'] = 1 
                    locked_rows[['USER_ID', 'YEAR', 'EVALUATION','IS_LOCKED']] = locked_rows[['USER_ID', 'YEAR', 'EVALUATION','IS_LOCKED']].astype(int)
                    progress_text = "**Odesílám data do databáze...**"
                    progress = st.progress(0, text=progress_text)
                    save_changed_rows_snowflake(df_orig, locked_rows, False, client, progress)
                    st.session_state['rows_to_lock'] = pd.DataFrame()
                    progress.progress(100)
                    st.session_state['grid_key_filter'] +=  f"_locked_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
                    st.rerun()
                else:
                    st.warning("Nebyly vybrány žádné záznamy k uzamčení.")
        with ne_col:
            if st.button("Ne", use_container_width=True):
                st.info("Záznamy nebyly uzamknuty.")
                st.session_state['rows_to_lock'] = pd.DataFrame()
                st.rerun()
                