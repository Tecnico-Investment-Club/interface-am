import streamlit as st
from pathlib import Path
from dotenv import load_dotenv

# Imports dos nossos módulos (estão na mesma pasta src)
from ui.auth import tela_login
from ui.dashboard import interface_trading

# 1. Configuração Global (Deve ser a primeira linha de Streamlit)
st.set_page_config(page_title="Trading Interface", layout="wide", initial_sidebar_state="expanded")

# 2. Carregar Variáveis de Ambiente
# Como o main.py está em /src, o .env está na pasta acima (..)
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# 3. Gestão de Estado da Sessão
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# 4. Router (Login ou App)
if st.session_state['logged_in']:
    interface_trading()
else:
    tela_login()