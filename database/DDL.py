from .connection import get_db_connection

def create_tables():
    """ایجاد جداول دیتابیس کامل"""
    try:
        conn = get_db_connection()
        if conn is None:
            return False
            
        cursor = conn.cursor()
        
        # جدول users
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT NOT NULL PRIMARY KEY,
                phone VARCHAR(20),
                address TEXT,
                postal_code VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # جدول books
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS books (
                book_key VARCHAR(255) NOT NULL PRIMARY KEY,
                title VARCHAR(255),
                author VARCHAR(255),
                cover_url TEXT,
                price INT
            )
        """)
        
        # جدول cart_items - جدید
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cart_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                book_key VARCHAR(255) NOT NULL,
                title VARCHAR(255),
                author VARCHAR(255),
                price INT,
                quantity INT DEFAULT 1,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (book_key) REFERENCES books(book_key) ON DELETE CASCADE,
                UNIQUE KEY unique_user_book (user_id, book_key)
            )
        """)
        
        # جدول orders - آپدیت شده
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT,
                total_price INT,
                receipt_photo VARCHAR(200),
                phone VARCHAR(20),
                address TEXT,
                postal_code VARCHAR(20),
                status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # جدول order_items
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                item_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                order_id INT,
                title VARCHAR(255),
                author VARCHAR(255),
                price INT,
                count INT
            )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ تمام جداول با موفقیت ایجاد شدند!")
        return True
        
    except Exception as e:
        print(f"❌ خطا در ایجاد جداول: {e}")
        return False