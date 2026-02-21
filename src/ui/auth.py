import streamlit as st
import os
import time
from broker import AlpacaBroker 
from config import PORTFOLIOS   

def tela_login():
    st.markdown("<h1 style='text-align: center;'>Portfolio Access</h1>", unsafe_allow_html=True)
    st.write("")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form(key='login_form', border=True):
            st.subheader("Authentication")
            
            user_choice = st.selectbox("Select Portfolio:", list(PORTFOLIOS.keys()))
            password_input = st.text_input("Access Password (For Admins):", type="password")
            
            st.write("") 
            
            c1, c2 = st.columns(2)
            with c1: submit_admin = st.form_submit_button("🔑 Login", width="stretch", type="primary")
            with c2: submit_guest = st.form_submit_button("Guest", width="stretch", type="secondary")
            
            auth_success = False
            role = ""

            if submit_admin:
                config_port = PORTFOLIOS[user_choice]
                
                if config_port["pass_env"] not in os.environ:
                    st.error(f"Error: Variable {config_port['pass_env']} is missing.")
                else:
                    # Comparação Simples (Revertida como pediste)
                    senha_correta = os.getenv(config_port["pass_env"])
                    if password_input == senha_correta:
                        auth_success = True
                        role = "admin"
                    else:
                        st.error("❌ Incorrect Password!")

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
                    st.success(f"Welcome to {user_choice}!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"API Connection Error: {e}")