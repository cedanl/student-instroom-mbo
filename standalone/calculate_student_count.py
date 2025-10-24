import pandas as pd
import json
import os

# --- Load paths from config ---
paths_file = "configuration/paths.json" # Placing the files locally will make it faster to test and to manage than using network paths
with open(paths_file, "r") as f:
    paths = json.load(f)

student_count_path = paths.get("paths", {}).get("path_student_count")

print(f"Resolved student count path: {student_count_path}")
print(f"Path exists: {os.path.exists(student_count_path)}")

# --- Load dataset ---
if student_count_path and os.path.exists(student_count_path):
    # Explicitly specify the delimiter and handle large files
    df = pd.read_csv(student_count_path, delimiter=',', low_memory=False)
    print(f"Columns in dataset: {df.columns.tolist()}")

    # --- Filter only ENROLLED students ---
    df = df[df["status"] == "ENROLLED"].copy()

    # --- Derive 'Collegejaar' from 'schooljaar' ---
    if "schooljaar" in df.columns:
        df["Collegejaar"] = df["schooljaar"].astype(str).str.strip()
    else:
        raise KeyError("Column 'schooljaar' not found in dataset")

    # --- Clean string columns for grouping ---
    for col in ["opleidingcode", "leertrajectmbo"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
        else:
            raise KeyError(f"Column '{col}' not found in dataset")

    # Clean and prepare 'instellingserkenningscode' column
    df['instellingserkenningscode'] = df['instellingserkenningscode'].astype(str).str.strip()

    # Remove rows with no value or invalid value in 'opleidingcode'
    df = df[df['opleidingcode'].notna() & df['opleidingcode'].str.isnumeric()]

    # --- Debug: show unique values before grouping ---
    print("Unique Collegejaar:", df["Collegejaar"].unique())
    print("Unique opleidingcode:", df["opleidingcode"].unique())
    print("Unique leertrajectmbo:", df["leertrajectmbo"].unique())

    # --- Group and count students ---
    aggregated_df = (
        df.groupby(['Collegejaar', 'opleidingcode', 'leertrajectmbo', 'instellingserkenningscode'], dropna=False)
        .agg(aantal_studenten=('status', 'count'))
        .reset_index()
    )

    # --- Save aggregated result ---
    output_path = os.path.join(os.path.dirname(__file__), "../output/student_count.csv")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    aggregated_df.to_csv(output_path, index=False, sep=';')

    print(f"Overview datafile created at: {output_path}")
else:
    print("Student count file not found or path not defined in paths.json.")
