from django.shortcuts import render
from django.db.models import Sum
from django.http import  HttpResponse

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from app.utils import convert_time_utc_to_local
from .models import *
from .serializers import *
from .pagination import MyPagination
from .resource import *

from decouple import config
import pandas as pd
import boto3
import uuid
import os

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

    def update(self, request, pk=None, *args, **kwargs):
        # print(" POST DATA ::", request.data)
        user = User.objects.get(pk=pk)
        # print("USER ::", user)
        old_pic = f"digi_profile_pic/{os.path.basename(user.profile_pic)}" if user.profile_pic else None
        # print("OLD PIC URL :: ", old_pic)

        if 'password' in request.data:
            # print("PASSWORD ::", request.data['password'])
            # user.password = request.data['password']
            user.set_password(request.data['password'])
            user.save()
            request.data.pop('password')

        if 'profile_pic' in request.data:
            # print("::: PROFILE PIC :::")
            bucket_name = config('wasabisys_bucket_name')
            region = config('wasabisys_region')
            s3 = boto3.client('s3',
                          endpoint_url=config('wasabisys_endpoint_url'),
                          aws_access_key_id=config('wasabisys_access_key_id'),
                          aws_secret_access_key=config('wasabisys_secret_access_key')
                          )
            
            if old_pic:
                s3.delete_object(
                            Bucket = bucket_name, 
                            Key=old_pic
                            )
            
            file = request.data['profile_pic']
            file_name = f"digi_profile_pic/{uuid.uuid4().hex}.jpg"

            s3.upload_fileobj(file, bucket_name, file_name)

            s3_file_url = f"https://s3.{region}.wasabisys.com/{bucket_name}/{file_name}"
            # print("S3 File URL :: ",s3_file_url)
            request.data['profile_pic'] = s3_file_url

        # print("UPDATED DATA :: ",request.data)
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.data)


class StudioDetailsViewSet(viewsets.ModelViewSet):
    queryset = StudioDetails.objects.all().order_by('-id').distinct()
    serializer_class = StudioDetailsSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'user_id__id':['exact'],
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
        'address':['icontains']
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
    # pagination_class = MyPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'user_id__id':['exact'],
        'full_name':['icontains'],
        'mobile_no':['icontains'],
        'email':['icontains'],
        # 'skill_id__id':['exact'],
        # 'skill_id__inventory_id__name':['icontains'],
    }

    def list(self, request):
        querysets = self.filter_queryset(self.get_queryset())
        # print("queryset ::", querysets)
        # print("LENGTH ::", len(querysets))
        data = []
        for queryset in querysets:
            # print("Queryset ::", queryset)
            # print("Queryset ID ::", queryset.id)
            q_skills = StaffSkill.objects.filter(staff_id__id=queryset.id)
            # print("QUERTSET Skills ::", q_skills)
            staff = StaffSerializer(queryset)
            skills = StaffSkillSerializer(q_skills, many=True)
            data.append({'staff': staff.data, 'skills': skills.data}) 
        # print("DATA ::::", data)
        # serializer = StaffSerializer(querysets, many=True)
        return Response({'data':data})

    def create(self, request, *args, **kwargs):
        staff = request.data.get('staff_data')
        # print("STAFF ::", staff)
        skills = request.data.get('skill_data')
        # print("SKILLS ::", skills)

        staffSerializer = StaffSerializer(data=staff)
        if staffSerializer.is_valid():
            staff_instance = staffSerializer.save() 

            staff_skill_instances = []
            staff_skill_serializer = StaffSkillSerializer()
            for skill in skills:
                # print("SKILL ::", skill)
                skill["staff_id"] = staff_instance.id
                # print("SKILL STAFF ID ::", skill["staff_id"])
                staff_skill_serializer = StaffSkillSerializer(data=skill)
                if staff_skill_serializer.is_valid():
                    staff_skill_instance = staff_skill_serializer.save()
                    staff_skill_instances.append(staff_skill_instance)
                else:
                    return Response(staff_skill_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            response_data = {
                'staff': staffSerializer.data,
                'skills': StaffSkillSerializer(staff_skill_instances, many=True).data
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        else:
            return Response(staffSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None, *args, **kwargs):
        staff_data = request.data.get('staff_data', None)
        # print("STAFF DATA :: ", staff_data)
        skills = request.data.get('skills', None)
        # print("SKILLS :: ", skills)
        delete_skills = request.data.get('delete_skills', None)
        # print("DELETE SKILLS :: ", delete_skills)
        # print("--------------------------------------")

        staff = Staff.objects.get(pk=pk)
        # print("STAFF :: ", staff)
        # print("--------------------------------------")

        s_serializer = StaffSerializer(staff, data=staff_data, partial=True)
        if s_serializer.is_valid():
            s_serializer.save()
        else:
            return Response(s_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        
        if delete_skills is not None:
            for delete_skill in delete_skills:
                # print("ONE DELETE SKILL ::",delete_skill)
                d_skill = StaffSkill.objects.get(id=delete_skill)
                d_skill.delete()
        # print("--------------------------------------")

        if skills is not None:
            for skill in skills:
                # print("ONE SKILL ::",skill)
                # print("STAFFSKILL ID ::", skill['id'])
                # print("===================")
                if skill['id'] == '':
                    # print("NEW SKILL")
                    skill.pop("id")
                    # print("SKILLLLL ::",skill)
                    ns_serializer = StaffSkillSerializer(data=skill)
                    if ns_serializer.is_valid():
                        ns_serializer.save()
                    else:
                        return Response(ns_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    # print("--------------------------------------")
                else:
                    # print("OLD SKILL")
                    o_skill = StaffSkill.objects.get(id=skill['id'])
                    os_serializer = StaffSkillSerializer(o_skill, data=skill, partial=True)
                    if os_serializer.is_valid():
                        os_serializer.save()
                    else:
                        return Response(os_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    # print("--------------------------------------")

        return Response({
            "staff_data":s_serializer.data,
            # "new_skill":ns_serializer.data,
            # "updated_skill":os_serializer.data
                         })


class StaffSkillViewSet(viewsets.ModelViewSet):
    queryset = StaffSkill.objects.all().order_by('-id').distinct()
    serializer_class = StaffSkillSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'staff_id__user_id':['exact'],
        'staff_id__full_name':['icontains'],
        'inventory_id__id':['exact'],
        'inventory_id__name':['icontains'],
        'price':['icontains']
    }


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
        'customer_id__mobile_no':['icontains'],
        'start_date':['exact'],
        'due_date':['exact'],
        'converted_on':['gt'],
        'event_venue':['icontains'],
        'is_converted': ['exact'],
        'payment_status':['exact'],
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        from_date = self.request.query_params.get('from_date')
        # print("FROM DATE :: ",from_date)
        to_date = self.request.query_params.get('to_date')
        # print("TO DATE :: ",to_date)

        if from_date and to_date:
            try:
                print("LENGTH :: ",len(queryset))
                queryset = queryset.filter(converted_on__range=[from_date, to_date])
                # return queryset
            except ValueError:
                pass

        return queryset

    def list(self, request):
        querysets = self.filter_queryset(self.get_queryset())
        paginator = MyPagination()  
        paginated_queryset = paginator.paginate_queryset(querysets, request)
        data = []
        for queryset in paginated_queryset:
            total_amount = Transaction.objects.filter(quotation_id=queryset.id).aggregate(Sum('amount'))['amount__sum']
            total_amount = total_amount if total_amount is not None else 0
            s_transaction = Transaction.objects.filter(quotation_id=queryset.id)
            serializers = QuotationSerializer(queryset)
            transaction = TransactionSerializer(s_transaction, many=True)
            payable_amount = queryset.final_amount - queryset.discount
            data.append({"quotation":serializers.data,
                         "transaction":transaction.data,
                         "payable_amount":payable_amount,
                         "received_amount":total_amount})

        return paginator.get_paginated_response(data)


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

    def create(self, request, *args, **kwargs):
        # print("POST DATA ::", request.data)
    
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        quotation_id = request.data.get('quotation_id')
        # print("Quotation ID ::", quotation_id)
        quotation = Quotation.objects.get(id=quotation_id)
        # print("Quotation ::", quotation)
        total_amount = Transaction.objects.filter(quotation_id=quotation_id).aggregate(Sum('amount'))['amount__sum']
        payable_amount = quotation.final_amount - quotation.discount

        # print("Final amount :::", quotation.final_amount)
        # print("Discount amount :::", quotation.discount)
        # print("Total amount :::", total_amount)
        # print("Payable amount :::",payable_amount)

        if payable_amount == total_amount:
            # print("PAID")
            quotation.payment_status = 'paid'
            quotation.save()
        else:
            # print("PENDING")
            quotation.payment_status = 'pending'
            quotation.save()

        return Response({"transaction_data":serializer.data,
                         "payable_amount":payable_amount,
                         "received_amount":total_amount})

    def update(self, request, pk=None, *args, **kwargs):
        # print("POST DATA ::", request.data)

        transaction = Transaction.objects.get(pk=pk)
        # print("DATA ::", transaction)
        t_serializer = TransactionSerializer(transaction, data=request.data, partial=True)
        if t_serializer.is_valid():
            t_serializer.save()
        else:
            return Response(t_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        quotation_id = transaction.quotation_id.id
        # print("Quotation ID ::", quotation_id)
        quotation = Quotation.objects.get(id=quotation_id)
        # print("Quotation ::", quotation)
        total_amount = Transaction.objects.filter(quotation_id=quotation_id).aggregate(Sum('amount'))['amount__sum']
        payable_amount = quotation.final_amount - quotation.discount

        # print("Final amount :::", quotation.final_amount)
        # print("Discount amount :::", quotation.discount)
        # print("Total amount :::", total_amount)
        # print("Payable amount :::",payable_amount)

        if payable_amount == total_amount:
            # print("PAID")
            quotation.payment_status = 'paid'
            quotation.save()
        else:
            # print("PENDING")
            quotation.payment_status = 'pending'
            quotation.save()

        return Response({"transaction_data":t_serializer.data,
                         "payable_amount":payable_amount,
                         "received_amount":total_amount})

    def destroy(self, request, pk=None, *args, **kwargs):
        transaction = Transaction.objects.get(pk=pk)
        transaction.delete()
        # print("DATA ::", transaction)
        
        quotation_id = transaction.quotation_id.id
        # print("Quotation ID ::", quotation_id)
        quotation = Quotation.objects.get(id=quotation_id)
        # print("Quotation ::", quotation)
        total_amount = Transaction.objects.filter(quotation_id=quotation_id).aggregate(Sum('amount'))['amount__sum']
        total_amount = total_amount if total_amount is not None else 0
        payable_amount = quotation.final_amount - quotation.discount

        # print("Final amount :::", quotation.final_amount)
        # print("Discount amount :::", quotation.discount)
        # print("Total amount :::", total_amount)
        # print("Payable amount :::",payable_amount)

        if payable_amount == total_amount:
            # print("PAID")
            quotation.payment_status = 'paid'
            quotation.save()
        else:
            # print("PENDING")
            quotation.payment_status = 'pending'
            quotation.save()

        return Response({"payable_amount":payable_amount,
                         "received_amount":total_amount})
    

class AmountReportViewSet(viewsets.ModelViewSet):
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
        'customer_id__mobile_no':['icontains'],
        'start_date':['exact'],
        'due_date':['exact'],
        'converted_on':['gt'],
        'event_venue':['icontains'],
        'is_converted': ['exact'],
        'payment_status':['exact'],
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        from_date = self.request.query_params.get('from_date')
        # print("FROM DATE :: ",from_date)
        to_date = self.request.query_params.get('to_date')
        # print("TO DATE :: ",to_date)

        if from_date and to_date:
            try:
                # print("LENGTH :: ",len(queryset))
                queryset = queryset.filter(converted_on__range=[from_date, to_date])
                # return queryset
            except ValueError:
                pass

        return queryset

    def list(self, request):
        querysets = self.filter_queryset(self.get_queryset())
        paid_amount = 0
        total = 0
        for queryset in querysets:
            total_amount = Transaction.objects.filter(quotation_id=queryset.id).aggregate(Sum('amount'))['amount__sum']
            total_amount = total_amount if total_amount is not None else 0
            s_transaction = Transaction.objects.filter(quotation_id=queryset.id)
            # serializers = QuotationSerializer(queryset)
            # transaction = TransactionSerializer(s_transaction, many=True)
            payable_amount = queryset.final_amount - queryset.discount
            
            paid_amount += total_amount
            total += payable_amount
        data = {
            "paid_amount":paid_amount,
            "total":total
        }
        return Response(data)


@api_view(['POST'])
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
                total_amount = Transaction.objects.filter(quotation_id=i.id).aggregate(Sum('amount'))['amount__sum']
                # transaction = Transaction.objects.get(quotation_id = i.id)
                # print("FINAL AMOUNT :: ",i.final_amount)
                # print("DISCOUNT :: ",i.discount)

                if (i.final_amount - i.discount) == total_amount:
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
                total_amount = Transaction.objects.filter(quotation_id=i.id).aggregate(Sum('amount'))['amount__sum']
                # transaction = Transaction.objects.get(quotation_id = i.id)
                # print("TRANSACTION :: ",total_amount)
                # print("FINAL AMOUNT :: ",i.final_amount)
                if (i.final_amount - i.discount) == total_amount:
                    report['completed'] += 1
                else:
                    report['not_completed'] += 1
            report['converted'] = len(converted)

        return Response(report)
    

class CustomerExport(viewsets.ReadOnlyModelViewSet):
    queryset = Customer.objects.all().order_by('-id').distinct()
    serializer_class = CustomerSerializer
    pagination_class = MyPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'user_id__id':['exact'],
        'full_name':['icontains'],
        'mobile_no':['icontains'],
        'email':['icontains'],
        'address':['icontains']
    }

    def list(self, request):
        queryset_obj = self.filter_queryset(self.get_queryset())
        customer_resource = CustomerResource()
        data_set = customer_resource.export(queryset_obj)
        print(":: DATA SET ::")
        print(data_set)

        file_name = data_set.xlsx
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        return HttpResponse(file_name, content_type=content_type)


class QuotationExport(viewsets.ReadOnlyModelViewSet):
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
        'customer_id__mobile_no':['icontains'],
        'start_date':['exact'],
        'event_venue':['icontains'],
        'is_converted': ['exact'],
        'payment_status':['exact'],
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        from_date = self.request.query_params.get('from_date')
        print("FROM DATE :: ",from_date)
        to_date = self.request.query_params.get('to_date')
        print("TO DATE :: ",to_date)

        if from_date and to_date:
            try:
                queryset = queryset.filter(converted_on__range=[from_date, to_date])
            except ValueError:
                pass

        return queryset

    def list(self, request):
        queryset_obj = self.filter_queryset(self.get_queryset())
        quotation_resource = QuotationResource()
        data_set = quotation_resource.export(queryset_obj)
        print(":: DATA SET ::")
        print(data_set)

        file_name = data_set.xlsx
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        return HttpResponse(file_name, content_type=content_type)
    
    def retrieve(self, request, *args, **kwarge):
        instance = self.get_object()
        print("INSTANCE :: ",instance)
        quotation_resource = QuotationResource()
        print("quotation_resource", quotation_resource)
        data_set = quotation_resource.export([instance])
        print(":: DATA SET ::")
        print(data_set)

        file_name = data_set.xlsx
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        return HttpResponse(file_name, content_type=content_type)


class TransactionExport(viewsets.ReadOnlyModelViewSet):
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

    def list(self, request):
        queryset_obj = self.filter_queryset(self.get_queryset())
        transaction_resource = TransactionResource()
        data_set = transaction_resource.export(queryset_obj)
        print(":: DATA SET ::")
        print(data_set)

        file_name = data_set.xlsx
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        return HttpResponse(file_name, content_type=content_type)
    
    def retrieve(self, request, *args, **kwarge):
        instance = self.get_object()
        print("INSTANCE :: ",instance)
        transaction_resource = TransactionResource()
        print("transaction_resource", transaction_resource)
        data_set = transaction_resource.export([instance])
        print(":: DATA SET ::")
        print(data_set)

        file_name = data_set.xlsx
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        return HttpResponse(file_name, content_type=content_type)
    

class InvoiceExport(viewsets.ReadOnlyModelViewSet):
    queryset = Quotation.objects.all().order_by('-id').distinct()
    serializer_class = QuotationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'user_id__id':['exact'],
        'customer_id__id':['exact'],
        'event_id__id':['exact'],
        'customer_id__full_name':['icontains'],
        'event_id__event_name':['icontains'],
        'customer_id__mobile_no':['icontains'],
        'start_date':['exact'],
        'event_venue':['icontains'],
        'is_converted': ['exact'],
        'payment_status':['exact'],
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        from_date = self.request.query_params.get('from_date')
        print("FROM DATE :: ",from_date)
        to_date = self.request.query_params.get('to_date')
        print("TO DATE :: ",to_date)

        if from_date and to_date:
            try:
                queryset = queryset.filter(converted_on__range=[from_date, to_date])
                print("queryset ::: ", queryset)
            except ValueError:
                pass

        return queryset

    def list(self, request):
        querysets = self.filter_queryset(self.get_queryset())
        # print("QUERYSET list :::",querysets)
        timezone = request.query_params.get("timezone")
        # print("TIME ZONE ::",timezone)
        data = []
        for queryset in querysets:
            # print("Quotation ID ::", queryset.id)
            s_transaction = Transaction.objects.filter(quotation_id=queryset.id)
            # print("s_transaction :: ", s_transaction)
            serializers = QuotationSerializer(queryset)
            transaction = TransactionSerializer(s_transaction, many=True)

            total_amount = Transaction.objects.filter(quotation_id=queryset.id).aggregate(Sum('amount'))['amount__sum']
            # print("TYPE ::", type(total_amount))
            # print("Amount ::",total_amount)
            total_amount = total_amount if total_amount is not None else 0
            # print("GGGG Amount ::",total_amount)
            # status = "Paid" if queryset.final_amount == total_amount else "Pending"
            data.append({"quotation":serializers.data,
                        "transaction":transaction.data,
                        "payable_amount":queryset.final_amount - queryset.discount,
                        "received_amount": total_amount ,
                        "pending_amount":queryset.final_amount - int(total_amount),
                        # "payment_status": status
                        })

        formatted_data = []

        for item in data:
            quotation = item['quotation']
            transaction = item['transaction']
            payable_amount = item['payable_amount']
            received_amount = item['received_amount']
            pending_amount = item['pending_amount']
            # payment_status = item['payment_status']

            print("TIMEEEEE :::",quotation['converted_on'])
            formatted_item = {
                "Invoice NO.": quotation['id'],
                "Customer ID": quotation['customer']['id'],
                "Customer Name": quotation['customer']['full_name'],
                "Event Name": quotation['event']['event_name'],
                # "event_venue": quotation['event_venue'],
                # "couple_name": quotation['couple_name'],
                # "start_date": quotation['start_date'],
                # "end_date": quotation['end_date'],
                "Created On": convert_time_utc_to_local(timezone, quotation['converted_on']),
                "due_date": quotation['due_date'],
                # "is_converted": quotation['is_converted'],
                # "json_data": quotation['json_data'],
                # "created_on": quotation['created_on'],
                "Total Amount (INR)": quotation['final_amount'],
                "Discount (INR)": quotation['discount'],
                "Final Amount (INR)": payable_amount,
                "Received Amount (INR)": received_amount,
                "Panding Amount (INR)": pending_amount,
                "Payment Status":quotation['payment_status']
                
            }
            
            for idx, transaction_item in enumerate(transaction, start=1):
                formatted_item[f"Transaction_{idx}_Date"] = transaction_item['date']
                formatted_item[f"Transaction_{idx}_Amount"] = transaction_item['amount']
                formatted_item[f"Transaction_{idx}_Notes"] = transaction_item['notes']
                
                # Add empty values for the other transactions (if any)
                for i in range(idx + 1, len(transaction) + 1): 
                    formatted_item[f"Transaction_{i}_Date"] = ""
                    formatted_item[f"Transaction_{i}_Amount"] = ""
                    formatted_item[f"Transaction_{i}_Notes"] = ""
            
            formatted_data.append(formatted_item)

        df = pd.DataFrame(formatted_data)
        # print(df)

        output_path = "output_data.xlsx"
        df.to_excel(output_path, index=False)
        # print(f"Excel file saved at {output_path}")

        with open(output_path, 'rb') as excel_file:
            response = HttpResponse(excel_file.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename=output_data.xlsx'
            return response
        
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        timezone = request.query_params.get("timezone")
        data = []
        s_transaction = Transaction.objects.filter(quotation_id=instance.id)
        serializers = QuotationSerializer(instance)
        transaction = TransactionSerializer(s_transaction, many=True)

        total_amount = Transaction.objects.filter(quotation_id=instance.id).aggregate(Sum('amount'))['amount__sum']
        total_amount = total_amount if total_amount is not None else 0
        status = "Paid" if instance.final_amount == total_amount else "Pending"
        print("STATUS :: ", status)
        data.append({
            "quotation": serializers.data,
            "transaction": transaction.data,
            "payable_amount": instance.final_amount - instance.discount,
            "received_amount": total_amount,
            "pending_amount":instance.final_amount - total_amount,
            # "payment_status": status
        })

        
        formatted_data = []  

        for item in data:
            quotation = item['quotation']
            transaction = item['transaction']
            payable_amount = item['payable_amount']
            received_amount = item['received_amount']
            pending_amount = item['pending_amount']
            # payment_status = item['payment_status']

            # print("TIMEEEEE :::",quotation['converted_on'])
            formatted_item = {
                "Invoice NO.": quotation['id'],
                "Customer ID": quotation['customer']['id'],
                "Customer Name": quotation['customer']['full_name'],
                "Event Name": quotation['event']['event_name'],
                # "event_venue": quotation['event_venue'],
                # "couple_name": quotation['couple_name'],
                # "start_date": quotation['start_date'],
                # "end_date": quotation['end_date'],
                "Created On": convert_time_utc_to_local(timezone, quotation['converted_on']),
                "due_date": quotation['due_date'],
                # "is_converted": quotation['is_converted'],
                # "json_data": quotation['json_data'],
                # "created_on": quotation['created_on'],
                "Total Amount (INR)": quotation['final_amount'],
                "Discount (INR)": quotation['discount'],
                "Final Amount (INR)": payable_amount,
                "Received Amount (INR)": received_amount,
                "Pending Amount (INR)": pending_amount,
                "Payment Status":quotation['payment_status']
            }
            
            for idx, transaction_item in enumerate(transaction, start=1):
                formatted_item[f"Transaction_{idx}_Date"] = transaction_item['date']
                formatted_item[f"Transaction_{idx}_Amount"] = transaction_item['amount']
                formatted_item[f"Transaction_{idx}_Notes"] = transaction_item['notes']
                
                # Add empty values for the other transactions (if any)
                for i in range(idx + 1, len(transaction) + 1): 
                    formatted_item[f"Transaction_{i}_Date"] = ""
                    formatted_item[f"Transaction_{i}_Amount"] = ""
                    formatted_item[f"Transaction_{i}_Notes"] = ""
            
            formatted_data.append(formatted_item)


        df = pd.DataFrame(formatted_data)
        output_path = "single_object_output.xlsx"
        df.to_excel(output_path, index=False)

        with open(output_path, 'rb') as excel_file:
            response = HttpResponse(excel_file.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename=single_object_output.xlsx'
            return response
