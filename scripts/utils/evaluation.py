import pandas as pd
import logging
from pathlib import Path
from datetime import datetime
import sys

# Add project root to path to allow importing from scripts
root = Path(__file__).resolve().parents[2]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from scripts.models.individual_mbo import load_data

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def evaluate_predictions(predictions_file: str = None, tolerance: float = 0.2):
    """
    Evaluates predictions by comparing them with historical trends or simple heuristics.
    current implementation checks for extreme deviations.
    
    Args:
        predictions_file: Path to the predictions excel file. If None, finds the latest one.
        tolerance: Fraction of deviation allowed (default 0.2 = 20%).
    """
    output_dir = root / 'output'
    
    # 1. Load latest prediction if not specified
    if not predictions_file:
        files = list(output_dir.glob('output_mbo_*.xlsx'))
        if not files:
            logger.error("No prediction files found in output directory.")
            return
        # Sort by modification time, newest first
        predictions_file = sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)[0]
    
    logger.info(f"Evaluating predictions from: {predictions_file}")
    
    try:
        df_pred = pd.read_excel(predictions_file)
    except Exception as e:
        logger.error(f"Failed to read predictions: {e}")
        return

    # Check required columns
    required_cols = ['Opleidingscode', 'Individual_ratio']
    if not all(col in df_pred.columns for col in required_cols):
        logger.error(f"Missing required columns in prediction file. Found: {df_pred.columns.tolist()}")
        return

    # 2. Heuristic Checks
    logger.info("Running heuristic checks...")
    
    # Check 1: Zero predictions
    zero_preds = df_pred[df_pred['Individual_ratio'] == 0]
    if not zero_preds.empty:
        logger.warning(f"Found {len(zero_preds)} programs with 0 predicted students. Check if this is expected.")
        
    # Check 2: High predictions (Soft warning for very large numbers, adjust threshold as needed)
    high_threshold = 500 
    high_preds = df_pred[df_pred['Individual_ratio'] > high_threshold]
    if not high_preds.empty:
        logger.warning(f"Found {len(high_preds)} programs with >{high_threshold} predicted students. Verify if these are realistic.")
        for _, row in high_preds.iterrows():
            logger.info(f"  - {row['Opleidingscode']}: {row['Individual_ratio']:.1f}")

    # 3. Compare with historical average (mock implementation concept)
    # In a real scenario, you would load last year's actuals here.
    # Since we don't have a guaranteed 'actuals' file in this context, we will skip hard comparison
    # but describe how to add it.
    
    logger.info("Evaluation complete. Please review any warnings above.")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate MBO predictions.")
    parser.add_argument('-f', '--file', type=str, help='Path to specific prediction file to evaluate')
    args = parser.parse_args()
    
    evaluate_predictions(args.file)

if __name__ == "__main__":
    main()
