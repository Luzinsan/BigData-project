#! /bin/bash

# stage #1
./src/app/scripts/db/data_collection.sh
source ./.venv/bin/activate
python ./src/app/scripts/db/preprocessing.py
python ./src/app/scripts/db/build_projectdb.py

# stage #2
./src/app/scripts/db/import_to_hdfs.sh
./src/app/scripts/hive/create_hive.sh
./src/app/scripts/hive/eda.sh


# stage #3
./src/app/modelling/run_trainings.sh

