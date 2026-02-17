import streamlit as st
import pandas as pd
import pickle
import os
import tempfile
from io import BytesIO

# ---------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------
title = "Selecteer bestandslocatie(s)"
icon = ":material/file_upload:"

# ---------------------------------------
# UTILITY FUNCTIONS
# ---------------------------------------
def initialize_session_state():
    """Initialize session state variables if they don't exist"""
    # Separate storage for different file types
    if 'uploaded_files_beschrijving' not in st.session_state:
        st.session_state['uploaded_files_beschrijving'] = []  # List of file objects
    if 'file_metadata_beschrijving' not in st.session_state:
        st.session_state['file_metadata_beschrijving'] = []  # List of dicts with name, size, type
    if 'uploaded_files_prognose' not in st.session_state:
        st.session_state['uploaded_files_prognose'] = []  # List of file objects
    if 'file_metadata_prognose' not in st.session_state:
        st.session_state['file_metadata_prognose'] = []  # List of dicts with name, size, type

def clear_session_state(file_type=None):
    """Clear all file-related session state
    
    Args:
        file_type: 'beschrijving', 'prognose', or None (all)
    """
    if file_type is None:
        st.session_state['uploaded_files_beschrijving'] = []
        st.session_state['file_metadata_beschrijving'] = []
        st.session_state['uploaded_files_prognose'] = []
        st.session_state['file_metadata_prognose'] = []
    elif file_type == 'beschrijving':
        st.session_state['uploaded_files_beschrijving'] = []
        st.session_state['file_metadata_beschrijving'] = []
    elif file_type == 'prognose':
        st.session_state['uploaded_files_prognose'] = []
        st.session_state['file_metadata_prognose'] = []

def remove_file_from_session(file_name, file_type):
    """Remove a specific file from session state
    
    Args:
        file_name: Name of the file to remove
        file_type: 'beschrijving' or 'prognose'
    """
    uploaded_key = f'uploaded_files_{file_type}'
    metadata_key = f'file_metadata_{file_type}'
    
    if uploaded_key in st.session_state and metadata_key in st.session_state:
        # Find and remove file
        indices_to_remove = []
        for i, meta in enumerate(st.session_state[metadata_key]):
            if meta['file_name'] == file_name:
                indices_to_remove.append(i)
        
        # Remove in reverse order to maintain indices
        for i in sorted(indices_to_remove, reverse=True):
            if i < len(st.session_state[uploaded_key]):
                st.session_state[uploaded_key].pop(i)
            if i < len(st.session_state[metadata_key]):
                st.session_state[metadata_key].pop(i)

def save_file_to_temp(uploaded_file, file_type):
    """Save uploaded file to temporary location for persistence across refreshes
    
    Args:
        uploaded_file: The uploaded file object
        file_type: 'beschrijving' or 'prognose'
    """
    if uploaded_file is not None:
        # Create temp directory if it doesn't exist
        temp_dir = tempfile.gettempdir()
        app_temp_dir = os.path.join(temp_dir, 'streamlit_app_files')
        os.makedirs(app_temp_dir, exist_ok=True)
        
        # Create subdirectory for file type
        type_dir = os.path.join(app_temp_dir, file_type)
        os.makedirs(type_dir, exist_ok=True)
        
        # Save file to temp location (use unique name if file exists)
        base_name = uploaded_file.name
        temp_file_path = os.path.join(type_dir, base_name)
        counter = 1
        while os.path.exists(temp_file_path):
            name, ext = os.path.splitext(base_name)
            temp_file_path = os.path.join(type_dir, f"{name}_{counter}{ext}")
            counter += 1
        
        with open(temp_file_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        
        # Save metadata with file type
        metadata = {
            'file_name': uploaded_file.name,
            'file_size': uploaded_file.size,
            'temp_path': temp_file_path,
            'file_type': file_type
        }
        
        # Load existing metadata and add new file (per type)
        metadata_path = os.path.join(type_dir, 'files_metadata.pkl')
        all_metadata = []
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'rb') as f:
                    all_metadata = pickle.load(f)
            except:
                all_metadata = []
        
        # Check if file already exists in metadata
        if not any(m['file_name'] == uploaded_file.name and m['temp_path'] == temp_file_path for m in all_metadata):
            all_metadata.append(metadata)
            with open(metadata_path, 'wb') as f:
                pickle.dump(all_metadata, f)
        
        return temp_file_path, metadata

def load_files_from_temp(file_type=None):
    """Load files from temporary location if they exist
    
    Args:
        file_type: 'beschrijving', 'prognose', or None (all types)
    
    Returns:
        list: List of (temp_file_path, metadata) tuples
    """
    temp_dir = tempfile.gettempdir()
    app_temp_dir = os.path.join(temp_dir, 'streamlit_app_files')
    
    valid_files = []
    types_to_load = [file_type] if file_type else ['beschrijving', 'prognose']
    
    for ftype in types_to_load:
        type_dir = os.path.join(app_temp_dir, ftype)
        metadata_path = os.path.join(type_dir, 'files_metadata.pkl')
        
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'rb') as f:
                    all_metadata = pickle.load(f)
                
                # Return only files that still exist
                for metadata in all_metadata:
                    temp_file_path = metadata.get('temp_path')
                    if temp_file_path and os.path.exists(temp_file_path):
                        valid_files.append((temp_file_path, metadata))
            except:
                pass
    
    return valid_files

def clear_temp_file(file_name=None, file_type=None):
    """Clear temporary file(s) and metadata
    
    Args:
        file_name: If provided, only remove this specific file. Otherwise remove all.
        file_type: 'beschrijving', 'prognose', or None (all types)
    """
    temp_dir = tempfile.gettempdir()
    app_temp_dir = os.path.join(temp_dir, 'streamlit_app_files')
    
    types_to_clear = [file_type] if file_type else ['beschrijving', 'prognose']
    
    try:
        for ftype in types_to_clear:
            type_dir = os.path.join(app_temp_dir, ftype)
            metadata_path = os.path.join(type_dir, 'files_metadata.pkl')
            
            if not os.path.exists(metadata_path):
                continue
            
            if file_name:
                # Remove specific file
                with open(metadata_path, 'rb') as f:
                    all_metadata = pickle.load(f)
                
                # Find and remove file
                updated_metadata = []
                for metadata in all_metadata:
                    if metadata['file_name'] == file_name:
                        # Remove the temp file
                        temp_file_path = metadata.get('temp_path')
                        if temp_file_path and os.path.exists(temp_file_path):
                            try:
                                os.remove(temp_file_path)
                            except:
                                pass
                    else:
                        updated_metadata.append(metadata)
                
                # Save updated metadata or remove if empty
                if updated_metadata:
                    with open(metadata_path, 'wb') as f:
                        pickle.dump(updated_metadata, f)
                else:
                    os.remove(metadata_path)
            else:
                # Remove all files for this type
                with open(metadata_path, 'rb') as f:
                    all_metadata = pickle.load(f)
                
                # Remove all temp files
                for metadata in all_metadata:
                    temp_file_path = metadata.get('temp_path')
                    if temp_file_path and os.path.exists(temp_file_path):
                        try:
                            os.remove(temp_file_path)
                        except:
                            pass
                
                # Remove metadata file
                os.remove(metadata_path)
    except:
        pass
def get_uploaded_files(file_type=None):
    """Get uploaded files from session state or temp storage
    
    Args:
        file_type: 'beschrijving', 'prognose', or None (all types)
    
    Returns:
        list: List of tuples (file_object, file_name, file_size)
    """
    files = []
    
    types_to_get = [file_type] if file_type else ['beschrijving', 'prognose']
    
    # First check session state
    for ftype in types_to_get:
        uploaded_key = f'uploaded_files_{ftype}'
        metadata_key = f'file_metadata_{ftype}'
        
        if uploaded_key in st.session_state and metadata_key in st.session_state:
            for i, metadata in enumerate(st.session_state[metadata_key]):
                if i < len(st.session_state[uploaded_key]):
                    file_obj = st.session_state[uploaded_key][i]
                    if file_obj is not None:
                        files.append((file_obj, metadata['file_name'], metadata['file_size']))
    
    # If not enough in session state, try to load from temp storage
    temp_files = load_files_from_temp(file_type)
    for temp_file_path, metadata in temp_files:
        # Check if file is already in session state
        file_exists = False
        ftype = metadata.get('file_type', file_type)
        if ftype:
            metadata_key = f'file_metadata_{ftype}'
            if metadata_key in st.session_state:
                for meta in st.session_state[metadata_key]:
                    if meta['file_name'] == metadata['file_name']:
                        file_exists = True
                        break
        
        if not file_exists:
            # Create a file-like object from temp file
            class TempFileWrapper:
                def __init__(self, file_path, file_name, file_size):
                    self.file_path = file_path
                    self.name = file_name
                    self.size = file_size
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
                
                def seek(self, offset, whence=0):
                    """Seek to a position in the file
                    
                    Args:
                        offset: Offset to seek to
                        whence: 0 = from start, 1 = from current position, 2 = from end
                    """
                    if whence == 0:  # From start
                        self._position = max(0, min(offset, len(self._content)))
                    elif whence == 1:  # From current position
                        self._position = max(0, min(self._position + offset, len(self._content)))
                    elif whence == 2:  # From end
                        self._position = max(0, min(len(self._content) + offset, len(self._content)))
                    else:
                        raise ValueError("whence must be 0, 1, or 2")
                    return self._position
                
                def tell(self):
                    return self._position
                
                def seekable(self):
                    """Return True if the file is seekable"""
                    return True
                
                def getbuffer(self):
                    return self._content
            
            temp_file_obj = TempFileWrapper(temp_file_path, metadata['file_name'], metadata['file_size'])
            files.append((temp_file_obj, metadata['file_name'], metadata['file_size']))
    
    return files

def get_uploaded_file():
    """Get the first uploaded file (backward compatibility)
    
    Returns:
        tuple: (file_object, file_name, file_size) or (None, None, None) if no file uploaded
    """
    files = get_uploaded_files()
    if files:
        return files[0]  # Return first file for backward compatibility
    return None, None, None

def detect_encoding(file):
    """Detect the encoding of a file by trying common encodings
    
    Args:
        file: File-like object with bytes content
        
    Returns:
        str: Detected encoding or 'utf-8' as fallback
    """
    # Common encodings to try (most common first)
    encodings = ['utf-8', 'iso-8859-1', 'windows-1252', 'cp1252', 'latin-1']
    
    # Reset to beginning
    file.seek(0)
    
    # Try to read a sample (first 10000 bytes or entire file if smaller)
    sample = file.read(10000)
    file.seek(0)
    
    for encoding in encodings:
        try:
            sample.decode(encoding)
            return encoding
        except (UnicodeDecodeError, UnicodeError):
            continue
    
    # If all fail, return a safe default
    return 'iso-8859-1'

def read_excel_file(file_obj, file_name=None):
    """Read Excel file (XLSX or XLS) using pandas
    
    Args:
        file_obj: File-like object
        file_name: Optional file name
    
    Returns:
        pandas.DataFrame or None
    """
    try:
        # Reset file position
        file_obj.seek(0)
        
        # Read Excel file
        df = pd.read_excel(file_obj, engine='openpyxl')
        return df
    except Exception as e:
        st.error(f"Fout bij het lezen van Excel bestand: {str(e)}")
        return None

def read_csv_file(file_obj, file_name=None):
    """Read CSV file using pandas with automatic encoding detection
    
    Args:
        file_obj: File-like object
        file_name: Optional file name
    
    Returns:
        pandas.DataFrame or None
    """
    try:
        # Detect encoding
        file_obj.seek(0)
        encoding = detect_encoding(file_obj)
        
        # Reset and read first line to detect separator
        file_obj.seek(0)
        try:
            first_line_bytes = file_obj.read(1000)
            first_line = first_line_bytes.decode(encoding)
        except (UnicodeDecodeError, UnicodeError):
            file_obj.seek(0)
            first_line_bytes = file_obj.read(1000)
            first_line = first_line_bytes.decode('iso-8859-1')
            encoding = 'iso-8859-1'
        
        # Detect separator
        if ';' in first_line and first_line.count(';') > first_line.count(','):
            separator = ';'
        elif ',' in first_line:
            separator = ','
        else:
            separator = None
        
        # Reset and read CSV
        file_obj.seek(0)
        if separator:
            df = pd.read_csv(file_obj, sep=separator, encoding=encoding)
        else:
            df = pd.read_csv(file_obj, encoding=encoding)
        
        return df
    except Exception as e:
        # Fallback: manual parsing
        file_obj.seek(0)
        try:
            content = file_obj.read().decode(encoding)
        except (UnicodeDecodeError, UnicodeError):
            file_obj.seek(0)
            content = file_obj.read().decode('iso-8859-1')
        
        lines = content.strip().split('\n')
        if lines:
            headers = lines[0].split(';') if ';' in lines[0] else lines[0].split(',')
            data = []
            for line in lines[1:]:
                if line.strip():
                    row = line.split(';') if ';' in line else line.split(',')
                    data.append(row)
            return pd.DataFrame(data, columns=headers)
    else:
        return None
    
    return None

def read_data_file(file_obj=None, file_name=None):
    """Read data file (CSV or XLSX) - generic reader
    
    Args:
        file_obj: Optional file object to read
        file_name: Optional file name
    
    Returns:
        pandas.DataFrame or None
    """
    if file_obj is None:
        file, file_name, _ = get_uploaded_file()
        if file is None:
            return None
        file_obj = file
    
    if file_name is None:
        if hasattr(file_obj, 'name'):
            file_name = file_obj.name
        else:
            file_name = 'unknown'
    
    # Determine file type and read accordingly
    if file_name.endswith('.xlsx') or file_name.endswith('.xls'):
        return read_excel_file(file_obj, file_name)
    elif file_name.endswith('.csv'):
        return read_csv_file(file_obj, file_name)
    else:
        return None

def get_column_overview(file_obj=None, file_name=None):
    """Get column overview for uploaded file (CSV or XLSX)
    
    Args:
        file_obj: Optional file object to read
        file_name: Optional file name
    
    Returns:
        pandas.DataFrame with column information or None if no file
    """
    df = read_data_file(file_obj, file_name)
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
def save_file_location(uploaded_files, file_type):
    """Save uploaded file(s) to session state and temp storage for persistence
    
    Args:
        uploaded_files: Streamlit UploadedFile object or list of UploadedFile objects
        file_type: 'beschrijving' or 'prognose'
    """
    # Ensure it's a list
    if not isinstance(uploaded_files, list):
        uploaded_files = [uploaded_files] if uploaded_files is not None else []
    
    uploaded_key = f'uploaded_files_{file_type}'
    metadata_key = f'file_metadata_{file_type}'
    
    # Initialize if needed
    if uploaded_key not in st.session_state:
        st.session_state[uploaded_key] = []
    if metadata_key not in st.session_state:
        st.session_state[metadata_key] = []
    
    for uploaded_file in uploaded_files:
        if uploaded_file is not None:
            # Check if file already exists
            file_exists = False
            for meta in st.session_state[metadata_key]:
                if meta['file_name'] == uploaded_file.name:
                    file_exists = True
                    break
            
            if not file_exists:
                # Save to session state for immediate use
                st.session_state[uploaded_key].append(uploaded_file)
                st.session_state[metadata_key].append({
                    'file_name': uploaded_file.name,
                    'file_size': uploaded_file.size,
                    'file_type': file_type
                })
                
                # Also save to temp storage for persistence across refreshes
                save_file_to_temp(uploaded_file, file_type)

# Export functions for other modules
def get_beschrijving_files():
    """Get all files for 'Beschrijving aanmeldingen'
    
    Returns:
        list: List of tuples (file_object, file_name, file_size)
    """
    return get_uploaded_files('beschrijving')

def get_prognose_files():
#    """Get all files for 'Prognose inschrijvingen'
  
    """Get all files for 'Instroomprognose'
    
    Returns:
        list: List of tuples (file_object, file_name, file_size)
    """
    return get_uploaded_files('prognose')

# Initialize session state (always run, needed for imports)
initialize_session_state()

# Load files from temp storage if session state is empty (per type)
# This should also run when imported to ensure session state is populated
for file_type in ['beschrijving', 'prognose']:
    uploaded_key = f'uploaded_files_{file_type}'
    metadata_key = f'file_metadata_{file_type}'
    
    if not st.session_state[uploaded_key]:
        temp_files = load_files_from_temp(file_type)
        for temp_file_path, metadata in temp_files:
            # Create TempFileWrapper objects (similar to get_uploaded_files)
            class TempFileWrapper:
                def __init__(self, file_path, file_name, file_size):
                    self.file_path = file_path
                    self.name = file_name
                    self.size = file_size
                    self._position = 0
                    with open(self.file_path, 'rb') as f:
                        self._content = f.read()
                
                def read(self, size=-1):
                    if size == -1:
                        data = self._content[self._position:]
                        self._position = len(self._content)
                        return data
                    else:
                        end_pos = min(self._position + size, len(self._content))
                        data = self._content[self._position:end_pos]
                        self._position = end_pos
                        return data
                
                def readline(self):
                    remaining = self._content[self._position:]
                    if not remaining:
                        return b''
                    newline_pos = remaining.find(b'\n')
                    if newline_pos == -1:
                        line = remaining
                        self._position = len(self._content)
                        return line
                    else:
                        line = remaining[:newline_pos + 1]
                        self._position += len(line)
                        return line
                
                def seek(self, offset, whence=0):
                    """Seek to a position in the file
                    
                    Args:
                        offset: Offset to seek to
                        whence: 0 = from start, 1 = from current position, 2 = from end
                    """
                    if whence == 0:  # From start
                        self._position = max(0, min(offset, len(self._content)))
                    elif whence == 1:  # From current position
                        self._position = max(0, min(self._position + offset, len(self._content)))
                    elif whence == 2:  # From end
                        self._position = max(0, min(len(self._content) + offset, len(self._content)))
                    else:
                        raise ValueError("whence must be 0, 1, or 2")
                    return self._position
                
                def tell(self):
                    return self._position
                
                def seekable(self):
                    """Return True if the file is seekable"""
                    return True
                
                def getbuffer(self):
                    return self._content
            
            temp_file_obj = TempFileWrapper(temp_file_path, metadata['file_name'], metadata['file_size'])
            st.session_state[uploaded_key].append(temp_file_obj)
            st.session_state[metadata_key].append(metadata)

# Only show UI when this file is loaded as a page (not when imported)
# Check if this module is being imported via importlib (flag set by importing module)
if '_imported_via_importlib' not in globals():
    # File upload section
    st.header("📁 Upload Bestand")
    
    # Two drag & drop sections side by side
    col1, col2 = st.columns(2)
    
    # Beschrijving aanmeldingen upload
    with col1:
        st.subheader("📋 Beschrijving aanmeldingen")
        st.markdown(
            "Sleep in de onderstaande grijze box een bestand of klik op <strong><em>Browse files here</em></strong> om een bestand te selecteren. "
            "Het gaat om het bestand dat een resultaat is uit het volgende: "
            "https://github.com/cedanl/instroomprognose-mbo/tree/main.<br>"
            "Een voorbeeld van een dergelijk bestand (<strong><em>application_enriched_with_context_<span style='color: #9C27B0;'>xxx</span></em></strong>) "
            "is te vinden in de <a href='https://github.com/cedanl/student-instroom-mbo/tree/shirley' target='_blank'>repository</a> in de map "
            "<strong><em><span style='color: #9C27B0;'>data/voorbeeld_data</span></em></strong>",
            unsafe_allow_html=True
        )        
        uploaded_files_beschrijving = st.file_uploader(
            "Sleep bestanden hierheen of klik om te selecteren",
            type=['csv', 'xlsx', 'xls'],
            accept_multiple_files=True,
            key="uploader_beschrijving",
            help="Upload bestanden voor beschrijving aanmeldingen"
        )
        
        if uploaded_files_beschrijving:
            save_file_location(uploaded_files_beschrijving, 'beschrijving')
            file_names = [f.name for f in uploaded_files_beschrijving]
            st.success(f"✅ {len(uploaded_files_beschrijving)} bestand(en) toegevoegd voor Beschrijving aanmeldingen!")
            st.rerun()
        
        # Show count of uploaded files
        beschrijving_files = get_uploaded_files('beschrijving')
        if beschrijving_files:
            st.info(f"📁 {len(beschrijving_files)} bestand(en) geüpload voor Beschrijving aanmeldingen")

    # Instroomprognose upload
    with col2:
        st.subheader("📊 Instroomprognose")
        st.markdown(
           "Sleep in de onderstaande grijze box een bestand of klik op <strong><em>Browse files here</em></strong> om een of meerdere bestanden te selecteren. "
            "Het gaat om de bestanden die een resultaat zijn uit het volgende: "
            "<a href='https://github.com/cedanl/instroomprognose-mbo/tree/main' target='_blank'>https://github.com/cedanl/instroomprognose-mbo/tree/main</a>.<br>"
            " en uit <a href='https://github.com/cedanl/student-instroom-mbo/tree/amir' target='_blank'>https://github.com/cedanl/student-instroom-mbo/tree/amir</a>.<br>" 
            "Een voorbeeld van een dergelijk bestanden (<strong>Historische jaren:</strong> <em>inschrijvingen_summary_<span style='color: #9C27B0;'>xxx</span>.csv</em><br>"
            "<strong>Prognose:</strong> <em>predictions_mbo_<span style='color: #9C27B0;'>****</span>_week<span style='color: #9C27B0;'>##</span>.xlsx</em>)"
            " is te vinden in de <a href='https://github.com/cedanl/student-instroom-mbo/tree/shirley' target='_blank'>repository</a> in de map "
            "<strong><em><span style='color: #9C27B0;'>data/voorbeeld_data</span></em></strong>"
            ,
            unsafe_allow_html=True
        )
        uploaded_files_prognose = st.file_uploader(
            "Selecteer bestanden",
            type=['csv', 'xlsx', 'xls'],
            accept_multiple_files=True,
            key="uploader_prognose",
         #   help="Upload bestanden voor prognose inschrijvingen"
         help="Upload bestanden voor Instroomprognose"
        )
        
        if uploaded_files_prognose:
            save_file_location(uploaded_files_prognose, 'prognose')
            file_names = [f.name for f in uploaded_files_prognose]
         #   st.success(f"✅ {len(uploaded_files_prognose)} bestand(en) toegevoegd voor Prognose inschrijvingen!")
            st.success(f"✅ {len(uploaded_files_prognose)} bestand(en) toegevoegd voor Instroomprognose!")
            st.rerun()
        
        # Show count of uploaded files
        prognose_files = get_uploaded_files('prognose')
        if prognose_files:
         #   st.info(f"📁 {len(prognose_files)} bestand(en) geüpload voor Prognose inschrijvingen")
         st.info(f"📁 {len(prognose_files)} bestand(en) geüpload voor Instroomprognose")

    # Overview section
    st.header("📊 Overzicht geüploade bestanden")
    
    # Get all files for overview (both types)
    all_files_overview = get_uploaded_files()  # Get all types

    # Initialize file_info_map for use in detail section
    file_info_map = {}

    if all_files_overview:
        # Create overview table with file information for all files
        overview_data = []
        
        for file_type in ['beschrijving', 'prognose']:
            files = get_uploaded_files(file_type)
            for file_obj, file_name, file_size in files:
                file_info_map[file_name] = (file_obj, file_name, file_size, file_type)
        
        for file_obj, file_name, file_size, file_type in file_info_map.values():
            # Determine file format
            if file_name.endswith('.xlsx') or file_name.endswith('.xls'):
                file_format = 'Excel'
            elif file_name.endswith('.csv'):
                file_format = 'CSV'
            else:
                file_format = 'Onbekend'
            
            # Try to read file to get columns and rows
            # Get a fresh copy of the file content to avoid position issues
            num_columns = None
            num_rows = None
            
            try:
                # Get fresh copy of file content using getbuffer if available, otherwise read
                if hasattr(file_obj, 'getbuffer'):
                    file_content = file_obj.getbuffer()
                elif hasattr(file_obj, '_content'):
                    # TempFileWrapper has _content attribute
                    file_content = file_obj._content
                elif hasattr(file_obj, 'read'):
                    file_obj.seek(0)
                    file_content = file_obj.read()
                else:
                    file_content = None
                
                if file_content is None:
                    num_columns = None
                    num_rows = None
                else:
                    # Create a fresh BytesIO buffer from the content (make a copy)
                    if isinstance(file_content, bytes):
                        file_buffer = BytesIO(file_content)
                    else:
                        # If it's already a buffer-like object, create a copy
                        file_obj.seek(0)
                        if hasattr(file_obj, 'getbuffer'):
                            file_content = file_obj.getbuffer()
                        else:
                            file_content = file_obj.read()
                        file_buffer = BytesIO(file_content)
                    
                    # Determine file type and read accordingly
                    if file_name.endswith('.xlsx') or file_name.endswith('.xls'):
                        # Read Excel file - ensure we have bytes content
                        if isinstance(file_content, bytes):
                            file_buffer = BytesIO(file_content)
                        else:
                            # Fallback: try to get bytes again
                            file_obj.seek(0)
                            if hasattr(file_obj, 'getbuffer'):
                                file_content = file_obj.getbuffer()
                            elif hasattr(file_obj, '_content'):
                                file_content = file_obj._content
                            else:
                                file_content = file_obj.read()
                            file_buffer = BytesIO(file_content)
                        
                        file_buffer.seek(0)
                        try:
                            df = pd.read_excel(file_buffer, engine='openpyxl', sheet_name=0)  # Read first sheet
                            # Verify we got a valid DataFrame
                            if df is not None and isinstance(df, pd.DataFrame):
                                # Remove empty rows that might be at the end
                                df = df.dropna(how='all')
                                num_columns = int(df.shape[1])
                                num_rows = int(df.shape[0])
                            else:
                                num_columns = None
                                num_rows = None
                        except Exception as excel_error:
                            # Try again without sheet_name parameter
                            try:
                                file_buffer.seek(0)
                                df = pd.read_excel(file_buffer, engine='openpyxl')
                                if df is not None and isinstance(df, pd.DataFrame):
                                    df = df.dropna(how='all')
                                    num_columns = int(df.shape[1])
                                    num_rows = int(df.shape[0])
                                else:
                                    num_columns = None
                                    num_rows = None
                            except:
                                num_columns = None
                                num_rows = None
                            
                    elif file_name.endswith('.csv'):
                        # Detect encoding from a fresh buffer
                        encoding_buffer = BytesIO(file_content if isinstance(file_content, bytes) else file_content)
                        encoding = detect_encoding(encoding_buffer)
                        
                        # Read first line to detect separator
                        encoding_buffer.seek(0)
                        try:
                            first_line_bytes = encoding_buffer.read(1000)
                            first_line = first_line_bytes.decode(encoding)
                        except (UnicodeDecodeError, UnicodeError):
                            encoding_buffer.seek(0)
                            first_line_bytes = encoding_buffer.read(1000)
                            first_line = first_line_bytes.decode('iso-8859-1')
                            encoding = 'iso-8859-1'
                        
                        # Detect separator
                        if ';' in first_line and first_line.count(';') > first_line.count(','):
                            separator = ';'
                        elif ',' in first_line:
                            separator = ','
                        else:
                            separator = None
                        
                        # Read CSV from buffer
                        file_buffer.seek(0)
                        try:
                            if separator:
                                df = pd.read_csv(file_buffer, sep=separator, encoding=encoding)
                            else:
                                df = pd.read_csv(file_buffer, encoding=encoding)
                            
                            if df is not None and isinstance(df, pd.DataFrame):
                                num_columns = int(df.shape[1])
                                num_rows = int(df.shape[0])
                            else:
                                num_columns = None
                                num_rows = None
                        except Exception as csv_error:
                            num_columns = None
                            num_rows = None
                    else:
                        num_columns = None
                        num_rows = None
                    
            except Exception as e:
                # If reading fails, set to None
                num_columns = None
                num_rows = None
            
            # Format values for display - ensure they are integers
            # Explicitly convert to Python int to avoid any numpy/pandas type issues
            if num_columns is not None:
                try:
                    cols_display = int(num_columns)
                except (ValueError, TypeError):
                    cols_display = 'N/A'
            else:
                cols_display = 'N/A'
                
            if num_rows is not None:
                try:
                    rows_display = int(num_rows)
                except (ValueError, TypeError):
                    rows_display = 'N/A'
            else:
                rows_display = 'N/A'
            
            # Verify the values before adding to overview
         #   type_label = 'Beschrijving aanmeldingen' if file_type == 'beschrijving' else 'Prognose inschrijvingen'
            type_label = 'Beschrijving aanmeldingen' if file_type == 'beschrijving' else 'Instroomprognose'
            overview_data.append({
                'Type upload': type_label,
                'Formaat': str(file_format),  # Kortere naam
                'Bestandsgrootte': f"{file_size / 1024:.2f} KB",  # Kortere naam
                '# Kolommen': cols_display,  # Kortere naam
                '# Rijen': rows_display,  # Kortere naam    
                'Bestandsnaam': str(file_name)
            })
        
        # Display overview table
        if overview_data:
            overview_df = pd.DataFrame(overview_data)
            # Reorder columns for better visibility: most important first
            column_order = ['Type upload', 'Formaat', 'Bestandsgrootte', '# Kolommen', '# Rijen', 'Bestandsnaam']   
            overview_df = overview_df[column_order]
            
            # Use CSS to make table more compact and fit better
            st.markdown("""
            <style>
            .dataframe {
                font-size: 0.85em;
            }
            .dataframe th {
                white-space: nowrap;
                padding: 8px 4px !important;
            }
            .dataframe td {
                white-space: nowrap;
                padding: 8px 4px !important;
            }
            </style>
            """, unsafe_allow_html=True)
            
            st.dataframe(overview_df, use_container_width=True, hide_index=True)
        else:
            st.info("Geen bestanden geüpload. Upload bestanden via de secties hierboven.")
    else:
        st.info("📤 Upload bestanden via de drag & drop secties hierboven om te beginnen")

    # Detail section: eerst Type upload kiezen, dan bestand selecteren
    if all_files_overview and len(file_info_map) > 0:
        st.header("📄 Bestandsdetails")
        
        # Groepeer bestanden per type
        files_by_type = {'beschrijving': [], 'prognose': []}
        type_labels = {'beschrijving': 'Beschrijving aanmeldingen', 'prognose': 'Instroomprognose'}
        for file_obj, file_name, file_size, file_type in file_info_map.values():
            if file_type in files_by_type:
                files_by_type[file_type].append((file_obj, file_name, file_size))
        
        # Alleen types tonen die bestanden hebben
        available_types = [(ftype, type_labels[ftype]) for ftype in ['beschrijving', 'prognose'] 
                          if files_by_type[ftype]]
        
        if not available_types:
            st.info("Geen bestanden om details van te tonen.")
        else:
            # Stap 1: Kies Type upload
            selected_type_label = st.selectbox(
                "**Type upload**",
                options=[label for _, label in available_types],
                key="detail_type_select"
            )
            selected_type = next(ftype for ftype, label in available_types if label == selected_type_label)
            
            # Stap 2: Kies bestand uit filterlijst
            files_of_type = files_by_type[selected_type]
            file_options = [f[1] for f in files_of_type]  # file names
            
            selected_file_name = st.selectbox(
                "**Selecteer bestand**",
                options=file_options,
                key=f"detail_file_select_{selected_type}"
            )
            
            # Toon overzicht van geselecteerd bestand
            if selected_file_name:
                file_obj, _, file_size = next((f for f in files_of_type if f[1] == selected_file_name))
                type_label = type_labels[selected_type]
                
                col1, col2 = st.columns([10, 1])
                with col1:
                    st.subheader(f"📄 {selected_file_name} ({type_label})")
                with col2:
                    if st.button("🗑️", key=f"delete_detail_{selected_type}_{selected_file_name}", help=f"Verwijder {selected_file_name}"):
                        remove_file_from_session(selected_file_name, selected_type)
                        clear_temp_file(selected_file_name, selected_type)
                        st.success(f"✅ Bestand '{selected_file_name}' verwijderd!")
                        st.rerun()
                
                df = read_data_file(file_obj, selected_file_name)
                if df is not None:
                    st.markdown("##### 📊 Kolom overzicht")
                    overview_df = get_column_overview(file_obj, selected_file_name)
                    if overview_df is not None:
                        st.dataframe(overview_df, use_container_width=True)
                    
                    st.markdown("##### 👀 Voorbeeld van inhoud")
                    st.dataframe(df.head(5), use_container_width=True)
                else:
                    st.error(f"Kon bestand '{selected_file_name}' niet lezen")
