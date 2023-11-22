from datetime import datetime, timedelta
import jwt
from django.conf import settings
from app.models import *

def generate_access_token(email, neverexp = False):

    access_token_payload = {
        'email': email,
        'iat': datetime.utcnow(),
    }

    if not neverexp:
        access_token_payload['exp'] = datetime.utcnow() + timedelta(seconds=int(settings.ACCESS_TOKEN_EXPIRE_TIME_SECONDS))
    access_token = jwt.encode(access_token_payload,
                              settings.SECRET_KEY , algorithm='HS256')
    return access_token


def generate_refresh_token(email):
    refresh_token_payload = {
        'email': email,
        'exp': datetime.utcnow() + timedelta(seconds=int(settings.REFRESH_TOKEN_EXPIRE_TIME_SECONDS)),
        'iat': datetime.utcnow()
    }
    refresh_token = jwt.encode(
        refresh_token_payload, settings.REFRESH_TOKEN_SECRET , algorithm='HS256')

    return refresh_token