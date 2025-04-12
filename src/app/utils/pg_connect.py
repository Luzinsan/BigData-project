import psycopg2
from psycopg2 import sql
from psycopg2.extensions import connection as pg_connection
from typing import Optional, Tuple
from time import time
from typing import List
import pandas as pd
import logging
from src.config.configs import configs


class PostgresHandler:
    def __init__(self, configs):
        self.pg_conn: Optional[pg_connection] = None
        self.config = dict(
            dbname=configs.DB_NAME,
            host=configs.DB_HOST,
            port=configs.DB_PORT,
            user=configs.DB_USER,
            password=configs.DB_PASSWORD
        )

    def __enter__(self):
        self.pg_conn = psycopg2.connect(**self.config)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.pg_conn:
            self.pg_conn.close()

    def post(self, query: str) -> float:
        start_time = time()
        try:
            with self.pg_conn.cursor() as cursor:
                cursor.execute(sql.SQL(query))
                self.pg_conn.commit()
                return time() - start_time
        except (Exception, psycopg2.Error) as error:
            print("Error while sending data into PostgreSQL", error)
            return 0.0

    def get(self, query: str) -> Tuple[List[tuple], float]:
        start_time = time()
        try:
            return pd.read_sql(query, self.pg_conn), \
                time() - start_time
        except (Exception, psycopg2.Error) as error:
            print("Error while sending data into PostgreSQL", error)
            return (), 0.0

    @staticmethod
    def send(query: str) -> pd.DataFrame:
        logging.info(f"Executing query: {query[:100]}...")
        try:
            with PostgresHandler(configs) as handler:
                result, execution_time = handler.get(query)
                logging.info(f"Запрос выполнен успешно за {execution_time:.2f} сек")
                return result
        except Exception as e:
            logging.error(f"Ошибка при выполнении запроса: {str(e)}")
            raise
