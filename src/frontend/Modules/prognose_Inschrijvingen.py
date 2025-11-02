import streamlit as st
import pandas as pd

# Import utility functions from the Files module
try:
    # Try relative import first (works when run as part of the package)
    from ..Files.selecteer_bestandslocatie import get_uploaded_file, read_csv_file, get_column_overview
except ImportError:
    # Fallback to absolute import (works when run directly or in different contexts)
    import sys
    import os
    # Add the src directory to the path
    src_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    from frontend.Files.selecteer_bestandslocatie import get_uploaded_file, read_csv_file, get_column_overview  # type: ignore

# Page title
st.title("📊 Prognose Inschrijvingen")

# Get file info
file, file_name, file_size = get_uploaded_file()
if file:
    st.success(f"✅ Analyse {file_name}")
    
    
    # Read CSV directly
    df = read_csv_file()
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
        
        # Bar chart: Week vs Aantal voorspeld
        if 'week' in df.columns and 'aantal_voorspeld' in df.columns:
            st.subheader("📊 Voorspellingen per week")
            
            # Group by week and sum aantal_voorspeld
            weekly_data = df.groupby('week')['aantal_voorspeld'].sum().reset_index()
            weekly_data = weekly_data.sort_values('week')
            
            # Create bar chart
            st.bar_chart(
                weekly_data.set_index('week'),
                use_container_width=True
            )
            
            # Show summary statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Totaal voorspeld", f"{weekly_data['aantal_voorspeld'].sum():,}")
            with col2:
                st.metric("Gemiddelde per week", f"{weekly_data['aantal_voorspeld'].mean():.1f}")
            with col3:
                st.metric("Week met meeste inschrijvingen", f"Week {weekly_data.loc[weekly_data['aantal_voorspeld'].idxmax(), 'week']}")
                
        else:
            st.warning("⚠️ Kolommen 'week' en/of 'aantal_voorspeld' niet gevonden in de data.")
            st.info("Beschikbare kolommen: " + ", ".join(df.columns.tolist()))
        
    else:
        st.error("Kon bestand niet lezen")
else:
    st.warning("⚠️ Geen bestand geüpload. Upload a.u.b. eerst een CSV-bestand via de File Upload pagina.")
    st.info("💡 Ga naar tabbblad 'Files' en selecteer een bestand onder 'selecteer bestandslocatie'.")