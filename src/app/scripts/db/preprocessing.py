import os
import h3
import pandas as pd
import numpy as np
from sklearn.neighbors import BallTree
import sys
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.config.configs import settings
from src.app.utils.common import setup_logger



def open_lst(path: Path) -> pd.DataFrame:
    """
    Reads a .lst file containing h3 indexes, returns DataFrame with lat/lon.
    
    Args:
        path (Path): Path to the .lst file

    Returns:
        df (pd.DataFrame): DataFrame with lat/lon
    """
    with open(path, "r") as f:
        df = pd.DataFrame({'h3_09': [x.strip() for x in f.readlines()]})
        df[['lat', 'lon']] = df['h3_09'].apply(h3.cell_to_latlng).to_list()
    return df

def preprocess_data(
        raw_dir: Path, 
        processed_dir: Path,
        logger: logging.Logger
    ):
    """
    Performs preprocessing steps: 
    1. Combines hexes
    2. Converts formats
    3. Processes Moscow data
    
    Args:
        raw_dir (Path): Raw data directory
        processed_dir (Path): Processed data directory
        logger (logging.Logger): Logger instance
    """
    logger.info("Starting preprocessing...")
    hexses_data_path = raw_dir / 'hexses_data.lst'
    hexses_target_path = raw_dir / 'hexses_target.lst'
    moscow_parquet_path = raw_dir / 'moscow.parquet'
    target_parquet_path = raw_dir / 'target.parquet'
    transactions_parquet_path = raw_dir / 'transactions.parquet'

    os.makedirs(processed_dir, exist_ok=True)
    cash_withdrawals_csv_path = processed_dir / 'cash_withdrawals.csv'
    locations_csv_path = processed_dir / 'locations.csv'
    moscow_csv_path = processed_dir / 'moscow.csv'
    transactions_csv_path = processed_dir / 'transactions.csv'

    # --- Process hexses data --- 
    logger.info(f"Reading hexses data from {hexses_data_path} and {hexses_target_path}")
    hexses_data = open_lst(hexses_data_path)
    hexses_target = open_lst(hexses_target_path)

    logger.info("Combining and saving unique hex locations...")
    hexses = pd.concat([hexses_data, hexses_target]).drop_duplicates()
    logger.info(f"Total unique locations: {hexses.shape[0]}")
    hexses.to_csv(locations_csv_path, index=False)
    logger.info(f"Saved locations to {locations_csv_path}")

    # --- Convert Parquet files to CSV --- 
    logger.info(f"Converting {transactions_parquet_path} to CSV...")
    (pd
    .read_parquet(transactions_parquet_path)
    .to_csv(transactions_csv_path, index=True, index_label='transaction_pk')
    )
    logger.info(f"Saved transactions to {transactions_csv_path}")

    logger.info(f"Converting {target_parquet_path} to CSV...")
    (pd
    .read_parquet(target_parquet_path)
    .to_csv(cash_withdrawals_csv_path, index=False)
    )
    logger.info(f"Saved cash withdrawals to {cash_withdrawals_csv_path}")

    # --- Process Moscow data --- 
    logger.info(f"Reading Moscow POI data from {moscow_parquet_path}...")
    moscow = pd.read_parquet(moscow_parquet_path, engine='pyarrow')
    logger.info("Processing Moscow data (filtering, calculating h3, finding nearest centers)...")
    moscow = moscow[moscow['tags'].notna()].copy()
    logger.info(f"Filtered Moscow POIs: {moscow.shape[0]}")
    # Calculate h3 index for Moscow POIs
    moscow['h3_09'] = moscow[['lat','lon']].apply(
        lambda row: h3.latlng_to_cell(row['lat'], row['lon'], 9), 
        axis=1
    )
    # Prepare BallTree from unique hex locations
    unique_h3 = hexses['h3_09'].unique()
    coords_data1 = [h3.cell_to_latlng(h) for h in unique_h3]
    coords_data1_rad = np.radians(coords_data1)
    tree = BallTree(coords_data1_rad, metric='haversine')
    # Find nearest hex center for each Moscow POI
    data2_coords = moscow['h3_09'].apply(h3.cell_to_latlng).tolist()
    data2_coords_rad = np.radians(data2_coords)
    distances, indices = tree.query(data2_coords_rad, k=1)
    nearest_indices = indices.flatten()
    moscow['h3_09_centers'] = unique_h3[nearest_indices]
    # Save processed Moscow data
    moscow.to_csv(moscow_csv_path, index=False)
    logger.info(f"Saved processed Moscow data to {moscow_csv_path}")

    logger.info("Preprocessing finished.")

if __name__ == "__main__":
    logger = setup_logger()
    preprocess_data(Path(settings.DATA_DIR) / 'raw', Path(settings.DATA_DIR) / 'processed', logger)
