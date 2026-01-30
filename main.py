import streamlit as st
import pandas as pd
import os
import time
from dotenv import load_dotenv
from broker import AlpacaBroker

# --- SETUP INICIAL ---
st.set_page_config(page_title="Trader Pro", layout="wide", initial_sidebar_state="expanded")
load_dotenv()

# --- CONFIGURAÇÃO DOS 3 PORTFÓLIOS ---
PORTFOLIOS = {
    "🛡️ Guardian": {
        "key_env": "API_KEY_GUARDIAN",
        "sec_env": "SECRET_KEY_GUARDIAN",
        "pass_env": "PASS_GUARDIAN"
    },
    "🌅 Horizon": {
        "key_env": "API_KEY_HORIZON",
        "sec_env": "SECRET_KEY_HORIZON",
        "pass_env": "PASS_HORIZON"
    },
    "📈 Market Plus": {
        # Atualizei aqui as chaves para MARKET_PLUS como pediste
        "key_env": "API_KEY_MARKET_PLUS",
        "sec_env": "SECRET_KEY_MARKET_PLUS",
        "pass_env": "PASS_MARKET_PLUS"
    }
}

# --- TELA DE LOGIN ---
def tela_login():
    st.markdown("<h1 style='text-align: center;'>🔐 Acesso aos Portfólios</h1>", unsafe_allow_html=True)
    st.write("")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form(key='login_form', border=True):
            st.subheader("Autenticação")
            
            user_choice = st.selectbox("Selecionar Portfólio:", list(PORTFOLIOS.keys()))
            password_input = st.text_input("Senha de Acesso (Para Admins):", type="password")
            
            st.write("") # Espaço estético
            
            c_btn1, c_btn2 = st.columns(2)
            
            with c_btn1:
                # Botão Principal (Admin)
                submit_admin = st.form_submit_button("🔑 Entrar (Admin)", use_container_width=True, type="primary")
            
            with c_btn2:
                # Botão Secundário (Guest)
                submit_guest = st.form_submit_button("👀 Visitante", use_container_width=True, type="secondary")
            
            # --- LÓGICA DE LOGIN ---
            auth_success = False
            role = ""

            if submit_admin:
                config = PORTFOLIOS[user_choice]
                # Tenta buscar a senha. Se não existir no .env, avisa.
                if config["pass_env"] not in os.environ:
                    st.error(f"Erro: Variável {config['pass_env']} não encontrada no .env")
                else:
                    senha_correta = os.getenv(config["pass_env"])
                    if password_input == senha_correta:
                        auth_success = True
                        role = "admin"
                    else:
                        st.error("❌ Senha Incorreta!")

            elif submit_guest:
                auth_success = True
                role = "guest"
            
            # Se a autenticação passou
            if auth_success:
                st.session_state['logged_in'] = True
                st.session_state['portfolio_name'] = user_choice
                st.session_state['user_role'] = role
                
                config = PORTFOLIOS[user_choice]
                api_key = os.getenv(config["key_env"])
                secret_key = os.getenv(config["sec_env"])
                
                try:
                    st.session_state.broker = AlpacaBroker(api_key, secret_key, paper=True)
                    if role == 'admin':
                        st.success(f"Bem-vindo, Chefe! Acedendo ao {user_choice}...")
                    else:
                        st.info(f"Modo Leitura: Acedendo ao {user_choice}...")
                    
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao conectar API: {e}")

# --- APP PRINCIPAL (TRADING) ---
def interface_trading():
    user_role = st.session_state.get('user_role', 'guest')

    with st.sidebar:
        st.write(f"Logado em: **{st.session_state['portfolio_name']}**")
        
        if user_role == 'guest':
            st.warning("👀 MODO VISITANTE\n(Apenas Leitura)")
        else:
            st.success("🔑 MODO ADMIN\n(Acesso Total)")

        if st.button("Sair / Logout", type="secondary"):
            st.session_state['logged_in'] = False
            if 'broker' in st.session_state:
                del st.session_state.broker
            st.rerun()
            
        st.divider()
        st.header("Conta Alpaca")
        try:
            saldo = st.session_state.broker.get_balance()
            st.metric("Saldo (Paper)", f"${saldo:,.2f}")
        except:
            st.error("Erro ao ler saldo")

    st.title(f"🚀 Painel de Trading: {st.session_state['portfolio_name']}")
    
    if 'broker' not in st.session_state:
        st.error("Erro de sessão. Faz login novamente.")
        return

    broker = st.session_state.broker
    
    @st.cache_data(ttl=3600)
    def get_assets():
        try: return broker.get_all_assets()
        except: return ["AAPL", "TSLA", "MSFT"]

    lista_ativos = get_assets()

    # --- DEFINIÇÃO DAS ABAS ---
    if user_role == 'admin':
        tab_trade, tab_portfolio, tab_pending, tab_history = st.tabs(["💸 Negociar", "📊 Portfólio", "⏳ Pendentes", "📜 Histórico"])
    else:
        tab_portfolio, tab_history = st.tabs(["📊 Portfólio", "📜 Histórico"])
        tab_trade = None
        tab_pending = None

    # --- ABA 1: Negociar (SÓ ADMIN) ---
    if user_role == 'admin' and tab_trade:
        with tab_trade:
            c1, c2 = st.columns([1, 2])
            with c1:
                st.subheader("Nova Ordem")
                symbol = st.selectbox("Ativo:", options=lista_ativos, index=None, placeholder="Pesquisar...")
                
                preco_atual = 0
                if symbol:
                    try:
                        preco_atual = broker.get_price(symbol)
                        st.metric(f"Preço {symbol}", f"${preco_atual:.2f}")
                    except:
                        st.warning("Preço indisponível.")

                if preco_atual > 0:
                    tipo = st.radio("Operação:", ["Compra", "Venda"], horizontal=True)
                    qty = 0.0

                    if tipo == "Venda":
                        qtd_tenho = broker.get_position_qty(symbol)
                        st.caption(f"Disponível: {qtd_tenho}")
                        if qtd_tenho > 0:
                            if st.checkbox("Vender Tudo"):
                                qty = float(qtd_tenho)
                            else:
                                qty = st.number_input("Qtd:", value=1.0, step=1.0)
                        else:
                            st.warning("Nada para vender.")
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
                            st.error("❌ Ações insuficientes!")
                            validado = False
                        
                        if validado:
                            with st.spinner("A processar..."):
                                try:
                                    broker.place_order(symbol, qty, tipo)
                                    st.success("✅ Sucesso!")
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    erro_msg = str(e).lower()
                                    if "wash trade" in erro_msg or "opposite side" in erro_msg:
                                        st.warning("⚠️ Conflito: Verifica aba Pendentes.")
                                    elif "insufficient qty" in erro_msg:
                                        st.error("❌ Ações presas em ordens pendentes.")
                                    else:
                                        st.error(f"Erro: {e}")
            with c2: pass

    # --- ABA 2: Portfólio (TODOS VEEM) ---
    with tab_portfolio:
        if st.button("Atualizar Carteira"): st.rerun()
        try:
            posicoes = broker.get_positions()
            if posicoes:
                dados = []
                for p in posicoes:
                    lucro = float(p.unrealized_plpc) * 100
                    dados.append({
                        "Ativo": p.symbol,
                        "Qtd": float(p.qty),
                        "Total": f"${float(p.market_value):.2f}",
                        "Lucro (%)": f"{lucro:.2f}%"
                    })
                # CORREÇÃO AQUI: mudado de use_container_width=True para width="stretch"
                st.dataframe(pd.DataFrame(dados), width="stretch")
            else:
                st.info("Carteira Vazia")
        except Exception as e:
             st.error(f"Erro: {e}")

    # --- ABA 3: Pendentes (SÓ ADMIN) ---
    if user_role == 'admin' and tab_pending:
        with tab_pending:
            st.subheader("Ordens na Fila")
            if st.button("🔄 Atualizar"): st.rerun()
            try:
                pendentes = broker.get_pending_orders()
                if pendentes:
                    for ordem in pendentes:
                        c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 2])
                        with c1: st.write(ordem.created_at.strftime("%d/%m %H:%M"))
                        with c2: st.write(f"**{ordem.symbol}**")
                        with c3: st.write("🟢 COMPRA" if ordem.side == "buy" else "🔴 VENDA")
                        with c4: st.write(f"Qtd: {ordem.qty}")
                        with c5:
                            if st.button("❌ Cancelar", key=f"cancel_{ordem.id}"):
                                broker.cancel_order(ordem.id)
                                st.toast("Cancelada!")
                                time.sleep(1)
                                st.rerun()
                        st.divider()
                else:
                    st.success("Tudo limpo! ✨")
            except Exception as e:
                st.error(f"Erro: {e}")

    # --- ABA 4: Histórico (TODOS VEEM) ---
    with tab_history:
        if st.button("Atualizar Histórico"): st.rerun()
        try:
            ordens = broker.get_orders_history()
            if ordens:
                dados_hist = []
                for o in ordens:
                    dados_hist.append({
                        "Data": o.created_at.strftime("%d/%m %H:%M"),
                        "Símbolo": o.symbol,
                        "Ação": "Compra" if o.side == "buy" else "Venda",
                        "Qtd": float(o.qty),
                        "Preço": f"${float(o.filled_avg_price):.2f}" if o.filled_avg_price else "-",
                        "Status": o.status.upper()
                    })
                
                # CORREÇÃO AQUI TAMBÉM: mudado de use_container_width=True para width="stretch"
                st.dataframe(pd.DataFrame(dados_hist), width="stretch")
            else:
                st.info("Sem histórico.")
        except Exception as e:
            st.error(f"Erro: {e}")

# --- ARRANQUE ---
if __name__ == "__main__":
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    
    if st.session_state['logged_in']:
        interface_trading()
    else:
        tela_login()