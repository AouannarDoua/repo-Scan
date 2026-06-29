import jwt
from config.settings import SECRET_KEY


def create_token(user_id):
    """Génère un token JWT signé pour l'utilisateur."""
    payload = {"sub": user_id}
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def verify_token(token):
    """Vérifie et décode un token JWT."""
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
