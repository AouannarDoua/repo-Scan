import os

SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
API_KEY = os.getenv("STRIPE_API_KEY")
DEBUG = False
