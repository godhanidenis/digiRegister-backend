from rest_framework import serializers

from expense.serializers import ExpenseSerializer
from .models import *

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"


class StudioDetailsSerializer(serializers.ModelSerializer):
    # user = UserSerializer(source="user_id", read_only=True)
    class Meta:
        model = StudioDetails
        fields = "__all__"


class CustomerSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Customer
        fields = "__all__"


class InventorySerializer(serializers.ModelSerializer):
    # user = UserSerializer(source="user_id", read_only=True)
    class Meta:
        model = Inventory
        fields = "__all__"


class StaffSerializer(serializers.ModelSerializer):
    # user = UserSerializer(source="user_id", read_only=True)
    studiodetails = StudioDetailsSerializer(source="studio_id", read_only=True)
    class Meta:
        model = Staff
        fields = "__all__"


class StaffSkillSerializer(serializers.ModelSerializer):
    inventory = InventorySerializer(source="inventory_id", read_only=True)
    staff = StaffSerializer(source="staff_id", read_only=True)
    class Meta:
        model = StaffSkill
        fields = "__all__"


class EventSerializer(serializers.ModelSerializer):
    # user = UserSerializer(source="user_id", read_only=True)
    class Meta:
        model = Event
        fields = "__all__"


# class CategorySerializer(serializers.ModelSerializer):
#     # user = UserSerializer(source="user_id", read_only=True)
#     class Meta:
#         model = Category
#         fields = "__all__"


# class ItemSerializer(serializers.ModelSerializer):
#     category = CategorySerializer(source="category_id", read_only=True)
#     class Meta:
#         model = Item
#         fields = "__all__"


# class QuotationSerializer(serializers.ModelSerializer):
#     # user = UserSerializer(source="user_id", read_only=True)
#     customer = CustomerSerializer(source="customer_id", read_only=True)
#     event = EventSerializer(source="event_id", read_only=True)
#     class Meta:
#         model = Quotation
#         fields = "__all__"



class QuotationSerializer(serializers.ModelSerializer):
    # user = UserSerializer(source="user_id", read_only=True)
    customer = CustomerSerializer(source="customer_id", read_only=True)
    # event = EventSerializer(source="event_id", read_only=True)
    class Meta:
        model = Quotation
        fields = "__all__"

class EventDaySerializer(serializers.ModelSerializer):
    # quotation = QuotationSerializer(source="quotation_id", read_only=True)
    class Meta:
        model = EventDay
        fields = "__all__"

class InventoryDetailsSerializer(serializers.ModelSerializer):
    # eventday = EventDaySerializer(source="eventday_id", read_only=True)
    inventory = InventorySerializer(source="inventory_id", read_only=True)
    class Meta:
        model = InventoryDetails
        fields = "__all__"

class EventDetailsSerializer(serializers.ModelSerializer):
    # eventday = EventDaySerializer(source="eventday_id", read_only=True)
    # quotation = QuotationSerializer(source="quotation_id", read_only=True)
    event = EventSerializer(source="event_id", read_only=True)
    class Meta:
        model = EventDetails
        fields = "__all__"

class ExposureDetailsSerializer(serializers.ModelSerializer):
    # eventdetails = EventDetailsSerializer(source="eventdetails_id", read_only=True)
    staff = StaffSerializer(source="staff_id", read_only=True)
    class Meta:
        model = ExposureDetails
        fields = "__all__"



class TransactionSerializer(serializers.ModelSerializer):
    # quotation = QuotationSerializer(source="quotation_id", read_only=True)
    expense = ExpenseSerializer(source="expense_id", read_only=True)
    class Meta:
        model = Transaction
        fields = "__all__"
