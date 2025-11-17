import streamlit as st

# Import utility functions from the frontend Bestanden module
try:
    # Try relative import first (works when run as part of the package)
    from ..frontend.Bestanden.selecteer_bestandslocatie import get_uploaded_file, read_data_file
except ImportError:
    # Fallback to absolute import (works when run directly or in different contexts)
    import sys
    import os
    # Add the src directory to the path
    src_path = os.path.join(os.path.dirname(__file__), '..', '..')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    from frontend.Bestanden.selecteer_bestandslocatie import get_uploaded_file, read_data_file  # type: ignore

# Get file info
file, file_name, file_size = get_uploaded_file()
if file:
    st.write(f"Analyzing: {file_name}")
    
    # Read file directly (CSV or XLSX)
    df = read_data_file()
    if df is not None:
        # Do your analysis here
        st.dataframe(df.head())