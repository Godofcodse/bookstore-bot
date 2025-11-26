from .connection import get_db_connection


# ========== USER OPERATIONS ==========
def save_user(user_id, phone=None, address=None, postal_code=None):
    """ذخیره کاربر - مطابق جدول users"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO users (user_id, phone, address, postal_code)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            phone = VALUES(phone),
            address = VALUES(address),
            postal_code = VALUES(postal_code)
        """,
            (user_id, phone, address, postal_code),
        )

        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ خطا در ذخیره کاربر: {e}")
        return False


# ========== BOOK OPERATIONS ==========
def save_book(book_key, title, author, cover_url, price):
    """ذخیره کتاب - مطابق جدول books"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO books (book_key, title, author, cover_url, price)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            title = VALUES(title),
            author = VALUES(author),
            cover_url = VALUES(cover_url),
            price = VALUES(price)
        """,
            (book_key, title, author, cover_url, price),
        )

        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ خطا در ذخیره کتاب: {e}")
        return False


# ========== CART OPERATIONS ==========
def add_to_cart(user_id, book_key, title, author, price):
    """افزودن کتاب به سبد خرید"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO cart_items (user_id, book_key, title, author, price, quantity)
            VALUES (%s, %s, %s, %s, %s, 1)
            ON DUPLICATE KEY UPDATE
            quantity = quantity + 1
        """,
            (user_id, book_key, title, author, price),
        )

        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ خطا در افزودن به سبد: {e}")
        return False


def update_cart_quantity(user_id, book_key, change):
    """آپدیت تعداد کتاب در سبد"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if change == 0:  # حذف
            cursor.execute(
                "DELETE FROM cart_items WHERE user_id = %s AND book_key = %s",
                (user_id, book_key),
            )
        else:
            cursor.execute(
                """
                UPDATE cart_items 
                SET quantity = quantity + %s 
                WHERE user_id = %s AND book_key = %s
            """,
                (change, user_id, book_key),
            )

        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ خطا در آپدیت سبد: {e}")
        return False


def clear_user_cart(user_id):
    """پاک کردن سبد خرید کاربر"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM cart_items WHERE user_id = %s", (user_id,))

        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ خطا در پاک کردن سبد: {e}")
        return False


# ========== ORDER OPERATIONS ==========
def create_order(user_id, total_price, receipt_photo, phone, address, postal_code):
    """ایجاد سفارش کامل - آپدیت شده"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO orders (user_id, total_price, receipt_photo, phone, address, postal_code)
            VALUES (%s, %s, %s, %s, %s, %s)
        """,
            (user_id, total_price, receipt_photo, phone, address, postal_code),
        )

        order_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()

        return order_id

    except Exception as e:
        print(f"❌ خطا در ایجاد سفارش: {e}")
        return None


def add_order_item(order_id, title, author, price, count):
    """افزودن آیتم سفارش - مطابق جدول order_items"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO order_items (order_id, title, author, price, count)
            VALUES (%s, %s, %s, %s, %s)
        """,
            (order_id, title, author, price, count),
        )

        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ خطا در افزودن آیتم سفارش: {e}")
        return False


def update_order_status(order_id, status):
    """آپدیت وضعیت سفارش - مطابق جدول orders"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE orders SET status = %s WHERE order_id = %s", (status, order_id)
        )

        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ خطا در آپدیت وضعیت سفارش: {e}")
        return False
