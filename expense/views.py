from django.shortcuts import render

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.response import Response

from app.models import Transaction
from app.serializers import TransactionSerializer
from .models import *
from .serializers import *
# Create your views here.

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by('-id').distinct()
    serializer_class = CategorySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'user_id__id':['exact'],
        'name':['icontains']
    }

    # def list(self, request):
    #     querysets = self.filter_queryset(self.get_queryset())

    #     data = []
    #     for queryset in querysets:
    #         q_items = Item.objects.filter(category_id__id=queryset.id)
    #         category = CategorySerializer(queryset)
    #         items = ItemSerializer(q_items, many=True)
    #         data.append({'category': category.data, 'items': items.data})

    #     return Response({'data':data}) 


class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all().order_by('-id').distinct()
    serializer_class = ItemSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        # 'category_id__user_id__id':['exact'],
        # 'category_id__id':['exact'],
        # 'category_id__name':['icontains'],
        'name':['icontains'],
        'price':['icontains']
    }

    # def list(self, request):
    #     querysets = self.filter_queryset(self.get_queryset())

    #     data = []
    #     for queryset in querysets:
    #         q_transaction = Transaction.objects.filter(item_id__id=queryset.id)
    #         category = ItemSerializer(queryset)
    #         transaction = TransactionSerializer(q_transaction, many=True)
    #         data.append({'category': category.data, 'transaction': transaction.data})

    #     return Response({'data':data}) 


class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all().order_by('-id').distinct()
    serializer_class = ExpenseSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'date':['exact'],
        'amount':['icontains'],
    }


class ExpenseItemViewSet(viewsets.ModelViewSet):
    queryset = ExpenseItem.objects.all().order_by('-id').distinct()
    serializer_class = ExpenseItemSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'category_id__user_id__id':['exact'],
        'category_id__name':['icontains'],
        'expense_id__id':['exact'],
        'expense_id__date':['exact'],
        'expense_id__amount':['icontains'],
        'item_id__id':['exact'],
        'item_id__name':['exact'],
        'item_id__price':['exact'],
        'amount':['icontains'],
    }
