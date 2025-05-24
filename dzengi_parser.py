import requests
import logging

class DzengiRatesClient:
    BASE_URL = "https://api-adapter.dzengi.com"

    def __init__(self, api_key: str = '', secret_key: str = ''):
        self.api_key = api_key
        self.secret_key = secret_key

    def get_usd_byn_bid(self) -> float:
        """
        Получает актуальный bidPrice по паре USD/BYN с Dzengi.
        """
        try:
            url = f"{self.BASE_URL}/api/v1/ticker/24hr"
            params = {"symbol": "USD/BYN"}
            response = requests.get(url, params=params, timeout=5)

            if not response.ok:
                raise Exception(f"[DZENGI] Ошибка API: {response.status_code} - {response.text}")

            data = response.json()
            bid = float(data["bidPrice"])
            ask = float(data["askPrice"])

            logging.info(f"[DZENGI] USD/BYN → bid: {bid}, ask: {ask}")
            return bid

        except Exception as e:
            logging.exception(f"[DZENGI] Ошибка получения курса USD/BYN: {e}")
            return 0.0
