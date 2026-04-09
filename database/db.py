import pymysql
import sys
import os

# Import config from parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG

def get_connection():
    """
    Establishes and returns a connection to the MySQL database.
    
    Returns:
        pymysql.connections.Connection: Database connection object
        
    Raises:
        Exception: If connection fails
    """
    try:
        config = DB_CONFIG.copy()
        config["cursorclass"] = pymysql.cursors.DictCursor
        connection = pymysql.connect(**config)
        return connection
    except Exception as e:
        print(f"Database connection failed: {e}")
        raise
