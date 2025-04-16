import os
import h3
import pandas as pd
import numpy as np
from sklearn.neighbors import BallTree
import sys
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from config.configs import configs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def open_lst(path):
    """Reads a .lst file containing h3 indexes, returns DataFrame with lat/lon."""
    with open(path, "r") as f:
        df = pd.DataFrame({'h3_09': [x.strip() for x in f.readlines()]})
        df[['lat', 'lon']] = df['h3_09'].apply(h3.cell_to_latlng).to_list()
    return df

def preprocess_data(config):
    """Performs preprocessing steps: combines hexes, converts formats, processes Moscow data."""
    logging.info("Starting preprocessing...")
    # Define paths using config
    data_dir = config.DATA_DIR
    hexses_data_path = os.path.join(data_dir, 'hexses_data.lst')
    hexses_target_path = os.path.join(data_dir, 'hexses_target.lst')
    locations_csv_path = os.path.join(data_dir, 'locations.csv')
    transactions_parquet_path = os.path.join(data_dir, 'transactions.parquet')
    transactions_csv_path = os.path.join(data_dir, 'transactions.csv')
    target_parquet_path = os.path.join(data_dir, 'target.parquet')
    cash_withdrawals_csv_path = os.path.join(data_dir, 'cash_withdrawals.csv')
    moscow_parquet_path = os.path.join(data_dir, 'moscow.parquet')
    moscow_csv_path = os.path.join(data_dir, 'moscow.csv')

    # --- Process hexses data --- 
    logging.info(f"Reading hexses data from {hexses_data_path} and {hexses_target_path}")
    hexses_data = open_lst(hexses_data_path)
    hexses_target = open_lst(hexses_target_path)

    logging.info("Combining and saving unique hex locations...")
    hexses = pd.concat([hexses_data, hexses_target]).drop_duplicates().reset_index(drop=True)
    logging.info(f"Total unique locations: {hexses.shape[0]}")
    hexses.to_csv(locations_csv_path, index=False)
    logging.info(f"Saved locations to {locations_csv_path}")

    # --- Convert Parquet files to CSV --- 
    logging.info(f"Converting {transactions_parquet_path} to CSV...")
    pd.read_parquet(transactions_parquet_path).to_csv(transactions_csv_path, index=True, index_label='transaction_pk')
    logging.info(f"Saved transactions to {transactions_csv_path}")

    logging.info(f"Converting {target_parquet_path} to CSV...")
    pd.read_parquet(target_parquet_path).to_csv(cash_withdrawals_csv_path, index=False)
    logging.info(f"Saved cash withdrawals to {cash_withdrawals_csv_path}")

    # --- Process Moscow data --- 
    logging.info(f"Reading Moscow POI data from {moscow_parquet_path}...")
    moscow = pd.read_parquet(moscow_parquet_path, engine='pyarrow')

    logging.info("Processing Moscow data (filtering, calculating h3, finding nearest centers)...")
    moscow = moscow[moscow['tags'].notna()].copy()
    logging.info(f"Filtered Moscow POIs: {moscow.shape[0]}")

    # Calculate h3 index for Moscow POIs
    moscow['h3_09'] = moscow[['lat','lon']].apply(lambda row: h3.latlng_to_cell(row['lat'], row['lon'], 9), axis=1)

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
    logging.info(f"Saved processed Moscow data to {moscow_csv_path}")

    logging.info("Preprocessing finished.")

if __name__ == "__main__":
    preprocess_data(configs)