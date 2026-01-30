# Usa uma versão leve do Python
FROM python:3.9-slim

# Define a pasta de trabalho dentro do contentor
WORKDIR /interface_am

# Copia primeiro os requisitos 
COPY requirements.txt .

# Instala as bibliotecas
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o resto do código para dentro do contentor
COPY . .

# Porta do programa
EXPOSE 8501

# Comando para iniciar a aplicação quando o contentor arrancar
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]