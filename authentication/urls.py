from django.contrib import admin
from django.urls import path, include
from .views import *

urlpatterns = [
    path("login/", LoginView.as_view()),
    path("refresh_token/", RefreshTokenView.as_view()),
    path("register/", RegisterView.as_view()),
    path("forgot_password/", ForgotPasswordView.as_view()),
]