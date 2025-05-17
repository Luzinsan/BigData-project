import psycopg2
from psycopg2 import sql
from psycopg2.extensions import connection as pg_connection
from typing import Optional, Tuple
from time import time
from typing import List
import pandas as pd
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.config.configs import settings, Settings


class PostgresHandler:
    """
    A class for handling PostgreSQL connections.
    """
    def __init__(self, configs: Settings, logger: logging.Logger):
        """
        Initialize the PostgresHandler.
        Args:
            configs (Settings): The settings for the project.
            logger (logging.Logger): The logger for the project.
        """
        self.pg_conn: Optional[pg_connection] = None
        self.config = dict(
            dbname=configs.DB_NAME,
            host=configs.DB_HOST,
            port=configs.DB_PORT,
            user=configs.DB_USER,
            password=configs.DB_PASSWORD
        )
        self.logger = logger
    def __enter__(self):
        self.pg_conn = psycopg2.connect(**self.config)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.pg_conn:
            self.pg_conn.close()

    def post(self, query: str) -> float:
        """
        Execute a query without returning any results and return the execution time.
        Args:
            query (str): The query to execute.
        Returns:
            float: The execution time.
        """
        start_time = time()
        try:
            with self.pg_conn.cursor() as cursor:
                cursor.execute(sql.SQL(query))
                
            self.pg_conn.commit()
            return time() - start_time
        except (Exception, psycopg2.Error) as error:
            logging.error("Error while executing query: ", error)
            return 0.0
        
    def copy_from(self, table: str, table_path: str) -> float:
        """
        Copy data from a file to a table and return the execution time.
        Args:
            table (str): The table to copy data to.
            table_path (str): The path to the file to copy data from.
        Returns:
            float: The execution time.
        """
        start_time = time()
        try:
            with self.pg_conn.cursor() as cursor:
                with open(table_path, 'r') as f:
                    copy_sql = sql.SQL("COPY {} FROM STDIN WITH (FORMAT CSV, HEADER TRUE)").format(sql.Identifier(table))
                    cursor.copy_expert(copy_sql, f)
            self.pg_conn.commit()
            return time() - start_time  
        except (Exception, psycopg2.Error) as error:
            logging.error(f"Error while copying data into PostgreSQL table {table} from {table_path}: ", error)
            self.pg_conn.rollback()
            return 0.0

    def get(self, query: str) -> Tuple[List[tuple], float]:
        """
        Execute a query and return the results and the execution time.
        Args:
            query (str): The query to execute.
        Returns:
            Tuple[List[tuple], float]: The results and the execution time.
        """
        start_time = time()
        try:
            return pd.read_sql(query, self.pg_conn), \
                time() - start_time
        except (Exception, psycopg2.Error) as error:
            logging.error("Error while sending data into PostgreSQL", error)
            return (), 0.0

    @staticmethod
    def send(query: str, logger: logging.Logger) -> pd.DataFrame:
        """
        Execute a query and return the results.
        Args:
            query (str): The query to execute.
            logger (logging.Logger): Instance of logging.Logger.
        Returns:
            pd.DataFrame: The results.
        """
        logger.info(f"Executing query: {query[:100]}...")
        try:
            with PostgresHandler(settings, logger) as handler:
                result, execution_time = handler.get(query)
                logger.info(f"Query executed successfully in {execution_time:.2f} seconds")
                return result
        except Exception as e:
            logger.error(f"Error while executing query: {str(e)}")
            raise
