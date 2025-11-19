"""
MBO Prognose - Main Entry Point
Handles enrollment predictions for MBO programs using historical data.
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

from utils.load_data import load_individual, load_latest, load_cumulative
from scripts.models.individual import Individual

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_configuration(config_path: Path) -> dict:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='MBO enrollment prediction model')
    parser.add_argument('-y', '--year', type=int,
                      help='Year to predict for (default: current year)')
    parser.add_argument('-w', '--week', type=int,
                      help='Week number to predict for (default: current week)')
    return parser.parse_args()

def get_current_year_week():
    """Get current year and week number."""
    current_date = datetime.now()
    return current_date.year, current_date.isocalendar().week

def main():
    """Main execution function."""
    try:
        # Parse arguments
        args = parse_args()
        current_year, current_week = get_current_year_week()
        
        target_year = args.year if args.year is not None else current_year
        target_week = args.week if args.week is not None else current_week
        
        logger.info(f"Target prediction: Year {target_year}, Week {target_week}")

        # Load configuration
        config_path = Path('configuration/configuration.yaml')
        config = load_configuration(config_path)
        logger.info("Configuration loaded successfully")

        # Add defaults for missing configuration sections
        if "filters" not in config:
            config["filters"] = {}
        if "filtering" not in config:
            config["filtering"] = {
                "programme": None,
                "herkomst": None,
                "examentype": None
            }
        config.setdefault("individual_start_year", 2020)
        config.setdefault("numerus_fixus", {})

        # Load data
        logger.info("Loading data...")
        individual_data = load_individual()
        latest_data = load_latest()
        cumulative_data = load_cumulative()
        distances = None  # MBO data doesn't use distances

        logger.info(f"Loaded data with {len(individual_data)} records")

        # Initialize Individual model
        logger.info("Initializing prediction model...")
        individual_model = Individual(
            data_individual=individual_data,
            data_distances=distances,
            data_latest=latest_data,
            configuration=config,
            data_cumulative=cumulative_data
        )

        # Run prediction loop
        logger.info(f"Running predictions for year {target_year}, week {target_week}...")
        predictions = individual_model.run_full_prediction_loop(
            predict_year=target_year,
            predict_week=target_week,
            write_file=True,
            verbose=True,
            args=None
        )

        logger.info(f"Predictions completed: {len(predictions)} rows generated")

    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
