import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
class Database:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = psycopg2.connect(DATABASE_URL)
        return cls._instance

    @classmethod
    def init_db(cls):
        connection = cls.get_instance()
        cursor = connection.cursor()
        with open("database/schema.sql", "r") as f:
            sql = f.read()
        cursor.execute(sql)
        connection.commit()