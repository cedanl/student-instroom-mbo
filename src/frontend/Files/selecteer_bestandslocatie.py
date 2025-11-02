import streamlit as st
import pandas as pd
import pickle
import os
import tempfile

# ---------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------
title = "Selecteer bestandslocatie"
icon = ":material/file_upload:"

# ---------------------------------------
# UTILITY FUNCTIONS
# ---------------------------------------
def initialize_session_state():
    """Initialize session state variables if they don't exist"""
    if 'uploaded_file' not in st.session_state:
        st.session_state['uploaded_file'] = None
    if 'file_name' not in st.session_state:
        st.session_state['file_name'] = None
    if 'file_size' not in st.session_state:
        st.session_state['file_size'] = None

def clear_session_state():
    """Clear all file-related session state"""
    st.session_state.pop('uploaded_file', None)
    st.session_state.pop('file_name', None)
    st.session_state.pop('file_size', None)

def save_file_to_temp(uploaded_file):
    """Save uploaded file to temporary location for persistence across refreshes"""
    if uploaded_file is not None:
        # Create temp directory if it doesn't exist
        temp_dir = tempfile.gettempdir()
        app_temp_dir = os.path.join(temp_dir, 'streamlit_app_files')
        os.makedirs(app_temp_dir, exist_ok=True)
        
        # Save file to temp location
        temp_file_path = os.path.join(app_temp_dir, uploaded_file.name)
        with open(temp_file_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        
        # Save metadata
        metadata = {
            'file_name': uploaded_file.name,
            'file_size': uploaded_file.size,
            'temp_path': temp_file_path
        }
        
        metadata_path = os.path.join(app_temp_dir, 'file_metadata.pkl')
        with open(metadata_path, 'wb') as f:
            pickle.dump(metadata, f)
        
        return temp_file_path, metadata

def load_file_from_temp():
    """Load file from temporary location if it exists"""
    temp_dir = tempfile.gettempdir()
    app_temp_dir = os.path.join(temp_dir, 'streamlit_app_files')
    metadata_path = os.path.join(app_temp_dir, 'file_metadata.pkl')
    
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, 'rb') as f:
                metadata = pickle.load(f)
            
            temp_file_path = metadata['temp_path']
            if os.path.exists(temp_file_path):
                return temp_file_path, metadata
        except:
            pass
    
    return None, None

def clear_temp_file():
    """Clear temporary file and metadata"""
    temp_dir = tempfile.gettempdir()
    app_temp_dir = os.path.join(temp_dir, 'streamlit_app_files')
    
    try:
        # Remove metadata
        metadata_path = os.path.join(app_temp_dir, 'file_metadata.pkl')
        if os.path.exists(metadata_path):
            os.remove(metadata_path)
        
        # Remove temp files
        if os.path.exists(app_temp_dir):
            for file in os.listdir(app_temp_dir):
                if file != 'file_metadata.pkl':
                    os.remove(os.path.join(app_temp_dir, file))
    except:
        pass
def get_uploaded_file():
    """Get the uploaded file from session state or temp storage for analysis
    
    Returns:
        tuple: (file_object, file_name, file_size) or (None, None, None) if no file uploaded
    """
    # First check session state
    if 'uploaded_file' in st.session_state and st.session_state['uploaded_file'] is not None:
        return st.session_state['uploaded_file'], st.session_state['file_name'], st.session_state['file_size']
    
    # If not in session state, try to load from temp storage
    temp_file_path, metadata = load_file_from_temp()
    if temp_file_path and metadata:
        # Create a file-like object from temp file
        class TempFileWrapper:
            def __init__(self, file_path):
                self.file_path = file_path
                self.name = metadata['file_name']
                self.size = metadata['file_size']
                self._position = 0
                # Pre-load file content into memory for proper file-like behavior
                with open(self.file_path, 'rb') as f:
                    self._content = f.read()
            
            def read(self, size=-1):
                if size == -1:
                    # Read all remaining content from current position
                    data = self._content[self._position:]
                    self._position = len(self._content)
                    return data
                else:
                    # Read specified number of bytes
                    end_pos = min(self._position + size, len(self._content))
                    data = self._content[self._position:end_pos]
                    self._position = end_pos
                    return data
            
            def readline(self):
                # Find the next newline from current position
                remaining = self._content[self._position:]
                if not remaining:
                    return b''
                
                # Find first newline
                newline_pos = remaining.find(b'\n')
                if newline_pos == -1:
                    # No newline found, return remaining content
                    line = remaining
                    self._position = len(self._content)
                    return line
                else:
                    # Include the newline character
                    line = remaining[:newline_pos + 1]
                    self._position += len(line)
                    return line
            
            def seek(self, position):
                self._position = max(0, min(position, len(self._content)))
            
            def tell(self):
                return self._position
            
            def getbuffer(self):
                return self._content
        
        temp_file_obj = TempFileWrapper(temp_file_path)
        return temp_file_obj, metadata['file_name'], metadata['file_size']
    
    return None, None, None

def read_csv_file():
    """Read the uploaded CSV file as a DataFrame
    
    Returns:
        pandas.DataFrame or None if no CSV file uploaded
    """
    file, file_name, file_size = get_uploaded_file()
    if file and file_name and file_name.endswith('.csv'):
        file.seek(0)  # Reset file pointer
        
        # Read first line to detect separator
        first_line = file.readline().decode('utf-8')
        file.seek(0)  # Reset file pointer
        
        # Detect separator based on first line
        if ';' in first_line and first_line.count(';') > first_line.count(','):
            separator = ';'
        elif ',' in first_line:
            separator = ','
        else:
            separator = None
        
        try:
            if separator:
                return pd.read_csv(file, sep=separator)
            else:
                # Try auto-detection
                return pd.read_csv(file)
        except Exception as e:
            # If all else fails, try reading as text and splitting manually
            file.seek(0)
            content = file.read().decode('utf-8')
            lines = content.strip().split('\n')
            if lines:
                headers = lines[0].split(';') if ';' in lines[0] else lines[0].split(',')
                data = []
                for line in lines[1:]:
                    if line.strip():
                        row = line.split(';') if ';' in line else line.split(',')
                        data.append(row)
                return pd.DataFrame(data, columns=headers)
    return None

def get_column_overview():
    """Get column overview for uploaded CSV file
    
    Returns:
        pandas.DataFrame with column information or None if no CSV file
    """
    df = read_csv_file()
    if df is not None:
        # Create overview DataFrame
        overview_data = []
        for col in df.columns:
            overview_data.append({
                'Kolom': col,
                'Datatype': str(df[col].dtype),
                'Aantal waarden': len(df[col]),
                'Ontbrekende waarden': df[col].isnull().sum(),
                'Unieke waarden': df[col].nunique()
            })
        return pd.DataFrame(overview_data)
    return None

# ---------------------------------------
# PAGE ELEMENTS
# ---------------------------------------
def save_file_location(uploaded_file):
    """Save uploaded file to session state and temp storage for persistence
    
    Args:
        uploaded_file: Streamlit UploadedFile object
    """
    if uploaded_file is not None:
        # Save to session state for immediate use
        st.session_state['uploaded_file'] = uploaded_file
        st.session_state['file_name'] = uploaded_file.name
        st.session_state['file_size'] = uploaded_file.size
        
        # Also save to temp storage for persistence across refreshes
        save_file_to_temp(uploaded_file)

# Initialize session state
initialize_session_state()

# File upload section
st.header("📁 Upload Bestand")

# Check if file is already available (session state or temp storage)
file, file_name, file_size = get_uploaded_file()
if file:
    # Determine if file is from session state or temp storage
    is_from_temp = 'uploaded_file' not in st.session_state or st.session_state['uploaded_file'] is None
    
    if is_from_temp:
        st.success(f"✅ Bestand '{file_name}' is hersteld uit geheugen!")
        st.info("💾 Dit bestand was opgeslagen en is automatisch hersteld na refresh.")
    else:
        st.success(f"✅ Bestand '{file_name}' is al geüpload!")
    
    # Show current file info
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Bestandsnaam", file_name)
    with col2:
        st.metric("Bestandsgrootte", f"{file_size:,} bytes")
    
    # Option to upload new file
    st.subheader("🔄 Nieuw bestand uploaden")
    uploaded_file = st.file_uploader("Kies een nieuw bestand", key="new_file_uploader")
    
    if uploaded_file:
        save_file_location(uploaded_file)
        st.success(f"✅ Nieuw bestand '{uploaded_file.name}' geüpload!")
        st.rerun()
    
    # Option to clear current file
    if st.button("🗑️ Huidig bestand verwijderen"):
        clear_session_state()
        clear_temp_file()
        st.success("✅ Bestand verwijderd!")
        st.rerun()
        
else:
    # No file uploaded yet
    uploaded_file = st.file_uploader("Kies een bestand")
    
    if uploaded_file:
        save_file_location(uploaded_file)
        st.success(f"✅ Bestand '{uploaded_file.name}' succesvol geüpload!")
        st.rerun()
    
 

     





    # Get file info
file, file_name, file_size = get_uploaded_file()
if file:
   # st.success(f"✅ Analyse {file_name}")
    
    # Read CSV directly
    df = read_csv_file()
    if df is not None:
        # File information
        st.subheader("📋 Inhoud geselecteerde bestand")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Bestandsnaam", file_name)
        with col2:
            st.metric("Bestandsgrootte", f"{file_size:,} bytes")
        with col3:
            st.metric("Status", "Klaar voor analyse")
        
        # Column overview
        st.subheader("📊 Kolom overzicht")
        overview_df = get_column_overview()
        if overview_df is not None:
            st.dataframe(overview_df, use_container_width=True)
            
            # Additional statistics
            st.subheader("📈 Samenvatting")
            col_stats1, col_stats2, col_stats3 = st.columns(3)
            with col_stats1:
                st.metric("Aantal rijen", f"{len(df):,}")
            with col_stats2:
                st.metric("Aantal kolommen", len(df.columns))
            with col_stats3:
                st.metric("Geheugengebruik", f"{df.memory_usage(deep=True).sum() / 1024:.1f} KB")
        
        # Data preview
        st.subheader("👀 Voorbeeld van inhoud")
        st.dataframe(df.head(5), use_container_width=True)
        
        # Analysis section (placeholder)
            # Simple file info only
        st.info("Bestand is klaar voor het maken van een prognose. Gebruik de Module 'prognose Inschrijvingen' om de kolommen te bekijken.")
       # st.info("Volgt later...")


        
    else:
        st.error("Kon bestand niet lezen")
