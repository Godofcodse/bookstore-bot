from config import DB_CONFIG
import mysql.connector
import time
import logging
from mysql.connector import errorcode

logger = logging.getLogger(__name__)

def get_db_connection(max_retries=3, retry_delay=2):
    """ایجاد اتصال به دیتابیس MySQL با قابلیت تلاش مجدد"""
    logger.info("=" * 50)
    logger.info("🔄 تلاش برای اتصال به دیتابیس...")
    logger.info(f"   Host: {DB_CONFIG.get('host', 'NOT SET')}")
    logger.info(f"   Database: {DB_CONFIG.get('database', 'NOT SET')}")
    logger.info(f"   User: {DB_CONFIG.get('user', 'NOT SET')}")
    logger.info(f"   Port: {DB_CONFIG.get('port', 'NOT SET')}")
    logger.info("=" * 50)
    
    for attempt in range(max_retries):
        try:
            logger.info(f"📡 تلاش برای اتصال (تلاش {attempt + 1}/{max_retries})...")
            
            # ایجاد اتصال با تنظیمات اضافی
            conn = mysql.connector.connect(
                **DB_CONFIG,
                autocommit=True,
                connection_timeout=10,
                buffered=True  # مهم: جلوگیری از Unread result
            )
            
            # تست اتصال با cursor بافر شده
            cursor = conn.cursor(buffered=True)
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            
            if result and result[0] == 1:
                logger.info("✅ اتصال به دیتابیس موفقیت‌آمیز بود")
                return conn
            else:
                logger.error("❌ تست اتصال ناموفق بود")
                conn.close()
                
        except mysql.connector.Error as e:
            logger.error(f"❌ خطای MySQL (تلاش {attempt + 1}): {e}")
            
            if e.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                logger.error("   دلیل: نام کاربری یا رمز عبور اشتباه")
            elif e.errno == errorcode.ER_BAD_DB_ERROR:
                logger.error(f"   دلیل: دیتابیس '{DB_CONFIG.get('database')}' وجود ندارد")
            elif e.errno == errorcode.CR_CONN_HOST_ERROR:
                logger.error(f"   دلیل: نمی‌توان به میزبان '{DB_CONFIG.get('host')}' متصل شد")
            
            if attempt < max_retries - 1:
                logger.info(f"⏳ صبر {retry_delay} ثانیه قبل از تلاش مجدد...")
                time.sleep(retry_delay)
            else:
                logger.error("💥 تمام تلاش‌ها ناموفق بود")
                return None
                
        except Exception as e:
            logger.error(f"❌ خطای غیرمنتظره در اتصال دیتابیس: {e}")
            return None
    
    return None