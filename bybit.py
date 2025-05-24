import requests

class BinanceAPI:
    BASE_URL = "https://api.binance.com"

    def __init__(self):
        self.session = requests.Session()

    def get_last_price(self, symbol: str) -> float:
        endpoint = "/api/v3/ticker/price"
        params = {"symbol": symbol.upper()}
        response = self.session.get(self.BASE_URL + endpoint, params=params)
        response.raise_for_status()
        data = response.json()
        return float(data['price'])

if __name__ == "__main__":
    api = BinanceAPI()
    symbol = "BTCUSDT"  # Пример
    try:
        price = api.get_last_price(symbol)
        print(f"Последняя цена {symbol}: {price}")
    except requests.RequestException as e:
        print(f"Ошибка запроса: {e}")
