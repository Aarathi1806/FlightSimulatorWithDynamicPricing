import mysql.connector
from mysql.connector import Error
import config  # 🔒 your private credentials (ignored by Git)
def get_connection():
    try:
        connection = mysql.connector.connect(
            host=config.MYSQL_HOST,
            user=config.MYSQL_USER,
            password=config.MYSQL_PASSWORD,
            database=config.MYSQL_DATABASE
        )
        if connection.is_connected():
            print("Database connected successfully!")
            return connection
    except Error as e:
        print("Database connection failed:", e)
        return None




