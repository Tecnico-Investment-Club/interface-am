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

# --- CACHE PARA A LISTA DE ATIVOS (NOVO) ---
@st.cache_data(ttl=3600) # Cache válido por 1 hora
def carregar_tickers_validos():
    # Esta função só corre uma vez por hora para não lentificar a app
    if 'broker' in st.session_state:
        try:
            return st.session_state.broker.get_all_assets()
        except:
            return ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN"] # Fallback se falhar
    return []

def run():
    st.title("🚀 Interface de Trading: Pedro & Cruz")
    
    if 'broker' not in st.session_state: return
    broker = st.session_state.broker
    
    # Carregar a lista de ativos (usando o cache)
    lista_ativos = carregar_tickers_validos()
    
    with st.sidebar:
        st.header("Conta Alpaca")
        try:
            saldo = broker.get_balance()
            st.metric("Saldo (Paper)", f"${saldo:,.2f}")
        except:
            st.error("Erro ao ler saldo")

    tab_trade, tab_portfolio, tab_history = st.tabs(["💸 Negociar", "📊 Portfólio", "📜 Histórico"])

    # --- ABA NEGOCIAR ---
    with tab_trade:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.subheader("Nova Ordem")
            
            # --- MUDANÇA AQUI: Selectbox com pesquisa ---
            # O index=None faz com que a caixa comece vazia
            symbol = st.selectbox(
                "Escolha o Ativo:", 
                options=lista_ativos,
                index=None, 
                placeholder="Escreva para pesquisar (ex: AAPL)..."
            )
            
            preco_atual = 0
            if symbol:
                try:
                    preco_atual = broker.get_price(symbol)
                    st.metric(f"Preço {symbol}", f"${preco_atual:.2f}")
                except:
                    st.warning(f"Preço indisponível para {symbol}.")

            if preco_atual > 0:
                tipo = st.radio("Operação:", ["Compra", "Venda"], horizontal=True)
                qty = 0.0

                if tipo == "Venda":
                    qtd_tenho = broker.get_position_qty(symbol)
                    st.caption(f"Disponível: {qtd_tenho}")
                    if qtd_tenho > 0:
                        if st.checkbox("Vender Tudo (Total)"):
                            qty = float(qtd_tenho)
                        else:
                            qty = st.number_input("Qtd:", min_value=0.01, value=1.0)
                    else:
                        st.warning("Sem ações para vender.")
                        qty = 0.0
                else:
                    qty = st.number_input("Qtd:", min_value=0.01, value=1.0)

                if qty > 0:
                    custo = preco_atual * qty
                    st.caption(f"Total estimado: ${custo:,.2f}")
                    
                    if st.button("Confirmar Ordem", width="stretch"):
                        validado = True
                        if tipo == "Compra" and custo > broker.get_balance():
                            st.error("Saldo insuficiente!")
                            validado = False
                        elif tipo == "Venda" and qty > broker.get_position_qty(symbol):
                            st.error("Não tens ações suficientes!")
                            validado = False
                        
                        if validado:
                            with st.spinner("Enviando..."):
                                try:
                                    broker.place_order(symbol, qty, tipo)
                                    st.success("Ordem enviada!")
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Erro: {e}")

        with c2:
            pass

    # --- ABA PORTFÓLIO ---
    with tab_portfolio:
        if st.button("Atualizar Carteira"): st.rerun()
        try:
            posicoes = broker.get_positions()
            if posicoes:
                dados = []
                for p in posicoes:
                    lucro_pct = float(p.unrealized_plpc) * 100
                    dados.append({
                        "Ativo": p.symbol,
                        "Qtd": float(p.qty),
                        "Valor Total": f"${float(p.market_value):.2f}",
                        "Lucro (%)": f"{lucro_pct:.2f}%"
                    })
                st.dataframe(pd.DataFrame(dados), width="stretch")
            else:
                st.info("Carteira Vazia")
        except Exception as e:
             st.error(f"Erro: {e}")

    # --- ABA HISTÓRICO ---
    with tab_history:
        st.subheader("Histórico Completo")
        if st.button("Atualizar Histórico"): st.rerun()
        
        try:
            ordens = broker.get_orders_history()
            if ordens:
                dados_hist = []
                for o in ordens:
                    data_criacao = o.created_at.strftime("%d/%m/%Y %H:%M")
                    preco_exec = f"${float(o.filled_avg_price):.2f}" if o.filled_avg_price else "-"
                    
                    dados_hist.append({
                        "Data": data_criacao,
                        "Símbolo": o.symbol,
                        "Ação": "Compra" if o.side == "buy" else "Venda",
                        "Qtd": float(o.qty),
                        "Preço": preco_exec,
                        "Status": o.status.upper()
                    })
                
                df_hist = pd.DataFrame(dados_hist)
                st.dataframe(df_hist, width="stretch")
            else:
                st.info("Nenhuma ordem encontrada no histórico.")
        except Exception as e:
            st.error(f"Erro ao buscar histórico: {e}")

if __name__ == "__main__":
    run()