import requests
from decimal import Decimal, getcontext
import time

getcontext().prec = 18

class Adv:
    def __init__(self, tradable_quantity, price):
        self.tradable_quantity = Decimal(tradable_quantity)
        self.price = Decimal(price)

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

class BinanceP2PParser:
    URL = 'https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search'
    PAGE_SIZE = 10

    def __init__(self, asset='USDT', fiat='RUB', markup_percent=0):
        self.asset = asset
        self.fiat = fiat
        self.markup_percent = Decimal(markup_percent)
        self.pay_types = []
        self.order_position = 0
        self.order_range = 5
        self.spot_api = BinanceAPI()

    def fetch_ads(self, trade_type, page=1):
        payload = {
            'asset': self.asset,
            'fiat': self.fiat,
            'tradeType': trade_type,
            'payTypes': self.pay_types,
            'page': page,
            'rows': self.PAGE_SIZE,
            'classifies': ['mass', 'profession', 'fiat_trade'],
            'proMerchantAds': False,
            'shieldMerchantAds': False,
            'additionalKycVerifyFilter': 0,
            'filterType': 'all',
        }
        try:
            response = requests.post(self.URL, json=payload, timeout=5)
            response.raise_for_status()
            data = response.json()
            if not data.get('success', False) or 'data' not in data:
                return []
            return [Adv(i['adv']['tradableQuantity'], i['adv']['price']) for i in data['data']]
        except Exception as e:
            print(f'Ошибка запроса к Binance P2P: {e}')
            return []

    def average_price(self, ads):
        subset = ads[self.order_position:self.order_position + self.order_range]
        if not subset:
            return None

        total_qty = sum(adv.tradable_quantity for adv in subset)
        if total_qty == 0:
            return None

        weighted_sum = sum(adv.tradable_quantity * adv.price for adv in subset)
        base_price = weighted_sum / total_qty

        if self.markup_percent:
            base_price *= (1 + self.markup_percent / Decimal(100))

        return base_price.quantize(Decimal('0.00000001'))

    def get_rates(self):
        rates = {}
        for trade_type in ['BUY', 'SELL']:
            ads = self.fetch_ads(trade_type)
            time.sleep(0.3)

            if ads:
                avg = self.average_price(ads)
                if avg:
                    rates[trade_type] = float(avg)
            else:
                # Если нет данных в P2P, пробуем взять цену с SPOT Binance
                try:
                    symbol = f"{self.asset}USDT"  # например DASHUSDT
                    spot_price = self.spot_api.get_last_price(symbol)
                    if spot_price:
                        rates[trade_type] = float(spot_price)
                        print(f"[SPOT] Получен курс {symbol}: {spot_price}")
                except Exception as e:
                    print(f"[SPOT ERROR] Ошибка получения цены через SPOT: {e}")

        return rates
