import json
import time
import os 

import pandas as pd
import streamlit as st

from datetime import datetime

# Set page configuration for wide layout
st.set_page_config(layout="wide")

# Local application imports
from ui import display_header
from chart_manager import display_charts, preprocess_df_for_charts
from data_manager import (
    filter_data_by_role,
    generate_csv_file_dialog,
    mask_dataframe_for_1on1,
    merge_changed_rows,
    lock_filtered_rows_dialog
)
from data_manager_snowflake import (
    read_data_snowflake,
    save_changed_rows_snowflake,
        
)
from filter_manager import (
    apply_filter,
    load_saved_filters_snowflake,
    save_filter_dialog_snowflake

)
from grid_manager import display_table, setup_aggrid
from keboola_streamlit import KeboolaStreamlit


# Initialize Keboola integration client
keboola=KeboolaStreamlit(st.secrets["kbc_url"], st.secrets["kbc_token"])
license_key=keboola.aggrid_license_key

# Set debug mode based on secrets configuration
debug = st.secrets['DEBUG'] == 'true'

# Header setup (only retrieved if debug is off)
headers = keboola._get_headers() if not debug else {}


def initialize_session_state():
    """
    Initialize default session state variables used across the app.
    
    Sets up key session state variables like dataframes, user role and email, editable columns, 
    display options, and flags for UI behavior. Ensures these variables have default values 
    at the start of the app to prevent key errors during runtime.
    """
    state_defaults = {
        'df': pd.DataFrame(),
        'df_original': pd.DataFrame(),
        'user_role': None,
        'user_email': None,
        'editable_columns': [],
        'columns_to_display': [],
        'grid_options': None,
        'filtered_df': pd.DataFrame(),
        'changed_rows': pd.DataFrame(),
        'chart_year': None,
        'chart_title': None,
        'rows_to_lock': pd.DataFrame(),
        'filter_name': None,
        'df_last_saved': pd.DataFrame(),
        'unsaved_warning_displayed': False,
        'user_filters': None,
        'filter_names': None,
        'snowflake_session': None,
        'toggle': 'Ne',
        'active_tab' : 'tab1',
        'grid_key_filter': ''
    }
    for key, default in state_defaults.items():
        st.session_state.setdefault(key, default)


def process_and_save_changes(df, changed_rows, debug):
    """
    Confirm and save any changes made to the dataframe, displaying a confirmation dialog and progress bar.
    
    Parameters:
        df (pd.DataFrame): The current dataframe with original data.
        changed_rows (pd.DataFrame): Rows that have been modified and need saving.
        debug (bool): Debug mode flag for enhanced logging.
    """
    if st.session_state['changed_rows'].empty:
        st.warning('Nebyly provedeny žádné změny k uložení')
    else:
        try:
            progress_text = "**Odesílám data do databáze...**"
            progress = st.progress(0, text=progress_text)
            changed_rows.reset_index(drop=True, inplace=True)
            progress.progress(20, text=progress_text)

            # Flatten MultiIndex columns if present
            if isinstance(changed_rows.columns, pd.MultiIndex):
                changed_rows_flattened = changed_rows.xs('self', axis=1, level=1)
                changed_rows = pd.concat([changed_rows[['USER_ID', 'YEAR', 'EVALUATION']], changed_rows_flattened], axis=1)
                changed_rows.columns = ['USER_ID', 'YEAR', 'EVALUATION'] + list(changed_rows_flattened.columns)

            pk_columns = ['USER_ID', 'YEAR', 'EVALUATION']
            progress.progress(40, text=progress_text)

            # Ensure primary key columns are set correctly
            if all(col in changed_rows.columns for col in pk_columns):
                changed_rows.dropna(subset=pk_columns, inplace=True)
                changed_rows[pk_columns] = changed_rows[pk_columns].astype(int)

                df_orig = df.copy()
                save_changed_rows_snowflake(df_orig, changed_rows, debug, keboola, progress)
            
            progress.progress(80, text="**Uloženo. Proběhne obnova aplikace...**")
            time.sleep(1)
            progress.progress(100)
            time.sleep(1)

        except Exception as e:
            st.error('Ukládání dat selhalo. Kontaktujte prosím administrátora:'+str(e))
            st.stop()
        st.rerun()


def filter_dataframe(filter_model, selected_year, toggle):
    # Start with the base filtered data for the role
    filtered = filter_data_by_role(st.session_state['df'], st.session_state['user_role'], st.session_state['user_email'])

    # Apply year filter
    filtered = filtered[filtered['YEAR_EVALUATION'] == selected_year]

    if filter_model:
        filtered = apply_filter(filtered, filter_model)

    # Apply toggle filter for MA role
    if st.session_state['user_role'] == 'MA' and toggle == "Ano":
        filtered = filtered[filtered['DIRECT_MANAGER_EMAIL'] == st.session_state['user_email']]
    
    return filtered


def main():
    """
    Primary function to set up and run the Streamlit app.
    
    Initializes the user environment, role-based options, and UI components based on user role. 
    Loads data based on debug mode, sets up role-based filtering and displays, and 
    defines functionality for editing, filtering, and visualizing data. Also manages 
    condition-based display options and caching behavior.
    """
    initialize_session_state()

    # Load data based on debug mode and assign roles
    try:
        role_mapping = {
            st.secrets["ROLE_BP_ID"]: "BP", st.secrets["ROLE_LC_ID"]: "LC",
            st.secrets["ROLE_MA_ID"]: "MA", st.secrets["ROLE_DEV_ID"]: "DEV",
            st.secrets["ROLE_TEST_ID"]: "TEST"
        }
        user_role_ids = headers["X-Kbc-User-Roles"].split(",") 
        matched_role = next((role_mapping.get(role_id, "UNKNOWN") for role_id in user_role_ids if role_id in role_mapping), "UNKNOWN")
        st.session_state['user_role'] = matched_role
        if st.session_state['user_email'] is None:
            st.session_state['user_email'] = headers["X-Kbc-User-Email"].lower()
        if matched_role=='UNKNOWN':
            unknown_roles = headers["X-Kbc-User-Roles"]
            warning_text = f'Nepodařilo se rozpoznat roli. Kontaktujte administrátora: {unknown_roles}'
            st.warning(warning_text)
            st.stop()
    except KeyError:
        # Line for DEV
        st.session_state['user_role'] = 'DEV'
        #st.error("Nepodařilo se rozpoznat roli uživatele. Kontaktujte administrátora.")
        #st.stop()
    
    if st.session_state['df'].empty:
        with st.spinner("Načítám data..."):
            read_data_snowflake(st.secrets["WORKSPACE_SOURCE_TABLE_ID"], keboola)

    if st.session_state['user_role'] in ['DEV', 'TEST']:
        def on_user_email_change():
            """Callback to reload filters when user_email changes."""
            st.session_state['user_email'] = st.session_state['user_email'].lower()
            st.session_state['user_filters'], st.session_state['filter_names'] = load_saved_filters_snowflake(st.session_state['user_email'], keboola)

        roles = ['LC', 'BP', 'MA', 'DEV', 'TEST']
        st.sidebar.title("DEV/TEST roles options:")
        st.sidebar.text_input(
                'Enter user email',
                key='user_email',  # Ensure it's tied to the session state
                on_change=on_user_email_change  # Trigger the callback when changed
            )
        st.session_state['user_role'] = st.sidebar.selectbox("Role", options=roles)
    
    # Load saved filters
    if st.session_state['user_filters'] is None or st.session_state['filter_names'] is None:
        st.session_state['user_filters'], st.session_state['filter_names'] = load_saved_filters_snowflake(st.session_state['user_email'], keboola)      
    
    # Display header and logged user
    logged_user_text = f"Uživatel: {st.session_state['user_email']}"
    display_header(text=logged_user_text)

    # Define tabs based on the user role
    tab1, tab2, tab3 = st.tabs(['Editace', 'Vizualizace', 'O aplikaci'])

    with tab1:
        if st.session_state["active_tab"] != "tab1":
            st.session_state["active_tab"] = "tab1"
        
        # Filters
        if st.session_state['user_role'] == 'MA':
            filter_col1, filter_col2, filter_col3 = st.columns([0.5,0.4,0.1])
        else:
            filter_col1, filter_col2 = st.columns([0.5,0.5])

        with filter_col1:
            selected_filter_name = st.selectbox("Použít uložený filtr", [''] + st.session_state['filter_names'],
                                                disabled=st.session_state['unsaved_warning_displayed'],
                                                help="Globální filtr je možné měnit, pokud nejsou neuložené změny.")
            if selected_filter_name:
                selected_filter_row = st.session_state['user_filters'][st.session_state['user_filters']['FILTER_NAME'] == selected_filter_name].iloc[0]
                st.session_state['grid_key_filter'] = selected_filter_row['FILTER_NAME']
                filter_model = json.loads(selected_filter_row['FILTERED_VALUES'])
            else:
                filter_model = None
    
        with filter_col2:
            unique_years = sorted(st.session_state['df']['YEAR_EVALUATION'].unique(), reverse=True)
            default_year = unique_years[0] if unique_years else None
            selected_year = st.selectbox("Kolo hodnocení", 
                                         key="selected_year",
                                         options=unique_years, 
                                         index=0 if default_year else None,
                                         disabled=st.session_state['unsaved_warning_displayed'],
                                         help="Globální filtr je možné měnit, pokud nejsou neuložené změny.")
    
        if st.session_state['user_role'] == 'MA':
            with filter_col3:
                toggle = st.select_slider(
                    "Pouze můj tým",
                    options=["Ne", "Ano"],  # Text options instead of numbers
                    value="Ano",  # Default value
                    disabled=st.session_state['unsaved_warning_displayed'],
                    help="Globální filtr je možné měnit, pokud nejsou neuložené změny."
                )
                st.session_state['toggle'] = toggle
                specific_value = "_team_view"
                if st.session_state['toggle'] == 'Ano':
                    if specific_value not in st.session_state['grid_key_filter']:
                        st.session_state['grid_key_filter'] += specific_value
                elif st.session_state['toggle'] == 'Ne':
                    if specific_value in st.session_state['grid_key_filter']:
                        st.session_state['grid_key_filter'] = st.session_state['grid_key_filter'].replace(specific_value,'')

        # Filter the dataframe to be displayed based on selected filters and conditions 
        st.session_state['filtered_df'] = filter_dataframe(filter_model, selected_year, st.session_state['toggle'])

        # Set up and display AgGrid table
        st.session_state['columns_to_display'] = ['FULL_NAME', 'JOB_TITLE_CZ', 'LOGIN','L2_ORGANIZATION_UNIT_NAME_CZ', 'L3_ORGANIZATION_UNIT_NAME_CZ', 
                                                  'L4_ORGANIZATION_UNIT_NAME_CZ', 'TEAM_CODE', 'L2_HEAD_OF_UNIT_FULL_NAME', 'L3_HEAD_OF_UNIT_FULL_NAME',
                                                  'L4_HEAD_OF_UNIT_FULL_NAME', 'MES_DPP_STATUS', 'DIRECT_MANAGER_FULL_NAME', 'LAST_EVALUATION', 'VYKON_PREVIOUS',
                                                  'HODNOTY_PREVIOUS', 'POTENCIAL_PREVIOUS', 'VYKON_SYSTEM', 'HODNOTY_SYSTEM', 'IS_LOCKED']
        
        st.session_state['editable_columns'] = ['VYKON', 'HODNOTY', 'POTENCIAL', 'MOZNY_KARIERNI_POSUN', 'PRAVDEPODOBNOST_ODCHODU', 'NASTUPCE', 'POZNAMKY']

        df_for_grid = st.session_state['filtered_df'].copy()
        st.session_state['grid_options'] = setup_aggrid(df_for_grid, 
                                                        st.session_state['editable_columns'], 
                                                        st.session_state['columns_to_display'],
                                                        st.session_state['user_role'], 
                                                        st.session_state['user_email'])
        if not df_for_grid.empty:
            df_grid, new_changes, grid_response = display_table(df_for_grid, st.session_state['grid_options'], st.session_state['grid_key_filter'], license_key=license_key)
        else:
            st.warning("Pro vybrané filtry a období nebyla nalezena žádná data.")
            st.stop()

        if 'data' in grid_response and not grid_response['data'].empty:
            st.session_state['filtered_df'] = df_grid.copy()

        grid_state = grid_response.grid_state
        current_filter_model = grid_state['filter']['filterModel'] if grid_state and 'filter' in grid_state and 'filterModel' in grid_state['filter'] else {}
        merge_changed_rows(new_changes)

        # Display warning if unsaved changes exist
        if not st.session_state['changed_rows'].empty:
            st.session_state['unsaved_warning_displayed'] = True
        else:
            st.session_state['unsaved_warning_displayed'] = False

        if st.session_state['unsaved_warning_displayed']:
            st.error("⚠️ Máte neuložené změny. Nezapomeňte je uložit před opuštěním aplikace")

        # Display buttons based on user_role
        if st.session_state['user_role'] in ['BP','DEV','TEST']:
            # Define 4 equally wide columns for button layout, with conditional display for each role
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                if st.button("🔎 Uložit aktuální filtry", use_container_width=True, help='Kliknutím uložíte aktuálně nastavené filtry'):
                    save_filter_dialog_snowflake(current_filter_model, keboola)

            with col2:
                if st.button("📥 Vygenerovat CSV", use_container_width=True, help='Kliknutím vygenerujete CSV soubor ke stažení'):
                    generate_csv_file_dialog(grid_response['data'])

            with col3:
                if st.button("💾 Potvrdit uložení změn", use_container_width=True, type='primary', help='Kliknutím potvrdíte uložení provedených změn, změny budou uloženy do databáze'):
                    process_and_save_changes(st.session_state['df'], st.session_state['changed_rows'], debug)

            with col4:
                if st.button("🔒 Uzamknout hodnocení", use_container_width=True, help='Kliknutím uzamknete hodnocení všech aktuálně vyfiltrovaných záznamů'):
                    if not st.session_state['filtered_df'].empty:
                        st.session_state['rows_to_lock'] = st.session_state['filtered_df'].copy()
                        lock_filtered_rows_dialog(st.session_state['df'], keboola)  
                    else:
                        st.warning("Nebyly vybrány žádné záznamy k uzamčení.")
                
        # Handle 'MA' role
        if st.session_state['user_role'] in ['MA']:
            ma_col1, ma_col2, ma_col3 = st.columns([0.2, 0.2, 0.4])
            with ma_col1:
                if st.button("🔎 Uložit aktuální filtry", use_container_width=True, help='Kliknutím uložíte aktuálně nastavené filtry'):
                    save_filter_dialog_snowflake(current_filter_model, keboola)
            
            with ma_col2:
                if st.button("📥 Vygenerovat CSV", use_container_width=True, help='Kliknutím vygenerujete CSV soubor ke stažení'):
                    generate_csv_file_dialog(grid_response['data'])

            with ma_col3:
                if st.button("💾 Potvrdit uložení změn", use_container_width=True, type='primary', help='Kliknutím potvrdíte uložení provedených změn, změny budou uloženy do databáze'):
                    process_and_save_changes(st.session_state['df'], st.session_state['changed_rows'], debug)

        if st.session_state['user_role'] == 'LC':
            lc_col1, lc_col2 = st.columns(2)
            with lc_col1:
                if st.button("🔎 Uložit aktuální filtry", use_container_width=True, help='Kliknutím uložíte aktuálně nastavené filtry'):
                    save_filter_dialog_snowflake(current_filter_model, keboola)
            
            with lc_col2:
                if st.button("📥 Vygenerovat CSV", use_container_width=True, help='Kliknutím vygenerujete CSV soubor ke stažení'):
                    generate_csv_file_dialog(grid_response['data'])
        
        # Visualization tab
        with tab2:
            if st.session_state["active_tab"] != "tab2":
                st.session_state["active_tab"] = "tab2"
            
            if st.session_state['active_tab'] == 'tab2':
                if st.session_state['user_role'] == 'MA':
                    full_names = ["Zobraz všechny"] + list(st.session_state['filtered_df']['FULL_NAME'].unique())
                    selected_name = st.selectbox("Schůzka 1-on-1:", full_names)
                    masked_df = st.session_state['filtered_df'] if selected_name == "Zobraz všechny" else mask_dataframe_for_1on1(st.session_state['filtered_df'], selected_name)
                    with st.spinner("Načítám vizualizace..."):
                        masked_df_charts = preprocess_df_for_charts(masked_df)
                        display_charts(st.session_state['df'], masked_df_charts, license_key)
                else:
                    with st.spinner("Načítám vizualizace..."):
                        df_filtered_charts = preprocess_df_for_charts(st.session_state['filtered_df'])
                        display_charts(st.session_state['df'], df_filtered_charts, license_key)
        
        # Manual tab
        with tab3:
            if st.session_state["active_tab"] != "tab3":
                st.session_state["active_tab"] = "tab3"

            # CSS for the grey rounded box
            st.markdown("""
            <style>
            .info-box {
                background-color: #f9f9f9; /* Light grey background */
                border: 1px solid #ddd;    /* Light border */
                border-radius: 10px;       /* Rounded corners */
                padding: 20px;             /* Padding inside the box */
                margin-top: 10px;          /* Space above the box */
                font-family: Arial, sans-serif; /* Clean font */
                color: #333;               /* Text color */
            }
            .info-box h2 {
                color: #444; /* Slightly darker color for headers */
            }
            .info-box a {
                color: #0073e6; /* Link color */
                text-decoration: none;
            }
            .info-box a:hover {
                text-decoration: underline; /* Underline link on hover */
            }
            </style>
            """, unsafe_allow_html=True)

            # Content inside the grey rounded box
            confluence_url = "https://cnfl.csin.cz/pages/viewpage.action?pageId=1509163068"
            st.markdown(f"""
            <div class="info-box">
                <p>
                Aplikace poskytuje rozhraní pro správu hodnocení zaměstnanců v rámci procesu Kulaté stoly.
                Využijte její funkce pro filtrování a editaci dat a ukládání provedených změn, 
                rovněž pak dostupné vizualizace hodnocených skupin zaměstnanců.
                </p>
                <h3>Potřebujete více informací?</h3>
                <p>
                Podrobné instrukce a průvodce naleznete v 
                <a href="{confluence_url}" target="_blank">plném manuálu na Confluence</a>.
                </p>
            </div>
            """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
