import streamlit as st
import pandas as pd
import os, plotly.express as px
from dotenv import load_dotenv
from alpaca_trade_api.rest import REST
from datetime import datetime

# --- Config & API ---
load_dotenv()
# Nota: Removi o /v2 do BASE_URL pois a lib REST trata disso internamente
api = REST(os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY"), "https://paper-api.alpaca.markets")

st.set_page_config(page_title="Minimal Trader", layout="centered")

def run():
    st.title("📈 Pedro e Cruz a Bombar")
    
    if 'historico' not in st.session_state:
        st.session_state.historico = []

    # 1. CÁLCULO DE CUSTÓDIA
    posicoes = {}
    for t in st.session_state.historico:
        s, q, tipo, total = t['Símbolo'], t['Qtd'], t['Tipo'], t['Total']
        if s not in posicoes: posicoes[s] = {'qtd': 0, 'custo_total': 0}
        if tipo == "Buy":
            posicoes[s]['qtd'] += q
            posicoes[s]['custo_total'] += total
        else:
            if posicoes[s]['qtd'] > 0:
                p_medio = posicoes[s]['custo_total'] / posicoes[s]['qtd']
                posicoes[s]['qtd'] -= q
                posicoes[s]['custo_total'] -= (p_medio * q)

    custodia = {s: v for s, v in posicoes.items() if v['qtd'] > 0}

    tab_trade, tab_portfolio, tab_hist = st.tabs(["💸 Negociar", "📊 Portfólio", "📜 Histórico"])

    with tab_trade:
        st.subheader("Nova Operação")
        symbol = st.text_input("Ticker (ex: AAPL)", value="").upper().strip()
        
        # Só avançamos se o utilizador escreveu algo
        if symbol:
            try:
                # Tentativa real de obter o preço
                trade = api.get_latest_trade(symbol)
                price = trade.price
                
                st.success(f"Preço de Mercado: ${price:,.2f}")
                qtd = st.number_input("Quantidade", min_value=1, value=1)
                
                qtd_atual = custodia.get(symbol, {}).get('qtd', 0)
                st.caption(f"Saldo em carteira: {qtd_atual} unidades")

                c1, c2 = st.columns(2)
                # Os botões de submissão agora estão CONDICIONADOS ao preço existir
                if c1.button(f"Comprar {symbol}", use_container_width=True):
                    st.session_state.historico.append({
                        "Data": datetime.now().strftime("%H:%M:%S"), 
                        "Símbolo": symbol, 
                        "Tipo": "Buy", 
                        "Qtd": qtd, 
                        "Total": price * qtd
                    })
                    st.rerun()
                
                if c2.button(f"Vender {symbol}", use_container_width=True, disabled=(qtd_atual < qtd), type="primary"):
                    st.session_state.historico.append({
                        "Data": datetime.now().strftime("%H:%M:%S"), 
                        "Símbolo": symbol, 
                        "Tipo": "Sell", 
                        "Qtd": qtd, 
                        "Total": price * qtd
                    })
                    st.rerun()
                    
            except Exception:
                # Se a API der erro, não mostramos botões nem permitimos compra
                st.warning("Ticker inválido ou não encontrado na Alpaca.")
        else:
            st.info("Digita um ticker para começar.")

    with tab_portfolio:
        if custodia:
            dados_p = []
            for s, v in custodia.items():
                try:
                    p_atual = api.get_latest_trade(s).price
                    v_mercado = p_atual * v['qtd']
                    dados_p.append({
                        "Ativo": s, 
                        "Qtd": v['qtd'], 
                        "Custo Médio": f"${(v['custo_total']/v['qtd']):,.2f}", 
                        "Valor Atual": v_mercado
                    })
                except: continue
            
            if dados_p:
                df_p = pd.DataFrame(dados_p)
                st.table(df_p.set_index("Ativo"))
                fig = px.pie(df_p, values='Valor Atual', names='Ativo', hole=0.5)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Carteira vazia.")

    with tab_hist:
        if st.session_state.historico:
            st.dataframe(pd.DataFrame(st.session_state.historico), use_container_width=True)
            if st.button("Limpar Tudo"):
                st.session_state.historico = []
                st.rerun()

if __name__ == "__main__":
    run()