from ib_async import *
import time
from .base import BrokerBase

class InteractiveBroker(BrokerBase):
    def __init__(self, paper: bool = True, client_id: int = 1, host: str = '127.0.0.1'):
        self.ib = IB()
        print(f"[*] Tentando conectar com clientId={client_id}...")
        try:
            self.ib.connect(host=host, port=4002, clientId=client_id)
            self.ib.sleep(0.5)  # Wait for connection to establish
            print(f"[✓] Conectado!")
        except Exception as e:
            print(f"[✗] Erro: {e}")
            raise

    def get_balance(self): #DONE #TODO talvez adicionar filtro de client ID
        """Obter saldo em BASE (agregado de todas as moedas)"""
        self.ib.sleep(0.5)
        summary = self.ib.accountSummary()

        for item in summary:
            if item.tag == "NetLiquidation":
                return float(item.value)
        return ValueError("Não foi possível obter o saldo da conta.")

    def get_account_summary(self): #DONE 
        self.ib.sleep(0.5)
        summary = self.ib.accountSummary()
        data = {
            "cash": 0.0,
            "equity": 0.0,
            "unrealized_pnl": 0.0
        }

        for item in summary:
            if item.tag == "NetLiquidation":
                data["equity"] = float(item.value)

            if item.tag == "CashBalance" and item.currency == "BASE":
                data["cash"] = float(item.value)

            if item.tag == "UnrealizedPnL":
                data["unrealized_pnl"] = float(item.value)

        return data

    def get_positions(self): #TODO talvez adicionar filtro de client ID
        """Obter resumo das posições do Portfólio"""
        self.ib.sleep(0.5)

        positions = self.ib.reqPositions()
        #print(positions)
        data = {}
        for stock in positions:
            data[stock.contract.symbol] = {}
            data[stock.contract.symbol]["symbol"] = stock.contract.symbol
            data[stock.contract.symbol]["quantity"] = stock.position
            data[stock.contract.symbol]["avg_price"] = stock.avgCost
        return data
    
    def get_price(self, symbol="AAPL"):

        self.ib.reqMarketDataType(3)

        naive_stock = Stock(symbol=symbol)

        # Checks the 1st possible Contract
        contract = self.ib.reqContractDetails(naive_stock)[0].contract

        qualified_list = self.ib.qualifyContracts(contract)

        if not qualified_list:
            print("❌ Contract não resolvido")
            return None

        contract = qualified_list[0]

        ticker = self.ib.reqMktData(contract)

        for _ in range(50):
            self.ib.sleep(0.1)

            price = ticker.last or ticker.marketPrice()

            if price == price:
                return float(price)

        return None
    
    def get_position_qty(self, symbol: str):#TODO talvez adicionar filtro de client ID
        """Obter quantos stocks tenho de um determinado ticker.
        Exemplo: Se tiver 40 ações de AAPL, então: get_position_qty('AAPL') é igual a 40.
        """
        self.ib.sleep(0.5)

        stock = self.get_positions()[symbol]
        position_qty = stock["quantity"]

        return position_qty

    def place_order(self, symbol: str, qty: float, side: str):
        
        naive_stock = Stock(symbol=symbol)

        # Checks the 1st possible Contract
        contract = self.ib.reqContractDetails(naive_stock)[0].contract

        contract = self.ib.qualifyContracts(contract)[0]

        order = MarketOrder(action=side, totalQuantity=qty)
        order.tif = "IOC" # Immediate or Cancel

        self.ib.placeOrder(contract=contract, order=order)

        return f"{side} {qty} at {self.get_price(symbol)} {contract.currency}"  # Retorna o preço atual do ticker após a ordem (pode ser melhorado para retornar o preço de execução real)
    
    def get_orders_history(self): # Este não é o histórico de ordens completo
        history = self.ib.reqExecutions()
        orders_history = []
        for h in history:
            if h.execution.side == "BOT":
                side = "BUY"
            else:
                side = "SELL"

            date = h.execution.time
            date = date.strftime("%Y-%m-%d %H:%M:%S")
            orders_history.append({
                #"client_id": h.execution.clientId,
                #"exec_id": h.execution.execId,
                "order_id": h.execution.orderId,
                "symbol": h.contract.symbol,
                "Side": side,
                "quantity": h.execution.shares,
                "price": h.execution.price,
                "date": date
            })
            
        return orders_history
    
    def get_pending_orders(self): #Falta verificar se este é o formato correto
        return self.ib.openOrders()
    
    def cancel_order(self, order_id: str):

        open_orders = self.ib.openOrders()

        if not open_orders:
            return "Não há ordens para cancelar."

        # Cancel all
        if order_id == "ALL":
            for order in open_orders:
                self.ib.cancelOrder(order)
            return f"Canceladas {len(open_orders)} ordens."

        # Cancel specific
        for order in open_orders:
            if str(order.orderId) == str(order_id):
                self.ib.cancelOrder(order)
                return f"Ordem {order_id} cancelada."

        return f"Ordem {order_id} não encontrada."

    def get_all_assets(self): # TODO
        #TODO
        # Não vai ser possível fazer selectbox, aqui a malta vai meter logo o symbolo
        return ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "JPM", "V", "DIS"]
        raise ValueError("Não quero aqui selectbox")
    
    def disconnect(self):
        self.ib.disconnect()

if __name__ == "__main__":
    try:
        print("\n" + "="*60)
        print("Interactive Broker")
        print("="*60 + "\n")
        
        ib = InteractiveBroker(host='127.0.0.1', client_id=2)
        
        if ib.ib.isConnected():
            stock_symbol = "AAPL"

            print("\n[*] A obter o balanço da conta...")
            balance = ib.get_balance()
            print(f"\nBalanço: {balance}")

            print("\n[*] A obter resumo da conta...")
            summary = ib.get_account_summary()
            print(f"\nResumo: {summary}")

            print("\n[*] A obter as posições da conta...")
            positions = ib.get_positions()
            print(f"\nPosições: {positions}")

            print(f"\n[*] A obter a quantidade de {stock_symbol} no portfólio...")
            qty = ib.get_position_qty(stock_symbol)
            print(f"\nQuantidade: {qty}")

            print(f"\n[*] Compra uma unidade de {stock_symbol}...")
            buy = ib.place_order(stock_symbol, 1, "BUY")
            print(f"\nOutput: {buy}")
            
            print(f"\n[*] A obter a quantidade de {stock_symbol} no portfólio...")
            qty = ib.get_position_qty(stock_symbol)
            print(f"\nQuantidade: {qty}")

            print(f"\n[*] Vende uma unidade de {stock_symbol}...")
            sell = ib.place_order(stock_symbol, 1, "SELL")
            print(f"\nOutput: {sell}")

            print(f"\n[*] A obter a quantidade de {stock_symbol} no portfólio...")
            qty = ib.get_position_qty(stock_symbol)
            print(f"\nQuantidade: {qty}")

            print("\n[*] A obter a ordens pendentes...")
            pending_orders = ib.get_pending_orders()
            print(f"\nOrdens Pendentes: {pending_orders}")
            
            print("\n[*] A cancelar ordens...")
            canceling_orders = ib.cancel_order("ALL")
            print(f"\nOrdens Pendentes: {canceling_orders}")

            print("\n[*] Histórico de transações...")
            history = ib.get_orders_history()
            print(f"\nHistórico: {history}")

        else:
            print("[✗] Não conectado")
        
        
        
        ib.ib.disconnect()
        print("\n" + "="*60)
    except Exception as e:
        print(f"[✗] Erro: {e}")