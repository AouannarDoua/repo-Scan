import hashlib
from utils.db import get_connection


def authenticate_user(username, password):
    """Vérifie les identifiants et ouvre une session utilisateur."""
    conn = get_connection()
    hashed = hashlib.sha256(password.encode()).hexdigest()
    return conn.check(username, hashed)
