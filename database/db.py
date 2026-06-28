import sqlite3

class Database:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = sqlite3.connect("multidrive.db")
        return cls._instance

    @classmethod
    def init_db(cls):
        connection = cls.get_instance()
        with open("database/schema.sql", "r") as f:
            sql = f.read()
        connection.executescript(sql)
