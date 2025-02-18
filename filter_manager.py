import pandas as pd
import streamlit as st

import time
import json

from data_manager_snowflake import get_snowflake_session, execute_query_snowflake


@st.dialog("Potvrdit uložení filtru")
def save_filter_dialog_snowflake(filter_model, client):
    """
    Display a dialog to confirm and save a filter to Snowflake with the specified filter model.

    Parameters:
    - filter_model (dict): The filter model configuration to save.

    Saves the filter model to Snowflake after user confirmation. Allows the user 
    to input a filter name and displays a progress bar during the save process.
    Updates session state and reloads available filters after saving.
    """
    st.session_state['filter_name'] = st.text_input(label="Název filtru", value=st.session_state['filter_name'])
    st.session_state['show_filter_name_input'] = False
    if st.button('Potvrdit uložení filtru', use_container_width=True, type='primary'):
        if st.session_state['filter_name']:
            progress_bar = st.progress(0)
            save_success = save_current_filters_snowflake(
                st.session_state['user_email'], 
                st.session_state['filter_name'], 
                filter_model, 
                progress_bar, 
                client
            )
            if save_success:
                st.session_state['show_filter_name_input'] = False
                st.session_state['filter_name'] = ""
                st.rerun()
            else:
                st.warning("Filtr nebyl uložen kvůli chybě. Prosím zkuste to znovu nebo kontaktujte administrátora.")
        else:
            st.warning("Filtr nebyl uložen. Pro uložení zadejte název filtru")


def load_saved_filters_snowflake(user_email, client):
    """
    Load saved filters from Snowflake for a specific user.

    Parameters:
    - user_email (str): The email of the user whose filters to load.

    Returns:
    - tuple: A tuple containing a DataFrame of user-specific filters and a list of filter names.
    
    Retrieves saved filters from Snowflake filtered by the provided user email. 
    Returns empty results if an error occurs.
    """
    try:
        # Get the reusable Snowflake session
        session = get_snowflake_session(client)
        
        with st.spinner("Načítám uložené filtry..."):
            # Load filter table from Keboola
            table_id = st.secrets["WORKSPACE_FILTER_TABLE_ID"]
            filters_df = session.table(table_id).to_pandas()
            client.create_event(message='Streamlit App Snowflake Read Table', event_type='keboola_data_app_snowflake_read_table', event_data=f'table_id: {table_id}')
        
        # Filter only for the current user’s filters
        user_filters = filters_df[filters_df['FILTER_CREATOR'] == user_email]
        filter_names = user_filters['FILTER_NAME'].tolist()
    except:
        # Return empty results if any error occurs
        user_filters = pd.DataFrame()
        filter_names = []
    return user_filters, filter_names


def save_current_filters_snowflake(user_email, filter_name, current_filter_model, progress_bar=None, client=None):
    """
    Save the current filter model to Snowflake, including user and filter metadata.

    Parameters:
    - user_email (str): The email of the user saving the filter.
    - filter_name (str): The name for the saved filter.
    - current_filter_model (dict): JSON-serializable filter model.
    - progress_bar (st.progress, optional): Optional progress bar for user feedback.

    Side Effects:
    - Executes a Snowflake MERGE statement to update or insert the filter, then reloads 
      filters into session state. Displays progress updates if a progress bar is provided.
    """
    # Serialize the filter model to JSON format
    filter_model_json = json.dumps(current_filter_model)
    if progress_bar:
        progress_bar.progress(25)
    
    # Write the filter incrementally to the database using Snowpark
    try:
        # Target table name
        table_id = st.secrets["WORKSPACE_FILTER_TABLE_ID"]
        
        # Execute the MERGE statement to update or insert
        merge_query = f"""
            MERGE INTO {table_id} AS target
            USING (SELECT '{filter_name}' AS FILTER_NAME, '{user_email}' AS FILTER_CREATOR, '{filter_model_json}' AS FILTERED_VALUES) AS source
            ON target.FILTER_NAME = source.FILTER_NAME AND target.FILTER_CREATOR = source.FILTER_CREATOR
            WHEN MATCHED THEN UPDATE SET target.FILTERED_VALUES = source.FILTERED_VALUES
            WHEN NOT MATCHED THEN INSERT (FILTER_NAME, FILTER_CREATOR, FILTERED_VALUES)
            VALUES (source.FILTER_NAME, source.FILTER_CREATOR, source.FILTERED_VALUES)
        """
        execute_query_snowflake(merge_query, client)
        
        if progress_bar:
            progress_bar.progress(75)

    except Exception as e:
        # Handle error without breaking the app
        error_message = f"Ukládání filtru selhalo: {str(e)}"
        st.error(error_message)
        
        # Ensure progress bar is cleared to avoid UI locking
        if progress_bar:
            progress_bar.empty()
        
        # Safely return to allow app to continue running
        return False  # Indicates failure

    # Step 4: Complete the progress bar and reload filters
    if progress_bar:
        progress_bar.progress(100)
    st.success("Filtr úspěšně uložen.")
    time.sleep(2)

    # Reload filters after saving
    try:
        st.session_state['user_filters'], st.session_state['filter_names'] = load_saved_filters_snowflake(user_email, client)
    except Exception as reload_error:
        st.warning(f"Chyba při načítání uložených filtrů: {str(reload_error)}")
    
    return True  # Indicates success


def apply_filter(df, filter_model):
    """
    Apply a filter to the provided DataFrame based on the specified filter model.

    Parameters:
    - df (pd.DataFrame): The DataFrame to filter.
    - filter_model (dict): The filter model defining column filters and their criteria.

    Returns:
    - pd.DataFrame: A filtered DataFrame containing only rows matching the filter criteria.
    """
    # Iterate through each column in the filter model
    for filter_column, filter_details in filter_model.items():
        if filter_details['filterType'] == 'set':
            filter_values = filter_details['values']
            
            # Apply the filter for each column using the values in the filter model
            df = df[df[filter_column].isin(filter_values)]
    return df
