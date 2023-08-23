from django.urls import path, include

from rest_framework import routers

from expense import views
from expense.views import *

router = routers.DefaultRouter()
router.register(r'category',views.CategoryViewSet)
router.register(r'item',views.ItemViewSet)
router.register(r'expense',views.ExpenseViewSet)
router.register(r'expenseitem',views.ExpenseItemViewSet)

urlpatterns =[
    path('',include(router.urls)),
]