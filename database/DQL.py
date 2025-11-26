from .connection import get_db_connection


def get_user(user_id):
    """دریافت اطلاعات کاربر - مطابق جدول users"""
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


def get_book(book_key):
    """دریافت اطلاعات کتاب - مطابق جدول books"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM books WHERE book_key = %s", (book_key,))
        book = cursor.fetchone()

        cursor.close()
        conn.close()
        return book

    except Exception as e:
        print(f"❌ خطا در دریافت کتاب: {e}")
        return None


def get_user_cart(user_id):
    """دریافت سبد خرید کاربر"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT book_key, title, author, price, quantity 
            FROM cart_items 
            WHERE user_id = %s
        """,
            (user_id,),
        )

        cart_items = {}
        for row in cursor.fetchall():
            cart_items[row["book_key"]] = {
                "title": row["title"],
                "author": row["author"],
                "price": row["price"],
                "count": row["quantity"],
            }

        cursor.close()
        conn.close()
        return cart_items

    except Exception as e:
        print(f"❌ خطا در دریافت سبد خرید: {e}")
        return {}


def get_cart_total(user_id):
    """محاسبه جمع کل سبد خرید"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT SUM(price * quantity)
            FROM cart_items 
            WHERE user_id = %s
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


def get_pending_orders():
    """دریافت سفارشات در انتظار تایید - مطابق جدول orders"""
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
    """دریافت آیتم‌های یک سفارش - مطابق جدول order_items"""
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
    """دریافت سفارشات کاربر - مطابق جدول orders"""
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
