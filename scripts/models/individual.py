# individual.py

# --- Standard library ---
import os
import sys
import math
import json
import time
import logging
import warnings
from datetime import date
from pathlib import Path

# --- Third-party libraries ---
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

# --- Project modules ---
root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))

from utils.load_data import (
    load_individual,
    load_latest,
    load_cumulative
)
from utils.helper import get_all_weeks_valid, get_weeks_list, get_pred_len

# --- Warnings and logging setup ---
warnings.simplefilter("ignore", ConvergenceWarning)
logger = logging.getLogger(__name__)

# --- Environment setup ---
load_dotenv()
ROOT_PATH = os.getenv("ROOT_PATH")

# --- Constants and mappings ---
GROUP_COLS = [
    "schooljaar",
    "opleidingcode",
    "opleidingcode_display",  # To show the code separately
    "Opleidingsnaam",        # From the enriched data
    "leertraject",          # Mapped from leertrajectmbo
    "instellingserkenningscode",
]

# Column mappings for consistent naming
COLUMN_MAPPINGS = {
    'schooljaar': 'schooljaar',               # Academic year
    'Collegejaar': 'schooljaar',             # For consistency
    'leertraject': 'leertrajectmbo',         # Learning path
    'Opleidingsnaam': 'Opleidingsnaam',      # Program name
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


# --- Main individual class ---

class Individual():
    def __init__(self, data_individual, data_distances, data_latest, configuration, data_cumulative = None):
        self.data_individual = data_individual
        self.data_cumulative = data_cumulative
        self.data_distances = data_distances
        self.data_latest = data_latest
        self.configuration = configuration
        self.pred_len = None

        # Cached xgboost models
        self.xgboost_models = {}

        # Backup data
        self.data_individual_backup = self.data_individual.copy()

        # Store processing variables
        self.preprocessed = False
        self.predicted = False

    # --------------------------------------------------
    # -- General helper functions --
    # --------------------------------------------------
    
    def _get_transformed_data(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        """
        Filters, cleans, and reshapes data from long to wide format.
        """
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



    # --------------------------------------------------
    # -- Preprocessing --
    # --------------------------------------------------

    ### --- Helpers --- ###
    def to_weeknummer(self, datum):
        try:
            day, month, year = map(int, datum.split("-"))
            return date(year, month, day).isocalendar()[1]
        except (AttributeError, ValueError):
            return np.nan

    def get_herkomst(self, nat=None, eer=None):
        # For MBO data, we assume all students are from NL
        return "NL"

    def get_deadlineweek(self, row):
        # For MBO, we'll consider week 17 as the deadline week for all programs
        return row["Weeknummer"] == 17

    # --- Main logic ---
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
        
        # Use week_of_year for week numbers if available
        if 'week_of_year' in df.columns:
            df['Weeknummer'] = pd.to_numeric(df['week_of_year'], errors='coerce')
        
        # --- Convert schooljaar to numeric ---
        df['schooljaar'] = pd.to_numeric(df['schooljaar'], errors='coerce').fillna(0).astype(int)
        df['Collegejaar'] = df['schooljaar']  # For consistency
        
        # --- Handle missing values in numeric columns ---
        df['postcodecijfers'] = pd.to_numeric(df['postcodecijfers'], errors='coerce').fillna(0)

        # --- Add count of entries per key ---
        key_col = 'ketenid'  # Unique identifier for MBO students
        df["Sleutel_count"] = df.groupby(["schooljaar", key_col])[key_col].transform("count")

        # --- Convert dates to week numbers ---
        # Convert the dates directly without using apply
        df["Weeknummer"] = pd.to_datetime(df["Datum Verzoek Inschr"]).dt.isocalendar().week
        df["Datum intrekking vooraanmelding"] = pd.to_datetime(df["Datum intrekking vooraanmelding"]).dt.isocalendar().week

        # --- Set origin (all NL for MBO) ---
        df["Herkomst"] = "NL"

        # --- Filter to only include rows with valid status ---
        df = df[df["status"].notna()]
        
        # --- Map enrollment status to binary outcome ---
        status_map = {
            "ENROLLED": 1,    # Successfully enrolled
            "REJECTED": 0,    # Application rejected
            "CANCELLED": 0,   # Student cancelled
            "RECEIVED": 0.5,  # Application received but not processed
            "OFFERED": 0.75   # Offer made but not yet accepted
        }
        df["enrollment_status"] = df["status"].map(status_map).fillna(0)
        
        # --- Filter based on configuration ---
        if self.configuration.get("filters", {}).get("instellingscode", {}).get("enabled"):
            allowed_codes = self.configuration["filters"]["instellingscode"]["values"]
            df = df[df["instellingserkenningscode"].isin(allowed_codes)]

        # --- Add distances if available ---
        if self.data_distances is not None:
            afstand_lookup = self.data_distances.set_index("Geverifieerd adres plaats")["Afstand"]
            df["Afstand"] = df["Geverifieerd adres plaats"].map(afstand_lookup)
        else:
            df["Afstand"] = np.nan

        # --- Determine deadline week flag ---
        df["Deadlineweek"] = df.apply(self.get_deadlineweek, axis=1)

        # --- Drop unneeded columns ---
        if "Sleutel" in df.columns:
            df = df.drop(columns=["Sleutel"])

        # --- Final cleanup ---
        # Ensure columns required later in the pipeline are preserved
        extra_cols = ["Examentype", "Herkomst", "Croho groepeernaam", "Collegejaar"]
        cols_to_keep = GROUP_COLS + CATEGORICAL_COLS + NUMERIC_COLS + WEEK_COL + ["enrollment_status", "Datum intrekking vooraanmelding"] + extra_cols
        # Keep only existing columns to avoid KeyError
        cols_to_keep = [c for c in cols_to_keep if c in df.columns]
        df = df[cols_to_keep]

        # Filter based on configuration
        if self.configuration.get("filters", {}).get("instellingscode", {}).get("enabled"):
            allowed_codes = self.configuration["filters"]["instellingscode"]["values"]
            df = df[df["instellingserkenningscode"].isin(allowed_codes)]

        # --- Store results ---
        self.data_individual_backup = self.data_individual.copy()
        self.data_individual = df
        self.preprocessed = True

        return df

    # --------------------------------------------------
    # -- Prediction of pre-applicant probabilities (chance that someone will enroll) --
    # --------------------------------------------------
    
    ### --- Main logic --- ###
    def predict_preapplicant_probabilities(self, programme, herkomst, examentype, predict_year: int, predict_week: int, predict = True) -> pd.DataFrame:
        """
        Predict the probability that a pre-applicant will enroll for each individual. Returns the updated dataset.
        """

        # --- Preprocess if not done ---
        if not self.preprocessed:
            self.preprocess()

        df = self.data_individual.copy()

        # --- Filter by weeks to predict ---
        weeks_to_predict = get_weeks_list(predict_week)
        df = df[df["Weeknummer"].isin(weeks_to_predict)].copy()

        # Replace infinite values with NaN
        df.replace([np.inf, -np.inf], np.nan, inplace=True)

        # Filter by opleidingcode and instellingserkenningscode
        df = df[df["opleidingcode"] == programme]
        
        # Also filter by institution if configured
        if self.configuration.get("filters", {}).get("instellingscode", {}).get("enabled"):
            allowed_codes = self.configuration["filters"]["instellingscode"]["values"]
            df = df[df["instellingserkenningscode"].isin(allowed_codes)]

        # Filter by leertraject if specified
        if examentype is not None:
            df = df[df["leertraject"] == examentype]

        try:
            logger.info(f"Filtering for opleiding '{df['opleidingsnaam'].iloc[0]}' ({programme})")
        except (IndexError, KeyError):
            logger.warning(f"No data found for opleiding {programme}")
        logger.info(f"Dataset shapes: before_filter={len(self.data_individual)}, after_filter={len(df)}")

        logger.info(f"Preapplicant filter: programme={programme}, leertraject={examentype}")
        logger.info(f"Preapplicant shapes: total={len(self.data_individual)}, after_filter={len(df)}; train/test split year={predict_year}")

        # --- Train/Test Split ---
        train_mask = (df["Collegejaar"] < predict_year) & (df["Collegejaar"] >= self.configuration["individual_start_year"])
        test_mask = df["Collegejaar"] == predict_year

        train = df[train_mask].copy()
        test = df[test_mask].copy()

        # --- Filter out cancelled registrations ---
        if predict_week <= 38:
            cancellation_filter = train["Datum intrekking vooraanmelding"].isna() | (
                (train["Datum intrekking vooraanmelding"] >= predict_week) & (train["Datum intrekking vooraanmelding"] < 39)
            )
        else:
            cancellation_filter = (
                train["Datum intrekking vooraanmelding"].isna()
                | (train["Datum intrekking vooraanmelding"] > predict_week)
                | (train["Datum intrekking vooraanmelding"] < 39)
            )
        train = train[cancellation_filter]

        # --- Target Mapping ---
        status_map = {
            "Ingeschreven": 1,
            "Uitgeschreven": 1,
            "Geannuleerd": 0,
            "Verzoek tot inschrijving": 0,
            "Studie gestaakt": 0,
            "Aanmelding vervolgen": 0,
        }
        
        # Keep the original statuses for masking
        original_statuses = test[TARGET_COL[0]].copy()
        
        train[TARGET_COL[0]] = train[TARGET_COL[0]].map(status_map)
        test[TARGET_COL[0]] = test[TARGET_COL[0]].map(status_map)

        # --- Features and Labels ---
        X_train = train.drop(columns=[TARGET_COL[0]])
        y_train = train[TARGET_COL[0]]
        X_test = test.drop(columns=[TARGET_COL[0]])

        # --- Preprocessing + Model Pipeline ---
        preprocessor = ColumnTransformer(
            transformers=[
                ("numeric", "passthrough", NUMERIC_COLS),
                ("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=True),
                CATEGORICAL_COLS + GROUP_COLS + WEEK_COL),
            ],
            remainder="drop",
        )

        pipeline = Pipeline(steps=[
            ("preprocessor", preprocessor),
            ("model", XGBClassifier(objective="binary:logistic", eval_metric="auc", random_state=0))
        ])

        # --- Fit Pipeline ---
        pipeline.fit(X_train, y_train)

        # --- Predictions ---
        probabilities = pipeline.predict_proba(X_test)[:, 1]

        # --- Vectorized Post-processing ---
        cancelled_flag = (original_statuses == "Geannuleerd")
        week_mask = np.isin(test["Datum intrekking vooraanmelding"].to_numpy(), weeks_to_predict)
        final_mask = cancelled_flag.to_numpy() & week_mask
        final_predictions = np.where(final_mask, 0, probabilities)

        # --- Assign predictions back safely ---
        self.data_individual.loc[:, TARGET_COL[0]] = self.data_individual[TARGET_COL[0]].map(status_map)
        if predict:
            self.data_individual.loc[test.index, TARGET_COL[0]] = final_predictions

        self.predicted = True

        return self.data_individual

    # --------------------------------------------------
    # -- Prediction of inflow (using SARIMA to extent the current inflow to week 38) --
    # --------------------------------------------------

    ### --- Helpers --- ###
    def _filter_data(self, data: pd.DataFrame, herkomst: str, predict_year: int, programme: str, examentype: str) -> pd.DataFrame:
        data = self._get_transformed_data(data, TARGET_COL[0])
        filtered = data[
            (data["Herkomst"] == herkomst)
            & (data["Collegejaar"] <= predict_year)
            & (data["Croho groepeernaam"] == programme)
            & (data["Examentype"] == examentype)
        ]
        return filtered

    def _create_time_series(self, data: pd.DataFrame, pred_len: int) -> np.ndarray:
        ts_data = data.loc[:, get_all_weeks_valid(data.columns)].values.flatten()
        return ts_data[:-pred_len], ts_data[-pred_len:]


    def _fit_sarima(self, ts_data: np.ndarray, exog_train: np.ndarray, model_name: str, programme: str, predict_week: int, predict_year: int, refit: bool):
        model_path = os.path.join(self.configuration["other_paths"]["individual_sarima_models"].replace("${root_path}", ROOT_PATH), f"{model_name}.json")

        deadline_weeks = [17, 18, 19, 20, 21]
        is_bachelor_near_deadline = (
            programme.startswith("B") and predict_week in deadline_weeks
        )

        sarimax_args = dict(
            order=(1, 1, 1) if not is_bachelor_near_deadline else (1, 0, 1),
            seasonal_order=(1, 1, 0, 52) if not is_bachelor_near_deadline else (1, 1, 1, 52),
            enforce_stationarity=False,
            enforce_invertibility=False,
            exog=exog_train
        )

        model = sm.tsa.SARIMAX(ts_data, **sarimax_args)

        if os.path.exists(model_path) and not refit:
            try:
                with open(model_path, "r") as f:
                    model_data = json.load(f)
                loaded_params = model_data["model_params"]
                trained_year = model_data["trained_year"]

                if predict_year > trained_year:
                    fitted_model = model.fit(disp=False)
                else:
                    param_array = [loaded_params[name] for name in model.param_names]
                    fitted_model = model.fit(start_params=param_array, disp=False)
                    return fitted_model
            except KeyError:
                fitted_model = model.fit(disp=False)
        else:
            fitted_model = model.fit(disp=False)

        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        with open(model_path, "w") as f:
            json.dump(
                {"trained_year": predict_year, "model_params": dict(zip(fitted_model.param_names, fitted_model.params))},
                f, indent=4
            )

        return fitted_model
    
    def _nf_students_based_on_distribution_of_last_years(self, prediction, examentype, programme, herkomst, predict_year, predict_week):
        last_years_data = self.data_latest[
            (self.data_latest["Collegejaar"] < predict_year)
            & (self.data_latest["Collegejaar"] >= predict_year - 3)
            & (self.data_latest["Weeknummer"] == predict_week)
            & (self.data_latest["Croho groepeernaam"] == programme)
            & (self.data_latest["Examentype"] == examentype)
        ].fillna(0)

        # Initialize a list to store distributions per year
        distributions = []

        for last_year in range(predict_year - 3, predict_year):
            year_data = last_years_data[last_years_data["Collegejaar"] == last_year]

            total_students = year_data["Aantal_studenten"].sum()
            if total_students == 0:
                continue  # Skip if no data or avoid division by zero

            herkomst_students = year_data[year_data["Herkomst"] == herkomst]["Aantal_studenten"].sum()

            distributions.append(herkomst_students / total_students)

        # Compute mean distribution across available years
        distribution = np.mean(distributions) if distributions else 0

        # Apply numerus fixus cap if configured for this programme
        nf_limit = self.configuration.get('numerus_fixus', {}).get(programme)
        if nf_limit is not None and prediction > nf_limit * distribution:
            prediction = nf_limit * distribution

        return round(prediction)

    ### --- Exog variables --- ####
    def _set_deadline(self, row):
        """
        Determines if the given row falls close to the deadline week.
        """
        # Make sure Weeknummer is numeric
        week = int(row["Weeknummer"])

        # Numerus fixus programs
        nf_programs = list(self.configuration.get("numerus_fixus", {}).keys())

        # Bachelor non-numerus fixus: weeks 15–19
        if row["Examentype"] == "Bachelor" and week in range(15, 20) and row["Croho groepeernaam"] not in nf_programs:
            return 1

        # Bachelor numerus fixus: weeks 1–2
        elif row["Examentype"] == "Bachelor" and week in range(1, 3) and row["Croho groepeernaam"] in nf_programs:
            return 1

        return 0
    
    def _create_exog_variables(self, df: pd.DataFrame, pred_len: int):
        """
        Creates exog variables for a given dataframe.
        """
        df = df.copy()

        try:
            # Deadline week
            df["Deadline"] = df.apply(self._set_deadline, axis=1)
        except ValueError:
            df["Deadline"] = 0

        # Split based on pred_len
        try:
            exog_train, exog_test = self._create_time_series(df, pred_len, target = "Deadline")
        except ValueError:
            exog_train = None
            exog_test = None

        return exog_train, exog_test


    ### --- Main logic --- ###
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
        Predicts MBO student inflow using SARIMA modeling with fallback to trend-based
        prediction for sparse data.
        """
        # --- Check if preapplicant probabilities are predicted ---
        if not self.predicted:
            try:
                self.predict_preapplicant_probabilities(programme, herkomst, examentype, predict_year, predict_week)
            except ValueError:
                prediction = 0
                if verbose:
                    print(f"Individual prediction for {programme}, year: {predict_year}, week: {predict_week}: {prediction}")
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
        year_filter = df_wide["schooljaar"] <= predict_year
        
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
            
        df_wide = df_wide[filter_mask].sort_values("schooljaar")

        # Log filtering results
        logger.info(f"SARIMA filter: programme={programme}, leertraject={examentype}")
        logger.info(f"Filtered data: {len(df_wide)} rows spanning years {df_wide['schooljaar'].min()}-{df_wide['schooljaar'].max()}")

        if len(df_wide) < 2:  # Not enough data for prediction
            logger.warning(f"Insufficient historical data for {programme}")
            return 0

        # Get all week columns and create time series
        week_cols = get_all_weeks_valid(df_wide.columns)
        ts_data = df_wide[week_cols].values.flatten()
        
        # Remove trailing zeros but keep track of the last known value
        last_known = ts_data[-1] if len(ts_data) > 0 else 0
        while len(ts_data) > 0 and ts_data[-1] == 0:
            ts_data = ts_data[:-1]

        # Log the data we're working with
        logger.info(f"Time series data points: {len(ts_data)}")
        logger.info(f"Last known value: {last_known}")
        
        # For sparse data, use last known value as baseline
        if len(ts_data) < 2:
            logger.info(f"Using last known value with growth for {programme}")
            if last_known > 0:
                return round(last_known * 1.1)  # 10% growth assumption
            return 0

        # Shortcut for week 38 (no prediction needed)
        if predict_week == 38:
            return last_known

        try:
            if len(ts_data) < 12:  # If we have limited historical data
                # Use simple trend-based prediction
                recent_data = ts_data
                current_count = recent_data[-1]
                
                # Calculate trend from available data
                avg_change = (recent_data[-1] - recent_data[0]) / len(recent_data)
                trend_factor = max(0.8, min(1.2, 1 + avg_change/current_count if current_count > 0 else 1))
                prediction = round(current_count * trend_factor)
                
                logger.info(f"Using trend-based prediction for {programme} due to limited data")
            else:
                # Use SARIMA for longer time series
                sarimax_args = dict(
                    order=(1, 0, 1),  # Less aggressive differencing
                    seasonal_order=(1, 1, 0, 12),  # Monthly seasonality
                    enforce_stationarity=False,
                    enforce_invertibility=False
                )
                
                model = sm.tsa.SARIMAX(ts_data, **sarimax_args)
                results = model.fit(disp=False)
                forecast = results.forecast(steps=pred_len)
                prediction = round(forecast[-1])
                
                # Ensure prediction is not unreasonably different from last known value
                if prediction > last_known * 2:  # Cap at 100% growth
                    prediction = round(last_known * 2)
                elif prediction < last_known * 0.5:  # Floor at 50% decline
                    prediction = round(last_known * 0.5)
            
            logger.info(f"Prediction for {programme}: {prediction}")
            
        except Exception as e:
            logger.exception(f"Prediction failed for {programme}: {str(e)}")
            prediction = 0

        if verbose:
            print(f"Individual prediction for {programme}, leertraject={examentype}, "
                  f"year: {predict_year}, week: {predict_week}: {prediction}")

        if programme in list(self.configuration["numerus_fixus"].keys()):
            prediction = self._nf_students_based_on_distribution_of_last_years(prediction, examentype, programme, herkomst, predict_year, predict_week)

        if verbose:
            print(
                f"Individual prediction for {programme}, {herkomst}, {examentype}, year: {predict_year}, week: {predict_week}: {prediction}"
            )
 
        return prediction


    # --------------------------------------------------
    # -- Full prediction loop --
    # --------------------------------------------------

    ### --- Helpers --- ###
    def predict_students_row(self, row_tuple, verbose):
        """Process a single row for prediction, using MBO-specific column structure."""
        programme = getattr(row_tuple, "opleidingcode", None)
        predict_year = getattr(row_tuple, "schooljaar", None)
        predict_week = getattr(row_tuple, "Weeknummer", None)
        leertraject = getattr(row_tuple, "leertraject", None)
        
        # Log the prediction details
        opleiding_naam = getattr(row_tuple, "Opleidingsnaam", programme)
        if verbose:
            logger.info(f"Processing prediction for: {opleiding_naam} ({programme}), "
                       f"leertraject={leertraject}, year={predict_year}, week={predict_week}")

        return self.predict_inflow_with_sarima(
            programme=programme,
            herkomst=None,  # Not used for MBO
            examentype=leertraject,
            predict_year=predict_year,
            predict_week=predict_week,
            verbose=verbose,
        )

    ### --- Main logic --- ###
    def run_full_prediction_loop(self, predict_year: int, predict_week: int, write_file: bool, verbose: bool, args = None):
        """
        Run the full prediction loop for all years and weeks.
        """
        logger.info("Running individual prediction loop")

        # --- Preprocess if not done ---
        if not self.preprocessed:
            self.preprocess()

        # --- Apply filtering from configuration ---
        filtering = self.configuration["filtering"]

        # --- Initialize prediction dataframe ---
        prediction_df = pd.DataFrame()

        # Get unique combinations from individual data
        # Use count of rows (via enrollment_status) instead of relying on an 'id' column
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
        
        # Apply configuration filters
        if self.configuration.get("filters", {}).get("instellingscode", {}).get("enabled"):
            allowed_codes = self.configuration["filters"]["instellingscode"]["values"]
            prediction_df = prediction_df[prediction_df["instellingserkenningscode"].isin(allowed_codes)]
        
        # --- Apply mask ---
        # Already created prediction_df above

        # --- Make sure the rows are unique ---
        prediction_df = prediction_df.drop_duplicates()

        # --- Parallel prediction ---
        nr_CPU_cores = os.cpu_count() or 1
        chunk_size = math.ceil(len(prediction_df) / nr_CPU_cores)

        chunks = [
            prediction_df.iloc[i : i + chunk_size] for i in range(0, len(prediction_df), chunk_size)
        ]

        # --- Predict student inflow --- 
        predictions = joblib.Parallel(n_jobs=nr_CPU_cores)(
            joblib.delayed(self.predict_students_row)(row, verbose)
            for chunk in chunks
            for row in chunk.itertuples(index=False)
        )

        # Create results dataframe
        results_df = prediction_df.copy()
        results_df["SARIMA_individual"] = predictions
        results_df["Aantal_studenten"] = results_df["count"]  # Actual counts
        
        # --- Write the file ---
        if write_file:
            output_path = os.path.join("output", f"predictions_{time.strftime('%Y%m%d_%H%M%S')}.xlsx")
            results_df.to_excel(output_path, index=False, engine="xlsxwriter")
            print(f"\nPredictions saved to: {output_path}")
        
        return results_df


        # TODO: Re-implement evaluation
        pass

        logger.info("Individual prediction done")



# --- Main function ---
def main(predict_year=2024, predict_week=5, write_file=True, verbose=True):
    # --- Load configuration ---
    CONFIG_FILE = Path("configuration/configuration.yaml")
    with open(CONFIG_FILE, "r") as f:
        configuration = yaml.safe_load(f)
    
    # Add defaults for missing configuration sections
    if "filters" not in configuration:
        configuration["filters"] = {}
    if "filtering" not in configuration:
        configuration["filtering"] = {
            "programme": None,
            "herkomst": None,
            "examentype": None
        }
    # sensible defaults for missing keys
    configuration.setdefault("individual_start_year", 2020)
    configuration.setdefault("numerus_fixus", {})

    # --- Load data ---
    individual_data = load_individual()
    distances = None  # MBO data doesn't use distances
    latest_data = load_latest()
    data_cumulative = load_cumulative()

    # --- Initialize model ---
    individual_model = Individual(individual_data, distances, latest_data, configuration, data_cumulative)

    # --- Run prediction loop ---
    individual_model.run_full_prediction_loop(
        predict_year=predict_year,
        predict_week=predict_week,
        write_file=write_file,
        verbose=verbose,
        args=None  # TODO: Re-implement argument handling
    )



if __name__ == "__main__":

    main()

    '''
    CONFIG_FILE = Path("configuration.yaml")
    with open(CONFIG_FILE, "r") as f:
        configuration = yaml.safe_load(f)  

    # Load data
    individual_data = load_individual()
    distances = load_distances()
    latest_data = load_latest()

    # Initialize model
    individual_model = Individual(individual_data, distances, latest_data, configuration)

    individual_model.predict_inflow_with_sarima(programme="B Bedrijfskunde", herkomst="NL", examentype="Bachelor", predict_year=2024, predict_week=20)
    '''