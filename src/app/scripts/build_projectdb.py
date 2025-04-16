import os
from pprint import pprint
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from app.utils.pg_connect import PostgresHandler
from config.configs import configs


class DatabaseManager:

    def __init__(self, configs):
        self.configs = configs

    def create_tables(self):
        create_script_path = os.path.join(self.configs.SQL_SCRIPTS_DIR, "create_tables.sql") 
        print(f"Creating tables using {create_script_path}...")
        with open(create_script_path, "r") as file:
            create_commands = file.read()
        with PostgresHandler(self.configs) as handler:
            execution_time = handler.post(create_commands)
            print(f"Table creation completed in {execution_time:.2f} seconds")
        

    def import_data(self):
        data_files = {
            "locations": "locations.csv",
            "transactions": "transactions.csv",
            "cash_withdrawals": "cash_withdrawals.csv",
            "moscow": "moscow.csv"
        }
        print("Importing data...")
        with PostgresHandler(self.configs) as handler:
            for table, file_name in data_files.items():
                file_path = os.path.join(self.configs.DATA_DIR, file_name)
                print(f"Attempting to import {file_path} into table {table}...")
                execution_time = handler.copy_from(table, file_path)
                print(f"Successfully imported data into {table} in {execution_time:.2f} seconds")
                


if __name__ == "__main__":
    db_manager = DatabaseManager(configs)

    print("--- Running Table Creation ---")
    db_manager.create_tables()
    
    print("\n--- Running Data Import ---")
    db_manager.import_data()
    
    print("\nDatabase management script finished.")