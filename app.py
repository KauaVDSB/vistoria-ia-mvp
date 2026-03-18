"""
Ponto de Entrada da API (Vistoria IA)
Inicializa o Flask, configura o banco de dados (SQLAlchemy) e registra os Blueprints.
"""
import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Importa a instância do banco de dados (desacoplada)
from models import db

# Importa os blueprints das nossas frentes de batalha
from routes.admin import admin_bp
from routes.staff import staff_bp

# Carrega variáveis de ambiente (.env)
load_dotenv()

def create_app():
    app = Flask(__name__)
    
    # Configuração de CORS: Essencial para o React (porta 3000) conversar com o Flask (porta 5000)
    # No MVP liberamos tudo ('*'), mas em produção travaríamos para o domínio do front-end.
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Configuração do PostgreSQL (Supabase) via SQLAlchemy
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URI")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Vincula o SQLAlchemy ao nosso app
    db.init_app(app)

    # Registra as rotas no motor do Flask
    app.register_blueprint(admin_bp)
    app.register_blueprint(staff_bp)

    # Rota de Monitoramento (Health Check)
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            "status": "online", 
            "missao": "Vistoria IA API Integrada e Operacional"
        }), 200

    return app

# Instancia a aplicação usando o padrão Application Factory
app = create_app()

if __name__ == '__main__':
    # Roda o servidor na porta 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)