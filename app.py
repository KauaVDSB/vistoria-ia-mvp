import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from supabase import create_client, Client
from flask_sqlalchemy import SQLAlchemy

# Carrega as variáveis do .env
load_dotenv()

app = Flask(__name__)
CORS(app) # Permite que o front-end React faça requisições para a API

# Configuração do SQLAlchemy (ORM para PostgreSQL no Supabase)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URI")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Configuração do Supabase Client (Para Auth e Storage)
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "Servidor Operacional", "missao": "Vistoria IA"}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)