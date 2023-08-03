from django.shortcuts import render
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import *
from .serializers import *
from .pagination import MyPagination

# Create your views here.

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-id').distinct()
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields ={
        'full_name':['icontains'],
        'mobile_no':['icontains'],
        'email':['icontains'],
        'address':['icontains']
    }

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all().order_by('-id').distinct()
    serializer_class = CustomerSerializer
    pagination_class = MyPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'user_id__id':['exact'],
        'full_name':['icontains'],
        'mobile_no':['icontains'],
        'email':['icontains'],
        # 'address':['icontains']
    }

class InventoryViewSet(viewsets.ModelViewSet):
    queryset = Inventory.objects.all().order_by('-id').distinct()
    serializer_class = InventorySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'user_id__id':['exact'],
        'type':['exact'],
        'name':['icontains']
    }


class StaffViewSet(viewsets.ModelViewSet):
    queryset = Staff.objects.all().order_by('-id').distinct()
    serializer_class = StaffSerializer
    pagination_class = MyPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'user_id__id':['exact'],
        'full_name':['icontains'],
        'mobile_no':['icontains'],
        'email':['icontains'],
        # 'skill_id__id':['exact'],
        # 'skill_id__inventory_id__name':['icontains'],
    }


class StaffSkillViewSet(viewsets.ModelViewSet):
    queryset = StaffSkill.objects.all().order_by('-id').distinct()
    serializer_class = StaffSkillSerializer
    # filter_backends = [DjangoFilterBackend]
    # filterset_fields = {
    #     'inventory_id__user_id__id':['exact'],
    #     'inventory_id__id':['exact'],
    #     'inventory_id__name':['icontains'],
    # }
class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all().order_by('-id').distinct()
    serializer_class = EventSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'user_id__id':['exact'],
        'event_name':['icontains']
    }

class QuotationViewSet(viewsets.ModelViewSet):
    queryset = Quotation.objects.all().order_by('-id').distinct()
    serializer_class = QuotationSerializer
    pagination_class = MyPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'user_id__id':['exact'],
        'customer_id__id':['exact'],
        'event_id__id':['exact'],
        'customer_id__full_name':['icontains'],
        'event_id__event_name':['icontains'],
        'is_converted': ['exact'],
    }

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all().order_by('-id').distinct()
    serializer_class = TransactionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'quotation_id__user_id__id':['exact'],
        'quotation_id__id':['exact'],
        'notes':['icontains'],
        'quotation_id__customer_id__full_name':['icontains'],
        'quotation_id__event_id__event_name':['icontains'],
    }


@api_view(['GET', 'POST'])
def Report(request):
    if request.method == 'POST':
        report = {}
        report['completed'] = 0
        report['not_completed'] = 0

        user = request.data.get('user_id')
        # print("USER ::", user)
        start_date = request.data.get('start_date', None)
        # print("START ::", start_date)
        end_date = request.data.get('end_date', None)
        # print("END ::", end_date)

        if start_date is None and end_date is None:
            not_converted = Quotation.objects.filter(user_id=user, is_converted=False)
            report['not_converted'] = len(not_converted)

            converted = Quotation.objects.filter(user_id=user, is_converted=True)
            # print("Converted :: ", converted)
            for i in converted:
                # print("I :: ",i.id)
                transaction = Transaction.objects.get(quotation_id = i.id)
                # print("TRANSACTION :: ",transaction.amount)

                if i.final_amount == transaction.amount:
                    report['completed'] += 1
                else:
                    report['not_completed'] += 1
            report['converted'] = len(converted)

        else:
            not_converted = Quotation.objects.filter(user_id=user, is_converted=False, created_on__range=[start_date, end_date])
            report['not_converted'] = len(not_converted)

            converted = Quotation.objects.filter(user_id=user, is_converted=True, created_on__range=[start_date, end_date])
            # print("Converted :: ", converted)
            for i in converted:
                # print("I :: ",i.id)
                transaction = Transaction.objects.get(quotation_id = i.id)
                # print("TRANSACTION :: ",transaction.amount)

                if i.final_amount == transaction.amount:
                    report['completed'] += 1
                else:
                    report['not_completed'] += 1
            report['converted'] = len(converted)

        return Response(report)