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
file_module_path = os.path.join(current_dir, '..', 'Bestanden', 'selecteer_bestandslocatie.py')
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
st.title("📈 Beschrijving aanmeldingen")

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
            
            # Find filter columns
            school_col = find_column(df, ['school', 'instelling', 'schoolnaam'])
            brin_col = find_column(df, ['instellingserkenningscode', 'brin', 'erkenningscode'])
            leerweg_col = find_column(df, ['leertrajectmbo', 'leerweg', 'leertraject'])
            opleidingcode_col = find_column(df, ['opleidingcode', 'opleiding_code', 'code'])
            opleidingsnaam_col = find_column(df, ['opleidingsnaam', 'opleiding_naam', 'opleidingnaam', 'naam'])
            
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
                
                # Create combined opleiding column if both code and name exist
                def format_opleidingcode(code_value):
                    """Convert opleidingcode to integer string (remove .0)"""
                    if pd.isna(code_value):
                        return ''
                    try:
                        num_val = pd.to_numeric(code_value, errors='coerce')
                        if pd.isna(num_val):
                            return str(code_value)
                        else:
                            return str(int(float(num_val)))
                    except (ValueError, TypeError, OverflowError):
                        code_str = str(code_value)
                        if code_str.endswith('.0'):
                            return code_str[:-2]
                        return code_str
                
                if opleidingcode_col and opleidingsnaam_col:
                    df_chart['_opleiding_combined'] = (
                        df_chart[opleidingcode_col].apply(format_opleidingcode) + ' - ' + 
                        df_chart[opleidingsnaam_col].astype(str)
                    )
                elif opleidingcode_col:
                    df_chart['_opleiding_combined'] = df_chart[opleidingcode_col].apply(format_opleidingcode)
                elif opleidingsnaam_col:
                    df_chart['_opleiding_combined'] = df_chart[opleidingsnaam_col].astype(str)
                
                # Filter section
                st.markdown("### 🔽 Filters")
                
                # Initialize session state for filters
                if 'filter_school_selected' not in st.session_state:
                    st.session_state.filter_school_selected = []
                if 'filter_brin_selected' not in st.session_state:
                    st.session_state.filter_brin_selected = []
                if 'filter_leerweg_selected' not in st.session_state:
                    st.session_state.filter_leerweg_selected = []
                if 'filter_opleiding_selected' not in st.session_state:
                    st.session_state.filter_opleiding_selected = []
                if 'filter_schooljaar_selected' not in st.session_state:
                    st.session_state.filter_schooljaar_selected = []
                
                # Helper function to get available options for a column based on OTHER filters
                def get_available_options(temp_df, col):
                    """Get unique values from column in df that match current OTHER filters"""
                    filtered_df = temp_df.copy()
                    
                    # Apply all OTHER filters (not the current one being filtered)
                    if school_col and col != school_col and st.session_state.filter_school_selected:
                        filtered_df = filtered_df[filtered_df[school_col].isin(st.session_state.filter_school_selected)]
                    if brin_col and col != brin_col and st.session_state.filter_brin_selected:
                        filtered_df = filtered_df[filtered_df[brin_col].isin(st.session_state.filter_brin_selected)]
                    if leerweg_col and col != leerweg_col and st.session_state.filter_leerweg_selected:
                        filtered_df = filtered_df[filtered_df[leerweg_col].isin(st.session_state.filter_leerweg_selected)]
                    if '_opleiding_combined' in filtered_df.columns and col != '_opleiding_combined' and st.session_state.filter_opleiding_selected:
                        filtered_df = filtered_df[filtered_df['_opleiding_combined'].isin(st.session_state.filter_opleiding_selected)]
                    if schooljaar_col and col != schooljaar_col and st.session_state.filter_schooljaar_selected:
                        filtered_df = filtered_df[filtered_df[schooljaar_col].isin(st.session_state.filter_schooljaar_selected)]
                    
                    return sorted(filtered_df[col].dropna().unique().tolist())
                
                # Create filter columns
                filter_col1, filter_col2, filter_col3 = st.columns(3)
                
                with filter_col1:
                    # School filter
                    if school_col:
                        school_options = get_available_options(df_chart, school_col)
                        valid_selected_schools = [s for s in st.session_state.filter_school_selected if s in school_options]
                        selected_schools = st.multiselect(
                            "Instelling",
                            options=school_options,
                            default=valid_selected_schools,
                            key='filter_school'
                        )
                        st.session_state.filter_school_selected = selected_schools
                    
                    # BRIN filter
                    if brin_col:
                        brin_options = get_available_options(df_chart, brin_col)
                        valid_selected_brin = [b for b in st.session_state.filter_brin_selected if b in brin_options]
                        selected_brin = st.multiselect(
                            "BRIN",
                            options=brin_options,
                            default=valid_selected_brin,
                            key='filter_brin'
                        )
                        st.session_state.filter_brin_selected = selected_brin
                
                with filter_col2:
                    # Leerweg filter
                    if leerweg_col:
                        leerweg_options = get_available_options(df_chart, leerweg_col)
                        valid_selected_leerweg = [l for l in st.session_state.filter_leerweg_selected if l in leerweg_options]
                        selected_leerweg = st.multiselect(
                            "Leerweg",
                            options=leerweg_options,
                            default=valid_selected_leerweg,
                            key='filter_leerweg'
                        )
                        st.session_state.filter_leerweg_selected = selected_leerweg
                    
                    # Opleiding filter
                    if '_opleiding_combined' in df_chart.columns:
                        opleiding_options = get_available_options(df_chart, '_opleiding_combined')
                        valid_selected_opleiding = [o for o in st.session_state.filter_opleiding_selected if o in opleiding_options]
                        selected_opleiding = st.multiselect(
                            "Opleiding",
                            options=opleiding_options,
                            default=valid_selected_opleiding,
                            key='filter_opleiding'
                        )
                        st.session_state.filter_opleiding_selected = selected_opleiding
                
                with filter_col3:
                    # Schooljaar filter
                    if schooljaar_col:
                        schooljaar_options = get_available_options(df_chart, schooljaar_col)
                        valid_selected_schooljaar = [sj for sj in st.session_state.filter_schooljaar_selected if sj in schooljaar_options]
                        selected_schooljaar = st.multiselect(
                            "Schooljaar",
                            options=schooljaar_options,
                            default=valid_selected_schooljaar,
                            key='filter_schooljaar'
                        )
                        st.session_state.filter_schooljaar_selected = selected_schooljaar
                
                # Apply all filters to get final filtered dataframe
                if st.session_state.filter_school_selected and school_col:
                    df_chart = df_chart[df_chart[school_col].isin(st.session_state.filter_school_selected)]
                if st.session_state.filter_brin_selected and brin_col:
                    df_chart = df_chart[df_chart[brin_col].isin(st.session_state.filter_brin_selected)]
                if st.session_state.filter_leerweg_selected and leerweg_col:
                    df_chart = df_chart[df_chart[leerweg_col].isin(st.session_state.filter_leerweg_selected)]
                if st.session_state.filter_opleiding_selected and '_opleiding_combined' in df_chart.columns:
                    df_chart = df_chart[df_chart['_opleiding_combined'].isin(st.session_state.filter_opleiding_selected)]
                if st.session_state.filter_schooljaar_selected and schooljaar_col:
                    df_chart = df_chart[df_chart[schooljaar_col].isin(st.session_state.filter_schooljaar_selected)]
                
                # Show active filter count
                if len(df_chart) < len(df):
                    st.info(f"📊 {len(df_chart):,} van {len(df):,} rijen getoond na filtering")
                
                if len(df_chart) == 0:
                    st.warning("⚠️ Geen data beschikbaar met de huidige filterinstellingen.")
                    st.stop()
                
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
                
                # Helper function to extract week number for sorting (prioritize academic week)
                def extract_week_number(label):
                    """Extract week number from label for sorting - prioritize schooljaar week"""
                    label_str = str(label)
                    # Try to find "Schooljaar week X" first
                    academic_match = re.search(r'Schooljaar week (\d+)', label_str)
                    if academic_match:
                        return int(academic_match.group(1))
                    # Fallback to first number (calendar week)
                    match = re.search(r'\d+', label_str)
                    return int(match.group()) if match else 0
                
                # Define status order (from top to bottom in stacked chart)
                # In stacked charts, first added is bottom, last added is top
                # So we reverse the order: bottom to top = Offered, Received, Submitted, Created, Rejected, Withdrawn, Enrolled
                STATUS_ORDER = ['Offered', 'Received', 'Submitted', 'Created', 'Rejected', 'Withdrawn', 'Enrolled']
                
                def sort_statuses(status_list):
                    """Sort statuses according to predefined order"""
                    # Create a dictionary with order values
                    order_dict = {status: idx for idx, status in enumerate(STATUS_ORDER)}
                    
                    # Sort: first by predefined order, then alphabetically for unknown statuses
                    def get_sort_key(status):
                        status_str = str(status)
                        # Check for exact match first
                        if status_str in order_dict:
                            return (0, order_dict[status_str])
                        # Check case-insensitive match
                        status_lower = status_str.lower()
                        for ordered_status in STATUS_ORDER:
                            if ordered_status.lower() == status_lower:
                                return (0, STATUS_ORDER.index(ordered_status))
                        # Unknown status - put at end
                        return (1, status_str)
                    
                    return sorted(status_list, key=get_sort_key)
                
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
                
                # Create week labels without schooljaar prefix (we'll show per schooljaar separately)
                # If we have both week types in original data but only one in chart_data, try to map back
                if '_academic_week' in chart_data.columns and '_week' not in chart_data.columns and '_week' in df_chart.columns:
                    # Try to map calendar week from original data
                    week_mapping = df_chart.groupby([schooljaar_col, '_academic_week'] if schooljaar_col else ['_academic_week'])['_week'].first().to_dict()
                    def get_calendar_week(row):
                        key = (row[schooljaar_col], row['_academic_week']) if schooljaar_col and schooljaar_col in chart_data.columns else row['_academic_week']
                        return week_mapping.get(key)
                    chart_data['_week'] = chart_data.apply(get_calendar_week, axis=1)
                def create_week_label_simple(row):
                    academic_week = row.get('_academic_week') if '_academic_week' in chart_data.columns else None
                    week = row.get('_week') if '_week' in chart_data.columns else None
                    
                    if academic_week is not None and pd.notna(academic_week):
                        if week is not None and pd.notna(week):
                            return f"Week {int(week)} (Schooljaar week {int(academic_week)})"
                        else:
                            return f"Schooljaar week {int(academic_week)}"
                    elif week is not None and pd.notna(week):
                        return f"Week {int(week)}"
                    else:
                        return "Onbekend"
                
                chart_data['week_label'] = chart_data.apply(create_week_label_simple, axis=1)
                
                # Get available schooljaren for selection
                if schooljaar_col and schooljaar_col in chart_data.columns:
                    available_schooljaren = sorted(chart_data[schooljaar_col].unique().tolist())
                    
                    # Schooljaar selector
                    st.markdown("### 📅 Selecteer schooljaren")
                    selected_schooljaren = st.multiselect(
                        "Kies de schooljaren om weer te geven:",
                        options=available_schooljaren,
                        default=available_schooljaren[:2] if len(available_schooljaren) >= 2 else available_schooljaren,
                        key='schooljaar_selector'
                    )
                    
                    if selected_schooljaren:
                        # Filter data to selected schooljaren
                        chart_data_filtered = chart_data[chart_data[schooljaar_col].isin(selected_schooljaren)].copy()
                        
                        # Create charts per schooljaar - one chart per schooljaar
                        # Display max 2 charts per row
                        for idx, schooljaar in enumerate(selected_schooljaren):
                            # Filter data for this schooljaar
                            jaar_data = chart_data_filtered[chart_data_filtered[schooljaar_col] == schooljaar].copy()
                            
                            if len(jaar_data) > 0:
                                # Pivot data for this schooljaar
                                pivot_data = jaar_data.pivot_table(
                                    index='week_label',
                                    columns=status_col,
                                    values='cumulatief',
                                    aggfunc='sum',
                                    fill_value=0
                                )
                                
                                # Sort by schooljaar week (prioritize academic_week if available in data)
                                if '_academic_week' in jaar_data.columns:
                                    # Use academic_week directly for sorting if available
                                    # Create a mapping from week_label to academic_week
                                    week_mapping = jaar_data.set_index('week_label')['_academic_week'].to_dict()
                                    pivot_data['_sort_key'] = pivot_data.index.map(lambda x: week_mapping.get(x, extract_week_number(x)))
                                else:
                                    # Fallback to extracting from label
                                    pivot_data['_sort_key'] = pivot_data.index.map(extract_week_number)
                                
                                pivot_data = pivot_data.sort_values('_sort_key')
                                pivot_data = pivot_data.drop('_sort_key', axis=1)
                                
                                # Create a unique stackgroup name for this schooljaar
                                stackgroup_name = f'stack_{schooljaar}_{idx}'
                                
                                # Create stacked area chart for this schooljaar
                                fig = go.Figure()
                                
                                # Get unique status values and sort according to predefined order
                                statuses = sort_statuses(pivot_data.columns.tolist())
                                
                                # Add a trace for each status in the correct order
                                for status in statuses:
                                    fig.add_trace(go.Scatter(
                                        x=pivot_data.index,
                                        y=pivot_data[status],
                                        mode='lines',
                                        name=str(status),
                                        stackgroup=stackgroup_name,  # Unique stackgroup per schooljaar
                                        fill='tonexty' if status != statuses[0] else 'tozeroy',
                                        line=dict(width=0.5)
                                    ))
                                
                                # Update layout
                                fig.update_layout(
                                    title=f'Schooljaar {schooljaar}',
                                    xaxis_title='Week (Kalenderweek / Schooljaar week)',
                                    yaxis_title='Cumulatief aantal aanmeldingen',
                                    xaxis=dict(tickangle=-45),
                                    height=500,
                                    hovermode='x unified',
                                    legend=dict(
                                        orientation="v",
                                        yanchor="top",
                                        y=1,
                                        xanchor="left",
                                        x=1.02
                                    ),
                                    showlegend=True  # Show legend for each chart
                                )
                                
                                # Display chart in columns (max 2 per row)
                                if idx % 2 == 0:
                                    # Start new row
                                    cols = st.columns(2)
                                
                                # Display in appropriate column
                                with cols[idx % 2]:
                                    st.plotly_chart(fig, use_container_width=True)
                                    
                                    # Show summary for this schooljaar
                                    jaar_total = jaar_data['aantal_aanmeldingen'].sum()
                                    st.metric("Totaal aanmeldingen", f"{jaar_total:,}")
                    else:
                        st.info("Selecteer ten minste één schooljaar om de grafieken weer te geven.")
                else:
                    # No schooljaar column - show single chart
                    # Pivot data for stacked area chart: status as columns, week_label as index
                    pivot_data = chart_data.pivot_table(
                        index='week_label',
                        columns=status_col,
                        values='cumulatief',
                        aggfunc='sum',
                        fill_value=0
                    )
                    
                    # Sort by schooljaar week (prioritize academic week)
                    # Try to use academic_week from chart_data if available
                    if '_academic_week' in chart_data.columns:
                        # Create a mapping from week_label to academic_week
                        week_mapping = chart_data.set_index('week_label')['_academic_week'].to_dict()
                        pivot_data['_sort_key'] = pivot_data.index.map(lambda x: week_mapping.get(x, extract_week_number(x)))
                    else:
                        # Fallback to extracting from label
                        pivot_data['_sort_key'] = pivot_data.index.map(extract_week_number)
                    
                    pivot_data = pivot_data.sort_values('_sort_key')
                    pivot_data = pivot_data.drop('_sort_key', axis=1)
                    
                    # Create stacked area chart with Plotly
                    fig = go.Figure()
                    
                    # Get unique status values and sort according to predefined order
                    statuses = sort_statuses(pivot_data.columns.tolist())
                    
                    # Add a trace for each status in the correct order
                    for status in statuses:
                        fig.add_trace(go.Scatter(
                            x=pivot_data.index,
                            y=pivot_data[status],
                            mode='lines',
                            name=str(status),
                            stackgroup='one',
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
    st.info("💡 Ga naar tabbblad 'Files' en upload een bestand onder 'Beschrijving aanmeldingen' in de 'Selecteer bestandslocatie' pagina.")

