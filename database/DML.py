from .connection import get_db_connection


#  USER OPERATIONS 
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


#  CATEGORY OPERATIONS  
def add_category(name):
    """اضافه کردن دسته‌بندی جدید"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO categories (name)
            VALUES (%s)
            ON DUPLICATE KEY UPDATE name = VALUES(name)
        """,
            (name,),
        )

        conn.commit()
        category_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return category_id

    except Exception as e:
        print(f"❌ خطا در اضافه کردن دسته‌بندی: {e}")
        return None


def delete_category(category_id):
    """حذف دسته‌بندی"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM categories WHERE category_id = %s",
            (category_id,),
        )

        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ خطا در حذف دسته‌بندی: {e}")
        return False


#  BOOK OPERATIONS  
def save_book(
    book_key,
    title,
    author,
    cover_url,
    price,
    category_id=None,
    description="",
    file_id=None,
):
    """ذخیره کتاب - مطابق جدول books"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO books (book_key, title, author, cover_url, price, category_id, description, file_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            title = VALUES(title),
            author = VALUES(author),
            cover_url = VALUES(cover_url),
            price = VALUES(price),
            category_id = VALUES(category_id),
            description = VALUES(description),
            file_id = VALUES(file_id)
        """,
            (
                book_key,
                title,
                author,
                cover_url,
                price,
                category_id,
                description,
                file_id,
            ),
        )

        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ خطا در ذخیره کتاب: {e}")
        return False


def add_book_full(
    title,
    author,
    description,
    price,
    category_id,
    file_id=None,
    cover_url=None,
    stock=1,
):
    """اضافه کردن کتاب با جزئیات کامل """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO books (title, author, description, price, category_id, file_id, cover_url, stock)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
            (title, author, description, price, category_id, file_id, cover_url, stock),
        )

        book_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        return book_id

    except Exception as e:
        print(f"❌ خطا در اضافه کردن کتاب: {e}")
        return None


def update_book(book_id, **kwargs):
    """آپدیت اطلاعات کتاب"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if not kwargs:
            return False

        set_clause = ", ".join([f"{k} = %s" for k in kwargs.keys()])
        values = list(kwargs.values())
        values.append(book_id)

        cursor.execute(
            f"""
            UPDATE books 
            SET {set_clause}
            WHERE book_id = %s
        """,
            values,
        )

        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ خطا در آپدیت کتاب: {e}")
        return False


def delete_book(book_id):
    """حذف کتاب"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM books WHERE book_id = %s",
            (book_id,),
        )

        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ خطا در حذف کتاب: {e}")
        return False


#  ADMIN OPERATIONS  
def add_admin(user_id, username=None, is_super_admin=False):
    """اضافه کردن ادمین"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO admins (user_id, username, is_super_admin)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            username = VALUES(username),
            is_super_admin = VALUES(is_super_admin)
        """,
            (user_id, username, is_super_admin),
        )

        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ خطا در اضافه کردن ادمین: {e}")
        return False


def remove_admin(user_id):
    """حذف ادمین"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM admins WHERE user_id = %s",
            (user_id,),
        )

        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ خطا در حذف ادمین: {e}")
        return False


#  CART OPERATIONS  
def add_to_cart(user_id, book_id, quantity=1):
    """افزودن کتاب به سبد خرید """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # اول اطلاعات کتاب رو بگیریم
        cursor.execute(
            "SELECT title, author, price FROM books WHERE book_id = %s",
            (book_id,),
        )
        book = cursor.fetchone()

        if not book:
            return False

        cursor.execute(
            """
            INSERT INTO cart_items (user_id, book_id, quantity)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
            quantity = quantity + VALUES(quantity)
        """,
            (user_id, book_id, quantity),
        )

        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ خطا در افزودن به سبد: {e}")
        return False


def update_cart_quantity(user_id, book_id, change):
    """آپدیت تعداد کتاب در سبد """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if change == 0:  # حذف
            cursor.execute(
                "DELETE FROM cart_items WHERE user_id = %s AND book_id = %s",
                (user_id, book_id),
            )
        else:
            cursor.execute(
                """
                UPDATE cart_items 
                SET quantity = quantity + %s 
                WHERE user_id = %s AND book_id = %s
            """,
                (change, user_id, book_id),
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


#  ORDER OPERATIONS 
def create_order(user_id, total_price, receipt_photo, phone, address, postal_code):
    """ایجاد سفارش کامل"""
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


def add_order_item(order_id, book_id, title, author, price, count):
    """افزودن آیتم سفارش"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO order_items (order_id, book_id, title, author, price, count)
            VALUES (%s, %s, %s, %s, %s, %s)
        """,
            (order_id, book_id, title, author, price, count),
        )

        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ خطا در افزودن آیتم سفارش: {e}")
        return False


def update_order_status(order_id, status):
    """آپدیت وضعیت سفارش"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE orders SET status = %s WHERE order_id = %s",
            (status, order_id),
        )

        conn.commit()
        cursor.close()
        conn.close()
        return True

    except Exception as e:
        print(f"❌ خطا در آپدیت وضعیت سفارش: {e}")
        return False