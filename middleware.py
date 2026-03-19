import os
import jwt
from functools import wraps
from flask import request, jsonify, g

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # --- LIBERAÇÃO DO PREFLIGHT DO CORS ---
        if request.method == 'OPTIONS':
            return jsonify({}), 200

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Token não fornecido ou mal formatado"}), 401

        token = auth_header.split(" ", 1)[1]
        
        try:
            # PROTOCOLO DE EMERGÊNCIA
            payload = jwt.decode(
                token,
                options={"verify_signature": False},
                algorithms=["HS256"] # <--- FALTAVA ISSO PARA NÃO DAR ERRO 500
            )
            g.user_id = payload.get("sub", "anon")
            g.user_email = payload.get("email", "")

            # MOCK DE ROLES
            if g.user_email == "admin@teste.com":
                g.user_role = "admin"
            else:
                g.user_role = "staff"

        except Exception as e:
            return jsonify({"error": f"Erro interno de autenticação: {str(e)}"}), 500

        return f(*args, **kwargs)
    return decorated

def require_admin(f):
    @wraps(f)
    @require_auth
    def decorated(*args, **kwargs):
        if getattr(g, 'user_role', None) != "admin":
            return jsonify({"error": "Acesso negado. Requer privilégios de Administrador."}), 403
        return f(*args, **kwargs)
    return decorated