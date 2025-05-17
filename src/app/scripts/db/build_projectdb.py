import os
import sys
from pathlib import Path
import logging
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from src.app.utils.pg_connect import PostgresHandler
from src.config.configs import settings, Settings
from src.app.utils.common import setup_logger


class DatabaseManager:

    def __init__(
            self, 
            settings: Settings, 
            logger: logging.Logger
        ):
        self.settings = settings
        self.sql_scripts_dir = Path(settings.SCRIPTS_DIR) / 'db'
        self.data_dir = Path(settings.DATA_DIR) / 'processed'
        self.logger = logger

    def create_tables(self):
        """
        Create the tables in the database:
        - locations
        - transactions
        - cash_withdrawals
        - moscow
        """
        create_script_path = self.sql_scripts_dir / "create_tables.sql" 
        self.logger.info(f"Creating tables using {create_script_path}...")
        with open(create_script_path, "r") as file:
            create_commands = file.read()
        with PostgresHandler(self.settings, self.logger) as handler:
            execution_time = handler.post(create_commands)
            self.logger.info(f"Table creation completed in {execution_time:.2f} seconds")
        

    def import_data(self):
        """
        Import the data into the database:
        - locations
        - transactions
        - cash_withdrawals
        - moscow
        """
        data_files = {
            "locations": "locations.csv",
            "transactions": "transactions.csv",
            "cash_withdrawals": "cash_withdrawals.csv",
            "moscow": "moscow.csv"
        }
        self.logger.info("Importing data...")
        with PostgresHandler(self.settings, self.logger) as handler:
            for table, file_name in data_files.items():
                file_path = self.data_dir / file_name
                self.logger.info(f"Attempting to import {file_path} into table {table}...")
                execution_time = handler.copy_from(table, file_path)
                self.logger.info(f"Successfully imported data into {table} in {execution_time:.2f} seconds")
                


if __name__ == "__main__":
    logger = setup_logger()
    db_manager = DatabaseManager(settings, logger)

    logger.info("--- Running Table Creation ---")
    db_manager.create_tables()
    
    logger.info("--- Running Data Import ---")
    db_manager.import_data()
    
    logger.info("Database management script finished.")