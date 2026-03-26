from .base import *
from decouple import config


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

DEBUG = True
# Keep dev friendly defaults; production should set this explicitly.
ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS", default="localhost,127.0.0.1,[::1]"
).split(",")




