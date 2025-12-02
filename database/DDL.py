from .connection import get_db_connection


def create_tables():
    """ایجاد جداول دیتابیس کامل"""
    try:
        conn = get_db_connection()
        if conn is None:
            return False

        cursor = conn.cursor()

        # جدول users
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT NOT NULL PRIMARY KEY,
                phone VARCHAR(20),
                address TEXT,
                postal_code VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # جدول categories (جدید)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                category_id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # جدول books 
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS books (
                book_id INT AUTO_INCREMENT PRIMARY KEY,
                book_key VARCHAR(255),
                title VARCHAR(255) NOT NULL,
                author VARCHAR(255),
                description TEXT,
                cover_url TEXT,
                file_id VARCHAR(200),  # آیدی فایل عکس در تلگرام
                price INT NOT NULL DEFAULT 0,
                category_id INT,
                stock INT DEFAULT 1,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(category_id) ON DELETE SET NULL
            )
        """
        )

        # جدول cart_items
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cart_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                book_id INT NOT NULL,
                quantity INT DEFAULT 1,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE CASCADE,
                UNIQUE KEY unique_user_book (user_id, book_id)
            )
        """
        )

        # جدول orders
        cursor.execute(
            """
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
        """
        )

        # جدول order_items
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS order_items (
                item_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                order_id INT,
                book_id INT,
                title VARCHAR(255),
                author VARCHAR(255),
                price INT,
                count INT
            )
        """
        )

        # جدول admins (جدید)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                admin_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL UNIQUE,
                username VARCHAR(100),
                is_super_admin BOOLEAN DEFAULT FALSE,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        conn.commit()
        cursor.close()
        conn.close()
        print("✅ تمام جداول با موفقیت ایجاد شدند!")
        return True

    except Exception as e:
        print(f"❌ خطا در ایجاد جداول: {e}")
        return False