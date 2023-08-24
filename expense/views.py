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

    def list(self, request):
        querysets = self.filter_queryset(self.get_queryset())
        data = []
        for queryset in querysets:
            q_item = ExpenseItem.objects.filter(expense_id=queryset.id)
            expense = ExpenseSerializer(queryset)
            items = ExpenseItemSerializer(q_item, many=True)
            data.append({"expense":expense.data,
                         "items":items.data})
            
        return Response({'data':data})

    def retrieve(self, request, *args, **kwarge):
        instance = self.get_object()

        item = ExpenseItem.objects.filter(expense_id=instance.id)
        transaction = Transaction.objects.filter(expense_id=instance.id)

        serializers = ExpenseSerializer(instance)
        i_serializers = ExpenseItemSerializer(item, many=True)
        t_serializers = TransactionSerializer(transaction, many=True)

        return Response({"expense":serializers.data,
                         "items":i_serializers.data,
                         "serializers":t_serializers.data})

    def create(self, request, *args, **kwargs):
        # print("POST DATA ::", request.data)
        expense = request.data['expense_data']
        # print("EXPENSE ::", expense)
        transaction = request.data['transaction_data']
        # print("TRANSACTION ::", transaction)
        items = request.data['item_data']
        # print("ITEMS ::", items)

        expenseSerializer = ExpenseSerializer(data=expense)
        if expenseSerializer.is_valid():
            expenseSerializer.save()
        else:
            print("Expense Failed to save")
            return Response(expenseSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        transaction['expense_id'] = expenseSerializer.data['id']
        transactionSerializer = TransactionSerializer(data=transaction)
        if transactionSerializer.is_valid():
            transactionSerializer.save()
        else:
            print("Transaction Failed to save")
            return Response(transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        item_instances = []
        for item in items:
            # print("ITEM :::", item)
            item['expense_id'] = expenseSerializer.data['id']
            # print("CHANGE :::", item)
            expenseitemSerializer = ExpenseItemSerializer(data=item)
            if expenseitemSerializer.is_valid():
                item_instance = expenseitemSerializer.save()
                item_instances.append(item_instance)
            else:
                # print("Item Failed to save")
                return Response(expenseitemSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "expense_data": expenseSerializer.data,
            "transaction_data": transactionSerializer.data,
            "items": ExpenseItemSerializer(item_instances, many=True).data
        })


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
