from .connection import get_db_connection


def get_user(user_id):
    """دریافت اطلاعات کاربر"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()

        cursor.close()
        conn.close()
        return user

    except Exception as e:
        print(f"❌ خطا در دریافت کاربر: {e}")
        return None


#  CATEGORY QUERIES  
def get_all_categories():
    """دریافت همه دسته‌بندی‌ها"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT category_id, name 
            FROM categories 
            ORDER BY name
        """
        )

        categories = cursor.fetchall()
        cursor.close()
        conn.close()
        return categories

    except Exception as e:
        print(f"❌ خطا در دریافت دسته‌بندی‌ها: {e}")
        return []


def get_category_by_id(category_id):
    """دریافت اطلاعات یک دسته‌بندی"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM categories WHERE category_id = %s",
            (category_id,),
        )

        category = cursor.fetchone()
        cursor.close()
        conn.close()
        return category

    except Exception as e:
        print(f"❌ خطا در دریافت دسته‌بندی: {e}")
        return None


#  BOOK QUERIES  
def get_book(book_id):
    """دریافت اطلاعات کتاب با ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT b.*, c.name as category_name
            FROM books b
            LEFT JOIN categories c ON b.category_id = c.category_id
            WHERE b.book_id = %s
        """,
            (book_id,),
        )

        book = cursor.fetchone()
        cursor.close()
        conn.close()
        return book

    except Exception as e:
        print(f"❌ خطا در دریافت کتاب: {e}")
        return None


def get_books_by_category(category_id, limit=10):
    """دریافت کتاب‌های یک دسته‌بندی"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT b.*, c.name as category_name
            FROM books b
            LEFT JOIN categories c ON b.category_id = c.category_id
            WHERE b.category_id = %s AND b.is_active = TRUE
            ORDER BY b.title
            LIMIT %s
        """,
            (category_id, limit),
        )

        books = cursor.fetchall()
        cursor.close()
        conn.close()
        return books

    except Exception as e:
        print(f"❌ خطا در دریافت کتاب‌های دسته‌بندی: {e}")
        return []


def get_all_books(limit=20):
    """دریافت همه کتاب‌ها"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT b.*, c.name as category_name
            FROM books b
            LEFT JOIN categories c ON b.category_id = c.category_id
            WHERE b.is_active = TRUE
            ORDER BY b.created_at DESC
            LIMIT %s
        """,
            (limit,),
        )

        books = cursor.fetchall()
        cursor.close()
        conn.close()
        return books

    except Exception as e:
        print(f"❌ خطا در دریافت همه کتاب‌ها: {e}")
        return []


def search_books(query, limit=10):
    """جستجوی کتاب در دیتابیس داخلی"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        search_query = f"%{query}%"
        cursor.execute(
            """
            SELECT b.*, c.name as category_name
            FROM books b
            LEFT JOIN categories c ON b.category_id = c.category_id
            WHERE b.is_active = TRUE 
            AND (b.title LIKE %s OR b.author LIKE %s OR b.description LIKE %s)
            ORDER BY b.title
            LIMIT %s
        """,
            (search_query, search_query, search_query, limit),
        )

        books = cursor.fetchall()
        cursor.close()
        conn.close()
        return books

    except Exception as e:
        print(f"❌ خطا در جستجوی کتاب: {e}")
        return []


#  ADMIN QUERIES  
def is_admin(user_id):
    """بررسی اینکه آیا کاربر ادمین است"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT 1 FROM admins WHERE user_id = %s",
            (user_id,),
        )

        result = cursor.fetchone() is not None
        cursor.close()
        conn.close()
        return result

    except Exception as e:
        print(f"❌ خطا در بررسی ادمین: {e}")
        return False


def get_all_admins():
    """دریافت لیست همه ادمین‌ها"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT a.*, u.phone
            FROM admins a
            LEFT JOIN users u ON a.user_id = u.user_id
            ORDER BY a.added_at DESC
        """
        )

        admins = cursor.fetchall()
        cursor.close()
        conn.close()
        return admins

    except Exception as e:
        print(f"❌ خطا در دریافت ادمین‌ها: {e}")
        return []


#  CART QUERIES  
def get_user_cart(user_id):
    """دریافت سبد خرید کاربر"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT ci.*, b.title, b.author, b.price, b.file_id, b.cover_url
            FROM cart_items ci
            JOIN books b ON ci.book_id = b.book_id
            WHERE ci.user_id = %s
        """,
            (user_id,),
        )

        cart_items = []
        for row in cursor.fetchall():
            cart_items.append(
                {
                    "book_id": row["book_id"],
                    "title": row["title"],
                    "author": row["author"],
                    "price": row["price"],
                    "count": row["quantity"],
                    "file_id": row["file_id"],
                    "cover_url": row["cover_url"],
                }
            )

        cursor.close()
        conn.close()
        return cart_items

    except Exception as e:
        print(f"❌ خطا در دریافت سبد خرید: {e}")
        return []


def get_cart_total(user_id):
    """محاسبه جمع کل سبد خرید"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT SUM(b.price * ci.quantity)
            FROM cart_items ci
            JOIN books b ON ci.book_id = b.book_id
            WHERE ci.user_id = %s
        """,
            (user_id,),
        )

        total = cursor.fetchone()[0] or 0
        cursor.close()
        conn.close()
        return total

    except Exception as e:
        print(f"❌ خطا در محاسبه جمع کل: {e}")
        return 0


#  ORDER QUERIES 
def get_pending_orders():
    """دریافت سفارشات در انتظار تایید"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT o.*, u.phone, u.address, u.postal_code
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.user_id
            WHERE o.status = 'pending'
            ORDER BY o.created_at DESC
        """
        )

        orders = cursor.fetchall()
        cursor.close()
        conn.close()
        return orders

    except Exception as e:
        print(f"❌ خطا در دریافت سفارشات: {e}")
        return []


def get_order_items(order_id):
    """دریافت آیتم‌های یک سفارش"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM order_items WHERE order_id = %s", (order_id,))
        items = cursor.fetchall()

        cursor.close()
        conn.close()
        return items

    except Exception as e:
        print(f"❌ خطا در دریافت آیتم‌های سفارش: {e}")
        return []


def get_user_orders(user_id):
    """دریافت سفارشات کاربر"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT * FROM orders 
            WHERE user_id = %s 
            ORDER BY created_at DESC
        """,
            (user_id,),
        )

        orders = cursor.fetchall()
        cursor.close()
        conn.close()
        return orders

    except Exception as e:
        print(f"❌ خطا در دریافت سفارشات کاربر: {e}")
        return []
