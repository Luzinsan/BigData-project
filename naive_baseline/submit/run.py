#! /usr/bin/env python3
# -*- coding: utf-8 -*-
from datetime import datetime
from pathlib import Path
from typing import Annotated
from warnings import simplefilter

import pandas as pd
import typer
from typer import Option
import json

app = typer.Typer()

def main(
  hexses_target_path: Annotated[
    Path, Option('--hexses-target-path', '-ht', dir_okay=False, help='Список локаций таргета', show_default=True, exists=True)
  ] = 'hexses_target.lst',
  hexses_data_path: Annotated[
    Path, Option('--hexses-data-path', '-hd', dir_okay=False, help='Список локаций транзакций', show_default=True, exists=True)
  ] = 'hexses_data.lst',
  input_path: Annotated[
    Path, Option('--input-path', '-i', dir_okay=False, help='Входные данные', show_default=True, exists=True)
  ] = 'moscow_transaction_data01.parquet',
  output_path: Annotated[
    Path, Option('--output-path', '-o', dir_okay=False, help='Выходные данные', show_default=True)
  ] = 'output.parquet',
):
    with open(hexses_target_path, "r") as f:
        hexses_target = [x.strip() for x in f.readlines()]
    with open(hexses_data_path, "r") as f:
        hexses_data = [x.strip() for x in f.readlines()]
    with open("means.json", "r") as f:
        means = json.load(f)['target']
    customers = pd.read_parquet(input_path).customer_id.unique()
    submit = pd.DataFrame({"customer_id": customers} | {x: [means[x]] * len(customers) for x in hexses_target}, index=customers).sort_index()
    submit.to_parquet(output_path)

if __name__ == '__main__':
  typer.run(main, )
