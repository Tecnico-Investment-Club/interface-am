import streamlit as st
import os
import time
from broker import AlpacaBroker 
from config import PORTFOLIOS   

def tela_login():
    st.markdown("<h1 style='text-align: center;'>Acesso aos Portfólios</h1>", unsafe_allow_html=True)
    st.write("")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form(key='login_form', border=True):
            st.subheader("Autenticação")
            
            user_choice = st.selectbox("Selecionar Portfólio:", list(PORTFOLIOS.keys()))
            password_input = st.text_input("Senha de Acesso (Para Admins):", type="password")
            
            st.write("") 
            
            c1, c2 = st.columns(2)
            with c1: submit_admin = st.form_submit_button("🔑 Entrar", width="stretch", type="primary")
            with c2: submit_guest = st.form_submit_button("Visitante", width="stretch", type="secondary")
            
            auth_success = False
            role = ""

            if submit_admin:
                config_port = PORTFOLIOS[user_choice]
                
                if config_port["pass_env"] not in os.environ:
                    st.error(f"Erro: Variável {config_port['pass_env']} em falta.")
                else:
                    # Comparação Simples (Revertida como pediste)
                    senha_correta = os.getenv(config_port["pass_env"])
                    if password_input == senha_correta:
                        auth_success = True
                        role = "admin"
                    else:
                        st.error("❌ Senha Incorreta!")

            elif submit_guest:
                auth_success = True
                role = "guest"
            
            if auth_success:
                st.session_state['logged_in'] = True
                st.session_state['portfolio_name'] = user_choice
                st.session_state['user_role'] = role
                
                # Inicializar Broker
                conf = PORTFOLIOS[user_choice]
                api = os.getenv(conf["key_env"])
                sec = os.getenv(conf["sec_env"])
                
                try:
                    st.session_state.broker = AlpacaBroker(api, sec, paper=True)
                    st.success(f"Bem-vindo ao {user_choice}!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao conectar API: {e}")