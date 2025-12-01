from .connection import get_db_connection
from .DDL import create_tables
from .DML import (
    save_user,
    save_user_login,  # NEW: Added for login tracking
    save_book,
    create_order,
    add_order_item,
    update_order_status,
    add_to_cart,
    update_cart_quantity,
    clear_user_cart,
)
from .DQL import (
    get_user,
    get_book,
    get_pending_orders,
    get_order_items,
    get_user_orders,
    get_user_cart,
    get_cart_total,
    get_user_stats,  # NEW: Added for login tracking
    get_all_users_stats,  # NEW: Added for login tracking
    get_daily_starts,  # NEW: Added for login tracking
)

__all__ = [
    "get_db_connection",
    "create_tables",
    "save_user",
    "save_user_login",  # NEW: Added for login tracking
    "save_book",
    "create_order",
    "add_order_item",
    "update_order_status",
    "add_to_cart",
    "update_cart_quantity",
    "clear_user_cart",
    "get_user",
    "get_book",
    "get_pending_orders",
    "get_order_items",
    "get_user_orders",
    "get_user_cart",
    "get_cart_total",
    "get_user_stats",  # NEW: Added for login tracking
    "get_all_users_stats",  # NEW: Added for login tracking
    "get_daily_starts",  # NEW: Added for login tracking
]
