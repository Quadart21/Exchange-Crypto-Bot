import json
import base64
import hashlib
import requests

from config import HELEKET_API_URL, HELEKET_API_KEY, HELEKET_MERCHANT_ID


import logging


def get_invoice_status(uuid: str) -> dict:
    """Проверка статуса по UUID"""
    url = "https://api.heleket.com/v1/payment/info"
    data = {"uuid": uuid}
    json_data = json.dumps(data, separators=(',', ':'))  # строго такой же JSON как для подписи
    sign = generate_sign(data)

    headers = {
        "merchant": HELEKET_MERCHANT_ID,
        "sign": sign,
        "Content-Type": "application/json"
    }

    logging.debug("📤 UUID: %s", uuid)
    logging.debug("📤 JSON data: %s", json_data)
    logging.debug("📤 Sign: %s", sign)
    logging.debug("📤 Headers: %s", headers)

    response = requests.post(url, headers=headers, data=json_data)  # <== ВАЖНО: data, НЕ json
    logging.debug("📥 Response: %s %s", response.status_code, response.text)
    return response.json()



def get_payout_services_full() -> list:
    url = HELEKET_API_URL.replace('/payment', '/payout/services')
    headers = {
        "merchant": HELEKET_MERCHANT_ID,
        "sign": generate_sign({}),
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(url, headers=headers, json={})
        data = response.json()
        if data.get("state") != 0:
            return []
        return data.get("result", [])
    except Exception as e:
        print(f"[ERROR] get_payout_services_full: {e}")
        return []


def get_exchange_rate_heleket(token: str, markup: float) -> float:
    """Получить курс токена через Heleket и применить наценку"""
    try:
        response = requests.get(f"https://api.heleket.com/v1/exchange-rate/{token}/list", timeout=5)
        data = response.json()

        if data.get("state") != 0:
            return None

        usd_rate = None
        for item in data.get("result", []):
            if item["to"] == "USD":
                usd_rate = float(item["course"])
                break

        if usd_rate is None:
            return None

        final_rate = usd_rate * (1 + markup / 100)
        return final_rate

    except Exception as e:
        print(f"[EXCEPTION] Ошибка запроса курса Heleket: {e}")
        return None

def get_exchange_rate_heleket_reversed(token: str) -> float:
    """Получает обратный курс токена к USDT через Heleket API"""
    try:
        url = f"https://api.heleket.com/v1/exchange-rate/USDT/list"
        response = requests.get(url, timeout=5)
        data = response.json()

        if data.get("state") != 0:
            return None

        for item in data.get("result", []):
            if item["to"].upper() == token.upper():
                course = float(item["course"])
                if course > 0:
                    return 1 / course  # Инвертируем курс: сколько USDT за 1 токен

        return None

    except Exception as e:
        print(f"[EXCEPTION] Ошибка в get_exchange_rate_heleket_reversed: {e}")
        return None

def get_exchange_rate_heleket_ask(token: str) -> float:
    try:
        url = f"https://api.heleket.com/v1/exchange-rate/{token}/list"
        response = requests.get(url)
        data = response.json()
        for item in data.get("result", []):
            if item["to"] == "USDT":
                return float(item["course"])
    except Exception as e:
        print(f"[ERROR] get_exchange_rate_heleket_ask: {e}")
    return 0.0

def generate_sign(data: dict) -> str:
    """Генерация подписи"""
    json_data = json.dumps(data, separators=(',', ':'))  # строго без пробелов
    sign_raw = base64.b64encode(json_data.encode()).decode() + HELEKET_API_KEY
    return hashlib.md5(sign_raw.encode()).hexdigest()

def create_invoice(amount: float, currency: str, order_id: str, to_currency: str = None, network: str = None, url_callback: str = None) -> dict:
    """Создание инвойса через Heleket"""
    data = {
        "amount": str(amount),
        "currency": currency,
        "order_id": order_id,
    }
    if to_currency:
        data["to_currency"] = to_currency
    if network:
        data["network"] = network
    if url_callback:
        data["url_callback"] = url_callback

    json_data = json.dumps(data, separators=(',', ':'))  # правильная подготовка JSON без пробелов
    sign = generate_sign(data)

    headers = {
        "merchant": HELEKET_MERCHANT_ID,
        "sign": sign,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(HELEKET_API_URL, headers=headers, data=json_data, timeout=5)  # именно data, не json!
        result = response.json()
        return result
    except Exception as e:
        from heleket_logger import logger
        logger.exception(f"Ошибка при запросе Heleket API: {e}")
        return {"state": 1, "message": "Connection error"}


def get_available_tokens_and_networks() -> list:
    """Запрашивает доступные токены и сети через Heleket API"""
    import requests
    from config import HELEKET_API_URL, HELEKET_MERCHANT_ID, HELEKET_API_KEY

    url = HELEKET_API_URL.replace('/payment', '/payment/services')  # Формируем URL для списка сервисов
    headers = {
        "merchant": HELEKET_MERCHANT_ID,
        "sign": generate_sign({}),
        "Content-Type": "application/json"
    }
    response = requests.post(url, headers=headers, json={})
    services = response.json()

    result = {}
    if services.get("state") == 0:
        for item in services["result"]:
            currency = item["currency"]
            network = item["network"]
            if item["is_available"]:
                if currency not in result:
                    result[currency] = []
                result[currency].append(network)
    return result  # {'USDT': ['TRC20', 'ERC20'], 'BTC': ['BTC'], ...}


def verify_webhook(data: dict) -> bool:
    received_sign = data.get('sign')
    temp = data.copy()
    temp.pop('sign', None)

    json_data = json.dumps(temp, separators=(',', ':'))
    base64_data = base64.b64encode(json_data.encode()).decode()
    expected_sign = hashlib.md5((base64_data + HELEKET_API_KEY).encode()).hexdigest()

    return expected_sign == received_sign
