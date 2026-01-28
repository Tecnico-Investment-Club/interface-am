from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestTradeRequest
from .base import BrokerBase

class AlpacaBroker(BrokerBase):
    def __init__(self, api_key: str, secret_key: str, paper: bool = True):
        self.trading_client = TradingClient(api_key, secret_key, paper=paper)
        self.data_client = StockHistoricalDataClient(api_key, secret_key)

    def get_balance(self):
        account = self.trading_client.get_account()
        return float(account.cash)

    def place_order(self, symbol: str, qty: float, side: str):
        order_side = OrderSide.BUY if side.lower() == "compra" else OrderSide.SELL
        order_request = MarketOrderRequest(
            symbol=symbol,
            qty=qty,
            side=order_side,
            time_in_force=TimeInForce.DAY
        )
        return self.trading_client.submit_order(order_data=order_request)

    def get_positions(self):
        return self.trading_client.get_all_positions()

    def get_price(self, symbol: str):
        request_params = StockLatestTradeRequest(symbol_or_symbols=symbol)
        trades = self.data_client.get_stock_latest_trade(request_params)
        return trades[symbol].price

    def get_position_qty(self, symbol: str):
        """Tenta buscar a posição. Se der erro (404), significa que não temos nada."""
        try:
            pos = self.trading_client.get_open_position(symbol)
            return float(pos.qty)
        except:
            return 0.0