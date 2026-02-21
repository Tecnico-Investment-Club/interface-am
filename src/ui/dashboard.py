# src/ui/dashboard.py
import streamlit as st
import pandas as pd
import time
from utils import get_saldo_disponivel

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
    
    lista = get_assets()
    
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("New Order")
        symbol = st.selectbox("Asset:", lista, index=None, placeholder="Choose an asset...")
        
        preco = 0
        if symbol:
            try: 
                preco = broker.get_price(symbol)
                st.metric(f"{symbol} Price", f"${preco:.2f}")
            except: st.warning("Price N/A")
            
        if preco > 0:
            tipo = st.radio("Side:", ["Buy", "Sell"], horizontal=True)
            qty = 0.0

            # Verifica Conflitos
            bloqueio_conflito = False
            msg_conflito = ""
            try:
                pendentes = broker.get_pending_orders()
                for p in pendentes:
                    if p.symbol == symbol:
                        if tipo == "Buy" and p.side == 'sell':
                            bloqueio_conflito = True
                            msg_conflito = f"⛔ You have a pending SELL of {p.qty}!"
                        elif tipo == "Sell" and p.side == 'buy':
                            bloqueio_conflito = True
                            msg_conflito = f"⛔ You have a pending BUY of {p.qty}!"
            except: pass

            # Inputs
            if tipo == "Sell":
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
                if tipo == "Buy" and custo > saldo_disp:
                    st.error(f"Insufficient funds! Available: ${saldo_disp:.2f}")
                else:
                    try:
                        with st.spinner("Sending..."):
                            broker.place_order(symbol, qty, tipo)
                            st.success("Success!")
                            time.sleep(1)
                            st.rerun()
                    except Exception as e: st.error(str(e))
    with c2: pass

def render_tab_portfolio(broker):
    if st.button("🔄 Refresh Table"): st.rerun()
    try:
        pos = broker.get_positions()
        dados_conta = broker.get_account_summary()
        
        # Garante que o cash é um número (float). Se vier string, converte.
        cash = float(dados_conta["cash"])
        
        data = []
        if pos:
            for p in pos:
                # --- PROTEÇÃO CONTRA ERROS DE DADOS ---
                try:
                    lucro_val = float(p.unrealized_plpc) if p.unrealized_plpc else 0.0
                    total_val = float(p.market_value) if p.market_value else 0.0
                    qtd_val = float(p.qty) if p.qty else 0.0
                except:
                    lucro_val, total_val, qtd_val = 0.0, 0.0, 0.0

                data.append({
                    "Asset": p.symbol, 
                    "Qty": qtd_val,
                    "Total Value": total_val,
                    "Profit (%)": lucro_val 
                })
        
        # Adiciona Cash se for significativo
        if cash > 1.0:
            data.append({
                "Asset": "CASH",
                "Qty": cash,
                "Total Value": cash,
                "Profit (%)": 0.0
            })

        if data:
            df = pd.DataFrame(data)
            df = df.sort_values(by="Total Value", ascending=False)
            
            # --- FUNÇÃO DE COR SEGURA ---
            def color_profit(val):
                if isinstance(val, (int, float)):
                    color = '#4CAF50' if val > 0 else '#FF4B4B' if val < 0 else 'white'
                    return f'color: {color}'
                return 'color: white' 

            # Aplica o estilo
            styled_df = df.style.map(color_profit, subset=['Profit (%)']).format({
                'Total Value': '${:,.2f}',
                'Profit (%)': '{:.2%}',
                'Qty': '{:,.2f}'
            })

            st.dataframe(styled_df, width="stretch", hide_index=True)
        else: 
            st.info("Portfolio is empty.")
            
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
        d = []
        for o in hist:
            if o.status == 'filled':
                d.append({
                    "Date": o.filled_at.strftime("%d/%m %H:%M") if o.filled_at else "-",
                    "Symbol": o.symbol, 
                    "Side": o.side, 
                    "Qty": float(o.qty),
                    "Price": float(o.filled_avg_price) if o.filled_avg_price else 0.0
                })
        
        if d:
            df = pd.DataFrame(d)
            
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