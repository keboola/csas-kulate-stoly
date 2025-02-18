import streamlit as st
import pandas as pd

import json
import os

from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode, JsCode

# Define common grid styling that can be reused across all grids
GRID_STYLE = {
    ".ag-row-hover": {"background-color": "#def8ff !important"},  # Light blue hover color
}

def setup_aggrid(df, editable_columns, columns_to_display, user_role, user_email):
    """
    Configure and set up AgGrid with specific settings for editability, conditional formatting, and column options.

    Parameters:
    - df (pd.DataFrame): The DataFrame to display in AgGrid.
    - editable_columns (list): Columns that should be editable based on user role.
    - columns_to_display (list): Columns to display in the grid.
    - user_role (str): The user's role, affecting edit permissions.
    - user_email (str): The user’s email, used to control editability for certain columns.

    Returns:
    - dict: Configuration options for AgGrid, tailored to user roles and edit permissions.
    """
    columns_for_grid = (
        [col for col in columns_to_display if col not in ["MES_DPP_STATUS", "IS_LOCKED"]]
        + editable_columns                                        
        + ["MES_DPP_STATUS", "IS_LOCKED"]                                         
    )
    gb = GridOptionsBuilder.from_dataframe(df[columns_for_grid])
    # gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=100)
    gb.configure_grid_options(
        statusBar={
            "statusPanels": [
                {"statusPanel": "agTotalRowCountComponent", "align": "left"},
                {"statusPanel": "agFilteredRowCountComponent", "align": "left"},
                {"statusPanel": "agAggregationComponent", "align": "right"},
            ]
        }
    )
    
    gb.configure_default_column(editable=False, filterable=True)

    # Apply filtering to display columns
    for col in columns_to_display:
        gb.configure_column(col, filter=True)
    
    cell_style_js = JsCode(f"""
        function(params) {{
            var style = {{}};
            const editableColumns = {str(editable_columns).replace("'", '"')};

            // Highlight locked rows with a specific color
            if (params.data.IS_LOCKED == 1) {{
                style['backgroundColor'] = 'lightGrey';
                style['color'] = 'gray';
            }} 
            // Highlight editable columns
            else if (editableColumns.includes(params.colDef.field)) {{
                style['fontWeight'] = 'bold';
                style['color'] = 'black'
            }}

            // Highlight HODNOTY if different from HODNOTY_SYSTEM and IS_LOCKED is 0
            if (params.data.IS_LOCKED == 0 && params.colDef.field === 'HODNOTY' && params.data.HODNOTY !== params.data.HODNOTY_SYSTEM) {{
                style['backgroundColor'] = '#EDA528';
                style['color'] = 'black';
                style['fontWeight'] = 'bold';
            }}
            
            // Highlight VYKON if different from VYKON_SYSTEM and IS_LOCKED is 0
            if (params.data.IS_LOCKED == 0 && params.colDef.field === 'VYKON' && params.data.VYKON !== params.data.VYKON_SYSTEM) {{
                style['backgroundColor'] = '#EDA528';
                style['color'] = 'black';
                style['fontWeight'] = 'bold';
            }}

            return style;
        }}
    """)
    
    # Highlight rows where IS_LOCKED
    cell_style_lock = JsCode("""
        function(params) {
            if (params.data.IS_LOCKED == 1) {
                return {'backgroundColor': 'lightGrey'};
            }
            if (['HODNOTY_SYSTEM', 'VYKON_SYSTEM'].includes(params.colDef.field)) {
                return {'backgroundColor': '#e7effd', 'color': '#2870ed'};
            }
            return {};
        }
    """)

    # Apply the combined cellStyle to all columns
    for col in columns_to_display:
        gb.configure_column(col, cellStyle=cell_style_lock)

    gb.configure_column("JOB_TITLE_CZ", cellStyle={'backgroundColor': '#e7effd', 'color': '#2870ed'})
    
    # Apply conditional styling to both display and editable columns
    for col in editable_columns:
        gb.configure_column(col, cellStyle=cell_style_js)   

    # Set up cell editors for performance columns
    gb.configure_column("HODNOTY", cellEditor="agSelectCellEditor", cellEditorParams={'values': [0, 1, 2, 3, 4, 5]})
    gb.configure_column("VYKON", cellEditor="agSelectCellEditor", cellEditorParams={'values': [0, 1, 2, 3, 4, 5]})
    for col in [col for col in columns_to_display if col not in ["IS_LOCKED"]]+editable_columns:
        gb.configure_column(col, minWidth=100)
    gb.configure_column("POZNAMKY", minWidth=400)
    gb.configure_column("IS_LOCKED", minWidth=70)


    options = ["nízký", "střední", "vysoký", 0]
    gb.configure_column("POTENCIAL", cellEditor="agSelectCellEditor", cellEditorParams={'values': options})
    gb.configure_column("PRAVDEPODOBNOST_ODCHODU", cellEditor="agSelectCellEditor", cellEditorParams={'values': options})
    gb.configure_column("NASTUPCE", cellEditor="agSelectCellEditor", cellEditorParams={'values': ['Ano', 'Ne']})
    gb.configure_column("MOZNY_KARIERNI_POSUN", cellEditor="agSelectCellEditor", cellEditorParams={'values': ['Ano', 'Ne']})

    # Configure editability based on user role
    if user_role == 'BP':
        editable_condition_js = JsCode("""
            function(params) {
                var isLocked = params.data.IS_LOCKED === 1;  // Check if IS_LOCKED is 1
                var lockedTimestamp = params.data.LOCKED_TIMESTAMP ? new Date(params.data.LOCKED_TIMESTAMP) : null;
                var cutoffDate = new Date();
                cutoffDate.setDate(cutoffDate.getDate() - 30);

                // Make editable if IS_LOCKED is 0 or LOCKED_TIMESTAMP is within the last 30 days
                return !isLocked || (lockedTimestamp && lockedTimestamp >= cutoffDate);
            }
        """)
        
        bp_lock_condition_js = JsCode("""
            function(params) {
                return params.data.IS_LOCKED != 1;
            }
        """)
        #allow_system_edit = editable_condition_js
        gb.configure_column('IS_LOCKED', editable=bp_lock_condition_js, cellStyle=cell_style_js, 
                            cellEditor="agSelectCellEditor", cellEditorParams={'values': [0, 1]})

    elif user_role == 'MA':
        editable_condition_js = JsCode(f"""
            function(params) {{
                return params.data.IS_LOCKED != 1 && params.data.DIRECT_MANAGER_EMAIL == '{user_email}';
            }}
        """)

        cell_style_js = JsCode(f"""
            function(params) {{
                var style = {{}};
                const editableColumns = {str(editable_columns).replace("'", '"')};

                // Check if the cell is editable by checking if it's not locked,
                // belongs to editableColumns, and matches the direct manager email.
                if (params.data.IS_LOCKED == 1) {{
                    style['backgroundColor'] = 'lightGrey';
                    style['color'] = 'gray';
                }} else if (editableColumns.includes(params.colDef.field) && params.data.DIRECT_MANAGER_EMAIL == '{user_email}') {{
                    style['color'] = 'black';
                    style['fontWeight'] = 'bold';
                }}
                
                // Highlight HODNOTY if different from HODNOTY_SYSTEM and IS_LOCKED is 0
                if (params.data.IS_LOCKED == 0 && params.colDef.field === 'HODNOTY' && params.data.HODNOTY !== params.data.HODNOTY_SYSTEM) {{
                    style['backgroundColor'] = '#EDA528';
                    style['color'] = 'black';
                    style['fontWeight'] = 'bold';
                }}
                
                // Highlight VYKON if different from VYKON_SYSTEM and IS_LOCKED is 0
                if (params.data.IS_LOCKED == 0 && params.colDef.field === 'VYKON' && params.data.VYKON !== params.data.VYKON_SYSTEM) {{
                    style['backgroundColor'] = '#EDA528';
                    style['color'] = 'black';
                    style['fontWeight'] = 'bold';
                }}
                
                return style;
            }}
        """)
        #allow_system_edit = False
    elif user_role == 'LC':
        editable_condition_js = JsCode("""
            function(params) {
                return false;
            }
        """)
        #allow_system_edit = False
    
    elif user_role in ['DEV', 'TEST']:
        editable_condition_js = JsCode("""
            function(params) {
                return true;
            }
        """)
        #allow_system_edit = True
        gb.configure_column('IS_LOCKED', editable=True, cellStyle=cell_style_js, cellEditor="agSelectCellEditor", cellEditorParams={'values': [0, 1]})

    #gb.configure_column("VYKON_SYSTEM", editable=allow_system_edit, cellEditor="agSelectCellEditor", cellEditorParams={'values': [0, 1, 2, 3, 4, 5]})
    #gb.configure_column("HODNOTY_SYSTEM", editable=allow_system_edit, cellEditor="agSelectCellEditor", cellEditorParams={'values': [0, 1, 2, 3, 4, 5]})
        
    # Configure editable columns and apply styling
    for col in editable_columns:
        gb.configure_column(col, editable=editable_condition_js, cellStyle=cell_style_js, cellClassRules={"editingStyle": "params.node.isEditing"})

    # Pin essential columns for better visibility
    gb.configure_column("FULL_NAME", pinned="left", cellStyle={'backgroundColor': '#2870ed', 'fontWeight': 'bold', 'color': 'white'})
    gb.configure_column("DIRECT_MANAGER_FULL_NAME", pinned="left", cellStyle={'backgroundColor': '#e7effd', 'color': '#2870ed'})
    
    #filtering columns styles
    for col in ['LOGIN', 'L2_ORGANIZATION_UNIT_NAME_CZ', 'L3_ORGANIZATION_UNIT_NAME_CZ', 'L4_ORGANIZATION_UNIT_NAME_CZ', 
                'TEAM_CODE', 'L2_HEAD_OF_UNIT_FULL_NAME', 'L3_HEAD_OF_UNIT_FULL_NAME','L4_HEAD_OF_UNIT_FULL_NAME']:
        gb.configure_column(col, cellStyle={'backgroundColor': '#e7effd', 'color': '#2870ed'})

    # Auto-size columns based on content
    auto_size_js = JsCode('''
    function(params) {
        params.api.sizeColumnsToFit();
        let allColumnIds = params.columnApi.getAllColumns().map(col => col.colId);
        params.columnApi.autoSizeColumns(allColumnIds, false);
    }
    ''')
    gb.configure_grid_options(onFirstDataRendered=auto_size_js)

    # Load and apply friendly column names from JSON
    file_path = os.path.join(os.path.dirname(__file__), './static/column_names.json')
    with open(file_path, 'r', encoding='utf-8') as file: 
        column_names = json.load(file)    

    for col in columns_to_display + editable_columns:
        friendly_name = column_names.get(col, col)
        gb.configure_column(col, header_name=friendly_name)

    grid_options = gb.build()
    
    return grid_options


def display_table(input_df, grid_options, grid_key, license_key):
    """
    Display the filtered DataFrame in an AgGrid table and track changes made by the user.

    Parameters:
    - input_df (pd.DataFrame): The filtered DataFrame to be displayed in AgGrid.
    - grid_options (dict): AgGrid configuration options set up with `setup_aggrid`.

    Returns:
    - tuple: A tuple with the filtered data, DataFrame of changed rows, and the grid response object.
    """
    df_filtered = input_df.copy()
    selected_year = df_filtered['YEAR_EVALUATION'].unique()[0]
    pk_columns = ['USER_ID', 'YEAR', 'EVALUATION']
    df_filtered.set_index(pk_columns, inplace=True)
    
    # Initialize original and last_saved DataFrames before displaying the grid
    if 'df_original' not in st.session_state or st.session_state['df_original'].empty:
        st.session_state['df_original'] = df_filtered.copy()
    if 'df_last_saved' not in st.session_state or st.session_state['df_last_saved'].empty:
        st.session_state['df_last_saved'] = st.session_state['df_original'].copy()
    
    # Reset index for display purposes
    df_filtered.reset_index(inplace=True)

    grid_response = AgGrid(
        df_filtered,
        key=f'editable_grid_{selected_year}_{grid_key}',
        gridOptions=grid_options,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        update_mode=GridUpdateMode.MODEL_CHANGED,
        allow_unsafe_jscode=True,
        license_key=license_key,
        height=350,
        width='100%',
        enable_enterprise_modules=True,
        custom_css=GRID_STYLE
    )

    filtered_data = pd.DataFrame(grid_response['data'])
    filtered_data.set_index(pk_columns, inplace=True)
    
    # Align indexes for accurate comparison and find changes
    # excluding columns so that values are not considered a change because those fields are not edited by user
    excluded_columns = ['HIST_DATA_MODIFIED_BY', 'HIST_DATA_MODIFIED_WHEN', 'LOCKED_TIMESTAMP'] 
    filtered_data_aligned, df_last_saved_aligned = filtered_data.align(st.session_state['df_last_saved'], join='inner', axis=0)
    filtered_data_aligned_no_hist = filtered_data_aligned.drop(columns=excluded_columns, errors='ignore')
    df_last_saved_aligned_no_hist = df_last_saved_aligned.drop(columns=excluded_columns, errors='ignore')

    changed_rows = filtered_data_aligned_no_hist.compare(df_last_saved_aligned_no_hist)
    # Update df_last_saved to track the most recent changes
    st.session_state['df_last_saved'] = filtered_data.copy()

    # Reset index for display purposes
    changed_rows.reset_index(inplace=True)

    return filtered_data.reset_index(), changed_rows, grid_response


