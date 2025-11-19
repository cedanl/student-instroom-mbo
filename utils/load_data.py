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
            "path_individual": str(Path(ROOT_PATH) / "data/input" / "applications_enriched_with_context.csv"),
            "path_student_count": str(Path(ROOT_PATH) / "data/input" / "aanmeldingen_oktober_2024.csv")
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
