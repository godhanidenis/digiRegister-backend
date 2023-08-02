from rest_framework import serializers
from .models import *

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"


class CustomerSerializer(serializers.ModelSerializer):
    user = UserSerializer(source="user_id", read_only=True)
    class Meta:
        model = Customer
        fields = "__all__"


class InventorySerializer(serializers.ModelSerializer):
    user = UserSerializer(source="user_id", read_only=True)
    class Meta:
        model = Inventory
        fields = "__all__"


class SkillSerializer(serializers.ModelSerializer):
    inventory = InventorySerializer(source="inventory_id", read_only=True)
    class Meta:
        model = Skill
        fields = "__all__"


class StaffSerializer(serializers.ModelSerializer):
    # user = UserSerializer(source="user_id", read_only=True)
    skill = SkillSerializer(source="skill_id", read_only=True)
    class Meta:
        model = Staff
        fields = "__all__"


class EventSerializer(serializers.ModelSerializer):
    user = UserSerializer(source="user_id", read_only=True)
    class Meta:
        model = Event
        fields = "__all__"


class QuotationSerializer(serializers.ModelSerializer):
    # user = UserSerializer(source="user_id", read_only=True)
    customer = CustomerSerializer(source="customer_id", read_only=True)
    event = EventSerializer(source="event_id", read_only=True)
    class Meta:
        model = Quotation
        fields = "__all__"


class TransactionSerializer(serializers.ModelSerializer):
    quotation = QuotationSerializer(source="quotation_id", read_only=True)
    class Meta:
        model = Transaction
        fields = "__all__"