#!/bin/bash

mkdir -p data/raw
curl -o data/raw/hexses_target.lst https://storage.yandexcloud.net/ds-ods/files/data/docs/competitions/DataFusion2024/Data/geo/hexses_target.lst
curl -o data/raw/transactions.parquet https://storage.yandexcloud.net/ds-ods/files/data/docs/competitions/DataFusion2024/Data/geo/transactions.parquet
curl -o data/raw/target.parquet https://storage.yandexcloud.net/ds-ods/files/data/docs/competitions/DataFusion2024/Data/geo/target.parquet
curl -o data/raw/hexses_data.lst https://storage.yandexcloud.net/ds-ods/files/data/docs/competitions/DataFusion2024/Data/geo/hexses_data.lst
curl -o data/raw/moscow.parquet https://storage.yandexcloud.net/ds-ods/files/data/docs/competitions/DataFusion2024/Data/geo/moscow.parquet