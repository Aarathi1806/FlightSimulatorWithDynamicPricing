import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_config import get_connection
def get_domestic_flights():
    try:
        conn = get_connection()
        if not conn:
            print("Database connection failed")
            return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM domestic_flights")
        results = cursor.fetchall()
        print(f"Found {len(results)} domestic flights")
        cursor.close()
        conn.close()
        return results
    except Exception as e:
        print(f"Error in get_domestic_flights: {e}")
        import traceback
        traceback.print_exc()
        return []
def get_international_flights():
    try:
        conn = get_connection()
        if not conn:
            print(" Database connection failed")
            return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM international_flights")
        results = cursor.fetchall()
        print(f" Found {len(results)} international flights")
        cursor.close()
        conn.close()
        return results
    except Exception as e:
        print(f"Error in get_international_flights: {e}")
        import traceback
        traceback.print_exc()
        return []




