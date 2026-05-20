import asyncio
import json
import logging
import math
import os
import random
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from flask import Flask

import discord
from discord.ext import commands

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


def load_env_file() -> None:
    env_paths = [Path(".env"), Path(__file__).resolve().parent / ".env"]
    if load_dotenv is not None:
        for env_path in env_paths:
            load_dotenv(env_path)
        load_dotenv()
        return

    for env_path in env_paths:
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file()


DATA_FILE = Path("economy_data.json")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
PORT = int(os.getenv("PORT", "10000"))
TIMEZONE = ZoneInfo("Asia/Riyadh")

ADMIN_PANEL_CHANNEL_ID = 1498037576538259556
EVENT_PUBLIC_CHANNEL_ID = 1498037416672493829
EVENT_SCHEDULE_CHANNEL_ID = 1505299102236409886
AUCTION_CHANNEL_ID = 1505270221089538218
MARKET_CHANNEL_ID = 1505270148213243944
ADMIN_ROLE_ID = 1478970736717598840

START_MONEY = 3000
INVEST_COOLDOWN = 180
TRADE_COOLDOWN = 180
STEAL_COOLDOWN = 300
STEAL_PROTECTED_COST = 500
DAILY_COOLDOWN = 86400
ROULETTE_COOLDOWN = 600
EVENT_DURATION_SECONDS = 1800
PROTECTION_COST = 10000
PROTECTION_DURATION_SECONDS = 7200
PRICE_UPDATE_SECONDS = 600
AUTO_AUCTION_INTERVAL_SECONDS = 900
HIDDEN_AUCTION_INTERVAL_SECONDS = 900
RANDOM_EVENT_INTERVAL_SECONDS = 180
AUCTION_DURATION_SECONDS = 300
AUCTION_COUNTDOWN_SECONDS = 5
AUCTION_BID_CONFIRM_DELETE_AFTER = 60
COMPANY_PRICE = 250000
LOAN_MAX_AMOUNT = 20000
LOAN_MIN_PAYMENT = 1000
LOAN_DURATION_SECONDS = 3600
LOAN_LATE_FEE = 5000
BOT_REPLY_DELAY_SECONDS = 0.5

COLOR_PRIMARY = 0x1E2124
COLOR_SUCCESS = 0x57F287
COLOR_DANGER = 0xED4245
COLOR_WARNING = 0xFEE75C
COLOR_INFO = 0x5865F2
COLOR_GOLD = 0xF1C40F
COLOR_LAND = 0x3BA55D
COLOR_STOCK = 0x11806A
COLOR_SECRET = 0x2F3136

app = Flask(__name__)


@app.route("/", methods=["GET", "HEAD"])
def home() -> str:
    return "Bot is alive"


def run_web() -> None:
    app.run(host="0.0.0.0", port=PORT)


threading.Thread(target=run_web).start()


ITEM_DEFINITIONS = {
    "gold": {
        "label": "ذهب",
        "icon": "🥇",
        "base_buy": 1200,
        "base_sell": 850,
        "min_buy": 700,
        "max_buy": 18000,
        "step": 100,
        "auction_quantity": 3,
        "color": COLOR_GOLD,
        "update_seconds": PRICE_UPDATE_SECONDS,
        "delta_min": 100,
        "delta_max": 3500,
        "roulette_chance": None,
    },
    "diamonds": {
        "label": "ألماس",
        "icon": "💎",
        "base_buy": 2500,
        "base_sell": 1800,
        "min_buy": 700,
        "max_buy": 28000,
        "step": 100,
        "auction_quantity": 2,
        "color": COLOR_INFO,
        "update_seconds": PRICE_UPDATE_SECONDS,
        "delta_min": 200,
        "delta_max": 5000,
        "roulette_chance": None,
    },
    "lands": {
        "label": "أرض",
        "icon": "🏝️",
        "base_buy": 6000,
        "base_sell": 4500,
        "min_buy": 3500,
        "max_buy": 33000,
        "step": 500,
        "auction_quantity": 1,
        "color": COLOR_LAND,
        "update_seconds": PRICE_UPDATE_SECONDS,
        "delta_min": 500,
        "delta_max": 6000,
        "roulette_chance": None,
    },
    "stocks": {
        "label": "أسهم",
        "icon": "📈",
        "base_buy": 1500,
        "base_sell": 1300,
        "min_buy": 800,
        "max_buy": 50000,
        "step": 100,
        "auction_quantity": 5,
        "color": COLOR_STOCK,
        "update_seconds": PRICE_UPDATE_SECONDS,
        "delta_min": 100,
        "delta_max": 8000,
        "roulette_chance": "العادي",
    },
    "almarai_stock": {
        "label": "سهم المراعي",
        "icon": "🥛",
        "fixed_buy": 250000,
        "fixed_sell": 250000,
        "color": COLOR_SUCCESS,
        "roulette_chance": "1%",
    },
    "naseej_stock": {
        "label": "سهم ناسة",
        "icon": "🏙️",
        "fixed_buy": 900000,
        "fixed_sell": 900000,
        "color": COLOR_INFO,
        "roulette_chance": "0.5%",
    },
    "sabic_stock": {
        "label": "سهم سابك",
        "icon": "🏭",
        "fixed_buy": 850000,
        "fixed_sell": 850000,
        "color": COLOR_WARNING,
        "roulette_chance": "0.3%",
    },
    "aramco_stock": {
        "label": "سهم أرامكو",
        "icon": "🛢️",
        "fixed_buy": 1000000,
        "fixed_sell": 1000000,
        "color": COLOR_GOLD,
        "roulette_chance": None,
        "admin_only": True,
    },
    "companies": {
        "label": "شركة",
        "icon": "🏢",
        "fixed_buy": COMPANY_PRICE,
        "fixed_sell": COMPANY_PRICE,
        "color": COLOR_INFO,
        "roulette_chance": None,
    },
}

BUYABLE_DYNAMIC_ITEMS = ("gold", "diamonds", "lands", "stocks")
FIXED_STOCK_ITEMS = ("almarai_stock", "naseej_stock", "sabic_stock", "aramco_stock")
MARKET_ALLOWED_ITEMS = ("gold", "diamonds", "lands", "stocks", "almarai_stock", "naseej_stock", "sabic_stock", "aramco_stock", "companies")

ITEM_ALIASES = {
    "ذهب": "gold",
    "gold": "gold",
    "الماس": "diamonds",
    "ألماس": "diamonds",
    "diamond": "diamonds",
    "diamonds": "diamonds",
    "ارض": "lands",
    "أرض": "lands",
    "land": "lands",
    "lands": "lands",
    "سهم": "stocks",
    "اسهم": "stocks",
    "أسهم": "stocks",
    "stock": "stocks",
    "stocks": "stocks",
    "سهم المراعي": "almarai_stock",
    "المراعي": "almarai_stock",
    "almarai": "almarai_stock",
    "سهم ناسة": "naseej_stock",
    "ناسة": "naseej_stock",
    "nasa": "naseej_stock",
    "naseej": "naseej_stock",
    "سهم سابك": "sabic_stock",
    "سابك": "sabic_stock",
    "sabic": "sabic_stock",
    "سهم ارامكو": "aramco_stock",
    "سهم أرامكو": "aramco_stock",
    "ارامكو": "aramco_stock",
    "أرامكو": "aramco_stock",
    "aramco": "aramco_stock",
    "شركة": "companies",
    "شركه": "companies",
    "company": "companies",
    "companies": "companies",
}

EVENT_REWARD_TYPES = {
    "money": {"label": "فلوس", "key": "money", "icon": "💵", "color": COLOR_SUCCESS},
    "gold": {"label": "ذهب", "key": "gold", "icon": "🥇", "color": COLOR_GOLD},
    "diamonds": {"label": "ألماس", "key": "diamonds", "icon": "💎", "color": COLOR_INFO},
    "lands": {"label": "أراضي", "key": "lands", "icon": "🏝️", "color": COLOR_LAND},
    "stocks": {"label": "أسهم", "key": "stocks", "icon": "📈", "color": COLOR_STOCK},
    "almarai_stock": {"label": "سهم المراعي", "key": "almarai_stock", "icon": "🥛", "color": COLOR_SUCCESS},
    "naseej_stock": {"label": "سهم ناسة", "key": "naseej_stock", "icon": "🏙️", "color": COLOR_INFO},
    "sabic_stock": {"label": "سهم سابك", "key": "sabic_stock", "icon": "🏭", "color": COLOR_WARNING},
    "aramco_stock": {"label": "سهم أرامكو", "key": "aramco_stock", "icon": "🛢️", "color": COLOR_GOLD},
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("bls-economy")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="", intents=intents, help_command=None)
event_cleanup_task: asyncio.Task | None = None
background_task: asyncio.Task | None = None
auto_save_task: asyncio.Task | None = None
views_registered = False
dirty_data = False


def ensure_token() -> None:
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN is missing in environment variables.")


def mark_dirty() -> None:
    global dirty_data
    dirty_data = True


def build_default_prices() -> dict[str, dict[str, int]]:
    prices: dict[str, dict[str, int]] = {}
    for key in BUYABLE_DYNAMIC_ITEMS:
        item = ITEM_DEFINITIONS[key]
        prices[key] = {
            "buy_price": item["base_buy"],
            "sell_price": item["base_sell"],
            "last_update": 0,
        }
    return prices


def next_timestamp(seconds: int) -> int:
    return int(time.time()) + seconds


def default_event_schedule() -> dict[str, Any]:
    return {
        "friday": {
            "enabled": True,
            "time": "16:00",
            "reward_type": "money",
            "amount": 2000,
            "limit": 20,
            "last_run_date": "",
        },
        "saturday": {
            "enabled": True,
            "time": "16:00",
            "reward_type": "gold",
            "amount": 2,
            "limit": 15,
            "last_run_date": "",
        },
    }


def default_system_settings() -> dict[str, Any]:
    return {
        "auto_auction_enabled": True,
        "hidden_auction_enabled": False,
        "scheduled_events_enabled": True,
        "random_events_enabled": True,
        "next_auto_auction_at": next_timestamp(AUTO_AUCTION_INTERVAL_SECONDS),
        "next_hidden_auction_at": next_timestamp(HIDDEN_AUCTION_INTERVAL_SECONDS),
        "next_random_event_at": next_timestamp(RANDOM_EVENT_INTERVAL_SECONDS),
        "last_schedule_post_date": "",
    }


def load_data() -> dict[str, Any]:
    defaults = {
        "users": {},
        "active_event": None,
        "panel_message_id": None,
        "price_panel_message_id": None,
        "event_schedule_message_id": None,
        "prices": build_default_prices(),
        "auctions": {},
        "market_listings": {},
        "systems": default_system_settings(),
        "event_schedule": default_event_schedule(),
    }
    if not DATA_FILE.exists():
        return defaults

    try:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except Exception:
        logger.exception("Failed to load economy data file.")
        return defaults

    for key, value in defaults.items():
        data.setdefault(key, value)

    data["systems"] = {**default_system_settings(), **data.get("systems", {})}
    data["event_schedule"] = {
        "friday": {**default_event_schedule()["friday"], **data.get("event_schedule", {}).get("friday", {})},
        "saturday": {**default_event_schedule()["saturday"], **data.get("event_schedule", {}).get("saturday", {})},
    }
    for item_key, item_prices in build_default_prices().items():
        existing = data["prices"].setdefault(item_key, item_prices)
        existing.setdefault("buy_price", item_prices["buy_price"])
        existing.setdefault("sell_price", item_prices["sell_price"])
        existing.setdefault("last_update", 0)
    return data


data_store = load_data()


def ensure_state() -> None:
    data_store.setdefault("users", {})
    data_store.setdefault("active_event", None)
    data_store.setdefault("panel_message_id", None)
    data_store.setdefault("price_panel_message_id", None)
    data_store.setdefault("event_schedule_message_id", None)
    data_store.setdefault("prices", build_default_prices())
    data_store.setdefault("auctions", {})
    data_store.setdefault("market_listings", {})
    data_store["systems"] = {**default_system_settings(), **data_store.get("systems", {})}
    data_store["event_schedule"] = {
        "friday": {**default_event_schedule()["friday"], **data_store.get("event_schedule", {}).get("friday", {})},
        "saturday": {**default_event_schedule()["saturday"], **data_store.get("event_schedule", {}).get("saturday", {})},
    }
    for item_key, item_prices in build_default_prices().items():
        current = data_store["prices"].setdefault(item_key, item_prices)
        current.setdefault("buy_price", item_prices["buy_price"])
        current.setdefault("sell_price", item_prices["sell_price"])
        current.setdefault("last_update", 0)


ensure_state()


def save_data(force: bool = False) -> None:
    global dirty_data
    if not force and not dirty_data:
        return
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(data_store, file, ensure_ascii=False, indent=2)
    dirty_data = False


async def auto_save_loop() -> None:
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            save_data()
        except Exception as exc:
            logger.error("Auto save failed: %s", exc)
        await asyncio.sleep(60)


def create_user(user_id: int) -> dict[str, Any]:
    return {
        "userId": str(user_id),
        "money": START_MONEY,
        "gold": 0,
        "diamonds": 0,
        "lands": 0,
        "stocks": 0,
        "companies": 0,
        "almarai_stock": 0,
        "naseej_stock": 0,
        "sabic_stock": 0,
        "aramco_stock": 0,
        "lastInvest": 0,
        "lastTrade": 0,
        "lastSteal": 0,
        "lastDaily": 0,
        "lastRoulette": 0,
        "protectionUntil": 0,
        "loan": None,
    }


def get_user(user_id: int) -> dict[str, Any]:
    key = str(user_id)
    if key not in data_store["users"]:
        data_store["users"][key] = create_user(user_id)
        mark_dirty()
    user = data_store["users"][key]
    for field in ("stocks", "companies", "loan", "gold", "diamonds", "lands", "almarai_stock", "naseej_stock", "sabic_stock", "aramco_stock"):
        if field == "loan":
            user.setdefault(field, None)
        else:
            user.setdefault(field, 0)
    return user


def save_user(user: dict[str, Any]) -> None:
    data_store["users"][user["userId"]] = user
    mark_dirty()


def has_admin_access(member: discord.Member) -> bool:
    return any(role.id == ADMIN_ROLE_ID for role in member.roles)


def base_embed(color: int = COLOR_PRIMARY) -> discord.Embed:
    embed = discord.Embed(color=color)
    embed.set_footer(text="BLS Economy")
    return embed


def info_embed(title: str, description: str, color: int = COLOR_PRIMARY) -> discord.Embed:
    embed = base_embed(color)
    embed.title = title
    embed.description = description
    return embed


def card_embed(title: str, value: str, color: int, icon: str) -> discord.Embed:
    embed = base_embed(color)
    embed.add_field(name=f"{icon} {title}", value=f"```{value}```", inline=False)
    return embed


def format_wait(seconds: int) -> str:
    total = max(0, int(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if hours:
        parts.append(f"{hours} ساعة")
    if minutes:
        parts.append(f"{minutes} دقيقة")
    if secs or not parts:
        parts.append(f"{secs} ثانية")
    return " و ".join(parts)


def get_item_meta(item_key: str) -> dict[str, Any]:
    return ITEM_DEFINITIONS[item_key]


def get_price(item_key: str) -> dict[str, int]:
    return data_store["prices"][item_key]


def get_current_buy_price(item_key: str) -> int:
    if item_key in data_store["prices"]:
        return get_price(item_key)["buy_price"]
    return ITEM_DEFINITIONS[item_key]["fixed_buy"]


def get_current_sell_price(item_key: str) -> int:
    if item_key in data_store["prices"]:
        return get_price(item_key)["sell_price"]
    return ITEM_DEFINITIONS[item_key]["fixed_sell"]


def parse_amount(raw: str) -> int:
    if not raw.isdigit():
        raise ValueError("الكمية لازم تكون رقم صحيح.")
    amount = int(raw)
    if amount <= 0:
        raise ValueError("الكمية لازم تكون أكبر من 0.")
    return amount


def parse_item_key(raw_name: str) -> str:
    item_key = ITEM_ALIASES.get(raw_name.strip().lower())
    if not item_key:
        raise ValueError("العنصر غير معروف.")
    return item_key


def can_use_admin_only_item(item_key: str, member: discord.abc.User) -> bool:
    item = ITEM_DEFINITIONS[item_key]
    if not item.get("admin_only"):
        return True
    return isinstance(member, discord.Member) and has_admin_access(member)


def parse_buy_sell_item(raw_name: str, member: discord.abc.User | None = None) -> dict[str, Any]:
    item_key = parse_item_key(raw_name)
    if member is not None and not can_use_admin_only_item(item_key, member):
        raise ValueError("هذا العنصر مخصص للإدارة فقط.")
    item = ITEM_DEFINITIONS[item_key]
    return {
        "key": item_key,
        "label": item["label"],
        "icon": item["icon"],
        "buy_price": get_current_buy_price(item_key),
        "sell_price": get_current_sell_price(item_key),
    }


def parse_sell_item(raw_name: str) -> dict[str, Any]:
    item_key = parse_item_key(raw_name)
    item = ITEM_DEFINITIONS[item_key]
    return {
        "key": item_key,
        "label": item["label"],
        "icon": item["icon"],
        "buy_price": get_current_buy_price(item_key),
        "sell_price": get_current_sell_price(item_key),
    }


def credit_money(user: dict[str, Any], amount: int) -> tuple[int, int]:
    if amount <= 0:
        return 0, 0
    used_for_negative = 0
    if user["money"] < 0:
        needed = min(amount, abs(user["money"]))
        user["money"] += needed
        amount -= needed
        used_for_negative = needed
    if amount > 0:
        user["money"] += amount
    save_user(user)
    return amount, used_for_negative


def debit_money(user: dict[str, Any], amount: int) -> None:
    if amount <= 0:
        return
    if user["money"] < amount:
        raise ValueError("رصيدك ما يكفي.")
    user["money"] -= amount
    save_user(user)


def recalculate_sell_price(item_key: str, buy_price: int) -> int:
    item = ITEM_DEFINITIONS[item_key]
    ratio = item["base_sell"] / item["base_buy"]
    step = max(50, item["step"] // 2)
    sell_price = int(round((buy_price * ratio) / step) * step)
    return max(step, sell_price)


def random_price_change(item_key: str) -> int:
    item = ITEM_DEFINITIONS[item_key]
    delta = random.randint(item["delta_min"], item["delta_max"])
    direction = random.choice((-1, 1))
    return delta * direction


def adjust_price_by_amount(item_key: str, amount_change: int) -> tuple[int, int]:
    item = ITEM_DEFINITIONS[item_key]
    current = get_price(item_key)
    step = item["step"]
    rounded_change = int(round(amount_change / step) * step)
    new_buy = current["buy_price"] + rounded_change
    new_buy = max(item["min_buy"], min(item["max_buy"], new_buy))
    new_sell = recalculate_sell_price(item_key, new_buy)
    current["buy_price"] = new_buy
    current["sell_price"] = new_sell
    current["last_update"] = time.time()
    mark_dirty()
    return new_buy, new_sell


def adjust_price_auto(item_key: str) -> tuple[int, int]:
    return adjust_price_by_amount(item_key, random_price_change(item_key))


def format_prices_lines() -> str:
    lines = []
    for item_key in BUYABLE_DYNAMIC_ITEMS:
        item = ITEM_DEFINITIONS[item_key]
        price = get_price(item_key)
        extra = ""
        if item.get("roulette_chance"):
            extra = f" | روليت: `{item['roulette_chance']}`"
        lines.append(
            f"{item['icon']} {item['label']}: شراء `{price['buy_price']}` | بيع `{price['sell_price']}`{extra}"
        )
    for item_key in ("almarai_stock", "naseej_stock", "sabic_stock", "aramco_stock"):
        item = ITEM_DEFINITIONS[item_key]
        chance = f" | روليت: `{item['roulette_chance']}`" if item.get("roulette_chance") else ""
        admin_tag = " | إداري فقط" if item.get("admin_only") else ""
        lines.append(
            f"{item['icon']} {item['label']}: شراء `{item['fixed_buy']}` | بيع `{item['fixed_sell']}`{chance}{admin_tag}"
        )
    return "\n".join(lines)


def shop_embed() -> discord.Embed:
    embed = base_embed(COLOR_GOLD)
    embed.title = "المتجر"
    embed.description = (
        f"{format_prices_lines()}\n\n"
        "الأسعار المتغيرة تتحدث تلقائيًا كل 10 دقائق.\n"
        "أمر `متجر` يفتح لك سوق اللاعبين للبيع المباشر."
    )
    return embed


def dashboard_embed(user: dict[str, Any], member: discord.abc.User) -> discord.Embed:
    embed = base_embed(COLOR_INFO)
    embed.title = "لوحة ممتلكاتك"
    protection_left = max(0, int(user.get("protectionUntil", 0) - time.time()))
    loan = user.get("loan")
    if loan:
        loan_text = f"`{loan['balance']}` | المتبقي: `{format_wait(int(loan['due_at'] - time.time()))}`"
    elif user["money"] < 0:
        loan_text = f"رصيد سالب `{abs(user['money'])}`"
    else:
        loan_text = "لا يوجد"
    embed.description = (
        f"💵 المال: `{user['money']}`\n"
        f"🥇 الذهب: `{user['gold']}`\n"
        f"💎 الألماس: `{user['diamonds']}`\n"
        f"🏝️ الأراضي: `{user['lands']}`\n"
        f"📈 الأسهم: `{user['stocks']}`\n"
        f"🥛 سهم المراعي: `{user['almarai_stock']}`\n"
        f"🏙️ سهم ناسة: `{user['naseej_stock']}`\n"
        f"🏭 سهم سابك: `{user['sabic_stock']}`\n"
        f"🛢️ سهم أرامكو: `{user['aramco_stock']}`\n"
        f"🏢 الشركات: `{user['companies']}`\n"
        f"🏦 القرض/الدين: {loan_text}\n"
        f"🛡️ الحماية: {'لا توجد حماية' if protection_left <= 0 else f'مفعلة لمدة `{format_wait(protection_left)}`'}"
    )
    embed.set_author(name=str(member), icon_url=member.display_avatar.url)
    return embed


def admin_panel_embed() -> discord.Embed:
    systems = data_store["systems"]
    embed = base_embed(COLOR_INFO)
    embed.title = "لوحة الإدارة"
    embed.description = (
        f"روم التحكم: `{ADMIN_PANEL_CHANNEL_ID}`\n"
        f"روم الأحداث العامة: `{EVENT_PUBLIC_CHANNEL_ID}`\n"
        f"روم جدول الأحداث: `{EVENT_SCHEDULE_CHANNEL_ID}`\n"
        f"روم المزادات: `{AUCTION_CHANNEL_ID}`\n"
        f"روم سوق اللاعبين: `{MARKET_CHANNEL_ID}`\n"
        f"المزاد التلقائي: `{'شغال' if systems['auto_auction_enabled'] else 'متوقف'}`\n"
        f"المزاد المخفي: `{'شغال' if systems['hidden_auction_enabled'] else 'متوقف'}`\n"
        "الأحداث العشوائية تحاول العمل كل 3 دقائق عند عدم وجود حدث نشط."
    )
    return embed


def price_panel_embed() -> discord.Embed:
    embed = base_embed(COLOR_GOLD)
    embed.title = "لوحة التحكم بالأسعار"
    embed.description = (
        f"{format_prices_lines()}\n\n"
        "كل زر يفتح لك نافذة تكتب فيها مقدار الرفع أو التنزيل بنفسك."
    )
    return embed


def event_schedule_embed() -> discord.Embed:
    schedule = data_store["event_schedule"]
    embed = base_embed(COLOR_INFO)
    embed.title = "جدول أحداث العقار"
    friday = schedule["friday"]
    saturday = schedule["saturday"]
    f_reward = EVENT_REWARD_TYPES[friday["reward_type"]]["label"]
    s_reward = EVENT_REWARD_TYPES[saturday["reward_type"]]["label"]
    embed.description = (
        f"📅 الجمعة: `{friday['time']}` | الجائزة: `{friday['amount']} {f_reward}` | العدد: `{friday['limit']}`\n"
        f"📅 السبت: `{saturday['time']}` | الجائزة: `{saturday['amount']} {s_reward}` | العدد: `{saturday['limit']}`\n\n"
        "مدة كل حدث: `30 دقيقة`\n"
        f"روم استلام الأحداث: `{EVENT_PUBLIC_CHANNEL_ID}`"
    )
    return embed


def event_post_embed(event: dict[str, Any]) -> discord.Embed:
    reward = EVENT_REWARD_TYPES[event["reward_type"]]
    remaining_time = max(0, int(event["expires_at"] - time.time()))
    embed = base_embed(reward["color"])
    embed.title = "حدث خاص"
    claimed_count = len(event.get("claimed_by", []))
    embed.description = (
        f"{reward['icon']} الجائزة لكل شخص: `{event['amount']}` {reward['label']}\n"
        f"🎟️ المقاعد المتبقية: `{event['remaining']}`\n"
        f"✅ عدد المستلمين: `{claimed_count}`\n"
        f"⏳ الوقت المتبقي: `{format_wait(remaining_time)}`\n"
        f"👤 المنشئ: `{event['creator_name']}`"
    )
    return embed


def clean_event_schedule_embed() -> discord.Embed:
    schedule = data_store["event_schedule"]
    embed = base_embed(COLOR_INFO)
    embed.title = "جدول أحداث العقار"
    friday = schedule["friday"]
    saturday = schedule["saturday"]
    f_reward = EVENT_REWARD_TYPES[friday["reward_type"]]["label"]
    s_reward = EVENT_REWARD_TYPES[saturday["reward_type"]]["label"]
    embed.description = (
        "يتم نشر جدول الأحداث يوميًا الساعة `5:00 ص`\n"
        f"📅 الجمعة: `{friday['time']}` | الجائزة: `{friday['amount']} {f_reward}` | العدد: `{friday['limit']}`\n"
        f"📅 السبت: `{saturday['time']}` | الجائزة: `{saturday['amount']} {s_reward}` | العدد: `{saturday['limit']}`\n\n"
        "مدة كل حدث: `30 دقيقة`\n"
        f"روم استلام الأحداث: `{EVENT_PUBLIC_CHANNEL_ID}`"
    )
    return embed


def clean_admin_panel_embed() -> discord.Embed:
    systems = data_store["systems"]
    embed = base_embed(COLOR_INFO)
    embed.title = "لوحة الإدارة"
    embed.description = (
        f"روم التحكم: `{ADMIN_PANEL_CHANNEL_ID}`\n"
        f"روم الأحداث العامة: `{EVENT_PUBLIC_CHANNEL_ID}`\n"
        f"روم جدول الأحداث: `{EVENT_SCHEDULE_CHANNEL_ID}`\n"
        f"روم المزادات: `{AUCTION_CHANNEL_ID}`\n"
        f"روم سوق اللاعبين: `{MARKET_CHANNEL_ID}`\n"
        f"المزاد التلقائي: `{'شغال' if systems['auto_auction_enabled'] else 'متوقف'}`\n"
        f"المزاد المخفي: `{'شغال' if systems['hidden_auction_enabled'] else 'متوقف'}`\n"
        f"الأحداث المجدولة: `{'شغال' if systems['scheduled_events_enabled'] else 'متوقف'}`\n"
        f"الأحداث العشوائية: `{'شغال' if systems['random_events_enabled'] else 'متوقف'}`"
    )
    return embed


def cooldown_left(last_time: float, cooldown: int) -> int:
    return max(0, int(cooldown - (time.time() - last_time)))


def estimate_user_total_value(user: dict[str, Any]) -> int:
    total = user["money"]
    for item_key in ("gold", "diamonds", "lands", "stocks", "almarai_stock", "naseej_stock", "sabic_stock", "aramco_stock"):
        total += user.get(item_key, 0) * get_current_sell_price(item_key)
    total += user.get("companies", 0) * COMPANY_PRICE
    return total


async def delayed_reply(message: discord.Message, **kwargs: Any) -> discord.Message:
    await asyncio.sleep(BOT_REPLY_DELAY_SECONDS)
    return await message.reply(**kwargs)


async def delayed_send(channel: discord.abc.Messageable, **kwargs: Any) -> discord.Message:
    await asyncio.sleep(BOT_REPLY_DELAY_SECONDS)
    return await channel.send(**kwargs)


async def delayed_interaction_send(interaction: discord.Interaction, *, content: str | None = None, embed: discord.Embed | None = None, ephemeral: bool = True, view: discord.ui.View | None = None) -> None:
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=ephemeral)
    await asyncio.sleep(BOT_REPLY_DELAY_SECONDS)
    await interaction.followup.send(content=content, embed=embed, ephemeral=ephemeral, view=view)


async def delayed_interaction_edit(interaction: discord.Interaction, *, content: str | None = None, embed: discord.Embed | None = None, view: discord.ui.View | None = None) -> None:
    if not interaction.response.is_done():
        await interaction.response.defer()
    await asyncio.sleep(BOT_REPLY_DELAY_SECONDS)
    await interaction.edit_original_response(content=content, embed=embed, view=view)


def get_active_event() -> dict[str, Any] | None:
    event = data_store.get("active_event")
    if not event:
        return None
    if event.get("expires_at", 0) <= time.time() or event.get("remaining", 0) <= 0:
        data_store["active_event"] = None
        mark_dirty()
        return None
    return event


def set_active_event(event: dict[str, Any] | None) -> None:
    data_store["active_event"] = event
    mark_dirty()


async def clear_active_event(reason: str = "انتهى الحدث.") -> None:
    global event_cleanup_task
    event = data_store.get("active_event")
    if not event:
        return
    channel = bot.get_channel(event["channel_id"])
    if isinstance(channel, discord.TextChannel):
        try:
            message = await channel.fetch_message(event["message_id"])
            await message.delete()
        except discord.NotFound:
            pass
        except discord.HTTPException:
            logger.exception("Failed to delete event message.")
        try:
            await delayed_send(channel, embed=info_embed("انتهى الحدث", reason, COLOR_WARNING), delete_after=12)
        except discord.HTTPException:
            logger.exception("Failed to send event end message.")
    set_active_event(None)
    if event_cleanup_task and not event_cleanup_task.done():
        event_cleanup_task.cancel()
    event_cleanup_task = None


def schedule_event_cleanup() -> None:
    global event_cleanup_task
    event = get_active_event()
    if not event:
        return
    if event_cleanup_task and not event_cleanup_task.done():
        event_cleanup_task.cancel()

    async def cleanup_after_delay() -> None:
        delay = max(0, event["expires_at"] - time.time())
        await asyncio.sleep(delay)
        await clear_active_event("انتهت مدة الحدث وتم إغلاقه تلقائيًا.")

    event_cleanup_task = asyncio.create_task(cleanup_after_delay())


async def post_event(event: dict[str, Any]) -> None:
    public_channel = bot.get_channel(EVENT_PUBLIC_CHANNEL_ID)
    schedule_channel = bot.get_channel(EVENT_SCHEDULE_CHANNEL_ID)
    if not isinstance(public_channel, discord.TextChannel):
        return
    message = await delayed_send(public_channel, embed=event_post_embed(event), view=ClaimEventView())
    event["message_id"] = message.id
    event["channel_id"] = public_channel.id
    set_active_event(event)
    schedule_event_cleanup()
    if isinstance(schedule_channel, discord.TextChannel):
        try:
            await delayed_send(
                schedule_channel,
                embed=info_embed("بدأ حدث جديد", f"تم تشغيل حدث في روم الأحداث العامة.\nالجائزة: `{event['amount']}` {EVENT_REWARD_TYPES[event['reward_type']]['label']}", COLOR_SUCCESS),
            )
        except discord.HTTPException:
            logger.exception("Failed to send event schedule announcement.")


def build_event_payload(reward_type: str, amount: int, limit: int, creator_name: str) -> dict[str, Any]:
    return {
        "reward_type": reward_type,
        "amount": amount,
        "remaining": limit,
        "claimed_by": [],
        "creator_name": creator_name,
        "channel_id": EVENT_PUBLIC_CHANNEL_ID,
        "message_id": 0,
        "expires_at": time.time() + EVENT_DURATION_SECONDS,
    }


async def maybe_start_random_event() -> None:
    systems = data_store["systems"]
    if not systems.get("random_events_enabled", True):
        return
    now = time.time()
    if now < systems["next_random_event_at"]:
        return
    systems["next_random_event_at"] = next_timestamp(RANDOM_EVENT_INTERVAL_SECONDS)
    mark_dirty()
    if get_active_event():
        return
    roll = random.random() * 100
    if roll <= 1.0:
        reward_type = "aramco_stock"
        amount = 1
        limit = 1
    elif roll <= 2.0:
        reward_type = "almarai_stock"
        amount = 1
        limit = 1
    elif roll <= 2.5:
        reward_type = "naseej_stock"
        amount = 1
        limit = 1
    elif roll <= 2.8:
        reward_type = "sabic_stock"
        amount = 1
        limit = 1
    else:
        reward_type = random.choice(["money", "gold", "diamonds", "lands", "stocks"])
        amount = {
            "money": random.randint(500, 2500),
            "gold": random.randint(1, 3),
            "diamonds": random.randint(1, 2),
            "lands": 1,
            "stocks": random.randint(2, 6),
        }[reward_type]
        limit = random.randint(5, 20)
    await post_event(build_event_payload(reward_type, amount, limit, "BLS Random Event"))


def parse_schedule_time(raw: str) -> tuple[int, int]:
    parts = raw.strip().split(":")
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        raise ValueError("الوقت لازم يكون بصيغة HH:MM")
    hour = int(parts[0])
    minute = int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("وقت غير صالح.")
    return hour, minute


async def maybe_start_scheduled_events() -> None:
    if not data_store["systems"].get("scheduled_events_enabled", True):
        return
    if get_active_event():
        return
    now = datetime.now(TIMEZONE)
    weekday_map = {4: "friday", 5: "saturday"}
    schedule_key = weekday_map.get(now.weekday())
    if not schedule_key:
        return
    config = data_store["event_schedule"][schedule_key]
    if not config.get("enabled", True):
        return
    hour, minute = parse_schedule_time(config["time"])
    if now.hour != hour or now.minute != minute:
        return
    today_key = now.strftime("%Y-%m-%d")
    if config.get("last_run_date") == today_key:
        return
    config["last_run_date"] = today_key
    mark_dirty()
    await post_event(build_event_payload(config["reward_type"], int(config["amount"]), int(config["limit"]), "الحدث المجدول"))
    await refresh_event_schedule_message()


async def maybe_post_daily_schedule_table() -> None:
    now = datetime.now(TIMEZONE)
    if now.hour != 5 or now.minute != 0:
        return
    today_key = now.strftime("%Y-%m-%d")
    systems = data_store["systems"]
    if systems.get("last_schedule_post_date") == today_key:
        return
    systems["last_schedule_post_date"] = today_key
    mark_dirty()
    await refresh_event_schedule_message()


async def update_panel_message(channel: discord.TextChannel) -> None:
    panel_id = data_store.get("panel_message_id")
    view = AdminPanelView()
    if panel_id:
        try:
            message = await channel.fetch_message(panel_id)
            await message.edit(embed=clean_admin_panel_embed(), view=view)
            return
        except discord.NotFound:
            logger.info("Admin panel message not found, creating a new one.")
        except discord.HTTPException:
            logger.exception("Failed to update admin panel message.")
    message = await delayed_send(channel, embed=clean_admin_panel_embed(), view=view)
    data_store["panel_message_id"] = message.id
    mark_dirty()


async def update_price_panel_message(channel: discord.TextChannel) -> None:
    panel_id = data_store.get("price_panel_message_id")
    view = PriceControlView()
    if panel_id:
        try:
            message = await channel.fetch_message(panel_id)
            await message.edit(embed=price_panel_embed(), view=view)
            return
        except discord.NotFound:
            logger.info("Price panel message not found, creating a new one.")
        except discord.HTTPException:
            logger.exception("Failed to update price panel message.")
    message = await delayed_send(channel, embed=price_panel_embed(), view=view)
    data_store["price_panel_message_id"] = message.id
    mark_dirty()


async def refresh_event_schedule_message() -> None:
    channel = bot.get_channel(EVENT_SCHEDULE_CHANNEL_ID)
    if not isinstance(channel, discord.TextChannel):
        return
    message_id = data_store.get("event_schedule_message_id")
    if message_id:
        try:
            message = await channel.fetch_message(message_id)
            await message.edit(embed=clean_event_schedule_embed(), view=None)
            return
        except discord.NotFound:
            pass
        except discord.HTTPException:
            logger.exception("Failed to update event schedule message.")
    message = await delayed_send(channel, embed=clean_event_schedule_embed(), view=None)
    data_store["event_schedule_message_id"] = message.id
    mark_dirty()


async def refresh_admin_room_panels() -> None:
    channel = bot.get_channel(ADMIN_PANEL_CHANNEL_ID)
    if not isinstance(channel, discord.TextChannel):
        return
    try:
        await update_panel_message(channel)
        await update_price_panel_message(channel)
        await refresh_event_schedule_message()
    except discord.HTTPException:
        logger.exception("Failed to refresh admin room panels.")


def get_auction(auction_id: str) -> dict[str, Any] | None:
    auction = data_store["auctions"].get(auction_id)
    if not auction or auction.get("closed"):
        return None
    return auction


def find_auction_by_message(message_id: int) -> dict[str, Any] | None:
    for auction in data_store["auctions"].values():
        if auction.get("message_id") == message_id and not auction.get("closed"):
            return auction
    return None


def list_open_auctions() -> list[dict[str, Any]]:
    return [auction for auction in data_store["auctions"].values() if not auction.get("closed")]


def auction_title(auction: dict[str, Any]) -> str:
    if auction["kind"] == "hidden":
        return "مزاد مخفي"
    if auction["kind"] == "special":
        return auction["title"]
    return "مزاد تلقائي"


def auction_embed(auction: dict[str, Any]) -> discord.Embed:
    asset_meta = get_item_meta(auction["item_key"])
    color = COLOR_SECRET if auction["kind"] == "hidden" else asset_meta["color"]
    embed = base_embed(color)
    embed.title = auction_title(auction)
    remaining = max(0, int(auction["expires_at"] - time.time())) if auction["state"] == "running" else max(0, int(math.ceil(auction["countdown_end_at"] - time.time())))
    timer_line = f"⏳ {'العد النهائي' if auction['state'] == 'countdown' else 'الوقت المتبقي'}: `{remaining}`"
    if auction["current_bid"] > 0:
        top_bid_line = f"💰 أعلى مزايدة: `{auction['current_bid']}`"
        top_user_line = f"👑 أعلى مزايد: <@{auction['current_winner_id']}>"
    else:
        top_bid_line = f"💰 السعر المطروح: `{auction['starting_bid']}`"
        top_user_line = "👑 أعلى مزايد: لا يوجد حتى الآن"
    if auction["kind"] == "hidden":
        item_line = "🎁 الجائزة: شيء مخفي وحصري"
        quantity_line = "❔ التفاصيل: مجهولة"
    else:
        item_line = f"{asset_meta['icon']} العنصر: `{asset_meta['label']}`"
        quantity_line = f"📦 الكمية: `{auction['quantity']}`"
    embed.description = (
        f"{item_line}\n{quantity_line}\n{top_bid_line}\n{top_user_line}\n{timer_line}"
    )
    return embed


def build_auction_view() -> discord.ui.View:
    return AuctionBidOnlyView()


async def update_auction_message(auction: dict[str, Any]) -> None:
    channel = bot.get_channel(auction["channel_id"])
    if not isinstance(channel, discord.TextChannel):
        return
    try:
        message = await channel.fetch_message(auction["message_id"])
        await message.edit(embed=auction_embed(auction), view=build_auction_view())
    except discord.NotFound:
        pass
    except discord.HTTPException:
        logger.exception("Failed to update auction message.")


async def repost_auction_message(auction: dict[str, Any]) -> None:
    channel = bot.get_channel(auction["channel_id"])
    if not isinstance(channel, discord.TextChannel):
        return
    old_message_id = auction.get("message_id", 0)
    if old_message_id:
        try:
            old_message = await channel.fetch_message(old_message_id)
            await old_message.delete()
        except discord.NotFound:
            pass
        except discord.HTTPException:
            logger.exception("Failed to delete old auction message during repost.")
    message = await delayed_send(channel, embed=auction_embed(auction), view=build_auction_view())
    auction["message_id"] = message.id
    mark_dirty()


def upsert_bid_history(auction: dict[str, Any], user_id: int, amount: int, user_name: str) -> None:
    bids = auction.setdefault("bid_history", [])
    filtered = [bid for bid in bids if bid["user_id"] != user_id]
    filtered.append({"user_id": user_id, "amount": amount, "user_name": user_name, "timestamp": time.time()})
    filtered.sort(key=lambda bid: (bid["amount"], bid["timestamp"]), reverse=True)
    auction["bid_history"] = filtered


def get_best_valid_bid(auction: dict[str, Any]) -> dict[str, Any] | None:
    for bid in sorted(auction.get("bid_history", []), key=lambda entry: (entry["amount"], entry["timestamp"]), reverse=True):
        user = get_user(bid["user_id"])
        if user["money"] >= bid["amount"]:
            return bid
    return None


def create_auction_payload(*, kind: str, item_key: str, quantity: int, starting_bid: int, title: str, creator_name: str) -> dict[str, Any]:
    return {
        "auction_id": uuid.uuid4().hex,
        "kind": kind,
        "item_key": item_key,
        "quantity": quantity,
        "starting_bid": starting_bid,
        "current_bid": 0,
        "current_winner_id": None,
        "channel_id": AUCTION_CHANNEL_ID,
        "message_id": 0,
        "expires_at": time.time() + AUCTION_DURATION_SECONDS,
        "state": "running",
        "countdown_end_at": 0,
        "last_countdown_value": 0,
        "bid_history": [],
        "title": title,
        "creator_name": creator_name,
        "closed": False,
    }


async def post_auction(auction: dict[str, Any]) -> None:
    channel = bot.get_channel(AUCTION_CHANNEL_ID)
    if not isinstance(channel, discord.TextChannel):
        return
    message = await delayed_send(channel, embed=auction_embed(auction), view=build_auction_view())
    auction["message_id"] = message.id
    auction["channel_id"] = channel.id
    data_store["auctions"][auction["auction_id"]] = auction
    mark_dirty()


async def create_auto_auction() -> None:
    item_key = random.choice(["gold", "diamonds", "lands", "stocks", "almarai_stock", "sabic_stock"])
    quantity = 1 if item_key in FIXED_STOCK_ITEMS else ITEM_DEFINITIONS[item_key]["auction_quantity"]
    starting_bid = max(500, int(get_current_buy_price(item_key) * quantity * 0.65))
    auction = create_auction_payload(kind="auto", item_key=item_key, quantity=quantity, starting_bid=starting_bid, title="مزاد تلقائي", creator_name="BLS Economy")
    await post_auction(auction)
    data_store["systems"]["next_auto_auction_at"] = next_timestamp(AUTO_AUCTION_INTERVAL_SECONDS)
    mark_dirty()


async def create_hidden_auction() -> None:
    starting_bid = random.choice([2000, 3000, 4000, 5000, 7500])
    auction = create_auction_payload(kind="hidden", item_key="stocks", quantity=1, starting_bid=starting_bid, title="مزاد مخفي", creator_name="BLS Economy")
    await post_auction(auction)
    data_store["systems"]["next_hidden_auction_at"] = next_timestamp(HIDDEN_AUCTION_INTERVAL_SECONDS)
    mark_dirty()


def hidden_auction_reward() -> tuple[str, str]:
    if random.random() < 0.01:
        return "aramco_stock", "🛢️ ربحت سهم أرامكو واحد"
    reward_key = random.choice(["money", "gold", "diamonds", "stocks", "lands"])
    if reward_key == "money":
        amount = random.randint(5000, 18000)
        return reward_key, f"💵 ربحت `{amount}` فلوس"
    if reward_key == "gold":
        amount = random.randint(2, 6)
        return reward_key, f"🥇 ربحت `{amount}` ذهب"
    if reward_key == "diamonds":
        amount = random.randint(1, 3)
        return reward_key, f"💎 ربحت `{amount}` ألماس"
    if reward_key == "stocks":
        amount = random.randint(6, 15)
        return reward_key, f"📈 ربحت `{amount}` أسهم"
    return reward_key, "🏝️ ربحت أرض نادرة واحدة"


async def close_auction_message(auction: dict[str, Any], embed: discord.Embed) -> None:
    channel = bot.get_channel(auction["channel_id"])
    if not isinstance(channel, discord.TextChannel):
        return
    try:
        message = await channel.fetch_message(auction["message_id"])
        await message.edit(embed=embed, view=None)
    except discord.NotFound:
        pass
    except discord.HTTPException:
        logger.exception("Failed to update final auction message.")


async def finish_auction_without_winner(auction: dict[str, Any], reason: str) -> None:
    await close_auction_message(auction, info_embed("انتهى المزاد", reason, COLOR_WARNING))
    auction["closed"] = True
    mark_dirty()


async def finish_auction_with_winner(auction: dict[str, Any]) -> None:
    best_bid = get_best_valid_bid(auction)
    if not best_bid:
        await finish_auction_without_winner(auction, "انتهى المزاد لكن لا يوجد مزايد يملك المبلغ حاليًا.")
        return
    winner = get_user(best_bid["user_id"])
    debit_money(winner, best_bid["amount"])
    result_embed = base_embed(COLOR_SUCCESS)
    result_embed.title = "انتهى المزاد"
    result_embed.description = f"🏆 الفائز: <@{best_bid['user_id']}>\n💰 السعر النهائي: `{best_bid['amount']}`"
    if auction["kind"] == "hidden":
        reward_type, reward_text = hidden_auction_reward()
        if reward_type == "money":
            amount = int(reward_text.split("`")[1])
            credit_money(winner, amount)
        elif reward_type == "gold":
            winner["gold"] += int(reward_text.split("`")[1])
            save_user(winner)
        elif reward_type == "diamonds":
            winner["diamonds"] += int(reward_text.split("`")[1])
            save_user(winner)
        elif reward_type == "stocks":
            winner["stocks"] += int(reward_text.split("`")[1])
            save_user(winner)
        elif reward_type == "lands":
            winner["lands"] += 1
            save_user(winner)
        elif reward_type == "aramco_stock":
            winner["aramco_stock"] += 1
            save_user(winner)
        result_embed.description += f"\n🎁 نتيجة المزاد المخفي: {reward_text}"
    else:
        winner[auction["item_key"]] += auction["quantity"]
        save_user(winner)
        item = get_item_meta(auction["item_key"])
        result_embed.description += f"\n{item['icon']} الجائزة: `{auction['quantity']}` {item['label']}"
    await close_auction_message(auction, result_embed)
    auction["closed"] = True
    mark_dirty()


async def run_auction_countdown_step(auction: dict[str, Any]) -> None:
    remaining = max(0, int(math.ceil(auction["countdown_end_at"] - time.time())))
    if remaining <= 0:
        await finish_auction_with_winner(auction)
        return
    if remaining != auction.get("last_countdown_value"):
        auction["last_countdown_value"] = remaining
        mark_dirty()
        channel = bot.get_channel(auction["channel_id"])
        if isinstance(channel, discord.TextChannel):
            try:
                await delayed_send(channel, content=f"⏳ ينتهي المزاد خلال `{remaining}`", delete_after=2)
            except discord.HTTPException:
                logger.exception("Failed to send auction countdown message.")
        await update_auction_message(auction)


async def tick_auction_system() -> None:
    systems = data_store["systems"]
    now = time.time()
    if systems["auto_auction_enabled"] and now >= systems["next_auto_auction_at"]:
        await create_auto_auction()
    if systems["hidden_auction_enabled"] and now >= systems["next_hidden_auction_at"]:
        await create_hidden_auction()
    for auction in list(list_open_auctions()):
        if auction["state"] == "running" and now >= auction["expires_at"]:
            if auction["current_bid"] <= 0:
                await finish_auction_without_winner(auction, "انتهت مدة المزاد بدون أي مزايدة.")
                continue
            auction["state"] = "countdown"
            auction["countdown_end_at"] = time.time() + AUCTION_COUNTDOWN_SECONDS
            auction["last_countdown_value"] = 0
            mark_dirty()
            await update_auction_message(auction)
            await run_auction_countdown_step(auction)
        elif auction["state"] == "countdown":
            await run_auction_countdown_step(auction)


def get_market_listing(listing_id: str) -> dict[str, Any] | None:
    listing = data_store["market_listings"].get(listing_id)
    if not listing or listing.get("closed"):
        return None
    return listing


def find_listing_by_message(message_id: int) -> dict[str, Any] | None:
    for listing in data_store["market_listings"].values():
        if listing.get("message_id") == message_id and not listing.get("closed"):
            return listing
    return None


def market_embed(listing: dict[str, Any]) -> discord.Embed:
    item = get_item_meta(listing["item_key"])
    embed = base_embed(item["color"])
    embed.title = "عرض جديد في سوق اللاعبين"
    embed.description = (
        f"{item['icon']} العنصر: `{item['label']}`\n"
        f"📦 الكمية المتبقية: `{listing['quantity']}`\n"
        f"💰 السعر للوحدة: `{listing['unit_price']}`\n"
        f"💳 السعر الكلي المتبقي: `{listing['quantity'] * listing['unit_price']}`\n"
        f"👤 البائع: <@{listing['seller_id']}>"
    )
    return embed


def build_market_view() -> discord.ui.View:
    return MarketItemView()


async def post_market_listing(listing: dict[str, Any]) -> None:
    channel = bot.get_channel(MARKET_CHANNEL_ID)
    if not isinstance(channel, discord.TextChannel):
        return
    message = await delayed_send(channel, embed=market_embed(listing), view=build_market_view())
    listing["message_id"] = message.id
    listing["channel_id"] = channel.id
    data_store["market_listings"][listing["listing_id"]] = listing
    mark_dirty()


def create_market_listing_payload(item_key: str, quantity: int, unit_price: int, seller_id: int, seller_name: str) -> dict[str, Any]:
    return {
        "listing_id": uuid.uuid4().hex,
        "item_key": item_key,
        "quantity": quantity,
        "unit_price": unit_price,
        "seller_id": seller_id,
        "seller_name": seller_name,
        "channel_id": MARKET_CHANNEL_ID,
        "message_id": 0,
        "closed": False,
    }


async def update_market_listing_message(listing: dict[str, Any]) -> None:
    channel = bot.get_channel(listing["channel_id"])
    if not isinstance(channel, discord.TextChannel):
        return
    try:
        message = await channel.fetch_message(listing["message_id"])
        await message.edit(embed=market_embed(listing), view=build_market_view())
    except discord.NotFound:
        pass
    except discord.HTTPException:
        logger.exception("Failed to update market listing.")


async def close_market_listing_message(listing: dict[str, Any], embed: discord.Embed) -> None:
    channel = bot.get_channel(listing["channel_id"])
    if not isinstance(channel, discord.TextChannel):
        return
    try:
        message = await channel.fetch_message(listing["message_id"])
        await message.edit(embed=embed, view=None)
    except discord.NotFound:
        pass
    except discord.HTTPException:
        logger.exception("Failed to close market listing.")


async def notify_seller_sale(listing: dict[str, Any], buyer: discord.abc.User, quantity: int, total_price: int) -> None:
    member = bot.get_user(listing["seller_id"])
    item = get_item_meta(listing["item_key"])
    message_text = (
        f"تم شراء `{quantity}` من `{item['label']}` من عرضك.\n"
        f"المشتري: `{buyer}`\n"
        f"المبلغ المحول: `{total_price}`"
    )
    if member:
        try:
            await member.send(embed=info_embed("تم بيع عنصر من متجرك", message_text, COLOR_SUCCESS))
            return
        except discord.HTTPException:
            pass
    channel = bot.get_channel(MARKET_CHANNEL_ID)
    if isinstance(channel, discord.TextChannel):
        await delayed_send(channel, content=f"<@{listing['seller_id']}>", embed=info_embed("إشعار بيع", message_text, COLOR_SUCCESS), delete_after=20)


def calculate_company_sale_total(user: dict[str, Any], quantity: int, include_stocks: bool) -> tuple[int, int]:
    base_total = 0
    for _ in range(quantity):
        base_total += random.randint(185000, 235000)
    bundled_stocks = 0
    if include_stocks and user["stocks"] > 0:
        bundled_stocks = user["stocks"]
        base_total += bundled_stocks * get_current_sell_price("stocks") + bundled_stocks * 350
    return base_total, bundled_stocks


def investment_profit(amount: int) -> int:
    base_floor = max(50, int(amount * 0.35))
    scaled_floor = max(base_floor, int(amount * 0.70) if amount >= 1000 else int(amount * 0.30))
    scaled_ceiling = max(scaled_floor + 50, int(amount * 1.30))
    return random.randint(scaled_floor, scaled_ceiling)


def investment_loss(amount: int, all_in: bool) -> int:
    return amount if all_in else max(1, amount // 2)


def trade_profit(amount: int) -> int:
    floor = max(50, int(amount * 0.40))
    if amount >= 1000:
        floor = max(floor, 700)
    ceiling = max(floor + 50, int(amount * 1.60))
    return random.randint(floor, ceiling)


def trade_loss(amount: int, all_in: bool) -> int:
    return amount if all_in else max(1, amount // 2)


def resolve_steal_amount(victim_money: int) -> int:
    roll = random.random()
    if victim_money <= 0:
        return 0
    if victim_money >= 50000 and roll < 0.30:
        return min(victim_money, random.randint(3500, 6000))
    if victim_money >= 15000 and roll < 0.65:
        return min(victim_money, random.randint(1800, 3500))
    if roll < 0.90:
        return min(victim_money, random.randint(250, min(1500, max(300, victim_money // 6))))
    return min(victim_money, random.randint(1500, min(4500, victim_money)))


def roulette_reward() -> tuple[str, int]:
    roll = random.random() * 100
    if roll < 0.3:
        return "sabic_stock", 1
    if roll < 0.8:
        return "naseej_stock", 1
    if roll < 1.8:
        return "almarai_stock", 1
    reward_type = random.choice(["money", "gold", "diamonds", "lands", "stocks"])
    amount = {
        "money": random.randint(100, 450),
        "gold": random.randint(1, 4),
        "diamonds": random.randint(1, 2),
        "lands": 1,
        "stocks": random.randint(1, 4),
    }[reward_type]
    return reward_type, amount


def build_commands_embed() -> discord.Embed:
    embed = base_embed(COLOR_INFO)
    embed.title = "قائمة الأوامر"
    embed.description = (
        "`ممتلكاتي` أو `رصيدي`\n"
        "`اوامر`\n"
        "`شراء`\n"
        "`اسعار`\n"
        "`راتب`\n"
        "`حماية`\n"
        "`استثمار <مبلغ/كل>`\n"
        "`تداول <مبلغ/كل>`\n"
        "`روليت`\n"
        "`تحويل @شخص <مبلغ>`\n"
        "`سرقة @شخص`\n"
        "`توب`\n"
        "`شراء <العنصر> <الكمية>`\n"
        "`بيع <العنصر> <الكمية/كل>`\n"
        "`شراء شركة <عدد>`\n"
        "`بيع شركة <عدد>`\n"
        "`بيع شركة <عدد> مع_الاسهم`\n"
        "`قرض` أو `قرض <مبلغ>`\n"
        "`سداد` أو `سداد <مبلغ>`\n"
        "`متجر` لفتح سوق اللاعبين\n"
        "أوامر الإدارة: `لوحة الادارة`"
    )
    return embed


class ClaimEventView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="استلام الحدث", style=discord.ButtonStyle.success, custom_id="claim_event")
    async def claim_event(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        event = get_active_event()
        if not event:
            await delayed_interaction_send(interaction, content="لا يوجد حدث نشط الآن.")
            return
        if interaction.channel_id != event["channel_id"]:
            await delayed_interaction_send(interaction, content="هذا الزر ليس لهذا الروم.")
            return
        user_id = str(interaction.user.id)
        if user_id in event["claimed_by"]:
            await delayed_interaction_send(interaction, content="أنت استلمت الحدث بالفعل.")
            return
        user = get_user(interaction.user.id)
        reward_key = EVENT_REWARD_TYPES[event["reward_type"]]["key"]
        if reward_key == "money":
            credit_money(user, event["amount"])
        else:
            user[reward_key] += event["amount"]
            save_user(user)
        event["claimed_by"].append(user_id)
        event["remaining"] -= 1
        reward = EVENT_REWARD_TYPES[event["reward_type"]]
        if event["remaining"] <= 0:
            await delayed_interaction_send(
                interaction,
                embed=card_embed("تم الاستلام", f"{event['amount']} {reward['label']}", reward["color"], reward["icon"]),
            )
            await clear_active_event("تم استلام جميع الجوائز وانتهى الحدث.")
            return
        set_active_event(event)
        await interaction.response.defer()
        await asyncio.sleep(BOT_REPLY_DELAY_SECONDS)
        await interaction.message.edit(embed=event_post_embed(event), view=ClaimEventView())
        await interaction.followup.send(
            embed=card_embed("تم الاستلام", f"{event['amount']} {reward['label']}", reward["color"], reward["icon"]),
            ephemeral=True,
        )


class EventCreateModal(discord.ui.Modal):
    def __init__(self, reward_type: str) -> None:
        reward = EVENT_REWARD_TYPES[reward_type]
        super().__init__(title=f"إنشاء حدث {reward['label']}")
        self.reward_type = reward_type
        self.reward_amount = discord.ui.TextInput(label="كمية الجائزة لكل شخص", placeholder="مثال: 500", max_length=10)
        self.claim_limit = discord.ui.TextInput(label="عدد الأشخاص المسموح لهم", placeholder="مثال: 10", max_length=10)
        self.add_item(self.reward_amount)
        self.add_item(self.claim_limit)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            amount = parse_amount(str(self.reward_amount))
            limit = parse_amount(str(self.claim_limit))
        except ValueError as exc:
            await delayed_interaction_send(interaction, content=str(exc))
            return
        old_event = get_active_event()
        if old_event:
            await clear_active_event("تم استبدال الحدث بحدث جديد.")
        await post_event(build_event_payload(self.reward_type, amount, limit, str(interaction.user)))
        reward = EVENT_REWARD_TYPES[self.reward_type]
        await delayed_interaction_send(
            interaction,
            embed=card_embed("تم إنشاء الحدث", f"{amount} {reward['label']} لعدد {limit} أشخاص", reward["color"], reward["icon"]),
        )


class SpecialAuctionModal(discord.ui.Modal):
    def __init__(self) -> None:
        super().__init__(title="مزاد خاص وحصري")
        self.auction_name = discord.ui.TextInput(label="اسم المزاد", placeholder="مثال: مزاد خاص وحصري", max_length=50)
        self.item_name = discord.ui.TextInput(label="العنصر", placeholder="ذهب أو ألماس أو أرض أو أسهم", max_length=30)
        self.start_price = discord.ui.TextInput(label="السعر الابتدائي", placeholder="مثال: 5000", max_length=12)
        self.quantity = discord.ui.TextInput(label="الكمية", placeholder="مثال: 1", default="1", max_length=6)
        self.add_item(self.auction_name)
        self.add_item(self.item_name)
        self.add_item(self.start_price)
        self.add_item(self.quantity)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            item_key = parse_item_key(str(self.item_name))
            start_price = parse_amount(str(self.start_price))
            quantity = parse_amount(str(self.quantity))
        except ValueError as exc:
            await delayed_interaction_send(interaction, content=str(exc))
            return
        auction = create_auction_payload(kind="special", item_key=item_key, quantity=quantity, starting_bid=start_price, title=str(self.auction_name), creator_name=str(interaction.user))
        await post_auction(auction)
        await delayed_interaction_send(interaction, content="تم إنشاء المزاد الخاص في روم المزادات.")


class PriceAdjustModal(discord.ui.Modal):
    def __init__(self, item_key: str, direction: int) -> None:
        title = f"{'رفع' if direction > 0 else 'تنزيل'} {ITEM_DEFINITIONS[item_key]['label']}"
        super().__init__(title=title)
        self.item_key = item_key
        self.direction = direction
        self.amount = discord.ui.TextInput(label="مقدار التغيير", placeholder="مثال: 2000", max_length=10)
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            value = parse_amount(str(self.amount))
        except ValueError as exc:
            await delayed_interaction_send(interaction, content=str(exc))
            return
        signed = value if self.direction > 0 else -value
        new_buy, new_sell = adjust_price_by_amount(self.item_key, signed)
        await refresh_admin_room_panels()
        item = ITEM_DEFINITIONS[self.item_key]
        await delayed_interaction_send(
            interaction,
            embed=info_embed(
                "تم تحديث السعر",
                f"السعر الجديد لـ {item['label']}:\nشراء `{new_buy}`\nبيع `{new_sell}`",
                COLOR_SUCCESS,
            ),
        )


class EventScheduleModal(discord.ui.Modal):
    def __init__(self) -> None:
        super().__init__(title="إعداد الأحداث المجدولة")
        friday = data_store["event_schedule"]["friday"]
        saturday = data_store["event_schedule"]["saturday"]
        self.friday_time = discord.ui.TextInput(label="وقت الجمعة HH:MM", default=str(friday["time"]), max_length=5)
        self.friday_reward = discord.ui.TextInput(label="جائزة الجمعة", default=str(friday["reward_type"]), max_length=20)
        self.friday_amount = discord.ui.TextInput(label="كمية الجمعة", default=str(friday["amount"]), max_length=10)
        self.saturday_time = discord.ui.TextInput(label="وقت السبت HH:MM", default=str(saturday["time"]), max_length=5)
        self.saturday_reward = discord.ui.TextInput(label="جائزة السبت", default=str(saturday["reward_type"]), max_length=20)
        self.saturday_amount = discord.ui.TextInput(label="كمية السبت", default=str(saturday["amount"]), max_length=10)
        self.add_item(self.friday_time)
        self.add_item(self.friday_reward)
        self.add_item(self.friday_amount)
        self.add_item(self.saturday_time)
        self.add_item(self.saturday_reward)
        self.add_item(self.saturday_amount)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            parse_schedule_time(str(self.friday_time))
            parse_schedule_time(str(self.saturday_time))
            friday_reward = str(self.friday_reward).strip()
            saturday_reward = str(self.saturday_reward).strip()
            if friday_reward not in EVENT_REWARD_TYPES or saturday_reward not in EVENT_REWARD_TYPES:
                raise ValueError("نوع الجائزة غير مدعوم في الجدول.")
            friday_amount = parse_amount(str(self.friday_amount))
            saturday_amount = parse_amount(str(self.saturday_amount))
        except ValueError as exc:
            await delayed_interaction_send(interaction, content=str(exc))
            return
        data_store["event_schedule"]["friday"]["time"] = str(self.friday_time)
        data_store["event_schedule"]["friday"]["reward_type"] = friday_reward
        data_store["event_schedule"]["friday"]["amount"] = friday_amount
        data_store["event_schedule"]["saturday"]["time"] = str(self.saturday_time)
        data_store["event_schedule"]["saturday"]["reward_type"] = saturday_reward
        data_store["event_schedule"]["saturday"]["amount"] = saturday_amount
        mark_dirty()
        await refresh_event_schedule_message()
        await delayed_interaction_send(interaction, content="تم تحديث جدول الأحداث بنجاح.")


class MarketCreateModal(discord.ui.Modal):
    def __init__(self, owner_id: int) -> None:
        super().__init__(title="إضافة عنصر إلى السوق")
        self.owner_id = owner_id
        self.item_name = discord.ui.TextInput(label="العنصر", placeholder="مثال: ذهب أو سهم المراعي", max_length=30)
        self.quantity = discord.ui.TextInput(label="الكمية", placeholder="مثال: 10", max_length=10)
        self.unit_price = discord.ui.TextInput(label="سعر الوحدة", placeholder="مثال: 5000", max_length=12)
        self.add_item(self.item_name)
        self.add_item(self.quantity)
        self.add_item(self.unit_price)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.owner_id:
            await delayed_interaction_send(interaction, content="هذه النافذة خاصة بصاحب الأمر فقط.")
            return
        try:
            item_key = parse_item_key(str(self.item_name))
            quantity = parse_amount(str(self.quantity))
            unit_price = parse_amount(str(self.unit_price))
        except ValueError as exc:
            await delayed_interaction_send(interaction, content=str(exc))
            return
        if item_key not in MARKET_ALLOWED_ITEMS:
            await delayed_interaction_send(interaction, content="هذا العنصر غير متاح للبيع في السوق.")
            return
        user = get_user(interaction.user.id)
        if user[item_key] < quantity:
            await delayed_interaction_send(interaction, content="لا تملك هذه الكمية لعرضها في السوق.")
            return
        user[item_key] -= quantity
        save_user(user)
        listing = create_market_listing_payload(item_key, quantity, unit_price, interaction.user.id, str(interaction.user))
        await post_market_listing(listing)
        await delayed_interaction_send(
            interaction,
            embed=info_embed("تم نشر العرض", f"تم نشر `{quantity}` من `{ITEM_DEFINITIONS[item_key]['label']}` بسعر `{unit_price}` للوحدة.", COLOR_SUCCESS),
        )


class MarketBuyModal(discord.ui.Modal):
    def __init__(self, listing_id: str) -> None:
        super().__init__(title="شراء من سوق اللاعبين")
        self.listing_id = listing_id
        self.quantity = discord.ui.TextInput(label="الكمية المطلوبة", placeholder="اكتب الكمية", max_length=10)
        self.add_item(self.quantity)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        listing = get_market_listing(self.listing_id)
        if not listing:
            await delayed_interaction_send(interaction, content="هذا العرض غير متاح الآن.")
            return
        try:
            quantity = parse_amount(str(self.quantity))
        except ValueError as exc:
            await delayed_interaction_send(interaction, content=str(exc))
            return
        if quantity > listing["quantity"]:
            await delayed_interaction_send(interaction, content="الكمية المطلوبة أكبر من المتاح.")
            return
        if interaction.user.id == listing["seller_id"]:
            await delayed_interaction_send(interaction, content="لا يمكنك شراء عرضك الخاص.")
            return
        buyer = get_user(interaction.user.id)
        seller = get_user(listing["seller_id"])
        total_price = quantity * listing["unit_price"]
        if buyer["money"] < total_price:
            await delayed_interaction_send(interaction, content="رصيدك لا يكفي لإتمام الشراء.")
            return
        buyer["money"] -= total_price
        seller_credit, _ = credit_money(seller, total_price)
        buyer[listing["item_key"]] += quantity
        listing["quantity"] -= quantity
        save_user(buyer)
        save_user(seller)
        if listing["quantity"] <= 0:
            listing["closed"] = True
            await close_market_listing_message(listing, info_embed("تم بيع العرض", f"تم بيع كامل العرض وتحويل `{seller_credit}` للبائع.", COLOR_SUCCESS))
        else:
            await update_market_listing_message(listing)
        mark_dirty()
        await notify_seller_sale(listing, interaction.user, quantity, total_price)
        await delayed_interaction_send(
            interaction,
            embed=info_embed("تم الشراء", f"اشتريت `{quantity}` من `{ITEM_DEFINITIONS[listing['item_key']]['label']}` بقيمة `{total_price}`.", COLOR_SUCCESS),
        )


class MarketItemView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="شراء", style=discord.ButtonStyle.success, custom_id="market_buy")
    async def buy_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if interaction.message is None:
            await delayed_interaction_send(interaction, content="تعذر قراءة العرض.")
            return
        listing = find_listing_by_message(interaction.message.id)
        if not listing:
            await delayed_interaction_send(interaction, content="العرض غير متاح الآن.")
            return
        await interaction.response.send_modal(MarketBuyModal(listing["listing_id"]))

    @discord.ui.button(label="إلغاء العرض", style=discord.ButtonStyle.danger, custom_id="market_cancel")
    async def cancel_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if interaction.message is None:
            await delayed_interaction_send(interaction, content="تعذر قراءة العرض.")
            return
        listing = find_listing_by_message(interaction.message.id)
        if not listing:
            await delayed_interaction_send(interaction, content="العرض غير موجود.")
            return
        is_admin = isinstance(interaction.user, discord.Member) and has_admin_access(interaction.user)
        if interaction.user.id != listing["seller_id"] and not is_admin:
            await delayed_interaction_send(interaction, content="فقط البائع أو الإدارة يمكنهم إلغاء العرض.")
            return
        seller = get_user(listing["seller_id"])
        seller[listing["item_key"]] += listing["quantity"]
        save_user(seller)
        listing["closed"] = True
        mark_dirty()
        await close_market_listing_message(listing, info_embed("تم إلغاء العرض", f"تم إرجاع `{listing['quantity']}` إلى البائع.", COLOR_WARNING))
        await delayed_interaction_send(interaction, content="تم إلغاء العرض بنجاح.")


class MarketLauncherView(discord.ui.View):
    def __init__(self, owner_id: int) -> None:
        super().__init__(timeout=120)
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("هذه النافذة خاصة بصاحب الأمر فقط.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="إضافة عنصر للبيع", style=discord.ButtonStyle.primary)
    async def add_item_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(MarketCreateModal(self.owner_id))


class ProtectedStealAttemptView(discord.ui.View):
    def __init__(self, thief_id: int, victim_id: int) -> None:
        super().__init__(timeout=60)
        self.thief_id = thief_id
        self.victim_id = victim_id
        self.correct_choice = random.choice(["A", "B", "C"])

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.thief_id:
            await interaction.response.send_message("هذه المحاولة ليست لك.", ephemeral=True)
            return False
        return True

    async def resolve_choice(self, interaction: discord.Interaction, choice: str) -> None:
        thief = get_user(self.thief_id)
        victim = get_user(self.victim_id)
        for child in self.children:
            child.disabled = True
        if choice != self.correct_choice:
            credit_money(victim, STEAL_PROTECTED_COST)
            thief["lastSteal"] = time.time()
            save_user(victim)
            save_user(thief)
            await delayed_interaction_edit(
                interaction,
                embed=info_embed("فشلت المحاولة", f"اختيارك كان خطأ.\nتم تحويل `{STEAL_PROTECTED_COST}` للهدف.", COLOR_DANGER),
                view=self,
            )
            return
        stolen = resolve_steal_amount(max(1, victim["money"]))
        victim["money"] -= stolen
        thief["money"] += STEAL_PROTECTED_COST + stolen
        thief["lastSteal"] = time.time()
        save_user(victim)
        save_user(thief)
        await delayed_interaction_edit(
            interaction,
            embed=info_embed("نجحت السرقة", f"استرجعت `{STEAL_PROTECTED_COST}` وسرقت `{stolen}`.", COLOR_SUCCESS),
            view=self,
        )

    @discord.ui.button(label="A", style=discord.ButtonStyle.primary)
    async def choice_a(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.resolve_choice(interaction, "A")

    @discord.ui.button(label="B", style=discord.ButtonStyle.primary)
    async def choice_b(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.resolve_choice(interaction, "B")

    @discord.ui.button(label="C", style=discord.ButtonStyle.primary)
    async def choice_c(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.resolve_choice(interaction, "C")


class ProtectedStealConfirmView(discord.ui.View):
    def __init__(self, thief_id: int, victim_id: int) -> None:
        super().__init__(timeout=60)
        self.thief_id = thief_id
        self.victim_id = victim_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.thief_id:
            await interaction.response.send_message("هذه المحاولة ليست لك.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="إي", style=discord.ButtonStyle.danger)
    async def yes_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        thief = get_user(self.thief_id)
        if thief["money"] < STEAL_PROTECTED_COST:
            await delayed_interaction_send(interaction, content="تحتاج 500 لبدء محاولة تجاوز الحماية.")
            return
        thief["money"] -= STEAL_PROTECTED_COST
        save_user(thief)
        await delayed_interaction_edit(
            interaction,
            embed=info_embed("اختر الخيار الصحيح", "واحد فقط صحيح. إذا اخترته تنجح السرقة، وإذا أخطأت تفشل المحاولة.", COLOR_WARNING),
            view=ProtectedStealAttemptView(self.thief_id, self.victim_id),
        )

    @discord.ui.button(label="لا", style=discord.ButtonStyle.secondary)
    async def no_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await delayed_interaction_edit(interaction, embed=info_embed("تم الإلغاء", "تم إلغاء محاولة السرقة المحمية.", COLOR_WARNING), view=None)


class ResetConfirmView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=60)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.channel_id != ADMIN_PANEL_CHANNEL_ID:
            await interaction.response.send_message("استخدم هذه اللوحة داخل روم الإدارة فقط.", ephemeral=True)
            return False
        if not isinstance(interaction.user, discord.Member) or not has_admin_access(interaction.user):
            await interaction.response.send_message("هذه اللوحة مخصصة فقط للرتبة المصرح لها.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="نعم", style=discord.ButtonStyle.danger, custom_id="confirm_reset_yes")
    async def confirm_yes(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        users = data_store.get("users", {})
        for user in users.values():
            reset = create_user(int(user["userId"]))
            user.clear()
            user.update(reset)
        data_store["auctions"] = {}
        data_store["market_listings"] = {}
        data_store["systems"] = default_system_settings()
        mark_dirty()
        await clear_active_event("تم تصفير الاقتصاد وإغلاق الحدث الحالي.")
        for child in self.children:
            child.disabled = True
        await delayed_interaction_edit(
            interaction,
            embed=info_embed("تم التصفير", f"تم تصفير الاقتصاد لعدد `{len(users)}` مستخدم.", COLOR_DANGER),
            view=self,
        )
        self.stop()

    @discord.ui.button(label="لا", style=discord.ButtonStyle.secondary, custom_id="confirm_reset_no")
    async def confirm_no(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        for child in self.children:
            child.disabled = True
        await delayed_interaction_edit(interaction, embed=info_embed("تم الإلغاء", "تم إلغاء عملية التصفير.", COLOR_WARNING), view=self)
        self.stop()


class PriceControlView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.channel_id != ADMIN_PANEL_CHANNEL_ID:
            await interaction.response.send_message("هذه اللوحة تعمل فقط في روم الإدارة.", ephemeral=True)
            return False
        if not isinstance(interaction.user, discord.Member) or not has_admin_access(interaction.user):
            await interaction.response.send_message("هذه اللوحة مخصصة فقط للرتبة المصرح لها.", ephemeral=True)
            return False
        return True

    async def open_modal(self, interaction: discord.Interaction, item_key: str, direction: int) -> None:
        await interaction.response.send_modal(PriceAdjustModal(item_key, direction))

    @discord.ui.button(label="رفع الذهب", style=discord.ButtonStyle.success, custom_id="price_gold_up")
    async def price_gold_up(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.open_modal(interaction, "gold", 1)

    @discord.ui.button(label="تنزيل الذهب", style=discord.ButtonStyle.secondary, custom_id="price_gold_down")
    async def price_gold_down(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.open_modal(interaction, "gold", -1)

    @discord.ui.button(label="رفع الألماس", style=discord.ButtonStyle.success, custom_id="price_diamonds_up")
    async def price_diamonds_up(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.open_modal(interaction, "diamonds", 1)

    @discord.ui.button(label="تنزيل الألماس", style=discord.ButtonStyle.secondary, custom_id="price_diamonds_down")
    async def price_diamonds_down(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.open_modal(interaction, "diamonds", -1)

    @discord.ui.button(label="رفع الأرض", style=discord.ButtonStyle.success, custom_id="price_lands_up", row=1)
    async def price_lands_up(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.open_modal(interaction, "lands", 1)

    @discord.ui.button(label="تنزيل الأرض", style=discord.ButtonStyle.secondary, custom_id="price_lands_down", row=1)
    async def price_lands_down(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.open_modal(interaction, "lands", -1)

    @discord.ui.button(label="رفع الأسهم", style=discord.ButtonStyle.success, custom_id="price_stocks_up", row=2)
    async def price_stocks_up(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.open_modal(interaction, "stocks", 1)

    @discord.ui.button(label="تنزيل الأسهم", style=discord.ButtonStyle.secondary, custom_id="price_stocks_down", row=2)
    async def price_stocks_down(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.open_modal(interaction, "stocks", -1)


class AuctionBidModal(discord.ui.Modal):
    def __init__(self, auction_id: str) -> None:
        super().__init__(title="المزايدة على المزاد")
        self.auction_id = auction_id
        self.bid_amount = discord.ui.TextInput(label="المبلغ", placeholder="اكتب مبلغ المزايدة", max_length=12)
        self.add_item(self.bid_amount)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        auction = get_auction(self.auction_id)
        if not auction:
            await delayed_interaction_send(interaction, content="لا يوجد مزاد نشط الآن.")
            return
        try:
            amount = parse_amount(str(self.bid_amount))
        except ValueError as exc:
            await delayed_interaction_send(interaction, content=str(exc))
            return
        minimum_required = auction["current_bid"] + 1 if auction["current_bid"] > 0 else auction["starting_bid"]
        if amount < minimum_required:
            await delayed_interaction_send(interaction, content=f"لازم تكون المزايدة `{minimum_required}` أو أعلى.")
            return
        user = get_user(interaction.user.id)
        if user["money"] < amount:
            await delayed_interaction_send(interaction, content="ما تقدر تشارك لأن فلوسك ما تكفي.")
            return
        auction["current_bid"] = amount
        auction["current_winner_id"] = interaction.user.id
        upsert_bid_history(auction, interaction.user.id, amount, str(interaction.user))
        if auction["state"] == "countdown":
            auction["countdown_end_at"] = time.time() + AUCTION_COUNTDOWN_SECONDS
            auction["last_countdown_value"] = 0
        mark_dirty()
        await delayed_interaction_send(interaction, content="تم تسجيل مزايدتك.")
        await repost_auction_message(auction)
        channel = bot.get_channel(auction["channel_id"])
        if isinstance(channel, discord.TextChannel):
            await delayed_send(
                channel,
                content=f"📢 {interaction.user.mention}",
                embed=info_embed("تمت مزايدة جديدة", f"تم رفع المزاد إلى `{amount}`.", COLOR_SUCCESS),
                delete_after=AUCTION_BID_CONFIRM_DELETE_AFTER,
            )


class AuctionBidOnlyView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="مزايدة", style=discord.ButtonStyle.success, custom_id="auction_bid_only_button")
    async def bid_button(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if interaction.message is None:
            await interaction.response.send_message("تعذر قراءة رسالة المزاد.", ephemeral=True)
            return
        auction = find_auction_by_message(interaction.message.id)
        if not auction:
            await interaction.response.send_message("لا يوجد مزاد نشط الآن.", ephemeral=True)
            return
        await interaction.response.send_modal(AuctionBidModal(auction["auction_id"]))


class EventScheduleView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="تحديث الجدول", style=discord.ButtonStyle.primary, custom_id="schedule_update")
    async def update_schedule(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if interaction.channel_id != EVENT_SCHEDULE_CHANNEL_ID and interaction.channel_id != ADMIN_PANEL_CHANNEL_ID:
            await interaction.response.send_message("هذا الزر مخصص للإدارة.", ephemeral=True)
            return
        if not isinstance(interaction.user, discord.Member) or not has_admin_access(interaction.user):
            await interaction.response.send_message("هذا الزر مخصص للإدارة فقط.", ephemeral=True)
            return
        await interaction.response.send_modal(EventScheduleModal())


class AdminPanelView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    async def ensure_admin(self, interaction: discord.Interaction) -> bool:
        if interaction.channel_id != ADMIN_PANEL_CHANNEL_ID:
            await interaction.response.send_message("هذه اللوحة تعمل فقط في روم الإدارة.", ephemeral=True)
            return False
        if not isinstance(interaction.user, discord.Member) or not has_admin_access(interaction.user):
            await interaction.response.send_message("هذه اللوحة مخصصة فقط للرتبة المصرح لها.", ephemeral=True)
            return False
        return True

    async def open_event_modal(self, interaction: discord.Interaction, reward_type: str) -> None:
        if not await self.ensure_admin(interaction):
            return
        await interaction.response.send_modal(EventCreateModal(reward_type))

    @discord.ui.button(label="حدث فلوس", style=discord.ButtonStyle.success, custom_id="panel_money")
    async def money_event(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.open_event_modal(interaction, "money")

    @discord.ui.button(label="حدث ذهب", style=discord.ButtonStyle.secondary, custom_id="panel_gold")
    async def gold_event(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.open_event_modal(interaction, "gold")

    @discord.ui.button(label="حدث ألماس", style=discord.ButtonStyle.primary, custom_id="panel_diamonds")
    async def diamonds_event(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.open_event_modal(interaction, "diamonds")

    @discord.ui.button(label="حدث أراضي", style=discord.ButtonStyle.danger, custom_id="panel_lands")
    async def lands_event(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.open_event_modal(interaction, "lands")

    @discord.ui.button(label="حدث أرامكو", style=discord.ButtonStyle.success, custom_id="panel_aramco", row=1)
    async def aramco_event(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.open_event_modal(interaction, "aramco_stock")

    @discord.ui.button(label="مزاد خاص", style=discord.ButtonStyle.primary, custom_id="panel_special_auction", row=1)
    async def special_auction(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self.ensure_admin(interaction):
            return
        await interaction.response.send_modal(SpecialAuctionModal())

    @discord.ui.button(label="تشغيل/إيقاف المزاد", style=discord.ButtonStyle.secondary, custom_id="panel_toggle_auto", row=1)
    async def toggle_auto(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self.ensure_admin(interaction):
            return
        systems = data_store["systems"]
        systems["auto_auction_enabled"] = not systems["auto_auction_enabled"]
        if systems["auto_auction_enabled"]:
            systems["next_auto_auction_at"] = next_timestamp(AUTO_AUCTION_INTERVAL_SECONDS)
        mark_dirty()
        await refresh_admin_room_panels()
        await delayed_interaction_send(interaction, content=f"المزاد التلقائي الآن: `{'شغال' if systems['auto_auction_enabled'] else 'متوقف'}`")

    @discord.ui.button(label="تشغيل/إيقاف المخفي", style=discord.ButtonStyle.secondary, custom_id="panel_toggle_hidden", row=2)
    async def toggle_hidden(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self.ensure_admin(interaction):
            return
        systems = data_store["systems"]
        systems["hidden_auction_enabled"] = not systems["hidden_auction_enabled"]
        if systems["hidden_auction_enabled"]:
            systems["next_hidden_auction_at"] = next_timestamp(HIDDEN_AUCTION_INTERVAL_SECONDS)
        mark_dirty()
        await refresh_admin_room_panels()
        await delayed_interaction_send(interaction, content=f"المزاد المخفي الآن: `{'شغال' if systems['hidden_auction_enabled'] else 'متوقف'}`")

    @discord.ui.button(label="جدولة الأحداث", style=discord.ButtonStyle.primary, custom_id="panel_schedule_events", row=2)
    async def schedule_events(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self.ensure_admin(interaction):
            return
        await interaction.response.send_modal(EventScheduleModal())

    @discord.ui.button(label="تصفير الاقتصاد", style=discord.ButtonStyle.danger, custom_id="panel_reset_economy", row=2)
    async def reset_economy(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self.ensure_admin(interaction):
            return
        await interaction.response.send_message(
            embed=info_embed("تأكيد التصفير", f"هل أنت متأكد؟ سيتم حذف الممتلكات وإرجاع كل لاعب إلى `{START_MONEY}`.", COLOR_DANGER),
            view=ResetConfirmView(),
            ephemeral=True,
        )


    @discord.ui.button(label="تشغيل/إيقاف المجدول", style=discord.ButtonStyle.success, custom_id="panel_toggle_scheduled", row=3)
    async def toggle_scheduled_events(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self.ensure_admin(interaction):
            return
        systems = data_store["systems"]
        systems["scheduled_events_enabled"] = not systems.get("scheduled_events_enabled", True)
        mark_dirty()
        await refresh_admin_room_panels()
        await delayed_interaction_send(
            interaction,
            content=f"الأحداث المجدولة الآن: `{'شغال' if systems['scheduled_events_enabled'] else 'متوقف'}`",
        )

    @discord.ui.button(label="تشغيل/إيقاف العشوائي", style=discord.ButtonStyle.secondary, custom_id="panel_toggle_random", row=3)
    async def toggle_random_events(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not await self.ensure_admin(interaction):
            return
        systems = data_store["systems"]
        systems["random_events_enabled"] = not systems.get("random_events_enabled", True)
        mark_dirty()
        await refresh_admin_room_panels()
        await delayed_interaction_send(
            interaction,
            content=f"الأحداث العشوائية الآن: `{'شغال' if systems['random_events_enabled'] else 'متوقف'}`",
        )

async def maybe_auto_update_prices() -> None:
    changed = False
    now = time.time()
    for item_key in BUYABLE_DYNAMIC_ITEMS:
        item = ITEM_DEFINITIONS[item_key]
        last_update = data_store["prices"][item_key].get("last_update", 0)
        if now - last_update >= item["update_seconds"]:
            adjust_price_auto(item_key)
            changed = True
    if changed:
        await refresh_admin_room_panels()


async def process_loans() -> None:
    now = time.time()
    changed = False
    for user in data_store["users"].values():
        loan = user.get("loan")
        if loan and now >= loan["due_at"]:
            user["money"] -= loan["balance"] + LOAN_LATE_FEE
            user["loan"] = None
            changed = True
    if changed:
        mark_dirty()


async def background_loop() -> None:
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            await maybe_auto_update_prices()
            await process_loans()
            await tick_auction_system()
            await maybe_start_scheduled_events()
            await maybe_post_daily_schedule_table()
            await maybe_start_random_event()
        except Exception:
            logger.exception("Background loop crashed.")
        await asyncio.sleep(5)


@bot.event
async def on_ready() -> None:
    global background_task, views_registered, auto_save_task
    logger.info("Logged in as %s", bot.user)
    if not views_registered:
        bot.add_view(AdminPanelView())
        bot.add_view(PriceControlView())
        bot.add_view(ClaimEventView())
        bot.add_view(AuctionBidOnlyView())
        bot.add_view(MarketItemView())
        bot.add_view(EventScheduleView())
        views_registered = True
    await refresh_admin_room_panels()
    schedule_event_cleanup()
    if background_task is None or background_task.done():
        background_task = asyncio.create_task(background_loop())
    if auto_save_task is None or auto_save_task.done():
        auto_save_task = bot.loop.create_task(auto_save_loop())


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot or message.guild is None:
        return
    content = message.content.strip()
    if not content:
        return
    args = content.split()
    cmd = args[0].lower()
    user = get_user(message.author.id)
    try:
        if cmd == "لوحة" and len(args) > 1 and args[1] == "الادارة":
            if not isinstance(message.author, discord.Member) or not has_admin_access(message.author):
                raise ValueError("هذا الأمر فقط للرتبة المصرح لها.")
            if message.channel.id != ADMIN_PANEL_CHANNEL_ID:
                raise ValueError(f"استخدم هذا الأمر داخل روم الإدارة: {ADMIN_PANEL_CHANNEL_ID}")
            await refresh_admin_room_panels()
            await delayed_reply(message, embed=info_embed("تم", "تم تحديث لوحات الإدارة والأسعار وجدول الأحداث.", COLOR_SUCCESS), delete_after=8)
            return
        allowed_channels = {EVENT_PUBLIC_CHANNEL_ID, ADMIN_PANEL_CHANNEL_ID, MARKET_CHANNEL_ID, EVENT_SCHEDULE_CHANNEL_ID, AUCTION_CHANNEL_ID}
        if message.channel.id not in allowed_channels:
            return
        if cmd in {"ممتلكاتي", "رصيدي", "فلوسي"}:
            await delayed_reply(message, embed=dashboard_embed(user, message.author))
            return
        if cmd in {"اوامر", "أوامر"}:
            await delayed_reply(message, embed=build_commands_embed())
            return
        if cmd == "شراء" and len(args) == 1:
            await delayed_reply(message, embed=shop_embed())
            return
        if cmd in {"اسعار", "أسعار"}:
            await delayed_reply(message, embed=shop_embed())
            return
        if cmd == "متجر":
            await delayed_reply(
                message,
                embed=info_embed("سوق اللاعبين", "اضغط الزر لإضافة عنصر وبيعه داخل سوق اللاعبين بشكل احترافي.", COLOR_INFO),
                view=MarketLauncherView(message.author.id),
            )
            return
        if cmd == "قرض":
            if len(args) == 1:
                await delayed_reply(
                    message,
                    embed=info_embed("طلب قرض", f"الحد الأقصى للقرض هو `{LOAN_MAX_AMOUNT}`.", COLOR_INFO),
                    view=MarketLauncherView(message.author.id) if False else None,
                )
                await delayed_reply(
                    message,
                    embed=info_embed("قرض", "اكتب `قرض <مبلغ>` أو استخدم الصيغة المباشرة.", COLOR_INFO),
                )
                return
            amount = parse_amount(args[1])
            if user.get("loan"):
                raise ValueError("عندك قرض قائم بالفعل، سدده أولًا.")
            if amount > LOAN_MAX_AMOUNT:
                raise ValueError(f"الحد الأقصى للقرض هو `{LOAN_MAX_AMOUNT}`.")
            user["loan"] = {"balance": amount, "due_at": time.time() + LOAN_DURATION_SECONDS}
            credit_money(user, amount)
            await delayed_reply(message, embed=info_embed("تم القرض", f"تم صرف `{amount}` ومدة السداد `ساعة`.", COLOR_SUCCESS))
            return
        if cmd == "سداد":
            if len(args) == 1:
                current_amount = min(user["loan"]["balance"], LOAN_MIN_PAYMENT) if user.get("loan") else 0
                await delayed_reply(message, embed=info_embed("سداد", f"اكتب `سداد <مبلغ>`.\nالحد الأدنى المقترح الآن: `{current_amount or LOAN_MIN_PAYMENT}`", COLOR_INFO))
                return
            amount = parse_amount(args[1])
            if user.get("loan"):
                if amount < LOAN_MIN_PAYMENT:
                    raise ValueError(f"أقل مبلغ للسداد هو `{LOAN_MIN_PAYMENT}`.")
                if user["money"] < amount:
                    raise ValueError("رصيدك ما يكفي.")
                pay = min(amount, user["loan"]["balance"])
                user["money"] -= pay
                user["loan"]["balance"] -= pay
                if user["loan"]["balance"] <= 0:
                    user["loan"] = None
                    save_user(user)
                    await delayed_reply(message, embed=info_embed("تم السداد", "تم سداد القرض بالكامل.", COLOR_SUCCESS))
                    return
                user["loan"]["due_at"] = time.time() + LOAN_DURATION_SECONDS
                save_user(user)
                await delayed_reply(message, embed=info_embed("تم السداد الجزئي", f"سددت `{pay}` والمتبقي `{user['loan']['balance']}` وتم تجديد المهلة لساعة.", COLOR_SUCCESS))
                return
            raise ValueError("لا يوجد عليك قرض قائم.")
        if cmd == "راتب":
            left = cooldown_left(user["lastDaily"], DAILY_COOLDOWN)
            if left > 0:
                await delayed_reply(message, embed=info_embed("انتظر شوي", f"تقدر تستلم راتبك بعد `{format_wait(left)}`.", COLOR_WARNING))
                return
            salary = random.randint(350, 900)
            credited, absorbed = credit_money(user, salary)
            user["lastDaily"] = time.time()
            save_user(user)
            text = f"{salary}"
            if absorbed > 0:
                text += f"\nذهب `{absorbed}` لتقليل الرصيد السالب"
            elif credited != salary:
                text += f"\nالمضاف فعليًا `{credited}`"
            await delayed_reply(message, embed=card_embed("راتبك", text, COLOR_WARNING, "💰"))
            return
        if cmd == "حماية":
            if user["money"] < PROTECTION_COST:
                raise ValueError(f"تحتاج `{PROTECTION_COST}` لتفعيل الحماية.")
            user["money"] -= PROTECTION_COST
            start_from = max(time.time(), float(user.get("protectionUntil", 0)))
            user["protectionUntil"] = start_from + PROTECTION_DURATION_SECONDS
            save_user(user)
            await delayed_reply(message, embed=info_embed("تم تفعيل الحماية", f"تم خصم `{PROTECTION_COST}` وتفعيل الحماية لمدة `ساعتين`.", COLOR_SUCCESS))
            return
        if cmd == "استثمار":
            left = cooldown_left(user["lastInvest"], INVEST_COOLDOWN)
            if left > 0:
                await delayed_reply(message, embed=info_embed("انتظر", f"باقي `{format_wait(left)}` على الاستثمار.", COLOR_WARNING))
                return
            if len(args) < 2:
                raise ValueError("اكتب: استثمار <مبلغ/كل>")
            all_in = args[1] == "كل"
            amount = user["money"] if all_in else parse_amount(args[1])
            if amount > user["money"]:
                raise ValueError("ما عندك المبلغ المطلوب.")
            user["money"] -= amount
            user["lastInvest"] = time.time()
            if random.random() < 0.58:
                gain = investment_profit(amount)
                _, absorbed = credit_money(user, amount + gain)
                text = f"رجع لك رأس المال `{amount}` + ربح `{gain}`"
                if absorbed > 0:
                    text += f"\nتم امتصاص `{absorbed}` للرصد السالب"
                save_user(user)
                await delayed_reply(message, embed=card_embed("ربح الاستثمار", text, COLOR_SUCCESS, "📈"))
            else:
                loss = investment_loss(amount, all_in)
                if not all_in:
                    user["money"] += amount - loss
                save_user(user)
                await delayed_reply(message, embed=card_embed("خسارة الاستثمار", f"-{loss}", COLOR_DANGER, "📉"))
            return
        if cmd == "تداول":
            left = cooldown_left(user["lastTrade"], TRADE_COOLDOWN)
            if left > 0:
                await delayed_reply(message, embed=info_embed("انتظر", f"باقي `{format_wait(left)}` على التداول.", COLOR_WARNING))
                return
            if len(args) < 2:
                raise ValueError("اكتب: تداول <مبلغ/كل>")
            all_in = args[1] == "كل"
            amount = user["money"] if all_in else parse_amount(args[1])
            if amount > user["money"]:
                raise ValueError("ما عندك المبلغ المطلوب.")
            user["money"] -= amount
            user["lastTrade"] = time.time()
            if random.random() < 0.52:
                gain = trade_profit(amount)
                credit_money(user, amount + gain)
                save_user(user)
                await delayed_reply(message, embed=card_embed("ربح التداول", f"رأس المال `{amount}` + ربح `{gain}`", COLOR_SUCCESS, "💹"))
            else:
                loss = trade_loss(amount, all_in)
                if not all_in:
                    user["money"] += amount - loss
                save_user(user)
                await delayed_reply(message, embed=card_embed("خسارة التداول", f"-{loss}", COLOR_DANGER, "📉"))
            return
        if cmd == "روليت":
            left = cooldown_left(user["lastRoulette"], ROULETTE_COOLDOWN)
            if left > 0:
                await delayed_reply(message, embed=info_embed("انتظر", f"الروليت كل 10 دقائق. باقي `{format_wait(left)}`.", COLOR_WARNING))
                return
            user["lastRoulette"] = time.time()
            reward_type, amount = roulette_reward()
            if reward_type == "money":
                credit_money(user, amount)
            else:
                user[reward_type] += amount
                save_user(user)
            reward = EVENT_REWARD_TYPES[reward_type]
            await delayed_reply(message, embed=card_embed("جائزة الروليت", f"{amount} {reward['label']}", reward["color"], reward["icon"]))
            return
        if cmd == "تحويل":
            if len(args) < 3 or not message.mentions:
                raise ValueError("اكتب: تحويل @شخص <مبلغ>")
            target = message.mentions[0]
            if target.bot:
                raise ValueError("ما تقدر تحول لبوت.")
            if target.id == message.author.id:
                raise ValueError("ما تقدر تحول لنفسك.")
            amount = parse_amount(args[-1])
            if amount > user["money"]:
                raise ValueError("رصيدك ما يكفي.")
            receiver = get_user(target.id)
            user["money"] -= amount
            _, absorbed = credit_money(receiver, amount)
            save_user(user)
            await delayed_reply(message, embed=card_embed("تم التحويل", f"{amount} إلى {target.display_name}", COLOR_SUCCESS, "💸"))
            if absorbed > 0:
                await delayed_send(message.channel, content=f"تم استخدام `{absorbed}` من التحويل لتقليل الرصيد السالب لدى {target.mention}.", delete_after=10)
            return
        if cmd == "سرقة":
            if not message.mentions:
                raise ValueError("اكتب: سرقة @شخص")
            target = message.mentions[0]
            if target.bot:
                raise ValueError("ما تقدر تسرق بوت.")
            if target.id == message.author.id:
                raise ValueError("ما تقدر تسرق نفسك.")
            left = cooldown_left(user["lastSteal"], STEAL_COOLDOWN)
            if left > 0:
                await delayed_reply(message, embed=info_embed("انتظر", f"باقي `{format_wait(left)}` على السرقة.", COLOR_WARNING))
                return
            victim = get_user(target.id)
            if victim["money"] <= 0:
                raise ValueError("الهدف ما عنده فلوس.")
            protection_left = max(0, int(victim.get("protectionUntil", 0) - time.time()))
            if protection_left > 0:
                await delayed_reply(
                    message,
                    embed=info_embed("الهدف عليه حماية", f"باقي على الحماية `{format_wait(protection_left)}`.\nهل تريد محاولة تجاوز الحماية مقابل `{STEAL_PROTECTED_COST}`؟", COLOR_WARNING),
                    view=ProtectedStealConfirmView(message.author.id, target.id),
                )
                return
            stolen = resolve_steal_amount(victim["money"])
            victim["money"] -= stolen
            user["money"] += stolen
            user["lastSteal"] = time.time()
            save_user(victim)
            save_user(user)
            await delayed_reply(message, content=f"🚨 {target.mention}", embed=card_embed("المبلغ المسروق", str(stolen), 0xFF8C00, "🕵️"))
            return
        if cmd == "توب":
            all_users = list(data_store["users"].values())
            ranked = sorted(all_users, key=estimate_user_total_value, reverse=True)[:10]
            lines = []
            for index, ranked_user in enumerate(ranked, start=1):
                member = message.guild.get_member(int(ranked_user["userId"]))
                name = member.display_name if member else f"User {ranked_user['userId']}"
                lines.append(f"`#{index}` {name} - `{estimate_user_total_value(ranked_user)}`")
            embed = base_embed(COLOR_GOLD)
            embed.title = "أغنى اللاعبين"
            embed.description = "\n".join(lines) if lines else "لا يوجد بيانات بعد."
            await delayed_reply(message, embed=embed)
            return
        if cmd == "شراء" and len(args) >= 2 and args[1] == "شركة":
            quantity = 1 if len(args) < 3 else parse_amount(args[2])
            total = COMPANY_PRICE * quantity
            if user["money"] < total:
                raise ValueError(f"تحتاج `{total}` لشراء {quantity} شركة.")
            user["money"] -= total
            user["companies"] += quantity
            save_user(user)
            await delayed_reply(message, embed=card_embed("تم شراء شركة", f"{quantity} شركة مقابل {total}", COLOR_SUCCESS, "🏢"))
            return
        if cmd == "بيع" and len(args) >= 2 and args[1] == "شركة":
            quantity = 1 if len(args) < 3 else parse_amount(args[2])
            if user["companies"] < quantity:
                raise ValueError("ما عندك هذا العدد من الشركات.")
            include_stocks = len(args) >= 4 and args[3] in {"مع_الاسهم", "مع-الاسهم", "معالاسهم"}
            total_sale, bundled_stocks = calculate_company_sale_total(user, quantity, include_stocks)
            user["companies"] -= quantity
            if include_stocks and bundled_stocks > 0:
                user["stocks"] = 0
            credit_money(user, total_sale)
            save_user(user)
            sale_text = f"{quantity} شركة مقابل {total_sale}"
            if include_stocks:
                sale_text += f"\nتم نقل `{bundled_stocks}` أسهم مع الشركة"
            await delayed_reply(message, embed=card_embed("تم بيع الشركة", sale_text, COLOR_WARNING, "🏢"))
            return
        if cmd == "شراء":
            if len(args) < 3:
                raise ValueError("اكتب: شراء <العنصر> <الكمية>")
            item = parse_buy_sell_item(args[1], message.author)
            quantity = parse_amount(args[2])
            total_price = item["buy_price"] * quantity
            if user["money"] < total_price:
                raise ValueError("فلوسك ما تكفي للشراء.")
            user["money"] -= total_price
            user[item["key"]] += quantity
            save_user(user)
            await delayed_reply(message, embed=card_embed("تم الشراء", f"{quantity} {item['label']} مقابل {total_price}", COLOR_SUCCESS, item["icon"]))
            return
        if cmd == "بيع":
            if len(args) < 3:
                raise ValueError("اكتب: بيع <العنصر> <الكمية/كل>")
            item = parse_sell_item(args[1])
            owned = user[item["key"]]
            quantity = owned if args[2] == "كل" else parse_amount(args[2])
            if quantity > owned:
                raise ValueError("أنت ما تملك هذه الكمية.")
            total_price = item["sell_price"] * quantity
            user[item["key"]] -= quantity
            credit_money(user, total_price)
            save_user(user)
            await delayed_reply(message, embed=card_embed("تم البيع", f"{quantity} {item['label']} مقابل {total_price}", COLOR_WARNING, item["icon"]))
            return
    except ValueError as exc:
        await delayed_reply(message, embed=info_embed("خطأ", str(exc), COLOR_DANGER))
        return
    except Exception:
        logger.exception("Unexpected error while processing a message.")
        await delayed_reply(message, embed=info_embed("خطأ", "صار خطأ غير متوقع، حاول مرة ثانية.", COLOR_DANGER))
        return


ensure_token()
bot.run(DISCORD_TOKEN, log_handler=None)
