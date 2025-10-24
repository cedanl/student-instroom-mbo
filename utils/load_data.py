# load_data.py
import os
import yaml
import pandas as pd
from pathlib import Path
from joblib import Memory
from dotenv import load_dotenv
import logging
from typing import Optional, Dict

# --- Environment and logging setup ---
load_dotenv()
logger = logging.getLogger(__name__)

# --- Configure disk cache ---
ROOT_PATH = os.getenv("ROOT_PATH") or str(Path(__file__).resolve().parents[1])
CACHE_DIR = Path(ROOT_PATH) / "cache_dir"
memory = Memory(CACHE_DIR, verbose=0)

# --- Load paths configuration ---
def get_config_paths() -> Dict[str, str]:
    """Get paths from configuration file"""
    config_path = Path(ROOT_PATH) / "configuration" / "paths.json"
    if not config_path.exists():
        logger.warning(f"No paths.json found at {config_path}, using defaults")
        return {
            "path_individual": str(Path(ROOT_PATH) / "input" / "applications_enriched_with_context_DEMO.csv"),
            "path_student_count": str(Path(ROOT_PATH) / "input" / "aanmeldingen_oktober_2024.csv")
        }
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config.get("paths", {})
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return {}

# Get paths from configuration
paths = get_config_paths()


# Function removed: Using simplified path handling from get_config_paths()


# --- Loader functions ---
@memory.cache
def load_individual() -> Optional[pd.DataFrame]:
    """Load the enriched applications data for predictions."""
    path = paths.get("path_individual")
    if not path:
        logger.error("No path_individual configured")
        return None
        
    logger.debug(f"Loading applications data from {path}")
    try:
        df = pd.read_csv(path, low_memory=False, dtype={
            'id': str,
            'createdat': str,
            'ketenid': str,
            'postcodecijfers': str,
            'instellingserkenningscode': str,
            'onderwijsaanbiedercode': str,
            'onderwijslocatiecode': str,
            'opleidingcode': str,
            'leertrajectmbo': str,
            'status': str,
            'schooljaar': str
        })
        logger.info(f"Successfully loaded applications data: {len(df)} rows")
        return df
    except Exception as e:
        logger.error(f"Error loading applications data: {str(e)}")
        return None

@memory.cache
def load_student_count() -> Optional[pd.DataFrame]:
    """Load actual enrollment numbers from October 2024."""
    path = paths.get("path_student_count")
    if not path:
        logger.error("No path_student_count configured")
        return None
        
    logger.debug(f"Loading student count data from {path}")
    try:
        df = pd.read_csv(path)
        logger.info(f"Successfully loaded student count data: {len(df)} rows")
        return df
    except Exception as e:
        logger.error(f"Error loading student count data: {str(e)}")
        return None

    # Load with mixed type handling and explicit data types
    try:
        df = pd.read_csv(path, low_memory=False, dtype={
            'id': str,
            'version': str,
            'createdat': str,
            'lastmodifiedat': str,
            'createdby': str,
            'lastmodifiedby': str,
            'ketenid': str,
            'bsnhash': str,
            'leeftijdscategorie': str,
            'postcodecijfers': str,
            'instellingserkenningscode': str,
            'onderwijsaanbiedercode': str,
            'onderwijslocatiecode': str,
            'opleidingcode': str,
            'leertrajectmbo': str,
            'startmoment': str,
            'status': str,
            'begindatum': str,
            'schooljaar': str,
            'statussource': str,
            'caketenid': str
        })
        logger.debug(f"Successfully loaded data from {path}")
        logger.debug(f"Columns found: {df.columns.tolist()}")
        return df
    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        return None
    if df is None:
        logger.warning(f"Could not load individual file at: {path}")
        return None

    # If this appears to be an MBO export (has `schooljaar`), map relevant columns to the
    # field names expected by the university prediction pipeline so the rest of the code
    # can operate with minimal changes.
    cols = [c.lower() for c in df.columns]
    if "schooljaar" in cols:
        # Normalize column names to lowercase for easier access
        df.columns = [c.lower() for c in df.columns]

        # Basic mappings
        df = df.rename(columns={
            "schooljaar": "Collegejaar",
            "opleidingcode": "Opleiding",
            "leertrajectmbo": "Leertraject",
            "instellingserkenningscode": "Instellingscode",
            "ketenid": "Sleutel",
            "begindatum": "Datum Verzoek Inschr",
            "startmoment": "Datum Verzoek Inschr",
            "status": "Inschrijfstatus",
        })

        # Ensure expected columns exist (with sensible defaults)
        # Convert Collegejaar to numeric (keep 0 values as-is) and ensure consistent types
        df['Collegejaar'] = pd.to_numeric(df['Collegejaar'], errors='coerce').fillna(0).astype(int)

        # Map programme and institution identifiers into names used by the rest of the pipeline
        df['Croho groepeernaam'] = df.get('Opleiding', df.get('opleidingcode', '')).astype(str)
        df['Faculteit'] = 'MBO'
        # Set Examentype to a compatible value so downstream code doesn't drop rows.
        # This is a pragmatic choice: university pipeline expects values like 'Bachelor'.
        df['Examentype'] = 'Bachelor'
        df['Herkomst'] = 'NL'

        # Date columns: use the provided timestamp for 'Datum Verzoek Inschr' and construct
        # an 'Ingangsdatum' with 01-09-YYYY so the intake filtering in preprocess keeps rows.
        if 'begindatum' in df.columns:
            col = df['begindatum']
            if isinstance(col, pd.DataFrame):
                col = col.iloc[:, 0]
            df['Datum Verzoek Inschr'] = pd.to_datetime(col, errors='coerce')
            df['Ingangsdatum'] = df['Datum Verzoek Inschr'].dt.strftime('01-09-%Y').fillna('')
        else:
            df['Datum Verzoek Inschr'] = pd.NaT
            df['Ingangsdatum'] = ''

        # Create the minimal set of columns expected later in the individual pipeline
        df['Datum intrekking vooraanmelding'] = pd.NA
        df['Sleutel'] = df.get('Sleutel', df.get('ketenid', df.get('bsnhash', pd.NA)))
        df['Aantal studenten'] = 1
        df['Sleutel_count'] = 1
        df['is_numerus_fixus'] = 0
        df['Afstand'] = 0.0
        df['Deadlineweek'] = False
        df['Is eerstejaars croho opleiding'] = 1
        df['Is hogerejaars'] = 0
        df['BBC ontvangen'] = 0
        df['Hoofdopleiding'] = 'ja'
        df['Nationaliteit'] = df.get('nationaliteit', 'Nederlandse')
        df['EER'] = df.get('eer', 'J')

        # Make sure column names use the exact casing used by the old pipeline (some code checks exact names)
        df.columns = [c if any(ch.isupper() for ch in c) else c.capitalize() if c.islower() else c for c in df.columns]

        # Return the dataframe with mapped columns (the rest of the pipeline will further process it)
        return df

@memory.cache
def load_latest() -> Optional[pd.DataFrame]:
    """For MBO data, we use the same file as individual data"""
    logger.debug("Loading latest dataset (same as individual for MBO)...")
    return load_individual()

@memory.cache
def load_student_numbers_first_years() -> Optional[pd.DataFrame]:
    logger.debug("Loading first-year student numbers dataset...")
    return _load_file(_paths['input']['path_student_count_first_years'], file_type="excel")

@memory.cache
def load_oktober_file() -> Optional[pd.DataFrame]:
    logger.debug("Loading oktober file...")
    return _load_file(_other_paths['path_october'], file_type="excel")


# --- Public API ---
@memory.cache
def load_latest() -> Optional[pd.DataFrame]:
    """For MBO data, we use the applications data"""
    return load_individual()

@memory.cache
def load_cumulative() -> Optional[pd.DataFrame]:
    """For MBO data, we use the applications data"""
    return load_individual()

def load_data() -> Dict[str, Optional[pd.DataFrame]]:
    """Load all required datasets using cached loaders."""
    return {
        "individual": load_individual(),
        "latest": load_latest(),
        "cumulative": load_cumulative(),
        "student_count": load_student_count(),
    }

def clear_cache():
    """Clear the disk cache"""
    memory.clear(warn=False)

if __name__ == "__main__":
    clear_cache()