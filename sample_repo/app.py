from auth.login import authenticate_user
from payments.charge import process_payment
from utils.db import get_connection


def main():
    conn = get_connection()
    user = authenticate_user("alice", "secret")
    if user:
        process_payment(user, amount=4200)


if __name__ == "__main__":
    main()
