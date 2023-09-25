from rest_framework import serializers
from .models import *

class CategorySerializer(serializers.ModelSerializer):
    # user = UserSerializer(source="user_id", read_only=True)
    class Meta:
        model = Category
        fields = "__all__"


class ItemSerializer(serializers.ModelSerializer):
    # category = CategorySerializer(source="category_id", read_only=True)
    class Meta:
        model = Item
        fields = "__all__"
    

class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = "__all__"


class ExpenseItemSerializer(serializers.ModelSerializer):
    # expense = ExpenseSerializer(source="expense_id", read_only=True)
    # category = CategorySerializer(source="category_id", read_only=True)
    item = ItemSerializer(source="item_id", read_only=True)
    class Meta:
        model = ExpenseItem
        fields = "__all__"
