# Install required dependencies:
# $ uv sync
# Or if using pip:
# $ pip install plotly

import streamlit as st
import pandas as pd

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
    get_prognose_files = getattr(file_module, 'get_prognose_files', None)
    read_data_file = getattr(file_module, 'read_data_file', None)
    get_column_overview = getattr(file_module, 'get_column_overview', None)
    
    # Fallback: if get_prognose_files doesn't exist, use get_uploaded_files with 'prognose'
    if get_prognose_files is None:
        get_uploaded_files = getattr(file_module, 'get_uploaded_files', None)
        if get_uploaded_files is not None:
            def get_prognose_files():
                return get_uploaded_files('prognose')
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
st.title("📊 Prognose inschrijvingen")

# Get files for Prognose inschrijvingen only
prognose_files = get_prognose_files()

if prognose_files:
    # Use the first prognose file (or allow selection if multiple)
    if len(prognose_files) > 1:
        # Multiple files - let user select
        file_names = [file_name for _, file_name, _ in prognose_files]
        selected_file_name = st.selectbox(
            "Selecteer een bestand voor analyse:",
            file_names,
            key="prognose_file_selector"
        )
        # Find the selected file
        file, file_name, file_size = next((f, n, s) for f, n, s in prognose_files if n == selected_file_name)
    else:
        # Single file - use it directly
        file, file_name, file_size = prognose_files[0]
    
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
            # Analysis section
            
            # Helper function to find column name (case-insensitive, with fallbacks)
            def find_column(df, possible_names):
                """Find column name from possible variations"""
                df_cols_lower = {col.lower(): col for col in df.columns}
                for name in possible_names:
                    if name.lower() in df_cols_lower:
                        return df_cols_lower[name.lower()]
                return None
            
            # Find relevant columns
            week_col = find_column(df, ['week_of_year', 'week', 'weeknummer', 'weeknr'])
            academic_week_col = find_column(df, ['academic_week', 'academicweek', 'academische_week'])
            aantal_col = find_column(df, ['aantal', 'aantal_voorspeld', 'count'])
            school_col = find_column(df, ['school', 'instelling', 'schoolnaam'])
            brin_col = find_column(df, ['instellingserkenningscode', 'brin', 'erkenningscode'])
            leerweg_col = find_column(df, ['leertrajectmbo', 'leerweg', 'leertraject'])
            opleidingcode_col = find_column(df, ['opleidingcode', 'opleiding_code', 'code'])
            opleidingsnaam_col = find_column(df, ['opleidingsnaam', 'opleiding_naam', 'opleidingnaam', 'naam'])
            schooljaar_col = find_column(df, ['schooljaar', 'school_jaar', 'jaar'])
            jaar_col = find_column(df, ['jaar', 'year', 'academic_year', 'academisch_jaar'])
            
            # Bar chart: Week vs Aantal voorspeld
            if week_col and aantal_col:
                st.subheader("📊 Voorspellingen per week")
                
                # Prepare data for filtering
                df_filtered = df.copy()
                
                # Create combined opleiding column if both code and name exist
                # Convert opleidingcode to integer (remove .0) before combining
                def format_opleidingcode(code_value):
                    """Convert opleidingcode to integer string (remove .0)"""
                    if pd.isna(code_value):
                        return ''
                    try:
                        # Try to convert to numeric first
                        num_val = pd.to_numeric(code_value, errors='coerce')
                        if pd.isna(num_val):
                            # Not numeric, return as string
                            return str(code_value)
                        else:
                            # Is numeric, convert to int and then string (removes .0)
                            return str(int(float(num_val)))
                    except (ValueError, TypeError, OverflowError):
                        # Fallback: remove .0 from string representation
                        code_str = str(code_value)
                        # Remove trailing .0 but keep integers with .0 in the middle
                        if code_str.endswith('.0'):
                            return code_str[:-2]
                        return code_str
                
                if opleidingcode_col and opleidingsnaam_col:
                    # Apply formatting function to each value
                    df_filtered['_opleiding_combined'] = (
                        df_filtered[opleidingcode_col].apply(format_opleidingcode) + ' - ' + 
                        df_filtered[opleidingsnaam_col].astype(str)
                    )
                elif opleidingcode_col:
                    df_filtered['_opleiding_combined'] = df_filtered[opleidingcode_col].apply(format_opleidingcode)
                elif opleidingsnaam_col:
                    df_filtered['_opleiding_combined'] = df_filtered[opleidingsnaam_col].astype(str)
                
                # Filter section
                st.markdown("### 🔽 Filters")
                
                # Start with base filtered data (only rows with aantal > 0)
                df_base = df_filtered[df_filtered[aantal_col] > 0].copy() if aantal_col else df_filtered.copy()
                
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
                def get_available_options(df, col):
                    """Get unique values from column in df that match current OTHER filters and have aantal > 0"""
                    temp_df = df.copy()
                    
                    # Apply all OTHER filters (not the current one being filtered)
                    if school_col and col != school_col and st.session_state.filter_school_selected:
                        temp_df = temp_df[temp_df[school_col].isin(st.session_state.filter_school_selected)]
                    if brin_col and col != brin_col and st.session_state.filter_brin_selected:
                        temp_df = temp_df[temp_df[brin_col].isin(st.session_state.filter_brin_selected)]
                    if leerweg_col and col != leerweg_col and st.session_state.filter_leerweg_selected:
                        temp_df = temp_df[temp_df[leerweg_col].isin(st.session_state.filter_leerweg_selected)]
                    if '_opleiding_combined' in temp_df.columns and col != '_opleiding_combined' and st.session_state.filter_opleiding_selected:
                        temp_df = temp_df[temp_df['_opleiding_combined'].isin(st.session_state.filter_opleiding_selected)]
                    if schooljaar_col and col != schooljaar_col and st.session_state.filter_schooljaar_selected:
                        temp_df = temp_df[temp_df[schooljaar_col].isin(st.session_state.filter_schooljaar_selected)]
                    
                    # Ensure we only show options that have aantal > 0
                    if aantal_col:
                        temp_df = temp_df[temp_df[aantal_col] > 0]
                    
                    return sorted(temp_df[col].dropna().unique().tolist())
                
                # Create filter columns
                filter_col1, filter_col2, filter_col3 = st.columns(3)
                
                with filter_col1:
                    # School filter
                    if school_col:
                        school_options = get_available_options(df_base, school_col)
                        # Only keep selected values that are still in available options
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
                        brin_options = get_available_options(df_base, brin_col)
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
                        leerweg_options = get_available_options(df_base, leerweg_col)
                        valid_selected_leerweg = [l for l in st.session_state.filter_leerweg_selected if l in leerweg_options]
                        selected_leerweg = st.multiselect(
                            "Leerweg",
                            options=leerweg_options,
                            default=valid_selected_leerweg,
                            key='filter_leerweg'
                        )
                        st.session_state.filter_leerweg_selected = selected_leerweg
                    
                    # Opleiding filter
                    if '_opleiding_combined' in df_base.columns:
                        opleiding_options = get_available_options(df_base, '_opleiding_combined')
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
                        schooljaar_options = get_available_options(df_base, schooljaar_col)
                        valid_selected_schooljaar = [sj for sj in st.session_state.filter_schooljaar_selected if sj in schooljaar_options]
                        selected_schooljaar = st.multiselect(
                            "Schooljaar",
                            options=schooljaar_options,
                            default=valid_selected_schooljaar,
                            key='filter_schooljaar'
                        )
                        st.session_state.filter_schooljaar_selected = selected_schooljaar
                
                # Apply all filters to get final filtered dataframe
                df_filtered = df_base.copy()
                if st.session_state.filter_school_selected and school_col:
                    df_filtered = df_filtered[df_filtered[school_col].isin(st.session_state.filter_school_selected)]
                if st.session_state.filter_brin_selected and brin_col:
                    df_filtered = df_filtered[df_filtered[brin_col].isin(st.session_state.filter_brin_selected)]
                if st.session_state.filter_leerweg_selected and leerweg_col:
                    df_filtered = df_filtered[df_filtered[leerweg_col].isin(st.session_state.filter_leerweg_selected)]
                if st.session_state.filter_opleiding_selected and '_opleiding_combined' in df_filtered.columns:
                    df_filtered = df_filtered[df_filtered['_opleiding_combined'].isin(st.session_state.filter_opleiding_selected)]
                if st.session_state.filter_schooljaar_selected and schooljaar_col:
                    df_filtered = df_filtered[df_filtered[schooljaar_col].isin(st.session_state.filter_schooljaar_selected)]
                
                # Show active filter count
                if len(df_filtered) < len(df):
                    st.info(f"📊 {len(df_filtered):,} van {len(df):,} rijen getoond na filtering")
                
                # Group by week and sum aantal
                if len(df_filtered) > 0:
                    # Group by week_col and get both week_of_year and academic_week for labels
                    if academic_week_col:
                        # Group by both columns to get the mapping
                        weekly_data = df_filtered.groupby([week_col, academic_week_col])[aantal_col].sum().reset_index()
                        # Then aggregate by academic_week_col (taking most common week_col value per academic_week)
                        # This ensures we sort by schooljaar week
                        weekly_data = weekly_data.groupby(academic_week_col).agg({
                            aantal_col: 'sum',
                            week_col: lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else x.iloc[0]
                        }).reset_index()
                        weekly_data = weekly_data.sort_values(academic_week_col)  # Sort by schooljaar week
                        # Create combined labels
                        weekly_data['week_label'] = weekly_data.apply(
                            lambda row: f"Week {int(row[week_col])} (Schooljaar week {int(row[academic_week_col])})" 
                            if pd.notna(row[academic_week_col]) and pd.notna(row[week_col]) else f"Schooljaar week {int(row[academic_week_col])}",
                            axis=1
                        )
                    else:
                        # Only week_col available
                        weekly_data = df_filtered.groupby(week_col)[aantal_col].sum().reset_index()
                        weekly_data = weekly_data.sort_values(week_col)
                        weekly_data['week_label'] = weekly_data[week_col].apply(lambda x: f"Week {int(x)}")
                    
                    weekly_data.columns = [col if col != aantal_col else 'aantal' for col in weekly_data.columns]
                    
                    # Create bar chart with Plotly to show both week numbers on x-axis
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=weekly_data['week_label'],
                        y=weekly_data['aantal'],
                        name='Aantal voorspeld'
                    ))
                    fig.update_layout(
                        title='Voorspellingen per week',
                        xaxis_title='Week (Weeknummer / Schooljaar weeknummer)',
                        yaxis_title='Aantal voorspeld',
                        xaxis=dict(tickangle=-45),
                        height=500
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Show summary statistics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Totaal voorspeld", f"{weekly_data['aantal'].sum():,}")
                    with col2:
                        st.metric("Gemiddelde per week", f"{weekly_data['aantal'].mean():.1f}")
                    with col3:
                        if len(weekly_data) > 0:
                            max_idx = weekly_data['aantal'].idxmax()
                            max_week_label = weekly_data.loc[max_idx, 'week_label']
                            st.metric("Week met meeste inschrijvingen", max_week_label)
                else:
                    st.warning("⚠️ Geen data beschikbaar met de huidige filterinstellingen.")
                
                # Cumulative line chart: Cumulative numbers per year
                if academic_week_col and aantal_col and (schooljaar_col or jaar_col):
                    st.subheader("📈 Cumulatieve voorspellingen per jaar")
                    
                    # Use schooljaar_col if available, otherwise jaar_col
                    jaar_column = schooljaar_col if schooljaar_col else jaar_col
                    
                    # Filter to academic_week between 1 and 52 and apply all existing filters
                    df_cumulative = df_filtered[
                        (df_filtered[academic_week_col] >= 1) & 
                        (df_filtered[academic_week_col] <= 52)
                    ].copy()
                    
                    if len(df_cumulative) > 0:
                        # Initialize week_mapping
                        week_mapping = {}
                        
                        # Group by jaar and academic_week, sum aantal, and get week_of_year mapping
                        if week_col:
                            # Group by all three to get the mapping between academic_week and week_of_year
                            weekly_by_year = df_cumulative.groupby([jaar_column, academic_week_col, week_col])[aantal_col].sum().reset_index()
                            # Aggregate to get one week_of_year per academic_week per year (take first/mode)
                            weekly_by_year = weekly_by_year.groupby([jaar_column, academic_week_col]).agg({
                                aantal_col: 'sum',
                                week_col: 'first'  # Take first week_of_year for this academic_week
                            }).reset_index()
                            
                            # Create mapping from academic_week to week_of_year (for labels)
                            # Use the most common week_of_year for each academic_week across all years
                            week_mapping = df_cumulative.groupby(academic_week_col)[week_col].agg(
                                lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else x.iloc[0]
                            ).to_dict()
                        else:
                            # Only academic_week available
                            weekly_by_year = df_cumulative.groupby([jaar_column, academic_week_col])[aantal_col].sum().reset_index()
                        
                        weekly_by_year = weekly_by_year.sort_values([jaar_column, academic_week_col])
                        
                        # Calculate cumulative sums per year
                        cumulative_data = []
                        for jaar in weekly_by_year[jaar_column].unique():
                            jaar_data = weekly_by_year[weekly_by_year[jaar_column] == jaar].copy()
                            jaar_data = jaar_data.sort_values(academic_week_col)
                            # Calculate cumulative sum
                            jaar_data['cumulatief'] = jaar_data[aantal_col].cumsum()
                            cumulative_data.append(jaar_data[[academic_week_col, 'cumulatief', jaar_column]])
                        
                        if cumulative_data:
                            # Combine all years
                            df_cumulative_combined = pd.concat(cumulative_data, ignore_index=True)
                            
                            # Pivot to have years as columns and weeks as index
                            df_cumulative_pivot = df_cumulative_combined.pivot_table(
                                index=academic_week_col,
                                columns=jaar_column,
                                values='cumulatief',
                                aggfunc='sum'
                            )
                            
                            # Reindex to include all weeks 1-52 for complete x-axis
                            all_weeks = pd.RangeIndex(start=1, stop=53, step=1)
                            df_cumulative_pivot = df_cumulative_pivot.reindex(all_weeks)
                            
                            # Forward fill missing weeks (carry forward last cumulative value)
                            df_cumulative_pivot = df_cumulative_pivot.ffill().fillna(0)
                            
                            # Create combined labels for x-axis using the week numbers from all_weeks
                            if week_col and week_mapping:
                                week_labels = []
                                for week in all_weeks:
                                    if week in week_mapping:
                                        week_of_year = int(week_mapping[week])
                                        week_labels.append(f"Week {week_of_year} (Schooljaar week {int(week)})")
                                    else:
                                        week_labels.append(f"Schooljaar week {int(week)}")
                            else:
                                week_labels = [f"Schooljaar week {int(week)}" for week in all_weeks]
                            
                            df_cumulative_pivot.index = week_labels
                            
                            # Create line chart with Plotly to show both week numbers on x-axis
                            fig = go.Figure()
                            
                            # Add a line for each year
                            for jaar in df_cumulative_pivot.columns:
                                fig.add_trace(go.Scatter(
                                    x=week_labels,
                                    y=df_cumulative_pivot[jaar],
                                    mode='lines+markers',
                                    name=str(jaar),
                                    line=dict(width=2)
                                ))
                            
                            fig.update_layout(
                                title='Cumulatieve voorspellingen per jaar',
                                xaxis_title='Week (Weeknummer / Schooljaar weeknummer)',
                                yaxis_title='Cumulatief aantal',
                                xaxis=dict(tickangle=-45),
                                height=500,
                                hovermode='x unified'
                            )
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Show summary statistics
                            col1, col2 = st.columns(2)
                            with col1:
                                # Total cumulative at end of year (week 52 - last row)
                                if len(df_cumulative_pivot) > 0:
                                    final_totals = df_cumulative_pivot.iloc[-1]  # Last row (week 52)
                                    st.metric("Totaal cumulatief (week 52)", f"{final_totals.sum():,.0f}")
                            with col2:
                                # Number of years shown
                                st.metric("Aantal jaren", len(df_cumulative_pivot.columns))
                        else:
                            st.info("ℹ️ Geen cumulatieve data beschikbaar met de huidige filterinstellingen.")
                    else:
                        st.info("ℹ️ Geen data gevonden voor academic_week 1-52 met de huidige filterinstellingen.")
                
                # New chart: Total inschrijvingen per jaar (som van academic_week 1 t/m 52)
                if academic_week_col and aantal_col and (schooljaar_col or jaar_col):
                    st.subheader("📊 Totaal inschrijvingen per schooljaar")
                    
                    # Use schooljaar_col if available, otherwise jaar_col
                    jaar_column = schooljaar_col if schooljaar_col else jaar_col
                    
                    # Filter to academic_week between 1 and 52 and apply all existing filters
                    df_year_weeks = df_filtered[
                        (df_filtered[academic_week_col] >= 1) & 
                        (df_filtered[academic_week_col] <= 52)
                    ].copy()
                    
                    if len(df_year_weeks) > 0:
                        # Group by jaar and sum aantal (sum over all weeks 1-52 per year)
                        yearly_data = df_year_weeks.groupby(jaar_column)[aantal_col].sum().reset_index()
                        yearly_data = yearly_data.sort_values(jaar_column)
                        yearly_data.columns = ['jaar', 'aantal']
                        
                        # Create bar chart
                        st.bar_chart(
                            yearly_data.set_index('jaar'),
                            use_container_width=True
                        )
                        
                        # Show summary statistics
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Totaal inschrijvingen", f"{yearly_data['aantal'].sum():,}")
                        with col2:
                            st.metric("Gemiddelde per jaar", f"{yearly_data['aantal'].mean():.1f}")
                        with col3:
                            if len(yearly_data) > 0:
                                max_jaar = yearly_data.loc[yearly_data['aantal'].idxmax(), 'jaar']
                                st.metric("Jaar met meeste inschrijvingen", str(max_jaar))
                    else:
                        st.info("ℹ️ Geen data gevonden voor academic_week 1-52 met de huidige filterinstellingen.")
                    
            else:
                st.warning("⚠️ Vereiste kolommen niet gevonden in de data.")
                missing_cols = []
                if not week_col:
                    missing_cols.append("week_of_year / week")
                if not aantal_col:
                    missing_cols.append("aantal / aantal_voorspeld")
                if missing_cols:
                    st.error(f"Ontbrekende kolommen: {', '.join(missing_cols)}")
                st.info("Beschikbare kolommen: " + ", ".join(df.columns.tolist()))
        
        else:
            st.error("Kon bestand niet lezen")
else:
    st.warning("⚠️ Geen bestand geüpload voor Prognose inschrijvingen.")
    st.info("💡 Ga naar tabbblad 'Files' en upload een bestand onder 'Prognose inschrijvingen' in de 'selecteer bestandslocatie' pagina.")