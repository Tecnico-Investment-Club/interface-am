def get_saldo_disponivel(broker):
    """
    Saldo disponível = cash - ordens de compra pendentes
    """
    try:
        dados_conta = broker.get_account_summary()
        saldo_atual = dados_conta["cash"]
    except:
        saldo_atual = float(broker.get_balance())

    custo_pendente = 0.0

    try:
        pendentes = broker.get_pending_orders()

        for ordem in pendentes:
            if ordem.side != "buy":
                continue

            if hasattr(ordem, "notional") and ordem.notional:
                custo = float(ordem.notional)
            else:
                try:
                    preco = broker.get_price(ordem.symbol)
                    custo = float(ordem.qty) * preco
                except:
                    custo = 0.0

            custo_pendente += custo

    except Exception as e:
        print(f"Erro ao calcular pendentes: {e}")

    saldo_disponivel = saldo_atual - custo_pendente

    return saldo_disponivel, custo_pendente