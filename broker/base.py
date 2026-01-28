from abc import ABC, abstractmethod

class BrokerBase(ABC):
    
    @abstractmethod
    def get_balance(self):
        """Retorna o saldo disponível em conta (float)."""
        pass

    @abstractmethod
    def place_order(self, symbol: str, qty: float, side: str):
        """Executa uma ordem (side: 'compra' ou 'venda')."""
        pass

    @abstractmethod
    def get_positions(self):
        """Retorna a lista de ativos na carteira."""
        pass

    @abstractmethod
    def get_price(self, symbol: str):
        """Retorna o preço atual de um ativo."""
        pass

    @abstractmethod
    def get_position_qty(self, symbol: str):
        """Retorna a quantidade que tenho de um ativo específico."""
        pass

    @abstractmethod
    def get_orders_history(self):
        """Retorna a lista de todas as ordens (histórico)."""
        pass

    def get_all_assets(self):
        """Retorna uma lista de ativos negociáveis."""
        pass