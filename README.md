# MBO Prognose

A prediction model for MBO student enrollments, using historical enrollment data to forecast future student numbers per program and learning path.

## Project Structure

```
mboprognose/
├── configuration/           # Configuration files
│   ├── configuration.yaml  # Main configuration (filters, settings)
│   └── paths.json         # File path configurations
├── input/                  # Input data directory
│   └── aanmeldingen_oktober_2024.csv  # Enrollment data
├── output/                 # Output directory for predictions
├── scripts/
│   └── models/            # Model implementations
│       └── individual.py  # Individual prediction model
└── utils/                 # Utility functions
    ├── helper.py         # Helper functions
    └── load_data.py      # Data loading functions
```

## Requirements

- Python 3.10+
- UV package manager

## Installation

1. Clone the repository:
```bash
git clone https://github.com/radboudir/mboprognose.git
cd mboprognose
```

2. Install dependencies using UV:
```bash
uv venv
uv pip install -r requirements.txt
```

## Configuration

### Main Configuration (`configuration/configuration.yaml`)

```yaml
filters:
  # Institution filter
  instellingscode:
    enabled: true
    values: ['01AA']  # Institution codes to include

  # Learning path filter (e.g., "BOL", "BBL")
  leertraject:
    enabled: true
    values: []  # Empty list includes all

  # Study program filter
  opleiding:
    enabled: true
    values: []  # Empty list includes all
```

### Data Requirements

The input CSV file should contain the following columns:
- `createdat`: Application timestamp
- `status`: Application status (ENROLLED, REJECTED, etc.)
- `schooljaar`: Academic year
- `opleidingcode`: Program code
- `Opleidingsnaam`: Program name
- `leertrajectmbo`: Learning path (BOL/BBL)
- `instellingserkenningscode`: Institution code

## Usage

1. Place your enrollment data CSV in the `input/` directory.

2. Update the configuration in `configuration/configuration.yaml` if needed.

3. Run the prediction model:
```bash
# Run with current year and week
uv run main.py

# Run with specific year and week
uv run main.py -y 2024 -w 42

# Run with specific year, current week
uv run main.py -y 2024

# Run with current year, specific week
uv run main.py -w 42
```

Command line options:
- `-y` or `--year`: Specify the target year (default: current year)
- `-w` or `--week`: Specify the target week number (default: current week)

Note: The script will abort if no actual data is found for the specified year and week.

The script will:
- Load and preprocess the enrollment data
- Verify data availability for target year/week
- Generate predictions per program and learning path
- Save results to `output/predictions_[timestamp].xlsx`

## Output Format

The prediction output includes:
- Program name and code
- Learning path (BOL/BBL)
- Predicted enrollments (SARIMA_individual)
- Actual enrollments (Aantal_studenten)
- Error metrics (Absolute_Error, Percentage_Error)

## Model Details

The prediction model uses:
1. A pre-applicant probability model for initial filtering
2. A trend-based prediction approach for sparse data
3. Optional institution and program filtering

For sparse data (< 2 years of history), the model uses a simple trend-based approach with:
- Current enrollment as baseline
- Growth assumptions based on available data
- Reasonable bounds on prediction changes

## Limitations

- Requires at least one year of historical data for meaningful predictions
- More accurate with multiple years of historical data
- Institution-specific filtering must be configured correctly

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request
