import json
import os
import uuid

import streamlit as st
import pandas as pd

from datetime import datetime
from snowflake.snowpark import Session


def get_snowflake_session(client):
    """Create and return a Snowflake session using Snowpark."""
    if st.session_state['snowflake_session'] is None:
        # Set up Snowflake connection parameters from st.secrets
        try:
            snowflake_config = {
                "account": st.secrets["SNOWFLAKE_ACCOUNT"],
                "user": st.secrets["SNOWFLAKE_USER"],
                "password": st.secrets["SNOWFLAKE_PASSWORD"],
                "warehouse": st.secrets["SNOWFLAKE_WAREHOUSE"],
                "database": st.secrets["SNOWFLAKE_DB"],
                "schema": st.secrets["SNOWFLAKE_SCHEMA"]
            }

            # Create and store the session in session state
            st.session_state["snowflake_session"] = Session.builder.configs(snowflake_config).create()
            client.create_event(message='Streamlit App Snowflake Init Connection', event_type='keboola_data_app_snowflake_init')
        except Exception as e:
            st.error(f"Error creating Snowflake session: {e}")
            return None

        return st.session_state["snowflake_session"]
    # Return the existing session if already created
    return st.session_state["snowflake_session"]


def read_data_snowflake(table_id, client):
    """Read data from Snowflake table into a Pandas DataFrame using Snowpark."""
    try:
        # Get the reusable Snowflake session
        session = get_snowflake_session(client)

        # Check if session is None
        if session is None:
            st.error("Snowflake session could not be created.")
            return
            
        # Load data from Snowflake table into a Pandas DataFrame
        columns = ['USER_ID', 'YEAR', 'EVALUATION', 'LOGIN', 'EMAIL_ADDRESS', 'DIRECT_MANAGER_EMAIL', 'FULL_NAME', 'JOB_TITLE_CZ', 'DIRECT_MANAGER_FULL_NAME', 'LAST_EVALUATION', 
                   'VYKON_PREVIOUS', 'HODNOTY_PREVIOUS', 'POTENCIAL_PREVIOUS', 'VYKON_SYSTEM', 'HODNOTY_SYSTEM', 'IS_LOCKED', 
                   'VYKON', 'HODNOTY', 'POTENCIAL', 'PRAVDEPODOBNOST_ODCHODU', 'NASTUPCE', 'MOZNY_KARIERNI_POSUN', 'POZNAMKY', 'LOCKED_TIMESTAMP', 
                   'HIST_DATA_MODIFIED_WHEN', 'HIST_DATA_MODIFIED_BY', 'JOB_ENTRY_DATE', 'TM_DATE', 'L2_ORGANIZATION_UNIT_NAME_CZ',
                   'L3_ORGANIZATION_UNIT_NAME_CZ', 'L4_ORGANIZATION_UNIT_NAME_CZ', 'TEAM_CODE', 'L2_HEAD_OF_UNIT_FULL_NAME', 'L3_HEAD_OF_UNIT_FULL_NAME',
                   'L4_HEAD_OF_UNIT_FULL_NAME', 'MES_DPP_STATUS']
        
        df_snowflake = session.table(table_id).select(columns).to_pandas()
        client.create_event(message='Streamlit App Snowflake Read Table', event_type='keboola_data_app_snowflake_read_table', event_data=f'table_id: {table_id}')

        # Add the YEAR_EVALUATION
        df_snowflake['YEAR_EVALUATION'] = df_snowflake.apply(
            lambda row: f"{row['YEAR']}-{int(float(row['EVALUATION']))}" 
                        if pd.notnull(row['EVALUATION']) else f"{row['YEAR']}-NA",
            axis=1
        )
        df_snowflake['DIRECT_MANAGER_EMAIL'] = df_snowflake['DIRECT_MANAGER_EMAIL'].str.lower()
        df_snowflake['EMAIL_ADDRESS'] = df_snowflake['EMAIL_ADDRESS'].str.lower()
        # Store in session state
        st.session_state['df'] = df_snowflake

    except Exception as e:
        st.error(f"Failed to load data from Snowflake: {e}")
        st.stop()


def execute_query_snowflake(query: str, client = None):
    # Step 3: Write the filter incrementally to the database using Snowpark
    try:
        # Get Snowflake session
        session = get_snowflake_session(client)
        session.sql(query).collect()
        client.create_event(message='Streamlit App Snowflake Query', event_type='keboola_data_app_snowflake_query', event_data=f'Query: {query}')
    except Exception as e:
        st.error(f"Failed to execute a query: {e}")


def write_data_snowflake(df: pd.DataFrame, table_name: str, auto_create_table: bool = False, overwrite: bool = False, client = None) -> None:
    try:
        # Get Snowflake session
        session = get_snowflake_session(client)
        session.write_pandas(df=df, table_name=table_name, auto_create_table=auto_create_table, overwrite=overwrite).collect()
        client.create_event(message='Streamlit App Snowflake Write Table', event_type='keboola_data_app_snowflake_write_table', event_data=f'table_id: {table_name}')
    except Exception as e:
        st.error(f"Failed to execute a query: {e}")


def map_json_to_snowflake_type(json_type):
    if json_type == "str":
        return "VARCHAR(16777216)"
    elif json_type == "int":
        return "NUMBER(38,0)"
    elif json_type == "datetime64[ns]":
        return "TIMESTAMP_NTZ(9)"
    else:
        raise ValueError(f"Unsupported JSON type: {json_type}")


def save_changed_rows_snowflake(df_original, changed_rows, debug, client, progress):
    """Save only the changed rows with new values to a CSV file or Snowflake."""
     
    # Step 1: Standardize Primary Key Column Data Types
    pk_columns = ['USER_ID', 'YEAR', 'EVALUATION']
    for col in pk_columns:
        df_original[col] = df_original[col].astype(str if col == 'USER_ID' else 'int32')
        changed_rows[col] = changed_rows[col].astype(str if col == 'USER_ID' else 'int32')
    
    # Log who and when is changing the values
    changed_rows['HIST_DATA_MODIFIED_BY'] = st.session_state['user_email']
    changed_rows['HIST_DATA_MODIFIED_WHEN'] = datetime.now()
    
    # Step 2: Ensure Timestamp Columns Are Converted to String Format
    timestamp_columns = ['LOCKED_TIMESTAMP', 'HIST_DATA_MODIFIED_WHEN', 'JOB_ENTRY_DATE', 'TM_DATE']
    default_timestamp = "1970-01-01 00:00:00.000"
    
    for timestamp_col in timestamp_columns:
        if timestamp_col in changed_rows.columns:
            changed_rows[timestamp_col] = changed_rows[timestamp_col].fillna(default_timestamp).astype(str)
        if timestamp_col in df_original.columns:
            df_original[timestamp_col] = df_original[timestamp_col].fillna(default_timestamp).astype(str)

    # Step 3: Merge DataFrames and Fill NaNs
    # Merge changed_rows with df_original on PK columns
    merged_df = pd.merge(
        changed_rows,
        df_original,
        on=pk_columns,
        how='left',
        suffixes=('', '_orig')
    )
    #'VYKON_SYSTEM', 'HODNOTY_SYSTEM'
    columns_to_update = ['HODNOTY', 'VYKON', 'POTENCIAL', 'POZNAMKY', 'NASTUPCE', 'PRAVDEPODOBNOST_ODCHODU', 
                         'IS_LOCKED', 'MOZNY_KARIERNI_POSUN', 'LOCKED_TIMESTAMP', 'HIST_DATA_MODIFIED_BY', 
                         'HIST_DATA_MODIFIED_WHEN']

    # For each column, fill NaNs in changed_rows with values from df_original
    for col in columns_to_update:
        if col in merged_df.columns and col + '_orig' in merged_df.columns:
            merged_df[col] = merged_df[col].fillna(merged_df[col + '_orig'])
    
    # Drop the original columns with '_orig' suffix
    cols_to_drop = [col for col in merged_df.columns if col.endswith('_orig')]
    merged_df.drop(columns=cols_to_drop, inplace=True)

    # Now, merged_df contains the updated rows with NaNs filled
    df_updated = merged_df.copy()

    # Step 4: Ensure Numeric Columns Are Properly Formatted
    for col in ['IS_LOCKED', 'HODNOTY', 'VYKON']: #'VYKON_SYSTEM', 'HODNOTY_SYSTEM'
        if col in df_updated.columns:
            df_updated[col] = pd.to_numeric(df_updated[col], errors='coerce').fillna(0).astype(int)

    # Step 5: Apply Conditional Logic to Update LOCKED_TIMESTAMP
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # Format with milliseconds
    df_updated.loc[(df_updated['IS_LOCKED'] == 1) & 
                   ((df_updated['LOCKED_TIMESTAMP'] == '') | 
                    (df_updated['LOCKED_TIMESTAMP'] == "1970-01-01 00:00:00") | 
                    (df_updated['LOCKED_TIMESTAMP'] == "1970-01-01 00:00:00.000000") |
                    (df_updated['LOCKED_TIMESTAMP'] == default_timestamp)), 
                   'LOCKED_TIMESTAMP'] = current_time
    
    # Step 6: Align with Expected Schema and Convert Datetimes to Strings
    file_path = os.path.join(os.path.dirname(__file__), './static/expected_schema.json')
    with open(file_path, 'r', encoding='utf-8') as file: 
        expected_schema = json.load(file)  
    
    for col, dtype in expected_schema.items():
        if col not in df_updated.columns:
            df_updated[col] = default_timestamp if 'datetime' in dtype else ('' if dtype == 'str' else 0)
        else:
            if dtype == 'str':
                df_updated[col] = df_updated[col].astype(str)
            elif 'int' in dtype:
                df_updated[col] = pd.to_numeric(df_updated[col], errors='coerce').fillna(0).astype('int')
            elif 'datetime' in dtype:
                df_updated[col] = pd.to_datetime(df_updated[col], errors='coerce').fillna(default_timestamp).astype(str)

    df_updated = df_updated.drop(columns=['YEAR_EVALUATION'])
    
    # Step 7: Save Data
    if debug:
        file_path = os.path.join(os.path.dirname(__file__), 'data', 'in', 'tables', 'anonymized_data.csv')
        df_anonymized = pd.read_csv(file_path)
        df_anonymized.set_index(pk_columns, inplace=True)
        df_updated.set_index(pk_columns, inplace=True)
        df_anonymized.update(df_updated)
        df_anonymized.reset_index(inplace=True)
        df_anonymized.to_csv(file_path, index=False)
    else:
        table_name = st.secrets["WORKSPACE_SOURCE_TABLE_ID"]
        temp_table_name = f"TEMP_STAGING_{st.session_state['user_email'].replace('@', '_').replace('.', '_')}_{uuid.uuid4().hex}"
        
        create_temp_table_sql = f"CREATE OR REPLACE TRANSIENT TABLE \"{temp_table_name}\" (\n"
        columns = [f'"{col}" {map_json_to_snowflake_type(dtype)}' for col, dtype in expected_schema.items()]
        create_temp_table_sql += ",\n".join(columns) + "\n);"
        
        progress.progress(50, text="**Probíhá zápis změn...**")
        execute_query_snowflake(create_temp_table_sql, client=client)
        write_data_snowflake(df_updated, temp_table_name, auto_create_table=False, overwrite=False, client=client)

        update_sql = f"""
            UPDATE "{table_name}" AS target
            SET { ', '.join([f'target."{col}" = source."{col}"' for col in columns_to_update]) }
            FROM "{temp_table_name}" AS source
            WHERE { ' AND '.join([f'target."{col}" = source."{col}"' for col in pk_columns]) };
        """
        drop_temp_table_sql = f'DROP TABLE IF EXISTS "{temp_table_name}";'
        progress.progress(60, text="**Ukládám...**")
        execute_query_snowflake(update_sql, client=client)
        execute_query_snowflake(drop_temp_table_sql, client=client)

    # Clear tracked changes
    st.session_state['changed_rows'] = pd.DataFrame()
    st.session_state['unsaved_warning_displayed'] = False
    
    read_data_snowflake(st.secrets["WORKSPACE_SOURCE_TABLE_ID"], client)

    pk_columns = ['USER_ID', 'YEAR', 'EVALUATION']
    st.session_state['df_original'] = st.session_state['df'].set_index(pk_columns).copy()
    st.session_state['df_last_saved'] = st.session_state['df_original'].copy()
    
    st.success("Změny uloženy, aplikace bude obnovena.")
    return df_updated


