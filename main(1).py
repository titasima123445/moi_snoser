import asyncio
import aiohttp
import json
import random
import logging
import os
import re
import secrets
import io
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
from collections import defaultdict
import time
import hashlib
import requests  # для работы с синхронными API

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import Forbidden

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== ДОБАВЛЕННЫЕ API КЛЮЧИ ИЗ ПЕРВОГО ФАЙЛА ====================
API_KEYS_EXTRA = {
    "vk": "0af157510af157510af15751aa0a89e69600af10af157516a0bc15996e74fe2b440998c",
    "ipgeolocation": "73d99145d2e948779263360bfeb67ecc",
    "ip2location": "965108E0429BB3E9329066D8D015564C"
}

FREE_SERVICES = {
    "ipleak": "https://ipleak.net/json/",
    "sypexgeo": "https://api.sypexgeo.net/json/",
    "geoplugin": "http://www.geoplugin.net/json.gp"
}

# ==================== ДОБАВЛЕННЫЕ ФУНКЦИИ ИЗ ПЕРВОГО ФАЙЛА ====================
def vk_get_user_sync(user_id: str) -> dict:
    """
    Синхронная версия получения пользователя VK (из первого файла)
    """
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    })
    url = "https://api.vk.com/method/users.get"
    params = {
        "access_token": API_KEYS_EXTRA["vk"],
        "v": "5.131",
        "user_ids": user_id,
        "fields": "first_name,last_name,status,sex,country,city,bdate,photo_max_orig,online,last_seen,domain,screen_name,about,activities,interests,books,games,movies,music,quotes"
    }
    try:
        resp = session.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if "response" in data and data["response"]:
                user = data["response"][0]
                last_seen_time = user.get("last_seen", {}).get("time", 0)
                if last_seen_time:
                    last_seen = datetime.fromtimestamp(last_seen_time).strftime("%Y-%m-%d %H:%M:%S")
                else:
                    last_seen = "Неизвестно"
                return {
                    "id": user.get("id"),
                    "first_name": user.get("first_name"),
                    "last_name": user.get("last_name"),
                    "full_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
                    "domain": user.get("domain"),
                    "screen_name": user.get("screen_name"),
                    "status": user.get("status", "Нет статуса"),
                    "sex": "Женский" if user.get("sex") == 1 else "Мужской" if user.get("sex") == 2 else "Не указан",
                    "country": user.get("country", {}).get("title", "Не указана"),
                    "city": user.get("city", {}).get("title", "Не указан"),
                    "bdate": user.get("bdate", "Не указана"),
                    "photo": user.get("photo_max_orig", "Нет фото"),
                    "online": "Да" if user.get("online") else "Нет",
                    "last_seen": last_seen,
                    "about": user.get("about", ""),
                    "activities": user.get("activities", ""),
                    "interests": user.get("interests", ""),
                    "quotes": user.get("quotes", "")
                }
            else:
                return {"error": "Пользователь не найден"}
        else:
            return {"error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)[:100]}

def ip_geolocation_sync(ip: str) -> dict:
    """Геолокация через ipgeolocation.io (синхронно)"""
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    url = "https://api.ipgeolocation.io/ipgeo"
    params = {
        "apiKey": API_KEYS_EXTRA["ipgeolocation"],
        "ip": ip
    }
    try:
        resp = session.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if "message" in data:
                return {"error": data["message"]}
            return {
                "ip": data.get("ip"),
                "hostname": data.get("hostname", ""),
                "country": data.get("country_name"),
                "country_code": data.get("country_code2"),
                "city": data.get("city"),
                "region": data.get("state_prov"),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "isp": data.get("isp"),
                "organization": data.get("organization", ""),
                "timezone": data.get("time_zone", {}).get("name"),
                "currency": data.get("currency", {}).get("code", ""),
                "asn": data.get("asn", {}).get("asn", ""),
                "asn_name": data.get("asn", {}).get("name", "")
            }
        else:
            return {"error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)[:100]}

def ip2location_lookup_sync(ip: str) -> dict:
    """Геолокация через ip2location.io (синхронно)"""
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    url = "https://api.ip2location.io/"
    params = {
        "key": API_KEYS_EXTRA["ip2location"],
        "ip": ip
    }
    try:
        resp = session.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if "error" in data:
                return {"error": data["error"].get("error_message", "Unknown error")}
            return {
                "ip": data.get("ip"),
                "country": data.get("country_name"),
                "country_code": data.get("country_code"),
                "city": data.get("city_name"),
                "region": data.get("region_name"),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "isp": data.get("isp"),
                "organization": data.get("organization", ""),
                "timezone": data.get("time_zone", {}).get("name"),
                "asn": data.get("asn")
            }
        else:
            return {"error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)[:100]}

def ip_free_lookup_sync(ip: str) -> dict:
    """Бесплатные IP-сервисы (синхронно)"""
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    results = {}
    # 1. ipleak.net
    try:
        resp = session.get(FREE_SERVICES["ipleak"] + ip, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            results["ipleak"] = {
                "country": data.get("country"),
                "city": data.get("city"),
                "region": data.get("region"),
                "lat": data.get("lat"),
                "lon": data.get("lon"),
                "isp": data.get("isp"),
                "org": data.get("org")
            }
        else:
            results["ipleak"] = {"error": f"HTTP {resp.status_code}"}
    except Exception as e:
        results["ipleak"] = {"error": str(e)[:100]}
    # 2. sypexgeo.net
    try:
        resp = session.get(FREE_SERVICES["sypexgeo"] + ip, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if "country" in data:
                results["sypexgeo"] = {
                    "country": data["country"].get("name_ru"),
                    "country_en": data["country"].get("name_en"),
                    "city": data["city"].get("name_ru"),
                    "city_en": data["city"].get("name_en"),
                    "region": data["region"].get("name_ru"),
                    "lat": data.get("lat"),
                    "lon": data.get("lon"),
                    "timezone": data.get("timezone")
                }
            else:
                results["sypexgeo"] = {"error": "Нет данных"}
        else:
            results["sypexgeo"] = {"error": f"HTTP {resp.status_code}"}
    except Exception as e:
        results["sypexgeo"] = {"error": str(e)[:100]}
    # 3. geoplugin.net
    try:
        resp = session.get(FREE_SERVICES["geoplugin"] + f"?ip={ip}", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if "geoplugin_countryName" in data:
                results["geoplugin"] = {
                    "country": data.get("geoplugin_countryName"),
                    "country_code": data.get("geoplugin_countryCode"),
                    "city": data.get("geoplugin_city"),
                    "region": data.get("geoplugin_region"),
                    "lat": data.get("geoplugin_latitude"),
                    "lon": data.get("geoplugin_longitude"),
                    "timezone": data.get("geoplugin_timezone")
                }
            else:
                results["geoplugin"] = {"error": "Нет данных"}
        else:
            results["geoplugin"] = {"error": f"HTTP {resp.status_code}"}
    except Exception as e:
        results["geoplugin"] = {"error": str(e)[:100]}
    return results

# ==================== КОНФИГУРАЦИЯ ХРАНИЛИЩА ====================
STORAGE_BOT_TOKEN = "8820418184:AAF54zSDwM4L-LzvLVszRQh114nwF3nr_kA"

# ==================== ДОБАВЛЕННЫЕ ДАННЫЕ ИЗ working_apis.json ====================
WORKING_APIS = {
    "ipinfo": {
        "key": "cf2b2febdde638",
        "doc_link": "https://ipinfo.io/developers"
    },
    "ipgeolocation": {
        "key": "73d99145d2e948779263360bfeb67ecc",
        "doc_link": "https://ipgeolocation.io/documentation/ip-location-api.html"
    },
    "bigdatacloud": {
        "key": "bdc_ead54c97234b498c8e0fd13478adeed3",
        "doc_link": "https://www.bigdatacloud.com/docs"
    },
    "ip2location": {
        "key": "965108E0429BB3E9329066D8D015564C",
        "doc_link": "https://www.ip2location.io/ip2location-documentation"
    },
    "veriphone": {
        "key": "D997B34B302B4A06B3AB815312852E51",
        "doc_link": "https://veriphone.io/docs"
    },
    "leakcheck": {
        "key": "49535f49545f5245414c4c595f4150495f4b4559",
        "doc_link": "https://leakcheck.io/docs"
    },
    "leakosint": {
        "key": "7128288325:1AKvhnOZ",
        "doc_link": "https://leakosint.com/docs"
    },
    "abuseipdb": {
        "key": "58878ed65228db88eddfda4983bce5d19d425ddf81f427857b3f59f11aecc34f127862a1cc7d4581",
        "doc_link": "https://www.abuseipdb.com/api"
    },
    "proxycheck1": {
        "key": "9fcd3e6622f96a780f0908ce414bb16360d3779d8253f484f319e02cc5c25065",
        "doc_link": "Нет ссылки"
    },
    "proxycheck2": {
        "key": "dbbc251dda62fb51321132d79b070d00cad48acec4c660f7f0b313eb09056e9b",
        "doc_link": "Нет ссылки"
    },
    "vk_token": {
        "key": "0af157510af157510af15751aa0a89e69600af10af157516a0bc15996e74fe2b440998c",
        "doc_link": "https://vk.com/dev/manuals"
    },
    "newsapi": {
        "key": "a701b803d0ac4fc89aaded6143de644d",
        "doc_link": "https://newsapi.org/docs"
    },
    "ipdata": {
        "key": "c335d87f4e99ce6a747f8628bea61368f7274ff83b39d019c4ed0731",
        "doc_link": "https://ipdata.co/docs.html"
    },
    "vk": {
        "key": "0af157510af157510af15751aa0a89e69600af10af157516a0bc15996e74fe2b440998c",
        "doc_link": "https://vk.com/dev/users.get"
    }
}

# ==================== КОНФИГУРАЦИЯ ====================
BOT_TOKEN = "8951543479:AAEBh-xHlYc_MQLvtW0kkCjhVYdqQS9476M"
ADMIN_USERNAMES = ["Mr_NN333", "Bogvkkm"]
ADMIN_CHAT_ID = 123456789
CHANNEL_ID = -1003963511849

# ==================== ДАННЫЕ ТОЛЬКО В ПАМЯТИ С БЛОКИРОВКАМИ ====================
_user_lock = asyncio.Lock()
_promo_lock = asyncio.Lock()

_user_data = {}
_promo_codes = {}
_promo_codes["TEST1234"] = {
    "max_activations": 10,
    "used_activations": 0,
    "bonus_queries": 3,
    "used_by": []
}

# Кэш для результатов API
_api_cache = {}
_cache_lock = asyncio.Lock()
CACHE_TTL = 60  # 1 минута кэширования

# Ограничение одновременных запросов
_api_semaphore = asyncio.Semaphore(30)

# ==================== РАБОТА С ДАННЫМИ ====================
async def get_user(user_id: int, username: Optional[str] = None) -> dict:
    uid = str(user_id)
    
    async with _user_lock:
        if uid not in _user_data:
            _user_data[uid] = {
                "requests_today": 0,
                "last_request_date": date.today().isoformat(),
                "pro": False,
                "pro_until": None,
                "username": username,
                "bonus_requests": 0,
                "referral_code": generate_referral_code(user_id),
                "referred_by": None,
                "referral_count": 0,
                "custom_api_token": None,
                "first_seen": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat()
            }
            logger.info(f"Новый пользователь: {user_id} (@{username})")
        
        _user_data[uid]["last_active"] = datetime.now().isoformat()
        if username and _user_data[uid].get("username") != username:
            _user_data[uid]["username"] = username
        
        return _user_data[uid].copy()

async def update_user(user_id: int, updates: dict):
    uid = str(user_id)
    
    async with _user_lock:
        if uid not in _user_data:
            _user_data[uid] = {
                "requests_today": 0,
                "last_request_date": date.today().isoformat(),
                "pro": False,
                "pro_until": None,
                "username": None,
                "bonus_requests": 0,
                "referral_code": generate_referral_code(user_id),
                "referred_by": None,
                "referral_count": 0,
                "custom_api_token": None,
                "first_seen": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat()
            }
        
        _user_data[uid].update(updates)
        _user_data[uid]["last_active"] = datetime.now().isoformat()
        logger.debug(f"Обновлён пользователь {user_id}: {updates}")

def generate_referral_code(user_id: int) -> str:
    salt = secrets.token_hex(4)
    raw = f"{user_id}_{salt}"
    return hashlib.md5(raw.encode()).hexdigest()[:8]

async def reset_daily_limit(user_id: int):
    user = await get_user(user_id)
    today = date.today().isoformat()
    if user["last_request_date"] != today:
        async with _user_lock:
            uid = str(user_id)
            if uid in _user_data:
                _user_data[uid]["requests_today"] = 0
                _user_data[uid]["last_request_date"] = today

def is_admin(user) -> bool:
    if not user or not user.username:
        return False
    return user.username.lower() in [name.lower() for name in ADMIN_USERNAMES]

async def is_pro(user_id: int) -> bool:
    user = await get_user(user_id)
    if not user.get("pro", False):
        return False
    until = user.get("pro_until")
    if until is None:
        return False
    try:
        until_date = datetime.fromisoformat(until).date()
        return until_date >= date.today()
    except:
        return False

async def can_search(user_id: int) -> tuple[bool, str]:
    await reset_daily_limit(user_id)
    if await is_pro(user_id):
        return True, "Безлимит (PRO)"
    user = await get_user(user_id)
    daily_limit = 2
    used = user["requests_today"]
    bonus = user.get("bonus_requests", 0)
    available = (daily_limit - used) + bonus
    if available <= 0:
        return False, f"Лимит исчерпан. Доступно: {available} запросов (2 в день + бонусные). Попробуйте завтра или используйте промокод."
    return True, f"Доступно запросов: {available} (из них бонусных: {bonus})"

# ==================== РАБОТА С ПРОМОКОДАМИ ====================
async def activate_promo(user_id: int, code: str) -> tuple[bool, str]:
    global _promo_codes
    
    code = code.upper().strip()
    
    async with _promo_lock:
        if code not in _promo_codes:
            return False, "❌ Неверный промокод."
        
        promo = _promo_codes[code]
        
        if user_id in promo.get("used_by", []):
            return False, "❌ Вы уже активировали этот промокод."
        
        if promo["used_activations"] >= promo["max_activations"]:
            return False, "❌ Этот промокод уже использован максимальное число раз."
        
        user_data = await get_user(user_id)
        current_bonus = user_data.get("bonus_requests", 0)
        new_bonus = current_bonus + promo["bonus_queries"]
        await update_user(user_id, {"bonus_requests": new_bonus})
        
        promo["used_activations"] += 1
        promo["used_by"].append(user_id)
        
        return True, f"✅ Промокод активирован! Вы получили {promo['bonus_queries']} бонусных запросов. Теперь у вас {new_bonus} бонусных запросов."

def generate_promo_code() -> str:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return ''.join(secrets.choice(alphabet) for _ in range(8))

# ==================== ОПЕРАТОРЫ ДЛЯ СНГ ====================
OPERATORS_RU = {}
OPERATORS_UA = {}
OPERATORS_BY = {}
OPERATORS_BY_COUNTRY = {'7': OPERATORS_RU, '380': OPERATORS_UA, '375': OPERATORS_BY}

def get_country_code(phone: str) -> Optional[str]:
    digits = re.sub(r'\D', '', phone)
    if not digits:
        return None
    if digits.startswith('7') and not digits.startswith('77'):
        return '7'
    if digits.startswith('380'):
        return '380'
    if digits.startswith('375'):
        return '375'
    return None

def get_operator_info(phone: str) -> Dict[str, Optional[str]]:
    digits = re.sub(r'\D', '', phone)
    if not digits:
        return {'op': None, 'reg': None, 'city': None}
    country_code = get_country_code(phone)
    if not country_code:
        return {'op': None, 'reg': None, 'city': None}
    ops_dict = OPERATORS_BY_COUNTRY.get(country_code)
    if not ops_dict:
        return {'op': None, 'reg': None, 'city': None}
    if country_code == '7':
        if len(digits) >= 11:
            prefix = digits[1:4]
        else:
            return {'op': None, 'reg': None, 'city': None}
    elif country_code in ('380', '375'):
        if len(digits) >= 12:
            prefix = digits[3:5]
        else:
            return {'op': None, 'reg': None, 'city': None}
    else:
        return {'op': None, 'reg': None, 'city': None}
    info = ops_dict.get(prefix)
    if info:
        return {'op': info['op'], 'reg': info['reg'], 'city': info['city']}
    return {'op': None, 'reg': None, 'city': None}

# ==================== API ДЛЯ ПОИСКА ====================
API_TOKENS = {
    "infinity": {
        "url": "https://infinity-search.fun/find.php",
        "token": "Bjm928HUcvsw923ZMBX19gd110FWSZgd"
    },
    "bigbase": {
        "url": "https://bigbase.top/api/search",
        "token": "yhIkVgFWlT4ldeiauETMCFGkla7-VYtH",
        "headers": {"Authorization": "yhIkVgFWlT4ldeiauETMCFGkla7-VYtH"}
    },
    "depsearch": {
        "url": "https://api.depsearch.sbs/quest={query}&token=OsMTcjyHTRtfABnWA4V3d12SYKVIYE8z"
    },
    "leakosint": {
        "url": "https://leakosintapi.com/",
        "token": WORKING_APIS["leakosint"]["key"]
    },
    "ipdata": {
        "url": "https://api.ipdata.co/",
        "token": "c335d87f4e99ce6a747f8628bea61368f7274ff83b39d019c4ed0731"
    },
    "vk": {
        "url": "https://api.vk.com/method/users.get",
        "token": "0af157510af157510af15751aa0a89e69600af10af157516a0bc15996e74fe2b440998c"
    }
}

# ==================== ГЛОБАЛЬНАЯ СЕССИЯ ====================
_session = None
_session_lock = asyncio.Lock()

async def get_client_session():
    global _session
    async with _session_lock:
        if _session is None or _session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                ttl_dns_cache=300,
                enable_cleanup_closed=True
            )
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            _session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
        return _session

async def close_client_session():
    global _session
    async with _session_lock:
        if _session is not None and not _session.closed:
            await _session.close()
            _session = None

# ==================== ТИПЫ ПОИСКА (ДОБАВЛЕН VK) ====================
SEARCH_TYPES = {"1": "phone", "5": "ip", "6": "vk"}  # добавили "6": "vk"
TYPE_NAMES = {"phone": "📱 Телефон", "ip": "🌐 IP-адрес", "vk": "👤 VK ID/username"}
TYPE_EXAMPLES = {"phone": "+380991234567", "ip": "192.168.1.1", "vk": "durov или 814893236"}

# ==================== API ФУНКЦИИ (ИЗМЕНЕНА ДЛЯ ДОБАВЛЕНИЯ БЕСПЛАТНЫХ IP) ====================
def get_cache_key(api_name: str, query: str, search_type: str) -> str:
    return f"{api_name}:{search_type}:{query}"

async def search_api(api_name: str, query: str, search_type: str, session: aiohttp.ClientSession) -> Dict[str, Any]:
    # Проверяем кэш
    cache_key = get_cache_key(api_name, query, search_type)
    async with _cache_lock:
        if cache_key in _api_cache:
            cached = _api_cache[cache_key]
            if time.time() - cached["timestamp"] < CACHE_TTL:
                logger.debug(f"Кэш hit для {api_name}")
                return cached["data"].copy()
    
    api = API_TOKENS.get(api_name)
    if not api:
        return {"api": api_name, "status": "error", "data": None}
    
    result = {"api": api_name, "status": "error", "data": None}
    headers = api.get("headers", {})
    headers["Content-Type"] = "application/json"
    
    async with _api_semaphore:
        try:
            if api_name == "bigbase":
                payload = {"search": query, "page": 0}
                async with session.post(api["url"], headers=headers, json=payload, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and data != {} and data != []:
                            result["status"] = "success"
                            result["data"] = data
            
            elif api_name == "infinity":
                url = f"{api['url']}?token={api['token']}&{search_type}={query}"
                async with session.get(url, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and data != {} and data != []:
                            result["status"] = "success"
                            result["data"] = data
            
            elif api_name == "depsearch":
                url = f"https://api.depsearch.sbs/quest={query}&token=OsMTcjyHTRtfABnWA4V3d12SYKVIYE8z"
                async with session.get(url, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and data != {} and data != []:
                            result["status"] = "success"
                            result["data"] = data
            
            elif api_name == "leakosint":
                token = api["token"]
                payload = {"token": token, "request": query, "limit": 50, "lang": "ru"}
                async with session.post(api["url"], headers=headers, json=payload, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and data != {} and data != []:
                            result["status"] = "success"
                            result["data"] = data
            
            elif api_name == "ipdata":
                if search_type != "ip":
                    return result
                url = f"{api['url']}{query}?api-key={api['token']}"
                async with session.get(url, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and data != {}:
                            result["status"] = "success"
                            result["data"] = data
            
            elif api_name == "vk":
                # Старый VK API (по ссылке) оставляем для обратной совместимости, но в основном поиске VK обрабатывается отдельно
                match = re.search(r'vk\.com/([^/?]+)', query)
                if not match:
                    return result
                vk_id = match.group(1)
                params = {
                    "user_ids": vk_id,
                    "access_token": api["token"],
                    "v": "5.131",
                    "fields": "id,first_name,last_name,sex,bdate,city,country,photo_max,education,universities,schools,about,activities,books,games,interests,music,movies,tv,quotes,home_town,status,last_seen,exports,connections"
                }
                async with session.get(api["url"], params=params, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and "response" in data:
                            result["status"] = "success"
                            result["data"] = data["response"]
                        else:
                            result["data"] = data
        
        except asyncio.TimeoutError:
            result["status"] = "timeout"
        except Exception as e:
            logger.error(f"Ошибка в API {api_name}: {e}")
            result["status"] = "error"
    
    # Сохраняем в кэш
    if result["status"] == "success" and result["data"]:
        async with _cache_lock:
            _api_cache[cache_key] = {
                "data": result.copy(),
                "timestamp": time.time()
            }
    
    return result

async def search_custom_api(user_token: str, query: str, search_type: str, session: aiohttp.ClientSession) -> Dict[str, Any]:
    result = {"api": "custom", "status": "error", "data": None}
    if not user_token:
        return result
    
    cache_key = get_cache_key("custom", query, search_type)
    async with _cache_lock:
        if cache_key in _api_cache:
            cached = _api_cache[cache_key]
            if time.time() - cached["timestamp"] < CACHE_TTL:
                return cached["data"].copy()
    
    url = "https://leakosintapi.com/"
    headers = {"Content-Type": "application/json"}
    payload = {"token": user_token, "request": query, "limit": 50, "lang": "ru"}
    
    async with _api_semaphore:
        try:
            async with session.post(url, headers=headers, json=payload, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and data != {} and data != []:
                        result["status"] = "success"
                        result["data"] = data
        except asyncio.TimeoutError:
            result["status"] = "timeout"
        except Exception:
            result["status"] = "error"
    
    if result["status"] == "success" and result["data"]:
        async with _cache_lock:
            _api_cache[cache_key] = {
                "data": result.copy(),
                "timestamp": time.time()
            }
    
    return result

async def search_all_apis(query: str, search_type: str, user_id: Optional[int] = None) -> Dict[str, Any]:
    session = await get_client_session()
    
    # Создаём задачи для всех API
    tasks = []
    task_to_api = {}
    
    for name in API_TOKENS:
        task = asyncio.create_task(search_api(name, query, search_type, session))
        tasks.append(task)
        task_to_api[task] = name
    
    if user_id:
        user_data = await get_user(user_id)
        custom_token = user_data.get("custom_api_token")
        if custom_token:
            task = asyncio.create_task(search_custom_api(custom_token, query, search_type, session))
            tasks.append(task)
            task_to_api[task] = "custom"
    
    # Ждём все задачи с таймаутом
    results = {}
    for task in tasks:
        api_name = task_to_api.get(task, "unknown")
        try:
            result = await asyncio.wait_for(task, timeout=15)
            if isinstance(result, dict):
                results[api_name] = {"status": result.get("status", "error"), "data": result.get("data")}
            else:
                results[api_name] = {"status": "error", "data": None}
        except asyncio.TimeoutError:
            task.cancel()
            results[api_name] = {"status": "timeout", "data": None}
        except Exception as e:
            logger.error(f"Ошибка в задаче {api_name}: {e}")
            results[api_name] = {"status": "error", "data": None}
    
    # ===== ДОБАВЛЯЕМ БЕСПЛАТНЫЕ IP-СЕРВИСЫ ИЗ ПЕРВОГО ФАЙЛА =====
    if search_type == "ip":
        try:
            # Запускаем синхронные методы в отдельном потоке
            free_data = await asyncio.to_thread(ip_free_lookup_sync, query)
            for service, data in free_data.items():
                results[service] = {"status": "success" if "error" not in data else "error", "data": data}
            
            ipgeo_data = await asyncio.to_thread(ip_geolocation_sync, query)
            results["ipgeolocation_osint"] = {"status": "success" if "error" not in ipgeo_data else "error", "data": ipgeo_data}
            
            ip2loc_data = await asyncio.to_thread(ip2location_lookup_sync, query)
            results["ip2location_osint"] = {"status": "success" if "error" not in ip2loc_data else "error", "data": ip2loc_data}
        except Exception as e:
            logger.error(f"Ошибка при добавлении бесплатных IP-сервисов: {e}")
    
    return results

# ==================== ФУНКЦИИ ДЛЯ ОБРАБОТКИ ДАННЫХ ====================
def extract_pretty_lines(data: Any) -> List[str]:
    if data is None:
        return ["Нет данных"]
    
    IGNORE_KEYS = {"error", "status", "search_type", "phone_info", "message", "code", "success"}
    
    if isinstance(data, dict):
        if "results" in data and isinstance(data["results"], list):
            data = data["results"]
        else:
            clean_dict = {k: v for k, v in data.items() if k not in IGNORE_KEYS and not k.startswith("_")}
            if not clean_dict:
                return ["Информативные поля отсутствуют"]
            if len(clean_dict) == 1:
                only_key = next(iter(clean_dict))
                if isinstance(clean_dict[only_key], list):
                    data = clean_dict[only_key]
                else:
                    data = clean_dict
            else:
                data = clean_dict
    
    if isinstance(data, list):
        if not data:
            return ["Пустой список"]
        lines = []
        for item in data:
            if isinstance(item, dict):
                pairs = []
                for k, v in item.items():
                    if k not in IGNORE_KEYS and not k.startswith("_"):
                        if isinstance(v, list):
                            v_str = ', '.join(str(x) for x in v[:10])
                            if len(v) > 10:
                                v_str += f" … (+{len(v)-10})"
                        elif isinstance(v, dict):
                            v_str = json.dumps(v, ensure_ascii=False)[:100] + ("…" if len(json.dumps(v, ensure_ascii=False)) > 100 else "")
                        else:
                            v_str = str(v)
                        pairs.append(f"{k}: {v_str}")
                if pairs:
                    lines.append(" | ".join(pairs))
                else:
                    lines.append(str(item)[:200])
            else:
                lines.append(str(item))
        return lines
    elif isinstance(data, dict):
        lines = []
        for k, v in data.items():
            if k not in IGNORE_KEYS and not k.startswith("_"):
                if isinstance(v, list):
                    v_str = ', '.join(str(x) for x in v[:10])
                    if len(v) > 10:
                        v_str += f" … (+{len(v)-10})"
                elif isinstance(v, dict):
                    v_str = json.dumps(v, ensure_ascii=False)[:100] + ("…" if len(json.dumps(v, ensure_ascii=False)) > 100 else "")
                else:
                    v_str = str(v)
                lines.append(f"{k}: {v_str}")
        return lines if lines else ["Информативные поля отсутствуют"]
    else:
        return [str(data)[:500]]

def generate_demo_data(query: str, search_type: str) -> dict:
    demo_data = {
        "phone": {"results": [{
            "operator": random.choice(["Киевстар", "Vodafone", "Lifecell"]),
            "region": random.choice(["Киев", "Харьков", "Львов"]),
            "registered": f"{random.randint(2010, 2024)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
            "social": random.sample(["Telegram", "WhatsApp", "Viber"], 3),
            "name": random.choice(["Иван Петров", "Мария Коваль", "Алексей Шевченко"]),
            "age": random.randint(18, 60)
        }]},
        "ip": {"results": [{
            "country": random.choice(["Ukraine", "USA", "Germany"]),
            "city": random.choice(["Kyiv", "New York", "Berlin"]),
            "isp": random.choice(["Kyivstar", "Vodafone", "Ukrtelecom"])
        }]}
    }
    return demo_data.get(search_type, {"results": [{"message": "Данные найдены"}]})

def build_report_text(query: str, search_type: str, results: dict) -> str:
    lines = []
    lines.append("📊 ОТЧЕТ ПОИСКА")
    lines.append("")
    lines.append(f"📌 Тип: {TYPE_NAMES.get(search_type, search_type)}")
    lines.append(f"🔎 Запрос: {query}")
    lines.append(f"📅 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    all_data_lines = []
    for api_name, api_result in results.items():
        data = api_result.get("data")
        status = api_result.get("status", "error")
        if data:
            pretty = extract_pretty_lines(data)
            if isinstance(pretty, list):
                all_data_lines.append(f"┌─── {api_name} ({status}) ───")
                for line in pretty:
                    all_data_lines.append(f"│ {line}")
                all_data_lines.append("└─────────────────────")
                all_data_lines.append("")
            else:
                all_data_lines.append(f"┌─── {api_name} ({status}) ───")
                all_data_lines.append(f"│ {str(pretty)}")
                all_data_lines.append("└─────────────────────")
                all_data_lines.append("")

    if not any(r.get('data') for r in results.values()):
        demo = generate_demo_data(query, search_type)
        demo_lines = extract_pretty_lines(demo)
        if isinstance(demo_lines, list):
            all_data_lines.append("┌─── ДЕМО-ДАННЫЕ ───")
            for line in demo_lines:
                all_data_lines.append(f"│ {line}")
            all_data_lines.append("└─────────────────────")
        else:
            all_data_lines.append(str(demo_lines))

    if all_data_lines and all_data_lines[-1] == "":
        all_data_lines.pop()

    if all_data_lines:
        for line in all_data_lines:
            lines.append(line)
    else:
        lines.append("    Нет данных для отображения")

    return "\n".join(lines)

def detect_operator(phone: str) -> Optional[str]:
    digits = re.sub(r'\D', '', phone)
    if not digits:
        return None
    if digits.startswith('380'):
        prefix = digits[3:6]
    elif digits.startswith('0'):
        prefix = digits[1:4]
    else:
        return None
    operators = {
        'Киевстар': ['067', '068', '096', '097', '098'],
        'Vodafone': ['050', '066', '095', '099'],
        'Lifecell': ['063', '073', '093'],
    }
    for op, prefixes in operators.items():
        if prefix in prefixes:
            return op
    return None

def parse_phone_data(results: dict, phone_number: Optional[str] = None) -> dict:
    report = {
        "phone": phone_number,
        "operator": None,
        "region": None,
        "personal": [],
        "phonebook": [],
        "banks": [],
        "social": [],
        "total_records": 0,
        "raw_data": []
    }
    
    op_keys = {"operator", "oper", "carrier", "provider", "оператор", "mcc", "mnc"}
    reg_keys = {"region", "city", "town", "area", "state", "country", "регион", "город", "страна", "location"}
    personal_keys = {"name", "fio", "full_name", "first_name", "last_name", "surname", "birth_date", "dob", "age", "birthday", "фИО", "имя", "фамилия", "дата рождения", "возраст", "sex", "gender"}
    phonebook_keys = {"contacts", "phonebook", "names", "people", "friends", "relatives", "телефонная книга", "контакты", "contact_list"}
    bank_keys = {"bank", "banks", "card", "account", "finance", "банк", "карта", "счёт", "credit", "debit"}
    social_keys = {"social", "telegram", "whatsapp", "viber", "instagram", "facebook", "twitter", "vk", "social_media", "social_networks"}
    
    all_entries = []

    def extract_from_dict(d):
        for k, v in d.items():
            k_lower = k.lower()
            
            if any(op in k_lower for op in op_keys):
                if isinstance(v, str) and v.strip():
                    report["operator"] = v.strip()
                elif isinstance(v, dict) and "name" in v:
                    report["operator"] = v["name"]
            
            if any(reg in k_lower for reg in reg_keys):
                if isinstance(v, str) and v.strip():
                    if report["region"] is None:
                        report["region"] = v.strip()
                    elif v.strip() not in report["region"]:
                        report["region"] += ", " + v.strip()
                elif isinstance(v, dict) and "name" in v:
                    if report["region"] is None:
                        report["region"] = v["name"]
                    elif v["name"] not in report["region"]:
                        report["region"] += ", " + v["name"]
            
            if any(pers in k_lower for pers in personal_keys):
                if isinstance(v, str) and v.strip():
                    report["personal"].append(v.strip())
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, str) and item.strip():
                            report["personal"].append(item.strip())
                        elif isinstance(item, dict):
                            for sub_k, sub_v in item.items():
                                if isinstance(sub_v, str) and sub_v.strip():
                                    report["personal"].append(sub_v.strip())
            
            if any(pb in k_lower for pb in phonebook_keys):
                if isinstance(v, list):
                    for item in v:
                        if isinstance(item, str) and item.strip():
                            report["phonebook"].append(item.strip())
                        elif isinstance(item, dict):
                            for sub_k, sub_v in item.items():
                                if isinstance(sub_v, str) and sub_v.strip():
                                    report["phonebook"].append(sub_v.strip())
                elif isinstance(v, str) and v.strip():
                    report["phonebook"].append(v.strip())
                elif isinstance(v, dict):
                    for sub_v in v.values():
                        if isinstance(sub_v, str) and sub_v.strip():
                            report["phonebook"].append(sub_v.strip())
            
            if any(bank in k_lower for bank in bank_keys):
                if isinstance(v, str) and v.strip():
                    report["banks"].append(v.strip())
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, str) and item.strip():
                            report["banks"].append(item.strip())
                elif isinstance(v, dict):
                    for sub_v in v.values():
                        if isinstance(sub_v, str) and sub_v.strip():
                            report["banks"].append(sub_v.strip())
            
            if any(soc in k_lower for soc in social_keys):
                if isinstance(v, str) and v.strip():
                    report["social"].append(v.strip())
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, str) and item.strip():
                            report["social"].append(item.strip())
            
            if isinstance(v, dict):
                extract_from_dict(v)
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        extract_from_dict(item)
                    elif isinstance(item, str) and len(item) > 3:
                        all_entries.append(item)

    # Извлекаем данные из всех API
    for api_name, api_result in results.items():
        data = api_result.get("data")
        if data:
            if isinstance(data, dict):
                extract_from_dict(data)
                report["raw_data"].append({api_name: data})
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        extract_from_dict(item)
                        report["raw_data"].append({api_name: item})
                    elif isinstance(item, str) and len(item) > 3:
                        all_entries.append(item)

    # Определяем оператора если не найден
    if report["operator"] is None and phone_number:
        detected = detect_operator(phone_number)
        if detected:
            report["operator"] = detected
        else:
            info = get_operator_info(phone_number)
            if info and info.get('op'):
                report["operator"] = info['op']
                if report["region"] is None and info.get('reg'):
                    report["region"] = info['reg']

    # Подсчитываем общее количество записей
    total = 0
    for api_name, api_result in results.items():
        data = api_result.get("data")
        if data:
            if isinstance(data, list):
                total += len(data)
            elif isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, list):
                        total += len(v)
                    elif isinstance(v, dict):
                        total += 1
                total += 1
    report["total_records"] = total

    # Удаляем дубликаты
    report["personal"] = list(dict.fromkeys(report["personal"]))
    report["phonebook"] = list(dict.fromkeys(report["phonebook"]))
    report["banks"] = list(dict.fromkeys(report["banks"]))
    report["social"] = list(dict.fromkeys(report["social"]))

    return report

def format_phone_report(report: dict) -> str:
    lines = []
    lines.append(f"🔎 РЕЗУЛЬТАТ ПОИСКА ПО НОМЕРУ {report['phone']}")
    lines.append("=" * 50)
    lines.append("")
    
    lines.append("📱 ИНФОРМАЦИЯ О НОМЕРЕ")
    lines.append(f"├ Номер: {report['phone']}")
    if report.get('operator'):
        lines.append(f"├ Оператор: {report['operator']}")
    if report.get('region'):
        lines.append(f"└ Регион: {report['region']}")
    lines.append("")
    
    if report.get('personal'):
        lines.append("👤 ЛИЧНЫЕ ДАННЫЕ")
        for item in report['personal'][:15]:
            lines.append(f"├ {item}")
        if len(report['personal']) > 15:
            lines.append(f"└ ... и ещё {len(report['personal'])-15} записей")
        lines.append("")
    
    if report.get('social'):
        lines.append("🌐 СОЦИАЛЬНЫЕ СЕТИ")
        for item in report['social'][:10]:
            lines.append(f"├ {item}")
        if len(report['social']) > 10:
            lines.append(f"└ ... и ещё {len(report['social'])-10}")
        lines.append("")
    
    if report.get('phonebook'):
        lines.append("📖 ТЕЛЕФОННАЯ КНИГА")
        phonebook_str = ", ".join(report['phonebook'][:20])
        if len(report['phonebook']) > 20:
            phonebook_str += f", ...и ещё {len(report['phonebook'])-20}"
        lines.append(f"└ {phonebook_str}")
        lines.append("")
    
    if report.get('banks'):
        lines.append("🏦 БАНКОВСКАЯ ИНФОРМАЦИЯ")
        for item in report['banks'][:5]:
            lines.append(f"├ {item}")
        if len(report['banks']) > 5:
            lines.append(f"└ ... и ещё {len(report['banks'])-5}")
        lines.append("")
    
    lines.append("📊 СТАТИСТИКА")
    lines.append(f"├ Всего записей: {report.get('total_records', 0)}")
    lines.append(f"├ Личных данных: {len(report.get('personal', []))}")
    lines.append(f"├ Контактов: {len(report.get('phonebook', []))}")
    lines.append(f"└ Соц.сетей: {len(report.get('social', []))}")
    lines.append("")
    
    lines.append("📎 Полный отчёт в HTML — по кнопке ниже")
    return "\n".join(lines)

def generate_html_report(query: str, search_type: str, results: dict, phone_report: Optional[dict] = None) -> str:
    css = """
    <style>
    *{margin:0;padding:0;box-sizing:border-box}
    body {
        background: #0a0a0f;
        color: #e8e8f0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        padding: 30px 20px;
        line-height: 1.6;
    }
    .container { max-width: 1100px; margin: 0 auto; }
    .header {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border: 1px solid rgba(255,255,255,.08);
        border-radius: 16px;
        padding: 30px;
        margin-bottom: 30px;
    }
    .header h1 { font-size: 28px; font-weight: 700; color: #ff6b6b; }
    .header .meta { color: #8888aa; font-size: 14px; margin-top: 8px; }
    .glass {
        background: rgba(255,255,255,.03);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255,255,255,.08);
        border-radius: 16px;
        overflow: hidden;
        margin-bottom: 24px;
    }
    .card-header {
        background: rgba(255,255,255,.05);
        border-bottom: 1px solid rgba(255,255,255,.06);
        padding: 16px 24px;
        font-weight: 600;
        font-size: 15px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .card-body { padding: 24px; }
    .section {
        background: rgba(255,255,255,.02);
        border: 1px solid rgba(255,255,255,.06);
        border-radius: 12px;
        margin-bottom: 16px;
        overflow: hidden;
    }
    .section-title {
        background: rgba(255,255,255,.03);
        border-bottom: 1px solid rgba(255,255,255,.06);
        padding: 12px 18px;
        font-size: 13px;
        font-weight: 700;
        color: #ff6b6b;
        text-transform: uppercase;
        letter-spacing: .5px;
    }
    .section-body { padding: 16px 18px; }
    .kv-grid {
        display: grid;
        grid-template-columns: auto 1fr;
        gap: 8px 20px;
        font-size: 14px;
    }
    .kv-key { color: #8888aa; font-weight: 500; }
    .kv-val { color: #e8e8f0; word-break: break-word; }
    .badge {
        display: inline-block;
        padding: 2px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-success { background: rgba(61,220,132,.15); color: #3ddc84; }
    .badge-error { background: rgba(255,45,58,.15); color: #ff2d3a; }
    .badge-timeout { background: rgba(255,165,0,.15); color: #ffa500; }
    .chip {
        display: inline-block;
        background: rgba(255,255,255,.06);
        border: 1px solid rgba(255,255,255,.06);
        border-radius: 6px;
        padding: 2px 10px;
        font-size: 13px;
        margin: 2px;
    }
    .value-phone { color: #ffb3b3; font-weight: 600; }
    .value-name { color: #ffffff; font-weight: 600; }
    .value-email { color: #6fc3df; }
    .value-date { color: #ffd8a8; }
    .value-password { color: #ff2d3a; font-family: monospace; }
    .raw-json {
        background: rgba(0,0,0,.4);
        border: 1px solid rgba(255,255,255,.06);
        border-radius: 8px;
        padding: 16px;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 12px;
        color: #d4d4d4;
        white-space: pre-wrap;
        overflow-x: auto;
        max-height: 400px;
        overflow-y: auto;
    }
    .empty { color: #666; text-align: center; padding: 20px; }
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 12px;
        margin-top: 12px;
    }
    .stat-item {
        background: rgba(255,255,255,.03);
        border: 1px solid rgba(255,255,255,.06);
        border-radius: 10px;
        padding: 12px 16px;
        text-align: center;
    }
    .stat-number { font-size: 24px; font-weight: 700; color: #ff6b6b; }
    .stat-label { font-size: 12px; color: #8888aa; margin-top: 4px; }
    @media (max-width: 600px) {
        .kv-grid { grid-template-columns: 1fr; gap: 4px; }
        .kv-key { font-weight: 600; }
    }
    </style>
    """

    html = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Отчёт DarkOsint</title>
        {css}
    </head>
    <body>
    <div class="container">
        <div class="header">
            <h1>🔍 DarkOsint Отчёт</h1>
            <div class="meta">
                Тип: {TYPE_NAMES.get(search_type, search_type)} &bull; 
                Запрос: {query} &bull; 
                Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </div>
        </div>
    """

    if phone_report:
        html += f"""
        <div class="glass">
            <div class="card-header">📱 Информация по номеру</div>
            <div class="card-body">
                <div class="kv-grid">
                    <div class="kv-key">Номер</div>
                    <div class="kv-val value-phone">{phone_report.get('phone', '')}</div>
                    <div class="kv-key">Оператор</div>
                    <div class="kv-val">{phone_report.get('operator', 'Не найден')}</div>
                    <div class="kv-key">Регион</div>
                    <div class="kv-val">{phone_report.get('region', 'Не найден')}</div>
                </div>
        """
        
        if phone_report.get('personal'):
            html += '<div style="margin-top:16px;"><strong style="color:#ff6b6b;">👤 Личные данные</strong><ul style="list-style:none;padding:0;margin-top:8px;">'
            for item in phone_report['personal'][:20]:
                html += f'<li style="padding:6px 0;border-bottom:1px solid rgba(255,255,255,.04);">• {item}</li>'
            if len(phone_report['personal']) > 20:
                html += f'<li style="color:#666;padding:6px 0;">... и ещё {len(phone_report["personal"])-20} записей</li>'
            html += '</ul></div>'
        
        if phone_report.get('social'):
            html += '<div style="margin-top:16px;"><strong style="color:#ff6b6b;">🌐 Социальные сети</strong><div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;">'
            for item in phone_report['social'][:15]:
                html += f'<span class="chip">{item}</span>'
            if len(phone_report['social']) > 15:
                html += f'<span class="chip">... и ещё {len(phone_report["social"])-15}</span>'
            html += '</div></div>'
        
        if phone_report.get('phonebook'):
            html += '<div style="margin-top:16px;"><strong style="color:#ff6b6b;">📖 Телефонная книга</strong><div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;">'
            for name in phone_report['phonebook'][:30]:
                html += f'<span class="chip">{name}</span>'
            if len(phone_report['phonebook']) > 30:
                html += f'<span class="chip">... и ещё {len(phone_report["phonebook"])-30}</span>'
            html += '</div></div>'
        
        if phone_report.get('banks'):
            html += '<div style="margin-top:16px;"><strong style="color:#ff6b6b;">🏦 Банки</strong><div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;">'
            for bank in phone_report['banks'][:10]:
                html += f'<span class="chip">{bank}</span>'
            if len(phone_report['banks']) > 10:
                html += f'<span class="chip">... и ещё {len(phone_report["banks"])-10}</span>'
            html += '</div></div>'
        
        html += f"""
                <div style="margin-top:18px;padding-top:16px;border-top:1px solid rgba(255,255,255,.06);">
                    <div class="stats-grid">
                        <div class="stat-item"><div class="stat-number">{phone_report.get('total_records', 0)}</div><div class="stat-label">Всего записей</div></div>
                        <div class="stat-item"><div class="stat-number">{len(phone_report.get('personal', []))}</div><div class="stat-label">Личных данных</div></div>
                        <div class="stat-item"><div class="stat-number">{len(phone_report.get('phonebook', []))}</div><div class="stat-label">Контактов</div></div>
                        <div class="stat-item"><div class="stat-number">{len(phone_report.get('social', []))}</div><div class="stat-label">Соц. сетей</div></div>
                    </div>
                </div>
            </div>
        </div>
        """

    html += '<div class="glass"><div class="card-header">🌐 Данные от API</div><div class="card-body">'
    
    for api_name, api_result in results.items():
        data = api_result.get('data')
        status = api_result.get('status', 'error')
        
        status_badge = {
            'success': 'badge-success',
            'error': 'badge-error',
            'timeout': 'badge-timeout'
        }.get(status, 'badge-error')
        
        status_text = {
            'success': '✔ Успешно',
            'error': '✘ Ошибка',
            'timeout': '⏱ Таймаут'
        }.get(status, status)
        
        html += f"""
        <div class="section">
            <div class="section-title">
                📡 {api_name} <span class="badge {status_badge}">{status_text}</span>
            </div>
            <div class="section-body">
        """
        
        if data:
            if isinstance(data, dict):
                if "results" in data and isinstance(data["results"], list):
                    for idx, item in enumerate(data["results"][:50]):
                        html += f'<div style="margin-bottom:12px;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.04);">'
                        html += f'<div style="color:#888;font-size:12px;margin-bottom:4px;">#{idx+1}</div>'
                        if isinstance(item, dict):
                            html += '<div class="kv-grid">'
                            for k, v in item.items():
                                if not k.startswith('_'):
                                    html += f'<div class="kv-key">{k}</div><div class="kv-val">{str(v)[:300]}</div>'
                            html += '</div>'
                        else:
                            html += f'<div class="kv-val">{str(item)[:300]}</div>'
                        html += '</div>'
                    if len(data["results"]) > 50:
                        html += f'<div style="color:#666;text-align:center;padding:8px;">... и ещё {len(data["results"])-50} записей</div>'
                else:
                    html += '<div class="kv-grid">'
                    for k, v in data.items():
                        if not k.startswith('_'):
                            html += f'<div class="kv-key">{k}</div><div class="kv-val">{str(v)[:500]}</div>'
                    html += '</div>'
            elif isinstance(data, list):
                for idx, item in enumerate(data[:50]):
                    html += f'<div style="margin-bottom:8px;padding:6px 0;border-bottom:1px solid rgba(255,255,255,.04);">'
                    html += f'<div style="color:#888;font-size:12px;">#{idx+1}</div>'
                    if isinstance(item, dict):
                        parts = []
                        for k, v in item.items():
                            if not k.startswith('_'):
                                parts.append(f"{k}: {str(v)[:150]}")
                        html += ' | '.join(parts)
                    else:
                        html += str(item)[:300]
                    html += '</div>'
                if len(data) > 50:
                    html += f'<div style="color:#666;text-align:center;padding:8px;">... и ещё {len(data)-50} записей</div>'
            else:
                html += f'<pre class="raw-json">{json.dumps(data, indent=2, ensure_ascii=False)[:3000]}</pre>'
        else:
            html += '<div class="empty">Нет данных</div>'
        
        html += '</div></div>'
    
    html += '</div></div></div></body></html>'
    return html

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
async def safe_send_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup=None):
    if not text:
        return
    MAX_LEN = 4096
    try:
        if len(text) <= MAX_LEN:
            await update.message.reply_text(text, reply_markup=reply_markup)
        else:
            parts = [text[i:i+MAX_LEN] for i in range(0, len(text), MAX_LEN)]
            for part in parts:
                await update.message.reply_text(part, reply_markup=reply_markup)
    except Forbidden:
        logger.warning("Пользователь заблокировал бота, сообщение не отправлено.")

async def safe_edit_message(update: Update, text: str, reply_markup=None):
    try:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    except Forbidden:
        logger.warning("Пользователь заблокировал бота, редактирование невозможно.")
    except Exception as e:
        logger.error(f"Edit error: {e}")

async def safe_delete_message(message):
    try:
        await message.delete()
    except Exception:
        pass

# ==================== ПРОВЕРКА ПОДПИСКИ ====================
async def is_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Ошибка проверки подписки: {e}")
        return False

async def require_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if user is None:
        return False
    if await is_subscribed(user.id, context):
        return True
    else:
        text = "❗ Для использования бота необходимо подписаться на наш канал.\n\nПодпишитесь на канал: https://t.me/+JtmagBAdAZY2MzQ6\n\nПосле подписки нажмите кнопку «Проверить подписку»."
        keyboard = [[InlineKeyboardButton("✅ Проверить подписку", callback_data="check_sub")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if update.callback_query:
            await update.callback_query.answer()
            await safe_edit_message(update, text, reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
        return False

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    if await is_subscribed(user.id, context):
        await safe_edit_message(
            update,
            "✅ Подписка подтверждена! Теперь вы можете использовать бота.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]])
        )
    else:
        await safe_edit_message(
            update,
            "❌ Вы всё ещё не подписаны. Пожалуйста, подпишитесь и нажмите кнопку снова.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Проверить подписку", callback_data="check_sub")]])
        )

# ==================== ОСНОВНЫЕ ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        arg = context.args[0]
        if arg.startswith("ref_"):
            ref_code = arg[4:]
            context.user_data['ref_code'] = ref_code

    if not await require_subscription(update, context):
        return
    user = update.effective_user
    uid = user.id
    user_data = await get_user(uid, user.username)

    ref_code = context.user_data.pop('ref_code', None)
    if ref_code:
        referrer_id = None
        async with _user_lock:
            for u_id, data in _user_data.items():
                if data.get("referral_code") == ref_code:
                    referrer_id = int(u_id)
                    break
        if referrer_id and referrer_id != uid:
            if user_data.get("referred_by") is None:
                referrer_data = await get_user(referrer_id)
                await update_user(referrer_id, {"bonus_requests": referrer_data.get("bonus_requests", 0) + 1})
                await update_user(referrer_id, {"referral_count": referrer_data.get("referral_count", 0) + 1})
                await update_user(uid, {"bonus_requests": user_data.get("bonus_requests", 0) + 1})
                await update_user(uid, {"referred_by": referrer_id})
                try:
                    await context.bot.send_message(chat_id=referrer_id, text=f"🎉 По вашей реферальной ссылке зарегистрировался новый пользователь! Вы получили +1 бонусный запрос.")
                except:
                    pass
                await update.message.reply_text("🎁 Вы активировали реферальную ссылку! Вам начислен 1 бонусный запрос.")
            else:
                await update.message.reply_text("Вы уже были приглашены ранее.")
        else:
            if referrer_id == uid:
                await update.message.reply_text("Вы не можете активировать свою собственную реферальную ссылку.")
            else:
                await update.message.reply_text("❌ Неверный реферальный код.")

    hour = datetime.now().hour
    if 6 <= hour < 18:
        greet = "🌞 Добрый день"
    else:
        greet = "🌙 Добрый вечер/ночь"
    text = f"{greet}, {user.first_name}!\n\nЯ бот для поиска информации по открытым источникам (DarkOsint).\n"
    uid = user.id
    await reset_daily_limit(uid)
    if is_admin(user):
        text += "👑 Вы администратор — доступ безлимитный и полная выдача.\n"
    elif await is_pro(uid):
        until = (await get_user(uid)).get("pro_until", "неизвестно")
        text += f"💎 У вас PRO-доступ (безлимит) до {until}.\n"
    else:
        text += "🔹 У вас обычный доступ (2 запроса в день).\n"
    bonus = (await get_user(uid)).get("bonus_requests", 0)
    if bonus:
        text += f"🎁 Бонусных запросов: {bonus}\n"
    text += "\nИспользуйте кнопки ниже для навигации:"
    keyboard = [
        [InlineKeyboardButton("🔍 Поиск", callback_data="search")],
        [InlineKeyboardButton("📖 Инструкция", callback_data="instruction")],
        [InlineKeyboardButton("🛒 Магазин", callback_data="shop")],
        [InlineKeyboardButton("🎫 Ввести промокод", callback_data="enter_promo")],
        [InlineKeyboardButton("🔗 Реферальная ссылка", callback_data="referral")],
    ]
    if is_admin(user):
        keyboard.append([InlineKeyboardButton("👑 Админ-панель", callback_data="admin_panel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    try:
        await update.message.reply_text(text, reply_markup=reply_markup)
    except Forbidden:
        logger.warning("Пользователь заблокировал бота, приветствие не отправлено.")

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_subscription(update, context):
        return
    query = update.callback_query
    await query.answer()
    user = query.from_user
    await get_user(user.id, user.username)
    hour = datetime.now().hour
    if 6 <= hour < 18:
        greet = "🌞 Добрый день"
    else:
        greet = "🌙 Добрый вечер/ночь"
    text = f"{greet}, {user.first_name}!\n\nЯ бот для поиска информации по открытым источникам (DarkOsint).\n"
    uid = user.id
    await reset_daily_limit(uid)
    if is_admin(user):
        text += "👑 Вы администратор — доступ безлимитный и полная выдача.\n"
    elif await is_pro(uid):
        until = (await get_user(uid)).get("pro_until", "неизвестно")
        text += f"💎 У вас PRO-доступ (безлимит) до {until}.\n"
    else:
        text += "🔹 У вас обычный доступ (2 запроса в день).\n"
    bonus = (await get_user(uid)).get("bonus_requests", 0)
    if bonus:
        text += f"🎁 Бонусных запросов: {bonus}\n"
    text += "\nИспользуйте кнопки ниже для навигации:"
    keyboard = [
        [InlineKeyboardButton("🔍 Поиск", callback_data="search")],
        [InlineKeyboardButton("📖 Инструкция", callback_data="instruction")],
        [InlineKeyboardButton("🛒 Магазин", callback_data="shop")],
        [InlineKeyboardButton("🎫 Ввести промокод", callback_data="enter_promo")],
        [InlineKeyboardButton("🔗 Реферальная ссылка", callback_data="referral")],
    ]
    if is_admin(user):
        keyboard.append([InlineKeyboardButton("👑 Админ-панель", callback_data="admin_panel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await safe_edit_message(update, text, reply_markup)

async def instruction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_subscription(update, context):
        return
    text = "📖 ИНСТРУКЦИЯ\n\nБот выполняет поиск по номеру по русским базам."
    keyboard = [[InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]]
    await safe_edit_message(update, text, InlineKeyboardMarkup(keyboard))


async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_subscription(update, context):
        return
    user = update.effective_user
    uid = user.id
    user_data = await get_user(uid, user.username)
    ref_code = user_data.get("referral_code")
    if not ref_code:
        ref_code = generate_referral_code(uid)
        await update_user(uid, {"referral_code": ref_code})
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start=ref_{ref_code}"
    text = f"🔗 Ваша реферальная ссылка:\n\n{link}\n\nЗа каждого приглашённого пользователя вы получаете +1 бонусный запрос, и новый пользователь также получает +1 бонусный запрос.\n\nКоличество приведённых пользователей: {user_data.get('referral_count', 0)}"
    keyboard = [[InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]]
    if update.callback_query:
        await safe_edit_message(update, text, InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== ПОИСК ====================
async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_subscription(update, context):
        return
    query = update.callback_query
    await query.answer()
    user = query.from_user
    await get_user(user.id, user.username)
    await reset_daily_limit(user.id)
    if not is_admin(user):
        can, msg = await can_search(user.id)
        if not can:
            await safe_edit_message(update, f"❌ {msg}\nВернуться в меню — /start")
            return
    context.user_data['search_mode'] = True
    keyboard = [
        [InlineKeyboardButton(TYPE_NAMES["phone"], callback_data="stype_1")],
        [InlineKeyboardButton(TYPE_NAMES["ip"], callback_data="stype_5")],
        [InlineKeyboardButton(TYPE_NAMES["vk"], callback_data="stype_6")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await safe_edit_message(update, "🔍 Выберите тип данных для поиска:", reply_markup)

async def select_search_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data.split('_')[1]
    search_type = SEARCH_TYPES[choice]
    type_name = TYPE_NAMES[search_type]
    example = TYPE_EXAMPLES[search_type]
    context.user_data['search_type'] = search_type
    text = f"Вы выбрали: {type_name}\nВведите значение для поиска (например: {example}):\n\n(Чтобы отменить, отправьте /cancel)"
    await safe_edit_message(update, text)
    context.user_data['awaiting_query'] = True

async def handle_search_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_subscription(update, context):
        return
    if not context.user_data.get('awaiting_query'):
        return
    user = update.effective_user
    await get_user(user.id, user.username)
    query_text = update.message.text.strip()
    if not query_text:
        await update.message.reply_text("❌ Запрос не может быть пустым. Введите ещё раз.")
        return
    search_type = context.user_data.get('search_type')
    if not search_type:
        await update.message.reply_text("❌ Ошибка: не выбран тип. Начните заново /start.")
        context.user_data['awaiting_query'] = False
        return

    if not is_admin(user):
        await reset_daily_limit(user.id)
        if await is_pro(user.id):
            pass
        else:
            can, msg = await can_search(user.id)
            if not can:
                await update.message.reply_text(f"❌ {msg}\nВернуться в меню — /start")
                context.user_data['awaiting_query'] = False
                return
            user_data = await get_user(user.id)
            daily_limit = 2
            used = user_data["requests_today"]
            bonus = user_data.get("bonus_requests", 0)
            if used < daily_limit:
                await update_user(user.id, {"requests_today": used + 1})
            elif bonus > 0:
                await update_user(user.id, {"bonus_requests": bonus - 1})
            else:
                await update.message.reply_text("❌ Недостаточно запросов.")
                context.user_data['awaiting_query'] = False
                return

    progress_msg = await update.message.reply_text("⏳ Выполняется поиск по всем API... Пожалуйста, подождите.")
    try:
        # Если тип поиска VK - используем отдельный метод
        if search_type == "vk":
            # Запускаем синхронную функцию в отдельном потоке
            result = await asyncio.to_thread(vk_get_user_sync, query_text)
            if "error" in result:
                await safe_delete_message(progress_msg)
                await update.message.reply_text(f"❌ Ошибка: {result['error']}\nВернуться в меню — /start")
                context.user_data['awaiting_query'] = False
                return
            # Формируем красивый отчет
            lines = []
            lines.append("👤 ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ VK")
            lines.append("=" * 50)
            for key, value in result.items():
                if value and value != "None" and value != "Не указана" and value != "Не указан":
                    lines.append(f"{key}: {value}")
            report_text = "\n".join(lines)
            context.user_data['last_query'] = query_text
            context.user_data['last_search_type'] = search_type
            context.user_data['last_raw_results'] = {"vk_result": result}
            keyboard = [[InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await safe_delete_message(progress_msg)
            await safe_send_message(update, context, report_text, reply_markup)
            context.user_data['awaiting_query'] = False
            return

        # Для остальных типов (phone, ip) используем стандартный поиск
        results = await search_all_apis(query_text, search_type, user.id)

        context.user_data['last_query'] = query_text
        context.user_data['last_search_type'] = search_type
        context.user_data['last_raw_results'] = results

        if search_type == "phone":
            phone_report = parse_phone_data(results, query_text)
            report_text = format_phone_report(phone_report)
            context.user_data['last_phone_report'] = phone_report
            context.user_data['last_raw_results'] = results

            keyboard = [
                [InlineKeyboardButton("📄 Скачать полный отчёт", callback_data="download_report")],
                [InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await safe_delete_message(progress_msg)
            await safe_send_message(update, context, report_text, reply_markup)
        else:
            report = build_report_text(query_text, search_type, results)
            if is_admin(user):
                report += "\n\n👑 Админский доступ — безлимит"
            elif await is_pro(user.id):
                report += "\n\n💎 PRO-доступ — безлимит"
            else:
                user_data = await get_user(user.id)
                used = user_data["requests_today"]
                bonus = user_data.get("bonus_requests", 0)
                report += f"\n\n📊 Использовано запросов сегодня: {used} из 2\n🎁 Бонусных осталось: {bonus}"

            keyboard = [[InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            context.user_data['last_results'] = {
                "query": query_text,
                "search_type": search_type,
                "results": results,
            }
            await safe_delete_message(progress_msg)
            await safe_send_message(update, context, report, reply_markup)
    except Exception as e:
        logger.error(f"Search error: {e}")
        try:
            await progress_msg.edit_text(f"❌ Ошибка при поиске: {e}")
        except:
            await update.message.reply_text(f"❌ Ошибка при поиске: {e}")
    finally:
        context.user_data['awaiting_query'] = False

# ==================== МАГАЗИН ====================
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_subscription(update, context):
        return
    query = update.callback_query
    await query.answer()
    user = query.from_user
    await get_user(user.id, user.username)
    uid = user.id
    if await is_pro(uid):
        until = (await get_user(uid)).get("pro_until", "неизвестно")
        text = f"💎 У вас уже есть PRO-доступ до {until}.\n\nСпасибо, что пользуетесь ботом!"
        keyboard = [[InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]]
        await safe_edit_message(update, text, InlineKeyboardMarkup(keyboard))
        return
    text = "🛒 МАГАЗИН PRO-ДОСТУПА\n\n"
    text += "💎 PRO-доступ даёт:\n"
    text += "• Безлимит запросов в день\n"
    text += "• Полный вывод данных (все записи)\n"
    text += "• Приоритетная поддержка\n\n"
    text += "💰 Стоимость: 250 звёзд (скидка!)\n"
    text += "Для получения PRO нажмите кнопку ниже. С вами свяжется модератор."
    keyboard = [
        [InlineKeyboardButton("💎 Купить PRO", callback_data="buy_pro")],
        [InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]
    ]
    await safe_edit_message(update, text, InlineKeyboardMarkup(keyboard))

async def buy_pro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_subscription(update, context):
        return
    query = update.callback_query
    await query.answer()
    user = query.from_user
    await get_user(user.id, user.username)
    uid = user.id
    if await is_pro(uid):
        await safe_edit_message(update, "У вас уже есть PRO-доступ.", InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]]))
        return
    text_admin = f"📩 Новая заявка на PRO\n"
    text_admin += f"👤 Username: @{user.username if user.username else 'нет'}\n"
    text_admin += f"🆔 User ID: {uid}\n"
    text_admin += f"💰 Цена: 250 звезд (скидка)\n"
    text_admin += f"📅 Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    text_admin += f"Чтобы выдать PRO, используйте админ-панель."
    try:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=text_admin)
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление админу: {e}")
    await safe_edit_message(update,
        "📩 Для получения PRO-доступа напишите @Bogvkkm.\n\n"
        "После оплаты вы получите безлимит навсегда (или на указанный срок).\n\n"
        "Вернуться в меню — /start",
        InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]])
    )

# ==================== ПРОМОКОДЫ ====================
async def enter_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_subscription(update, context):
        return
    query = update.callback_query
    await query.answer()
    await safe_edit_message(update,
        "🎫 Введите промокод (например, ABC12345):\n\n(Чтобы отменить, отправьте /cancel)"
    )
    context.user_data['awaiting_promo'] = True

async def handle_promo_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_promo'):
        return
    user = update.effective_user
    await get_user(user.id, user.username)
    code = update.message.text.strip()
    success, message = await activate_promo(user.id, code)
    await update.message.reply_text(message)
    context.user_data['awaiting_promo'] = False
    await start(update, context)

# ==================== СКАЧИВАНИЕ ОТЧЁТА ====================
async def download_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_subscription(update, context):
        return
    query = update.callback_query
    await query.answer()
    user = query.from_user
    await get_user(user.id, user.username)

    last_query = context.user_data.get('last_query')
    last_search_type = context.user_data.get('last_search_type')
    last_raw_results = context.user_data.get('last_raw_results')
    last_phone_report = context.user_data.get('last_phone_report')

    if not last_query or not last_raw_results:
        await query.edit_message_text("❌ Нет сохранённого отчёта. Сделайте новый поиск.")
        return

    html_content = generate_html_report(last_query, last_search_type, last_raw_results, last_phone_report)

    file_obj = io.BytesIO(html_content.encode('utf-8'))
    file_obj.name = f"report_{last_query[:20]}.html"

    await query.message.reply_document(
        document=file_obj,
        caption="📄 Полный отчёт в формате HTML",
        filename=file_obj.name
    )
    await query.edit_message_reply_markup(reply_markup=None)

    await query.message.reply_text(
        "Файл отправлен. Вернуться в меню:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]])
    )

# ==================== АДМИН-ПАНЕЛЬ ====================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_subscription(update, context):
        return
    query = update.callback_query
    await query.answer()
    user = query.from_user
    await get_user(user.id, user.username)
    if not is_admin(user):
        await safe_edit_message(update, "❌ Эта панель доступна только администратору.")
        return
    text = "👑 АДМИН-ПАНЕЛЬ\n\nВыберите действие:"
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("🎁 Выдать PRO", callback_data="admin_give_pro")],
        [InlineKeyboardButton("🔄 Сбросить лимиты всех", callback_data="admin_reset_all")],
        [InlineKeyboardButton("🎫 Сгенерировать промокод", callback_data="admin_gen_promo")],
        [InlineKeyboardButton("🔙 В меню", callback_data="back_to_menu")]
    ]
    await safe_edit_message(update, text, InlineKeyboardMarkup(keyboard))

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_subscription(update, context):
        return
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user):
        await safe_edit_message(update, "Доступ запрещён.")
        return
    
    async with _user_lock:
        if not _user_data:
            await safe_edit_message(update, "Нет данных о пользователях.")
            return
        
        text = "📊 СТАТИСТИКА ПОЛЬЗОВАТЕЛЕЙ\n\n"
        for uid, info in list(_user_data.items())[:20]:
            username = info.get("username", "неизвестно")
            pro = "✅" if info.get("pro") and info.get("pro_until") and datetime.fromisoformat(info["pro_until"]).date() >= date.today() else "❌"
            bonus = info.get("bonus_requests", 0)
            ref_count = info.get("referral_count", 0)
            text += f"👤 ID: {uid} (@{username})\n"
            text += f"   Запросов сегодня: {info.get('requests_today', 0)}\n"
            text += f"   Бонусных запросов: {bonus}\n"
            text += f"   PRO: {pro}\n"
            if info.get("pro_until"):
                text += f"   Действует до: {info['pro_until']}\n"
            text += f"   Приведено рефералов: {ref_count}\n"
            text += "\n"
        
        if len(_user_data) > 20:
            text += f"... и ещё {len(_user_data) - 20} пользователей.\n"
    
    MAX_LEN = 4096
    if len(text) > MAX_LEN:
        parts = [text[i:i+MAX_LEN] for i in range(0, len(text), MAX_LEN)]
        for part in parts:
            await query.message.reply_text(part)
        await query.edit_message_reply_markup(reply_markup=None)
    else:
        await safe_edit_message(update, text)

async def admin_give_pro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_subscription(update, context):
        return
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user):
        await safe_edit_message(update, "Доступ запрещён.")
        return
    await safe_edit_message(update,
        "Введите ID пользователя и срок действия (в днях) через пробел.\n"
        "Например: 123456789 30 — выдаст PRO на 30 дней.\n"
        "Чтобы отменить, отправьте /cancel."
    )
    context.user_data['admin_action'] = 'give_pro'

async def admin_gen_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_subscription(update, context):
        return
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user):
        await safe_edit_message(update, "Доступ запрещён.")
        return
    await safe_edit_message(update,
        "Введите два числа через пробел:\n"
        "1) Максимальное количество активаций (человек)\n"
        "2) Количество бонусных запросов для каждого\n\n"
        "Пример: 10 5 — промокод можно будет использовать 10 раз, каждый получит 5 бонусных запросов.\n"
        "Чтобы отменить, отправьте /cancel."
    )
    context.user_data['admin_action'] = 'generate_promo'

async def admin_handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('admin_action') == 'give_pro':
        user = update.effective_user
        await get_user(user.id, user.username)
        if not is_admin(user):
            await update.message.reply_text("Нет прав.")
            return
        parts = update.message.text.strip().split()
        if len(parts) != 2:
            await update.message.reply_text("Некорректный ввод. Введите ID и количество дней через пробел.")
            return
        try:
            target_id = int(parts[0])
            days = int(parts[1])
            if days <= 0:
                await update.message.reply_text("Количество дней должно быть положительным.")
                return
        except ValueError:
            await update.message.reply_text("Ошибка: ID и дни должны быть числами.")
            return
        until_date = date.today() + timedelta(days=days)
        await update_user(target_id, {"pro": True, "pro_until": until_date.isoformat()})
        await update.message.reply_text(f"✅ Пользователю с ID {target_id} выдан PRO до {until_date.isoformat()}.")
        context.user_data['admin_action'] = None
        try:
            await context.bot.send_message(chat_id=target_id, text=f"🎉 Вам выдан PRO-доступ до {until_date.isoformat()}!")
        except:
            pass
        return

    elif context.user_data.get('admin_action') == 'generate_promo':
        user = update.effective_user
        await get_user(user.id, user.username)
        if not is_admin(user):
            await update.message.reply_text("Нет прав.")
            return
        parts = update.message.text.strip().split()
        if len(parts) != 2:
            await update.message.reply_text("Некорректный ввод. Введите два числа через пробел.")
            return
        try:
            max_activations = int(parts[0])
            bonus_queries = int(parts[1])
            if max_activations <= 0 or bonus_queries <= 0:
                await update.message.reply_text("Оба числа должны быть положительными.")
                return
        except ValueError:
            await update.message.reply_text("Ошибка: нужно ввести числа.")
            return

        global _promo_codes
        async with _promo_lock:
            while True:
                code = generate_promo_code()
                if code not in _promo_codes:
                    break
            _promo_codes[code] = {
                "max_activations": max_activations,
                "used_activations": 0,
                "bonus_queries": bonus_queries,
                "used_by": []
            }
        await update.message.reply_text(
            f"✅ Промокод сгенерирован!\n\n"
            f"🎫 Код: `{code}`\n"
            f"👥 Максимум активаций: {max_activations}\n"
            f"🎁 Бонусных запросов на активацию: {bonus_queries}\n\n"
            f"Поделитесь этим кодом с пользователями."
        )
        context.user_data['admin_action'] = None
        return
    else:
        pass

async def admin_reset_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_subscription(update, context):
        return
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user):
        await safe_edit_message(update, "Доступ запрещён.")
        return
    
    async with _user_lock:
        for uid in _user_data:
            _user_data[uid]["requests_today"] = 0
            _user_data[uid]["last_request_date"] = date.today().isoformat()
    
    await safe_edit_message(update, "✅ Все лимиты сброшены на сегодня.")

# ==================== ЕДИНЫЙ ОБРАБОТЧИК ТЕКСТА ====================
async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_subscription(update, context):
        return
    if context.user_data.get('awaiting_query'):
        await handle_search_query(update, context)
    elif context.user_data.get('awaiting_promo'):
        await handle_promo_input(update, context)
    elif context.user_data.get('admin_action'):
        await admin_handle_input(update, context)
    else:
        await update.message.reply_text("Используйте кнопки для навигации или /start")

# ==================== ОБЩИЙ ОБРАБОТЧИК CALLBACK ====================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    if data == "back_to_menu":
        await main_menu(update, context)
    elif data == "search":
        await search_start(update, context)
    elif data.startswith("stype_"):
        await select_search_type(update, context)
    elif data == "shop":
        await shop(update, context)
    elif data == "buy_pro":
        await buy_pro(update, context)
    elif data == "enter_promo":
        await enter_promo(update, context)
    elif data == "download_report":
        await download_report(update, context)
    elif data == "admin_panel":
        await admin_panel(update, context)
    elif data == "admin_stats":
        await admin_stats(update, context)
    elif data == "admin_give_pro":
        await admin_give_pro(update, context)
    elif data == "admin_gen_promo":
        await admin_gen_promo(update, context)
    elif data == "admin_reset_all":
        await admin_reset_all(update, context)
    elif data == "check_sub":
        await check_subscription(update, context)
    elif data == "referral":
        await referral_command(update, context)
    elif data == "instruction":
        await instruction(update, context)
    else:
        await update.callback_query.answer("Неизвестная команда")

# ==================== MAIN ====================
async def shutdown():
    await close_client_session()
    async with _cache_lock:
        _api_cache.clear()

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('cancel', lambda u,c: u.message.reply_text("Отменено.")))
    application.add_handler(CommandHandler('referral', referral_command))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    import atexit
    atexit.register(lambda: asyncio.run(shutdown()))
    
    logger.info("🚀 Бот запущен! Данные хранятся ТОЛЬКО в ОЗУ, файлы НЕ создаются!")
    logger.info(f"📊 В памяти: {len(_user_data)} пользователей, {len(_promo_codes)} промокодов")
    logger.info("⚡ Оптимизирован для высокой нагрузки: кэширование, семафоры, пул соединений")
    logger.info("📝 Показывается максимальное количество информации")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()