📚 Bookstore Telegram Bot
<div align="center">
https://img.shields.io/badge/Python-3.8+-blue.svg
https://img.shields.io/badge/Telegram-Bot-blue.svg
https://img.shields.io/badge/MySQL-Database-orange.svg
https://img.shields.io/badge/Status-Active-brightgreen.svg

یک بات تلگرام هوشمند برای فروش کتاب با قابلیت جستجو، سبد خرید و سیستم پرداخت

ویژگی‌ها • نصب و راه‌اندازی • استفاده • ساختار پروژه

</div>
✨ ویژگی‌ها
ویژگی	توضیح
🔍 جستجوی هوشمند	جستجوی کتاب از OpenLibrary API
🛒 سبد خرید پیشرفته	مدیریت کامل سبد خرید با قابلیت افزایش/کاهش
💳 سیستم پرداخت	پرداخت با آپلود رسید بانکی
👨‍💼 پنل مدیریت	تایید یا رد سفارشات توسط ادمین
💾 پایگاه داده	ذخیره‌سازی داده‌ها در MySQL
🎨 رابط کاربری	کیبوردهای اینلاین زیبا
🔒 امنیت	مدیریت امن اطلاعات حساس
🚀 نصب و راه‌اندازی
پیش‌نیازها
Python 3.8 یا بالاتر

MySQL Server

اکانت Telegram

1. کلون کردن ریپوزیتوری
bash
git clone https://github.com/Godofcodse/bookstore-bot.git
cd bookstore-bot
2. نصب dependencies
bash
pip install -r requirements.txt
3. تنظیم دیتابیس
sql
CREATE DATABASE bookstore_bot;
4. پیکربندی
فایل .env را ایجاد و تنظیم کنید:

env
# Telegram Bot
BOT_TOKEN=your_bot_token_here
ADMIN_ID=your_admin_id_here

# Database
DB_HOST=localhost
DB_NAME=bookstore_bot
DB_USER=root
DB_PASSWORD=your_password
DB_PORT=3306

# Payment
PAYMENT_CARD=your_card_number_here
5. اجرای بات
bash
python bot.py
📖 استفاده
دستورات اصلی
/start - شروع بات و نمایش منوی اصلی

جستجوی کتاب - پیدا کردن کتاب‌های مورد نظر

سبد خرید - مدیریت کتاب‌های انتخاب شده

ثبت سفارش - تکمیل اطلاعات و پرداخت

فرآیند سفارش
جستجوی کتاب 📖

افزودن به سبد خرید 🛒

ثبت اطلاعات ارسال 📦

پرداخت و آپلود رسید 💳

تایید توسط ادمین ✅

🏗️ ساختار پروژه
text
bookstore-bot/
├── bot.py                 # فایل اصلی بات
├── config.py             # تنظیمات پروژه
├── requirements.txt      # کتابخانه‌های مورد نیاز
├── .env.example          # نمونه فایل محیط
├── .gitignore           # فایل‌های نادیده گرفته شده
└── database/            # ماژول دیتابیس
    ├── __init__.py
    ├── connection.py    # اتصال به دیتابیس
    ├── ddl.py          # تعریف جداول
    ├── dml.py          # عملیات insert/update/delete
    └── dql.py          # عملیات select و queries
🔧 API مورد استفاده
OpenLibrary API - برای جستجوی کتاب‌ها

Telegram Bot API - برای ارتباط با تلگرام

🤝 مشارکت
مشارکت‌ها همیشه welcome هستند!

Fork کنید

Branch ایجاد کنید (git checkout -b feature/AmazingFeature)

Commit کنید (git commit -m 'Add some AmazingFeature')

Push کنید (git push origin feature/AmazingFeature)

Pull Request باز کنید

📄 لایسنس
این پروژه تحت لایسنس MIT است - جزئیات در فایل LICENSE مشاهده کنید.

👤 توسعه‌دهنده
Godofcodse

GitHub: @Godofcodse

🙌 تشکر
python-telegram-bot

OpenLibrary

MySQL

<div align="center">
⭐ اگر این پروژه رو دوست داشتید، ستاره بدید!

</div>