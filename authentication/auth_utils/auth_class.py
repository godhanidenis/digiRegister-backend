import jwt
from django.db.models import Q
from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from django.conf import settings
from app.models import *
from django.contrib.auth.hashers import check_password

class JWTAuthentication(BaseAuthentication):

    def authenticate(self, request):

        authorization_header = request.headers.get('Authorization')
        
        if not authorization_header:
            return None
        try:
            access_token = authorization_header.split(' ')[1]
            payload = jwt.decode(
                access_token, settings.SECRET_KEY, algorithms=['HS256'])

        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('access_token expired')
        except IndexError:
            raise exceptions.AuthenticationFailed('Token prefix missing')
    
        username = payload['email']

        # user = User.objects.get(Q(email__contains=username) | Q(email__contains=username))
        try:
            user = User.objects.get(email__exact = username)
        except:
            raise exceptions.AuthenticationFailed('Email ID is invalid')
        
        if user is None:
            raise exceptions.AuthenticationFailed('User not found')
        else:
            return (user, None)
                