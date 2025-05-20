# Contributing to ATM Network Optimization Project

## Development Setup

### Prerequisites
- Python 3.11 (required version)
- PostgreSQL
- Apache Hadoop
- Apache Spark
- Apache Hive

### Project Structure
```
.
├── data/                  # Data directory
│   └── raw/              # Raw data files
├── notebooks/            # Jupyter notebooks
├── output/              # Output files and results
│   └── hive/
│       └── eda/         # EDA results
├── src/                 # Source code
│   ├── app/            # Application code
│   │   ├── modelling/  # ML models
│   │   ├── scripts/    # Scripts for data processing
│   │   └── utils/      # Utility functions
│   └── config/         # Configuration files
└── .venv/              # Virtual environment
```

### Dependencies
The project uses the following key dependencies:

#### Data Processing & Analysis
- `numpy==2.2.2`: Numerical computing
- `pandas`: Data manipulation
- `pyspark>=3.5.4`: Distributed computing
- `pyarrow>=19.0.1`: Data serialization
- `fastparquet>=2024.11.0`: Parquet file handling

#### Geospatial
- `geopandas>=1.0.1`: Geospatial data handling
- `h3>=4.2.2`: H3 geospatial indexing
- `contextily>=1.6.2`: Base maps for geospatial visualization
- `folium>=0.19.5`: Interactive maps

#### Machine Learning
- `scikit-learn==1.6.1`: Machine learning algorithms
- `torch==2.0.1`: Deep learning
- `torchvision>=0.15.2`: Computer vision utilities

#### Visualization
- `matplotlib>=3.10.1`: Basic plotting
- `seaborn>=0.13.2`: Statistical visualizations
- `jupyter>=1.1.1`: Interactive development
- `notebook>=7.3.2`: Jupyter notebook support

#### Database
- `psycopg2-binary>=2.9.10`: PostgreSQL adapter

#### Utilities
- `tqdm>=4.67.1`: Progress bars
- `tabulate>=0.9.0`: Pretty-printing tables
- `pydantic-settings>=2.8.1`: Configuration management

### Environment Setup

1. **Clone the repository**
```bash
git clone [repository-url]
cd [repository-name]
```

2. **Create and activate virtual environment**
```bash
python -m venv .venv
source ./.venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

### Data Pipeline

1. **Data Collection**
```bash
./src/app/scripts/db/data_collection.sh
```
This will download the following files to `data/raw`:
- hexses_data.lst
- hexses_target.lst
- moscow.parquet
- target.parquet
- transactions.parquet

2. **Data Preprocessing**
```bash
python ./src/app/scripts/db/preprocessing.py
```

3. **Database Setup**
```bash
python ./src/app/scripts/db/build_projectdb.py
```

4. **HDFS Import**
```bash
./src/app/scripts/db/import_to_hdfs.sh
```

5. **Hive Table Creation**
```bash
./src/app/scripts/hive/create_hive.sh
```

### Development Workflow

1. **EDA Execution**
```bash
./src/app/scripts/hive/eda.sh
```
Results will be written to `output/hive/eda`

2. **Model Training**
```bash
./src/app/modelling/run_trainings.sh
```
This will train all models:
- Linear Regressor
- Decision Tree
- Random Forest
- MLP

### Available Tables

| Table Name | Description |
|------------|-------------|
| cash_withdrawals | Cash withdrawal transactions |
| cleaned_moscow | Processed Moscow location data |
| locations | ATM locations |
| moscow | Raw Moscow location data |
| q4_results | Query results |
| transactions | Transaction records |
| transactions_per_h3 | Transactions aggregated by H3 index |
| withdraw_rate | Withdrawal rate statistics |
| word_frequency | Text analysis results |

### Testing

For testing different compression methods and data formats:
```bash
export PATH=$HOME/postgresql/bin:$PATH
./src/app/scripts/db/test_imports.sh
```

### Best Practices

1. **Code Style**
   - Follow PEP 8 guidelines
   - Use meaningful variable names
   - Add docstrings to functions and classes

2. **Version Control**
   - Create feature branches for new development
   - Write clear commit messages
   - Keep commits focused and atomic

3. **Documentation**
   - Update documentation when changing functionality
   - Include examples in docstrings
   - Document any assumptions or limitations

4. **Testing**
   - Write unit tests for new functionality
   - Ensure all tests pass before committing
   - Include edge cases in tests

### Troubleshooting

1. **Cluster Issues**
   - Check cluster status: `hdfs dfsadmin -report`
   - Verify Hive service: `beeline -u jdbc:hive2://`
   - Monitor Spark jobs: Spark UI

2. **Database Issues**
   - Check PostgreSQL connection
   - Verify table permissions
   - Monitor query performance

3. **Data Pipeline Issues**
   - Check file permissions
   - Verify data formats
   - Monitor disk space

### Support

For technical issues:
- Contact TA for cluster troubleshooting
- Use project issue tracker
- Consult team documentation 