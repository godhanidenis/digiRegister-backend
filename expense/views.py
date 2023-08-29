from django.shortcuts import render
from django.db.models import Sum

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

    def list(self, request):
        querysets = self.filter_queryset(self.get_queryset())

        data = []
        for queryset in querysets:
            total_amount = Expense.objects.filter(category_id__id=queryset.id).aggregate(Sum('amount'))['amount__sum']
            # print(f"CATEGORY ID::{queryset.id} ---- TOTAL AMOUNT:: {total_amount}")
            category = CategorySerializer(queryset)
            # q_items = ExpenseItem.objects.filter(category_id__id=queryset.id)
            # items = ExpenseItemSerializer(q_items, many=True)
            data.append({'category': category.data, 'total_amount':total_amount})

        return Response({'data':data}) 

    def retrieve(self, request, *args, **kwarge):
        instance = self.get_object()
        # print("INSTANCE ID :::", instance.id)
        data = {
            "category_data": CategorySerializer(instance).data,
            "category_expense": []
        }
        expenses = Expense.objects.filter(category_id=instance.id)
        for expense in expenses:
            # print("EXPENSE :::", expense.id)
            transaction = Transaction.objects.get(expense_id__id=expense.id)
            # print("TRANSACTION :::", transaction)
            expense_data = ExpenseSerializer(expense).data
            transaction_data = TransactionSerializer(transaction).data

            data["category_expense"].append({
                "expense_data": expense_data,
                "transaction": transaction_data
            })

        return Response(data)


class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.all().order_by('-id').distinct()
    serializer_class = ItemSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'user_id__id':['exact'],
        # 'category_id__id':['exact'],
        # 'category_id__name':['icontains'],
        'name':['icontains'],
        'price':['icontains']
    }

    def list(self, request):
        querysets = self.filter_queryset(self.get_queryset())

        data = []
        for queryset in querysets:
            total_amount = ExpenseItem.objects.filter(item_id__id=queryset.id).aggregate(Sum('amount'))['amount__sum']
            # print(f"ITEM ID::{queryset.id} ---- TOTAL AMOUNT:: {total_amount}")
            category = ItemSerializer(queryset)
            # q_transaction = Transaction.objects.filter(item_id__id=queryset.id)
            # transaction = TransactionSerializer(q_transaction, many=True)
            data.append({'item': category.data, 'total_amount':total_amount})

        return Response({'data':data}) 

    def retrieve(self, request, *args, **kwarge):
        instance = self.get_object()
        # print("INSTANCE ID :::", instance.id)
        data = {
            "item_data": ItemSerializer(instance).data,
            "item_expense": []
        }
        items = ExpenseItem.objects.filter(item_id=instance.id)
        for item in items:
            # print("ITEM :::", item.expense_id.id)
            transaction = Transaction.objects.get(expense_id__id=item.expense_id.id)
            # print("TRANSACTION :::", transaction)
            item_data = ExpenseItemSerializer(item).data
            transaction_data = TransactionSerializer(transaction).data

            data["item_expense"].append({
                "expense_data": item_data,
                "transaction": transaction_data
            })

        return Response(data)


class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all().order_by('-id').distinct()
    serializer_class = ExpenseSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'category_id':['exact'],
        'category_id__name':['icontains'],
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
                         "transaction":t_serializers.data})

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
            # print("Expense Failed to save")
            return Response(expenseSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        transaction['expense_id'] = expenseSerializer.data['id']
        transactionSerializer = TransactionSerializer(data=transaction)
        if transactionSerializer.is_valid():
            transactionSerializer.save()
        else:
            # print("Transaction Failed to save")
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

    def update(self, request, pk=None, *args, **kwargs):
        expense_data = request.data.get('expense_data', None)
        # print("EXPENSE ::", expense_data)
        transaction_data = request.data.get('transaction_data', None)
        # print("TRANSACTION ::", transaction_data)
        items = request.data.get('item_data', None)
        # print("ITEMS ::", items)
        delete_items = request.data.get('delete_item', None)
        # print("DELETE ::", delete_items)
        # print("--------------------------------------")

        expense = Expense.objects.get(pk=pk)
        # print("EXPENSE :::", expense)
        e_serializer = ExpenseSerializer(expense, data=expense_data, partial=True)
        if e_serializer.is_valid():
            e_serializer.save()
        else:
            return Response(e_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # print("--------------------------------------")
        transaction_id = transaction_data['id']
        # print("TRANSACTION ID :::", transaction_id)
        transaction = Transaction.objects.get(pk=transaction_id)
        # print("TRANSACTION :::", transaction)
        t_serializer = TransactionSerializer(transaction, data=transaction_data, partial=True)
        if t_serializer.is_valid():
            t_serializer.save()
        else:
            return Response(t_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # print("--------------------------------------")
        if delete_items is not None:
            for delete_item in delete_items:
                print("ONE ITEM :::", delete_item)
                d_item = ExpenseItem.objects.get(id=delete_item)
                d_item.delete()

        # print("--------------------------------------")
        if items is not None:
            for item in items:
                # print("ONE ITEM ::::", item)
                # print("ITEM ID ::::", item['id'])
                if item['id'] == '':
                    # print(":::: NEW ITEM ::::")
                    item.pop('id')
                    ni_serializer = ExpenseItemSerializer(data=item)
                    if ni_serializer.is_valid():
                        ni_serializer.save()
                    else:
                        return Response(ni_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    # print("--------------------------------------")
                else:
                    # print(":::: OLD ITEM ::::")
                    o_item = ExpenseItem.objects.get(id=item['id'])
                    oi_serializer = ExpenseItemSerializer(o_item, data=item, partial=True)
                    if oi_serializer.is_valid():
                        oi_serializer.save()
                    else:
                        return Response(oi_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response({
            "expense_data": e_serializer.data
        })


class ExpenseItemViewSet(viewsets.ModelViewSet):
    queryset = ExpenseItem.objects.all().order_by('-id').distinct()
    serializer_class = ExpenseItemSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        # 'category_id__user_id__id':['exact'],
        # 'category_id__name':['icontains'],
        'expense_id__id':['exact'],
        'expense_id__date':['exact'],
        'expense_id__amount':['icontains'],
        'item_id__id':['exact'],
        'item_id__name':['exact'],
        'item_id__price':['exact'],
        'amount':['icontains'],
    }

