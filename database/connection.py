from config import DB_CONFIG
import mysql.connector

def get_db_connection():
    """ایجاد اتصال به دیتابیس MySQL"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"❌ خطا در اتصال به دیتابیس: {e}")
        return None