from time import time
import math
import h3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from tabulate import tabulate
import seaborn as sns

def open_lst(path):
    with open(path, "r") as f:
        df = pd.DataFrame({'h3_09': [x.strip() for x in f.readlines()]})
        df[['lat', 'lon']] = df['h3_09'].apply(h3.cell_to_latlng).to_list()
    return df

hexses_data = open_lst('src/data/hexses_data.lst')
hexses_data.name = 'hexses_data'
# print("hexses_data shape: ", hexses_data.shape)
summary_shape = hexses_data.shape[0]
hexses_target = open_lst('src/data/hexses_target.lst')
hexses_target.name = 'hexses_target'
# print("hexses_target shape: ", hexses_target.shape)
summary_shape += hexses_target.shape[0]
# print("Summary shape: ", summary_shape)

hexses = pd.concat([hexses_data, hexses_target]).drop_duplicates().reset_index(drop=True)
hexses.name = 'hexses'
print(hexses.shape[0])
hexses.to_parquet("src/data/hexses.parquet", index=False)