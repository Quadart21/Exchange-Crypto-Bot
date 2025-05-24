import json
import base64
import hashlib
import requests

HELEKET_MERCHANT_ID = "f62d2ac5-addd-4d28-8ac9-c7ebe89d6ef3"
HELEKET_API_KEY = "75ccYNzG0DDsSGxm7qLSjsZyjYZXSXGv0IYSwf7bkssEsnODg9EchjKMa7qH3kEACxFjhGAKbgFT6XCE6vjgdw5iCH1XfVybChIZ5Xcf5KLqsPc2Vp4Vo9uaGtbgMLxX"

def generate_sign(data: dict) -> str:
    payload = json.dumps(data, separators=(",", ":"))
    b64 = base64.b64encode(payload.encode()).decode()
    raw = b64 + HELEKET_API_KEY
    sign = hashlib.md5(raw.encode()).hexdigest()

    # Отладка
    print("Payload:", payload)
    print("Base64:", b64)
    print("Raw для MD5:", raw)
    print("Sign:", sign)

    return sign

def check_payment_status(order_id: str):
    url = "https://api.heleket.com/v1/payment/info"
    data = {"order_id": order_id}
    sign = generate_sign(data)

    headers = {
        "merchant": HELEKET_MERCHANT_ID,
        "sign": sign
    }

    response = requests.post(url, json=data, headers=headers)
    print("Ответ API:", response.status_code)
    print(json.dumps(response.json(), indent=2))

# Тест
check_payment_status("4e189ffe-ff7c-4952-a1d6-dcd76e513c02")
