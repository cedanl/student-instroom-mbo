# Install required dependencies:
# $ uv sync
# Or if using pip:
# $ pip install plotly

import streamlit as st
import pandas as pd
import re

try:
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError:
    st.error("❌ Plotly is niet geïnstalleerd. Installeer het met: `uv sync` of `pip install plotly`")
    st.stop()

# Import utility functions from the Files module
import sys
import os
import importlib.util

# Get the path to selecteer_bestandslocatie.py
current_dir = os.path.dirname(os.path.abspath(__file__))
file_module_path = os.path.join(current_dir, '..', 'Files', 'selecteer_bestandslocatie.py')
file_module_path = os.path.abspath(file_module_path)

# Load the module directly from file
try:
    spec = importlib.util.spec_from_file_location("selecteer_bestandslocatie", file_module_path)
    file_module = importlib.util.module_from_spec(spec)
    # Set a flag to indicate this is being imported (not run as main page)
    file_module.__dict__['_imported_via_importlib'] = True
    # Execute the module (this will run all module-level code, but that's okay for Streamlit)
    spec.loader.exec_module(file_module)
    
    # Access functions directly from the module
    get_beschrijving_files = getattr(file_module, 'get_beschrijving_files', None)
    read_data_file = getattr(file_module, 'read_data_file', None)
    get_column_overview = getattr(file_module, 'get_column_overview', None)
    
    # Fallback: if get_prognose_files doesn't exist, use get_uploaded_files with 'prognose'
    if get_beschrijving_files is None:
        get_uploaded_files = getattr(file_module, 'get_uploaded_files', None)
        if get_uploaded_files is not None:
            def get_beschrijving_files():
                return get_uploaded_files('beschrijving')
        else:
            raise AttributeError("get_uploaded_files not found in module")
    
    # Verify all required functions are available
    if read_data_file is None or get_column_overview is None:
        raise AttributeError("Required functions not found in module")
        
except Exception as e:
    st.error(f"Kon bestandsfuncties niet laden: {str(e)}")
    st.info(f"Module pad: {file_module_path}")
    st.info(f"Bestand bestaat: {os.path.exists(file_module_path)}")
    st.stop()

# Page title
st.title("📊 Beschrijving Aanmeldingen")

# Get files for Beschrijving aanmeldingen
beschrijving_files = get_beschrijving_files()

if beschrijving_files:
    # Use the first beschrijving file (or allow selection if multiple)
    if len(beschrijving_files) > 1:
        # Multiple files - let user select
        file_names = [file_name for _, file_name, _ in beschrijving_files]
        selected_file_name = st.selectbox(
            "Selecteer een bestand voor analyse:",
            file_names,
            key="beschrijving_file_selector"
        )
        # Find the selected file
        file, file_name, file_size = next((f, n, s) for f, n, s in beschrijving_files if n == selected_file_name)
    else:
        # Single file - use it directly
        file, file_name, file_size = beschrijving_files[0]
    
    if file:
        # Read file directly (CSV or XLSX)
        try:
            df = read_data_file(file, file_name)
        except UnicodeDecodeError as e:
            st.error(f"❌ Encoding fout bij het lezen van het bestand: {str(e)}")
            st.info("💡 Het bestand gebruikt mogelijk een andere tekst encoding (bijv. ISO-8859-1 of Windows-1252). "
                    "De applicatie probeert automatisch de juiste encoding te detecteren, maar dit is niet gelukt.")
            st.stop()
        except Exception as e:
            st.error(f"❌ Fout bij het lezen van het bestand: {str(e)}")
            st.stop()
        
        if df is not None:
            # Helper function to find column name (case-insensitive, with fallbacks)
            def find_column(df, possible_names):
                """Find column name from possible variations"""
                df_cols_lower = {col.lower(): col for col in df.columns}
                for name in possible_names:
                    if name.lower() in df_cols_lower:
                        return df_cols_lower[name.lower()]
                return None
            
            # Find relevant columns
            caketenid_col = find_column(df, ['caketenid', 'caketen_id', 'caketen', 'ketenid', 'keten_id'])
            status_col = find_column(df, ['status', 'aanmelding_status', 'status_aanmelding'])
            week_col = find_column(df, ['week_of_year', 'week', 'weeknummer', 'weeknr', 'kalenderweek'])
            academic_week_col = find_column(df, ['academic_week', 'academicweek', 'academische_week', 'schooljaarweek'])
            schooljaar_col = find_column(df, ['schooljaar', 'school_jaar', 'jaar'])
            
            # Check if required columns are available
            if not caketenid_col:
                st.warning("⚠️ Kolom 'caketenid' niet gevonden in de data.")
                st.info("Beschikbare kolommen: " + ", ".join(df.columns.tolist()))
            elif not status_col:
                st.warning("⚠️ Kolom 'status' niet gevonden in de data.")
                st.info("Beschikbare kolommen: " + ", ".join(df.columns.tolist()))
            elif not week_col and not academic_week_col:
                st.warning("⚠️ Geen week-kolom gevonden in de data (week_of_year of academic_week).")
                st.info("Beschikbare kolommen: " + ", ".join(df.columns.tolist()))
            else:
                # Prepare data for stacked area chart
                st.subheader("📈 Status per aanmelding over tijd")
                
                # Create a copy for processing
                df_chart = df.copy()
                
                # Ensure we have both week columns or create mapping
                if week_col and academic_week_col:
                    # Both available - use both
                    df_chart['_week'] = df_chart[week_col]
                    df_chart['_academic_week'] = df_chart[academic_week_col]
                elif week_col:
                    # Only calendar week available
                    df_chart['_week'] = df_chart[week_col]
                    df_chart['_academic_week'] = None
                elif academic_week_col:
                    # Only academic week available
                    df_chart['_week'] = None
                    df_chart['_academic_week'] = df_chart[academic_week_col]
                
                # Create week labels first (combining both week types)
                if '_academic_week' in df_chart.columns and '_week' in df_chart.columns:
                    df_chart['week_label'] = df_chart.apply(
                        lambda row: f"Week {int(row['_week'])} (Schooljaar week {int(row['_academic_week'])})"
                        if pd.notna(row['_week']) and pd.notna(row['_academic_week'])
                        else f"Week {int(row['_week'])}" if pd.notna(row['_week'])
                        else f"Schooljaar week {int(row['_academic_week'])}" if pd.notna(row['_academic_week'])
                        else "Onbekend",
                        axis=1
                    )
                elif '_week' in df_chart.columns:
                    df_chart['week_label'] = df_chart['_week'].apply(lambda x: f"Week {int(x)}" if pd.notna(x) else "Onbekend")
                elif '_academic_week' in df_chart.columns:
                    df_chart['week_label'] = df_chart['_academic_week'].apply(lambda x: f"Schooljaar week {int(x)}" if pd.notna(x) else "Onbekend")
                else:
                    df_chart['week_label'] = "Onbekend"
                
                # Helper function to extract week number for sorting
                def extract_week_number(label):
                    """Extract week number from label for sorting"""
                    # Try to find first number in the label
                    match = re.search(r'\d+', str(label))
                    return int(match.group()) if match else 0
                
                # Group by schooljaar, week, and status to count unique caketenid per combination
                # This gives us the number of aanmeldingen (caketenid) per status per week per schooljaar
                grouping_cols = []
                if schooljaar_col:
                    grouping_cols.append(schooljaar_col)
                if '_academic_week' in df_chart.columns:
                    grouping_cols.append('_academic_week')
                elif '_week' in df_chart.columns:
                    grouping_cols.append('_week')
                grouping_cols.append(status_col)
                
                # Also preserve week columns for later use
                week_cols_to_preserve = []
                if '_academic_week' in df_chart.columns:
                    week_cols_to_preserve.append('_academic_week')
                if '_week' in df_chart.columns:
                    week_cols_to_preserve.append('_week')
                
                # Count unique caketenid per week/status/schooljaar combination
                if caketenid_col:
                    chart_data = df_chart.groupby(grouping_cols)[caketenid_col].nunique().reset_index()
                    chart_data.columns = list(chart_data.columns[:-1]) + ['aantal_aanmeldingen']
                else:
                    # Fallback: count rows if caketenid not available
                    chart_data = df_chart.groupby(grouping_cols).size().reset_index(name='aantal_aanmeldingen')
                
                # Calculate cumulative sum per schooljaar and status
                # Sort first by schooljaar and week
                sort_cols = []
                if schooljaar_col and schooljaar_col in chart_data.columns:
                    sort_cols.append(schooljaar_col)
                if '_academic_week' in chart_data.columns:
                    sort_cols.append('_academic_week')
                elif '_week' in chart_data.columns:
                    sort_cols.append('_week')
                
                if sort_cols:
                    chart_data = chart_data.sort_values(sort_cols)
                
                # Calculate cumulative sum per schooljaar and status
                cumulative_data = []
                if schooljaar_col and schooljaar_col in chart_data.columns:
                    for schooljaar in chart_data[schooljaar_col].unique():
                        jaar_data = chart_data[chart_data[schooljaar_col] == schooljaar].copy()
                        # Sort by week within this schooljaar
                        if '_academic_week' in jaar_data.columns:
                            jaar_data = jaar_data.sort_values('_academic_week')
                        elif '_week' in jaar_data.columns:
                            jaar_data = jaar_data.sort_values('_week')
                        
                        for status in jaar_data[status_col].unique():
                            status_data = jaar_data[jaar_data[status_col] == status].copy()
                            # Sort by week again within status
                            if '_academic_week' in status_data.columns:
                                status_data = status_data.sort_values('_academic_week')
                            elif '_week' in status_data.columns:
                                status_data = status_data.sort_values('_week')
                            status_data['cumulatief'] = status_data['aantal_aanmeldingen'].cumsum()
                            cumulative_data.append(status_data)
                else:
                    # No schooljaar column - just calculate cumulative per status
                    for status in chart_data[status_col].unique():
                        status_data = chart_data[chart_data[status_col] == status].copy()
                        # Sort by week within status
                        if '_academic_week' in status_data.columns:
                            status_data = status_data.sort_values('_academic_week')
                        elif '_week' in status_data.columns:
                            status_data = status_data.sort_values('_week')
                        status_data['cumulatief'] = status_data['aantal_aanmeldingen'].cumsum()
                        cumulative_data.append(status_data)
                
                if cumulative_data:
                    chart_data = pd.concat(cumulative_data, ignore_index=True)
                else:
                    # Fallback if no data
                    chart_data['cumulatief'] = chart_data['aantal_aanmeldingen']
                
                # Create week labels for x-axis (combining both week types and schooljaar)
                # If we have both week types in original data but only one in chart_data, try to map back
                if '_academic_week' in chart_data.columns and '_week' not in chart_data.columns and '_week' in df_chart.columns:
                    # Try to map calendar week from original data
                    week_mapping = df_chart.groupby([schooljaar_col, '_academic_week'] if schooljaar_col else ['_academic_week'])['_week'].first().to_dict()
                    def get_calendar_week(row):
                        key = (row[schooljaar_col], row['_academic_week']) if schooljaar_col and schooljaar_col in chart_data.columns else row['_academic_week']
                        return week_mapping.get(key)
                    chart_data['_week'] = chart_data.apply(get_calendar_week, axis=1)
                
                def create_week_label(row):
                    if schooljaar_col and schooljaar_col in chart_data.columns:
                        schooljaar_val = row[schooljaar_col]
                    else:
                        schooljaar_val = None
                    
                    academic_week = row.get('_academic_week') if '_academic_week' in chart_data.columns else None
                    week = row.get('_week') if '_week' in chart_data.columns else None
                    
                    if academic_week is not None and pd.notna(academic_week):
                        if week is not None and pd.notna(week):
                            week_label = f"Week {int(week)} (Schooljaar week {int(academic_week)})"
                        else:
                            week_label = f"Schooljaar week {int(academic_week)}"
                    elif week is not None and pd.notna(week):
                        week_label = f"Week {int(week)}"
                    else:
                        week_label = "Onbekend"
                    
                    if schooljaar_val is not None:
                        return f"{schooljaar_val} - {week_label}"
                    return week_label
                
                chart_data['week_label'] = chart_data.apply(create_week_label, axis=1)
                
                # Pivot data for stacked area chart: status as columns, week_label as index
                # Use cumulative values
                pivot_data = chart_data.pivot_table(
                    index='week_label',
                    columns=status_col,
                    values='cumulatief',
                    aggfunc='sum',
                    fill_value=0
                )
                
                # Sort by week (try to maintain chronological order)
                pivot_data['_sort_key'] = pivot_data.index.map(extract_week_number)
                pivot_data = pivot_data.sort_values('_sort_key')
                pivot_data = pivot_data.drop('_sort_key', axis=1)
                
                # Create stacked area chart with Plotly
                fig = go.Figure()
                
                # Get unique status values
                statuses = pivot_data.columns.tolist()
                
                # Add a trace for each status
                for status in statuses:
                    fig.add_trace(go.Scatter(
                        x=pivot_data.index,
                        y=pivot_data[status],
                        mode='lines',
                        name=str(status),
                        stackgroup='one',  # This creates the stacked area chart
                        fill='tonexty' if status != statuses[0] else 'tozeroy',
                        line=dict(width=0.5)
                    ))
                
                # Update layout
                fig.update_layout(
                    title='Status per aanmelding over tijd (cumulatief, gestapeld)',
                    xaxis_title='Week (Kalenderweek / Schooljaar week)',
                    yaxis_title='Cumulatief aantal aanmeldingen',
                    xaxis=dict(tickangle=-45),
                    height=600,
                    hovermode='x unified',
                    legend=dict(
                        orientation="v",
                        yanchor="top",
                        y=1,
                        xanchor="left",
                        x=1.02
                    )
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Show summary statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    total_aanmeldingen = chart_data['aantal_aanmeldingen'].sum()
                    st.metric("Totaal aanmeldingen", f"{total_aanmeldingen:,}")
                with col2:
                    unique_statuses = chart_data[status_col].nunique()
                    st.metric("Aantal statussen", unique_statuses)
                with col3:
                    if '_academic_week' in chart_data.columns or '_week' in chart_data.columns:
                        unique_weeks = len(chart_data['week_label'].unique())
                        st.metric("Aantal weken", unique_weeks)
        
        else:
            st.error("Kon bestand niet lezen")
else:
    st.warning("⚠️ Geen bestand geüpload voor Beschrijving aanmeldingen.")
    st.info("💡 Ga naar tabbblad 'Files' en upload een bestand onder 'Beschrijving aanmeldingen' in de 'selecteer bestandslocatie' pagina.")

