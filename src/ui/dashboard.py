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
        st.write(f"Logado em: **{portfolio_name}**")
        
        if user_role == 'guest': st.warning("VISITANTE")
        else: st.success("ADMIN")

        if st.button("Sair / Logout", type="secondary"):
            st.session_state['logged_in'] = False
            if 'broker' in st.session_state: del st.session_state.broker
            st.rerun()
            
        st.divider()
        st.header("Resumo")
        st.metric("Valor Portfólio (Equity)", f"${equity_total:,.2f}")
        st.divider()
        st.metric("Disponível para Comprar", f"${disponivel_real:,.2f}")

        if custo_pendentes > 0:
            st.caption(f"🔒 Bloqueado: ${custo_pendentes:,.2f}")
    
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
        st.subheader("Nova Ordem")
        symbol = st.selectbox("Ativo:", lista, index=None, placeholder="...")
        
        preco = 0
        if symbol:
            try: 
                preco = broker.get_price(symbol)
                st.metric(f"Preço {symbol}", f"${preco:.2f}")
            except: st.warning("Preço N/A")
            
        if preco > 0:
            tipo = st.radio("Op:", ["Compra", "Venda"], horizontal=True)
            qty = 0.0

            # Verifica Conflitos
            bloqueio_conflito = False
            msg_conflito = ""
            try:
                pendentes = broker.get_pending_orders()
                for p in pendentes:
                    if p.symbol == symbol:
                        if tipo == "Compra" and p.side == 'sell':
                            bloqueio_conflito = True
                            msg_conflito = f"⛔ Tens VENDA pendente de {p.qty}!"
                        elif tipo == "Venda" and p.side == 'buy':
                            bloqueio_conflito = True
                            msg_conflito = f"⛔ Tens COMPRA pendente de {p.qty}!"
            except: pass

            # Inputs
            if tipo == "Venda":
                qtd_tenho = broker.get_position_qty(symbol)
                if qtd_tenho <= 0:
                    st.error(f"⚠️ Não tens **{symbol}**.")
                    qty = 0.0
                else:
                    st.caption(f"Carteira: {qtd_tenho}")
                    if st.checkbox("Vender Tudo"):
                        qty = float(qtd_tenho)
                    else:
                        qty = st.number_input("Qtd:", min_value=0.0, max_value=float(qtd_tenho), value=1.0)
            else:
                qty = st.number_input("Qtd:", 1.0)
            
            custo = preco * qty
            st.caption(f"Total: ${custo:,.2f}")
            
            if bloqueio_conflito: st.error(msg_conflito)

            # Botão
            desativado = (qty <= 0) or bloqueio_conflito
            if st.button("Confirmar", disabled=desativado, width="stretch"):
                if tipo == "Compra" and custo > saldo_disp:
                    st.error(f"Falta saldo! Disp: ${saldo_disp:.2f}")
                else:
                    try:
                        with st.spinner("A enviar..."):
                            broker.place_order(symbol, qty, tipo)
                            st.success("Sucesso!")
                            time.sleep(1)
                            st.rerun()
                    except Exception as e: st.error(str(e))
    with c2: pass

def render_tab_portfolio(broker):
    if st.button("🔄 Atualizar Tabela"): st.rerun()
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
                    "Ativo": p.symbol, 
                    "Qtd": qtd_val,
                    "Total": total_val,
                    "Lucro (%)": lucro_val 
                })
        
        # Adiciona Cash se for significativo
        if cash > 1.0:
            data.append({
                "Ativo": "CASH",
                "Qtd": cash,
                "Total": cash,
                "Lucro (%)": 0.0
            })

        if data:
            df = pd.DataFrame(data)
            df = df.sort_values(by="Total", ascending=False)
            
            # --- FUNÇÃO DE COR SEGURA ---
            def color_profit(val):
                if isinstance(val, (int, float)):
                    color = '#4CAF50' if val > 0 else '#FF4B4B' if val < 0 else 'white'
                    return f'color: {color}'
                return 'color: white' 

            # Aplica o estilo
            styled_df = df.style.map(color_profit, subset=['Lucro (%)']).format({
                'Total': '${:,.2f}',
                'Lucro (%)': '{:.2%}',
                'Qtd': '{:,.2f}'
            })

            st.dataframe(styled_df, width="stretch", hide_index=True)
        else: 
            st.info("Carteira Vazia.")
            
    except Exception as e:
        # Se der erro, mostra detalhes para sabermos onde foi
        st.error(f"Erro ao renderizar portfólio: {e}")

def render_tab_pendentes(broker):
    st.subheader("Ordens na Fila")
    if st.button("🔄 Atualizar Lista"): st.rerun()
    
    pend = broker.get_pending_orders()
    if pend:
        c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
        c1.caption("Ativo")
        c2.caption("Operação")
        c3.caption("Hora")
        c4.caption("Ação")
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
                if c4.button("Cancelar", key=f"btn_{o.id}", type="primary", width="stretch",):
                    broker.cancel_order(o.id)
                    st.toast(f"Ordem {o.symbol} cancelada!")
                    time.sleep(0.5)
                    st.rerun()
                st.divider()
    else:
        st.success("Tudo limpo! Nenhuma ordem pendente.")

def render_tab_historico(broker):
    if st.button("🔄 Carregar Histórico"): st.rerun()
    
    hist = broker.get_orders_history()
    if hist:
        d = []
        for o in hist:
            if o.status == 'filled':
                d.append({
                    "Data": o.filled_at.strftime("%d/%m %H:%M") if o.filled_at else "-",
                    "Sym": o.symbol, 
                    "Side": o.side, 
                    "Qtd": float(o.qty),
                    "Price": float(o.filled_avg_price) if o.filled_avg_price else 0.0
                })
        
        if d:
            df = pd.DataFrame(d)
            
            # --- STYLING DO HISTÓRICO ---
            def color_side(val):
                return 'color: #4CAF50' if val == 'buy' else 'color: #FF4B4B'

            styled_df = df.style.map(color_side, subset=['Side']).format({
                'Price': '${:,.2f}',
                'Qtd': '{:,.2f}'
            })
            
            st.dataframe(styled_df,
                        width="stretch",
                        hide_index=True)
    else:
        st.info("Sem histórico.")

# --- MAIN INTERFACE ---
def interface_trading():
    if 'broker' not in st.session_state:
        st.error("Erro de sessão.")
        return

    broker = st.session_state.broker
    role = st.session_state.get('user_role', 'guest')
    name = st.session_state.get('portfolio_name', 'Unknown')

    saldo_disp = render_sidebar(broker, role, name)

    st.title(f"Painel: {name}")

    if role == 'admin':
        t1, t2, t3, t4 = st.tabs(["💸 Negociar", "📊 Portfólio", "⏳ Pendentes", "📜 Histórico"])
        with t1: render_tab_trade(broker, saldo_disp)
        with t2: render_tab_portfolio(broker)
        with t3: render_tab_pendentes(broker)
        with t4: render_tab_historico(broker)
    else:
        t2, t4 = st.tabs(["📊 Portfólio", "📜 Histórico"])
        with t2: render_tab_portfolio(broker)
        with t4: render_tab_historico(broker)