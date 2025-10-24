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

from utils.load_data import load_mbo_data
from scripts.models.individual import predict_individual

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

        # Load data
        df = load_mbo_data()
        logger.info(f"Loaded data with {len(df)} records")

        # Check if we have actual data for the target year and week
        if len(df) > 0:
            target_data = df[
                (df['jaar'] == target_year) & 
                (df['week'] == target_week)
            ]
            if target_data.empty:
                logger.error(f"No actual data found for Year {target_year}, Week {target_week}")
                sys.exit(1)

        # Apply filters from configuration
        for filter_name, filter_config in config.get('filters', {}).items():
            if filter_config.get('enabled', False):
                filter_values = filter_config.get('values', [])
                if filter_values:  # Only apply if values are specified
                    df = df[df[filter_name].isin(filter_values)]
                    logger.info(f"Applied {filter_name} filter, {len(df)} records remaining")

        # Generate predictions
        predictions = predict_individual(df)
        logger.info("Predictions generated successfully")

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(f'output/predictions_{timestamp}.xlsx')
        predictions.to_excel(output_path, index=False)
        logger.info(f"Results saved to {output_path}")

    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
