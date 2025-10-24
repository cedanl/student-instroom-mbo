import pandas as pd
import numpy as np
import logging
from pathlib import Path
from scripts.models.individual_updated import main as run_prediction
from utils.load_data import load_individual, load_student_count

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# First, verify our data files
logger.info("Checking input data...")
apps_data = load_individual()
actual_data = load_student_count()

if apps_data is None:
    raise ValueError("Could not load applications data - check path_individual in configuration")
if actual_data is None:
    raise ValueError("Could not load student count data - check path_student_count in configuration")

logger.info(f"Applications data shape: {apps_data.shape}")
logger.info(f"Student count data shape: {actual_data.shape}")

# Run prediction from week 5
logger.info("Running predictions...")
result = run_prediction(predict_year=2024, predict_week=5, write_file=True, verbose=True)

# Load the output file that was created (will have timestamp in name)
import glob
import os

# Get the most recent output file
list_of_files = glob.glob('output/*.xlsx') 
latest_file = max(list_of_files, key=os.path.getctime)

# Read the predictions
predictions = pd.read_excel(latest_file)

# Group by programme and leertraject to compare predicted vs actual
summary = predictions.groupby(['Opleidingsnaam', 'opleidingcode_display', 'leertraject']).agg({
    'SARIMA_individual': 'sum',  # Our prediction
    'Aantal_studenten': 'sum'    # Actual enrollments
}).reset_index()

# Calculate error metrics
summary['Absolute_Error'] = abs(summary['SARIMA_individual'] - summary['Aantal_studenten'])
summary['Percentage_Error'] = np.where(
    summary['Aantal_studenten'] == 0,
    0,
    (abs(summary['SARIMA_individual'] - summary['Aantal_studenten']) / summary['Aantal_studenten']) * 100
)

# Add error details and info about zeros
zero_predictions = summary[summary['SARIMA_individual'] == 0]
all_zeros = len(zero_predictions) == len(summary)

logger.info("\nPrediction Analysis:")
logger.info(f"Total programs: {len(summary)}")
logger.info(f"Programs with zero predictions: {len(zero_predictions)}")
if len(zero_predictions) > 0:
    logger.info("\nPrograms with zero predictions:")
    for _, row in zero_predictions.iterrows():
        logger.info(f"- {row['Opleidingsnaam']} ({row['opleidingcode_display']}) - "
                   f"Actual: {row['Aantal_studenten']}")

# Sort and display results
summary = summary.sort_values(['Absolute_Error', 'Opleidingsnaam'], ascending=[False, True])
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

print("\nPrediction Summary (sorted by absolute error):")
print(summary)

print("\nOverall Metrics:")
print(f"Mean Absolute Error: {summary['Absolute_Error'].mean():.2f}")
print(f"Mean Percentage Error: {summary['Percentage_Error'].mean():.2f}%")

if all_zeros:
    logger.error("WARNING: All predictions are zero - likely an issue with the data or model")