import streamlit as st
import pandas as pd
import plotly.express as px

from st_aggrid import AgGrid, GridOptionsBuilder, DataReturnMode, GridUpdateMode, JsCode, ColumnsAutoSizeMode

# Define common grid styling that can be reused across all grids
GRID_STYLES = {
    ".ag-row-hover": {"background-color": "#def8ff !important"},  # Light blue hover color
}

def preprocess_df_for_charts(df):
    """
    Prepare the DataFrame for chart display, converting columns to appropriate types 
    and adding missing combinations of JAK, CO, and POTENCIAL values.

    Parameters:
    - df (pd.DataFrame): The original DataFrame.

    Returns:
    - pd.DataFrame: A preprocessed DataFrame ready for visualization.
    """
    df = df.copy()  # Avoid modifying the original DataFrame

    # Define possible values, ensuring all are strings
    hodnoty_values = [0, 1, 2, 3, 4, 5]
    vykon_values = [0, 1, 2, 3, 4, 5]
    potencial_values = ["0", "nízký", "střední", "vysoký"]

    # Convert columns to integers if appropriate
    df['HODNOTY'] = df['HODNOTY'].fillna(0).astype('Int64')
    df['VYKON'] = df['VYKON'].fillna(0).astype('Int64')
    df['HODNOTY_PREVIOUS'] = df['HODNOTY_PREVIOUS'].fillna(0).astype('Int64')
    df['VYKON_PREVIOUS'] = df['VYKON_PREVIOUS'].fillna(0).astype('Int64')
    df = df.rename(columns={"HODNOTY": "JAK", "VYKON": "CO", "HODNOTY_PREVIOUS": "JAK_PREVIOUS",
                            "VYKON_PREVIOUS": "CO_PREVIOUS"})

    # Ensure POTENCIAL column is also in string format for consistency
    df['POTENCIAL'] = df['POTENCIAL'].astype(str)

    def transform_name(name):
        parts = name.split()
        if len(parts) > 1:
            return f"{parts[0][0]}. {parts[-1]}"
        return name
        
    # Identify missing combinations
    existing_combinations = df.set_index(['JAK', 'CO', 'POTENCIAL']).index
    all_combinations = pd.MultiIndex.from_product(
        [hodnoty_values, vykon_values, potencial_values],
        names=['JAK', 'CO', 'POTENCIAL']
    )
    missing_combinations = all_combinations.difference(existing_combinations)

    # Convert MultiIndex to DataFrame for missing rows and add FULL_NAME column
    missing_rows = pd.DataFrame(missing_combinations.tolist(), columns=['JAK', 'CO', 'POTENCIAL'])
    missing_rows['FULL_NAME'] = ''  # Add empty FULL_NAME for visualization

    # Append missing rows to the original DataFrame, dropping duplicates
    df = pd.concat([df, missing_rows], ignore_index=True).drop_duplicates(subset=['JAK', 'CO', 'POTENCIAL', 'FULL_NAME'])
    df['FULL_NAME_SPLIT'] = df['FULL_NAME'].apply(transform_name)
    return df


def categorize_3_grid(row):
    """
    Categorize rows into 'Top', 'Middle', 'Low', or 'Nehodnocení' based on CO, JAK, 
    and POTENCIAL values for a 3x3 grid.

    Parameters:
    - row (pd.Series): A single row from the DataFrame.

    Returns:
    - str: The category label for the row.
    """
    CO = row['CO']
    JAK = row['JAK']
    POTENCIAL = row['POTENCIAL']
    sum_co_jak = CO + JAK
    
    if POTENCIAL == "0" or sum_co_jak == 0:
        return 'Nehodnocení'
    elif POTENCIAL in ["nízký", "střední"] and sum_co_jak in range(1, 4):
        return 'Low'
    elif (POTENCIAL == "vysoký" and sum_co_jak in range(1, 4)) or \
         (POTENCIAL in ["nízký", "střední"] and sum_co_jak in range(4, 8)) or \
         (POTENCIAL == "nízký" and sum_co_jak in range(8, 11)):
        return 'Middle'
    elif (POTENCIAL == "vysoký" and sum_co_jak in range(4, 8)) or \
         (POTENCIAL in ["střední", "vysoký"] and sum_co_jak in range(8, 11)):
        return 'Top'
    else:
        return 'Nehodnocení'


def categorize_5_grid(row):
    """
    Categorize rows into 'Top', 'Middle', 'Low', or 'Nehodnocení' based on CO and JAK 
    values for a 5x5 grid.

    Parameters:
    - row (pd.Series): A single row from the DataFrame.

    Returns:
    - str: The category label for the row.
    """
    CO = row['CO']
    JAK = row['JAK']
    
    if CO == 0 or JAK == 0:
        return 'Nehodnocení'
    elif (CO in [4, 5] and JAK in [4, 5]):
        return 'Top'
    elif ((CO == 2 and JAK in [3, 4, 5]) or 
          (CO == 3 and JAK in [2, 3, 4, 5]) or 
          (CO in [4, 5] and JAK in [2, 3])):
        return 'Middle'
    elif ((CO == 1 or JAK == 1) or 
          (CO == 2 and JAK in [1, 2]) or 
          (CO in [3, 4, 5] and JAK == 1)):
        return 'Low'
    else:
        return 'Nehodnocení'


def display_5_grid_summary(filtered_df, period):
    """
    Display a summary of counts and percentages for each 5x5 grid category ('Top', 'Middle', 'Low', 'Nehodnocení').

    Parameters:
    - filtered_df (pd.DataFrame): Filtered data for the summary.
    - period (str): The evaluation period ('current' or 'previous').
    """
    # Apply the categorization function to each row in the DataFrame
    filtered_df_summary = filtered_df[filtered_df['USER_ID'].notnull()]
    filtered_df_summary.loc[:, 'Category'] = filtered_df_summary.apply(categorize_5_grid, axis=1)

    # Calculate the counts and percentages for each category
    category_counts = filtered_df_summary['Category'].value_counts()
    total_count = len(filtered_df_summary)
    category_percentages = (category_counts / total_count * 100).round(2)

    # Display the results in Streamlit
    with st.container():
        for category in ['Top', 'Middle', 'Low', 'Nehodnocení']:
            count = category_counts.get(category, 0)
            percentage = category_percentages.get(category, 0.0)
            
            # Use Markdown to format each category with a bold title, count, and percentage
            st.markdown(
                f"""
                <div style="border: 1px solid #ddd; padding: 10px; margin: 5px 0; border-radius: 5px;">
                    <strong style="font-size: 16px; color: #2A9D8F;">{category}:</strong>
                    <span style="font-size: 14px;">{count}</span> 
                    <span style="font-size: 14px; color: #888;">({percentage}%)</span>
                </div>
                """, 
                unsafe_allow_html=True
            )


def display_3_grid_summary(filtered_df, period):
    """
    Display a summary of counts and percentages for each 3x3 grid category ('Top', 'Middle', 'Low', 'Nehodnocení').

    Parameters:
    - filtered_df (pd.DataFrame): Filtered data for the summary.
    - period (str): The evaluation period ('current' or 'previous').
    """
    # Apply the categorization function to each row in the DataFrame
    filtered_df_summary = filtered_df[filtered_df['USER_ID'].notnull()]
    filtered_df_summary.loc[:, '3_grid_Category'] = filtered_df_summary.apply(categorize_3_grid, axis=1)

    # Calculate the counts and percentages for each 3_grid category
    grid_category_counts = filtered_df_summary['3_grid_Category'].value_counts()
    total_count = len(filtered_df_summary)
    grid_category_percentages = (grid_category_counts / total_count * 100).round(2)

    # Display the results in Streamlit
    with st.container():
        for category in ['Top', 'Middle', 'Low', 'Nehodnocení']:
            count = grid_category_counts.get(category, 0)
            percentage = grid_category_percentages.get(category, 0.0)
            
            st.markdown(
                f"""
                <div style="border: 1px solid #ddd; padding: 10px; margin: 5px 0; border-radius: 5px;">
                    <strong style="font-size: 16px; color: #2A9D8F;">{category}:</strong>
                    <span style="font-size: 14px;">{count}</span> 
                    <span style="font-size: 14px; color: #888;">({percentage}%)</span>
                </div>
                """, 
                unsafe_allow_html=True
            )


def display_5_grid(filtered_df, period, license_key):
    """
    Display a 5x5 grid of CO (performance) and JAK (values) ratings.

    Parameters:
    - filtered_df (pd.DataFrame): Filtered data for grid display.
    - period (str): 'current' or 'previous' period indicator.
    """
    # Define the mapping or use string formatting
    suffix = '_PREVIOUS' if period == 'previous' else ''
    index_column = f'CO{suffix}'
    columns_column = f'JAK{suffix}'

    # Create the pivot table
    pivot_df = filtered_df.pivot_table(
        index=index_column,
        columns=columns_column,
        values='FULL_NAME_SPLIT',
        aggfunc=lambda x: ', '.join([name for name in x if name]),
        observed=False
    ).fillna('')

    pivot_df = pivot_df.sort_index(ascending=False)
    pivot_df.reset_index(inplace=True)
    pivot_df.columns = pivot_df.columns.map(str)

    gb = GridOptionsBuilder.from_dataframe(pivot_df)
    # Dynamically enable/disable pagination
    page_size = 6
    if len(pivot_df) <= page_size:
        gb.configure_pagination(enabled=False)
    else:
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=page_size)

    gb.configure_default_column(
        filterable=False,
        resizable=True,
        autoHeight=True,
        wrapText=True,
        suppressMovable=True,
        sortable=False,
       # cellStyle={
       #     'whiteSpace': 'normal',
       #     'padding': '2px',
       #     'font-size': '10px',
       #     'line-height': '1.2',
       # }
    )
    
    js_code = JsCode("""
        function(params) {
            // Convert field names and data values to numbers for accurate comparison
            var colField = Number(params.colDef.field);
            var vykon = Number(params.data.CO);
            var vykon_previous = Number(params.data.CO_PREVIOUS);

            // Check if VYKON and VYKON_PREVIOUS are valid numbers
            var hasVykon = !isNaN(vykon);
            var hasVykonPrevious = !isNaN(vykon_previous);

            // Current period styling
            if (hasVykon) {
                if ((vykon === 1 && [1, 2, 3, 4, 5].includes(colField))) {
                    return { 'backgroundColor': '#2970ED','color': 'white' };
                } else if ([1, 2, 3, 4, 5].includes(vykon) && colField === 1) {
                    return { 'backgroundColor': '#2970ED', 'color': 'white' };
                } else if (vykon === 2 && colField === 2) {
                    return { 'backgroundColor': '#2970ED', 'color': 'white' };
                } else if ([3, 4, 5].includes(vykon) && colField === 2) {
                    return { 'backgroundColor': 'lightblue' };
                } else if ([2, 3, 4, 5].includes(vykon) && colField === 3) {
                    return { 'backgroundColor': 'lightblue' };
                } else if ([2, 3].includes(vykon) && [4, 5].includes(colField)) {
                    return { 'backgroundColor': 'lightblue' };
                }
            }
            // Previous period styling
            else if (hasVykonPrevious) {
                if ((vykon_previous === 1 && [1, 2, 3, 4, 5].includes(colField))) {
                    return { 'backgroundColor': 'grey' };
                } else if ([1, 2, 3, 4, 5].includes(vykon_previous) && colField === 1) {
                    return { 'backgroundColor': 'grey' };
                } else if (vykon_previous === 2 && [1, 2].includes(colField)) {
                    return { 'backgroundColor': 'grey' };
                } else if ([3, 4, 5].includes(vykon_previous) && colField === 2) {
                    return { 'backgroundColor': 'lightgrey' };
                } else if ([2, 3, 4, 5].includes(vykon_previous) && colField === 3) {
                    return { 'backgroundColor': 'lightgrey' };
                } else if ([2, 3].includes(vykon_previous) && [4, 5].includes(colField)) {
                    return { 'backgroundColor': 'lightgrey' };
                }
            }
            return null;
        }
        """)
    
    row_height_js = JsCode("""
        function(params) {
            // Safely get text length from any field, return 0 if field doesn't exist
            function getFieldLength(data, fieldName) {
                return (data && data[fieldName] && data[fieldName].toString) 
                       ? data[fieldName].toString().length 
                       : 0;
            }
        
            // Get lengths of all fields in the row
            let maxLength = 0;
            for (let field in params.data) {
                maxLength = Math.max(maxLength, getFieldLength(params.data, field));
            }
            // Base height
            let baseHeight = 25;
            
            // Add height based on content length
            let additionalHeight = Math.ceil((maxLength - 50) / 50) * 25;  // Add 25px for every 50 characters
            
            return baseHeight + additionalHeight;
        }
        """)
    
   # for column in pivot_df.columns:
    #    gb.configure_column(column, cellStyle=js_code)

    gb.configure_column(
        pivot_df.columns[0],
        pinned="left",
        suppressMenu=True,
        resizable=False,
        minWidth=50,
        maxWidth=50,
        cellStyle={'backgroundColor': '#f8f9fb'}
    )
    
    for column in pivot_df.columns[1:]:
        gb.configure_column(column, flex=1, minWidth=150, cellStyle=js_code) #, maxWidth=200
    
    gb.configure_grid_options(
        getRowHeight=row_height_js,
        domLayout='normal'
        #onFirstDataRendered="function(params) { params.api.sizeColumnsToFit(); }"
    )
    
    grid_options = gb.build()
    
    try:
        if period == 'previous':
            chart_year = 'Předchozí hodnocení'
        else:
            chart_year = str(filtered_df['YEAR_EVALUATION'].unique()[0])
    except:
        chart_year = 'Žádná data k zobrazení'
    #chart_title = f'Výkon v dimenzích CO a JAK: {chart_year}'
    #st.markdown(f"<h7 style='text-align: left; font-weight: bold;'>{chart_title}</h7>", unsafe_allow_html=True)
    
    AgGrid(
        pivot_df,
        gridOptions=grid_options,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        allow_unsafe_jscode=True,
        fit_columns_on_grid_load=True,
        height=700,
        enable_enterprise_modules=True,
        license_key=license_key,
        custom_css=GRID_STYLES
        #columns_auto_size_mode=ColumnsAutoSizeMode.NO_AUTOSIZE,
        #update_mode="MODEL_CHANGED",
        #width='100%'
    )


def display_3_grid(filtered_df, period, license_key):
    """
    Display a 3x3 grid of CO (performance), JAK (values), and POTENCIAL ratings.

    Parameters:
    - filtered_df (pd.DataFrame): Filtered data for grid display.
    - period (str): 'current' or 'previous' period indicator.
    """
    # Define the suffix based on the period
    suffix = '_PREVIOUS' if period == 'previous' else ''
    vykon_column = f'CO{suffix}'
    hodnoty_column = f'JAK{suffix}'
    potencial_column = f'POTENCIAL{suffix}'
   
    # Compute 'HODNOTY_VYKON_SUM' for the selected period
    filtered_df['JAK_CO_SUM'] = filtered_df[hodnoty_column] + filtered_df[vykon_column]
    
    # Define bins and labels for CO_JAK
    bins = [-float('inf'), 0, 3, 7, 10]
    labels = ['0', '1-3', '4-7', '8-10']
    filtered_df['CO_JAK'] = pd.cut(
        filtered_df['JAK_CO_SUM'],
        bins=bins,
        labels=labels,
        include_lowest=True,
        right = True
    )

    # Create the pivot table using the selected period's POTENCIAL column
    pivot_df = filtered_df.pivot_table(
        index='CO_JAK',
        columns=potencial_column,
        values='FULL_NAME_SPLIT',
        aggfunc=lambda x: ', '.join([name for name in x if name]),
        observed=False
    ).fillna('')
    
    pivot_df = pivot_df.sort_index(ascending=False)
    pivot_df.reset_index(inplace=True)
    pivot_df.columns = pivot_df.columns.map(str)
    
    # Configure grid options
    gb = GridOptionsBuilder.from_dataframe(pivot_df)
    page_size = 4
    if len(pivot_df) <= page_size:
        gb.configure_pagination(enabled=False)
    else:
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=page_size)

    gb.configure_default_column(
        filterable=False,
        autoHeight=True,
        resizable=True,
        wrapText=True,
        suppressMovable=True,
        #cellStyle={
        #    'whiteSpace': 'normal',
        #    'padding': '2px',
        #    'font-size': '10px',
        #    'line-height': '1.2',
        #}
    )
    
    #for column in pivot_df.columns:
      #  gb.configure_column(column, flex=1, minWidth=300) # , maxWidth=200
    
    # Define colors based on the period
    if period == 'current':
        primary_color = '#2970ED'      # Blue
        secondary_color = 'lightBlue'  # Light Blue
    elif period == 'previous':
        primary_color = 'grey'         # Grey
        secondary_color = 'lightgrey'  # Light Grey
    else:
        primary_color = '#FFFFFF'      # Default to white if period is invalid
        secondary_color = '#FFFFFF'
    
    # JavaScript code for cell styling
    js_code_template = """
    function(params) {
        if ((params.data.CO_JAK == '1-3') && 
            (params.colDef.field == 'nízký' || params.colDef.field == 'střední')) {
            return { 'backgroundColor': '%(primary_color)s', 'color': 'white' };
        } else if ((params.data.CO_JAK == '4-7') && 
                   (params.colDef.field == 'nízký' || params.colDef.field == 'střední')) {
            return { 'backgroundColor': '%(secondary_color)s' };
        } else if ((params.data.CO_JAK == '8-10') && 
                   (params.colDef.field == 'nízký')) {
            return { 'backgroundColor': '%(secondary_color)s' };
        } else if ((params.data.CO_JAK == '1-3') && 
                   (params.colDef.field == 'vysoký')) {
            return { 'backgroundColor': '%(secondary_color)s' };
        }
        return null;
    }
    """
    # Format the JavaScript code with the selected colors
    js_code = JsCode(js_code_template % {
        'primary_color': primary_color,
        'secondary_color': secondary_color
    })

    row_height_js = JsCode("""
        function(params) {
            // Safely get text length from any field, return 0 if field doesn't exist
            function getFieldLength(data, fieldName) {
                return (data && data[fieldName] && data[fieldName].toString) 
                       ? data[fieldName].toString().length 
                       : 0;
            }
        
            // Get lengths of all fields in the row
            let maxLength = 0;
            for (let field in params.data) {
                maxLength = Math.max(maxLength, getFieldLength(params.data, field));
            }
            // Base height
            let baseHeight = 25;
            
            // Add height based on content length
            let additionalHeight = Math.ceil((maxLength - 50) / 50) * 25;  // Add 25px for every 50 characters
            
            return baseHeight + additionalHeight;
        }
        """)
    
    gb.configure_column(
        pivot_df.columns[0],
        pinned="left",
        suppressMenu=True,
        resizable=False,
        minWidth=70,
        maxWidth=70,
        cellStyle={'backgroundColor': '#f8f9fb'}
    )
    
    # Apply the cell styling
    for column in pivot_df.columns[1:]:
        gb.configure_column(column, flex=1, minWidth=200, cellStyle=js_code) #, maxWidth=200
    
    #for column in pivot_df.columns:
    #    gb.configure_column(column, cellStyle=js_code)
    
    gb.configure_grid_options(
       # rowHeight=70,
        getRowHeight=row_height_js,
        domLayout='normal',
    )
    
    grid_options = gb.build()
    
    # Display the chart title with the correct year
    try:
        if period == 'previous':
            chart_year = 'Předchozí hodnocení'
        else:
            chart_year = str(filtered_df['YEAR_EVALUATION'].unique()[0])
    except:
        chart_year = 'Žádná data k zobrazení'
    #chart_title = f'Výkon v dimenzích CO, JAK a potenciál: {chart_year}'
    #st.markdown(f"<h7 style='text-align: left; font-weight: bold;'>{chart_title}</h7>", unsafe_allow_html=True)
    
    # Display the grid
    AgGrid(
        pivot_df,
        gridOptions=grid_options,
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        allow_unsafe_jscode=True,
        fit_columns_on_grid_load=True,
        enable_enterprise_modules=True,
        license_key=license_key,
        height=700,
        custom_css=GRID_STYLES
       # width='100%'
    )

def display_column_chart(df, filtered_df):
    """
    Display a bar chart showing trends over time for CO and JAK ratings.

    Parameters:
    - df (pd.DataFrame): The main dataset.
    - filtered_df (pd.DataFrame): The filtered dataset based on user selections.
    """
    filtered_user_ids = filtered_df['USER_ID'].unique()
    df_filtered_by_user = df[df['USER_ID'].isin(filtered_user_ids)]
    df_filtered_by_user = df_filtered_by_user.rename(columns={"HODNOTY":"CO", "VYKON":"JAK"})
    column_chart_data = df_filtered_by_user.groupby(['YEAR']).agg({
        'JAK': 'mean',
        'CO': 'mean'
    }).reset_index()
    
    column_chart_data = column_chart_data.melt(
        id_vars='YEAR',
        value_vars=['JAK', 'CO'],
        var_name='Metric',
        value_name='Value'
    )
    
    st.markdown("<h7 style='text-align: left; font-weight: bold;'>Vývoj CO a JAK v čase</h7>", unsafe_allow_html=True)
    column_chart_fig = px.bar(
        column_chart_data,
        height=300,
        x='YEAR',
        y='Value',
        color='Metric',
        barmode='group'
    )
    # Set autoscaling for both width and height
    column_chart_fig.update_layout(
        autosize=True,
        height=None,
        width=None,
    )
    
    st.plotly_chart(column_chart_fig, use_container_width=True)


def display_charts(df, filtered_df, license_key):
    """
    Display all main charts, including the 5x5 and 3x3 grids and a trend chart.

    Parameters:
    - df (pd.DataFrame): The full dataset.
    - filtered_df (pd.DataFrame): Filtered data for the displayed charts.
    """
    with st.expander("**Výkon v dimenzích CO a JAK**", expanded=False):
        # col1, col2 = st.columns(2)
        # with col1:
        display_5_grid(filtered_df=filtered_df, period='current', license_key=license_key)
        display_5_grid_summary(filtered_df, period='current')
        # with col2:
        #     display_5_grid(filtered_df, period='previous')
    
    with st.expander("**Výkon v dimenzích CO, JAK a POTENCIÁL**", expanded=False):
        # col1, col2 = st.columns(2)
        # with col1:
        display_3_grid(filtered_df, period='current', license_key=license_key)
        display_3_grid_summary(filtered_df, period='current')
        # with col2:
        #     display_3_grid(filtered_df, period='previous')
    
    with st.expander("**Vývoj CO a JAK v čase**", expanded=False):
        display_column_chart(df, filtered_df)
