import streamlit as st
import pandas as pd
import os
import time
from dotenv import load_dotenv
from broker import AlpacaBroker

st.set_page_config(page_title="Trader Profissional", layout="wide")
load_dotenv()

# --- INICIALIZAÇÃO ---
if 'broker' not in st.session_state:
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")
    try:
        st.session_state.broker = AlpacaBroker(api_key, secret_key, paper=True)
    except Exception as e:
        st.error(f"Erro ao conectar: {e}")

def run():
    st.title("🚀 Interface de Trading: Pedro & Cruz")
    
    if 'broker' not in st.session_state: return
    broker = st.session_state.broker
    
    # Barra Lateral
    with st.sidebar:
        st.header("Conta Alpaca")
        try:
            saldo = broker.get_balance()
            st.metric("Saldo (Paper)", f"${saldo:,.2f}")
        except:
            st.error("Erro ao ler saldo")

    tab_trade, tab_portfolio = st.tabs(["💸 Negociar", "📊 Portfólio"])

    # --- ABA NEGOCIAR ---
    with tab_trade:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.subheader("Nova Ordem")
            symbol = st.text_input("Ticker", value="AAPL").upper().strip()
            
            # 1. Buscar Preço Atual
            preco_atual = 0
            if symbol:
                try:
                    preco_atual = broker.get_price(symbol)
                    st.metric(f"Preço {symbol}", f"${preco_atual:.2f}")
                except:
                    st.warning(f"Ticker {symbol} não encontrado.")

            if preco_atual > 0:
                tipo = st.radio("Operação:", ["Compra", "Venda"], horizontal=True)
                
                # VARIÁVEL PARA A QUANTIDADE FINAL
                qty = 0.0

                # === LÓGICA DE VENDA COM OPÇÃO "TOTAL" ===
                if tipo == "Venda":
                    # Verifica quanto temos ANTES de mostrar o input
                    qtd_tenho = broker.get_position_qty(symbol)
                    st.caption(f"Disponível em carteira: {qtd_tenho}")
                    
                    if qtd_tenho > 0:
                        vender_tudo = st.checkbox("Vender Tudo (Total)")
                        
                        if vender_tudo:
                            qty = float(qtd_tenho)
                            st.info(f"Modo Total: Serão vendidas {qty} ações.")
                        else:
                            qty = st.number_input("Qtd:", min_value=0.01, value=1.0, step=1.0)
                    else:
                        st.warning("Não tens ações deste ativo para vender.")
                        qty = 0.0 # Bloqueia

                # === LÓGICA DE COMPRA (PADRÃO) ===
                else:
                    qty = st.number_input("Qtd:", min_value=0.01, value=1.0, step=1.0)

                # Mostra o total estimado se a quantidade for válida
                if qty > 0:
                    custo_estimado = preco_atual * qty
                    st.caption(f"Total estimado: ${custo_estimado:,.2f}")

                    if st.button("Confirmar Ordem", use_container_width=True):
                        validado = True
                        
                        # VALIDAÇÃO DE COMPRA (Saldo)
                        if tipo == "Compra":
                            saldo_disponivel = broker.get_balance()
                            if custo_estimado > saldo_disponivel:
                                st.error(f"❌ Saldo insuficiente! Precisas de ${custo_estimado:.2f}.")
                                validado = False

                        # VALIDAÇÃO DE VENDA (Posição) - Segurança Extra
                        elif tipo == "Venda":
                            # Reconfirmamos a quantidade no momento do clique
                            qtd_check = broker.get_position_qty(symbol)
                            if qty > qtd_check:
                                st.error(f"❌ Erro: Tentaste vender {qty} mas só tens {qtd_check}.")
                                validado = False

                        if validado:
                            with st.spinner("A processar..."):
                                try:
                                    broker.place_order(symbol, qty, tipo)
                                    st.success("✅ Ordem Executada!")
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro na API: {e}")

        with c2:
            pass

    # --- ABA PORTFÓLIO ---
    with tab_portfolio:
        if st.button("Atualizar"): st.rerun()
        try:
            posicoes = broker.get_positions()
            if posicoes:
                dados = []
                for p in posicoes:
                    lucro_val = float(p.unrealized_pl)
                    lucro_pct = float(p.unrealized_plpc) * 100
                    
                    dados.append({
                        "Ativo": p.symbol,
                        "Qtd": float(p.qty),
                        "Valor Total": f"${float(p.market_value):.2f}",
                        "Lucro ($)": f"${lucro_val:.2f}",
                        "Lucro (%)": f"{lucro_pct:.2f}%"
                    })
                st.dataframe(pd.DataFrame(dados), use_container_width=True)
            else:
                st.info("Carteira Vazia")
        except Exception as e:
             st.error(f"Erro ao ler portfólio: {e}")

if __name__ == "__main__":
    run()