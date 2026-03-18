import os
import jwt
from functools import wraps
from flask import request, jsonify, g

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Token não fornecido ou mal formatado"}), 401

        token = auth_header.split(" ", 1)[1]
        try:
            secret = os.getenv("SUPABASE_JWT_SECRET")
            payload = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
            g.user_id = payload["sub"]
            g.user_email = payload.get("email", "")

            # MOCK DE ROLES (Conforme CLAUDE.md)
            # Se for o e-mail do admin, ele é admin. Qualquer outro é staff.
            if g.user_email == "admin@teste.com":
                g.user_role = "admin"
            else:
                g.user_role = "staff"

        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expirado"}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({"error": f"Token inválido: {str(e)}"}), 401
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