from utils.db import get_connection


def process_payment(user, amount):
    """Débite le compte de l'utilisateur du montant indiqué."""
    conn = get_connection()
    conn.execute("INSERT INTO payments VALUES (?, ?)", user, amount)
    return {"status": "ok", "amount": amount}
