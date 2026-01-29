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

# --- CACHE PARA A LISTA DE ATIVOS ---
@st.cache_data(ttl=3600)
def carregar_tickers_validos():
    if 'broker' in st.session_state:
        try:
            return st.session_state.broker.get_all_assets()
        except:
            return ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN"]
    return []

def run():
    st.title("🚀 Interface de Trading: Pedro & Cruz")
    
    if 'broker' not in st.session_state: return
    broker = st.session_state.broker
    
    lista_ativos = carregar_tickers_validos()
    
    with st.sidebar:
        st.header("Conta Alpaca")
        try:
            saldo = broker.get_balance()
            st.metric("Saldo (Paper)", f"${saldo:,.2f}")
        except:
            st.error("Erro ao ler saldo")

    # --- ATUALIZADO: 4 ABAS ---
    tab_trade, tab_portfolio, tab_pending, tab_history = st.tabs(["💸 Negociar", "📊 Portfólio", "⏳ Pendentes", "📜 Histórico"])

    # --- ABA NEGOCIAR ---
    with tab_trade:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.subheader("Nova Ordem")
            
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
                            qty = st.number_input("Qtd:", value=1.0, step=1.0)
                    else:
                        st.warning("Sem ações para vender.")
                        qty = 0.0
                else:
                    qty = st.number_input("Qtd:", value=1.0, step=1.0)

                custo = preco_atual * qty
                total_display = max(0, custo) 
                st.caption(f"Total estimado: ${total_display:,.2f}")
                
                botao_bloqueado = (qty <= 0)
                
                if st.button("Confirmar Ordem", width="stretch", disabled=botao_bloqueado):
                    validado = True
                    if tipo == "Compra" and custo > broker.get_balance():
                        st.error("❌ Saldo insuficiente!")
                        validado = False
                    elif tipo == "Venda" and qty > broker.get_position_qty(symbol):
                        st.error("❌ Não tens ações suficientes!")
                        validado = False
                    
                    if validado:
                        with st.spinner("Enviando..."):
                            try:
                                broker.place_order(symbol, qty, tipo)
                                st.success("✅ Ordem enviada com sucesso!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                erro_msg = str(e).lower()
                                if "wash trade" in erro_msg or "opposite side" in erro_msg:
                                    st.warning("⚠️ **Conflito:** Já tens uma ordem contrária pendente. Vai à aba 'Pendentes' e cancela-a.")
                                elif "insufficient qty" in erro_msg:
                                    st.error("❌ Ações presas em ordens pendentes. Verifica a aba 'Pendentes'.")
                                else:
                                    st.error(f"Erro da API: {e}")

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

    # --- ABA PENDENTES (NOVA) ---
    with tab_pending:
        st.subheader("Ordens na Fila de Espera")
        if st.button("🔄 Atualizar Pendentes"): st.rerun()
        
        try:
            pendentes = broker.get_pending_orders()
            if pendentes:
                for ordem in pendentes:
                    # Cria um layout de colunas para cada ordem
                    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 2])
                    
                    data_fmt = ordem.created_at.strftime("%d/%m %H:%M")
                    lado = "🟢 COMPRA" if ordem.side == "buy" else "🔴 VENDA"
                    
                    with c1: st.write(f"**{data_fmt}**")
                    with c2: st.write(f"**{ordem.symbol}**")
                    with c3: st.write(f"{lado}")
                    with c4: st.write(f"Qtd: {ordem.qty}")
                    with c5:
                        # Botão para cancelar esta ordem específica
                        if st.button(f"❌ Cancelar", key=f"btn_cancel_{ordem.id}"):
                            try:
                                broker.cancel_order(ordem.id)
                                st.toast(f"Ordem de {ordem.symbol} cancelada!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao cancelar: {e}")
                    
                    st.divider() # Linha separadora entre ordens
            else:
                st.success("Não tens ordens pendentes. O tabuleiro está limpo! ✨")
        except Exception as e:
            st.error(f"Erro ao buscar pendentes: {e}")

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
                st.dataframe(df_hist, width="stretch", height=500)
            else:
                st.info("Nenhuma ordem encontrada no histórico.")
        except Exception as e:
            st.error(f"Erro ao buscar histórico: {e}")

if __name__ == "__main__":
    run()