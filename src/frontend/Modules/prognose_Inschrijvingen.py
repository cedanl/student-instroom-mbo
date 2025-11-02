import streamlit as st
import pandas as pd

# Import utility functions from the Files module
try:
    # Try relative import first (works when run as part of the package)
    from ..Files.selecteer_bestandslocatie import get_uploaded_file, read_data_file, get_column_overview
except ImportError:
    # Fallback to absolute import (works when run directly or in different contexts)
    import sys
    import os
    # Add the src directory to the path
    src_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    from frontend.Files.selecteer_bestandslocatie import get_uploaded_file, read_data_file, get_column_overview  # type: ignore

# Page title
st.title("📊 Prognose Inschrijvingen")

# Get file info
file, file_name, file_size = get_uploaded_file()
if file:
    st.success(f"✅ Analyse {file_name}")
    
    
    # Read file directly (CSV or XLSX)
    try:
        df = read_data_file()
    except UnicodeDecodeError as e:
        st.error(f"❌ Encoding fout bij het lezen van het bestand: {str(e)}")
        st.info("💡 Het bestand gebruikt mogelijk een andere tekst encoding (bijv. ISO-8859-1 of Windows-1252). "
                "De applicatie probeert automatisch de juiste encoding te detecteren, maar dit is niet gelukt.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Fout bij het lezen van het bestand: {str(e)}")
        st.stop()
    
    if df is not None:
        # Debug: Show what columns we actually have
        st.subheader("📊 Kolom overzicht")
        st.write("**Gevonden kolommen:**")
        for i, col in enumerate(df.columns):
            st.write(f"{i+1}. `{col}` (type: {df[col].dtype})")
        
        # Show first few rows
        st.subheader("👀 Eerste rijen")
        st.dataframe(df.head(3), use_container_width=True)
        
        # Analysis section
        st.subheader("🔍 Analyse")
        
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
        aantal_col = find_column(df, ['aantal', 'aantal_voorspeld', 'count'])
        school_col = find_column(df, ['school', 'instelling', 'schoolnaam'])
        brin_col = find_column(df, ['instellingserkenningscode', 'brin', 'erkenningscode'])
        leerweg_col = find_column(df, ['leertrajectmbo', 'leerweg', 'leertraject'])
        opleidingcode_col = find_column(df, ['opleidingcode', 'opleiding_code', 'code'])
        opleidingsnaam_col = find_column(df, ['opleidingsnaam', 'opleiding_naam', 'opleidingnaam', 'naam'])
        schooljaar_col = find_column(df, ['schooljaar', 'school_jaar', 'jaar'])
        
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
                weekly_data = df_filtered.groupby(week_col)[aantal_col].sum().reset_index()
                weekly_data = weekly_data.sort_values(week_col)
                weekly_data.columns = ['week', 'aantal']
                
                # Create bar chart
                st.bar_chart(
                    weekly_data.set_index('week'),
                    use_container_width=True
                )
                
                # Show summary statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Totaal voorspeld", f"{weekly_data['aantal'].sum():,}")
                with col2:
                    st.metric("Gemiddelde per week", f"{weekly_data['aantal'].mean():.1f}")
                with col3:
                    if len(weekly_data) > 0:
                        max_week = weekly_data.loc[weekly_data['aantal'].idxmax(), 'week']
                        st.metric("Week met meeste inschrijvingen", f"Week {max_week}")
            else:
                st.warning("⚠️ Geen data beschikbaar met de huidige filterinstellingen.")
                
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
    st.warning("⚠️ Geen bestand geüpload. Upload a.u.b. eerst een CSV of XLSX bestand via de File Upload pagina.")
    st.info("💡 Ga naar tabbblad 'Files' en selecteer een bestand onder 'selecteer bestandslocatie'.")