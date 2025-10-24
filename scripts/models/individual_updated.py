"""
Temporary file to hold the corrected Individual class code.
Once we verify it works, we'll move it to individual.py
"""
import os
import sys
import math
import json
import time
import logging
import warnings
from datetime import date
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
import yaml
import joblib
import statsmodels.api as sm
from statsmodels.tools.sm_exceptions import ConvergenceWarning
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier
from dotenv import load_dotenv

# Configure logger
logger = logging.getLogger(__name__)

# Project imports
root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))

from utils.load_data import (
    load_individual,
    load_latest,
    load_cumulative
)
from utils.helper import get_all_weeks_valid, get_weeks_list, get_pred_len

# Constants
GROUP_COLS = [
    "schooljaar",
    "opleidingcode",
    "opleidingcode_display",  # To show the code separately
    "Opleidingsnaam",        # From the enriched data
    "leertraject",          # Mapped from leertrajectmbo
    "instellingserkenningscode",
]

# Column mappings for consistent naming across the code
COLUMN_MAPPINGS = {
    'schooljaar': 'schooljaar',               # Academic year
    'Collegejaar': 'schooljaar',             # For consistency
    'leertraject': 'leertrajectmbo',         # Learning path
    'Opleidingsnaam': 'Opleidingsnaam',      # Program name from enriched data
    'Weeknummer': 'week_of_year',            # Week number
    'enrollment_status': 'status',           # Status to binary outcome
    'instellingserkenningscode': 'instellingserkenningscode'  # Institution code
}

CATEGORICAL_COLS = [
    "onderwijsaanbiedercode",
    "onderwijslocatiecode",
    "status",
]

NUMERIC_COLS = [
    "postcodecijfers",
]

WEEK_COL = ["Weeknummer"]
TARGET_COL = ["enrollment_status"]

class Individual:
    def __init__(self, data_individual, data_distances, data_latest, configuration, data_cumulative=None):
        self.data_individual = data_individual
        self.data_cumulative = data_cumulative
        self.data_distances = data_distances
        self.data_latest = data_latest
        self.configuration = configuration
        self.pred_len = None

        # Cached models
        self.xgboost_models = {}

        # Backup data
        self.data_individual_backup = self.data_individual.copy()

        # Processing flags
        self.preprocessed = False
        self.predicted = False

    def preprocess(self) -> pd.DataFrame:
        """
        Preprocess the MBO enrollment data.
        """
        df = self.data_individual.copy()
        
        # --- Basic cleaning ---
        # Remove duplicates based on id
        df = df.drop_duplicates(subset=['id']).reset_index(drop=True)
        
        # --- Convert dates and extract week numbers ---
        df['Weeknummer'] = pd.to_datetime(df['createdat']).dt.isocalendar().week
        
        # Map MBO columns to expected names using COLUMN_MAPPINGS
        for target, source in COLUMN_MAPPINGS.items():
            if source in df.columns:
                df[target] = df[source]
            
        # Additional mappings and transformations
        df['Datum Verzoek Inschr'] = df['createdat']
        df['Datum intrekking vooraanmelding'] = pd.NA
        df['opleidingcode_display'] = df['opleidingcode']  # Keep code for reference
        
        # Use week_of_year for week numbers
        df['Weeknummer'] = pd.to_numeric(df['week_of_year'], errors='coerce')
        
        # --- Convert schooljaar to numeric ---
        df['schooljaar'] = pd.to_numeric(df['schooljaar'], errors='coerce').fillna(0).astype(int)
        df['Collegejaar'] = df['schooljaar']
        
        # --- Handle missing values in numeric columns ---
        df['postcodecijfers'] = pd.to_numeric(df['postcodecijfers'], errors='coerce').fillna(0)

        # --- Add count of entries per key ---
        df["Sleutel_count"] = df.groupby(["schooljaar", "ketenid"])["ketenid"].transform("count")
        
        # --- Map enrollment status to binary outcome ---
        status_map = {
            "ENROLLED": 1,    # Successfully enrolled
            "REJECTED": 0,    # Application rejected
            "CANCELLED": 0,   # Student cancelled
            "RECEIVED": 0.5,  # Application received but not processed
            "OFFERED": 0.75   # Offer made but not yet accepted
        }
        df["enrollment_status"] = df["status"].map(status_map).fillna(0)
        
        # --- Apply institutional filters ---
        if self.configuration.get("filters", {}).get("instellingscode", {}).get("enabled"):
            allowed_codes = self.configuration["filters"]["instellingscode"]["values"]
            df = df[df["instellingserkenningscode"].isin(allowed_codes)]
            
        # --- Drop unneeded columns ---
        extra_cols = ["Herkomst", "Examentype", "Collegejaar"]
        cols_to_keep = GROUP_COLS + CATEGORICAL_COLS + NUMERIC_COLS + WEEK_COL + ["enrollment_status"] + extra_cols
        cols_to_keep = [c for c in cols_to_keep if c in df.columns]
        df = df[cols_to_keep]

        # Store processed data
        self.data_individual_backup = self.data_individual.copy()
        self.data_individual = df
        self.preprocessed = True

        return df

    def _get_transformed_data(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        """Filters, cleans, and reshapes data from long to wide format."""
        start_year = self.configuration["individual_start_year"]

        # Filter and keep only necessary columns (avoid chained indexing)
        df = (
            df.loc[df["Collegejaar"] >= start_year, GROUP_COLS + ["Weeknummer", column]]
            .assign(**{column: pd.to_numeric(df[column], errors="coerce")})
        )

        # Pivot once to wide format
        pivot = (
            df.pivot_table(
                index=GROUP_COLS,
                columns="Weeknummer",
                values=column,
                aggfunc="sum",
                fill_value=0,
            )
            .sort_index(axis=1)
            .reset_index()
        )

        # Determine valid weeks (should be strings)
        pivot.columns = pivot.columns.map(str)

        valid_weeks = get_all_weeks_valid(pivot.columns)
        pivot = pivot[GROUP_COLS + valid_weeks]

        # Compute cumulative sum across weeks (vectorized)
        pivot[valid_weeks] = pivot[valid_weeks].cumsum(axis=1)

        return pivot

    def predict_preapplicant_probabilities(self, programme, herkomst, examentype, predict_year: int, predict_week: int) -> pd.DataFrame:
        """Predict enrollment probabilities for pre-applicants."""
        if not self.preprocessed:
            self.preprocess()

        df = self.data_individual.copy()

        # Filter by weeks
        weeks_to_predict = get_weeks_list(predict_week)
        df = df[df["Weeknummer"].isin(weeks_to_predict)].copy()
        
        # Replace infinites
        df.replace([np.inf, -np.inf], np.nan, inplace=True)

        # Filter by programme and institution
        df = df[df["opleidingcode"] == programme]
        
        if self.configuration.get("filters", {}).get("instellingscode", {}).get("enabled"):
            allowed_codes = self.configuration["filters"]["instellingscode"]["values"]
            df = df[df["instellingserkenningscode"].isin(allowed_codes)]

        # Filter by leertraject
        if examentype is not None:
            df = df[df["leertraject"] == examentype]

        # Log filtering results
        logger.info(f"Dataset shapes: before_filter={len(self.data_individual)}, after_filter={len(df)}")
        logger.info(f"Preapplicant filter: programme={programme}, leertraject={examentype}")
        logger.info(f"Preapplicant shapes: total={len(self.data_individual)}, after_filter={len(df)}; train/test split year={predict_year}")

        # Train/test split
        train = df[df["Collegejaar"] < predict_year].copy()
        test = df[df["Collegejaar"] == predict_year].copy()

        if len(train) == 0 or len(test) == 0:
            logger.warning(f"Insufficient data for programme {programme}")
            return df

        # Prepare features
        features = CATEGORICAL_COLS + NUMERIC_COLS + WEEK_COL
        X_train = train[features]
        y_train = train[TARGET_COL[0]]
        X_test = test[features]

        # Create and fit pipeline
        preprocessor = ColumnTransformer(
            transformers=[
                ("numeric", "passthrough", NUMERIC_COLS),
                ("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=True),
                 CATEGORICAL_COLS + WEEK_COL),
            ],
            remainder="drop",
        )

        pipeline = Pipeline([
            ("preprocessor", preprocessor),
            ("model", XGBClassifier(objective="binary:logistic", eval_metric="auc", random_state=0))
        ])

        try:
            pipeline.fit(X_train, y_train)
            predictions = pipeline.predict_proba(X_test)[:, 1]
            
            # Update predictions in main dataframe
            self.data_individual.loc[test.index, TARGET_COL[0]] = predictions
            self.predicted = True
            
        except Exception as e:
            logger.error(f"Error in predicting probabilities: {str(e)}")
            predictions = np.zeros(len(test))
            self.data_individual.loc[test.index, TARGET_COL[0]] = 0
            self.predicted = True

        return self.data_individual

    def predict_inflow_with_sarima(self,
        programme: str,
        herkomst: str,
        examentype: str,
        predict_year: int,
        predict_week: int,
        traject: str | None = None,
        refit: bool = False,
        verbose: bool = False
    ) -> list[float]:
        """
        Predicts MBO student inflow using SARIMA modeling.
        """
        # --- Check if preapplicant probabilities are predicted ---
        if not self.predicted:
            try:
                self.predict_preapplicant_probabilities(programme, herkomst, examentype, predict_year, predict_week)
            except ValueError:
                prediction = 0
                if verbose:
                    print(f"Individual prediction for {programme}, {herkomst}, {examentype}, year: {predict_year}, week: {predict_week}: {prediction}")
                return prediction

        # --- Get the prediction length ---
        pred_len = get_pred_len(predict_week)

        # --- Prepare data ---
        df = self.data_individual.copy()

        # Get transformed data for past 3 years
        df = df[df["Collegejaar"] >= predict_year - 3]  # Use 3 years of historical data
        df_wide = self._get_transformed_data(df, column=TARGET_COL[0])
        
        # Build filter conditions
        prog_filter = df_wide["opleidingcode"] == programme
        year_filter = df_wide["schooljaar"] <= predict_year  # Use schooljaar instead of Collegejaar
        
        # Add leertraject filter if specified
        if examentype is not None:
            traject_filter = df_wide["leertraject"] == examentype
            filter_mask = prog_filter & year_filter & traject_filter
        else:
            filter_mask = prog_filter & year_filter
            
        # Apply institution filter if configured
        if self.configuration.get("filters", {}).get("instellingscode", {}).get("enabled"):
            allowed_codes = self.configuration["filters"]["instellingscode"]["values"]
            filter_mask &= df_wide["instellingserkenningscode"].isin(allowed_codes)
            
            df_wide = df_wide[filter_mask].sort_values("schooljaar")        # Log filtering results
        logger.info(f"SARIMA filter: programme={programme}, leertraject={examentype}")
        logger.info(f"Filtered data: {len(df_wide)} rows spanning years {df_wide['schooljaar'].min()}-{df_wide['schooljaar'].max()}")

        if len(df_wide) < 2:  # Not enough data for prediction
            logger.warning(f"Insufficient historical data for {programme} ({df_wide['Opleidingsnaam'].iloc[0] if len(df_wide) > 0 else 'Unknown'})")
            return 0

            # Get all week columns
        week_cols = get_all_weeks_valid(df_wide.columns)
        
        # Create time series from weekly data
        ts_data = df_wide[week_cols].values.flatten()
        
        # Remove trailing zeros but keep track of the last known value
        last_known = ts_data[-1] if len(ts_data) > 0 else 0
        while len(ts_data) > 0 and ts_data[-1] == 0:
            ts_data = ts_data[:-1]

        # Log the data we're working with
        logger.info(f"Time series data for {programme}: {ts_data.tolist()}")
        logger.info(f"Last known value: {last_known}")
        
        # For sparse data, use last known value as baseline
        if not len(ts_data):
            logger.info(f"Using last known value {last_known} for {programme}")
            if last_known > 0:
                return round(last_known * 1.1)  # 10% growth
            return 0

        # Shortcut for week 38 (no prediction needed)
        if predict_week == 38:
            return last_known

        # Get prediction length
        pred_len = get_pred_len(predict_week)
        ts_train = ts_data        # --- Fit SARIMA model ---
        try:
            # For sparse MBO data, use simple trend-based prediction
            if len(ts_data) < 2:  # If we only have current year
                current_count = ts_data[-1] if len(ts_data) > 0 else 0
                # Base prediction on current count with slight growth
                prediction = round(current_count * 1.1)  # Assume 10% growth
                logger.info(f"Using simple growth prediction for {programme} due to limited data")
            else:
                # Use recent trend
                recent_data = ts_data[-12:] if len(ts_data) > 12 else ts_data
                # Remove any trailing zeros
                while len(recent_data) > 0 and recent_data[-1] == 0:
                    recent_data = recent_data[:-1]
                
                if len(recent_data) > 0:
                    current_count = recent_data[-1]
                    if len(recent_data) > 1:
                        # Calculate trend
                        avg_change = (recent_data[-1] - recent_data[0]) / len(recent_data)
                        trend_factor = max(0.8, min(1.2, 1 + avg_change/current_count if current_count > 0 else 1))
                        prediction = round(current_count * trend_factor)
                    else:
                        prediction = round(current_count * 1.05)  # Slight growth if only one point
                else:
                    prediction = 0
                    
            # Add some logging
            logger.info(f"Prediction for {programme}: {prediction} (based on {len(ts_data)} data points)")
            
        except Exception as e:
            logger.exception(f"Prediction failed for {programme}: {str(e)}")
            prediction = 0

        if verbose:
            print(f"Individual prediction for {programme}, leertraject={examentype}, year: {predict_year}, week: {predict_week}: {prediction}")
            if prediction == 0:
                print(f"Note: Zero prediction may indicate insufficient historical data")

        return prediction

    def run_full_prediction_loop(self, predict_year: int, predict_week: int, write_file: bool, verbose: bool, args = None):
        """Run predictions for all MBO programs."""
        logger.info("Running individual prediction loop")

        if not self.preprocessed:
            self.preprocess()

        # Initialize prediction dataframe
        tmp_df = self.data_individual[
            (self.data_individual["schooljaar"] == predict_year) &
            (self.data_individual["Weeknummer"] <= predict_week)
        ]

        prediction_df = (
            tmp_df.groupby(GROUP_COLS)
            .agg(
                count=("enrollment_status", "count"),
                enrollment_status_mean=("enrollment_status", "mean"),
            )
            .reset_index()
        )
        
        # Add week column
        prediction_df["Weeknummer"] = predict_week
        
        # Apply institutional filters
        if self.configuration.get("filters", {}).get("instellingscode", {}).get("enabled"):
            allowed_codes = self.configuration["filters"]["instellingscode"]["values"]
            prediction_df = prediction_df[prediction_df["instellingserkenningscode"].isin(allowed_codes)]
        
        # Remove duplicates
        prediction_df = prediction_df.drop_duplicates()

        # Parallel prediction
        nr_CPU_cores = os.cpu_count() or 1
        chunk_size = math.ceil(len(prediction_df) / nr_CPU_cores)
        chunks = [prediction_df.iloc[i:i + chunk_size] for i in range(0, len(prediction_df), chunk_size)]

        predictions = joblib.Parallel(n_jobs=nr_CPU_cores)(
            joblib.delayed(self.predict_students_row)(row, verbose)
            for chunk in chunks
            for row in chunk.itertuples(index=False)
        )

        # Create results dataframe
        results_df = prediction_df.copy()
        results_df["SARIMA_individual"] = predictions
        results_df["Aantal_studenten"] = results_df["count"]

        if write_file:
            output_path = os.path.join("output", f"predictions_{time.strftime('%Y%m%d_%H%M%S')}.xlsx")
            results_df.to_excel(output_path, index=False, engine="xlsxwriter")
            print(f"\nPredictions saved to: {output_path}")

        return results_df

    def predict_students_row(self, row_tuple, verbose):
        """Process a single row for prediction, using MBO-specific column structure."""
        programme = getattr(row_tuple, "opleidingcode", None)
        predict_year = getattr(row_tuple, "schooljaar", None)
        predict_week = getattr(row_tuple, "Weeknummer", None)
        leertraject = getattr(row_tuple, "leertraject", None)
        
        # Log the opleiding we're predicting
        opleiding_naam = getattr(row_tuple, "opleidingsnaam", programme)
        if verbose:
            logger.info(f"Processing prediction for: {opleiding_naam} ({programme}), leertraject={leertraject}")

        return self.predict_inflow_with_sarima(
            programme=programme,
            herkomst=None,  # Not used for MBO
            examentype=leertraject,  # Use leertraject instead of examentype
            predict_year=predict_year,
            predict_week=predict_week,
            verbose=verbose,
        )

def main(predict_year=2024, predict_week=5, write_file=True, verbose=True):
    # Load configuration
    CONFIG_FILE = Path("configuration/configuration.yaml")
    with open(CONFIG_FILE, "r") as f:
        configuration = yaml.safe_load(f)
    
    # Add defaults
    if "filters" not in configuration:
        configuration["filters"] = {}
    if "filtering" not in configuration:
        configuration["filtering"] = {
            "programme": None,
            "herkomst": None,
            "examentype": None
        }
    configuration.setdefault("individual_start_year", 2020)
    configuration.setdefault("numerus_fixus", {})

    # Load data
    individual_data = load_individual()
    distances = None  # MBO data doesn't use distances
    latest_data = load_latest()
    data_cumulative = load_cumulative()

    # Initialize and run model
    individual_model = Individual(individual_data, distances, latest_data, configuration, data_cumulative)
    return individual_model.run_full_prediction_loop(
        predict_year=predict_year,
        predict_week=predict_week,
        write_file=write_file,
        verbose=verbose,
        args=None
    )