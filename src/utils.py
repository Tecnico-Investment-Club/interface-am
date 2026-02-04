def get_saldo_disponivel(broker):
    """
    Calcula o saldo subtraindo o valor estimado das ordens de compra pendentes.
    Retorna: (saldo_bruto_buying_power, valor_preso_em_ordens)
    """
    try:
        dados_conta = broker.get_account_summary()
        saldo_atual = dados_conta["buying_power"]
    except:
        saldo_atual = float(broker.get_balance())

    custo_pendente = 0.0
    
    try:
        pendentes = broker.get_pending_orders()
        if pendentes:
            for ordem in pendentes:
                if ordem.side == 'buy':
                    valor_ordem = 0.0
                    if hasattr(ordem, 'notional') and ordem.notional is not None:
                         valor_ordem = float(ordem.notional)
                    else:
                        try:
                            preco = broker.get_price(ordem.symbol)
                            valor_ordem = float(ordem.qty) * preco
                        except:
                            valor_ordem = 0 
                    
                    custo_pendente += valor_ordem
    except Exception as e:
        print(f"Erro ao calcular pendentes: {e}")
        
    return saldo_atual, custo_pendente