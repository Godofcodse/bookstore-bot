import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
import os
import sys
import logging
from database import (
    create_tables, save_user, add_category, add_book_full,
    get_all_categories, get_books_by_category, get_book,
    add_to_cart, update_cart_quantity, clear_user_cart,
    create_order, add_order_item, update_order_status,
    is_admin, add_admin, get_all_books, search_books,
    get_user_cart, get_cart_total, get_pending_orders,
    get_order_items, get_user_orders, update_book, delete_book,
    delete_category, get_category_by_id
)
from config import BOT_TOKEN, ADMIN_ID, PAYMENT_CARD

# فعال کردن لاگینگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# ایجاد جداول در صورت عدم وجود
create_tables()

bot = telebot.TeleBot(BOT_TOKEN)

# دیکشنری برای ذخیره حالت کاربران
user_states = {}

# ========== HELPER FUNCTIONS ==========
def safe_edit_or_send(bot, call, text, reply_markup=None):
    """ویرایش امن پیام یا ارسال جدید"""
    try:
        if call.message.content_type == 'photo':
            bot.edit_message_caption(
                caption=text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=reply_markup
            )
        else:
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.warning(f"Could not edit message, sending new: {e}")
        bot.send_message(
            call.message.chat.id,
            text,
            reply_markup=reply_markup
        )

def send_or_edit_message(bot, user_id, message_id, content_type, text, reply_markup=None):
    """ارسال یا ویرایش پیام بر اساس نوع"""
    try:
        if content_type == 'photo':
            # اگر عکس هست، فقط پیام جدید بفرست
            bot.send_message(
                user_id,
                text,
                reply_markup=reply_markup
            )
        else:
            # اگر متن هست، ویرایش کن
            bot.edit_message_text(
                text,
                user_id,
                message_id,
                reply_markup=reply_markup
            )
    except:
        # اگر خطا داد، پیام جدید بفرست
        bot.send_message(
            user_id,
            text,
            reply_markup=reply_markup
        )

# ========== KEYBOARD BUILDERS ==========
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
        buttons.append(InlineKeyboardButton(
            f"📁 {cat['name']}",
            callback_data=f"category_{cat['category_id']}"
        ))
    
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
        mk.add(InlineKeyboardButton(
            f"📖 {book['title']} - {book['price']:,} تومان",
            callback_data=f"book_{book['book_id']}"
        ))
    
    if category_id:
        mk.row(InlineKeyboardButton("🔙 بازگشت به دسته‌بندی", callback_data=f"category_{category_id}"))
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
        mk.row(InlineKeyboardButton("🔙 بازگشت به لیست", callback_data=f"category_{category_id}"))
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
            InlineKeyboardButton(f"❌ {item['title'][:15]}", callback_data=f"remove_{item['book_id']}"),
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
        InlineKeyboardButton("🗂️ اضافه کردن دسته‌بندی", callback_data="admin_add_category"),
        InlineKeyboardButton("📋 لیست کتاب‌ها", callback_data="admin_list_books"),
        InlineKeyboardButton("📦 سفارشات در انتظار", callback_data="admin_pending_orders"),
        InlineKeyboardButton("📊 آمار", callback_data="admin_stats"),
        InlineKeyboardButton("➕➕ اضافه کردن ادمین", callback_data="admin_add_admin"),
        InlineKeyboardButton("🏠 بازگشت", callback_data="home"),
    )
    return mk

def categories_keyboard_markup():
    """کیبورد مخصوص انتخاب دسته‌بندی در حالت ادمین"""
    categories = get_all_categories()
    mk = InlineKeyboardMarkup(row_width=2)
    
    if not categories:
        mk.add(InlineKeyboardButton("⚠️ هیچ دسته‌بندی", callback_data="admin_no_category"))
        return mk
    
    for cat in categories:
        mk.add(InlineKeyboardButton(
            cat['name'],
            callback_data=f"admin_select_category_{cat['category_id']}"
        ))
    
    mk.add(InlineKeyboardButton(
        "❌ بدون دسته‌بندی",
        callback_data="admin_no_category"
    ))
    
    return mk

# ========== COMMAND HANDLERS ==========
@bot.message_handler(commands=['start'])
def start_command(message):
    """دستور شروع"""
    user_id = message.chat.id
    save_user(user_id)
    
    logger.info(f"User {user_id} started bot")
    
    # اگر ادمین است
    if is_admin(user_id):
        bot.send_message(
            user_id,
            "👨‍💼 به پنل مدیریت خوش آمدید!\n\n"
            "از منوی زیر استفاده کنید:",
            reply_markup=admin_menu_markup()
        )
    else:
        bot.send_message(
            user_id,
            "📚 به کتابفروشی آنلاین خوش آمدید!\n\n"
            "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
            reply_markup=main_menu_markup()
        )

@bot.message_handler(commands=['admin'])
def admin_command(message):
    """دستور ادمین"""
    user_id = message.chat.id
    
    if is_admin(user_id):
        bot.send_message(
            user_id,
            "🛠️ پنل مدیریت\n\n"
            "لطفاً عمل مورد نظر را انتخاب کنید:",
            reply_markup=admin_menu_markup()
        )
    else:
        bot.send_message(user_id, "⛔ شما دسترسی ادمین ندارید!")

# ========== CALLBACK HANDLERS ==========
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """مدیریت کلیک روی دکمه‌ها"""
    user_id = call.message.chat.id
    data = call.data
    
    logger.info(f"Callback received - User: {user_id}, Data: {data}")
    
    try:
        # بازگشت به خانه
        if data == "home":
            if is_admin(user_id):
                send_or_edit_message(
                    bot, user_id, call.message.message_id, call.message.content_type,
                    "🏠 منوی اصلی\n\nاز گزینه‌های زیر استفاده کنید:",
                    admin_menu_markup()
                )
            else:
                send_or_edit_message(
                    bot, user_id, call.message.message_id, call.message.content_type,
                    "🏠 منوی اصلی\n\nاز گزینه‌های زیر استفاده کنید:",
                    main_menu_markup()
                )
        
        # نمایش دسته‌بندی‌ها
        elif data == "categories":
            categories = get_all_categories()
            
            if not categories:
                send_or_edit_message(
                    bot, user_id, call.message.message_id, call.message.content_type,
                    "📭 در حال حاضر هیچ دسته‌بندی موجود نیست.",
                    InlineKeyboardMarkup().add(
                        InlineKeyboardButton("🏠 بازگشت", callback_data="home")
                    )
                )
                return
            
            text = "📚 دسته‌بندی‌های موجود:\n\n"
            for cat in categories:
                text += f"• {cat['name']}\n"
            
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                text,
                categories_markup()
            )
        
        # انتخاب دسته‌بندی
        elif data.startswith("category_"):
            category_id = int(data.split("_")[1])
            books = get_books_by_category(category_id)
            
            if not books:
                send_or_edit_message(
                    bot, user_id, call.message.message_id, call.message.content_type,
                    "📭 در این دسته‌بندی کتابی موجود نیست.",
                    InlineKeyboardMarkup().add(
                        InlineKeyboardButton("🔙 بازگشت", callback_data="categories"),
                        InlineKeyboardButton("🏠 خانه", callback_data="home")
                    )
                )
                return
            
            text = f"📚 کتاب‌های این دسته‌بندی:\n\n"
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                text,
                books_markup(books, category_id)
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
            if book.get('file_id'):
                try:
                    bot.delete_message(user_id, call.message.message_id)
                    bot.send_photo(
                        user_id,
                        book['file_id'],
                        caption=text,
                        reply_markup=book_detail_markup(book_id, book.get('category_id')),
                        parse_mode='Markdown'
                    )
                except:
                    send_or_edit_message(
                        bot, user_id, call.message.message_id, call.message.content_type,
                        text,
                        book_detail_markup(book_id, book.get('category_id'))
                    )
            else:
                send_or_edit_message(
                    bot, user_id, call.message.message_id, call.message.content_type,
                    text,
                    book_detail_markup(book_id, book.get('category_id'))
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
                send_or_edit_message(
                    bot, user_id, call.message.message_id, call.message.content_type,
                    "🛒 سبد خرید شما خالی است.",
                    InlineKeyboardMarkup().add(
                        InlineKeyboardButton("🏠 بازگشت", callback_data="home"),
                        InlineKeyboardButton("🔍 جستجوی کتاب", callback_data="search")
                    )
                )
                return
            
            total = get_cart_total(user_id)
            text = "🛒 سبد خرید شما:\n\n"
            
            for item in cart_items:
                text += f"📖 {item['title']}\n"
                text += f"   ✍️ {item['author']}\n"
                text += f"   💰 {item['price']:,} × {item['count']} = {item['price'] * item['count']:,} تومان\n\n"
            
            text += f"💵 مجموع کل: {total:,} تومان"
            
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                text,
                cart_markup(cart_items)
            )
        
        # کنترل‌های سبد خرید
        elif data.startswith("inc_"):
            book_id = int(data.split("_")[1])
            update_cart_quantity(user_id, book_id, 1)
            bot.answer_callback_query(call.id, "✅ افزایش یافت")
            # سبد خرید رو دوباره نمایش بده
            callback_handler(type('obj', (object,), {
                'message': call.message,
                'data': 'cart',
                'id': call.id
            }))
        
        elif data.startswith("dec_"):
            book_id = int(data.split("_")[1])
            update_cart_quantity(user_id, book_id, -1)
            bot.answer_callback_query(call.id, "✅ کاهش یافت")
            # سبد خرید رو دوباره نمایش بده
            callback_handler(type('obj', (object,), {
                'message': call.message,
                'data': 'cart',
                'id': call.id
            }))
        
        elif data.startswith("remove_"):
            book_id = int(data.split("_")[1])
            update_cart_quantity(user_id, book_id, 0)
            bot.answer_callback_query(call.id, "✅ حذف شد")
            # سبد خرید رو دوباره نمایش بده
            callback_handler(type('obj', (object,), {
                'message': call.message,
                'data': 'cart',
                'id': call.id
            }))
        
        elif data == "clear_cart":
            clear_user_cart(user_id)
            bot.answer_callback_query(call.id, "✅ سبد خرید خالی شد")
            # سبد خرید رو دوباره نمایش بده
            callback_handler(type('obj', (object,), {
                'message': call.message,
                'data': 'cart',
                'id': call.id
            }))
        
        # ثبت سفارش
        elif data == "checkout":
            cart_items = get_user_cart(user_id)
            if not cart_items:
                bot.answer_callback_query(call.id, "سبد خرید شما خالی است")
                return
            
            user_states[user_id] = {"step": "checkout_phone"}
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                "🧾 ثبت سفارش\n\n📞 لطفاً شماره تلفن خود را ارسال کنید:",
                None
            )
        
        # جستجو
        elif data == "search":
            user_states[user_id] = {"step": "search_query"}
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                "🔍 لطفاً عنوان کتاب یا نام نویسنده را وارد کنید:",
                None
            )
        
        # سفارشات من
        elif data == "my_orders":
            orders = get_user_orders(user_id)
            
            if not orders:
                send_or_edit_message(
                    bot, user_id, call.message.message_id, call.message.content_type,
                    "📭 شما هنوز سفارشی ثبت نکرده‌اید.",
                    InlineKeyboardMarkup().add(
                        InlineKeyboardButton("🏠 بازگشت", callback_data="home")
                    )
                )
                return
            
            text = "📦 سفارشات شما:\n\n"
            for order in orders:
                status_text = {
                    'pending': '⏳ در انتظار',
                    'approved': '✅ تایید شده',
                    'rejected': '❌ رد شده'
                }.get(order['status'], order['status'])
                
                text += f"🆔 کد سفارش: {order['order_id']}\n"
                text += f"💰 مبلغ: {order['total_price']:,} تومان\n"
                text += f"📊 وضعیت: {status_text}\n"
                text += f"📅 تاریخ: {order['created_at'].strftime('%Y/%m/%d')}\n"
                text += "─" * 20 + "\n"
            
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                text,
                InlineKeyboardMarkup().add(
                    InlineKeyboardButton("🏠 بازگشت", callback_data="home")
                )
            )
        
        # ========== ADMIN HANDLERS ==========
        
        # اضافه کردن کتاب
        elif data == "admin_add_book":
            user_states[user_id] = {"step": "admin_add_book_title", "data": {}}
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                "📝 اضافه کردن کتاب جدید\n\nلطفاً عنوان کتاب را وارد کنید:",
                None
            )
        
        # اضافه کردن دسته‌بندی
        elif data == "admin_add_category":
            user_states[user_id] = {"step": "admin_add_category_name"}
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                "🗂️ اضافه کردن دسته‌بندی جدید\n\nلطفاً نام دسته‌بندی را وارد کنید:",
                None
            )
        
        # لیست کتاب‌ها
        elif data == "admin_list_books":
            books = get_all_books()
            
            if not books:
                send_or_edit_message(
                    bot, user_id, call.message.message_id, call.message.content_type,
                    "📭 هیچ کتابی ثبت نشده است.",
                    admin_menu_markup()
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
            
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                text,
                admin_menu_markup()
            )
        
        # سفارشات در انتظار
        elif data == "admin_pending_orders":
            orders = get_pending_orders()
            
            if not orders:
                send_or_edit_message(
                    bot, user_id, call.message.message_id, call.message.content_type,
                    "✅ هیچ سفارش در انتظاری وجود ندارد.",
                    admin_menu_markup()
                )
                return
            
            for order in orders:
                items = get_order_items(order['order_id'])
                
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
                    InlineKeyboardButton("✅ تایید", callback_data=f"approve_{order['order_id']}"),
                    InlineKeyboardButton("❌ رد", callback_data=f"reject_{order['order_id']}")
                )
                
                bot.send_message(user_id, text, reply_markup=mk)
            
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                f"📊 {len(orders)} سفارش در انتظار تایید ارسال شد.",
                admin_menu_markup()
            )
        
        # تایید/رد سفارش
        elif data.startswith("approve_") or data.startswith("reject_"):
            action, order_id = data.split("_")
            order_id = int(order_id)
            
            if action == "approve":
                update_order_status(order_id, "approved")
                bot.answer_callback_query(call.id, "✅ سفارش تایید شد")
                send_or_edit_message(
                    bot, user_id, call.message.message_id, call.message.content_type,
                    "✅ سفارش تایید شد.",
                    None
                )
            else:
                update_order_status(order_id, "rejected")
                bot.answer_callback_query(call.id, "❌ سفارش رد شد")
                send_or_edit_message(
                    bot, user_id, call.message.message_id, call.message.content_type,
                    "❌ سفارش رد شد.",
                    None
                )
        
        # اضافه کردن ادمین
        elif data == "admin_add_admin":
            user_states[user_id] = {"step": "admin_add_admin_id"}
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                "➕ اضافه کردن ادمین جدید\n\nلطفاً آیدی عددی کاربر را وارد کنید:",
                None
            )
        
        # آمار
        elif data == "admin_stats":
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                "📊 در حال توسعه...",
                admin_menu_markup()
            )
        
        # ========== HANDLE CATEGORY SELECTION ==========
        elif data.startswith('admin_select_category_') or data == 'admin_no_category':
            logger.info(f"Category selection callback - Data: {data}")
            bot.answer_callback_query(call.id, "در حال پردازش...")
            
            if user_id not in user_states:
                bot.answer_callback_query(call.id, "❌ session منقضی شده")
                return
            
            state = user_states[user_id]
            
            if state.get("step") != "admin_add_book_category":
                logger.warning(f"Wrong step for category selection. Step: {state.get('step')}")
                bot.answer_callback_query(call.id, "❌ مرحله اشتباه")
                return
            
            if data.startswith('admin_select_category_'):
                category_id = int(data.split('_')[-1])
                state["data"]["category_id"] = category_id
                
                # دریافت نام دسته‌بندی
                category = get_category_by_id(category_id)
                category_name = category['name'] if category else "نامشخص"
                
                logger.info(f"Category selected: {category_name} (ID: {category_id})")
                
                send_or_edit_message(
                    bot, user_id, call.message.message_id, call.message.content_type,
                    f"✅ دسته‌بندی انتخاب شد: {category_name}\n\n📸 لطفاً عکس جلد کتاب را ارسال کنید:",
                    None
                )
                
            elif data == "admin_no_category":
                logger.info("No category selected")
                send_or_edit_message(
                    bot, user_id, call.message.message_id, call.message.content_type,
                    "📸 لطفاً عکس جلد کتاب را ارسال کنید:\n\n⚠️ توجه: کتاب بدون دسته‌بندی ذخیره می‌شود",
                    None
                )
            
            # به مرحله بعد برو
            state["step"] = "admin_add_book_photo"
            bot.answer_callback_query(call.id, "✅ دسته‌بندی ثبت شد")
    
    except Exception as e:
        logger.error(f"Error in callback handler: {e}", exc_info=True)
        try:
            bot.answer_callback_query(call.id, "❌ خطایی رخ داد")
        except:
            pass

# ========== MESSAGE HANDLER ==========
@bot.message_handler(func=lambda message: True, content_types=['text', 'photo'])
def handle_message(message):
    """مدیریت پیام‌های متنی و عکس"""
    user_id = message.chat.id
    text = message.text if message.text else ""
    
    logger.info(f"Message from {user_id}: {text[:50]}...")
    
    # اگر کاربر در حال ثبت سفارش است
    if user_id in user_states:
        state = user_states[user_id]
        logger.info(f"User state: {state}")
        
        # دریافت شماره تلفن
        if state["step"] == "checkout_phone":
            if not text:
                bot.send_message(user_id, "لطفاً شماره تلفن را به صورت متن ارسال کنید.")
                return
            
            state["phone"] = text
            state["step"] = "checkout_address"
            bot.send_message(user_id, "🏠 لطفاً آدرس کامل خود را وارد کنید:")
        
        # دریافت آدرس
        elif state["step"] == "checkout_address":
            if not text:
                bot.send_message(user_id, "لطفاً آدرس را به صورت متن ارسال کنید.")
                return
            
            state["address"] = text
            state["step"] = "checkout_postal"
            bot.send_message(user_id, "📮 لطفاً کد پستی را وارد کنید:")
        
        # دریافت کد پستی
        elif state["step"] == "checkout_postal":
            if not text:
                bot.send_message(user_id, "لطفاً کد پستی را به صورت متن ارسال کنید.")
                return
            
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
                parse_mode='Markdown'
            )
        
        # دریافت عکس رسید
        elif state["step"] == "checkout_receipt" and message.content_type == 'photo':
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
                state.get("postal")
            )
            
            if order_id:
                # اضافه کردن آیتم‌های سفارش
                for item in cart_items:
                    add_order_item(
                        order_id,
                        item['book_id'],
                        item['title'],
                        item['author'],
                        item['price'],
                        item['count']
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
                    InlineKeyboardButton("✅ تایید", callback_data=f"approve_{order_id}"),
                    InlineKeyboardButton("❌ رد", callback_data=f"reject_{order_id}")
                )
                
                bot.send_photo(ADMIN_ID, file_id, caption=admin_text, reply_markup=mk)
                
                bot.send_message(
                    user_id,
                    "✅ سفارش شما با موفقیت ثبت شد و در انتظار تایید ادمین است.\n\n"
                    "از خرید شما متشکریم!",
                    reply_markup=main_menu_markup()
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
                    reply_markup=main_menu_markup()
                )
            else:
                text_response = f"🔍 نتایج جستجو برای '{text}':\n\n"
                for book in books[:5]:  # فقط 5 نتیجه اول
                    text_response += f"📖 {book['title']}\n"
                    text_response += f"✍️ {book['author']}\n"
                    text_response += f"💰 {book['price']:,} تومان\n"
                    text_response += "─" * 20 + "\n"
                
                bot.send_message(
                    user_id,
                    text_response,
                    reply_markup=books_markup(books[:5])
                )
            
            del user_states[user_id]
        
        # ========== ADMIN STATES ==========
        
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
                
                logger.info(f"Price received: {price}, moving to category selection")
                
                # نمایش دسته‌بندی‌ها برای انتخاب
                categories = get_all_categories()
                logger.info(f"Categories found: {len(categories)}")
                
                if not categories:
                    bot.send_message(user_id, "⚠️ هیچ دسته‌بندی وجود ندارد. اول یک دسته‌بندی اضافه کنید.")
                    del user_states[user_id]
                    return
                
                # ارسال کیبورد دسته‌بندی‌ها
                bot.send_message(
                    user_id,
                    "🏷️ لطفاً دسته‌بندی کتاب را انتخاب کنید:",
                    reply_markup=categories_keyboard_markup()
                )
                
                state["step"] = "admin_add_book_category"
                logger.info(f"State updated: {state}")
                
            except ValueError:
                bot.send_message(user_id, "❌ قیمت باید عددی باشد. لطفاً مجدداً وارد کنید:")
        
        # اضافه کردن کتاب - مرحله عکس
        elif state["step"] == "admin_add_book_photo" and message.content_type == 'photo':
            file_id = message.photo[-1].file_id
            state["data"]["file_id"] = file_id
            
            # ذخیره کتاب
            book_id = add_book_full(
                title=state["data"]["title"],
                author=state["data"]["author"],
                description=state["data"]["description"],
                price=state["data"]["price"],
                category_id=state["data"].get("category_id"),
                file_id=file_id
            )
            
            if book_id:
                # نمایش اطلاعات کتاب اضافه شده
                category_text = ""
                if state["data"].get("category_id"):
                    category = get_category_by_id(state["data"]["category_id"])
                    if category:
                        category_text = f"\n🏷️ دسته‌بندی: {category['name']}"
                
                bot.send_message(
                    user_id,
                    f"✅ کتاب با موفقیت اضافه شد!\n\n"
                    f"📖 عنوان: {state['data']['title']}\n"
                    f"✍️ نویسنده: {state['data']['author']}\n"
                    f"💰 قیمت: {state['data']['price']:,} تومان"
                    f"{category_text}",
                    reply_markup=admin_menu_markup()
                )
                logger.info(f"Book added successfully: {state['data']['title']}")
            else:
                bot.send_message(
                    user_id,
                    "❌ خطا در اضافه کردن کتاب!",
                    reply_markup=admin_menu_markup()
                )
                logger.error("Failed to add book")
            
            del user_states[user_id]
        
        # اضافه کردن دسته‌بندی
        elif state["step"] == "admin_add_category_name":
            category_id = add_category(text)
            
            if category_id:
                bot.send_message(
                    user_id,
                    f"✅ دسته‌بندی '{text}' با موفقیت اضافه شد.",
                    reply_markup=admin_menu_markup()
                )
            else:
                bot.send_message(
                    user_id,
                    "❌ خطا در اضافه کردن دسته‌بندی!",
                    reply_markup=admin_menu_markup()
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
                        reply_markup=admin_menu_markup()
                    )
                else:
                    bot.send_message(
                        user_id,
                        "❌ خطا در اضافه کردن ادمین!",
                        reply_markup=admin_menu_markup()
                    )
            except:
                bot.send_message(
                    user_id,
                    "❌ آیدی باید عددی باشد!",
                    reply_markup=admin_menu_markup()
                )
            
            del user_states[user_id]
    
    else:
        # اگر کاربر سلام کرده
        if text.lower() in ['سلام', 'hi', 'hello']:
            if is_admin(user_id):
                bot.send_message(
                    user_id,
                    f"سلام {message.from_user.first_name}!\n"
                    "👨‍💼 به پنل مدیریت خوش آمدید.",
                    reply_markup=admin_menu_markup()
                )
            else:
                bot.send_message(
                    user_id,
                    f"سلام {message.from_user.first_name}!\n"
                    "📚 به کتابفروشی آنلاین خوش آمدید.",
                    reply_markup=main_menu_markup()
                )
        elif text and not text.startswith('/'):
            # پیشنهاد منوی اصلی
            bot.send_message(
                user_id,
                "برای شروع از منوی زیر استفاده کنید:",
                reply_markup=main_menu_markup()
            )

# ========== RUN BOT ==========
if __name__ == "__main__":
    print("=" * 50)
    print("🤖 ربات کتابفروشی در حال اجرا است...")
    print(f"👨‍💼 ادمین اصلی: {ADMIN_ID}")
    print("=" * 50)
    
    # چک توکن
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN not found!")
        sys.exit(1)
    
    # چک ادمین
    if not is_admin(ADMIN_ID):
        print(f"⚠️ کاربر {ADMIN_ID} ادمین نیست. در حال اضافه کردن...")
        add_admin(ADMIN_ID, "مدیر اصلی", True)
        print("✅ ادمین اضافه شد")
    
    # چک دسته‌بندی‌ها
    categories = get_all_categories()
    print(f"📊 تعداد دسته‌بندی‌ها: {len(categories)}")
    
    # شروع ربات
    print("🚀 ربات شروع به کار کرد...")
    bot.infinity_polling()