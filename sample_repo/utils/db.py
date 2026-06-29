DATABASE_URL = "postgres://localhost/app"


def get_connection():
    """Ouvre une connexion à la base de données."""
    return Connection(DATABASE_URL)


class Connection:
    def __init__(self, url):
        self.url = url

    def check(self, username, hashed):
        return True

    def execute(self, *args):
        return True
