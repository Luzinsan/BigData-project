import math
import h3
import pandas as pd
import numpy as np
from sklearn.neighbors import BallTree


hexses = pd.read_parquet("src/data/hexses.parquet")
summary_shape = 0
try:
    path = 'src/data/moscow.parquet'
    best_engine = 'pyarrow'
    moscow = pd.read_parquet(path, engine=best_engine)
    moscow.name = 'moscow'
    moscow = moscow[moscow['tags'].notna()]
    print("Moscow shape: ", moscow.shape)
    summary_shape += moscow.shape[0]
    moscow['h3_09'] =  moscow[['lat','lon']].apply(lambda row: h3.latlng_to_cell(row['lat'], row['lon'], 9), axis=1) 
    unique_h3 = hexses['h3_09'].unique()
    coords_data1 = [h3.cell_to_latlng(h) for h in unique_h3]
    coords_data1_rad = np.radians(coords_data1)
    tree = BallTree(coords_data1_rad, metric='haversine')
    data2_coords = moscow['h3_09'].apply(lambda h: h3.cell_to_latlng(h)).tolist()
    data2_coords_rad = np.radians(data2_coords) 

    distances, indices = tree.query(data2_coords_rad, k=1)
    nearest_indices = indices.flatten()  
    moscow['h3_09_centers'] = [unique_h3[i] for i in nearest_indices]

    moscow.to_parquet("src/data/moscow_updated.parquet", index=False)
except FileNotFoundError:
    print("Error: File transactions.parquet wasn't found.  Put the proper path.")