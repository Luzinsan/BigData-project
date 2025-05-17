> All following commands should be executed from the project root directory

For dataset downloading you need to execute:
```bash
./src/app/scripts/db/data_collection.sh
```
After executing the script, the following files will be downloaded to the data/raw directory:
- hexses_data.lst
- hexses_target.lst
- moscow.parquet
- target.parquet
- transactions.parquet

You can see dataset description here: https://ods.ai/competitions/data-fusion2024-geo

Activate the environment:
```bash
source ./.venv/bin/activate
``` 

Then, execute script for preprocess data:
```bash
python ./src/app/scripts/db/preprocessing.py
```

To create tables and load data into PostgreSQL, run the following command:
```bash
python ./src/app/scripts/db/build_projectdb.py
```

```bash
./src/app/scripts/db/import_to_hdfs.sh
```

To test different compression methods and data formats (Parquet and Avro), PostgreSQL client (psql) was installed in the home directory. You can activate it by running the following command, but you can skip this step since the optimal parameters are already used in import_to_hdfs.sh:
```bash
export PATH=$HOME/postgresql/bin:$PATH
```

Now, to load data into HDFS, you need to run the following command:
```bash
./src/app/scripts/db/import_to_hdfs.sh
```

