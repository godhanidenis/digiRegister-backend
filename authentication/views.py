import jwt

from django.contrib.auth import login
from django.conf import settings
from django.contrib.auth.hashers import check_password

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import status
from rest_framework import exceptions

from authentication.auth_utils import token
from app.models import *
from app.serializers import *


class LoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self,request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email:
            return Response("Please provide Email ID!",status=status.HTTP_401_UNAUTHORIZED)
        elif not password:
            return Response("Please provide password!",status=status.HTTP_401_UNAUTHORIZED)
        else:

            try:
                user = User.objects.get(email__exact = email)
            except:
                return Response("User Not Exist!",status=status.HTTP_401_UNAUTHORIZED)

            # if user.password != password:
            check_pass = check_password(password,user.password)
            if not check_pass:
                return Response("Invalid Credentials!",status=status.HTTP_401_UNAUTHORIZED)
            else:
                if user is not None:
                    user_data=UserSerializer(user).data
            
                    login(request, user)
                    return Response({
                        "access_token":str(token.generate_access_token(email, True)),
                        "refresh_token":str(token.generate_refresh_token(email)),
                        "user_data":user_data
                    })
                else:
                    return Response("Invalid Credentials!",status=status.HTTP_401_UNAUTHORIZED)

class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get("refresh_token")

        if refresh_token is None:
            raise exceptions.NotFound("Please provide refresh token!")
        
        try:
            tokenInfo = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=['HS256'], verify=False)
            email = tokenInfo['email']
            payload = jwt.decode(
                    refresh_token, settings.SECRET_KEY, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            # logoutUserOnRefreshExpire(username, password)
            raise exceptions.AuthenticationFailed('refresh_token expired')
        except jwt.DecodeError as ex:
            print(ex)
            # logoutUserOnRefreshExpire(username, password)
            raise exceptions.AuthenticationFailed("refresh_token is Not Valid")
        except IndexError:
            # logoutUserOnRefreshExpire(username, password)
            raise exceptions.AuthenticationFailed('Token prefix missing')
    
        try:
            user = User.objects.get(email__exact = email)
        except:
            return Response("Please provide Email Id!",status=status.HTTP_401_UNAUTHORIZED)

        if user is None:
            raise exceptions.AuthenticationFailed('User not found with us!')
        else:
            email = user.email
        return Response({
                "access_token":str(token.generate_access_token(email, True))
            })


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        shop_name = request.data.get('shop_name')
        print("SHOP NAME :: ",shop_name)
        full_name = request.data.get('full_name')
        print("FULL NAME :: ",full_name)
        mobile_no = request.data.get('mobile_no')
        print("MOBILE NO :: ",mobile_no)
        email = request.data.get('email')
        print("EMAIL :: ",email)
        password = request.data.get('password')
        print("PASSWORD :: ",password)

        if not shop_name:
            return Response("Please provide your Shop Name !!")
        elif not full_name:
            return Response("Please provide Full Name !!")
        elif not mobile_no:
            return Response("Please provide Mobile Number !!")
        elif not email:
            return Response("Please provide Email !!")
        elif not password:
            return Response("Please provide Password !!")
        else:

            try:
                user = User.objects.get(email = email)
                return Response("Email is Already Exist !!",status=status.HTTP_400_BAD_REQUEST)
            except:
                User.objects.create(
                    shop_name=shop_name,
                    full_name=full_name,
                    mobile_no=mobile_no,
                    email=email,
                    type_of_user = 'company_owner',
                    password=password
                )

                return Response({
                    "message": "User Created Successfully !!!"
                })