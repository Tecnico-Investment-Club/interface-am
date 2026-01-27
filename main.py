import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime

# --- Configuração da Página ---
st.set_page_config(page_title="AM - Stock Trader", layout="wide")

# --- Lista de Ações Populares ---
TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "PETR4.SA", "VALE3.SA"]

def run():
    st.title("🚀 AM - Interface Incrível")
    
    # Inicializar histórico na sessão
    if 'historico' not in st.session_state:
        st.session_state.historico = []

    tab_order, tab_history, tab_plots = st.tabs(["💸 Negociar", "📜 Histórico", "📈 Análise"])

    with tab_order:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            symbol = st.selectbox("Escolha a Ação:", TICKERS)
            tipo = st.radio("Operação:", ["Compra", "Venda"], horizontal=True)
            quantidade = st.number_input("Quantidade:", min_value=1, value=10, step=1)
            
            # Obter preço atual via yfinance
            ticker_data = yf.Ticker(symbol)
            preco_atual = ticker_data.fast_info['last_price']
            
            st.metric(label=f"Preço Atual ({symbol})", value=f"${preco_atual:.2f}")
            
            if st.button("Confirmar Transação", use_container_width=True):
                nova_transacao = {
                    "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Símbolo": symbol,
                    "Tipo": tipo,
                    "Qtd": quantidade,
                    "Preço Unit.": round(preco_atual, 2),
                    "Total": round(preco_atual * quantidade, 2)
                }
                st.session_state.historico.append(nova_transacao)
                st.success(f"{tipo} de {quantidade} unidades de {symbol} realizada!")

        with col2:
            st.subheader(f"Gráfico de {symbol}")
            periodo = st.select_slider("Período:", options=["1mo", "3mo", "6mo", "1y"], value="3mo")
            dados_hist = ticker_data.history(period=periodo)
            st.line_chart(dados_hist['Close'])

    with tab_history:
        st.subheader("Minhas Transações")
        if st.session_state.historico:
            df_hist = pd.DataFrame(st.session_state.historico)
            st.dataframe(df_hist, use_container_width=True, hide_index=True)
            
            # Resumo simples
            total_investido = df_hist[df_hist['Tipo'] == "Compra"]['Total'].sum()
            st.write(f"**Total Investido Acumulado:** ${total_investido:,.2f}")
        else:
            st.info("Nenhuma transação registada ainda.")

    with tab_plots:
        if st.session_state.historico:
            st.subheader("Distribuição da Carteira")
            df_plot = pd.DataFrame(st.session_state.historico)
            # Agrupar por símbolo para ver o que o user mais compra
            composicao = df_plot.groupby("Símbolo")["Qtd"].sum()
            st.bar_chart(composicao)
        else:
            st.warning("Adicione transações para ver a análise da sua carteira.")

    st.markdown("---")

if __name__ == "__main__":
    run()