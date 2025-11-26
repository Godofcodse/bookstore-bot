import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import random
from config import BOT_TOKEN, ADMIN_ID, PAYMENT_CARD

bot = telebot.TeleBot(API_TOKEN)


# user_data  stores: cart, order temp info, current state
user_data = {}

# book_cache  stores search results temporarily
book_cache = {}


#  Keyboard Builders
def main_menu_markup():
    """Main menu keyboard"""
    mk = InlineKeyboardMarkup(row_width=2)
    mk.add(
        InlineKeyboardButton("🔍 جستجوی کتاب", callback_data="search"),
        InlineKeyboardButton("🛒 سبد خرید", callback_data="cart"),
    )
    return mk


def make_book_markup(book_key):
    """Keyboard below each searched book"""
    mk = InlineKeyboardMarkup(row_width=2)
    mk.add(
        InlineKeyboardButton("➕ افزودن به سبد", callback_data=f"add|{book_key}"),
        InlineKeyboardButton("🛒 مشاهده سبد", callback_data="cart"),
    )
    mk.add(InlineKeyboardButton("🏠 بازگشت به خانه", callback_data="home"))
    return mk


def cart_menu_markup(include_checkout=True):
    """Keyboard inside cart"""
    mk = InlineKeyboardMarkup(row_width=2)
    if include_checkout:
        mk.add(InlineKeyboardButton("🧾 ثبت سفارش", callback_data="checkout"))
    mk.add(
        InlineKeyboardButton("🏠 بازگشت به خانه", callback_data="home"),
        InlineKeyboardButton("🔍 جستجوی کتاب", callback_data="search"),
    )
    return mk


#  Book Search Function
def search_books(query):
    """Searches books from OpenLibrary API"""
    url = f"https://openlibrary.org/search.json?q={query}"
    try:
        r = requests.get(url, timeout=5)
        data = r.json()
    except Exception:
        data = {}

    results = []
    docs = data.get("docs", [])[:5]
    for d in docs:
        title = d.get("title") or "نامشخص"
        author = (
            ", ".join(d.get("author_name", [])) if d.get("author_name") else "ناشناخته"
        )
        cover_id = d.get("cover_i")
        cover_url = (
            f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
            if cover_id
            else None
        )
        key = d.get("key") or f"/works/{random.randint(100000,999999)}"
        price = random.randint(80000, 200000)

        book_cache[key] = {
            "title": title,
            "author": author,
            "cover": cover_url,
            "price": price,
        }
        results.append(
            {
                "key": key,
                "title": title,
                "author": author,
                "cover": cover_url,
                "price": price,
            }
        )

    return results


#  start Command
@bot.message_handler(commands=["start"])
def start(message):
    """Initializes user data and shows main menu"""
    user_id = message.chat.id
    user_data[user_id] = {"cart": {}, "state": None}
    bot.send_message(
        user_id,
        "📚 به فروشگاه کتاب خوش آمدید!\n\nاز منو استفاده کنید 👇",
        reply_markup=main_menu_markup(),
    )


#  Callback Handler
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    cid = call.message.chat.id
    data = call.data

    # Ensure data exists
    user_data.setdefault(cid, {"cart": {}, "state": None})

    #  HOME
    if data == "home":
        msg = "🏠 منوی اصلی\n\nاز گزینه‌های زیر استفاده کنید:"
        try:
            if call.message.content_type == "photo":
                bot.edit_message_caption(
                    caption=msg,
                    chat_id=cid,
                    message_id=call.message.message_id,
                    reply_markup=main_menu_markup(),
                )
            else:
                bot.edit_message_text(
                    msg, cid, call.message.message_id, reply_markup=main_menu_markup()
                )
        except:
            bot.send_message(cid, msg, reply_markup=main_menu_markup())

    #  SEARCH
    elif data == "search":
        msg = "🔍 نام کتاب مورد نظر خود را وارد کنید:"
        try:
            if call.message.content_type == "photo":
                bot.edit_message_caption(
                    caption=msg, chat_id=cid, message_id=call.message.message_id
                )
            else:
                bot.edit_message_text(msg, cid, call.message.message_id)
        except:
            bot.send_message(cid, msg)

    #  CART
    elif data == "cart":
        cart = user_data[cid].get("cart", {})
        if not cart:
            text = "🛒 سبد خرید شما خالی است."
            markup = cart_menu_markup(False)
        else:
            text = "🛍️ سبد خرید شما:\n\n"
            markup = InlineKeyboardMarkup(row_width=2)
            total = 0

            for key, item in cart.items():
                total += item["price"] * item["count"]
                text += f"📘 {item['title']} — {item['author']}\n"
                text += f"💰 قیمت: {item['price']:,} | 📦 تعداد: {item['count']}\n\n"
                markup.add(
                    InlineKeyboardButton("➕", callback_data=f"inc|{key}"),
                    InlineKeyboardButton("➖", callback_data=f"dec|{key}"),
                    InlineKeyboardButton("❌ حذف", callback_data=f"del|{key}"),
                )

            text += f"\n💵 مجموع کل: {total:,} تومان"
            markup.add(
                InlineKeyboardButton("🧾 ثبت سفارش", callback_data="checkout"),
                InlineKeyboardButton("🏠 بازگشت به خانه", callback_data="home"),
            )

        try:
            if call.message.content_type == "photo":
                bot.edit_message_caption(
                    caption=text,
                    chat_id=cid,
                    message_id=call.message.message_id,
                    reply_markup=markup,
                )
            else:
                bot.edit_message_text(
                    text, cid, call.message.message_id, reply_markup=markup
                )
        except:
            bot.send_message(cid, text, reply_markup=markup)

    #  ADD TO CART
    elif data.startswith("add|"):
        _, key = data.split("|")
        book = book_cache.get(key)

        if book:
            cart = user_data[cid]["cart"]
            if key in cart:
                cart[key]["count"] += 1
            else:
                cart[key] = {**book, "count": 1}

            bot.answer_callback_query(call.id, "به سبد اضافه شد ✔️")

            text = f"📗 کتاب «{book['title']}» به سبد شما اضافه شد."
            try:
                if call.message.content_type == "photo":
                    bot.edit_message_caption(
                        caption=text,
                        chat_id=cid,
                        message_id=call.message.message_id,
                        reply_markup=make_book_markup(key),
                    )
                else:
                    bot.edit_message_text(
                        text,
                        cid,
                        call.message.message_id,
                        reply_markup=make_book_markup(key),
                    )
            except:
                bot.send_message(cid, text, reply_markup=make_book_markup(key))

    #  CART CONTROLS
    elif data.startswith("inc|"):
        _, key = data.split("|")
        if key in user_data[cid]["cart"]:
            user_data[cid]["cart"][key]["count"] += 1
        bot.answer_callback_query(call.id, "افزایش یافت ✔️")
        callback_query(type("tmp", (), {"data": "cart", "message": call.message}))

    elif data.startswith("del|"):
        _, key = data.split("|")
        user_data[cid]["cart"].pop(key, None)
        bot.answer_callback_query(call.id, "حذف شد")
        callback_query(type("tmp", (), {"data": "cart", "message": call.message}))

    elif data.startswith("dec|"):
        _, key = data.split("|")
        if key in user_data[cid]["cart"]:
            if user_data[cid]["cart"][key]["count"] > 1:
                user_data[cid]["cart"][key]["count"] -= 1
            else:
                del user_data[cid]["cart"][key]
        bot.answer_callback_query(call.id, "کاهش یافت")
        callback_query(type("tmp", (), {"data": "cart", "message": call.message}))

    #  CHECKOUT:
    elif data == "checkout":
        if not user_data[cid]["cart"]:
            bot.answer_callback_query(call.id, "سبد شما خالی است.")
            return

        user_data[cid]["state"] = "await_phone"
        user_data[cid]["order"] = {}

        bot.send_message(cid, "📞 لطفاً شماره تلفن خود را ارسال کنید:")

    #  ADMIN APPROVE / REJECT
    elif data.startswith("approve|") or data.startswith("reject|"):
        if cid != ADMIN_ID:
            bot.answer_callback_query(call.id, "شما ادمین نیستید.")
            return

        action, uid = data.split("|")
        uid = int(uid)

        if action == "approve":
            bot.send_message(
                uid,
                "✅ سفارش شما تایید شد!\n📦 کتاب شما طی 5 تا 10 روز کاری به دست‌تان خواهد رسید.",
            )
            bot.answer_callback_query(call.id, "تایید شد")
            bot.edit_message_caption(
                chat_id=cid,
                message_id=call.message.message_id,
                caption="✔️ سفارش تایید شد",
            )
            user_data[uid]["cart"].clear()

        else:
            bot.send_message(uid, "❌ سفارش شما رد شد.")
            bot.answer_callback_query(call.id, "رد شد")
            bot.edit_message_caption(
                chat_id=cid,
                message_id=call.message.message_id,
                caption="❌ سفارش رد شد",
            )


#  Message Handler (text/photo)
@bot.message_handler(func=lambda msg: True, content_types=["text", "photo"])
def message_handler(message):
    cid = message.chat.id
    text = message.text.strip() if message.content_type == "text" else None

    # Initialize user data if missing
    user_data.setdefault(cid, {"cart": {}, "state": None})

    #  GREETINGS
    if text and text.lower() in ["سلام", "hi", "hello"]:
        bot.send_message(
            cid,
            "سلام! لطفاً نام کتاب را وارد کنید یا از منو استفاده کنید.",
            reply_markup=main_menu_markup(),
        )
        return

    #  STEP 1: GET PHONE
    if user_data[cid]["state"] == "await_phone":
        if not text:
            bot.send_message(cid, "لطفاً شماره تلفن را به صورت متن ارسال کنید.")
            return

        user_data[cid]["order"]["phone"] = text
        user_data[cid]["state"] = "await_address"
        bot.send_message(cid, "🏠 لطفاً آدرس کامل خود را ارسال کنید:")
        return

    #  STEP 2: GET ADDRESS
    if user_data[cid]["state"] == "await_address":
        if not text:
            bot.send_message(cid, "لطفاً آدرس را به صورت متن ارسال کنید.")
            return

        user_data[cid]["order"]["address"] = text
        user_data[cid]["state"] = "await_postal"
        bot.send_message(cid, "📮 لطفاً کد پستی را ارسال کنید:")
        return

    #  STEP 3: GET POSTAL CODE
    if user_data[cid]["state"] == "await_postal":
        if not text:
            bot.send_message(cid, "لطفاً کد پستی را به صورت متن ارسال کنید.")
            return

        user_data[cid]["order"]["postal"] = text
        user_data[cid]["state"] = "await_receipt"

        bot.send_message(
            cid,
            f"💳 لطفاً مبلغ سفارش را به شماره کارت زیر واریز کنید و سپس عکس رسید را ارسال کنید:\n\n"
            f"💳 **{PAYMENT_CARD}**\n"
            "به نام: BookStore\n\n"
            "📸 عکس رسید را ارسال کنید.",
        )
    #  STEP 4: WAIT FOR RECEIPT IMAGE
    if user_data[cid]["state"] == "await_receipt":
        if message.content_type != "photo":
            bot.send_message(cid, "❗ لطفاً فقط عکس رسید را ارسال کنید.")
            return

        file_id = message.photo[-1].file_id
        user_data[cid]["order"]["receipt_photo"] = file_id
        user_data[cid]["state"] = None

        bot.send_message(cid, "📦 سفارش شما ثبت شد و در انتظار تایید ادمین است.")

        # Send to admin
        order = user_data[cid]["order"]
        cart = user_data[cid]["cart"]

        text_admin = (
            "📨 سفارش جدید:\n\n"
            f"👤 کاربر: {cid}\n"
            f"📞 شماره: {order['phone']}\n"
            f"🏠 آدرس: {order['address']}\n"
            f"📮 کد پستی: {order['postal']}\n\n"
            "📚 لیست کتاب‌ها:\n"
        )

        total = 0
        for b in cart.values():
            text_admin += f"• {b['title']} — {b['price']:,} × {b['count']}\n"
            total += b["price"] * b["count"]

        text_admin += f"\n💵 مجموع کل: {total:,} تومان"

        mk = InlineKeyboardMarkup(row_width=2)
        mk.add(
            InlineKeyboardButton("✔️ تایید سفارش", callback_data=f"approve|{cid}"),
            InlineKeyboardButton("❌ رد سفارش", callback_data=f"reject|{cid}"),
        )

        bot.send_photo(ADMIN_ID, file_id, caption=text_admin, reply_markup=mk)
        return

    #  DEFAULT: SEARCH BOOK
    if text:
        results = search_books(text)
        if not results:
            bot.send_message(
                cid, "هیچ کتابی یافت نشد.", reply_markup=main_menu_markup()
            )
            return

        for b in results:
            caption = f"{b['title']}\n✍️ {b['author']}\n💰 {b['price']:,} تومان"
            try:
                if b["cover"]:
                    bot.send_photo(
                        cid,
                        b["cover"],
                        caption=caption,
                        reply_markup=make_book_markup(b["key"]),
                    )
                else:
                    bot.send_message(
                        cid, caption, reply_markup=make_book_markup(b["key"])
                    )
            except:
                bot.send_message(cid, caption, reply_markup=make_book_markup(b["key"]))
        return


#  RUN BOT
print("Bookstore Bot is running...")
bot.infinity_polling(timeout=60, long_polling_timeout=60)
