# src/ui/dashboard.py
import streamlit as st
import pandas as pd
import time
from utils import get_saldo_disponivel
import plotly.express as px

# --- BARRA LATERAL ---
def render_sidebar(broker, user_role, portfolio_name):
    try:
        dados = broker.get_account_summary()
        equity_total = dados["equity"]
        cash_atual = dados["cash"]
        
        _, custo_pendentes = get_saldo_disponivel(broker)
        disponivel_real = cash_atual - custo_pendentes
        
    except Exception as e:
        equity_total, cash_atual, disponivel_real, custo_pendentes = 0, 0, 0, 0

    with st.sidebar:
        st.write(f"Logged in: **{portfolio_name}**")
        
        if user_role == 'guest': st.warning("GUEST")
        else: st.success("ADMIN")

        if st.button("Logout", type="secondary"):
            broker.disconnect()
            st.session_state['logged_in'] = False
            if 'broker' in st.session_state: del st.session_state.broker
            st.rerun()
            
        st.divider()
        st.header("Summary")
        st.metric("Total Equity", f"${equity_total:,.2f}")
        st.divider()
        st.metric("Buying Power", f"${disponivel_real:,.2f}")

        if custo_pendentes > 0:
            st.caption(f"🔒 Locked: ${custo_pendentes:,.2f}")
    
    return disponivel_real

# --- ABAS ---

def render_tab_trade(broker, saldo_disp):
    @st.cache_data(ttl=300)
    def get_assets():
        try: return broker.get_all_assets()
        except: return ["AAPL", "TSLA", "MSFT"]
    
    #lista = get_assets()
    
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("New Order")
        #symbol = st.selectbox("Asset:", lista, index=None, placeholder="Choose an asset...")
        symbol = st.text_input("Asset:", placeholder="Choose an asset...").upper().strip()
        preco = 0
        if symbol:
            try: 
                preco = broker.get_price(symbol)
                st.metric(f"{symbol} Price", f"${preco:.2f}")
            except: st.warning("Price N/A")
            
        if preco > 0:
            tipo_ui = st.radio("Side:", ["Buy", "Sell"], horizontal=True)
            tipo = tipo_ui.lower()
            
            qty = 0.0

            # Verifica Conflitos usando sempre minúsculas
            bloqueio_conflito = False
            msg_conflito = ""
            try:
                pendentes = broker.get_pending_orders()
                for p in pendentes:
                    if p.symbol == symbol:
                        if tipo == 'buy' and p.side == 'sell':
                            bloqueio_conflito = True
                            msg_conflito = f"⛔ You have a pending SELL of {p.qty}!"
                        elif tipo == 'sell' and p.side == 'buy':
                            bloqueio_conflito = True
                            msg_conflito = f"⛔ You have a pending BUY of {p.qty}!"
            except: pass

            # Inputs
            if tipo == 'sell':
                qtd_tenho = broker.get_position_qty(symbol)
                if qtd_tenho <= 0:
                    st.error(f"⚠️ You don't own **{symbol}**.")
                    qty = 0.0
                else:
                    st.caption(f"Portfolio: {qtd_tenho}")
                    if st.checkbox("Sell All"):
                        qty = float(qtd_tenho)
                    else:
                        qty = st.number_input("Qty:", min_value=0.0, max_value=float(qtd_tenho), value=1.0)
            else:
                qty = st.number_input("Qty:", 1.0)
            
            custo = preco * qty
            st.caption(f"Total: ${custo:,.2f}")
            
            if bloqueio_conflito: st.error(msg_conflito)

            # Botão
            desativado = (qty <= 0) or bloqueio_conflito
            if st.button("Confirme Order", disabled=desativado, width="stretch"):
                if tipo == 'buy' and custo > saldo_disp:
                    st.error(f"Insufficient funds! Available: ${saldo_disp:.2f}")
                else:
                    try:
                        with st.spinner("Sending..."):
                            # Agora passa o 'tipo' diretamente porque já é minúsculo
                            broker.place_order(symbol, qty, tipo)
                            st.success("Success!")
                            time.sleep(1)
                            st.rerun()
                    except Exception as e: st.error(str(e))
    with c2: pass

def render_tab_portfolio(broker): # Check TODOs
    if st.button("🔄 Refresh Table"): st.rerun()
    try:
        pos = broker.get_positions()
        dados_conta = broker.get_account_summary()
        equity = dados_conta["equity"]
        
        # Garante que o cash é um número (float). Se vier string, converte.
        cash = float(dados_conta["cash"])
        
        data = []

        if pos:
            for key, p in pos.items():

                qty = p["quantity"]
                avg_price = float(p["avg_price"])
                symbol = p["symbol"]

                price = float(broker.get_price(symbol))

                cost_basis = qty * avg_price
                total_value = qty * price

                profit = total_value - cost_basis

                profit_percent = ((price - avg_price) / avg_price) if avg_price != 0 else 0

                data.append({
                    "Asset": symbol,
                    "Quantity": qty,
                    "Current Price ($)": price,
                    "Average Price ($)": avg_price,
                    "Profit ($)": profit,
                    "Profit (%)": profit_percent,
                    "Total Value ($)": total_value,
                })
        
        # Adiciona Cash se for significativo
        if cash > 1.0:
            data.append({
                "Asset": "CASH",
                "Quantity": None,
                "Average Price ($)": None,
                "Current Price ($)": None,
                "Total Value ($)": cash,
                "Profit ($)": None,
                "Profit (%)": None
            })

        # Adiciona Total do Portfólio
        data.append({
            "Asset": "TOTAL",
            "Quantity": None,
            "Average Price ($)": None,
            "Current Price ($)": None,
            "Total Value ($)": equity,
            "Profit ($)": (equity - 1000000),
            "Profit (%)": (equity - 1000000) / 1000000
        })

        if data:
            df = pd.DataFrame(data)
            df = df.sort_values(by="Total Value ($)", ascending=False)
            
            # --- FUNÇÃO DE COR SEGURA ---
            def color_profit(val):
                if isinstance(val, (int, float)):
                    color = '#4CAF50' if val > 0 else '#FF4B4B' if val < 0 else 'white'
                    return f'color: {color}'
                return 'color: white'
            
            def whitebackground_none(val):
                if pd.isna(val):
                    return 'background-color: #000000'
                return ''
            
            # Aplica o estilo
            styled_df = (
                df.style
                .map(color_profit, subset=['Profit (%)'])
                .map(whitebackground_none, subset=['Quantity', 'Average Price ($)', 'Current Price ($)', 'Profit ($)', 'Profit (%)'])
                .format({
                'Total Value ($)': '{:,.2f}',
                'Profit ($)': '{:,.2f}',
                'Profit (%)': '{:.2%}',
                'Quantity': '{:,.2f}',
                'Average Price ($)': '{:,.2f}',
                'Current Price ($)': '{:,.2f}'
            }))

            st.dataframe(styled_df, width="stretch", hide_index=True)
        else: 
            st.info("Portfolio is empty.")

        #TODO Corrigir aqui, pois temos de colocar na mesma currency
        pie_plot = px.pie(df[df["Asset"] != "TOTAL"], names="Asset", values="Total Value ($)", title="Portfolio Distribution")
        st.plotly_chart(pie_plot, use_container_width=True)

    except Exception as e:
        # Se der erro, mostra detalhes para sabermos onde foi
        st.error(f"Error rendering portfolio: {e}")

    

def render_tab_pendentes(broker):
    st.subheader("Order Queue")
    if st.button("🔄 Refresh List"): st.rerun()
    
    pend = broker.get_pending_orders()
    if pend:
        c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
        c1.caption("Asset")
        c2.caption("Operation")
        c3.caption("Time")
        c4.caption("Action")
        st.divider()

        for o in pend:
            with st.container():
                c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
                c1.write(f"**{o.symbol}**")
                if o.side == 'buy':
                    c2.markdown(f":green[**🟢 COMPRA {o.qty}**]")
                else:
                    c2.markdown(f":red[**🔴 VENDA {o.qty}**]")
                c3.write(o.created_at.strftime("%H:%M %d/%m"))
                if c4.button("Cancel", key=f"btn_{o.id}", type="primary", width="stretch",):
                    broker.cancel_order(o.id)
                    st.toast(f"Order {o.symbol} canceled!")
                    time.sleep(0.5)
                    st.rerun()
                st.divider()
    else:
        st.success("All clear! No pending orders.")

def render_tab_historico(broker):
    if st.button("🔄 Load History"): st.rerun()
    
    hist = broker.get_orders_history()
    if hist:
        df = pd.DataFrame(hist)
        
        # --- STYLING DO HISTÓRICO ---
        def color_side(val):
            return 'color: #4CAF50' if val == 'buy' else 'color: #FF4B4B'

        styled_df = df.style.map(color_side, subset=['Side']).format({
            'Price': '${:,.2f}',
            'Qty': '{:,.2f}'
        })
        
        st.dataframe(styled_df,
                    width="stretch",
                    hide_index=True)
    else:
        st.info("No history found.")


# --- MAIN INTERFACE ---
def interface_trading():
    if 'broker' not in st.session_state:
        st.error("Session error.")
        return

    broker = st.session_state.broker
    role = st.session_state.get('user_role', 'guest')
    name = st.session_state.get('portfolio_name', 'Unknown')

    saldo_disp = render_sidebar(broker, role, name)

    st.title(f"Dashboard: {name}")

    if role == 'admin':
        t1, t2, t3, t4 = st.tabs(["Trade", "Portfolio", "Pending", "History"])
        with t1: render_tab_trade(broker, saldo_disp)
        with t2: render_tab_portfolio(broker)
        with t3: render_tab_pendentes(broker)
        with t4: render_tab_historico(broker)
    else:
        t2, t4 = st.tabs(["Portfolio", "History"])
        with t2: render_tab_portfolio(broker)
        with t4: render_tab_historico(broker)