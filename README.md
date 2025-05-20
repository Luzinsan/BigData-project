# ATM Network Optimization Project

## Business Understanding

The global cash logistics market, estimated at $26.53 billion in 2023, is expected to reach $54.46 billion in 2032, increasing by an average of 8.32% during the forecast period (2024-32). This project focuses on optimizing ATM network efficiency and customer experience for a financial institution by predicting cash withdrawal patterns at specific ATM locations.

### Project Overview
- **Goal**: Predict the probability of cash withdrawals at specific ATM locations (encoded as H3Index level 9 geospatial identifiers)
- **Data Source**: VTB Bank (Data Fusion Contest 2024)
- **Key Features**: Historical transaction data with aggregated statistics and H3Index geospatial features

### Business Objectives
- Optimize ATM network efficiency
- Improve cash replenishment strategies
- Reduce operational costs
- Enhance marketing effectiveness
- Increase customer satisfaction

### Success Criteria
- Reduce cash shortages at high-traffic ATMs by 10% within 6 months
- Increase transaction volume
- Improve customer satisfaction
- Increase NPS by 10 points
- Reduce cash-out complaints
- Drive revenue growth

### Technical Stack
- **Data Storage**: PostgreSQL, HDFS
- **Data Processing**: Apache Spark, Pandas, NumPy
- **Geospatial Analytics**: H3 Indexing, GeoPandas
- **Machine Learning**: SparkML
- **Visualization**: Matplotlib, Superset
- **Infrastructure**: IU Hadoop cluster (3-node architecture)

### Data Mining Objectives
- Develop predictive models for cash withdrawal probability at ATM locations
- Analyze transaction patterns and their relationship with time of day
- Identify optimal and suboptimal ATM locations
- Create interpretable models with feature importance analysis

### Methodology
1. **Data Collection & Preprocessing**
   - Download and process transaction data
   - Clean and validate geospatial data
   - Handle missing values and outliers

2. **Exploratory Data Analysis**
   - Analyze transaction patterns
   - Study temporal and spatial distributions
   - Identify key features and correlations

3. **Model Development**
   - Implement multiple models (Linear Regression, Decision Tree, Random Forest, MLP)
   - Perform feature engineering and selection
   - Optimize hyperparameters

4. **Evaluation & Deployment**
   - Assess model performance using appropriate metrics
   - Validate business impact
   - Deploy insights for ATM network optimization

### Project Team
- Anastassiya Luzinsan
- Diana Semenova
- Zlata Soluyanova

## Getting Started

For detailed setup instructions and development guidelines, please refer to [CONTRIBUTING.md](CONTRIBUTING.md).

## Dataset Description

The dataset description can be found at: https://ods.ai/competitions/data-fusion2024-geo

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


To test different compression methods and data formats (Parquet and Avro), PostgreSQL client (psql) was installed in the home directory. You can activate it by running the following command, but you can skip this step since the optimal parameters are already used in import_to_hdfs.sh:
```bash
export PATH=$HOME/postgresql/bin:$PATH
./src/app/scripts/db/test_imports.sh
```

Now, to load data into HDFS, you need to run the following command:
```bash
./src/app/scripts/db/import_to_hdfs.sh
```

To load tables into Hive with partitioning and bucketing, execute the following script:
```bash
./src/app/scripts/hive/create_hive.sh
```

The following script executes queries from `src/app/scripts/hive/queries` directory to perform EDA, with results being written to `output/hive/eda`:
```bash
./src/app/scripts/hive/eda.sh
```

Result tables:

| tab_name |
|----------|
| cash_withdrawals |
| cleaned_moscow |
| locations |
| moscow |
| q4_results |
| transactions |
| transactions_per_h3 |
| withdraw_rate |
| word_frequency |

To run training for all models (Linear Regressor, Decision Tree, Random Forest, MLP), execute the following script:
```bash
./src/app/modelling/run_trainings.sh
```