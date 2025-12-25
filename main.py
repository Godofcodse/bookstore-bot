import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
import os
import sys
import logging
import time
from telebot import apihelper
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

#  CONFIGURATION 

# فعال کردن لاگینگ پیشرفته
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 🔴 **تنظیمات مهم برای جلوگیری از خطای 409**
apihelper.SESSION_TIME_TO_LIVE = 5 * 60
apihelper.RETRY_ON_ERROR = True
apihelper.READ_TIMEOUT = 30
apihelper.CONNECT_TIMEOUT = 30

# تاخیر قبل از شروع (مهم برای جلوگیری از خطای 409)
logger.info("=" * 60)
logger.info("🤖 راه‌اندازی ربات کتابفروشی")
logger.info("=" * 60)
time.sleep(3)

#  تنظیمات ضد خطای 409
bot = telebot.TeleBot(
    BOT_TOKEN,
    threaded=True,
    skip_pending=True,  
    parse_mode='Markdown',
    num_threads=2
)

# تأیید skip_pending
bot.skip_pending = True

# 🔴 **لیست ادمین‌های ثابت برای مواقعی که دیتابیس در دسترس نیست**
FALLBACK_ADMINS = [int(ADMIN_ID)] if ADMIN_ID else []

def check_admin_with_fallback(user_id):
    """بررسی ادمین با fallback به لیست ثابت"""
    logger.info(f"🔍 بررسی دسترسی ادمین برای کاربر {user_id}")
    
    # ابتدا از لیست ثابت بررسی کن
    if user_id in FALLBACK_ADMINS:
        logger.info(f"✅ کاربر {user_id} در لیست ادمین‌های ثابت است")
        return True
    
    # سپس از دیتابیس بررسی کن
    try:
        is_admin_result = is_admin(user_id)
        logger.info(f"📊 نتیجه بررسی دیتابیس برای کاربر {user_id}: {is_admin_result}")
        return is_admin_result
    except Exception as e:
        logger.warning(f"⚠️ خطا در بررسی ادمین از دیتابیس: {e}")
        return False

#  DATABASE INITIALIZATION 

logger.info("🔄 ایجاد/بررسی جداول دیتابیس...")
try:
    if create_tables():
        logger.info("✅ جداول دیتابیس با موفقیت بررسی شدند")
    else:
        logger.error("❌ خطا در ایجاد جداول دیتابیس")
except Exception as e:
    logger.error(f"❌ خطا در ایجاد جداول: {e}")

user_states = {}

#  HELPER FUNCTIONS 

def safe_edit_or_send(bot, call, text, reply_markup=None):
    """ویرایش امن پیام یا ارسال جدید"""
    try:
        if call.message.content_type == 'photo':
            bot.edit_message_caption(
                caption=text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            bot.edit_message_text(
                text,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.warning(f"Could not edit message, sending new: {e}")
        bot.send_message(
            call.message.chat.id,
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

def send_or_edit_message(bot, user_id, message_id, content_type, text, reply_markup=None):
    """ارسال یا ویرایش پیام بر اساس نوع"""
    try:
        if content_type == 'photo':
            bot.send_message(
                user_id,
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            bot.edit_message_text(
                text,
                chat_id=user_id,
                message_id=message_id,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.warning(f"خطا در ویرایش پیام: {e}")
        bot.send_message(
            user_id,
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

def save_edited_book(bot, user_id, state):
    """ذخیره کتاب ویرایش شده"""
    try:
        book_data = state["data"]
        book_id = book_data.get("book_id")
        
        if not book_id:
            bot.send_message(user_id, "❌ آیدی کتاب پیدا نشد!")
            return
        
       
        update_data = {}
        if "title" in book_data and book_data["title"]:
            update_data["title"] = book_data["title"]
        if "author" in book_data and book_data["author"]:
            update_data["author"] = book_data["author"]
        if "description" in book_data and book_data["description"]:
            update_data["description"] = book_data["description"]
        if "price" in book_data and book_data["price"]:
            update_data["price"] = book_data["price"]
        if "category_id" in book_data:
            update_data["category_id"] = book_data["category_id"]
        
        if update_book(book_id, **update_data):
            bot.send_message(
                user_id,
                f"✅ کتاب با موفقیت ویرایش شد!\n\n"
                f"📖 عنوان: {book_data.get('title', 'بدون تغییر')}\n"
                f"✍️ نویسنده: {book_data.get('author', 'بدون تغییر')}\n"
                f"💰 قیمت: {book_data.get('price', 'بدون تغییر'):,} تومان",
                reply_markup=admin_menu_markup()
            )
        else:
            bot.send_message(
                user_id,
                "❌ خطا در ویرایش کتاب!",
                reply_markup=admin_menu_markup()
            )
    except Exception as e:
        logger.error(f"خطا در ذخیره کتاب ویرایش شده: {e}")
        bot.send_message(
            user_id,
            f"❌ خطا در ویرایش کتاب: {e}",
            reply_markup=admin_menu_markup()
        )
    
    if user_id in user_states:
        del user_states[user_id]

#  KEYBOARD BUILDERS 

def main_menu_markup():
    """منوی اصلی کاربران"""
    mk = InlineKeyboardMarkup(row_width=2)
    mk.add(
        InlineKeyboardButton("📚 دسته‌بندی‌ها", callback_data="categories"),
        InlineKeyboardButton("📋 لیست کتاب‌ها", callback_data="list_books"),
        InlineKeyboardButton("🔍 جستجوی کتاب", callback_data="search"),
        InlineKeyboardButton("🛒 سبد خرید", callback_data="cart"),
        InlineKeyboardButton("📦 سفارشات من", callback_data="my_orders"),
        InlineKeyboardButton("🆘 پشتیبانی", callback_data="support"),
    )
    return mk

def support_markup():
    """کیبورد پشتیبانی"""
    mk = InlineKeyboardMarkup()
    mk.add(InlineKeyboardButton("🔙 بازگشت", callback_data="home"))
    return mk

def categories_markup():
    """کیبورد دسته‌بندی‌ها"""
    categories = get_all_categories()
    mk = InlineKeyboardMarkup(row_width=2)
    
    if not categories:
        mk.add(InlineKeyboardButton("🔙 بازگشت", callback_data="home"))
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
    
    mk.row(InlineKeyboardButton("🔙 بازگشت", callback_data="home"))
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
        mk.row(InlineKeyboardButton("🔙 بازگشت", callback_data="list_books"))
    
    mk.row(InlineKeyboardButton("🏠 منوی اصلی", callback_data="home"))
    return mk

def books_list_markup(books, page=1):
    """کیبورد لیست کتاب‌ها برای کاربران"""
    books_per_page = 5
    start_idx = (page - 1) * books_per_page
    end_idx = start_idx + books_per_page
    paginated_books = books[start_idx:end_idx]
    
    mk = InlineKeyboardMarkup(row_width=1)
    
    if not paginated_books:
        mk.add(InlineKeyboardButton("🔙 بازگشت", callback_data="home"))
        return mk
    
    for book in paginated_books:
        mk.add(InlineKeyboardButton(
            f"📖 {book['title']} - {book['price']:,} تومان",
            callback_data=f"book_{book['book_id']}"
        ))
    
   
    pagination_buttons = []
    if page > 1:
        pagination_buttons.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"books_page_{page-1}"))
    if end_idx < len(books):
        pagination_buttons.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"books_page_{page+1}"))
    
    if pagination_buttons:
        mk.row(*pagination_buttons)
    
    mk.row(
        InlineKeyboardButton("🏠 منوی اصلی", callback_data="home"),
        InlineKeyboardButton("📚 دسته‌بندی‌ها", callback_data="categories")
    )
    
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
        mk.row(InlineKeyboardButton("🔙 بازگشت", callback_data="list_books"))
    
    mk.row(InlineKeyboardButton("🏠 منوی اصلی", callback_data="home"))
    return mk

def cart_markup(cart_items):
    """کیبورد سبد خرید"""
    mk = InlineKeyboardMarkup(row_width=3)
    
    if not cart_items:
        mk.add(InlineKeyboardButton("🔙 بازگشت", callback_data="home"))
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
        InlineKeyboardButton("🔙 بازگشت", callback_data="home"),
    )
    return mk

def admin_menu_markup():
    """منوی ادمین"""
    mk = InlineKeyboardMarkup(row_width=2)
    mk.add(
        InlineKeyboardButton("➕ اضافه کردن کتاب", callback_data="admin_add_book"),
        InlineKeyboardButton("📝 ویرایش کتاب", callback_data="admin_edit_book"),
        InlineKeyboardButton("🗑️ حذف کتاب", callback_data="admin_delete_book"),
        InlineKeyboardButton("🗂️ اضافه کردن دسته‌بندی", callback_data="admin_add_category"),
        InlineKeyboardButton("📝 ویرایش دسته‌بندی‌ها", callback_data="admin_edit_category"),
        InlineKeyboardButton("📋 لیست کتاب‌ها", callback_data="admin_list_books"),
        InlineKeyboardButton("📦 سفارشات در انتظار", callback_data="admin_pending_orders"),
        InlineKeyboardButton("➕ اضافه کردن ادمین", callback_data="admin_add_admin"),
        InlineKeyboardButton("🆘 پشتیبانی", callback_data="support"),
        InlineKeyboardButton("🔙 بازگشت", callback_data="home"),
    )
    return mk

def admin_edit_books_markup(books, page=1):
    """کیبورد لیست کتاب‌ها برای ویرایش ادمین"""
    books_per_page = 5
    start_idx = (page - 1) * books_per_page
    end_idx = start_idx + books_per_page
    paginated_books = books[start_idx:end_idx]
    
    mk = InlineKeyboardMarkup(row_width=1)
    
    if not paginated_books:
        mk.add(InlineKeyboardButton("🔙 بازگشت", callback_data="home"))
        return mk
    
    for book in paginated_books:
        mk.add(InlineKeyboardButton(
            f"#️⃣ {book['book_id']}: {book['title']}",
            callback_data=f"admin_edit_select_{book['book_id']}"
        ))
    
   
    pagination_buttons = []
    if page > 1:
        pagination_buttons.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"admin_edit_page_{page-1}"))
    if end_idx < len(books):
        pagination_buttons.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"admin_edit_page_{page+1}"))
    
    if pagination_buttons:
        mk.row(*pagination_buttons)
    
    mk.row(InlineKeyboardButton("🔙 بازگشت", callback_data="home"))
    
    return mk

def admin_delete_books_markup(books, page=1):
    """کیبورد لیست کتاب‌ها برای حذف ادمین"""
    books_per_page = 4 
    start_idx = (page - 1) * books_per_page
    end_idx = start_idx + books_per_page
    paginated_books = books[start_idx:end_idx]
    
    mk = InlineKeyboardMarkup(row_width=2)
    
    if not paginated_books:
        mk.add(InlineKeyboardButton("🔙 بازگشت", callback_data="home"))
        return mk
    
    for book in paginated_books:
        mk.row(
            InlineKeyboardButton(f"👁️ {book['book_id']}: {book['title'][:15]}...", 
                               callback_data=f"admin_view_{book['book_id']}"),
            InlineKeyboardButton("❌ حذف", 
                               callback_data=f"admin_delete_confirm_{book['book_id']}")
        )
    
    # دکمه‌های صفحه‌بندی
    pagination_buttons = []
    if page > 1:
        pagination_buttons.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"admin_delete_page_{page-1}"))
    if end_idx < len(books):
        pagination_buttons.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"admin_delete_page_{page+1}"))
    
    if pagination_buttons:
        mk.row(*pagination_buttons)
    
    mk.row(InlineKeyboardButton("🔙 بازگشت", callback_data="home"))
    
    return mk

def admin_edit_categories_markup(categories, page=1):
    """کیبورد لیست دسته‌بندی‌ها برای ویرایش"""
    categories_per_page = 4  # کمتر برای جا دادن دکمه‌های بیشتر
    start_idx = (page - 1) * categories_per_page
    end_idx = start_idx + categories_per_page
    paginated_categories = categories[start_idx:end_idx]
    
    mk = InlineKeyboardMarkup(row_width=2)
    
    if not paginated_categories:
        mk.add(InlineKeyboardButton("🔙 بازگشت", callback_data="home"))
        return mk
    
    for cat in paginated_categories:
        # دکمه ویرایش و حذف در یک ردیف
        mk.row(
            InlineKeyboardButton(f"✏️ {cat['name']}", 
                               callback_data=f"admin_edit_cat_{cat['category_id']}"),
            InlineKeyboardButton("❌ حذف", 
                               callback_data=f"admin_delete_cat_confirm_{cat['category_id']}")
        )
    
    
    pagination_buttons = []
    if page > 1:
        pagination_buttons.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"admin_edit_cat_page_{page-1}"))
    if end_idx < len(categories):
        pagination_buttons.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"admin_edit_cat_page_{page+1}"))
    
    if pagination_buttons:
        mk.row(*pagination_buttons)
    
    mk.row(InlineKeyboardButton("🔙 بازگشت", callback_data="home"))
    
    return mk

def confirm_delete_markup(book_id):
    """کیبورد تأیید حذف کتاب"""
    mk = InlineKeyboardMarkup(row_width=2)
    mk.add(
        InlineKeyboardButton("✅ بله، حذف کن", callback_data=f"admin_delete_final_{book_id}"),
        InlineKeyboardButton("❌ خیر، لغو", callback_data="admin_delete_book")
    )
    return mk

def confirm_delete_category_markup(category_id):
    """کیبورد تأیید حذف دسته‌بندی"""
    mk = InlineKeyboardMarkup(row_width=2)
    mk.add(
        InlineKeyboardButton("✅ بله، حذف کن", callback_data=f"admin_delete_cat_final_{category_id}"),
        InlineKeyboardButton("❌ خیر، لغو", callback_data="admin_edit_category")
    )
    return mk

def update_photo_markup(book_id):
    """کیبورد به‌روزرسانی عکس"""
    mk = InlineKeyboardMarkup(row_width=2)
    mk.add(
        InlineKeyboardButton("📸 آپلود عکس جدید", callback_data=f"admin_update_photo_{book_id}"),
        InlineKeyboardButton("⏭️ رد کردن", callback_data=f"admin_skip_photo_{book_id}")
    )
    mk.row(InlineKeyboardButton("🔙 بازگشت", callback_data="home"))
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

def edit_categories_keyboard_markup():
    """کیبورد مخصوص انتخاب دسته‌بندی در حالت ویرایش"""
    categories = get_all_categories()
    mk = InlineKeyboardMarkup(row_width=2)
    
    if not categories:
        mk.add(InlineKeyboardButton("⚠️ هیچ دسته‌بندی", callback_data="admin_edit_no_category"))
        return mk
    
    for cat in categories:
        mk.add(InlineKeyboardButton(
            cat['name'],
            callback_data=f"admin_edit_select_category_{cat['category_id']}"
        ))
    
    mk.add(InlineKeyboardButton(
        "❌ بدون دسته‌بندی",
        callback_data="admin_edit_no_category"
    ))
    
    return mk

#  COMMAND HANDLERS 

@bot.message_handler(commands=['start', 'admin'])
def handle_start_admin(message):
    """مدیریت دستورات start و admin"""
    user_id = message.chat.id
    command = message.text.split()[0] if message.text else ''
    
    logger.info(f"📩 دستور دریافت شده: {command} از کاربر {user_id}")
    
    try:
        save_user(user_id)
    except Exception as e:
        logger.error(f"خطا در ذخیره کاربر: {e}")
    
    # بررسی وضعیت ادمین
    is_user_admin = check_admin_with_fallback(user_id)
    logger.info(f"کاربر {user_id} وضعیت ادمین: {is_user_admin}")
    
    if command == '/admin' or (command == '/start' and is_user_admin):
        if is_user_admin:
            bot.send_message(
                user_id,
                "👨‍💼 به پنل مدیریت خوش آمدید!\n\n"
                "از منوی زیر استفاده کنید:",
                reply_markup=admin_menu_markup()
            )
            logger.info(f"پنل ادمین برای کاربر {user_id} نمایش داده شد")
        else:
            bot.send_message(user_id, "⛔ شما دسترسی ادمین ندارید!")
            logger.warning(f"کاربر {user_id} تلاش برای دسترسی به پنل ادمین بدون دسترسی")
    else:
        bot.send_message(
            user_id,
            "📚 به کتابفروشی آنلاین خوش آمدید!\n\n"
            "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
            reply_markup=main_menu_markup()
        )

#  CALLBACK HANDLER 

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """مدیریت کلیک روی دکمه‌ها"""
    user_id = call.message.chat.id
    data = call.data
    
    logger.info(f"🖱️ Callback دریافت شده - کاربر: {user_id}, دیتا: {data}")
    
    try:
        # اگر کاربر ادمین نیست و دیتای ادمین دارد، دسترسی رد کن
        if data.startswith('admin_') and not check_admin_with_fallback(user_id):
            bot.answer_callback_query(call.id, "⛔ دسترسی رد شد!")
            return
        
        # بازگشت به خانه
        if data == "home":
            if check_admin_with_fallback(user_id):
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
        
        # پشتیبانی
        elif data == "support":
            support_text = (
                "📞 **پشتیبانی**\n\n"
                "برای ارتباط با پشتیبانی، لطفاً به آیدی زیر پیام دهید:\n"
                "@GISHNIZ2007\n\n"
                "🕐 ساعات پاسخگویی: ۹ صبح تا ۱۲ شب"
            )
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                support_text,
                support_markup()
            )
        
        # نمایش دسته‌بندی‌ها
        elif data == "categories":
            try:
                categories = get_all_categories()
            except Exception as e:
                logger.error(f"خطا در دریافت دسته‌بندی‌ها: {e}")
                categories = []
            
            if not categories:
                send_or_edit_message(
                    bot, user_id, call.message.message_id, call.message.content_type,
                    "📭 در حال حاضر هیچ دسته‌بندی موجود نیست.",
                    InlineKeyboardMarkup().add(
                        InlineKeyboardButton("🔙 بازگشت", callback_data="home")
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
        
        # لیست کتاب‌ها برای کاربران
        elif data == "list_books":
            try:
                books = get_all_books()
            except Exception as e:
                logger.error(f"خطا در دریافت لیست کتاب‌ها: {e}")
                books = []
            
            if not books:
                send_or_edit_message(
                    bot, user_id, call.message.message_id, call.message.content_type,
                    "📭 در حال حاضر هیچ کتابی موجود نیست.",
                    InlineKeyboardMarkup().add(
                        InlineKeyboardButton("🔙 بازگشت", callback_data="home")
                    )
                )
                return
            
            text = f"📚 لیست کتاب‌ها (صفحه 1 از {(len(books) // 5) + 1}):\n\n"
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                text,
                books_list_markup(books, 1)
            )
        
        # صفحه‌بندی لیست کتاب‌ها برای کاربران
        elif data.startswith("books_page_"):
            try:
                page = int(data.split("_")[2])
                books = get_all_books()
            except Exception as e:
                logger.error(f"خطا در دریافت لیست کتاب‌ها: {e}")
                books = []
            
            if not books:
                send_or_edit_message(
                    bot, user_id, call.message.message_id, call.message.content_type,
                    "📭 در حال حاضر هیچ کتابی موجود نیست.",
                    InlineKeyboardMarkup().add(
                        InlineKeyboardButton("🔙 بازگشت", callback_data="home")
                    )
                )
                return
            
            text = f"📚 لیست کتاب‌ها (صفحه {page} از {(len(books) // 5) + 1}):\n\n"
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                text,
                books_list_markup(books, page)
            )
        
        # انتخاب دسته‌بندی
        elif data.startswith("category_"):
            category_id = int(data.split("_")[1])
            try:
                books = get_books_by_category(category_id)
            except Exception as e:
                logger.error(f"خطا در دریافت کتاب‌های دسته‌بندی: {e}")
                books = []
            
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
            try:
                book = get_book(book_id)
            except Exception as e:
                logger.error(f"خطا در دریافت کتاب: {e}")
                book = None
            
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
            try:
                if add_to_cart(user_id, book_id):
                    bot.answer_callback_query(call.id, "✅ به سبد خرید اضافه شد")
                else:
                    bot.answer_callback_query(call.id, "❌ خطا در اضافه کردن به سبد")
            except Exception as e:
                logger.error(f"خطا در افزودن به سبد: {e}")
                bot.answer_callback_query(call.id, "❌ خطا در عملیات")
        
        # سبد خرید
        elif data == "cart":
            try:
                cart_items = get_user_cart(user_id)
            except Exception as e:
                logger.error(f"خطا در دریافت سبد خرید: {e}")
                cart_items = []
            
            if not cart_items:
                send_or_edit_message(
                    bot, user_id, call.message.message_id, call.message.content_type,
                    "🛒 سبد خرید شما خالی است.",
                    InlineKeyboardMarkup().add(
                        InlineKeyboardButton("🔙 بازگشت", callback_data="home"),
                        InlineKeyboardButton("🔍 جستجوی کتاب", callback_data="search")
                    )
                )
                return
            
            try:
                total = get_cart_total(user_id)
            except Exception as e:
                logger.error(f"خطا در محاسبه مجموع: {e}")
                total = 0
            
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
            try:
                update_cart_quantity(user_id, book_id, 1)
                bot.answer_callback_query(call.id, "✅ افزایش یافت")
            except Exception as e:
                logger.error(f"خطا در افزایش سبد: {e}")
                bot.answer_callback_query(call.id, "❌ خطا")
            # سبد خرید رو دوباره نمایش بده
            callback_handler(type('obj', (object,), {
                'message': call.message,
                'data': 'cart',
                'id': call.id
            }))
        
        elif data.startswith("dec_"):
            book_id = int(data.split("_")[1])
            try:
                update_cart_quantity(user_id, book_id, -1)
                bot.answer_callback_query(call.id, "✅ کاهش یافت")
            except Exception as e:
                logger.error(f"خطا در کاهش سبد: {e}")
                bot.answer_callback_query(call.id, "❌ خطا")
            # سبد خرید رو دوباره نمایش بده
            callback_handler(type('obj', (object,), {
                'message': call.message,
                'data': 'cart',
                'id': call.id
            }))
        
        elif data.startswith("remove_"):
            book_id = int(data.split("_")[1])
            try:
                update_cart_quantity(user_id, book_id, 0)
                bot.answer_callback_query(call.id, "✅ حذف شد")
            except Exception as e:
                logger.error(f"خطا در حذف از سبد: {e}")
                bot.answer_callback_query(call.id, "❌ خطا")
            # سبد خرید رو دوباره نمایش بده
            callback_handler(type('obj', (object,), {
                'message': call.message,
                'data': 'cart',
                'id': call.id
            }))
        
        elif data == "clear_cart":
            try:
                clear_user_cart(user_id)
                bot.answer_callback_query(call.id, "✅ سبد خرید خالی شد")
            except Exception as e:
                logger.error(f"خطا در پاک کردن سبد: {e}")
                bot.answer_callback_query(call.id, "❌ خطا")
            # سبد خرید رو دوباره نمایش بده
            callback_handler(type('obj', (object,), {
                'message': call.message,
                'data': 'cart',
                'id': call.id
            }))
        
        # ثبت سفارش
        elif data == "checkout":
            try:
                cart_items = get_user_cart(user_id)
            except Exception as e:
                logger.error(f"خطا در دریافت سبد برای checkout: {e}")
                cart_items = []
                
            if not cart_items:
                bot.answer_callback_query(call.id, "سبد خرید شما خالی است")
                return
            
            user_states[user_id] = {"step": "checkout_phone", "data": {}}
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
            try:
                orders = get_user_orders(user_id)
            except Exception as e:
                logger.error(f"خطا در دریافت سفارشات کاربر: {e}")
                orders = []
            
            if not orders:
                send_or_edit_message(
                    bot, user_id, call.message.message_id, call.message.content_type,
                    "📭 شما هنوز سفارشی ثبت نکرده‌اید.",
                    InlineKeyboardMarkup().add(
                        InlineKeyboardButton("🔙 بازگشت", callback_data="home")
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
                    InlineKeyboardButton("🔙 بازگشت", callback_data="home")
                )
            )
        
        #  ADMIN HANDLERS 
        
        # اضافه کردن کتاب
        elif data == "admin_add_book":
            user_states[user_id] = {"step": "admin_add_book_title", "data": {}}
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                "📝 اضافه کردن کتاب جدید\n\nلطفاً عنوان کتاب را وارد کنید:",
                None
            )
        
        # ویرایش کتاب - نمایش لیست کتاب‌ها
        elif data == "admin_edit_book":
            try:
                books = get_all_books()
            except Exception as e:
                logger.error(f"خطا در دریافت لیست کتاب‌ها: {e}")
                books = []
            
            if not books:
                send_or_edit_message(
                    bot, user_id, call.message.message_id, call.message.content_type,
                    "📭 هیچ کتابی برای ویرایش وجود ندارد.",
                    admin_menu_markup()
                )
                return
            
            text = f"📝 ویرایش کتاب\n\n📚 لیست کتاب‌ها (صفحه 1 از {(len(books) // 5) + 1}):\n\n"
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                text,
                admin_edit_books_markup(books, 1)
            )
        
        # صفحه‌بندی ویرایش کتاب برای ادمین
        elif data.startswith("admin_edit_page_"):
            try:
                page = int(data.split("_")[3])
                books = get_all_books()
            except Exception as e:
                logger.error(f"خطا در دریافت لیست کتاب‌ها: {e}")
                books = []
            
            if not books:
                send_or_edit_message(
                    bot, user_id, call.message.message_id, call.message.content_type,
                    "📭 هیچ کتابی برای ویرایش وجود ندارد.",
                    admin_menu_markup()
                )
                return
            
            text = f"📝 ویرایش کتاب\n\n📚 لیست کتاب‌ها (صفحه {page} از {(len(books) // 5) + 1}):\n\n"
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                text,
                admin_edit_books_markup(books, page)
            )
        
        # انتخاب کتاب برای ویرایش
        elif data.startswith("admin_edit_select_"):
            book_id = int(data.split("_")[3])
            try:
                book = get_book(book_id)
            except Exception as e:
                logger.error(f"خطا در دریافت کتاب برای ویرایش: {e}")
                book = None
            
            if not book:
                bot.answer_callback_query(call.id, "کتاب یافت نشد!")
                return
            
            # ذخیره اطلاعات فعلی در user_state
            user_states[user_id] = {
                "step": "admin_edit_book_title",
                "data": {
                    "book_id": book_id,
                    "current_title": book.get('title', ''),
                    "current_author": book.get('author', ''),
                    "current_description": book.get('description', ''),
                    "current_price": book.get('price', 0),
                    "current_category_id": book.get('category_id')
                }
            }
            
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                f"📖 ویرایش کتاب: {book['title']}\n\n"
                f"آیدی کتاب: #{book_id}\n"
                f"عنوان فعلی: {book['title']}\n"
                f"نویسنده فعلی: {book['author']}\n"
                f"قیمت فعلی: {book['price']:,} تومان\n\n"
                f"عنوان جدید را وارد کنید (یا برای عدم تغییر Enter بزنید):",
                None
            )
        
        # حذف کتاب - نمایش لیست کتاب‌ها
        elif data == "admin_delete_book":
            try:
                books = get_all_books()
            except Exception as e:
                logger.error(f"خطا در دریافت لیست کتاب‌ها: {e}")
                books = []
            
            if not books:
                send_or_edit_message(
                    bot, user_id, call.message.message_id, call.message.content_type,
                    "📭 هیچ کتابی برای حذف وجود ندارد.",
                    admin_menu_markup()
                )
                return
            
            text = f"🗑️ حذف کتاب\n\n📚 لیست کتاب‌ها (صفحه 1 از {(len(books) // 4) + 1}):\n\n"
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                text,
                admin_delete_books_markup(books, 1)
            )
        
        # صفحه‌بندی حذف کتاب برای ادمین
        elif data.startswith("admin_delete_page_"):
            try:
                page = int(data.split("_")[3])
                books = get_all_books()
            except Exception as e:
                logger.error(f"خطا در دریافت لیست کتاب‌ها: {e}")
                books = []
            
            if not books:
                send_or_edit_message(
                    bot, user_id, call.message.message_id, call.message.content_type,
                    "📭 هیچ کتابی برای حذف وجود ندارد.",
                    admin_menu_markup()
                )
                return
            
            text = f"🗑️ حذف کتاب\n\n📚 لیست کتاب‌ها (صفحه {page} از {(len(books) // 4) + 1}):\n\n"
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                text,
                admin_delete_books_markup(books, page)
            )
        
        # مشاهده جزئیات کتاب برای حذف
        elif data.startswith("admin_view_"):
            book_id = int(data.split("_")[2])
            try:
                book = get_book(book_id)
            except Exception as e:
                logger.error(f"خطا در دریافت کتاب برای نمایش: {e}")
                book = None
            
            if not book:
                bot.answer_callback_query(call.id, "کتاب یافت نشد!")
                return
            
            text = (
                f"👁️ نمایش کتاب برای حذف\n\n"
                f"📖 **{book['title']}**\n\n"
                f"✍️ نویسنده: {book['author']}\n"
                f"🏷️ دسته: {book.get('category_name', 'بدون دسته')}\n"
                f"💰 قیمت: {book['price']:,} تومان\n"
                f"📝 موجودی: {book.get('stock', 1)} عدد\n\n"
                f"📄 توضیحات:\n{book.get('description', 'بدون توضیحات')[:200]}..."
            )
            
            mk = InlineKeyboardMarkup(row_width=2)
            mk.add(
                InlineKeyboardButton("❌ حذف این کتاب", callback_data=f"admin_delete_confirm_{book_id}"),
                InlineKeyboardButton("🔙 بازگشت", callback_data="admin_delete_book")
            )
            
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                text,
                mk
            )
        
        # تأیید حذف کتاب
        elif data.startswith("admin_delete_confirm_"):
            book_id = int(data.split("_")[3])
            try:
                book = get_book(book_id)
            except Exception as e:
                logger.error(f"خطا در دریافت کتاب برای تأیید حذف: {e}")
                book = None
            
            if not book:
                bot.answer_callback_query(call.id, "کتاب یافت نشد!")
                return
            
            text = f"⚠️ **تأیید حذف کتاب**\n\n"
            text += f"📖 عنوان: {book['title']}\n"
            text += f"✍️ نویسنده: {book['author']}\n"
            text += f"💰 قیمت: {book['price']:,} تومان\n\n"
            text += "آیا مطمئن هستید که می‌خواهید این کتاب را حذف کنید؟\n"
            text += "این عمل غیرقابل بازگشت است!"
            
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                text,
                confirm_delete_markup(book_id)
            )
        
        # حذف نهایی کتاب
        elif data.startswith("admin_delete_final_"):
            book_id = int(data.split("_")[3])
            
            try:
                if delete_book(book_id):
                    bot.answer_callback_query(call.id, "✅ کتاب با موفقیت حذف شد")
                    send_or_edit_message(
                        bot, user_id, call.message.message_id, call.message.content_type,
                        "✅ کتاب با موفقیت حذف شد.",
                        admin_menu_markup()
                    )
                else:
                    bot.answer_callback_query(call.id, "❌ خطا در حذف کتاب")
                    send_or_edit_message(
                        bot, user_id, call.message.message_id, call.message.content_type,
                        "❌ خطا در حذف کتاب!",
                        admin_menu_markup()
                    )
            except Exception as e:
                logger.error(f"خطا در حذف کتاب: {e}")
                bot.answer_callback_query(call.id, "❌ خطا در عملیات")
                send_or_edit_message(
                    bot, user_id, call.message.message_id, call.message.content_type,
                    f"❌ خطا در حذف کتاب: {e}",
                    admin_menu_markup()
                )
        
        # ویرایش دسته‌بندی‌ها - نمایش لیست
        elif data == "admin_edit_category":
            try:
                categories = get_all_categories()
            except Exception as e:
                logger.error(f"خطا در دریافت دسته‌بندی‌ها: {e}")
                categories = []
            
            if not categories:
                send_or_edit_message(
                    bot, user_id, call.message.message_id, call.message.content_type,
                    "📭 هیچ دسته‌بندی برای ویرایش وجود ندارد.",
                    admin_menu_markup()
                )
                return
            
            text = f"📝 ویرایش دسته‌بندی‌ها\n\n📁 لیست دسته‌بندی‌ها (صفحه 1 از {(len(categories) // 4) + 1}):\n\n"
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                text,
                admin_edit_categories_markup(categories, 1)
            )
        
        # صفحه‌بندی ویرایش دسته‌بندی‌ها
        elif data.startswith("admin_edit_cat_page_"):
            try:
                page = int(data.split("_")[4])
                categories = get_all_categories()
            except Exception as e:
                logger.error(f"خطا در دریافت دسته‌بندی‌ها: {e}")
                categories = []
            
            if not categories:
                send_or_edit_message(
                    bot, user_id, call.message.message_id, call.message.content_type,
                    "📭 هیچ دسته‌بندی برای ویرایش وجود ندارد.",
                    admin_menu_markup()
                )
                return
            
            text = f"📝 ویرایش دسته‌بندی‌ها\n\n📁 لیست دسته‌بندی‌ها (صفحه {page} از {(len(categories) // 4) + 1}):\n\n"
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                text,
                admin_edit_categories_markup(categories, page)
            )
        
        # ویرایش نام دسته‌بندی
        elif data.startswith("admin_edit_cat_"):
            # این فقط برای ویرایش نام است، نه حذف
            if "confirm" in data or "final" in data:
                pass
            else:
                category_id = int(data.split("_")[3])
                user_states[user_id] = {
                    "step": "admin_edit_category_name",
                    "data": {"category_id": category_id}
                }
                
                try:
                    category = get_category_by_id(category_id)
                    if category:
                        send_or_edit_message(
                            bot, user_id, call.message.message_id, call.message.content_type,
                            f"✏️ ویرایش نام دسته‌بندی\n\n"
                            f"نام فعلی: {category['name']}\n\n"
                            f"لطفاً نام جدید را وارد کنید:",
                            None
                        )
                    else:
                        bot.answer_callback_query(call.id, "دسته‌بندی یافت نشد!")
                except Exception as e:
                    logger.error(f"خطا در دریافت دسته‌بندی: {e}")
                    bot.answer_callback_query(call.id, "❌ خطا در دریافت اطلاعات")
        
        # تأیید حذف دسته‌بندی
        elif data.startswith("admin_delete_cat_confirm_"):
            category_id = int(data.split("_")[4])
            try:
                category = get_category_by_id(category_id)
            except Exception as e:
                logger.error(f"خطا در دریافت دسته‌بندی برای تأیید حذف: {e}")
                category = None
            
            if not category:
                bot.answer_callback_query(call.id, "دسته‌بندی یافت نشد!")
                return
            
            # بررسی اینکه آیا کتابی در این دسته‌بندی وجود دارد
            try:
                books_in_category = get_books_by_category(category_id)
            except Exception as e:
                logger.error(f"خطا در بررسی کتاب‌های دسته‌بندی: {e}")
                books_in_category = []
            
            text = f"⚠️ **تأیید حذف دسته‌بندی**\n\n"
            text += f"📁 نام: {category['name']}\n"
            text += f"📚 تعداد کتاب در این دسته: {len(books_in_category)}\n\n"
            text += "با حذف این دسته‌بندی:\n"
            text += "• تمام کتاب‌های این دسته بدون دسته‌بندی خواهند شد\n"
            text += "• این عمل غیرقابل بازگشت است!\n\n"
            text += "آیا مطمئن هستید؟"
            
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                text,
                confirm_delete_category_markup(category_id)
            )
        
        # حذف نهایی دسته‌بندی
        elif data.startswith("admin_delete_cat_final_"):
            category_id = int(data.split("_")[4])
            
            try:
                # ابتدا کتاب‌های این دسته را بدون دسته‌بندی کنیم
                books_in_category = get_books_by_category(category_id)
                for book in books_in_category:
                    update_book(book['book_id'], category_id=None)
                
                # سپس دسته‌بندی را حذف کنیم
                if delete_category(category_id):
                    bot.answer_callback_query(call.id, "✅ دسته‌بندی با موفقیت حذف شد")
                    send_or_edit_message(
                        bot, user_id, call.message.message_id, call.message.content_type,
                        f"✅ دسته‌بندی با موفقیت حذف شد.\n"
                        f"📚 {len(books_in_category)} کتاب به حالت بدون دسته‌بندی تغییر کردند.",
                        admin_menu_markup()
                    )
                else:
                    bot.answer_callback_query(call.id, "❌ خطا در حذف دسته‌بندی")
                    send_or_edit_message(
                        bot, user_id, call.message.message_id, call.message.content_type,
                        "❌ خطا در حذف دسته‌بندی!",
                        admin_menu_markup()
                    )
            except Exception as e:
                logger.error(f"خطا در حذف دسته‌بندی: {e}")
                bot.answer_callback_query(call.id, "❌ خطا در عملیات")
                send_or_edit_message(
                    bot, user_id, call.message.message_id, call.message.content_type,
                    f"❌ خطا در حذف دسته‌بندی: {e}",
                    admin_menu_markup()
                )
        
        # اضافه کردن دسته‌بندی
        elif data == "admin_add_category":
            user_states[user_id] = {"step": "admin_add_category_name"}
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                "🗂️ اضافه کردن دسته‌بندی جدید\n\nلطفاً نام دسته‌بندی را وارد کنید:",
                None
            )
        
        # لیست کتاب‌ها برای ادمین
        elif data == "admin_list_books":
            try:
                books = get_all_books()
            except Exception as e:
                logger.error(f"خطا در دریافت لیست کتاب‌ها: {e}")
                books = []
            
            if not books:
                send_or_edit_message(
                    bot, user_id, call.message.message_id, call.message.content_type,
                    "📭 هیچ کتابی ثبت نشده است.",
                    admin_menu_markup()
                )
                return
            
            text = "📚 لیست کتاب‌ها:\n\n"
            for book in books[:10]:  # فقط 10 کتاب اول
                text += f"#️⃣ {book['book_id']}: {book['title']}\n"
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
            try:
                orders = get_pending_orders()
            except Exception as e:
                logger.error(f"خطا در دریافت سفارشات در انتظار: {e}")
                orders = []
            
            if not orders:
                send_or_edit_message(
                    bot, user_id, call.message.message_id, call.message.content_type,
                    "✅ هیچ سفارش در انتظاری وجود ندارد.",
                    admin_menu_markup()
                )
                return
            
            for order in orders:
                try:
                    items = get_order_items(order['order_id'])
                except Exception as e:
                    logger.error(f"خطا در دریافت آیتم‌های سفارش: {e}")
                    items = []
                
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
            
            try:
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
            except Exception as e:
                logger.error(f"خطا در آپدیت وضعیت سفارش: {e}")
                bot.answer_callback_query(call.id, "❌ خطا در عملیات")
        
        # اضافه کردن ادمین
        elif data == "admin_add_admin":
            user_states[user_id] = {"step": "admin_add_admin_id"}
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                "➕ اضافه کردن ادمین جدید\n\nلطفاً آیدی عددی کاربر را وارد کنید:",
                None
            )
        
        # آپلود عکس جدید برای کتاب (بعد از ویرایش)
        elif data.startswith("admin_update_photo_"):
            book_id = int(data.split("_")[3])
            user_states[user_id] = {
                "step": "admin_update_book_photo",
                "data": {"book_id": book_id}
            }
            
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                f"📸 آپلود عکس جدید برای کتاب #{book_id}\n\n"
                f"لطفاً عکس جدید جلد کتاب را ارسال کنید:",
                None
            )
        
        # رد کردن آپلود عکس جدید
        elif data.startswith("admin_skip_photo_"):
            book_id = int(data.split("_")[3])
            bot.answer_callback_query(call.id, "⏭️ آپلود عکس رد شد")
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                f"✅ ویرایش کتاب #{book_id} کامل شد (بدون تغییر عکس).",
                admin_menu_markup()
            )
        
        #  HANDLE CATEGORY SELECTION 
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
                try:
                    category = get_category_by_id(category_id)
                    category_name = category['name'] if category else "نامشخص"
                except Exception as e:
                    logger.error(f"خطا در دریافت دسته‌بندی: {e}")
                    category_name = "نامشخص"
                
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
            
            # رفتن به مرحله بعد 
            state["step"] = "admin_add_book_photo"
            bot.answer_callback_query(call.id, "✅ دسته‌بندی ثبت شد")
        
        # مدیریت انتخاب دسته‌بندی در ویرایش
        elif data.startswith('admin_edit_select_category_') or data == 'admin_edit_no_category':
            logger.info(f"Edit category selection callback - Data: {data}")
            bot.answer_callback_query(call.id, "در حال پردازش...")
            
            if user_id not in user_states:
                bot.answer_callback_query(call.id, "❌ session منقضی شده")
                return
            
            state = user_states[user_id]
            
            if state.get("step") != "admin_edit_book_category":
                logger.warning(f"Wrong step for edit category selection. Step: {state.get('step')}")
                bot.answer_callback_query(call.id, "❌ مرحله اشتباه")
                return
            
            if data.startswith('admin_edit_select_category_'):
                category_id = int(data.split('_')[-1])
                state["data"]["category_id"] = category_id
            elif data == "admin_edit_no_category":
                state["data"]["category_id"] = None
            
            # درخواست آپلود عکس جدید
            book_id = state["data"]["book_id"]
            send_or_edit_message(
                bot, user_id, call.message.message_id, call.message.content_type,
                f"✅ اطلاعات کتاب ویرایش شد!\n\n"
                f"آیا می‌خواهید عکس جلد کتاب را نیز تغییر دهید؟",
                update_photo_markup(book_id)
            )
    
    except Exception as e:
        logger.error(f"Error in callback handler: {e}", exc_info=True)
        try:
            bot.answer_callback_query(call.id, "❌ خطایی رخ داد")
        except:
            pass

#  MESSAGE HANDLER 

@bot.message_handler(func=lambda message: True, content_types=['text', 'photo'])
def handle_message(message):
    """مدیریت پیام‌های متنی و عکس"""
    user_id = message.chat.id
    text = message.text if message.text else ""
    
    logger.info(f"📨 پیام از {user_id}: {text[:50]}...")
    
    # اگر کاربر در حال ثبت سفارش است
    if user_id in user_states:
        state = user_states[user_id]
        logger.info(f"User state: {state}")
        
        # دریافت شماره تلفن
        if state["step"] == "checkout_phone":
            if not text:
                bot.send_message(user_id, "لطفاً شماره تلفن را به صورت متن ارسال کنید.")
                return
            
            if "data" not in state:
                state["data"] = {}
            state["data"]["phone"] = text
            state["step"] = "checkout_address"
            bot.send_message(user_id, "🏠 لطفاً آدرس کامل خود را وارد کنید:")
        
        # دریافت آدرس
        elif state["step"] == "checkout_address":
            if not text:
                bot.send_message(user_id, "لطفاً آدرس را به صورت متن ارسال کنید.")
                return
            
            state["data"]["address"] = text
            state["step"] = "checkout_postal"
            bot.send_message(user_id, "📮 لطفاً کد پستی را وارد کنید:")
        
        # دریافت کد پستی
        elif state["step"] == "checkout_postal":
            if not text:
                bot.send_message(user_id, "لطفاً کد پستی را به صورت متن ارسال کنید.")
                return
            
            state["data"]["postal"] = text
            state["step"] = "checkout_receipt"
            
            try:
                cart_items = get_user_cart(user_id)
                total = get_cart_total(user_id)
            except Exception as e:
                logger.error(f"خطا در دریافت سبد خرید: {e}")
                cart_items = []
                total = 0
            
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
            
            try:
                # ایجاد سفارش
                cart_items = get_user_cart(user_id)
                total = get_cart_total(user_id)
                
                order_id = create_order(
                    user_id,
                    total,
                    file_id,
                    state.get("data", {}).get("phone"),
                    state.get("data", {}).get("address"),
                    state.get("data", {}).get("postal")
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
                    
                    # ✅ ذخیره اطلاعات کاربر در دیتابیس
                    save_user(
                        user_id,
                        phone=state.get("data", {}).get("phone"),
                        address=state.get("data", {}).get("address"),
                        postal_code=state.get("data", {}).get("postal")
                    )
                    
                    # پاک کردن سبد خرید
                    clear_user_cart(user_id)
                    
                    # ارسال به ادمین
                    admin_text = (
                        f"📦 سفارش جدید\n\n"
                        f"🆔 کد سفارش: {order_id}\n"
                        f"👤 کاربر: {user_id}\n"
                        f"📞 تلفن: {state.get('data', {}).get('phone')}\n"
                        f"🏠 آدرس: {state.get('data', {}).get('address')}\n"
                        f"📮 کد پستی: {state.get('data', {}).get('postal')}\n"
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
                else:
                    bot.send_message(
                        user_id,
                        "❌ خطا در ثبت سفارش! لطفاً مجدداً تلاش کنید.",
                        reply_markup=main_menu_markup()
                    )
                
            except Exception as e:
                logger.error(f"خطا در ثبت سفارش: {e}")
                bot.send_message(
                    user_id,
                    "❌ خطا در پردازش سفارش! لطفاً بعداً تلاش کنید.",
                    reply_markup=main_menu_markup()
                )
            
            # پاک کردن حالت کاربر
            if user_id in user_states:
                del user_states[user_id]
        
        # جستجوی کتاب
        elif state["step"] == "search_query":
            try:
                books = search_books(text)
            except Exception as e:
                logger.error(f"خطا در جستجوی کتاب: {e}")
                books = []
            
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
            
            if user_id in user_states:
                del user_states[user_id]
        
        #  ADMIN 
        
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
                try:
                    categories = get_all_categories()
                except Exception as e:
                    logger.error(f"خطا در دریافت دسته‌بندی‌ها: {e}")
                    categories = []
                    
                logger.info(f"Categories found: {len(categories)}")
                
                if not categories:
                    bot.send_message(user_id, "⚠️ هیچ دسته‌بندی وجود ندارد. اول یک دسته‌بندی اضافه کنید.")
                    if user_id in user_states:
                        del user_states[user_id]
                    return
                
                #  کیبورد دسته‌بندی‌ها
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
            
            try:
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
                        try:
                            category = get_category_by_id(state["data"]["category_id"])
                            if category:
                                category_text = f"\n🏷️ دسته‌بندی: {category['name']}"
                        except Exception as e:
                            logger.error(f"خطا در دریافت اطلاعات دسته‌بندی: {e}")
                    
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
                
            except Exception as e:
                logger.error(f"خطا در اضافه کردن کتاب: {e}")
                bot.send_message(
                    user_id,
                    f"❌ خطا در اضافه کردن کتاب: {e}",
                    reply_markup=admin_menu_markup()
                )
            
            if user_id in user_states:
                del user_states[user_id]
        
        # ویرایش کتاب - مرحله عنوان
        elif state["step"] == "admin_edit_book_title":
            if text.strip():
                state["data"]["title"] = text.strip()
            state["step"] = "admin_edit_book_author"
            bot.send_message(user_id, "✍️ نویسنده جدید را وارد کنید (یا برای عدم تغییر Enter بزنید):")
        
        # ویرایش کتاب - مرحله نویسنده
        elif state["step"] == "admin_edit_book_author":
            if text.strip():
                state["data"]["author"] = text.strip()
            state["step"] = "admin_edit_book_price"
            bot.send_message(user_id, "💰 قیمت جدید را به تومان وارد کنید (یا برای عدم تغییر Enter بزنید):")
        
        # ویرایش کتاب - مرحله قیمت
        elif state["step"] == "admin_edit_book_price":
            if text.strip():
                try:
                    price = int(text.replace(",", ""))
                    state["data"]["price"] = price
                except ValueError:
                    bot.send_message(user_id, "❌ قیمت باید عددی باشد!")
                    return
            
            # درخواست دسته‌بندی
            try:
                categories = get_all_categories()
            except Exception as e:
                logger.error(f"خطا در دریافت دسته‌بندی‌ها: {e}")
                categories = []
            
            if categories:
                bot.send_message(
                    user_id,
                    "🏷️ دسته‌بندی جدید را انتخاب کنید (یا 'بدون دسته‌بندی' را بزنید):",
                    reply_markup=edit_categories_keyboard_markup()
                )
                state["step"] = "admin_edit_book_category"
            else:

                book_id = state["data"]["book_id"]
                bot.send_message(
                    user_id,
                    f"✅ اطلاعات کتاب ویرایش شد!\n\n"
                    f"آیا می‌خواهید عکس جلد کتاب را نیز تغییر دهید؟",
                    update_photo_markup(book_id)
                )
        
        # آپلود عکس جدید برای کتاب ویرایش شده
        elif state["step"] == "admin_update_book_photo" and message.content_type == 'photo':
            file_id = message.photo[-1].file_id
            book_id = state["data"]["book_id"]
            
            try:
                if update_book(book_id, file_id=file_id):
                    bot.send_message(
                        user_id,
                        f"✅ عکس جدید برای کتاب #{book_id} با موفقیت آپلود شد!",
                        reply_markup=admin_menu_markup()
                    )
                    logger.info(f"Book photo updated for book #{book_id}")
                else:
                    bot.send_message(
                        user_id,
                        "❌ خطا در آپلود عکس جدید!",
                        reply_markup=admin_menu_markup()
                    )
            except Exception as e:
                logger.error(f"خطا در آپلود عکس جدید: {e}")
                bot.send_message(
                    user_id,
                    f"❌ خطا در آپلود عکس: {e}",
                    reply_markup=admin_menu_markup()
                )
            
            if user_id in user_states:
                del user_states[user_id]
        
        # ویرایش نام دسته‌بندی
        elif state["step"] == "admin_edit_category_name":
            if not text.strip():
                bot.send_message(user_id, "❌ نام دسته‌بندی نمی‌تواند خالی باشد!")
                return
            
            category_id = state["data"]["category_id"]
            
            try:
                # به‌روزرسانی نام دسته‌بندی
                delete_category(category_id)
                
                
                new_category_id = add_category(text.strip())
                
                if new_category_id:
                    bot.send_message(
                        user_id,
                        f"✅ نام دسته‌بندی با موفقیت تغییر کرد!\n\n"
                        f"📁 نام جدید: {text.strip()}",
                        reply_markup=admin_menu_markup()
                    )
                else:
                    bot.send_message(
                        user_id,
                        "❌ خطا در تغییر نام دسته‌بندی!",
                        reply_markup=admin_menu_markup()
                    )
            except Exception as e:
                logger.error(f"خطا در ویرایش نام دسته‌بندی: {e}")
                bot.send_message(
                    user_id,
                    f"❌ خطا در ویرایش نام دسته‌بندی: {e}",
                    reply_markup=admin_menu_markup()
                )
            
            if user_id in user_states:
                del user_states[user_id]
        
        # اضافه کردن دسته‌بندی
        elif state["step"] == "admin_add_category_name":
            try:
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
            except Exception as e:
                logger.error(f"خطا در اضافه کردن دسته‌بندی: {e}")
                bot.send_message(
                    user_id,
                    f"❌ خطا در اضافه کردن دسته‌بندی: {e}",
                    reply_markup=admin_menu_markup()
                )
            
            if user_id in user_states:
                del user_states[user_id]
        
        # اضافه کردن ادمین
        elif state["step"] == "admin_add_admin_id":
            try:
                new_admin_id = int(text)
                if add_admin(new_admin_id, "مدیر جدید", False):
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
            except ValueError:
                bot.send_message(
                    user_id,
                    "❌ آیدی باید عددی باشد!",
                    reply_markup=admin_menu_markup()
                )
            except Exception as e:
                logger.error(f"خطا در اضافه کردن ادمین: {e}")
                bot.send_message(
                    user_id,
                    f"❌ خطا در عملیات: {e}",
                    reply_markup=admin_menu_markup()
                )
            
            if user_id in user_states:
                del user_states[user_id]
    
    else:
        # اگر کاربر سلام کرده
        if text.lower() in ['سلام', 'hi', 'hello']:
            if check_admin_with_fallback(user_id):
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
            bot.send_message(
                user_id,
                "برای شروع از منوی زیر استفاده کنید:",
                reply_markup=main_menu_markup()
            )



if __name__ == "__main__":
    print("=" * 60)
    print("🚀 راه‌اندازی ربات کتابفروشی")
    print("=" * 60)
    
    # چک توکن
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN پیدا نشد!")
        sys.exit(1)
    
    print(f"🤖 شناسه ربات: {BOT_TOKEN[:15]}...")
    print(f"👨‍💼 ادمین اصلی: {ADMIN_ID}")
    
    # چک اتصال دیتابیس
    print("🔄 تست اتصال دیتابیس...")
    try:
        from database import get_db_connection
        conn = get_db_connection()
        if conn:
            print("✅ اتصال دیتابیس موفق!")
            conn.close()
        else:
            print("⚠️ اتصال دیتابیس ناموفق - استفاده از حالت fallback")
    except Exception as e:
        print(f"⚠️ خطا در تست دیتابیس: {e}")
    
    
    print("🔍 بررسی/اضافه کردن ادمین اصلی...")
    try:
        if ADMIN_ID and not is_admin(ADMIN_ID):
            print(f"➕ اضافه کردن ادمین {ADMIN_ID}...")
            if add_admin(ADMIN_ID, "مدیر اصلی", True):
                print("✅ ادمین اضافه شد")
            else:
                print("⚠️ خطا در اضافه کردن ادمین")
        else:
            print("✅ ادمین از قبل وجود دارد")
    except Exception as e:
        print(f"⚠️ خطا در بررسی/اضافه کردن ادمین: {e}")
        print(f"✅ استفاده از fallback admin: {FALLBACK_ADMINS}")
    
    
    print("=" * 60)
    print("🚀 شروع ربات تلگرام...")
    print("=" * 60)
    
    max_retries = 5
    retry_delay = 10
    
    for attempt in range(max_retries):
        try:
            print(f"🔄 تلاش برای شروع polling (تلاش {attempt + 1}/{max_retries})...")
            
            
            time.sleep(3)
            
            # شروع polling
            bot.infinity_polling(
                timeout=60,
                long_polling_timeout=60,
                skip_pending=True,
                allowed_updates=["message", "callback_query"]
            )
            
        except telebot.apihelper.ApiTelegramException as e:
            if "409" in str(e):
                print(f"⚠️ خطای 409: {e}")
                print("⏳ انتظار برای رفع تداخل...")
                time.sleep(retry_delay)
                retry_delay *= 2  
                
                
                try:
                    bot.stop_polling()
                except:
                    pass
                    
                if attempt == max_retries - 1:
                    print("💥 تمام تلاش‌ها ناموفق بود - خطای 409 حل نشد")
                    print("📌 راه‌حل: مطمئن شوید فقط یک نمونه از ربات در حال اجراست")
                    break
            else:
                print(f"❌ خطای تلگرام: {e}")
                break
                
        except KeyboardInterrupt:
            print("\n🛑 ربات توسط کاربر متوقف شد")
            break
            
        except Exception as e:
            print(f"❌ خطای غیرمنتظره: {e}")
            time.sleep(5)
            
    print("👋 ربات خاموش شد")