import telebot
from telebot.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove,
)
import os
from database import (
    create_tables,
    save_user,
    add_category,
    add_book_full,
    get_all_categories,
    get_books_by_category,
    get_book,
    add_to_cart,
    update_cart_quantity,
    clear_user_cart,
    create_order,
    add_order_item,
    update_order_status,
    is_admin,
    add_admin,
    get_all_books,
    search_books,
    get_user_cart,
    get_cart_total,
    get_pending_orders,
    get_order_items,
    get_user_orders,
    update_book,
    delete_book,
    delete_category,
)
from config import BOT_TOKEN, ADMIN_ID, PAYMENT_CARD

# ایجاد جداول در صورت عدم وجود
create_tables()

bot = telebot.TeleBot(BOT_TOKEN)

# دیکشنری برای ذخیره حالت کاربران
user_states = {}


#  KEYBOARD BUILDERS
def main_menu_markup():
    """منوی اصلی"""
    mk = InlineKeyboardMarkup(row_width=2)
    mk.add(
        InlineKeyboardButton("📚 دسته‌بندی‌ها", callback_data="categories"),
        InlineKeyboardButton("🔍 جستجوی کتاب", callback_data="search"),
        InlineKeyboardButton("🛒 سبد خرید", callback_data="cart"),
        InlineKeyboardButton("📦 سفارشات من", callback_data="my_orders"),
    )
    return mk


def categories_markup():
    """کیبورد دسته‌بندی‌ها"""
    categories = get_all_categories()
    mk = InlineKeyboardMarkup(row_width=2)

    if not categories:
        mk.add(InlineKeyboardButton("🏠 بازگشت", callback_data="home"))
        return mk

    buttons = []
    for cat in categories:
        buttons.append(
            InlineKeyboardButton(
                f"📁 {cat['name']}", callback_data=f"category_{cat['category_id']}"
            )
        )

    # چیدمان دکمه‌ها در ردیف‌های دو تایی
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            mk.row(buttons[i], buttons[i + 1])
        else:
            mk.row(buttons[i])

    mk.row(InlineKeyboardButton("🏠 بازگشت", callback_data="home"))
    return mk


def books_markup(books, category_id=None):
    """کیبورد لیست کتاب‌ها"""
    mk = InlineKeyboardMarkup(row_width=1)

    for book in books:
        mk.add(
            InlineKeyboardButton(
                f"📖 {book['title']} - {book['price']:,} تومان",
                callback_data=f"book_{book['book_id']}",
            )
        )

    if category_id:
        mk.row(
            InlineKeyboardButton(
                "🔙 بازگشت به دسته‌بندی", callback_data=f"category_{category_id}"
            )
        )
    else:
        mk.row(InlineKeyboardButton("🔙 بازگشت", callback_data="categories"))

    mk.row(InlineKeyboardButton("🏠 منوی اصلی", callback_data="home"))
    return mk


def book_detail_markup(book_id, category_id=None):
    """کیبورد جزئیات کتاب"""
    mk = InlineKeyboardMarkup(row_width=2)
    mk.add(
        InlineKeyboardButton("➕ افزودن به سبد", callback_data=f"add_{book_id}"),
        InlineKeyboardButton("🛒 سبد خرید", callback_data="cart"),
    )

    if category_id:
        mk.row(
            InlineKeyboardButton(
                "🔙 بازگشت به لیست", callback_data=f"category_{category_id}"
            )
        )
    else:
        mk.row(InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_books"))

    mk.row(InlineKeyboardButton("🏠 منوی اصلی", callback_data="home"))
    return mk


def cart_markup(cart_items):
    """کیبورد سبد خرید"""
    mk = InlineKeyboardMarkup(row_width=3)

    if not cart_items:
        mk.add(InlineKeyboardButton("🏠 بازگشت", callback_data="home"))
        return mk

    for item in cart_items:
        mk.row(
            InlineKeyboardButton(
                f"❌ {item['title'][:15]}", callback_data=f"remove_{item['book_id']}"
            ),
            InlineKeyboardButton("➖", callback_data=f"dec_{item['book_id']}"),
            InlineKeyboardButton("➕", callback_data=f"inc_{item['book_id']}"),
        )

    mk.row(InlineKeyboardButton("🧾 ثبت سفارش", callback_data="checkout"))
    mk.row(
        InlineKeyboardButton("🗑️ خالی کردن سبد", callback_data="clear_cart"),
        InlineKeyboardButton("🏠 منوی اصلی", callback_data="home"),
    )
    return mk


def admin_menu_markup():
    """منوی ادمین"""
    mk = InlineKeyboardMarkup(row_width=2)
    mk.add(
        InlineKeyboardButton("➕ اضافه کردن کتاب", callback_data="admin_add_book"),
        InlineKeyboardButton("📝 ویرایش کتاب", callback_data="admin_edit_book"),
        InlineKeyboardButton(
            "🗂️ اضافه کردن دسته‌بندی", callback_data="admin_add_category"
        ),
        InlineKeyboardButton("📋 لیست کتاب‌ها", callback_data="admin_list_books"),
        InlineKeyboardButton(
            "📦 سفارشات در انتظار", callback_data="admin_pending_orders"
        ),
        InlineKeyboardButton("📊 آمار", callback_data="admin_stats"),
        InlineKeyboardButton("➕ اضافه کردن ادمین", callback_data="admin_add_admin"),
        InlineKeyboardButton("🏠 بازگشت", callback_data="home"),
    )
    return mk


#  COMMAND HANDLERS
@bot.message_handler(commands=["start"])
def start_command(message):
    """دستور شروع"""
    user_id = message.chat.id
    save_user(user_id)

    # اگر ادمین است
    if is_admin(user_id):
        bot.send_message(
            user_id,
            "👨‍💼 به پنل مدیریت خوش آمدید!\n\n" "از منوی زیر استفاده کنید:",
            reply_markup=admin_menu_markup(),
        )
    else:
        bot.send_message(
            user_id,
            "📚 به کتابفروشی آنلاین خوش آمدید!\n\n"
            "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
            reply_markup=main_menu_markup(),
        )


@bot.message_handler(commands=["admin"])
def admin_command(message):
    """دستور ادمین"""
    user_id = message.chat.id

    if is_admin(user_id):
        bot.send_message(
            user_id,
            "🛠️ پنل مدیریت\n\n" "لطفاً عمل مورد نظر را انتخاب کنید:",
            reply_markup=admin_menu_markup(),
        )
    else:
        bot.send_message(user_id, "⛔ شما دسترسی ادمین ندارید!")


# = CALLBACK HANDLERS =
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """مدیریت کلیک روی دکمه‌ها"""
    user_id = call.message.chat.id
    data = call.data

    try:
        # بازگشت به خانه
        if data == "home":
            if is_admin(user_id):
                bot.edit_message_text(
                    "🏠 منوی اصلی\n\nاز گزینه‌های زیر استفاده کنید:",
                    user_id,
                    call.message.message_id,
                    reply_markup=admin_menu_markup(),
                )
            else:
                bot.edit_message_text(
                    "🏠 منوی اصلی\n\nاز گزینه‌های زیر استفاده کنید:",
                    user_id,
                    call.message.message_id,
                    reply_markup=main_menu_markup(),
                )

        # نمایش دسته‌بندی‌ها
        elif data == "categories":
            categories = get_all_categories()

            if not categories:
                bot.edit_message_text(
                    "📭 در حال حاضر هیچ دسته‌بندی موجود نیست.",
                    user_id,
                    call.message.message_id,
                    reply_markup=InlineKeyboardMarkup().add(
                        InlineKeyboardButton("🏠 بازگشت", callback_data="home")
                    ),
                )
                return

            text = "📚 دسته‌بندی‌های موجود:\n\n"
            for cat in categories:
                text += f"• {cat['name']}\n"

            bot.edit_message_text(
                text, user_id, call.message.message_id, reply_markup=categories_markup()
            )

        # انتخاب دسته‌بندی
        elif data.startswith("category_"):
            category_id = int(data.split("_")[1])
            books = get_books_by_category(category_id)

            if not books:
                bot.edit_message_text(
                    "📭 در این دسته‌بندی کتابی موجود نیست.",
                    user_id,
                    call.message.message_id,
                    reply_markup=InlineKeyboardMarkup().add(
                        InlineKeyboardButton("🔙 بازگشت", callback_data="categories"),
                        InlineKeyboardButton("🏠 خانه", callback_data="home"),
                    ),
                )
                return

            text = f"📚 کتاب‌های این دسته‌بندی:\n\n"
            bot.edit_message_text(
                text,
                user_id,
                call.message.message_id,
                reply_markup=books_markup(books, category_id),
            )

        # نمایش کتاب
        elif data.startswith("book_"):
            book_id = int(data.split("_")[1])
            book = get_book(book_id)

            if not book:
                bot.answer_callback_query(call.id, "کتاب یافت نشد!")
                return

            text = (
                f"📖 **{book['title']}**\n\n"
                f"✍️ نویسنده: {book['author']}\n"
                f"🏷️ دسته: {book.get('category_name', 'بدون دسته')}\n"
                f"💰 قیمت: {book['price']:,} تومان\n"
                f"📝 موجودی: {book.get('stock', 1)} عدد\n\n"
                f"📄 توضیحات:\n{book.get('description', 'بدون توضیحات')}"
            )

            # اگر عکس دارد
            if book.get("file_id"):
                try:
                    bot.delete_message(user_id, call.message.message_id)
                    bot.send_photo(
                        user_id,
                        book["file_id"],
                        caption=text,
                        reply_markup=book_detail_markup(
                            book_id, book.get("category_id")
                        ),
                        parse_mode="Markdown",
                    )
                except:
                    bot.edit_message_text(
                        text,
                        user_id,
                        call.message.message_id,
                        reply_markup=book_detail_markup(
                            book_id, book.get("category_id")
                        ),
                        parse_mode="Markdown",
                    )
            else:
                bot.edit_message_text(
                    text,
                    user_id,
                    call.message.message_id,
                    reply_markup=book_detail_markup(book_id, book.get("category_id")),
                    parse_mode="Markdown",
                )

        # اضافه به سبد خرید
        elif data.startswith("add_"):
            book_id = int(data.split("_")[1])
            if add_to_cart(user_id, book_id):
                bot.answer_callback_query(call.id, "✅ به سبد خرید اضافه شد")
            else:
                bot.answer_callback_query(call.id, "❌ خطا در اضافه کردن به سبد")

        # سبد خرید
        elif data == "cart":
            cart_items = get_user_cart(user_id)

            if not cart_items:
                bot.edit_message_text(
                    "🛒 سبد خرید شما خالی است.",
                    user_id,
                    call.message.message_id,
                    reply_markup=InlineKeyboardMarkup().add(
                        InlineKeyboardButton("🏠 بازگشت", callback_data="home"),
                        InlineKeyboardButton("🔍 جستجوی کتاب", callback_data="search"),
                    ),
                )
                return

            total = get_cart_total(user_id)
            text = "🛒 سبد خرید شما:\n\n"

            for item in cart_items:
                text += f"📖 {item['title']}\n"
                text += f"   ✍️ {item['author']}\n"
                text += f"   💰 {item['price']:,} × {item['count']} = {item['price'] * item['count']:,} تومان\n\n"

            text += f"💵 مجموع کل: {total:,} تومان"

            bot.edit_message_text(
                text,
                user_id,
                call.message.message_id,
                reply_markup=cart_markup(cart_items),
            )

        # کنترل‌های سبد خرید
        elif data.startswith("inc_"):
            book_id = int(data.split("_")[1])
            update_cart_quantity(user_id, book_id, 1)
            bot.answer_callback_query(call.id, "✅ افزایش یافت")
            callback_handler(
                type("obj", (object,), {"message": call.message, "data": "cart"})
            )

        elif data.startswith("dec_"):
            book_id = int(data.split("_")[1])
            update_cart_quantity(user_id, book_id, -1)
            bot.answer_callback_query(call.id, "✅ کاهش یافت")
            callback_handler(
                type("obj", (object,), {"message": call.message, "data": "cart"})
            )

        elif data.startswith("remove_"):
            book_id = int(data.split("_")[1])
            update_cart_quantity(user_id, book_id, 0)
            bot.answer_callback_query(call.id, "✅ حذف شد")
            callback_handler(
                type("obj", (object,), {"message": call.message, "data": "cart"})
            )

        elif data == "clear_cart":
            clear_user_cart(user_id)
            bot.answer_callback_query(call.id, "✅ سبد خرید خالی شد")
            callback_handler(
                type("obj", (object,), {"message": call.message, "data": "cart"})
            )

        # ثبت سفارش
        elif data == "checkout":
            cart_items = get_user_cart(user_id)
            if not cart_items:
                bot.answer_callback_query(call.id, "سبد خرید شما خالی است")
                return

            user_states[user_id] = {"step": "checkout_phone"}
            bot.edit_message_text(
                "🧾 ثبت سفارش\n\n" "📞 لطفاً شماره تلفن خود را ارسال کنید:",
                user_id,
                call.message.message_id,
            )

        # جستجو
        elif data == "search":
            user_states[user_id] = {"step": "search_query"}
            bot.edit_message_text(
                "🔍 لطفاً عنوان کتاب یا نام نویسنده را وارد کنید:",
                user_id,
                call.message.message_id,
            )

        # سفارشات من
        elif data == "my_orders":
            orders = get_user_orders(user_id)

            if not orders:
                bot.edit_message_text(
                    "📭 شما هنوز سفارشی ثبت نکرده‌اید.",
                    user_id,
                    call.message.message_id,
                    reply_markup=InlineKeyboardMarkup().add(
                        InlineKeyboardButton("🏠 بازگشت", callback_data="home")
                    ),
                )
                return

            text = "📦 سفارشات شما:\n\n"
            for order in orders:
                status_text = {
                    "pending": "⏳ در انتظار",
                    "approved": "✅ تایید شده",
                    "rejected": "❌ رد شده",
                }.get(order["status"], order["status"])

                text += f"🆔 کد سفارش: {order['order_id']}\n"
                text += f"💰 مبلغ: {order['total_price']:,} تومان\n"
                text += f"📊 وضعیت: {status_text}\n"
                text += f"📅 تاریخ: {order['created_at'].strftime('%Y/%m/%d')}\n"
                text += "─" * 20 + "\n"

            bot.edit_message_text(
                text,
                user_id,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("🏠 بازگشت", callback_data="home")
                ),
            )

        #  ADMIN HANDLERS

        # اضافه کردن کتاب
        elif data == "admin_add_book":
            user_states[user_id] = {"step": "admin_add_book_title", "data": {}}
            bot.edit_message_text(
                "📝 اضافه کردن کتاب جدید\n\n" "لطفاً عنوان کتاب را وارد کنید:",
                user_id,
                call.message.message_id,
            )

        # اضافه کردن دسته‌بندی
        elif data == "admin_add_category":
            user_states[user_id] = {"step": "admin_add_category_name"}
            bot.edit_message_text(
                "🗂️ اضافه کردن دسته‌بندی جدید\n\n" "لطفاً نام دسته‌بندی را وارد کنید:",
                user_id,
                call.message.message_id,
            )

        # لیست کتاب‌ها
        elif data == "admin_list_books":
            books = get_all_books()

            if not books:
                bot.edit_message_text(
                    "📭 هیچ کتابی ثبت نشده است.",
                    user_id,
                    call.message.message_id,
                    reply_markup=admin_menu_markup(),
                )
                return

            text = "📚 لیست کتاب‌ها:\n\n"
            for book in books[:10]:  # فقط 10 کتاب اول
                text += f"📖 {book['title']}\n"
                text += f"   ✍️ {book['author']}\n"
                text += f"   💰 {book['price']:,} تومان\n"
                text += f"   🏷️ {book.get('category_name', 'بدون دسته')}\n"
                text += "─" * 20 + "\n"

            if len(books) > 10:
                text += f"\n📊 و {len(books) - 10} کتاب دیگر..."

            bot.edit_message_text(
                text, user_id, call.message.message_id, reply_markup=admin_menu_markup()
            )

        # سفارشات در انتظار
        elif data == "admin_pending_orders":
            orders = get_pending_orders()

            if not orders:
                bot.edit_message_text(
                    "✅ هیچ سفارش در انتظاری وجود ندارد.",
                    user_id,
                    call.message.message_id,
                    reply_markup=admin_menu_markup(),
                )
                return

            for order in orders:
                items = get_order_items(order["order_id"])

                text = (
                    f"📦 سفارش جدید\n\n"
                    f"🆔 کد سفارش: {order['order_id']}\n"
                    f"👤 کاربر: {order['user_id']}\n"
                    f"📞 تلفن: {order['phone']}\n"
                    f"🏠 آدرس: {order['address']}\n"
                    f"📮 کد پستی: {order['postal_code']}\n"
                    f"💰 مبلغ کل: {order['total_price']:,} تومان\n\n"
                    f"📚 کتاب‌ها:\n"
                )

                for item in items:
                    text += f"• {item['title']} - {item['count']} عدد\n"

                mk = InlineKeyboardMarkup(row_width=2)
                mk.add(
                    InlineKeyboardButton(
                        "✅ تایید", callback_data=f"approve_{order['order_id']}"
                    ),
                    InlineKeyboardButton(
                        "❌ رد", callback_data=f"reject_{order['order_id']}"
                    ),
                )

                bot.send_message(user_id, text, reply_markup=mk)

            bot.edit_message_text(
                f"📊 {len(orders)} سفارش در انتظار تایید ارسال شد.",
                user_id,
                call.message.message_id,
                reply_markup=admin_menu_markup(),
            )

        # تایید/رد سفارش
        elif data.startswith("approve_") or data.startswith("reject_"):
            action, order_id = data.split("_")
            order_id = int(order_id)

            if action == "approve":
                update_order_status(order_id, "approved")
                bot.answer_callback_query(call.id, "✅ سفارش تایید شد")
                bot.edit_message_text(
                    "✅ سفارش تایید شد.", user_id, call.message.message_id
                )
            else:
                update_order_status(order_id, "rejected")
                bot.answer_callback_query(call.id, "❌ سفارش رد شد")
                bot.edit_message_text(
                    "❌ سفارش رد شد.", user_id, call.message.message_id
                )

        # اضافه کردن ادمین
        elif data == "admin_add_admin":
            user_states[user_id] = {"step": "admin_add_admin_id"}
            bot.edit_message_text(
                "➕ اضافه کردن ادمین جدید\n\n" "لطفاً آیدی عددی کاربر را وارد کنید:",
                user_id,
                call.message.message_id,
            )

        # آمار
        elif data == "admin_stats":
            # اینجا می‌توانید آمار را پیاده‌سازی کنید
            bot.edit_message_text(
                "📊 در حال توسعه...",
                user_id,
                call.message.message_id,
                reply_markup=admin_menu_markup(),
            )

    except Exception as e:
        print(f"Error in callback: {e}")
        bot.answer_callback_query(call.id, "❌ خطایی رخ داد")


# = MESSAGE HANDLER =
@bot.message_handler(func=lambda message: True, content_types=["text", "photo"])
def handle_message(message):
    """مدیریت پیام‌های متنی و عکس"""
    user_id = message.chat.id
    text = message.text if message.text else ""

    # اگر کاربر در حال ثبت سفارش است
    if user_id in user_states:
        state = user_states[user_id]

        # دریافت شماره تلفن
        if state["step"] == "checkout_phone":
            state["phone"] = text
            state["step"] = "checkout_address"
            bot.send_message(user_id, "🏠 لطفاً آدرس کامل خود را وارد کنید:")

        # دریافت آدرس
        elif state["step"] == "checkout_address":
            state["address"] = text
            state["step"] = "checkout_postal"
            bot.send_message(user_id, "📮 لطفاً کد پستی را وارد کنید:")

        # دریافت کد پستی
        elif state["step"] == "checkout_postal":
            state["postal"] = text
            state["step"] = "checkout_receipt"

            cart_items = get_user_cart(user_id)
            total = get_cart_total(user_id)

            bot.send_message(
                user_id,
                f"💳 پرداخت\n\n"
                f"💰 مبلغ قابل پرداخت: {total:,} تومان\n\n"
                f"لطفاً مبلغ فوق را به شماره کارت زیر واریز کنید:\n"
                f"`{PAYMENT_CARD}`\n\n"
                f"سپس عکس رسید بانکی را ارسال کنید.",
                parse_mode="Markdown",
            )

        # دریافت عکس رسید
        elif state["step"] == "checkout_receipt" and message.content_type == "photo":
            file_id = message.photo[-1].file_id

            # ایجاد سفارش
            cart_items = get_user_cart(user_id)
            total = get_cart_total(user_id)

            order_id = create_order(
                user_id,
                total,
                file_id,
                state.get("phone"),
                state.get("address"),
                state.get("postal"),
            )

            if order_id:
                # اضافه کردن آیتم‌های سفارش
                for item in cart_items:
                    add_order_item(
                        order_id,
                        item["book_id"],
                        item["title"],
                        item["author"],
                        item["price"],
                        item["count"],
                    )

                # پاک کردن سبد خرید
                clear_user_cart(user_id)

                # ارسال به ادمین
                admin_text = (
                    f"📦 سفارش جدید\n\n"
                    f"🆔 کد سفارش: {order_id}\n"
                    f"👤 کاربر: {user_id}\n"
                    f"📞 تلفن: {state.get('phone')}\n"
                    f"🏠 آدرس: {state.get('address')}\n"
                    f"📮 کد پستی: {state.get('postal')}\n"
                    f"💰 مبلغ کل: {total:,} تومان\n\n"
                )

                mk = InlineKeyboardMarkup(row_width=2)
                mk.add(
                    InlineKeyboardButton(
                        "✅ تایید", callback_data=f"approve_{order_id}"
                    ),
                    InlineKeyboardButton("❌ رد", callback_data=f"reject_{order_id}"),
                )

                bot.send_photo(ADMIN_ID, file_id, caption=admin_text, reply_markup=mk)

                bot.send_message(
                    user_id,
                    "✅ سفارش شما با موفقیت ثبت شد و در انتظار تایید ادمین است.\n\n"
                    "از خرید شما متشکریم!",
                    reply_markup=main_menu_markup(),
                )

            # پاک کردن حالت کاربر
            del user_states[user_id]

        # جستجوی کتاب
        elif state["step"] == "search_query":
            books = search_books(text)

            if not books:
                bot.send_message(
                    user_id,
                    "🔍 کتابی با این مشخصات یافت نشد.",
                    reply_markup=main_menu_markup(),
                )
            else:
                text_response = f"🔍 نتایج جستجو برای '{text}':\n\n"
                for book in books[:5]:  # فقط 5 نتیجه اول
                    text_response += f"📖 {book['title']}\n"
                    text_response += f"✍️ {book['author']}\n"
                    text_response += f"💰 {book['price']:,} تومان\n"
                    text_response += "─" * 20 + "\n"

                bot.send_message(
                    user_id, text_response, reply_markup=books_markup(books[:5])
                )

            del user_states[user_id]

        #  ADMIN STATES

        # اضافه کردن کتاب - مرحله عنوان
        elif state["step"] == "admin_add_book_title":
            state["data"]["title"] = text
            state["step"] = "admin_add_book_author"
            bot.send_message(user_id, "✍️ لطفاً نام نویسنده را وارد کنید:")

        # اضافه کردن کتاب - مرحله نویسنده
        elif state["step"] == "admin_add_book_author":
            state["data"]["author"] = text
            state["step"] = "admin_add_book_description"
            bot.send_message(user_id, "📄 لطفاً توضیحات کتاب را وارد کنید:")

        # اضافه کردن کتاب - مرحله توضیحات
        elif state["step"] == "admin_add_book_description":
            state["data"]["description"] = text
            state["step"] = "admin_add_book_price"
            bot.send_message(user_id, "💰 لطفاً قیمت کتاب را به تومان وارد کنید:")

        # اضافه کردن کتاب - مرحله قیمت
        elif state["step"] == "admin_add_book_price":
            try:
                price = int(text.replace(",", ""))
                state["data"]["price"] = price

                # نمایش دسته‌بندی‌ها برای انتخاب
                categories = get_all_categories()
                mk = InlineKeyboardMarkup(row_width=2)

                for cat in categories:
                    mk.add(
                        InlineKeyboardButton(
                            cat["name"],
                            callback_data=f"admin_select_category_{cat['category_id']}",
                        )
                    )

                mk.add(
                    InlineKeyboardButton(
                        "❌ بدون دسته", callback_data="admin_no_category"
                    )
                )

                bot.send_message(
                    user_id, "🏷️ لطفاً دسته‌بندی کتاب را انتخاب کنید:", reply_markup=mk
                )

                state["step"] = "admin_add_book_category"

            except:
                bot.send_message(
                    user_id, "❌ قیمت باید عددی باشد. لطفاً مجدداً وارد کنید:"
                )

        # اضافه کردن کتاب - مرحله عکس
        elif (
            state["step"] == "admin_add_book_photo" and message.content_type == "photo"
        ):
            file_id = message.photo[-1].file_id
            state["data"]["file_id"] = file_id

            # ذخیره کتاب
            book_id = add_book_full(
                title=state["data"]["title"],
                author=state["data"]["author"],
                description=state["data"]["description"],
                price=state["data"]["price"],
                category_id=state["data"].get("category_id"),
                file_id=file_id,
            )

            if book_id:
                bot.send_message(
                    user_id,
                    f"✅ کتاب با موفقیت اضافه شد!\n\n"
                    f"📖 عنوان: {state['data']['title']}\n"
                    f"✍️ نویسنده: {state['data']['author']}\n"
                    f"💰 قیمت: {state['data']['price']:,} تومان",
                    reply_markup=admin_menu_markup(),
                )
            else:
                bot.send_message(
                    user_id,
                    "❌ خطا در اضافه کردن کتاب!",
                    reply_markup=admin_menu_markup(),
                )

            del user_states[user_id]

        # اضافه کردن دسته‌بندی
        elif state["step"] == "admin_add_category_name":
            category_id = add_category(text)

            if category_id:
                bot.send_message(
                    user_id,
                    f"✅ دسته‌بندی '{text}' با موفقیت اضافه شد.",
                    reply_markup=admin_menu_markup(),
                )
            else:
                bot.send_message(
                    user_id,
                    "❌ خطا در اضافه کردن دسته‌بندی!",
                    reply_markup=admin_menu_markup(),
                )

            del user_states[user_id]

        # اضافه کردن ادمین
        elif state["step"] == "admin_add_admin_id":
            try:
                new_admin_id = int(text)
                if add_admin(new_admin_id):
                    bot.send_message(
                        user_id,
                        f"✅ کاربر {new_admin_id} به لیست ادمین‌ها اضافه شد.",
                        reply_markup=admin_menu_markup(),
                    )
                else:
                    bot.send_message(
                        user_id,
                        "❌ خطا در اضافه کردن ادمین!",
                        reply_markup=admin_menu_markup(),
                    )
            except:
                bot.send_message(
                    user_id, "❌ آیدی باید عددی باشد!", reply_markup=admin_menu_markup()
                )

            del user_states[user_id]

    else:
        # اگر کاربر سلام کرده
        if text.lower() in ["سلام", "hi", "hello"]:
            if is_admin(user_id):
                bot.send_message(
                    user_id,
                    f"سلام {message.from_user.first_name}!\n"
                    "👨‍💼 به پنل مدیریت خوش آمدید.",
                    reply_markup=admin_menu_markup(),
                )
            else:
                bot.send_message(
                    user_id,
                    f"سلام {message.from_user.first_name}!\n"
                    "📚 به کتابفروشی آنلاین خوش آمدید.",
                    reply_markup=main_menu_markup(),
                )
        else:
            # پیشنهاد جستجو
            bot.send_message(
                user_id,
                "برای شروع از منوی زیر استفاده کنید:",
                reply_markup=main_menu_markup(),
            )


# هندلر برای انتخاب دسته‌بندی در حالت ادمین
@bot.callback_query_handler(
    func=lambda call: call.data.startswith("admin_select_category_")
)
def handle_admin_select_category(call):
    user_id = call.message.chat.id

    if (
        user_id in user_states
        and user_states[user_id]["step"] == "admin_add_book_category"
    ):
        category_id = int(call.data.split("_")[-1])
        user_states[user_id]["data"]["category_id"] = category_id
        user_states[user_id]["step"] = "admin_add_book_photo"

        bot.edit_message_text(
            "📸 لطفاً عکس جلد کتاب را ارسال کنید:", user_id, call.message.message_id
        )

    elif call.data == "admin_no_category":
        user_states[user_id]["step"] = "admin_add_book_photo"

        bot.edit_message_text(
            "📸 لطفاً عکس جلد کتاب را ارسال کنید:", user_id, call.message.message_id
        )


# اجرای ربات
print("🤖 ربات کتابفروشی در حال اجرا است...")
bot.infinity_polling()
