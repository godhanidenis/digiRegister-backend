from django.shortcuts import render
from django.db.models import Sum, Count, Q

from django.http import  HttpResponse
from django.db.models.functions import TruncMonth, TruncYear

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from app.utils import *
from .models import *
from .serializers import *
from .pagination import MyPagination
from .resource import *

from datetime import date
import datetime
import pytz
from decouple import config
import pandas as pd
import boto3
import uuid
import os
import requests
import base64

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

    def retrieve(self, request, *args, **kwarge):
        instance = self.get_object()
        terms = TermsAndConditions.objects.filter(user_id=instance.id)

        return Response({'user_data' : UserSerializer(instance).data,
                         'terms' : TermsAndConditionsSerializer(terms, many=True).data})

    def update(self, request, pk=None, *args, **kwargs):
        user = User.objects.get(pk=pk)
        old_pic = f"digi_profile_pic/{os.path.basename(user.profile_pic)}" if user.profile_pic else None
        old_signature = f"digi_signature/{os.path.basename(user.signature)}" if user.signature else None

        ## SET NEW PASSWORD AS PASSWORD ##
        if 'password' in request.data:
            user.set_password(request.data['password'])
            user.save()
            request.data.pop('password')

        bucket_name = config('wasabisys_bucket_name')
        region = config('wasabisys_region')
        s3 = boto3.client('s3',
                        endpoint_url=config('wasabisys_endpoint_url'),
                        aws_access_key_id=config('wasabisys_access_key_id'),
                        aws_secret_access_key=config('wasabisys_secret_access_key')
                        )

        ## ADD USER PROFILE PIC IN BUCKET ##
        if 'profile_pic' in request.data:
            profile_pic = request.data['profile_pic']
            # print("profile_pic ::: ",profile_pic ,"type ::: ",type(profile_pic))

            if profile_pic == '':
                print("profile_pic is Null")
                # DELETE OLD PIC FORM BUCKET #
                if old_pic:
                    s3.delete_object(
                                Bucket = bucket_name, 
                                Key=old_pic
                                )
            else:
                print("profile_pic is not Null")
                # DELETE OLD PIC FORM BUCKET #
                if old_pic:
                    s3.delete_object(
                                Bucket = bucket_name, 
                                Key=old_pic
                                )
                
                file = request.data['profile_pic']
                file_name = f"digi_profile_pic/{uuid.uuid4().hex}.jpg"

                # ADD NEW PIC IN BUCKET #
                s3.upload_fileobj(file, bucket_name, file_name)

                s3_file_url = f"https://s3.{region}.wasabisys.com/{bucket_name}/{file_name}"
                request.data['profile_pic'] = s3_file_url

        ## ADD USER SIGNATURE IN BUCKET ##
        if 'signature' in request.data:
            signature = request.data['signature']
            # print("signature ::: ",signature ,"type ::: ",type(signature))
            
            if signature == '':
                print("Signature is Null")
                # DELETE OLD SIGNATURE FORM BUCKET #
                if old_signature:
                    s3.delete_object(
                                Bucket = bucket_name, 
                                Key=old_signature
                                )
            else:
                print("Signature is not Null")
                # DELETE OLD SIGNATURE FORM BUCKET #
                if old_signature:
                    s3.delete_object(
                                Bucket = bucket_name, 
                                Key=old_signature
                                )
                
                file = request.data['signature']
                file_name = f"digi_signature/{uuid.uuid4().hex}.jpg"

                # ADD NEW PIC IN BUCKET #
                s3.upload_fileobj(file, bucket_name, file_name)

                s3_file_url = f"https://s3.{region}.wasabisys.com/{bucket_name}/{file_name}"
                request.data['signature'] = s3_file_url

        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.data)


class TermsAndConditionsViewSet(viewsets.ModelViewSet):
    queryset = TermsAndConditions.objects.all().order_by('-id').distinct()
    serializer_class = TermsAndConditionsSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields ={
        'user_id__id':['exact'],
    }


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


    def list(self, request):
        querysets = self.filter_queryset(self.get_queryset())
        paginator = MyPagination()  
        paginated_queryset = paginator.paginate_queryset(querysets, request)
        data = []
        for queryset in paginated_queryset:
            total_amount = Balance.objects.filter(customer_id=queryset.id).aggregate(Sum('amount'))['amount__sum']
            data.append({'customer': CustomerSerializer(queryset).data,
                         'total_amount': total_amount })
        
        return paginator.get_paginated_response(data)


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
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'user_id__id':['exact'],
        'full_name':['icontains'],
        'mobile_no':['icontains'],
        'email':['icontains'],
        'is_eposure':['exact'],
    }

    def list(self, request):
        querysets = self.filter_queryset(self.get_queryset())
        data = []
        for queryset in querysets:
            # q_skills = StaffSkill.objects.filter(staff_id__id=queryset.id)
            total_amount = Balance.objects.filter(staff_id=queryset.id).aggregate(Sum('amount'))['amount__sum']
            # staff = StaffSerializer(queryset)
            # skills = StaffSkillSerializer(q_skills, many=True)

            data.append({'staff': StaffSerializer(queryset).data, 
                        #  'skills': StaffSkillSerializer(q_skills, many=True).data,
                         'total_amount': total_amount}) 
            
        return Response(data)

    def retrieve(self, request, *args, **kwarge):
        instance = self.get_object()
        staff_id = instance.id
        staffskill = StaffSkill.objects.filter(staff_id=staff_id)
        data = {
            "staff_data" : StaffSerializer(instance).data,
            "staffskill_data" : StaffSkillSerializer(staffskill, many=True).data
        }

        return Response(data)

    def create(self, request, *args, **kwargs):
        staff = request.data.get('staff_data')
        skills = request.data.get('skill_data')

        staffSerializer = StaffSerializer(data=staff)
        if staffSerializer.is_valid():
            staff_instance = staffSerializer.save() 

            staff_skill_instances = []
            staff_skill_serializer = StaffSkillSerializer()
            for skill in skills:
                skill["staff_id"] = staff_instance.id
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
        skills = request.data.get('skills', None)
        delete_skills = request.data.get('delete_skills', None)

        ## UPDATE STAFF DATA ##
        staff = Staff.objects.get(pk=pk)
        s_serializer = StaffSerializer(staff, data=staff_data, partial=True)
        if s_serializer.is_valid():
            s_serializer.save()
        else:
            return Response(s_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        ## DELETE SKILL FOR THAT STAFF ##
        if delete_skills is not None:
            for delete_skill in delete_skills:
                d_skill = StaffSkill.objects.get(id=delete_skill)
                d_skill.delete()

        ## ADD AND UPDATE SKILL FOR THAT STAFF##
        if skills is not None:
            for skill in skills:
                if skill['id'] == '':
                    # ADD NEW SKILL FOR STAFF #
                    skill.pop("id")
                    ns_serializer = StaffSkillSerializer(data=skill)
                    if ns_serializer.is_valid():
                        ns_serializer.save()
                    else:
                        return Response(ns_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                else:
                    # UPDATE OLD SIKLL  #
                    o_skill = StaffSkill.objects.get(id=skill['id'])
                    os_serializer = StaffSkillSerializer(o_skill, data=skill, partial=True)
                    if os_serializer.is_valid():
                        os_serializer.save()
                    else:
                        return Response(os_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response({"staff_data":s_serializer.data})


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
        # 'user_id__id':['exact'],
        'customer_id__id':['exact'],
        'customer_id__full_name':['icontains'],
        'customer_id__mobile_no':['icontains'],
        'due_date':['exact'],
        'invoice_type':['exact'],
        'converted_on':['gt'],
        'payment_status':['exact'],
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        from_date = self.request.query_params.get('from_date')
        to_date = self.request.query_params.get('to_date')

        if from_date and to_date:
            try:
                # print("LENGTH :: ",len(queryset))
                queryset = queryset.filter(converted_on__range=[from_date, to_date])
            except ValueError:
                pass

        return queryset

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # print("Instance ::", instance)
        # print("Instance ID ::", instance.id)

        return Response(quotation_get(instance.id))

        # data = {
        #     "quotation_data": QuotationSerializer(instance).data, 
        #     "datas": []
        #     }

        # eventdays = EventDay.objects.filter(quotation_id=instance.id)
        # # print("EventDays ::", eventdays)
        # for eventday in eventdays:
        #     eventday_data = {
        #         "event_day": EventDaySerializer(eventday).data,
        #         "event_details": [],
        #         "description": []
        #     }

        #     eventdetails = EventDetails.objects.filter(eventday_id=eventday.id)
        #     # print("EventDetails :: ", eventdetails)
        #     for eventdetail in eventdetails:
        #         eventday_data["event_details"].append(EventDetailsSerializer(eventdetail).data)

        #     inventorydetails = InventoryDetails.objects.filter(eventday_id = eventday.id)
        #     # print("inventorydetails :: ",inventorydetails)
            
        #     for inventorydetail in inventorydetails:
        #         exposuredetails = ExposureDetails.objects.filter(inventorydetails_id=inventorydetail.id)
        #         # print("exposuredetails :: ",exposuredetails)
        #         # exposure_details_list = []

        #         # grouped_exposure_details = exposuredetails.values('staff_id','inventorydetails_id','price').annotate(event_ids_list=ArrayAgg('eventdetails_id'))
        #         # exposure = {}

        #         # for entry in grouped_exposure_details:
        #         #     exposure = {
        #         #     "staff_id" : entry['staff_id'],
        #         #     "inventorydetails_id" : entry['inventorydetails_id'],
        #         #     "event_ids_list" : entry['event_ids_list'],
        #         #     "price" : entry['price'],
        #         #     }
        #         #     exposure_details_list.append(exposure)

        #         eventday_data["description"].append({"inventory_details": InventoryDetailsSerializer(inventorydetail).data,
        #                                              "exposure_details": ExposureDetailsSerializer(exposuredetails, many=True).data})
                
        #     data["datas"].append(eventday_data)

        # transaction_data = Transaction.objects.get(quotation_id=instance.id)
        # # print("Transaction data :: ", transaction_data)
        # data['transaction_data'] = TransactionSerializer(transaction_data).data

        # print(data)
        # return Response(data)

    def create(self, request, *args, **kwargs): 
        quotation =request.data['quotation_data']
        # print("quotation ::", quotation)
        datas = request.data['datas']
        # print("datas ::", datas)
        transaction = request.data['transaction_data']
        # print("TRANSACTION :::", transaction)
        linktransaction_data = request.data.get('linktransaction_data', None)
        # print("link_transaction_data :: ", linktransaction_data)

        ### FOR ADD QUOTATION DATA ###
        quotationSerializer = QuotationSerializer(data=quotation)
        if quotationSerializer.is_valid():
            quotation_instance = quotationSerializer.save()
        else:
            return Response(quotationSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        final_evnetday_data = []
        final_eventdetails_data = []
        final_inventorydetails_data = []
        final_exposuredetails_data = []

        for data in datas:
            ### FOR ADD EVENT DAY DATA ###
            # print("DATA ::",data)
            eventdate_data = {'event_date': data['event_date'],
                              'quotation_id':quotation_instance.id}
            # print("Event Date Data ::",eventdate_data)
            eventdaySerializer = EventDaySerializer(data=eventdate_data)
            if eventdaySerializer.is_valid():
                eventday_instance = eventdaySerializer.save()
                final_evnetday_data.append(eventday_instance)
            else:
                return Response(eventdaySerializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            ### FOR ADD EVENT DETAILS DATA ###
            eventdetails_datas = data['event_details']
            # print("Event Details ::",eventdetails_datas)

            for eventdetails_data in eventdetails_datas:
                # print("Single Event Details ::",eventdetails_data)

                eventdetails_data['eventday_id'] = eventday_instance.id
                eventdetails_data['quotation_id'] = quotation_instance.id

                # print("EventDetials Data ::",eventdetails_data)
                eventdetailsSerializer = EventDetailsSerializer(data=eventdetails_data)
                if eventdetailsSerializer.is_valid():
                    eventdetails_instance = eventdetailsSerializer.save()
                    final_eventdetails_data.append(eventdetails_instance)
                else:
                    return Response(eventdetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            descriptions = data['descriptions']
            # print("Descriptions ::", descriptions)
            for description in descriptions:
                # print("Single Description ::", description)
                ### FOR INVENTORY DETAILS DATA ###
                inventorydetails_data = {
                    'inventory_id':description.pop('inventory_id'),
                    'price':description.pop('price'),
                    'qty':description.pop('qty'),
                    'profit':description.pop('profit'),
                    'eventday_id':eventday_instance.id
                }
                
                # print("InventoryDetails Data ::", inventorydetails_data)
                inventorydetailsSerializer = InventoryDetailsSerializer(data=inventorydetails_data)
                if inventorydetailsSerializer.is_valid():
                    inventorydetails_instance = inventorydetailsSerializer.save()
                    final_inventorydetails_data.append(inventorydetails_instance)
                else:
                    return Response(inventorydetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                inventory = Inventory.objects.get(pk=inventorydetails_data['inventory_id'])
                # print("INVENTORY ::", inventory)
                if inventory.type == 'service':

                    ### FOR EXPOSURE DETAILS DATA ###
                    exposuredetails = description.get('exposure', None)
                    # print("EXPOSUREDETAILS ::",exposuredetails)
                    if exposuredetails is not None:
                        for exposuredetail in exposuredetails:
                            evnetdetials =[]
                            # print("Single exposure ::",exposuredetail)
                            allocations = exposuredetail['allocation']
                            # print("Allocations ::",allocations)
                            for allocation in allocations:
                                # print("Single allocation ::",allocation)
                                for single_eventdetails in final_eventdetails_data:
                                    # print("Single eventdetail ::",single_eventdetails)
                                    event_id = single_eventdetails.event_id.id
                                    # print("Event id ::",event_id)
                                    if event_id == int(allocation):
                                        evnetdetials.append(single_eventdetails.id)

                            # print("Event Detail List ::", evnetdetials)
                            exposuredetails_data = {
                                'staff_id':exposuredetail['staff_id'],
                                'price':exposuredetail['price'],
                                'eventdetails':evnetdetials,
                                'inventorydetails_id':inventorydetails_instance.id
                            }
                            # print("ExposureDetails Data ::", exposuredetails_data)
                            exposuredetailsSerializer = ExposureDetailsSerializer(data=exposuredetails_data)
                            if exposuredetailsSerializer.is_valid():
                                exposuredetails_instance = exposuredetailsSerializer.save()
                                final_exposuredetails_data.append(exposuredetails_instance)
                            else:
                                return Response(exposuredetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)                    
                    
                    # print("FINAL Exposure Details DATA :::",final_exposuredetails_data)

        ### FOR ADD TRANSACTION DATA ###
        if transaction['is_converted'] == 'true':
            # print("EVENT SALE")
            transaction['type'] = 'event_sale'
        else:
            transaction['type'] = 'estimate'
        transaction['quotation_id'] = quotation_instance.id
        transaction['customer_id'] = quotation_instance.customer_id.id
        transactionSerializer = TransactionSerializer(data = transaction)
        if transactionSerializer.is_valid():
            transaction_instance = transactionSerializer.save()
        else:
            return Response(transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        if transaction['is_converted'] == 'true':
            new_amount = transaction_instance.total_amount - transaction_instance.recived_or_paid_amount
            print("New Amount ::: ", new_amount)
            balance_amount(quotation_instance.customer_id.id, None, 0 , new_amount, transaction_instance.type)

        ### CHANGE IN CUSTOMER'S BALANCE AMOUNT BASE ON RESCIVED OR PAID AMOUNT
        # advance_amount = transaction.get('advance_amount', None)
        # # print("advance_amount ::: ",advance_amount)
        # if advance_amount is not None:
        #     # print("CHANGE IN BALANCE BASE ON RECIVED OR PAID AMOUNT")
        #     try:
        #         balance = Balance.objects.get(customer_id = transaction_instance.customer_id.id)
        #     except:
        #         balance = None
        #     # print("balance ::: ",balance)
        #     if balance is None:
        #         balance_data = {
        #             'customer_id': transaction_instance.customer_id.id,
        #             'amount': advance_amount
        #         }
        #         # print("Balance DATA ::: ", balance_data)
        #         balanceSerializer = BalanceSerializer(data = balance_data)
        #         if balanceSerializer.is_valid():
        #             balanceSerializer.save()
        #         else:
        #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
        #     else:
        #         balance_data = {
        #             'customer_id': transaction_instance.customer_id.id,
        #             'amount': balance.amount - float(advance_amount)
        #         }
        #         # print("Balance DATA ::: ", balance_data)
        #         balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
        #         if balanceSerializer.is_valid():
        #             balanceSerializer.save()
        #         else:
        #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

        ### CHANGE IN CUSTOMER'S BALANCE AMOUNT BASE ON SETTLED AMOUNT
        # settled_amount = transaction.get('settled_amount', None)
        # print("settled_amount ::: ",settled_amount)
        # if settled_amount is not None:
        #     # print("CHANGE IN BALANCE BASE ON RECIVED OR PAID AMOUNT")
        #     try:
        #         balance = Balance.objects.get(customer_id = transaction_instance.customer_id.id)
        #     except:
        #         balance = None
        #     # print("balance ::: ",balance)
        #     if balance is None:
        #         balance_data = {
        #             'customer_id': transaction_instance.customer_id.id,
        #             'amount': settled_amount
        #         }
        #         # print("Balance DATA ::: ", balance_data)
        #         balanceSerializer = BalanceSerializer(data = balance_data)
        #         if balanceSerializer.is_valid():
        #             balanceSerializer.save()
        #         else:
        #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
        #     else:
        #         balance_data = {
        #             'customer_id': transaction_instance.customer_id.id,
        #             'amount': balance.amount - float(settled_amount)
        #         }
        #         # print("Balance DATA ::: ", balance_data)
        #         balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
        #         if balanceSerializer.is_valid():
        #             balanceSerializer.save()
        #         else:
        #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)


        ### LINK TRNASACTION 
        if transaction['is_converted'] == 'true' and linktransaction_data is not None:
            link_transaction(transaction_instance.id, linktransaction_data)

        ### ADD BILL FOR EXOISURE ###
        if transaction['is_converted'] == 'true':
            # print("final_exposuredetails_data :: ",final_exposuredetails_data)
            finall_instance = []
            for i in final_exposuredetails_data:
                # print("iiiii :: ",i)
                # print("ID :: ",i.id)
                # print("Staff ID :::",i.staff_id.id)
                # print("Price :::",i.price)

                i_transaction_data = {
                    'user_id':transaction['user_id'],
                    'type' : "event_purchase",
                    'staff_id' : i.staff_id.id,
                    # 'date' : "",
                    'total_amount' : i.price,
                    # 'quotation_id':copy_quotation_instance.id,
                    'exposuredetails_id':i.id,
                    'date': date.today()
                    # 'status' : "",
                }
                i_transactionSerializer = TransactionSerializer(data=i_transaction_data)
                if i_transactionSerializer.is_valid():
                    t_instance = i_transactionSerializer.save()
                    finall_instance.append(t_instance)
                else:
                    return Response(i_transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                new_amount = t_instance.total_amount - t_instance.recived_or_paid_amount
                print("New Amount ::: ", new_amount)
                balance_amount(None, t_instance.staff_id.id, 0 , new_amount, transaction_instance.type)

                ## ADD BALANCE AMOUNT FOR STAFF
                # try:
                #     balance = Balance.objects.get(staff_id=t_instance.staff_id.id)
                # except:
                #     balance = None
                # # print("BALANCE :: ",balance)
                # if balance is None:
                #     balance_data = {
                #         'staff_id' : t_instance.staff_id.id,
                #         'amount' : -float(t_instance.total_amount)
                #     }
                #     # print("Balance Data :: ", balance_data)
                #     balanceSerializer = BalanceSerializer(data=balance_data)
                #     if balanceSerializer.is_valid():
                #         balanceSerializer.save()
                #     else:
                #         return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                # else:
                #     balance_data = {
                #         'staff_id' : t_instance.staff_id.id,
                #         'amount' : balance.amount - float(t_instance.total_amount)
                #     }
                #     # print("Balance Data :: ", balance_data)
                #     balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                #     if balanceSerializer.is_valid():
                #         balanceSerializer.save()
                #     else:
                #         return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # print("FINAL INSTANCE :: ", finall_instance)

        # return Response({
        #     "quotation_data":QuotationSerializer(quotation_instance).data,
        #     "eventday_data":EventDaySerializer(final_evnetday_data, many=True).data,
        #     "eventdetails_data":EventDetailsSerializer(final_eventdetails_data, many=True).data,
        #     "inventorydetails_data":InventoryDetailsSerializer(final_inventorydetails_data, many=True).data,
        #     "exposuredetails_data":ExposureDetailsSerializer(final_exposuredetails_data, many=True).data,
        #     "transaction_data":TransactionSerializer(transaction_instance).data})

        # print("quotation_instance.id :: ",quotation_instance.id)
        return Response(quotation_get(quotation_instance.id))

    def update(self, request, pk=None, *args, **kwargs):
        quotation_data = request.data.get('quotation_data', None)
        # print("Quotation data :", quotation_data)
        copy_quotation_data = quotation_data
        # print("Copy Quotation data :", copy_quotation_data)
        datas = request.data.get('datas', None)
        # print("Datas :", datas)
        copy_datas = datas
        # print("COPY DATAS ::", copy_datas)
        delete_exposures = request.data.get('delete_exposure', None)
        # print("Delete Exposure :", delete_exposures)
        delete_inventorys = request.data.get('delete_inventory', None)
        # print("Delete Inventory :", delete_inventorys)
        delete_events = request.data.get('delete_event', None)
        # print("Delete Event :", delete_events)
        delete_eventdays = request.data.get('delete_eventday', None)
        # print("Delete Eventday :", delete_eventdays)
        transaction_data = request.data.get('transaction_data', None)
        # print("Transaction Data :", transaction_data)
        linktransaction_data = request.data.get('linktransaction_data', None)
        # print("link_transaction_data :: ", linktransaction_data)

        transaction = Transaction.objects.get(quotation_id = pk)
        # print("Transaction :", transaction)
        old_amount = transaction.total_amount - transaction.recived_or_paid_amount
        # print("transaction.is_converted ::",type(transaction.is_converted) , transaction.is_converted)
        # print("GGGGG ::",transaction.is_converted == False)

        ### NOT CONVERTED TRANSACTION ###
        if transaction.is_converted == False:
            # print("NOT CONVERTED TRANSACTION")
            convert_status = transaction_data['is_converted']
            # print("*************************************************")
            ### FOR UPDATE QUOTATION DATA ###
            quotation = Quotation.objects.get(pk=pk)
            # print("Quotation ::", quotation)
            q_serializer = QuotationSerializer(quotation, data=quotation_data, partial=True)
            if q_serializer.is_valid():
                quotation_instance = q_serializer.save()
                # print("Quotation Instance saved ::", quotation_instance)
            else:
                return Response(q_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            final_eventdetails_data = []
            final_inventorydetails_data = []
            final_exposuredetails_data = []
            
            # print("*************************************************")
            ### FOR ADD AND UPDATE OTHER DATA ### 
            if datas is not None:
                for data in datas:

                    ### FOR ADD AND UPDATE EVENT DAY ###
                    eventdate_data = {
                        'id': data['id'],
                        'event_date': data['event_date'],
                        'quotation_id':quotation_instance.id
                    }

                    if eventdate_data['id'] == '':
                        # print(":::: NEW DAY ADDED ::::")
                        eventdate_data.pop('id')
                        # print("eventdate_data ::", eventdate_data)
                        n_eventdaySerializer = EventDaySerializer(data=eventdate_data)
                        if n_eventdaySerializer.is_valid():
                            eventday_instance = n_eventdaySerializer.save()
                        else:
                            return Response(n_eventdaySerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                        
                        ### FOR ADD EVENT DETAILS DATA ###
                        eventdetails_datas = data['event_details']
                        # print("eventdetails_datas ::", eventdetails_datas)
                        for eventdetails_data in eventdetails_datas:
                            eventdetails_data['eventday_id'] = eventday_instance.id
                            eventdetails_data['quotation_id'] = quotation_instance.id
                            # print("eventdetails_data ::", eventdetails_data)
                            eventdetailsSerializer = EventDetailsSerializer(data=eventdetails_data)
                            if eventdetailsSerializer.is_valid():
                                eventdetails_instance = eventdetailsSerializer.save()
                                final_eventdetails_data.append(eventdetails_instance)
                            else:
                                return Response(eventdetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                        
                        descriptions = data['descriptions']
                        # print("descriptions ::", descriptions)
                        for description in descriptions:
                            ### FOR INVENTORY DETAILS DATA ###
                            inventorydetails_data = {
                                'inventory_id':description['inventory_id'],
                                'price':description['price'],
                                'qty':description['qty'],
                                'profit':description['profit'],
                                'eventday_id':eventday_instance.id
                            }
                            # print("inventorydetails_data ::", inventorydetails_data)
                            inventorydetailsSerializer = InventoryDetailsSerializer(data=inventorydetails_data)
                            if inventorydetailsSerializer.is_valid():
                                inventorydetails_instance = inventorydetailsSerializer.save()
                                final_inventorydetails_data.append(inventorydetails_instance)
                            else:
                                return Response(inventorydetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                            
                            inventory = Inventory.objects.get(pk=inventorydetails_data['inventory_id'])
                            # print("INVENTORY ::", inventory)
                            if inventory.type == 'service':

                                ### FOR EXPOSURE DETAILS DATA ###
                                exposuredetails = description.get('exposure', None)
                                if exposuredetails is not None:
                                    # print("exposuredetails ::", exposuredetails)
                                    for exposuredetail in exposuredetails:
                                        evnetdetials =[]
                                        # print("Single exposure ::",exposuredetail)
                                        allocations = exposuredetail['allocation']
                                        # print("Allocations ::",allocations)
                                        for allocation in allocations:
                                            # print("Single allocation ::",allocation)
                                            for single_eventdetails in final_eventdetails_data:
                                                # print("Single eventdetail ::",single_eventdetails)
                                                event_id = single_eventdetails.event_id.id
                                                # print("Event id ::",event_id)
                                                if event_id == int(allocation):
                                                    evnetdetials.append(single_eventdetails.id)

                                        # print("Event Detail List ::", evnetdetials)
                                        exposuredetails_data = {
                                            'staff_id':exposuredetail['staff_id'],
                                            'price':exposuredetail['price'],
                                            'eventdetails':evnetdetials,
                                            'inventorydetails_id':inventorydetails_instance.id
                                        }
                                        # print("ExposureDetails Data ::", exposuredetails_data)
                                        exposuredetailsSerializer = ExposureDetailsSerializer(data=exposuredetails_data)
                                        if exposuredetailsSerializer.is_valid():
                                            exposuredetails_instance = exposuredetailsSerializer.save()
                                            final_exposuredetails_data.append(exposuredetails_instance)
                                        else:
                                            return Response(exposuredetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)                    
                            
                    else:
                        # print("*************************************************")

                        # print(":::: OLD DAY UPDATED ::::")
                        o_eventday = EventDay.objects.get(pk=eventdate_data['id'])
                        # print("o_eventday ::::: ",o_eventday)
                        # print("eventdate_data ::::: ",eventdate_data)
                        o_eventdaySerializer = EventDaySerializer(o_eventday, data=eventdate_data, partial=True)
                        if o_eventdaySerializer.is_valid():
                            o_eventdaySerializer.save()
                        else:
                            return Response(o_eventdaySerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                                
                        eventdetails_datas = data['event_details']
                        for eventdetails_data in eventdetails_datas:
                            # print("Event Details Data :::::",eventdetails_data)

                            if eventdetails_data['id'] == '':
                                # print("::: NEW EVENT DETAILS :::")
                                eventdetails_data.pop('id')
                                # print("eventdetails_data ::::: ",eventdetails_data)
                                n_eventdetailsSerializer = EventDetailsSerializer(data=eventdetails_data)
                                if n_eventdetailsSerializer.is_valid():
                                    eventdetails_instance = n_eventdetailsSerializer.save()
                                    final_eventdetails_data.append(eventdetails_instance)
                                    # print("Event Details Instance saved :::", eventdetails_instance)
                                else:
                                    return Response(n_eventdetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                            else:
                                # print("::: OLD EVENT DETAILS :::")
                                # print("eventdetails_data :::::",eventdetails_data)
                                o_eventdetail = EventDetails.objects.get(pk=eventdetails_data['id'])
                                o_eventdetailsSerializer = EventDetailsSerializer(o_eventdetail, data=eventdetails_data, partial=True)
                                if o_eventdetailsSerializer.is_valid():
                                    eventdetails_instance = o_eventdetailsSerializer.save()
                                    final_eventdetails_data.append(eventdetails_instance)
                                    # print("Event Details Instance saved :::::", eventdetails_instance)
                                else:
                                    return Response(o_eventdetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                                
                        descriptions = data['descriptions']
                        # print("Descriptions :::::", descriptions)

                        for description in descriptions:
                            inventorydetails_data = {
                                'id':description['id'],
                                'inventory_id':description['inventory_id'],
                                'price':description['price'],
                                'qty':description['qty'],
                                'profit':description['profit'],
                                'eventday_id':description['eventday_id']
                            }

                            if inventorydetails_data['id'] == '':
                                # print("::: NEW INVENTORY DETAILS :::")
                                inventorydetails_data.pop('id')
                                # print("inventorydetails_data :::::",inventorydetails_data)
                                n_inventorydetailsSerializer = InventoryDetailsSerializer(data=inventorydetails_data)
                                if n_inventorydetailsSerializer.is_valid():
                                    inventorydetails_instance = n_inventorydetailsSerializer.save()
                                    final_inventorydetails_data.append(inventorydetails_instance)
                                    # print("Inventory Details Instance saved ::::::", inventorydetails_instance)
                                else:
                                    return Response(n_inventorydetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                            else:
                                # print("::: OLD INVENTORY DETAILS :::")
                                # print("inventorydetails_data ::::: ",inventorydetails_data)
                                o_inventorydetails = InventoryDetails.objects.get(pk=inventorydetails_data['id'])
                                # print("o_inventorydetails ::::: ",o_inventorydetails)
                                o_inventorydetailsSerializer = InventoryDetailsSerializer(o_inventorydetails, data=inventorydetails_data, partial=True)
                                if o_inventorydetailsSerializer.is_valid():
                                    inventorydetails_instance = o_inventorydetailsSerializer.save()
                                    final_inventorydetails_data.append(inventorydetails_instance)
                                    # print("Inventory Details Instance saved ::::::", inventorydetails_instance)
                                else:
                                    return Response(o_inventorydetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                                
                            inventory = Inventory.objects.get(pk=inventorydetails_data['inventory_id'])
                            # print("INVENTORY ::", inventory)
                            if inventory.type == 'service':

                                exposuredetails = description.get('exposure', None)
                                # print("exposuredetails ::::: ",exposuredetails)
                                if exposuredetails is not None:
                                    for exposuredetail in exposuredetails:
                                        evnetdetials =[]
                                        allocations = exposuredetail['allocation']
                                        for allocation in allocations:
                                            for single_eventdetails in final_eventdetails_data:
                                                event_id = single_eventdetails.event_id.id
                                                if event_id == int(allocation):
                                                    evnetdetials.append(single_eventdetails.id)

                                        exposuredetails_data = {
                                            'id':exposuredetail['id'],
                                            'staff_id':exposuredetail['staff_id'],
                                            'price':exposuredetail['price'],
                                            'inventorydetails_id':inventorydetails_instance.id,
                                            'eventdetails':evnetdetials
                                        }
                                        if exposuredetails_data['id'] == '':
                                            # print("::: NEW EXPOSURE DETAILS :::")
                                            # print("exposuredetails_data :::::",exposuredetails_data)
                                            exposuredetails_data.pop('id')
                                            n_exposuredetailsSerializer = ExposureDetailsSerializer(data=exposuredetails_data)
                                            if n_exposuredetailsSerializer.is_valid():
                                                exposuredetails_instance = n_exposuredetailsSerializer.save()
                                                final_exposuredetails_data.append(exposuredetails_instance)
                                                # print("Inventory Details Instance saved ::::::::", exposuredetails_instance)
                                            else:
                                                return Response(n_exposuredetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                                        else:
                                            # print("::: NEW OLD DETAILS :::")
                                            # print("exposuredetails_data ::::: ",exposuredetails_data)
                                            o_exposuredetails = ExposureDetails.objects.get(pk=exposuredetails_data['id'])
                                            # print("o_exposuredetails ::::: ",o_exposuredetails)
                                            o_exposuredetailsSerializer = ExposureDetailsSerializer(o_exposuredetails, data=exposuredetails_data, partial=True)
                                            if o_exposuredetailsSerializer.is_valid():
                                                exposuredetails_instance = o_exposuredetailsSerializer.save()
                                                final_exposuredetails_data.append(exposuredetails_instance)
                                                # print("Inventory Details Instance saved ::::::::", exposuredetails_instance)
                                            else:
                                                return Response(o_exposuredetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # print("*************************************************")
            ### DELETE EXPOSURES DETAILS ###
            if delete_exposures is not None:
                for delete_exposure in delete_exposures:
                    # print("Delete Exposure ::", delete_exposure)

                    d_exposure = ExposureDetails.objects.get(pk=delete_exposure)
                    # print("Exposure ::", d_exposure)
                    d_exposure.delete()

            # print("*************************************************")
            ### DELETE INVENTORYS DETAILS ###
            if delete_inventorys is not None:
                for delete_inventory in delete_inventorys:
                    # print("Delete Inventory ::", delete_inventory)
                    d_inventory = InventoryDetails.objects.get(pk=delete_inventory)
                    # print("Inventory ::", d_inventory)
                    d_inventory.delete()
            
            # print("*************************************************")
            ### DELETE EVENTS DETAILS ###
            if delete_events is not None:
                for delete_event in delete_events:
                    # print("Delete Event ::", delete_event)
                    d_event = EventDetails.objects.get(pk=delete_event)
                    # print("EVENT ::", d_event)
                    d_event.delete()
            
            # print("*************************************************")
            ### DELETE EVENT DAY DETAILS ###
            if delete_eventdays is not None:
                for delete_eventday in delete_eventdays:
                    # print("Delete Event Day ::", delete_eventday)
                    d_eventday = EventDay.objects.get(pk=delete_eventday)
                    # print("EVENT DAY ::", d_eventday)
                    d_eventday.delete()

            # print("*************************************************")
            ## UPDATE TRANSACTON DETAILS ###
            if transaction_data is not None:
                # print("Transaction data :::", transaction_data)
                # print("Transaction ID :::", transaction_data['id'])
                
                # print("Transaction :::", transaction)
                if convert_status == 'true':
                    transaction_data['is_converted'] = True
                else:
                    transaction_data['is_converted'] = False
                transaction_data['type'] = 'estimate'
                t_serializer = TransactionSerializer(transaction, data=transaction_data, partial=True)
                if t_serializer.is_valid():
                    t_serializer.save()
                else:
                    return Response(t_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            # print("COPY COPY COPY COPY")
            # print("COPY DATA ::::", copy_datas)
            ### MAKE A COPY OF TRANSACTION AND QUOTATION ###
            if convert_status == 'true':
                # print("COPY COPY COPY COPY")
                ### QUOTATION COPY ###
                copy_quotationSerializer = QuotationSerializer(data=copy_quotation_data)
                # print("quotationSerializer :::", copy_quotationSerializer)
                if copy_quotationSerializer.is_valid():
                    copy_quotation_instance = copy_quotationSerializer.save()
                    # print("quotation_instance :::", quotation_instance)
                else:
                    return Response(copy_quotationSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                copy_final_eventdetails_data = []
                copy_final_inventorydetails_data = []
                copy_final_exposuredetails_data = []

                # print("COPY DATASSSSS :::",copy_datas)
                for copy_data in copy_datas:
                    # print("SINGL DATAAAA :::",copy_data)
                    ### FOR ADD EVENT DAY DATA ###
                    copy_eventdate_data = {
                        'event_date': copy_data['event_date'],
                        'quotation_id':copy_quotation_instance.id
                    }
                    # print("eventdate_data :::", copy_eventdate_data)
                    copy_eventdaySerializer = EventDaySerializer(data=copy_eventdate_data)
                    if copy_eventdaySerializer.is_valid():
                        copy_eventday_instance = copy_eventdaySerializer.save()
                        # print("eventday_instance :::", copy_eventday_instance)
                    else:
                        return Response(copy_eventdaySerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    
                    ### FOR ADD EVENT DETAILS DATA ###
                    copy_eventdetails_datas = copy_data['event_details']
                    # print("eventdetails_datas :::", copy_eventdetails_datas)
                    for copy_eventdetails_data in copy_eventdetails_datas:
                        copy_eventdetails_data['eventday_id'] = copy_eventday_instance.id
                        copy_eventdetails_data['quotation_id'] = copy_quotation_instance.id
                        # print("eventdetails_data :::", copy_eventdetails_data)
                        copy_eventdetailsSerializer = EventDetailsSerializer(data=copy_eventdetails_data)
                        if copy_eventdetailsSerializer.is_valid():
                            copy_eventdetails_instance = copy_eventdetailsSerializer.save()
                            # print("eventdetails_instance :::", copy_eventdetails_instance)
                            copy_final_eventdetails_data.append(copy_eventdetails_instance)
                        else:
                            return Response(copy_eventdetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    
                    copy_descriptions = copy_data['descriptions']
                    # print("COPY descriptions :::", copy_descriptions)
                    for copy_description in copy_descriptions:
                        # print("COPY SINGAL description :::", copy_description)
                        ### FOR INVENTORY DETAILS DATA ###
                        copy_inventorydetails_data = {
                            'inventory_id':copy_description['inventory_id'],
                            'price':copy_description['price'],
                            'qty':copy_description['qty'],
                            'profit':copy_description['profit'],
                            'eventday_id':copy_eventday_instance.id
                        }
                        # print("inventorydetails_data :::", copy_inventorydetails_data)
                        copy_inventorydetailsSerializer = InventoryDetailsSerializer(data=copy_inventorydetails_data)
                        if copy_inventorydetailsSerializer.is_valid():
                            copy_inventorydetails_instance = copy_inventorydetailsSerializer.save()
                            # print("inventorydetails_instance :::", copy_inventorydetails_instance)
                            copy_final_inventorydetails_data.append(copy_inventorydetails_instance)
                        else:
                            return Response(copy_inventorydetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                        
                        copy_inventory = Inventory.objects.get(pk=copy_inventorydetails_data['inventory_id'])
                        # print("INVENTORY ::", copy_inventory)
                        if copy_inventory.type == 'service':

                            ### FOR EXPOSURE DETAILS DATA ###
                            copy_exposuredetails = copy_description.get('exposure', None)
                            if copy_exposuredetails is not None:
                                # print("exposuredetails :::", copy_exposuredetails)
                                for copy_exposuredetail in copy_exposuredetails:
                                    copy_evnetdetials =[]
                                    copy_allocations = copy_exposuredetail['allocation']
                                    # print("allocations :::", copy_allocations)
                                    for copy_allocation in copy_allocations:
                                        for copy_single_eventdetails in copy_final_eventdetails_data:
                                            copy_event_id = copy_single_eventdetails.event_id.id
                                            # print("event_id :::", copy_event_id)
                                            if copy_event_id == int(copy_allocation):
                                                copy_evnetdetials.append(copy_single_eventdetails.id)

                                    copy_exposuredetails_data = {
                                        'staff_id':copy_exposuredetail['staff_id'],
                                        'price':copy_exposuredetail['price'],
                                        'eventdetails':copy_evnetdetials,
                                        'inventorydetails_id':copy_inventorydetails_instance.id
                                    }
                                    # print("exposuredetails_data :::", copy_exposuredetails_data)
                                    copy_exposuredetailsSerializer = ExposureDetailsSerializer(data=copy_exposuredetails_data)
                                    if copy_exposuredetailsSerializer.is_valid():
                                        copy_exposuredetails_instance = copy_exposuredetailsSerializer.save()
                                        # print("exposuredetails_instance :::", copy_exposuredetails_instance)
                                        copy_final_exposuredetails_data.append(copy_exposuredetails_instance)
                                    else:
                                        return Response(copy_exposuredetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)                    
                                
                            # print("FINAL Exposure Details DATA :::",final_exposuredetails_data)

                ### TRANSACTION COPY ###
                # print("ADD TRANSACTION COPY")
                transaction_data.pop('id')
                transaction_data['is_converted'] = True
                transaction_data['type'] = 'event_sale'
                transaction_data['quotation_id'] = copy_quotation_instance.id
                transaction_data['customer_id'] = copy_quotation_instance.customer_id.id
                # print("Transaction Data :: ", transaction_data)
                copy_transactionSerializer = TransactionSerializer(data=transaction_data)
                if copy_transactionSerializer.is_valid():
                    copy_transaction_instance = copy_transactionSerializer.save()
                else:
                    return Response(copy_transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                # print("copy_transaction_instance :: ",copy_transaction_instance) 

                new_amount = copy_transaction_instance.total_amount - copy_transaction_instance.recived_or_paid_amount
                print("New Amount ::: ", new_amount)
                balance_amount(copy_transaction_instance.customer_id.id, None, 0 , new_amount, copy_transaction_instance.type)

                ## ADD TOTAL AMOUNT IN CUSTOMER'S BALANCE
                # print("ADD BALANCE")
                # try:
                #     balance = Balance.objects.get(customer_id = copy_transaction_instance.customer_id.id)
                # except:
                #     balance = None
                # # print("balance ::: ",balance)
                # if balance is None:
                #     balance_data = {
                #         'customer_id': copy_transaction_instance.customer_id.id,
                #         'amount': copy_transaction_instance.total_amount
                #     }
                #     # print("Balance DATA ::: ", balance_data)
                #     balanceSerializer = BalanceSerializer(data = balance_data)
                #     if balanceSerializer.is_valid():
                #         balanceSerializer.save()
                #     else:
                #         return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                # else:
                #     balance_data = {
                #         'customer_id': copy_transaction_instance.customer_id.id,
                #         'amount': balance.amount + float(copy_transaction_instance.total_amount)
                #     }
                #     # print("Balance DATA ::: ", balance_data)
                #     balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                #     if balanceSerializer.is_valid():
                #         balanceSerializer.save()
                #     else:
                #         return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

                ### CHANGE IN CUSTOMER'S BALANCE AMOUNT BASE ON RESCIVED OR PAID AMOUNT
                # advance_amount = transaction_data.get('advance_amount', None)
                # # print("advance_amount ::: ",advance_amount)
                # if advance_amount is not None:
                #     # print("CHANGE IN BALANCE BASE ON RECIVED OR PAID AMOUNT")
                #     try:
                #         balance = Balance.objects.get(customer_id = copy_transaction_instance.customer_id.id)
                #     except:
                #         balance = None
                #     # print("balance ::: ",balance)
                #     if balance is None:
                #         balance_data = {
                #             'customer_id': copy_transaction_instance.customer_id.id,
                #             'amount': advance_amount
                #         }
                #         # print("Balance DATA ::: ", balance_data)
                #         balanceSerializer = BalanceSerializer(data = balance_data)
                #         if balanceSerializer.is_valid():
                #             balanceSerializer.save()
                #         else:
                #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                #     else:
                #         balance_data = {
                #             'customer_id': copy_transaction_instance.customer_id.id,
                #             'amount': balance.amount - float(advance_amount)
                #         }
                #         # print("Balance DATA ::: ", balance_data)
                #         balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                #         if balanceSerializer.is_valid():
                #             balanceSerializer.save()
                #         else:
                #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

                ### CHANGE IN CUSTOMER'S BALANCE AMOUNT BASE ON SETTLED AMOUNT
                # settled_amount = transaction_data.get('settled_amount', None)
                # # print("settled_amount ::: ",settled_amount)
                # if settled_amount is not None:
                #     # print("CHANGE IN BALANCE BASE ON RECIVED OR PAID AMOUNT")
                #     try:
                #         balance = Balance.objects.get(customer_id = copy_transaction_instance.customer_id.id)
                #     except:
                #         balance = None
                #     # print("balance ::: ",balance)
                #     if balance is None:
                #         balance_data = {
                #             'customer_id': copy_transaction_instance.customer_id.id,
                #             'amount': settled_amount
                #         }
                #         # print("Balance DATA ::: ", balance_data)
                #         balanceSerializer = BalanceSerializer(data = balance_data)
                #         if balanceSerializer.is_valid():
                #             balanceSerializer.save()
                #         else:
                #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                #     else:
                #         balance_data = {
                #             'customer_id': copy_transaction_instance.customer_id.id,
                #             'amount': balance.amount - float(settled_amount)
                #         }
                #         # print("Balance DATA ::: ", balance_data)
                #         balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                #         if balanceSerializer.is_valid():
                #             balanceSerializer.save()
                #         else:
                #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

                ### LINK TRNASACTION 
                linktransaction_data = request.data.get('linktransaction_data', None)
                # print("link_transaction_data :: ", linktransaction_data)
                if linktransaction_data is not None:
                    link_transaction(copy_transaction_instance.id, linktransaction_data)

                ### ADD BILL FOR EXOISURE ###
                # print("copy_final_exposuredetails_data :: ",copy_final_exposuredetails_data)
                finall_instance = []
                for i in copy_final_exposuredetails_data:
                    # print("iiiii :: ",i)
                    # print("ID :: ",i.id)
                    # print("Staff ID :::",i.staff_id.id)
                    # print("Price :::",i.price)

                    i_transaction_data = {
                        'user_id': transaction.user_id.id,
                        'type' : "event_purchase",
                        'staff_id' : i.staff_id.id,
                        # 'date' : "",
                        'total_amount' : i.price,
                        # 'quotation_id':copy_quotation_instance.id,
                        'exposuredetails_id':i.id,
                        'date': date.today()
                        # 'status' : "",
                    }
                    i_transactionSerializer = TransactionSerializer(data=i_transaction_data)
                    if i_transactionSerializer.is_valid():
                        t_instance = i_transactionSerializer.save()
                        finall_instance.append(t_instance)
                    else:
                        return Response(i_transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    
                    new_amount = t_instance.total_amount - t_instance.recived_or_paid_amount
                    print("New Amount ::: ", new_amount)
                    balance_amount(None, t_instance.staff_id.id, 0 , new_amount, t_instance.type)

                    ## ADD BALANCE AMOUNT FOR STAFF
                    # try:
                    #     balance = Balance.objects.get(staff_id=t_instance.staff_id.id)
                    # except:
                    #     balance = None
                    # # print("BALANCE :: ",balance)
                    # if balance is None:
                    #     balance_data = {
                    #         'staff_id' : t_instance.staff_id.id,
                    #         'amount' : -float(t_instance.total_amount)
                    #     }
                    #     # print("Balance Data :: ", balance_data)
                    #     balanceSerializer = BalanceSerializer(data=balance_data)
                    #     if balanceSerializer.is_valid():
                    #         balanceSerializer.save()
                    #     else:
                    #         return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    # else:
                    #     balance_data = {
                    #         'staff_id' : t_instance.staff_id.id,
                    #         'amount' : balance.amount - float(t_instance.total_amount)
                    #     }
                    #     # print("Balance Data :: ", balance_data)
                    #     balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                    #     if balanceSerializer.is_valid():
                    #         balanceSerializer.save()
                    #     else:
                    #         return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

                    
                # print("FINAL INSTANCE :: ", finall_instance)
        
        ### CONVERTED TRANSACTION ###
        else:
            # print("CONVERTED TRANSACTION")
            quotation = Quotation.objects.get(pk=pk)
            # print("Quotation ::", quotation)
            q_serializer = QuotationSerializer(quotation, data=quotation_data, partial=True)
            if q_serializer.is_valid():
                quotation_instance = q_serializer.save()
                # print("Quotation Instance saved ::", quotation_instance)
            else:
                return Response(q_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            final_eventdetails_data = []
            final_inventorydetails_data = []
            final_exposuredetails_data = []
            
            # print("*************************************************")
            ### FOR ADD AND UPDATE OTHER DATA ### 
            if datas is not None:
                for data in datas:

                    ### FOR ADD AND UPDATE EVENT DAY ###
                    eventdate_data = {
                        'id': data['id'],
                        'event_date': data['event_date'],
                        'quotation_id':quotation_instance.id
                    }

                    if eventdate_data['id'] == '':
                        # print(":::: NEW DAY ADDED ::::")
                        eventdate_data.pop('id')
                        # print("eventdate_data ::", eventdate_data)
                        n_eventdaySerializer = EventDaySerializer(data=eventdate_data)
                        if n_eventdaySerializer.is_valid():
                            eventday_instance = n_eventdaySerializer.save()
                        else:
                            return Response(n_eventdaySerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                        
                        ### FOR ADD EVENT DETAILS DATA ###
                        eventdetails_datas = data['event_details']
                        # print("eventdetails_datas ::", eventdetails_datas)
                        for eventdetails_data in eventdetails_datas:
                            eventdetails_data['eventday_id'] = eventday_instance.id
                            eventdetails_data['quotation_id'] = quotation_instance.id
                            # print("eventdetails_data ::", eventdetails_data)
                            eventdetailsSerializer = EventDetailsSerializer(data=eventdetails_data)
                            if eventdetailsSerializer.is_valid():
                                eventdetails_instance = eventdetailsSerializer.save()
                                final_eventdetails_data.append(eventdetails_instance)
                            else:
                                return Response(eventdetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                        
                        descriptions = data['descriptions']
                        # print("descriptions ::", descriptions)
                        for description in descriptions:
                            ### FOR INVENTORY DETAILS DATA ###
                            inventorydetails_data = {
                                'inventory_id':description['inventory_id'],
                                'price':description['price'],
                                'qty':description['qty'],
                                'profit':description['profit'],
                                'eventday_id':eventday_instance.id
                            }
                            # print("inventorydetails_data ::", inventorydetails_data)
                            inventorydetailsSerializer = InventoryDetailsSerializer(data=inventorydetails_data)
                            if inventorydetailsSerializer.is_valid():
                                inventorydetails_instance = inventorydetailsSerializer.save()
                                final_inventorydetails_data.append(inventorydetails_instance)
                            else:
                                return Response(inventorydetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                            
                            inventory = Inventory.objects.get(pk=inventorydetails_data['inventory_id'])
                            # print("INVENTORY ::", inventory)
                            if inventory.type == 'service':

                                ### FOR EXPOSURE DETAILS DATA ###
                                exposuredetails = description.get('exposure', None)
                                # print("exposuredetails ::", exposuredetails)
                                if exposuredetails is not None:
                                    for exposuredetail in exposuredetails:
                                        evnetdetials =[]
                                        # print("Single exposure ::",exposuredetail)
                                        allocations = exposuredetail['allocation']
                                        # print("Allocations ::",allocations)
                                        for allocation in allocations:
                                            # print("Single allocation ::",allocation)
                                            for single_eventdetails in final_eventdetails_data:
                                                # print("Single eventdetail ::",single_eventdetails)
                                                event_id = single_eventdetails.event_id.id
                                                # print("Event id ::",event_id)
                                                if event_id == int(allocation):
                                                    evnetdetials.append(single_eventdetails.id)

                                        # print("Event Detail List ::", evnetdetials)
                                        exposuredetails_data = {
                                            'staff_id':exposuredetail['staff_id'],
                                            'price':exposuredetail['price'],
                                            'eventdetails':evnetdetials,
                                            'inventorydetails_id':inventorydetails_instance.id
                                        }
                                        # print("ExposureDetails Data ::", exposuredetails_data)
                                        exposuredetailsSerializer = ExposureDetailsSerializer(data=exposuredetails_data)
                                        if exposuredetailsSerializer.is_valid():
                                            exposuredetails_instance = exposuredetailsSerializer.save()
                                            final_exposuredetails_data.append(exposuredetails_instance)
                                        else:
                                            return Response(exposuredetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)                    
                            
                    else:
                        # print("*************************************************")

                        # print(":::: OLD DAY UPDATED ::::")
                        o_eventday = EventDay.objects.get(pk=eventdate_data['id'])
                        # print("o_eventday ::::: ",o_eventday)
                        # print("eventdate_data ::::: ",eventdate_data)
                        o_eventdaySerializer = EventDaySerializer(o_eventday, data=eventdate_data, partial=True)
                        if o_eventdaySerializer.is_valid():
                            o_eventdaySerializer.save()
                        else:
                            return Response(o_eventdaySerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                                
                        eventdetails_datas = data['event_details']
                        for eventdetails_data in eventdetails_datas:
                            # print("Event Details Data :::::",eventdetails_data)

                            if eventdetails_data['id'] == '':
                                # print("::: NEW EVENT DETAILS :::")
                                eventdetails_data.pop('id')
                                # print("eventdetails_data ::::: ",eventdetails_data)
                                n_eventdetailsSerializer = EventDetailsSerializer(data=eventdetails_data)
                                if n_eventdetailsSerializer.is_valid():
                                    eventdetails_instance = n_eventdetailsSerializer.save()
                                    final_eventdetails_data.append(eventdetails_instance)
                                    # print("Event Details Instance saved :::", eventdetails_instance)
                                else:
                                    return Response(n_eventdetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                            else:
                                # print("::: OLD EVENT DETAILS :::")
                                # print("eventdetails_data :::::",eventdetails_data)
                                o_eventdetail = EventDetails.objects.get(pk=eventdetails_data['id'])
                                o_eventdetailsSerializer = EventDetailsSerializer(o_eventdetail, data=eventdetails_data, partial=True)
                                if o_eventdetailsSerializer.is_valid():
                                    eventdetails_instance = o_eventdetailsSerializer.save()
                                    final_eventdetails_data.append(eventdetails_instance)
                                    # print("Event Details Instance saved :::::", eventdetails_instance)
                                else:
                                    return Response(o_eventdetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                                
                        descriptions = data['descriptions']
                        # print("Descriptions :::::", descriptions)

                        for description in descriptions:
                            inventorydetails_data = {
                                'id':description['id'],
                                'inventory_id':description['inventory_id'],
                                'price':description['price'],
                                'qty':description['qty'],
                                'profit':description['profit'],
                                'eventday_id':description['eventday_id']
                            }

                            if inventorydetails_data['id'] == '':
                                # print("::: NEW INVENTORY DETAILS :::")
                                inventorydetails_data.pop('id')
                                # print("inventorydetails_data :::::",inventorydetails_data)
                                n_inventorydetailsSerializer = InventoryDetailsSerializer(data=inventorydetails_data)
                                if n_inventorydetailsSerializer.is_valid():
                                    inventorydetails_instance = n_inventorydetailsSerializer.save()
                                    final_inventorydetails_data.append(inventorydetails_instance)
                                    # print("Inventory Details Instance saved ::::::", inventorydetails_instance)
                                else:
                                    return Response(n_inventorydetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                            else:
                                # print("::: OLD INVENTORY DETAILS :::")
                                # print("inventorydetails_data ::::: ",inventorydetails_data)
                                o_inventorydetails = InventoryDetails.objects.get(pk=inventorydetails_data['id'])
                                # print("o_inventorydetails ::::: ",o_inventorydetails)
                                o_inventorydetailsSerializer = InventoryDetailsSerializer(o_inventorydetails, data=inventorydetails_data, partial=True)
                                if o_inventorydetailsSerializer.is_valid():
                                    inventorydetails_instance = o_inventorydetailsSerializer.save()
                                    final_inventorydetails_data.append(inventorydetails_instance)
                                    # print("Inventory Details Instance saved ::::::", inventorydetails_instance)
                                else:
                                    return Response(o_inventorydetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                                
                            inventory = Inventory.objects.get(pk=inventorydetails_data['inventory_id'])
                            # print("INVENTORY ::", inventory)
                            if inventory.type == 'service':

                                exposuredetails = description['exposure']
                                # print("exposuredetails ::::: ",exposuredetails)
                                for exposuredetail in exposuredetails:
                                    evnetdetials =[]
                                    allocations = exposuredetail['allocation']
                                    for allocation in allocations:
                                        for single_eventdetails in final_eventdetails_data:
                                            event_id = single_eventdetails.event_id.id
                                            if event_id == int(allocation):
                                                evnetdetials.append(single_eventdetails.id)

                                    exposuredetails_data = {
                                        'id':exposuredetail['id'],
                                        'staff_id':exposuredetail['staff_id'],
                                        'price':exposuredetail['price'],
                                        'inventorydetails_id':inventorydetails_instance.id,
                                        'eventdetails':evnetdetials
                                    }
                                    if exposuredetails_data['id'] == '':
                                        # print("::: NEW EXPOSURE DETAILS :::")
                                        # print("exposuredetails_data :::::",exposuredetails_data)
                                        exposuredetails_data.pop('id')
                                        n_exposuredetailsSerializer = ExposureDetailsSerializer(data=exposuredetails_data)
                                        if n_exposuredetailsSerializer.is_valid():
                                            exposuredetails_instance = n_exposuredetailsSerializer.save()
                                            final_exposuredetails_data.append(exposuredetails_instance)
                                            # print("Inventory Details Instance saved ::::::::", exposuredetails_instance)
                                        else:
                                            return Response(n_exposuredetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                                    else:
                                        # print("::: NEW OLD DETAILS :::")
                                        # print("exposuredetails_data ::::: ",exposuredetails_data)
                                        o_exposuredetails = ExposureDetails.objects.get(pk=exposuredetails_data['id'])
                                        # print("o_exposuredetails ::::: ",o_exposuredetails)
                                        o_exposuredetailsSerializer = ExposureDetailsSerializer(o_exposuredetails, data=exposuredetails_data, partial=True)
                                        if o_exposuredetailsSerializer.is_valid():
                                            exposuredetails_instance = o_exposuredetailsSerializer.save()
                                            final_exposuredetails_data.append(exposuredetails_instance)
                                            # print("Inventory Details Instance saved ::::::::", exposuredetails_instance)
                                        else:
                                            return Response(o_exposuredetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # print("*************************************************")
            ### DELETE EXPOSURES DETAILS ###
            if delete_exposures is not None:
                for delete_exposure in delete_exposures:
                    # print("Delete Exposure ::", delete_exposure)
                    d_exposure = ExposureDetails.objects.get(pk=delete_exposure)
                    # print("Exposure ::", d_exposure)
                    exposure_bill = Transaction.objects.get(exposuredetails_id=delete_exposure)
                    print("exposure_bill ::", exposure_bill)

                    balance = Balance.objects.get(staff_id=d_exposure.staff_id.id)
                    print("balance ::", balance)
                    print("balance.amount ::", balance.amount)
                    balance.amount = balance.amount + exposure_bill.total_amount
                    print("New balance.amount ::", balance.amount)
                    balance.save()

                    d_exposure.delete()

            # print("*************************************************")
            ### DELETE INVENTORYS DETAILS ###
            if delete_inventorys is not None:
                for delete_inventory in delete_inventorys:
                    # print("Delete Inventory ::", delete_inventory)
                    d_inventory = InventoryDetails.objects.get(pk=delete_inventory)
                    # print("Inventory ::", d_inventory)
                    d_inventory.delete()
            
            # print("*************************************************")
            ### DELETE EVENTS DETAILS ###
            if delete_events is not None:
                for delete_event in delete_events:
                    # print("Delete Event ::", delete_event)
                    d_event = EventDetails.objects.get(pk=delete_event)
                    # print("EVENT ::", d_event)
                    d_event.delete()
            
            # print("*************************************************")
            ### DELETE EVENT DAY DETAILS ###
            if delete_eventdays is not None:
                for delete_eventday in delete_eventdays:
                    # print("Delete Event Day ::", delete_eventday)
                    d_eventday = EventDay.objects.get(pk=delete_eventday)
                    # print("EVENT DAY ::", d_eventday)
                    d_eventday.delete()

            # print("*************************************************")
            ## UPDATE TRANSACTON DETAILS ###
            if transaction_data is not None:
                # print("Transaction data :::", transaction_data)
                # print("Transaction ID :::", transaction_data['id'])
                
                # print("Transaction :::", transaction)
                # transaction_data['is_converted'] = False
                # transaction_data['status'] = 'estimate'

                # old_total_amount = float(transaction.total_amount)
                # print("old_total_amount ::: ",old_total_amount)

                # old_advance_amount = float(transaction.advance_amount)
                # print("old_advance_amount ::: ",old_advance_amount)

                # old_settled_amount = float(transaction.settled_amount)
                # print("old_settled_amount ::: ",old_settled_amount)

                t_serializer = TransactionSerializer(transaction, data=transaction_data, partial=True)
                if t_serializer.is_valid():
                    update_transaction = t_serializer.save()
                else:
                    return Response(t_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
                new_amount = update_transaction.total_amount - update_transaction.recived_or_paid_amount
                print("New Amount ::: ", new_amount)
                balance_amount(update_transaction.customer_id.id, None, old_amount , new_amount, update_transaction.type)

                ## CHANGES IN CUSTOMER BALANCE
                # new_total_amount = float(transaction_data.get('total_amount', None))
                # # print("new_total_amount ::: ",new_total_amount)
                # try:
                #     balance = Balance.objects.get(customer_id=transaction.customer_id.id)
                # except:
                #     balance = None

                # if balance is None:
                #     balance_data = {'customer_id': transaction.customer_id.id,
                #                     'amount': new_total_amount}
                #     # print("Balance DATA ::: ", balance_data)
                #     balanceSerializer = BalanceSerializer(data = balance_data)
                #     if balanceSerializer.is_valid():
                #         balanceSerializer.save()
                #     else:
                #         return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                # else:
                #     balance_data = {'customer_id': transaction.customer_id.id,
                #                     'amount': (balance.amount - old_total_amount) + new_total_amount}
                #     # print("Balance DATA ::: ", balance_data)
                #     balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                #     if balanceSerializer.is_valid():
                #         balanceSerializer.save()
                #     else:
                #         return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                

                ### CHANGE IN CUSTOMER'S BALANCE AMOUNT BASE ON RESCIVED OR PAID AMOUNT
                # new_advance_amount = transaction_data.get('advance_amount', None)
                # # print("new_advance_amount ::: ",new_advance_amount)
                # new_advance_amount = new_advance_amount if new_advance_amount is not None else 0
                # if new_advance_amount is not None:
                #     new_advance_amount = float(new_advance_amount)
                # try:
                #     balance = Balance.objects.get(customer_id=transaction.customer_id.id)
                # except:
                #     balance = None

                # if balance is None:
                #     balance_data = {'customer_id': transaction.customer_id.id,
                #                     'amount': new_advance_amount}
                #     # print("Balance DATA ::: ", balance_data)
                #     balanceSerializer = BalanceSerializer(data = balance_data)
                #     if balanceSerializer.is_valid():
                #         balanceSerializer.save()
                #     else:
                #         return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                # else:
                #     balance_data = {'customer_id': transaction.customer_id.id,
                #                     'amount': (balance.amount + old_advance_amount) - new_advance_amount}
                #     # print("Balance DATA ::: ", balance_data)
                #     balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                #     if balanceSerializer.is_valid():
                #         balanceSerializer.save()
                #     else:
                #         return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                ### CHANGE IN CUSTOMER'S BALANCE AMOUNT BASE ON SETTLED AMOUNT
                # new_settled_amount = transaction_data.get('settled_amount', None)
                # new_settled_amount = new_settled_amount if new_settled_amount is not None else 0
                # if new_settled_amount is not None:
                #     new_settled_amount = float(new_settled_amount)
                # # print("new_settled_amount ::: ",new_settled_amount)
                # try:
                #     balance = Balance.objects.get(customer_id=transaction.customer_id.id)
                # except:
                #     balance = None

                # if balance is None:
                #     balance_data = {'customer_id': transaction.customer_id.id,
                #                     'amount': new_settled_amount}
                #     # print("Balance DATA ::: ", balance_data)
                #     balanceSerializer = BalanceSerializer(data = balance_data)
                #     if balanceSerializer.is_valid():
                #         balanceSerializer.save()
                #     else:
                #         return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                # else:
                #     balance_data = {'customer_id': transaction.customer_id.id,
                #                     'amount': (balance.amount + old_settled_amount) - new_settled_amount}
                #     # print("Balance DATA ::: ", balance_data)
                #     balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                #     if balanceSerializer.is_valid():
                #         balanceSerializer.save()
                #     else:
                #         return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)


            ### LINK TRNASACTION 
            if linktransaction_data is not None:
                link_transaction(transaction_data['id'], linktransaction_data)

            # print("final_exposuredetails_data :: ",final_exposuredetails_data)
            finall_instance = []
            for i in final_exposuredetails_data:
                # print("iiiii :: ",i)
                # print("ID :: ",i.id)
                # print("Staff ID :::",i.staff_id.id)
                # print("Price :::",i.price)

                try:
                    bill = Transaction.objects.get(exposuredetails_id = i.id)
                    # print("Bill :",bill)
                    old_amount = bill.total_amount - bill.recived_or_paid_amount
                except:
                    bill = None

                i_transaction_data = {
                        'user_id': transaction.user_id.id,
                        'type' : "event_purchase",
                        'staff_id' : i.staff_id.id,
                        # 'date' : "",
                        'total_amount' : i.price,
                        # 'quotation_id':quotation_instance.id,
                        'exposuredetails_id':i.id,
                        'date': date.today(),
                        # 'status' : "",
                    }

                if bill is not None:
                    # print("OLD BILL")
                    i_transactionSerializer = TransactionSerializer(bill, data=i_transaction_data, partial=True)
                    if i_transactionSerializer.is_valid():
                        t_instance = i_transactionSerializer.save()
                        finall_instance.append(t_instance)
                    else:
                        return Response(i_transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    
                    new_amount = t_instance.total_amount - t_instance.recived_or_paid_amount
                    print("New Amount ::: ", new_amount)
                    balance_amount(None, t_instance.staff_id.id, old_amount, new_amount, t_instance.type)

                    ## ADD BALANCE AMOUNT FOR STAFF
                    # try:
                    #     balance = Balance.objects.get(staff_id=t_instance.staff_id.id)
                    # except:
                    #     balance = None
                    # # print("BALANCE :: ",balance)
                    # if balance is None:
                    #     balance_data = {
                    #         'staff_id' : t_instance.staff_id.id,
                    #         'amount' : - float(t_instance.total_amount)
                    #     }
                    #     # print("Balance Data :: ", balance_data)
                    #     balanceSerializer = BalanceSerializer(data=balance_data)
                    #     if balanceSerializer.is_valid():
                    #         balanceSerializer.save()
                    #     else:
                    #         return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    # else:
                    #     old_total_amount = bill.total_amount
                    #     # print("old_total_amount ::: ", old_total_amount)
                    #     new_total_amount = t_instance.total_amount
                    #     # print("new_total_amount ::: ", new_total_amount)
                    #     balance_data = {
                    #         'staff_id' : t_instance.staff_id.id,
                    #         'amount' : (balance.amount - old_total_amount) + new_total_amount
                    #         # 'amount' : balance.amount + float(advance_amount)
                    #     }
                    #     # print("Balance Data :: ", balance_data)
                    #     balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                    #     if balanceSerializer.is_valid():
                    #         balanceSerializer.save()
                    #     else:
                    #         return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                else:
                    # print("NEW BILL")
                    i_transactionSerializer = TransactionSerializer(data=i_transaction_data)
                    if i_transactionSerializer.is_valid():
                        t_instance = i_transactionSerializer.save()
                        finall_instance.append(t_instance)
                    else:
                        return Response(i_transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    
                    new_amount = t_instance.total_amount - t_instance.recived_or_paid_amount
                    print("New Amount ::: ", new_amount)
                    balance_amount(None, t_instance.staff_id.id, 0 , new_amount, t_instance.type)


                    ## ADD BALANCE AMOUNT FOR STAFF
                    # try:
                    #     balance = Balance.objects.get(staff_id=t_instance.staff_id.id)
                    # except:
                    #     balance = None
                    # # print("BALANCE :: ",balance)
                    # if balance is None:
                    #     balance_data = {
                    #         'staff_id' : t_instance.staff_id.id,
                    #         'amount' : -float(t_instance.total_amount)
                    #     }
                    #     # print("Balance Data :: ", balance_data)
                    #     balanceSerializer = BalanceSerializer(data=balance_data)
                    #     if balanceSerializer.is_valid():
                    #         balanceSerializer.save()
                    #     else:
                    #         return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    # else:
                    #     balance_data = {
                    #         'staff_id' : t_instance.staff_id.id,
                    #         'amount' : balance.amount - float(t_instance.total_amount)
                    #     }
                    #     # print("Balance Data :: ", balance_data)
                    #     balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                    #     if balanceSerializer.is_valid():
                    #         balanceSerializer.save()
                    #     else:
                    #         return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # print("FINAL INSTANCE :: ", finall_instance)

        return Response({"quotation_data":QuotationSerializer(quotation_instance).data,})
                        #  "quotation_copy":QuotationSerializer(copy_quotation_instance).data


class EventDayViewSet(viewsets.ModelViewSet):
    queryset = EventDay.objects.all().order_by('-id').distinct()
    serializer_class = EventDaySerializer


class InventoryDetailsViewSet(viewsets.ModelViewSet):
    queryset = InventoryDetails.objects.all().order_by('-id').distinct()
    serializer_class = InventoryDetailsSerializer


class EventDetailsViewSet(viewsets.ModelViewSet):
    queryset = EventDetails.objects.all().order_by('-id').distinct()
    serializer_class = EventDetailsSerializer


class ExposureDetailsViewSet(viewsets.ModelViewSet):
    queryset = ExposureDetails.objects.all().order_by('-id').distinct()
    serializer_class = ExposureDetailsSerializer


class InventoryDescriptionViewSet(viewsets.ModelViewSet):
    queryset = InventoryDescription.objects.all().order_by('-id').distinct()
    serializer_class = InventoryDescriptionSerializer

    def create(self, request, *args, **kwargs):
        inventory_datas = request.data['inventory_data']
        # print("Inventory Data :: ",inventory_datas)
        transaction_data = request.data['transaction_data']
        # print("Trnasaction Data :: ",transaction_data)
        linktransaction_data = request.data.get('linktransaction_data', None)
        # print("link_transaction_data :: ", linktransaction_data)

        all_instance = []
        inventorydescription_ids = []

        for inventory_data in inventory_datas:
            # print("Single Inventory Data :: ", inventory_data)

            inventorySerializer = InventoryDescriptionSerializer(data=inventory_data)
            if inventorySerializer.is_valid():
                inventory_instance = inventorySerializer.save()
                all_instance.append(inventory_instance)
            else:
                return Response(inventorySerializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            # print("Inventory Description ID ::", inventory_instance.id)
            inventorydescription_ids.append(inventory_instance.id)

        transaction_data['inventorydescription'] = inventorydescription_ids
        # print("Transaction Data ::", transaction_data)
        transactionSerializer = TransactionSerializer(data = transaction_data)
        if transactionSerializer.is_valid():
            transaction_instance = transactionSerializer.save()
        else:
            return Response(transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        customer_id = transaction_instance.customer_id.id if transaction_instance.customer_id is not None else None
        # print("customer_id :::",customer_id)
        staff_id = transaction_instance.staff_id.id if transaction_instance.staff_id is not None else None
        # print("staff_id :::",staff_id)
        
        new_amount = transaction_instance.total_amount - transaction_instance.recived_or_paid_amount
        print("New Amount ::: ", new_amount)
        balance_amount(customer_id, staff_id, 0, new_amount, transaction_instance.type)
        
        if linktransaction_data is not None:
            link_transaction(transaction_instance.id, linktransaction_data)

        # if transaction_instance.type == 'sale':
        #     ## ADD TOTAL AMOUNT IN CUSTOMER'S BALANCE
        #     try:
        #         balance = Balance.objects.get(customer_id = transaction_instance.customer_id.id)
        #     except:
        #         balance = None
        #     # print("balance ::: ",balance)
        #     if balance is None:
        #         balance_data = {
        #             'customer_id': transaction_instance.customer_id.id,
        #             'amount': transaction_instance.total_amount
        #         }
        #         # print("Balance DATA ::: ", balance_data)
        #         balanceSerializer = BalanceSerializer(data = balance_data)
        #         if balanceSerializer.is_valid():
        #             balanceSerializer.save()
        #         else:
        #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
        #     else:
        #         balance_data = {
        #             'customer_id': transaction_instance.customer_id.id,
        #             'amount': balance.amount + float(transaction_instance.total_amount)
        #         }
        #         # print("Balance DATA ::: ", balance_data)
        #         balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
        #         if balanceSerializer.is_valid():
        #             balanceSerializer.save()
        #         else:
        #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

        #     ### CHANGE IN CUSTOMER'S BALANCE AMOUNT BASE ON RESCIVED OR PAID AMOUNT
        #     advance_amount = transaction_data.get('advance_amount', None)
        #     # print("advance_amount ::: ",advance_amount)
        #     if advance_amount is not None:
        #         # print("CHANGE IN BALANCE BASE ON RECIVED OR PAID AMOUNT")
        #         try:
        #             balance = Balance.objects.get(customer_id = transaction_instance.customer_id.id)
        #         except:
        #             balance = None
        #         # print("balance ::: ",balance)
        #         if balance is None:
        #             balance_data = {
        #                 'customer_id': transaction_instance.customer_id.id,
        #                 'amount': advance_amount
        #             }
        #             # print("Balance DATA ::: ", balance_data)
        #             balanceSerializer = BalanceSerializer(data = balance_data)
        #             if balanceSerializer.is_valid():
        #                 balanceSerializer.save()
        #             else:
        #                 return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
        #         else:
        #             balance_data = {
        #                 'customer_id': transaction_instance.customer_id.id,
        #                 'amount': balance.amount - float(advance_amount)
        #             }
        #             # print("Balance DATA ::: ", balance_data)
        #             balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
        #             if balanceSerializer.is_valid():
        #                 balanceSerializer.save()
        #             else:
        #                 return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # if transaction_instance.type in ('purchase', 'event_purchase'):
        #     ## ADD TOTAL AMOUNT IN CUSTOMER'S BALANCE
        #     try:
        #         balance = Balance.objects.get(customer_id = transaction_instance.customer_id.id)
        #     except:
        #         balance = None
        #     # print("balance ::: ",balance)
        #     if balance is None:
        #         balance_data = {
        #             'customer_id': transaction_instance.customer_id.id,
        #             'amount': - float(transaction_instance.total_amount)
        #         }
        #         # print("Balance DATA ::: ", balance_data)
        #         balanceSerializer = BalanceSerializer(data = balance_data)
        #         if balanceSerializer.is_valid():
        #             balanceSerializer.save()
        #         else:
        #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
        #     else:
        #         balance_data = {
        #             'customer_id': transaction_instance.customer_id.id,
        #             'amount': balance.amount - float(transaction_instance.total_amount)
        #         }
        #         # print("Balance DATA ::: ", balance_data)
        #         balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
        #         if balanceSerializer.is_valid():
        #             balanceSerializer.save()
        #         else:
        #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

        #     ### CHANGE IN CUSTOMER'S BALANCE AMOUNT BASE ON RESCIVED OR PAID AMOUNT
        #     advance_amount = transaction_data.get('advance_amount', None)
        #     if advance_amount is not None:
        #         # print("CHANGE IN BALANCE BASE ON RECIVED OR PAID AMOUNT")
        #         try:
        #             balance = Balance.objects.get(customer_id = transaction_instance.customer_id.id)
        #         except:
        #             balance = None
        #         # print("balance ::: ",balance)
        #         if balance is None:
        #             balance_data = {
        #                 'customer_id': transaction_instance.customer_id.id,
        #                 'amount': advance_amount
        #             }
        #             # print("Balance DATA ::: ", balance_data)
        #             balanceSerializer = BalanceSerializer(data = balance_data)
        #             if balanceSerializer.is_valid():
        #                 balanceSerializer.save()
        #             else:
        #                 return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
        #         else:
        #             balance_data = {
        #                 'customer_id': transaction_instance.customer_id.id,
        #                 'amount': balance.amount + float(advance_amount)
        #             }
        #             # print("Balance DATA ::: ", balance_data)
        #             balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
        #             if balanceSerializer.is_valid():
        #                 balanceSerializer.save()
        #             else:
        #                 return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "inventorydescription": InventoryDescriptionSerializer(all_instance, many=True).data,
            "transaction": TransactionSerializer(transaction_instance).data
        })


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all().order_by('-id').distinct()
    serializer_class = TransactionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'user_id__id':['exact'],
        'type':['in'],
        'quotation_id__id':['exact'],
        'expense_id__id':['exact'],
        'customer_id__id':['exact'],
        'customer_id__full_name':['icontains'],
        'staff_id__id':['exact'],
        'exposuredetails_id__id':['exact'],
        'payment_type':['exact'],
        'status':['exact'],
        'is_converted':['exact'],
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if start_date and end_date:
            try:
                # print("LENGTH :: ",len(queryset))
                queryset = queryset.filter(created_date__range=[start_date, end_date])
            except ValueError:
                pass

        return queryset

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        data = {}
        # print("Instance ::", instance)
        data['transaction_data'] = TransactionSerializer(instance).data

        inventory_descriptions = instance.inventorydescription.all()
        # print("Inventory Description IDs :: ",inventory_descriptions)

        if len(inventory_descriptions) != 0:
            data['inventory_data'] = InventoryDescriptionSerializer(inventory_descriptions, many=True).data

        linktransaction = LinkTransaction.objects.filter(from_transaction_id=instance.id)
        # print("LinkTransaction :: ", linktransaction)
        # print("Length :: ", len(linktransaction))
        if len(linktransaction) != 0:
            data['linktransaction_data'] = LinkTransactionSerializer(linktransaction, many=True).data

        exposuredetails_id = instance.exposuredetails_id
        # print("EXPOSURE DETAILS ID :: ", exposuredetails_id)
        if exposuredetails_id is not None:
            exposuredetail = ExposureDetails.objects.get(pk=exposuredetails_id.id)
            # print("ExposureDetails :: ", exposuredetail)
            inventorydetails_id = exposuredetail.inventorydetails_id
            # print("inventorydetails_id :: ", inventorydetails_id)
            inventorydetails = InventoryDetails.objects.get(pk=inventorydetails_id.id)
            # print("inventorydetails :: ",inventorydetails)
            eventdetails = exposuredetail.eventdetails.all()
            # print("eventdetails :: ", eventdetails)

            data['exposuredetails'] = ExposureDetailsSerializer(exposuredetail).data
            data['inventorydetails'] = InventoryDetailsSerializer(inventorydetails).data
            data['eventdetails'] = EventDetailsSerializer(eventdetails, many=True).data

        return Response(data)

    def create(self, request, *args, **kwargs):
        transaction_data = request.data['transaction_data']
        # print("transaction_data :: ", transaction_data)
        linktransaction_data = request.data.get('linktransaction_data', None)
        # print("link_transaction_data :: ", linktransaction_data)

        data = {}

        transactionSerializer = TransactionSerializer(data=transaction_data)
        if transactionSerializer.is_valid():
            transaction_instance = transactionSerializer.save()
        else:
            return Response(transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data['transaction_data'] = TransactionSerializer(transaction_instance).data
        # print("TRANSACTION ID :: ",transaction_instance.id)

        customer_id = transaction_data.get('customer_id', None)
        # print("customer_id :: ",customer_id)
        staff_id = transaction_data.get('staff_id', None)
        # print("staff_id :: ",staff_id)

        new_amount = transaction_instance.total_amount - transaction_instance.used_amount
        print("New Amount ::: ", new_amount)
        balance_amount(customer_id, staff_id, 0, new_amount, transaction_instance.type)

        # if transaction_instance.type == 'payment_in':
        #     # print("PAYMENT IN")
        #     if customer_id is not None:
        #         try:
        #             balance = Balance.objects.get(customer_id = customer_id)
        #         except:
        #             balance = None
        #         # print("balance ::: ",balance)
        #         if balance is None:
        #             balance_data = {'customer_id': customer_id,
        #                             'amount': - float(transaction_instance.total_amount)}
        #             # print("Balance DATA ::: ", balance_data)
        #             balanceSerializer = BalanceSerializer(data = balance_data)
        #             if balanceSerializer.is_valid():
        #                 balanceSerializer.save()
        #             else:
        #                 return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
        #         else:
        #             balance_data = {
        #                 'customer_id': customer_id,
        #                 'amount': balance.amount - float(transaction_instance.total_amount)
        #             }
        #             # print("Balance DATA ::: ", balance_data)
        #             balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
        #             if balanceSerializer.is_valid():
        #                 balanceSerializer.save()
        #             else:
        #                 return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

        #     if staff_id is not None:
        #         try:
        #             balance = Balance.objects.get(staff_id = staff_id)
        #         except:
        #             balance = None
        #         # print("balance ::: ",balance)
        #         if balance is None:
        #             balance_data = {'staff_id': staff_id,
        #                             'amount': - float(transaction_instance.total_amount)}
        #             # print("Balance DATA ::: ", balance_data)
        #             balanceSerializer = BalanceSerializer(data = balance_data)
        #             if balanceSerializer.is_valid():
        #                 balanceSerializer.save()
        #             else:
        #                 return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
        #         else:
        #             balance_data = {
        #                 'staff_id': staff_id,
        #                 'amount': balance.amount - float(transaction_instance.total_amount)
        #             }
        #             # print("Balance DATA ::: ", balance_data)
        #             balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
        #             if balanceSerializer.is_valid():
        #                 balanceSerializer.save()
        #             else:
        #                 return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # if transaction_instance.type == 'payment_out':
        #     # print("PAYMENT OUT")
        #     if customer_id is not None:
        #         try:
        #             balance = Balance.objects.get(customer_id = customer_id)
        #         except:
        #             balance = None
        #         # print("balance ::: ",balance)
        #         if balance is None:
        #             balance_data = {'customer_id': customer_id,
        #                             'amount': transaction_instance.total_amount}
        #             # print("Balance DATA ::: ", balance_data)
        #             balanceSerializer = BalanceSerializer(data = balance_data)
        #             if balanceSerializer.is_valid():
        #                 balanceSerializer.save()
        #             else:
        #                 return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
        #         else:
        #             balance_data = {
        #                 'customer_id': customer_id,
        #                 'amount': balance.amount + float(transaction_instance.total_amount)
        #             }
        #             # print("Balance DATA ::: ", balance_data)
        #             balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
        #             if balanceSerializer.is_valid():
        #                 balanceSerializer.save()
        #             else:
        #                 return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

        #     if staff_id is not None:
        #         try:
        #             balance = Balance.objects.get(staff_id = staff_id)
        #         except:
        #             balance = None
        #         # print("balance ::: ",balance)
        #         if balance is None:
        #             balance_data = {'staff_id': staff_id,
        #                             'amount': transaction_instance.total_amount}
        #             # print("Balance DATA ::: ", balance_data)
        #             balanceSerializer = BalanceSerializer(data = balance_data)
        #             if balanceSerializer.is_valid():
        #                 balanceSerializer.save()
        #             else:
        #                 return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
        #         else:
        #             balance_data = {
        #                 'staff_id': staff_id,
        #                 'amount': balance.amount + float(transaction_instance.total_amount)
        #             }
        #             # print("Balance DATA ::: ", balance_data)
        #             balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
        #             if balanceSerializer.is_valid():
        #                 balanceSerializer.save()
        #             else:
        #                 return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if linktransaction_data is not None:
            link_transaction(transaction_instance.id, linktransaction_data)

        return Response(data)

    def update(self, request, pk=None, *args, **kwargs):
        key = request.data.get('key')

        transaction = Transaction.objects.get(pk=pk)
        # print("Transaction :: ", transaction)

        if transaction.type in ('payment_in', 'payment_out'):
            old_amount = transaction.total_amount - transaction.used_amount
        else:
            old_amount = transaction.total_amount - transaction.recived_or_paid_amount

        data={}

        if key == 'inventorydescription_update':
            inventory_datas = request.data.get('inventory_data', None)
            # print("Inventory Data :: ",inventory_datas)
            copy_inventory_datas = inventory_datas
            # print("Copy Inventory Data :: ",copy_inventory_datas)
            transaction_data = request.data.get('transaction_data')
            # print("Trnasaction Data :: ",transaction_data)
            delete_inventorys = request.data.get('delete_inventory', None)
            # print("Delete Inventory :: ",delete_inventorys)
            linktransaction_data = request.data.get('linktransaction_data', None)
            # print("Link Transaction Data :: ",linktransaction_data)

            all_inventory = []
            inventorydescription_ids = []

            ### NOT CONVERTED TRANSACTION ###
            if transaction.is_converted == False:
                # print("CONVERTED FALSE")
                convert_status = transaction_data.get('is_converted', None)
                # print("CONVERTED STATUS :: ", convert_status)

                if delete_inventorys is not None:
                    for delete_inventory in delete_inventorys:
                        # print("Delete Inventory ID :: ", delete_inventory)
                        d_inventory = InventoryDescription.objects.get(pk=delete_inventory)
                        # print("Object :: ", d_inventory)
                        d_inventory.delete()
                
                for inventory_data in inventory_datas:
                    # print("Inventory Data :: ",inventory_data)
                    # print("Inventory Description ID :: ", inventory_data['id'])
                    if inventory_data['id'] == '':
                        # print("New Inventory")
                        inventory_data.pop('id')
                        n_inventory = InventoryDescriptionSerializer(data=inventory_data)
                        if n_inventory.is_valid():
                            new_inventory = n_inventory.save()
                            # print("Inventory Description ID ::", new_inventory.id)
                            inventorydescription_ids.append(new_inventory.id)
                            all_inventory.append(new_inventory)
                        else:
                            return Response(n_inventory.errors, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        # print("Old Inventory")
                        # print("Inventory ID :: ", inventory_data['id'])
                        inventory = InventoryDescription.objects.get(id=inventory_data['id'])
                        # print("Inventory Object :: ", inventory)
                        o_inventory = InventoryDescriptionSerializer(inventory, data=inventory_data, partial=True)
                        if o_inventory.is_valid():
                            old_inventory = o_inventory.save()
                            # print("Inventory Description ID ::", old_inventory.id)
                            inventorydescription_ids.append(old_inventory.id)
                            all_inventory.append(old_inventory)
                        else:
                            return Response(o_inventory.errors, status=status.HTTP_400_BAD_REQUEST)
                        
                # old_total_amount = float(transaction.total_amount)
                # print("old_total_amount ::: ",old_total_amount)

                # old_advance_amount = float(transaction.advance_amount)
                # print("old_advance_amount ::: ",old_advance_amount)

                if convert_status == 'true':
                    transaction_data['is_converted'] = True
                else:
                    transaction_data['is_converted'] = False
                transaction_data['inventorydescription'] = inventorydescription_ids 
                transactionSerializer = TransactionSerializer(transaction, data=transaction_data, partial=True)
                if transactionSerializer.is_valid():
                    transaction_instance = transactionSerializer.save()
                else:
                    return Response(transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                customer_id = transaction_instance.customer_id.id if transaction_instance.customer_id is not None else None
                # print("customer_id :::",customer_id)
                staff_id = transaction_instance.staff_id.id if transaction_instance.staff_id is not None else None
                # print("staff_id :::",staff_id)
                
                new_amount = transaction_instance.total_amount - transaction_instance.recived_or_paid_amount
                print("New Amount ::: ", new_amount)
                balance_amount(customer_id, staff_id, old_amount, new_amount, transaction_instance.type)
                
                # new_total_amount = float(transaction_instance.total_amount)
                # print("new_total_amount ::: ",new_total_amount)

                # new_advance_amount = float(transaction_instance.advance_amount)
                # print("new_advance_amount ::: ",new_advance_amount)

                # if transaction_instance.type == 'sale':
                #     ## ADD TOTAL AMOUNT IN CUSTOMER'S BALANCE
                #     try:
                #         balance = Balance.objects.get(customer_id = transaction_instance.customer_id.id)
                #     except:
                #         balance = None
                #     # print("balance ::: ",balance)
                #     if balance is None:
                #         # print("ADD TOTAL AMOUNT IN CUSTOMER'S BALANCE")
                #         balance_data = {'customer_id': transaction_instance.customer_id.id,
                #                         'amount': transaction_instance.total_amount}
                #         # print("Balance DATA ::: ", balance_data)
                #         balanceSerializer = BalanceSerializer(data = balance_data)
                #         if balanceSerializer.is_valid():
                #             balanceSerializer.save()
                #         else:
                #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                #     else:
                #         # print("ADD TOTAL AMOUNT IN CUSTOMER'S BALANCE")
                #         balance_data = {'customer_id': transaction_instance.customer_id.id,
                #                         'amount': (balance.amount - old_total_amount) + new_total_amount}
                #         # print("Balance DATA ::: ", balance_data)
                #         balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                #         if balanceSerializer.is_valid():
                #             balanceSerializer.save()
                #         else:
                #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

                #     ### CHANGE IN CUSTOMER'S BALANCE AMOUNT BASE ON RESCIVED OR PAID AMOUNT
                #     try:
                #         balance = Balance.objects.get(customer_id = transaction_instance.customer_id.id)
                #     except:
                #         balance = None
                #     # print("balance ::: ",balance)
                #     if balance is None:
                #         # print("CHANGE IN CUSTOMER'S BALANCE AMOUNT BASE ON RESCIVED OR PAID AMOUNT")
                #         balance_data = {'customer_id': transaction_instance.customer_id.id,
                #                         'amount': - float(transaction_instance.advance_amount)}
                #         # print("Balance DATA ::: ", balance_data)
                #         balanceSerializer = BalanceSerializer(data = balance_data)
                #         if balanceSerializer.is_valid():
                #             balanceSerializer.save()
                #         else:
                #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                #     else:
                #         # print("CHANGE IN CUSTOMER'S BALANCE AMOUNT BASE ON RESCIVED OR PAID AMOUNT")
                #         balance_data = {'customer_id': transaction.customer_id.id,
                #                         'amount': (balance.amount + old_advance_amount) - new_advance_amount}
                #         # print("Balance DATA ::: ", balance_data)
                #         balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                #         if balanceSerializer.is_valid():
                #             balanceSerializer.save()
                #         else:
                #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

                # if transaction_instance.type == 'purchase':
                #     ## ADD TOTAL AMOUNT IN CUSTOMER'S BALANCE
                #     try:
                #         balance = Balance.objects.get(customer_id = transaction_instance.customer_id.id)
                #     except:
                #         balance = None
                #     # print("balance ::: ",balance)
                #     if balance is None:
                #         print("ADD TOTAL AMOUNT IN CUSTOMER'S BALANCE")
                #         balance_data = {'customer_id': transaction_instance.customer_id.id,
                #                         'amount': - float(transaction_instance.total_amount)}
                #         print("Balance DATA ::: ", balance_data)
                #         balanceSerializer = BalanceSerializer(data = balance_data)
                #         if balanceSerializer.is_valid():
                #             balanceSerializer.save()
                #         else:
                #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                #     else:
                #         print("ADD TOTAL AMOUNT IN CUSTOMER'S BALANCE")
                #         balance_data = {'customer_id': transaction_instance.customer_id.id,
                #                         'amount': (balance.amount + old_total_amount) - new_total_amount}
                #         print("Balance DATA ::: ", balance_data)
                #         balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                #         if balanceSerializer.is_valid():
                #             balanceSerializer.save()
                #         else:
                #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

                #     ### CHANGE IN CUSTOMER'S BALANCE AMOUNT BASE ON RESCIVED OR PAID AMOUNT
                #     try:
                #         balance = Balance.objects.get(customer_id = transaction_instance.customer_id.id)
                #     except:
                #         balance = None
                #     # print("balance ::: ",balance)
                #     if balance is None:
                #         # print("CHANGE IN CUSTOMER'S BALANCE AMOUNT BASE ON RESCIVED OR PAID AMOUNT")
                #         balance_data = {'customer_id': transaction_instance.customer_id.id,
                #                         'amount': float(transaction_instance.advance_amount)}
                #         # print("Balance DATA ::: ", balance_data)
                #         balanceSerializer = BalanceSerializer(data = balance_data)
                #         if balanceSerializer.is_valid():
                #             balanceSerializer.save()
                #         else:
                #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                #     else:
                #         # print("CHANGE IN CUSTOMER'S BALANCE AMOUNT BASE ON RESCIVED OR PAID AMOUNT")
                #         balance_data = {'customer_id': transaction.customer_id.id,
                #                         'amount': (balance.amount - old_advance_amount) + new_advance_amount}
                #         # print("Balance DATA ::: ", balance_data)
                #         balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                #         if balanceSerializer.is_valid():
                #             balanceSerializer.save()
                #         else:
                #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)


                # print("convert_status == 'true' ::: ", convert_status == 'true')
                if convert_status is not None:
                    if convert_status == 'true':
                        # print("MAKE A NEW COPY")
                        copy_all_instance = []
                        copy_inventorydescription_ids = []

                        for copy_inventory_data in copy_inventory_datas:
                            # print("Single Inventory Data :: ", inventory_data)

                            copy_inventorySerializer = InventoryDescriptionSerializer(data=copy_inventory_data)
                            if copy_inventorySerializer.is_valid():
                                copy_inventory_instance = copy_inventorySerializer.save()
                                copy_all_instance.append(copy_inventory_instance)
                            else:
                                return Response(copy_inventorySerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                            
                            # print("Inventory Description ID ::", copy_inventory_instance.id)
                            copy_inventorydescription_ids.append(copy_inventory_instance.id)

                        if transaction_data['type'] == 'purchase_order':
                            transaction_data['type'] = 'purchase'
                        if transaction_data['type'] == 'sale_order':
                            transaction_data['type'] = 'sale'
                        transaction_data['is_converted'] = True
                        transaction_data['inventorydescription'] = copy_inventorydescription_ids
                        # print("Transaction Data ::", transaction_data)
                        copy_transactionSerializer = TransactionSerializer(data = transaction_data)
                        if copy_transactionSerializer.is_valid():
                            copy_trnasaction_instance = copy_transactionSerializer.save()
                        else:
                            return Response(copy_transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                        
                        customer_id = copy_trnasaction_instance.customer_id.id if copy_trnasaction_instance.customer_id is not None else None
                        # print("customer_id :::",customer_id)
                        staff_id = copy_trnasaction_instance.staff_id.id if copy_trnasaction_instance.staff_id is not None else None
                        # print("staff_id :::",staff_id)
                        
                        new_amount = copy_trnasaction_instance.total_amount - copy_trnasaction_instance.recived_or_paid_amount
                        print("New Amount ::: ", new_amount)
                        balance_amount(copy_trnasaction_instance.customer_id.id, None, 0 , new_amount, copy_trnasaction_instance.type)

                        # if copy_trnasaction_instance.type == 'sale':
                        #     ## ADD TOTAL AMOUNT IN CUSTOMER'S BALANCE
                        #     try:
                        #         balance = Balance.objects.get(customer_id = copy_trnasaction_instance.customer_id.id)
                        #     except:
                        #         balance = None
                        #     # print("balance ::: ",balance)
                        #     if balance is None:
                        #         balance_data = {
                        #             'customer_id': copy_trnasaction_instance.customer_id.id,
                        #             'amount': copy_trnasaction_instance.total_amount
                        #         }
                        #         # print("Balance DATA ::: ", balance_data)
                        #         balanceSerializer = BalanceSerializer(data = balance_data)
                        #         if balanceSerializer.is_valid():
                        #             balanceSerializer.save()
                        #         else:
                        #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                        #     else:
                        #         balance_data = {
                        #             'customer_id': copy_trnasaction_instance.customer_id.id,
                        #             'amount': balance.amount + float(copy_trnasaction_instance.total_amount)
                        #         }
                        #         # print("Balance DATA ::: ", balance_data)
                        #         balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                        #         if balanceSerializer.is_valid():
                        #             balanceSerializer.save()
                        #         else:
                        #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

                        #     ### CHANGE IN CUSTOMER'S BALANCE AMOUNT BASE ON RESCIVED OR PAID AMOUNT
                        #     advance_amount = transaction_data.get('advance_amount', None)
                        #     # print("advance_amount ::: ",advance_amount)
                        #     if advance_amount is not None:
                        #         # print("CHANGE IN BALANCE BASE ON RECIVED OR PAID AMOUNT")
                        #         try:
                        #             balance = Balance.objects.get(customer_id = copy_trnasaction_instance.customer_id.id)
                        #         except:
                        #             balance = None
                        #         # print("balance ::: ",balance)
                        #         if balance is None:
                        #             balance_data = {
                        #                 'customer_id': copy_trnasaction_instance.customer_id.id,
                        #                 'amount': advance_amount
                        #             }
                        #             # print("Balance DATA ::: ", balance_data)
                        #             balanceSerializer = BalanceSerializer(data = balance_data)
                        #             if balanceSerializer.is_valid():
                        #                 balanceSerializer.save()
                        #             else:
                        #                 return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                        #         else:
                        #             balance_data = {
                        #                 'customer_id': copy_trnasaction_instance.customer_id.id,
                        #                 'amount': balance.amount - float(advance_amount)
                        #             }
                        #             # print("Balance DATA ::: ", balance_data)
                        #             balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                        #             if balanceSerializer.is_valid():
                        #                 balanceSerializer.save()
                        #             else:
                        #                 return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

                        # if copy_trnasaction_instance.type == 'purchase':
                        #     ## ADD TOTAL AMOUNT IN CUSTOMER'S BALANCE
                        #     try:
                        #         balance = Balance.objects.get(customer_id = copy_trnasaction_instance.customer_id.id)
                        #     except:
                        #         balance = None
                        #     # print("balance ::: ",balance)
                        #     if balance is None:
                        #         balance_data = {
                        #             'customer_id': copy_trnasaction_instance.customer_id.id,
                        #             'amount': - float(copy_trnasaction_instance.total_amount)
                        #         }
                        #         # print("Balance DATA ::: ", balance_data)
                        #         balanceSerializer = BalanceSerializer(data = balance_data)
                        #         if balanceSerializer.is_valid():
                        #             balanceSerializer.save()
                        #         else:
                        #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                        #     else:
                        #         balance_data = {
                        #             'customer_id': copy_trnasaction_instance.customer_id.id,
                        #             'amount': balance.amount - float(copy_trnasaction_instance.total_amount)
                        #         }
                        #         # print("Balance DATA ::: ", balance_data)
                        #         balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                        #         if balanceSerializer.is_valid():
                        #             balanceSerializer.save()
                        #         else:
                        #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

                        #     ### CHANGE IN CUSTOMER'S BALANCE AMOUNT BASE ON RESCIVED OR PAID AMOUNT
                        #     advance_amount = transaction_data.get('advance_amount', None)
                        #     if advance_amount is not None:
                        #         # print("CHANGE IN BALANCE BASE ON RECIVED OR PAID AMOUNT")
                        #         try:
                        #             balance = Balance.objects.get(customer_id = copy_trnasaction_instance.customer_id.id)
                        #         except:
                        #             balance = None
                        #         # print("balance ::: ",balance)
                        #         if balance is None:
                        #             balance_data = {
                        #                 'customer_id': copy_trnasaction_instance.customer_id.id,
                        #                 'amount': advance_amount
                        #             }
                        #             # print("Balance DATA ::: ", balance_data)
                        #             balanceSerializer = BalanceSerializer(data = balance_data)
                        #             if balanceSerializer.is_valid():
                        #                 balanceSerializer.save()
                        #             else:
                        #                 return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                        #         else:
                        #             balance_data = {
                        #                 'customer_id': copy_trnasaction_instance.customer_id.id,
                        #                 'amount': balance.amount + float(advance_amount)
                        #             }
                        #             # print("Balance DATA ::: ", balance_data)
                        #             balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                        #             if balanceSerializer.is_valid():
                        #                 balanceSerializer.save()
                        #             else:
                        #                 return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

            else:
                if delete_inventorys is not None:
                    for delete_inventory in delete_inventorys:
                        # print("Delete Inventory ID :: ", delete_inventory)
                        d_inventory = InventoryDescription.objects.get(pk=delete_inventory)
                        # print("Object :: ", d_inventory)
                        d_inventory.delete()
                
                for inventory_data in inventory_datas:
                    # print("Inventory Data :: ",inventory_data)
                    # print("Inventory Description ID :: ", inventory_data['id'])
                    if inventory_data['id'] == '':
                        # print("New Inventory")
                        inventory_data.pop('id')
                        n_inventory = InventoryDescriptionSerializer(data=inventory_data)
                        if n_inventory.is_valid():
                            new_inventory = n_inventory.save()
                            # print("Inventory Description ID ::", new_inventory.id)
                            inventorydescription_ids.append(new_inventory.id)
                            all_inventory.append(new_inventory)
                        else:
                            return Response(n_inventory.errors, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        # print("Old Inventory")
                        # print("Inventory ID :: ", inventory_data['id'])
                        inventory = InventoryDescription.objects.get(id=inventory_data['id'])
                        # print("Inventory Object :: ", inventory)
                        o_inventory = InventoryDescriptionSerializer(inventory, data=inventory_data, partial=True)
                        if o_inventory.is_valid():
                            old_inventory = o_inventory.save()
                            # print("Inventory Description ID ::", old_inventory.id)
                            inventorydescription_ids.append(old_inventory.id)
                            all_inventory.append(old_inventory)
                        else:
                            return Response(o_inventory.errors, status=status.HTTP_400_BAD_REQUEST)
                        
                # old_total_amount = float(transaction.total_amount)
                # print("old_total_amount ::: ",old_total_amount)

                # old_advance_amount = float(transaction.advance_amount)
                # print("old_advance_amount ::: ",old_advance_amount)

                transaction_data['inventorydescription'] = inventorydescription_ids 
                transaction_data['is_converted'] = True
                transactionSerializer = TransactionSerializer(transaction, data=transaction_data, partial=True)
                if transactionSerializer.is_valid():
                    transaction_instance = transactionSerializer.save()
                else:
                    return Response(transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                customer_id = transaction_instance.customer_id.id if transaction_instance.customer_id is not None else None
                # print("customer_id :::",customer_id)
                staff_id = transaction_instance.staff_id.id if transaction_instance.staff_id is not None else None
                # print("staff_id :::",staff_id)
                
                new_amount = transaction_instance.total_amount - transaction_instance.recived_or_paid_amount
                print("New Amount ::: ", new_amount)
                balance_amount(transaction_instance.customer_id.id, None, old_amount, new_amount, transaction_instance.type)
                
                # new_total_amount = float(transaction_instance.total_amount)
                # print("new_total_amount ::: ",new_total_amount)

                # new_advance_amount = float(transaction_instance.advance_amount)
                # print("new_advance_amount ::: ",new_advance_amount)

                # if transaction_instance.type == 'sale':
                #     ## ADD TOTAL AMOUNT IN CUSTOMER'S BALANCE
                    
                #     try:
                #         balance = Balance.objects.get(customer_id = transaction_instance.customer_id.id)
                #     except:
                #         balance = None
                #     # print("balance ::: ",balance)
                #     if balance is None:
                #         # print("ADD TOTAL AMOUNT IN CUSTOMER'S BALANCE")
                #         balance_data = {'customer_id': transaction_instance.customer_id.id,
                #                         'amount': transaction_instance.total_amount}
                #         # print("Balance DATA ::: ", balance_data)
                #         balanceSerializer = BalanceSerializer(data = balance_data)
                #         if balanceSerializer.is_valid():
                #             balanceSerializer.save()
                #         else:
                #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                #     else:
                #         # print("ADD TOTAL AMOUNT IN CUSTOMER'S BALANCE")
                #         balance_data = {'customer_id': transaction_instance.customer_id.id,
                #                         'amount': (balance.amount - old_total_amount) + new_total_amount}
                #         # print("Balance DATA ::: ", balance_data)
                #         balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                #         if balanceSerializer.is_valid():
                #             balanceSerializer.save()
                #         else:
                #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

                #     ### CHANGE IN CUSTOMER'S BALANCE AMOUNT BASE ON RESCIVED OR PAID AMOUNT
                #     try:
                #         balance = Balance.objects.get(customer_id = transaction_instance.customer_id.id)
                #     except:
                #         balance = None
                #     # print("balance ::: ",balance)
                #     if balance is None:
                #         # print("CHANGE IN CUSTOMER'S BALANCE AMOUNT BASE ON RESCIVED OR PAID AMOUNT")
                #         balance_data = {'customer_id': transaction_instance.customer_id.id,
                #                         'amount': - float(transaction_instance.advance_amount)}
                #         # print("Balance DATA ::: ", balance_data)
                #         balanceSerializer = BalanceSerializer(data = balance_data)
                #         if balanceSerializer.is_valid():
                #             balanceSerializer.save()
                #         else:
                #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                #     else:
                #         # print("CHANGE IN CUSTOMER'S BALANCE AMOUNT BASE ON RESCIVED OR PAID AMOUNT")
                #         balance_data = {'customer_id': transaction.customer_id.id,
                #                         'amount': (balance.amount + old_advance_amount) - new_advance_amount}
                #         # print("Balance DATA ::: ", balance_data)
                #         balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                #         if balanceSerializer.is_valid():
                #             balanceSerializer.save()
                #         else:
                #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

                # if transaction_instance.type == 'purchase':
                #     ## ADD TOTAL AMOUNT IN CUSTOMER'S BALANCE
                #     try:
                #         balance = Balance.objects.get(customer_id = transaction_instance.customer_id.id)
                #     except:
                #         balance = None
                #     # print("balance ::: ",balance)
                #     if balance is None:
                #         # print("ADD TOTAL AMOUNT IN CUSTOMER'S BALANCE")
                #         balance_data = {'customer_id': transaction_instance.customer_id.id,
                #                         'amount': - float(transaction_instance.total_amount)}
                #         # print("Balance DATA ::: ", balance_data)
                #         balanceSerializer = BalanceSerializer(data = balance_data)
                #         if balanceSerializer.is_valid():
                #             balanceSerializer.save()
                #         else:
                #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                #     else:
                #         # print("ADD TOTAL AMOUNT IN CUSTOMER'S BALANCE")
                #         balance_data = {'customer_id': transaction_instance.customer_id.id,
                #                         'amount': (balance.amount + old_total_amount) - new_total_amount}
                #         # print("Balance DATA ::: ", balance_data)
                #         balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                #         if balanceSerializer.is_valid():
                #             balanceSerializer.save()
                #         else:
                #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

                #     ### CHANGE IN CUSTOMER'S BALANCE AMOUNT BASE ON RESCIVED OR PAID AMOUNT
                #     try:
                #         balance = Balance.objects.get(customer_id = transaction_instance.customer_id.id)
                #     except:
                #         balance = None
                #     # print("balance ::: ",balance)
                #     if balance is None:
                #         # print("CHANGE IN CUSTOMER'S BALANCE AMOUNT BASE ON RESCIVED OR PAID AMOUNT")
                #         balance_data = {'customer_id': transaction_instance.customer_id.id,
                #                         'amount': float(transaction_instance.advance_amount)}
                #         # print("Balance DATA ::: ", balance_data)
                #         balanceSerializer = BalanceSerializer(data = balance_data)
                #         if balanceSerializer.is_valid():
                #             balanceSerializer.save()
                #         else:
                #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                #     else:
                #         # print("CHANGE IN CUSTOMER'S BALANCE AMOUNT BASE ON RESCIVED OR PAID AMOUNT")
                #         balance_data = {'customer_id': transaction.customer_id.id,
                #                         'amount': (balance.amount - old_advance_amount) + new_advance_amount}
                #         # print("Balance DATA ::: ", balance_data)
                #         balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                #         if balanceSerializer.is_valid():
                #             balanceSerializer.save()
                #         else:
                #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # print("PKKKK :: ",pk)
            if linktransaction_data is not None:
                link_transaction(pk, linktransaction_data)

            data['tranasaction_data'] = TransactionSerializer(transaction_instance).data
            data['inventorydescription_data'] = InventoryDescriptionSerializer(all_inventory, many=True).data

        if key == 'transaction_update':
            transaction_data = request.data.get('transaction_data')
            # print("Trnasaction Data :: ",transaction_data)
            linktransaction_data = request.data.get('linktransaction_data', None)
            # print("Link Transaction Data :: ",linktransaction_data)
            # delete_linktransaction_datas = request.data.get('delete_linktransaction', None)
            # print("Delete Transaction Data :: ",delete_linktransaction_datas)

            # old_amount = transaction.recived_or_paid_amount
            # print("OLD AMOUNT :: ",old_amount)
            # old_total_amount = float(transaction.total_amount)
            # print("old_total_amount :::",old_total_amount)

            transactionSerializer = TransactionSerializer(transaction, data=transaction_data, partial=True)
            if transactionSerializer.is_valid():
                transaction_instance = transactionSerializer.save()
            else:
                return Response(transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            
            # new_total_amount = float(transaction_instance.total_amount)
            # print("new_total_amount :::",new_total_amount)

            customer_id = transaction_instance.customer_id.id if transaction_instance.customer_id is not None else None
            # print("customer_id :::",customer_id)
            staff_id = transaction_instance.staff_id.id if transaction_instance.staff_id is not None else None
            # print("staff_id :::",staff_id)

            new_amount = transaction_instance.total_amount - transaction_instance.used_amount
            print("New Amount ::: ", new_amount)
            balance_amount(customer_id, staff_id, old_amount, new_amount, transaction_instance.type)

            # if transaction_instance.type == 'payment_in':
            #     # print("PAYMENT IN")
            #     if customer_id is not None:
            #         try:
            #             balance = Balance.objects.get(customer_id = customer_id)
            #         except:
            #             balance = None
            #         # print("balance ::: ",balance)
            #         if balance is None:
            #             balance_data = {'customer_id': customer_id,
            #                             'amount': - float(transaction_instance.total_amount)}
            #             # print("Balance DATA ::: ", balance_data)
            #             balanceSerializer = BalanceSerializer(data = balance_data)
            #             if balanceSerializer.is_valid():
            #                 balanceSerializer.save()
            #             else:
            #                 return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
            #         else:
            #             balance_data = {'customer_id': customer_id,
            #                             'amount': (balance.amount + old_total_amount) - new_total_amount}
            #             # print("Balance DATA ::: ", balance_data)
            #             balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
            #             if balanceSerializer.is_valid():
            #                 balanceSerializer.save()
            #             else:
            #                 return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

            #     if staff_id is not None:
            #         try:
            #             balance = Balance.objects.get(staff_id = staff_id)
            #         except:
            #             balance = None
            #         # print("balance ::: ",balance)
            #         if balance is None:
            #             balance_data = {'staff_id': staff_id,
            #                             'amount': - float(transaction_instance.total_amount)}
            #             # print("Balance DATA ::: ", balance_data)
            #             balanceSerializer = BalanceSerializer(data = balance_data)
            #             if balanceSerializer.is_valid():
            #                 balanceSerializer.save()
            #             else:
            #                 return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
            #         else:
            #             balance_data = {'staff_id': staff_id,
            #                             'amount': (balance.amount + old_total_amount) - new_total_amount}
            #             # print("Balance DATA ::: ", balance_data)
            #             balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
            #             if balanceSerializer.is_valid():
            #                 balanceSerializer.save()
            #             else:
            #                 return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # if transaction_instance.type == 'payment_out':
            #     # print("PAYMENT OUT")
            #     if customer_id is not None:
            #         try:
            #             balance = Balance.objects.get(customer_id = customer_id)
            #         except:
            #             balance = None
            #         # print("balance ::: ",balance)
            #         if balance is None:
            #             balance_data = {'customer_id': customer_id,
            #                             'amount': transaction_instance.total_amount}
            #             # print("Balance DATA ::: ", balance_data)
            #             balanceSerializer = BalanceSerializer(data = balance_data)
            #             if balanceSerializer.is_valid():
            #                 balanceSerializer.save()
            #             else:
            #                 return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
            #         else:
            #             balance_data = {
            #                 'customer_id': customer_id,
            #                 'amount': (balance.amount - old_total_amount) + new_total_amount
            #             }
            #             # print("Balance DATA ::: ", balance_data)
            #             balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
            #             if balanceSerializer.is_valid():
            #                 balanceSerializer.save()
            #             else:
            #                 return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

            #     if staff_id is not None:
            #         try:
            #             balance = Balance.objects.get(staff_id = staff_id)
            #         except:
            #             balance = None
            #         # print("balance ::: ",balance)
            #         if balance is None:
            #             balance_data = {'staff_id': staff_id,
            #                             'amount': transaction_instance.total_amount}
            #             # print("Balance DATA ::: ", balance_data)
            #             balanceSerializer = BalanceSerializer(data = balance_data)
            #             if balanceSerializer.is_valid():
            #                 balanceSerializer.save()
            #             else:
            #                 return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
            #         else:
            #             balance_data = {
            #                 'staff_id': staff_id,
            #                 'amount': (balance.amount - old_total_amount) + new_total_amount
            #             }
            #             # print("Balance DATA ::: ", balance_data)
            #             balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
            #             if balanceSerializer.is_valid():
            #                 balanceSerializer.save()
            #             else:
            #                 return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # print("PKKKK :: ",pk)
            if linktransaction_data is not None:
                # print("LINK TRASACTION FUNCTION")
                link_transaction(pk, linktransaction_data, transaction.type)
                ### WE ADD TRANSACTION TYPE BECAUSE OF IF TO TRANSACTION AND UPDATE TRASACTION IS SAME THEN WE DON'T NEED TO EDIT USED AMOUNT
 
        if key == 'exposure_bill_update':
            transaction_data = request.data.get('transaction_data')
            # print("Trnasaction Data :: ",transaction_data)

            # old_total_amount = float(transaction.total_amount)
            # print("old_total_amount ::: ",old_total_amount)

            transactionSerializer = TransactionSerializer(transaction, data=transaction_data, partial=True)
            if transactionSerializer.is_valid():
                transaction_instance = transactionSerializer.save()
            else:
                return Response(transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            customer_id = transaction_instance.customer_id.id if transaction_instance.customer_id is not None else None
            # print("customer_id :::",customer_id)
            staff_id = transaction_instance.staff_id.id if transaction_instance.staff_id is not None else None
            # print("staff_id :::",staff_id)
            
            new_amount = transaction_instance.total_amount - transaction_instance.recived_or_paid_amount
            print("New Amount ::: ", new_amount)
            balance_amount(customer_id, staff_id, old_amount, new_amount, transaction_instance.type)

            
            # new_total_amount = float(transaction.total_amount)
            # print("new_total_amount ::: ",new_total_amount)

            # try:
            #     balance = Balance.object.get(staff_id=transaction_data['staff_id'])
            # except:
            #     balance = None
            # # print("balance ::: ",balance)
            # if balance is None:
            #     balance_data = {'staff_id': staff_id,
            #                     'amount': - float(transaction_instance.total_amount)}
            #     # print("Balance DATA ::: ", balance_data)
            #     balanceSerializer = BalanceSerializer(data = balance_data)
            #     if balanceSerializer.is_valid():
            #         balanceSerializer.save()
            #     else:
            #         return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
            # else:
            #     balance_data = {'staff_id': staff_id,
            #                     'amount': (balance.amount - old_total_amount) + new_total_amount}
            #     # print("Balance DATA ::: ", balance_data)
            #     balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
            #     if balanceSerializer.is_valid():
            #         balanceSerializer.save()
            #     else:
            #         return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)


            data['tranasaction_data'] = TransactionSerializer(transaction_instance).data
        
        return Response(data)

    def destroy(self, request, pk=None, *args, **kwargs):
        transaction_object = Transaction.objects.get(pk=pk)
        # print("TRANSACTION :: ",transaction_object)
        # print("TRANSACTION TYPE :: ",transaction_object.type)

        customer_id = transaction_object.customer_id.id if transaction_object.customer_id is not None else None
        # print("customer_id :::",customer_id)
        staff_id = transaction_object.staff_id.id if transaction_object.staff_id is not None else None
        # print("staff_id :::",staff_id)

        if transaction_object.type == 'estimate':
            # print("ESTIMANT TYPE")
            quotation_id = transaction_object.quotation_id
            # print("QUOTATION ID :: ",quotation_id)
            quotation = Quotation.objects.get(pk=quotation_id.id)
            # print("QUOTATION :: ",quotation)
            quotation.delete()
            
        if transaction_object.type == 'payment_in':
            # print("PAYMENT IN TYPE")
            linktrasactions = LinkTransaction.objects.filter(from_transaction_id=pk)
            # print("ALL LINKED TRANSACTION :: ", linktrasactions)
            for link in linktrasactions:
                to_transaction_id = link.to_transaction_id
                new_amount = link.linked_amount
                to_transaction = Transaction.objects.get(pk=to_transaction_id.id)

                if to_transaction.type in ('payment_in', 'payment_out'):
                    to_transaction.used_amount = to_transaction.used_amount - link.linked_amount
                else:
                    to_transaction.recived_or_paid_amount = to_transaction.recived_or_paid_amount - link.linked_amount
                to_transaction.save()

                print("New Amount ::: ", new_amount)
                balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

            to_linktrasactions = LinkTransaction.objects.filter(to_transaction_id=pk)
            print("ALL LINKED TRANSACTION :: ", linktrasactions)
            for to_link in to_linktrasactions:
                from_transaction_id = to_link.from_transaction_id
                new_amount = to_link.linked_amount
                from_trasaction = Transaction.objects.get(pk=from_transaction_id.id)

                if from_transaction.type in ('payment_in', 'payment_out'):
                    from_trasaction.used_amount = from_trasaction.used_amount - to_link.linked_amount
                else:
                    from_trasaction.recived_or_paid_amount = from_trasaction.recived_or_paid_amount - to_link.linked_amount
                from_trasaction.save()

                print("New Amount ::: ", new_amount)
                balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

            new_amount = transaction_object.total_amount - transaction_object.used_amount
            print("New Amount ::: ", new_amount)
            balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

            # if customer_id is not None:
            #     try:
            #         balance = Balance.objects.get(customer_id=customer_id)
            #     except:
            #         balance = None
            #     # print("BALANCE :: ",balance)
            #     if balance is not None:
            #         balance.amount = balance.amount + transaction_object.total_amount
            #         balance.save()

            # if staff_id is not None:
            #         try:
            #             balance = Balance.objects.get(staff_id=staff_id)
            #         except:
            #             balance = None
            #         # print("BALANCE :: ",balance)
            #         if balance is not None:
            #             balance.amount = balance.amount + transaction_object.total_amount
            #             balance.save()

        if transaction_object.type == 'payment_out':
            # print("PAYMENT IN TYPE")
            linktrasactions = LinkTransaction.objects.filter(from_transaction_id=pk)
            # print("ALL LINKED TRANSACTION :: ", linktrasactions)
            for link in linktrasactions:
                to_transaction_id = link.to_transaction_id
                new_amount = link.linked_amount          
                to_transaction = Transaction.objects.get(pk=to_transaction_id.id)

                if to_transaction in ('payment_in', 'payment_out'):
                    to_transaction.used_amount = to_transaction.used_amount - link.linked_amount
                else:
                    to_transaction.recived_or_paid_amount = to_transaction.recived_or_paid_amount - link.linked_amount
                to_transaction.save()

                print("New Amount ::: ", new_amount)
                balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

            to_linktrasactions = LinkTransaction.objects.filter(to_transaction_id=pk)
            print("ALL LINKED TRANSACTION :: ", linktrasactions)
            for to_link in to_linktrasactions:
                from_transaction_id = to_link.from_transaction_id
                new_amount = to_link.linked_amount
                from_trasaction = Transaction.objects.get(pk=from_transaction_id.id)

                if to_transaction in ('payment_in', 'payment_out'):
                    from_trasaction.used_amount = from_trasaction.used_amount - to_link.linked_amount
                else:
                    from_trasaction.recived_or_paid_amount = from_trasaction.recived_or_paid_amount - to_link.linked_amount
                
                from_trasaction.save()

                print("New Amount ::: ", new_amount)
                balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

            new_amount = transaction_object.total_amount - transaction_object.used_amount
            print("New Amount ::: ", new_amount)
            balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

            # if customer_id is not None:
            #     try:
            #         balance = Balance.objects.get(customer_id=customer_id)
            #     except:
            #         balance = None
            #     # print("BALANCE :: ",balance)
            #     if balance is not None:
            #         balance.amount = balance.amount - transaction_object.total_amount
            #         balance.save()

            # if staff_id is not None:
            #     try:
            #         balance = Balance.objects.get(staff_id=staff_id)
            #     except:
            #         balance = None
            #     # print("BALANCE :: ",balance)
            #     if balance is not None:
            #         balance.amount = balance.amount - transaction_object.total_amount
            #         balance.save()

        if transaction_object.type == 'sale_order':
            # print("SALE ORDER TYPE")
            pass
            
        if transaction_object.type == 'sale':
            # print("SALE TYPE")
            linktrasactions = LinkTransaction.objects.filter(to_transaction_id=pk)
            # print("ALL LINKED TRANSACTION :: ", linktrasactions)
            for link in linktrasactions:
                from_transaction_id = link.from_transaction_id
                new_amount = link.linked_amount
                from_transaction = Transaction.objects.get(pk=from_transaction_id.id)

                if to_transaction in ('payment_in', 'payment_out'):
                    from_transaction.used_amount = from_transaction.used_amount - link.linked_amount
                else:
                    from_transaction.recived_or_paid_amount = from_transaction.recived_or_paid_amount - link.linked_amount
                
                from_transaction.save()

                print("New Amount ::: ", new_amount)
                balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

            from_linktrasactions = LinkTransaction.objects.filter(from_transaction_id=pk)
            print("ALL LINKED TRANSACTION :: ", linktrasactions)
            for from_link in from_linktrasactions:
                to_transaction_id = from_link.to_transaction_id
                new_amount = from_link.linked_amount
                to_trasaction = Transaction.objects.get(pk=to_transaction_id.id)

                if to_transaction in ('payment_in', 'payment_out'):
                    to_trasaction.used_amount = to_trasaction.used_amount - from_link.linked_amount
                else:
                    to_trasaction.recived_or_paid_amount = to_trasaction.recived_or_paid_amount - from_link.linked_amount
                
                to_trasaction.save()

                print("New Amount ::: ", new_amount)
                balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

            new_amount = transaction_object.total_amount - transaction_object.recived_or_paid_amount
            print("New Amount ::: ", new_amount)
            balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

            # if customer_id is not None:
            #     try:
            #         balance = Balance.objects.get(customer_id=customer_id)
            #     except:
            #         balance = None
            #     # print("BALANCE :: ",balance)
            #     if balance is not None:
            #         balance.amount = (balance.amount + transaction_object.advance_amount) - transaction_object.total_amount
            #         balance.save() 

            # if staff_id is not None:
            #         try:
            #             balance = Balance.objects.get(staff_id=staff_id)
            #         except:
            #             balance = None
            #         # print("BALANCE :: ",balance)
            #         if balance is not None:
            #             balance.amount = (balance.amount + transaction_object.advance_amount) - transaction_object.total_amount
            #             balance.save()

        if transaction_object.type == 'event_sale':
            # print("EVENT PURCHASE TYPE")
            linktrasactions = LinkTransaction.objects.filter(to_transaction_id=pk)
            # print("ALL LINKED TRANSACTION :: ", linktrasactions)
            for link in linktrasactions:
                from_transaction_id = link.from_transaction_id
                new_amount = link.linked_amount
                from_transaction = Transaction.objects.get(pk=from_transaction_id.id)

                if to_transaction in ('payment_in', 'payment_out'):
                    from_transaction.used_amount = from_transaction.used_amount - link.linked_amount
                else:
                    from_transaction.recived_or_paid_amount = from_transaction.recived_or_paid_amount - link.linked_amount
                
                from_transaction.save()

                print("New Amount ::: ", new_amount)
                balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

            from_linktrasactions = LinkTransaction.objects.filter(from_transaction_id=pk)
            print("ALL LINKED TRANSACTION :: ", linktrasactions)
            for from_link in from_linktrasactions:
                to_transaction_id = from_link.to_transaction_id
                new_amount = from_link.linked_amount
                to_trasaction = Transaction.objects.get(pk=to_transaction_id.id)

                if to_transaction in ('payment_in', 'payment_out'):
                    to_trasaction.used_amount = to_trasaction.used_amount - from_link.linked_amount
                else:
                    to_trasaction.recived_or_paid_amount = to_trasaction.recived_or_paid_amount - from_link.linked_amount
                
                to_trasaction.save()

                print("New Amount ::: ", new_amount)
                balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)
                
            new_amount = transaction_object.total_amount - transaction_object.recived_or_paid_amount
            print("New Amount ::: ", new_amount)
            balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

            # if customer_id is not None:
            #     try:
            #         balance = Balance.objects.get(customer_id=customer_id)
            #     except:
            #         balance = None
            #     # print("BALANCE :: ",balance)
            #     if balance is not None:
            #         balance.amount = (balance.amount + transaction_object.advance_amount) - transaction_object.total_amount
            #         balance.save()

            # if staff_id is not None:
            #     try:
            #         balance = Balance.objects.get(staff_id=staff_id)
            #     except:
            #         balance = None
            #     # print("BALANCE :: ",balance)
            #     if balance is not None:
            #         balance.amount = (balance.amount + (transaction_object.recived_or_paid_amount + transaction_object.settled_amount)) - transaction_object.total_amount
            #         balance.save()

            quotation_id = transaction_object.quotation_id
            # print("QUOTATION ID :: ",quotation_id)
            quotation = Quotation.objects.get(pk=quotation_id.id)
            # print("QUOTATION :: ",quotation)

            eventdays = EventDay.objects.filter(quotation_id=quotation_id.id)
            for eventday in eventdays:
                # print("Single Event Day :: ",eventday)
                # print("Event Day ID :: ",eventday.id)

                inventorydetails = InventoryDetails.objects.filter(eventday_id=eventday.id)
                for inventorydetail in inventorydetails:
                    # print("Single Inventory Detail :: ",inventorydetail)
                    # print("Inventory Detail ID :: ",inventorydetail.id)

                    exposuredetails = ExposureDetails.objects.filter(inventorydetails_id=inventorydetail.id)
                    # print("Exposure Details :: ",exposuredetails)

                    for exposuredetail in exposuredetails:
                        # print("Exposure Detail :: ",exposuredetail)

                        transaction = Transaction.objects.get(exposuredetails_id=exposuredetail.id)
                        # print("Transaction :: ",transaction)
                        # print("Staff ID :: ",transaction.staff_id.id)

                        balance = Balance.objects.get(staff_id=transaction.staff_id.id)
                        # print("Balance :: ",balance)
                        # print("Balance Amount :: ",balance.amount)
                        balance.amount = balance.amount + float(transaction.total_amount)
                        # print("Balance Amount :: ",balance.amount)
                        balance.save()

            quotation.delete()

        if transaction_object.type == 'purchase_order':
            # print("PURCHASE ORDER TYPE")
            pass
            
        if transaction_object.type == 'purchase':
            # print("PURCHASE TYPE")
            linktrasactions = LinkTransaction.objects.filter(to_transaction_id=pk)
            # print("ALL LINKED TRANSACTION :: ", linktrasactions)
            for link in linktrasactions:
                from_transaction_id = link.from_transaction_id
                new_amount = link.linked_amount
                from_transaction = Transaction.objects.get(pk=from_transaction_id.id)

                if to_transaction in ('payment_in', 'payment_out'):
                    from_transaction.used_amount = from_transaction.used_amount - link.linked_amount
                else:
                    from_transaction.recived_or_paid_amount = from_transaction.recived_or_paid_amount - link.linked_amount
                
                from_transaction.save()

                print("New Amount ::: ", new_amount)
                balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)
            
            from_linktrasactions = LinkTransaction.objects.filter(from_transaction_id=pk)
            print("ALL LINKED TRANSACTION :: ", linktrasactions)
            for from_link in from_linktrasactions:
                to_transaction_id = from_link.to_transaction_id
                new_amount = from_link.linked_amount
                to_trasaction = Transaction.objects.get(pk=to_transaction_id.id)

                if to_transaction in ('payment_in', 'payment_out'):
                    to_trasaction.used_amount = to_trasaction.used_amount - from_link.linked_amount
                else:
                    to_trasaction.recived_or_paid_amount = to_trasaction.recived_or_paid_amount - from_link.linked_amount
                
                to_trasaction.save()

                print("New Amount ::: ", new_amount)
                balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)
            
            new_amount = transaction_object.total_amount - transaction_object.recived_or_paid_amount
            print("New Amount ::: ", new_amount)
            balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

            # if customer_id is not None:
            #     try:
            #         balance = Balance.objects.get(customer_id=customer_id)
            #     except:
            #         balance = None
            #     # print("BALANCE :: ",balance)
            #     if balance is not None:
            #         balance.amount = (balance.amount - transaction_object.advance_amount) + transaction_object.total_amount
            #         balance.save()

            # if staff_id is not None:
            #         try:
            #             balance = Balance.objects.get(staff_id=staff_id)
            #         except:
            #             balance = None
            #         # print("BALANCE :: ",balance)
            #         if balance is not None:
            #             balance.amount = (balance.amount - transaction_object.advance_amount) + transaction_object.total_amount
            #             balance.save()

        if transaction_object.type == 'event_purchase':
            # print("EVENT PURCHASE TYPE")
            linktrasactions = LinkTransaction.objects.filter(to_transaction_id=pk)
            # print("ALL LINKED TRANSACTION :: ", linktrasactions)
            for link in linktrasactions:
                # print("SINGLE TRANACTION :: ", link)
                from_transaction_id = link.from_transaction_id
                # print("FROM TRANACTION ID :: ", from_transaction_id)
                new_amount = link.linked_amount
                # print("LINKED AMOUNT ::", link.linked_amount)
                from_transaction = Transaction.objects.get(pk=from_transaction_id.id)
                # print("TO TRANACTION :: ", from_transaction)

                if to_transaction in ('payment_in', 'payment_out'):
                    from_transaction.used_amount = from_transaction.used_amount - link.linked_amount
                else:
                    from_transaction.recived_or_paid_amount = from_transaction.recived_or_paid_amount - link.linked_amount
                
                from_transaction.save()

                print("New Amount ::: ", new_amount)
                balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

            from_linktrasactions = LinkTransaction.objects.filter(from_transaction_id=pk)
            print("ALL LINKED TRANSACTION :: ", linktrasactions)
            for from_link in from_linktrasactions:
                to_transaction_id = from_link.to_transaction_id
                new_amount = from_link.linked_amount
                to_trasaction = Transaction.objects.get(pk=to_transaction_id.id)

                if to_transaction in ('payment_in', 'payment_out'):
                    to_trasaction.used_amount = to_trasaction.used_amount - from_link.linked_amount
                else:
                    to_trasaction.recived_or_paid_amount = to_trasaction.recived_or_paid_amount - from_link.linked_amount
                
                to_trasaction.save()

                print("New Amount ::: ", new_amount)
                balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

            new_amount = transaction_object.total_amount - transaction_object.recived_or_paid_amount
            print("New Amount ::: ", new_amount)
            balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

            # if customer_id is not None:
            #     try:
            #         balance = Balance.objects.get(customer_id=customer_id)
            #     except:
            #         balance = None
            #     # print("BALANCE :: ",balance)
            #     if balance is not None:
            #         balance.amount = (balance.amount - transaction_object.advance_amount) + transaction_object.total_amount
            #         balance.save()

            # if staff_id is not None:
            #         try:
            #             balance = Balance.objects.get(staff_id=staff_id)
            #         except:
            #             balance = None
            #         # print("BALANCE :: ",balance)
            #         if balance is not None:
            #             balance.amount = (balance.amount - transaction_object.advance_amount) + transaction_object.total_amount
            #             balance.save()

        transaction_object.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


### API USED FOR GET TRASACTION AND LINK TRANSACTION ###
@api_view(['POST'])
def TransactionLink(request):
    if request.method == 'POST':
        data = {}
        customer_id = request.data.get('customer_id', None)
        # print("Customer ID :: ", customer_id)
        staff_id = request.data.get('staff_id', None)
        # print("Staff ID :: ", staff_id)
        transaction_type = request.data.get('transaction_type', None)
        # print("TYPE :: ", transaction_type)
        # from_transaction_id = request.data.get('from_transaction_id', None)
        # print("From Transaction ID :: ",from_transaction_id)
        # to_transaction_id = request.data.get('to_transaction_id', None)
        # print("To Transaction ID :: ",to_transaction_id)
        transaction_id = request.data.get('transaction_id', None)
        # print("Transaction ID :: ",transaction_id)

        if customer_id is not None:
            if transaction_type is not None:
                transaction = Transaction.objects.filter(Q(customer_id=customer_id), Q(type__in=transaction_type))
            else:
                transaction = Transaction.objects.filter(customer_id=customer_id)
                # print("transaction ::", transaction)

        if staff_id is not None:
            if transaction_type is not None:
                transaction = Transaction.objects.filter(Q(staff_id=staff_id), Q(type__in=transaction_type))
            else:
                transaction = Transaction.objects.filter(staff_id=staff_id)
                # print("transaction ::", transaction)
        data['transaction_data'] = TransactionSerializer(transaction, many=True).data

        # if from_transaction_id is not None:
        #     linktransaction = LinkTransaction.objects.filter(from_transaction_id=from_transaction_id)
        #     data['linktransaction'] = LinkTransactionSerializer(linktransaction, many=True).data

        # if to_transaction_id is not None:
        #     linktransaction = LinkTransaction.objects.filter(to_transaction_id=to_transaction_id)
        #     data['linktransaction'] = LinkTransactionSerializer(linktransaction, many=True).data

        if transaction_id is not None:
            linktransaction = LinkTransaction.objects.filter(Q(from_transaction_id=transaction_id) 
                                                            | Q(to_transaction_id=transaction_id))
            data['linktransaction'] = LinkTransactionSerializer(linktransaction, many=True).data

        return Response(data)


### API FOR STAFF AVAILABLE STATUS ###
@api_view(['GET', 'POST'])
def StaffStatus(request):
    if request.method == 'GET':
        user_id = request.query_params.get("user_id")
        # print("user_id ::", user_id)

        current_utc_datetime = datetime.datetime.utcnow()
        itc_timezone = pytz.timezone('Asia/Kolkata')
        current_itc_datetime = current_utc_datetime.astimezone(itc_timezone)
        current_itc_date = current_itc_datetime.date()
        # print("Current ITC Date:", current_itc_date)

        staffs = Staff.objects.filter(user_id=user_id)
        # print("staffs ::", staffs)
        data = []
        for staff in staffs:
            # print("Single Staff :: ",staff)
            # print("Staff ID :: ",staff.id)
            detail ={
                'staff_detail': {},
                'event_data': []
            }
            staffskill = StaffSkill.objects.filter(staff_id=staff.id)
            # print("STAFF SKILL :: ",staffskill)
            detail['staff_detail'] = {
                "staff_data" : StaffSerializer(staff).data,
                "staffskill_data" : StaffSkillSerializer(staffskill, many=True).data
            }

            exposuredetails = ExposureDetails.objects.filter(staff_id=staff.id)
            # print("exposuredetails :: ",exposuredetails)
            for exposuredetail in exposuredetails:
                # print("exposuredetail :: ",exposuredetail)

                event_details = exposuredetail.eventdetails.all()
                # print("event_details :: ", event_details)
                
                for event_detail in event_details:
                    details ={}
                    # print("event_detail :: ", event_detail)
                    # print("event_detail.eventday_id :: ", event_detail.eventday_id)
                    # print("event_detail.event_venue :: ", event_detail.event_venue)
                    # print("event_detail.start_time :: ", event_detail.start_time)
                    # print("event_detail.end_time :: ", event_detail.end_time)

                    eventday = EventDay.objects.get(pk=event_detail.eventday_id.id)
                    # print("eventday :: ", eventday)
                    # print("eventday.event_date :: ", eventday.event_date)

                    if eventday.event_date >= current_itc_date:
                        # print("EVENT DATE IS GREATER THAN CURRENT DATE")
                        details = {
                            'event_date': eventday.event_date.strftime('%Y-%m-%d'),
                            'event_venue': event_detail.event_venue,
                            'start_time': event_detail.start_time.strftime('%H:%M:%S'),
                            'end_time': event_detail.end_time.strftime('%H:%M:%S'),
                        }

                    # today = data.today()
                    # print("TODAY :: ", today)

                    # print("DETAILS :: ",details)
                        detail['event_data'].append(details)
            data.append(detail)
        # print("DATA ::: ", data)
        
        return Response(data)


### API FOR TODAY'S EVENT DETAILS ###
@api_view(['POST'])
def EventDetail(request):
    if request.method == 'POST':
        today = request.data.get('today', None)
        print("TODAY :: ", today)
        user_id = request.data.get('user_id', None)
        print("user_id :: ", user_id)

        eventdays = EventDay.objects.filter(event_date=today)
        print("EVENT DAYS :: ", eventdays)

        data = []

        for eventday in eventdays:
            transaction = Transaction.objects.get(quotation_id=eventday.quotation_id)
            print("TRANSACTION TYPE :: ", transaction.type)
            print("TRANSACTION USER ID :: ",transaction.user_id.id)
            if transaction.type == 'event_sale' and transaction.user_id.id == user_id:
                eventdetails = EventDetails.objects.filter(eventday_id=eventday.id)
                print("Event Details :: ",eventdetails)
                for eventdetail in eventdetails:
                    print("Event Detail :: ",eventdetail)
                    event_detail_data = {
                        'eventdetail_id': eventdetail.event_id.id,
                        'event_name': eventdetail.event_id.event_name,
                        'event_venue': eventdetail.event_venue,
                        'start_time': eventdetail.start_time,
                        'end_time': eventdetail.end_time,
                    }

                    exposuredetails = ExposureDetails.objects.filter(eventdetails__id=eventdetail.id)
                    print("Exposure Details :: ", exposuredetails)
                    if len(exposuredetails) == 0:
                        exposuredetail_data = {
                                'staff_name': '',
                                'staff_mobile_no': '',
                                'event_detail': [event_detail_data],  # Add the event_detail_data here
                            }
                        
                        customer_name = eventday.quotation_id.customer_id.full_name
                        customer_mobile_no = eventday.quotation_id.customer_id.mobile_no

                        # Find the customer data in the existing list or create a new entry
                        customer_entry = next((entry for entry in data if entry['customer_name'] == customer_name and entry['customer_mobile_no'] == customer_mobile_no), None)

                        if customer_entry:
                            staff_entry = next((staff for staff in customer_entry['exposuredetails_data'] if staff['staff_name'] == exposuredetail_data['staff_name'] and staff['staff_mobile_no'] == exposuredetail_data['staff_mobile_no']), None)

                            if staff_entry:
                                staff_entry['event_detail'].append(event_detail_data)
                            else:
                                customer_entry['exposuredetails_data'].append(exposuredetail_data)
                        else:
                            data.append({
                                'customer_name': customer_name,
                                'customer_mobile_no': customer_mobile_no,
                                'exposuredetails_data': [exposuredetail_data],
                            })
                    else:
                        for exposuredetail in exposuredetails:
                            print("Exposure Detail :: ", exposuredetail)
                            exposuredetail_data = {
                                'staff_name': exposuredetail.staff_id.full_name,
                                'staff_mobile_no': exposuredetail.staff_id.mobile_no,
                                'event_detail': [event_detail_data],  # Add the event_detail_data here
                            }

                            customer_name = eventday.quotation_id.customer_id.full_name
                            customer_mobile_no = eventday.quotation_id.customer_id.mobile_no

                            # Find the customer data in the existing list or create a new entry
                            customer_entry = next((entry for entry in data if entry['customer_name'] == customer_name and entry['customer_mobile_no'] == customer_mobile_no), None)

                            if customer_entry:
                                staff_entry = next((staff for staff in customer_entry['exposuredetails_data'] if staff['staff_name'] == exposuredetail_data['staff_name'] and staff['staff_mobile_no'] == exposuredetail_data['staff_mobile_no']), None)

                                if staff_entry:
                                    staff_entry['event_detail'].append(event_detail_data)
                                else:
                                    customer_entry['exposuredetails_data'].append(exposuredetail_data)
                            else:
                                data.append({
                                    'customer_name': customer_name,
                                    'customer_mobile_no': customer_mobile_no,
                                    'exposuredetails_data': [exposuredetail_data],
                                })

        return Response(data)


class LinkTransactionViewSet(viewsets.ModelViewSet):
    queryset = LinkTransaction.objects.all().order_by('-id').distinct()
    serializer_class = LinkTransactionSerializer


class BalanceViewSet(viewsets.ModelViewSet):
    queryset = Balance.objects.all().order_by('-id').distinct()
    serializer_class = BalanceSerializer


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


### EXPORT CUSTOMER DETAILS TO EXCEL ###
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
        # print(":: DATA SET ::")
        # print(data_set)

        file_name = data_set.xlsx
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        return HttpResponse(file_name, content_type=content_type)


### EXPORT QUOTATION DETAILS TO EXCEL ###
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
        # print("FROM DATE :: ",from_date)
        to_date = self.request.query_params.get('to_date')
        # print("TO DATE :: ",to_date)

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
        # print(":: DATA SET ::")
        # print(data_set)

        file_name = data_set.xlsx
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        return HttpResponse(file_name, content_type=content_type)
    
    def retrieve(self, request, *args, **kwarge):
        instance = self.get_object()
        # print("INSTANCE :: ",instance)
        quotation_resource = QuotationResource()
        # print("quotation_resource", quotation_resource)
        data_set = quotation_resource.export([instance])
        # print(":: DATA SET ::")
        # print(data_set)

        file_name = data_set.xlsx
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        return HttpResponse(file_name, content_type=content_type)


### EXPORT TRANSACTION DETAILS TO EXCEL ###
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
        # print(":: DATA SET ::")
        # print(data_set)

        file_name = data_set.xlsx
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        return HttpResponse(file_name, content_type=content_type)
    
    def retrieve(self, request, *args, **kwarge):
        instance = self.get_object()
        # print("INSTANCE :: ",instance)
        transaction_resource = TransactionResource()
        # print("transaction_resource", transaction_resource)
        data_set = transaction_resource.export([instance])
        # print(":: DATA SET ::")
        # print(data_set)

        file_name = data_set.xlsx
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        return HttpResponse(file_name, content_type=content_type)
    

### EXPORT INVOICE DETAILS TO EXCEL ###
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
        # print("FROM DATE :: ",from_date)
        to_date = self.request.query_params.get('to_date')
        # print("TO DATE :: ",to_date)

        if from_date and to_date:
            try:
                queryset = queryset.filter(converted_on__range=[from_date, to_date])
                # print("queryset ::: ", queryset)
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
        # print("STATUS :: ", status)
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


### CONVERT BUCKET URL TO BASE 64 URL
@api_view(['POST'])
def ConvertBucketURL(request):
    if request.method == 'POST':
        s3_bucket_url = request.data.get('s3_bucket_url', None)
        # print("s3_bucket_url ::: ",s3_bucket_url)
        if s3_bucket_url is not None:
            response = requests.get(s3_bucket_url)
            image_data = response.content
            base64_image = base64.b64encode(image_data).decode()
            data_url = f"data:image/jpeg;base64,{base64_image}"
            # print("Data URL:", data_url)
        
        return Response(data_url)


### TOTAL SALE
@api_view(['POST'])
def TotalSale(request):
    if request.method == 'POST':
        user_id = request.data.get('user_id', None)
        # print('user_id ::: ', user_id)
        start_date = request.data.get('start_date', None)
        # print("START ::", start_date)
        end_date = request.data.get('end_date', None)
        # print("END ::", end_date)

        if start_date is None and end_date is None:
            total_amount = Transaction.objects.filter(user_id=user_id, type__in=['sale', 'event_sale']).aggregate(Sum('total_amount'))['total_amount__sum']
            # print('total_amount ::: ',total_amount)
        else:
            total_amount = Transaction.objects.filter(user_id=user_id, created_on__range=[start_date, end_date], type__in=['sale', 'event_sale']).aggregate(Sum('total_amount'))['total_amount__sum']
            # print('total_amount ::: ',total_amount)

        return Response(total_amount)


### TOTAL EXPENSES
@api_view(['POST'])
def TotalExpense(request):
    if request.method == 'POST':
        user_id = request.data.get('user_id', None)
        # print('user_id ::: ', user_id)
        start_date = request.data.get('start_date', None)
        # print("START ::", start_date)
        end_date = request.data.get('end_date', None)
        # print("END ::", end_date)

        if start_date is None and end_date is None:
            total_amount = Transaction.objects.filter(user_id=user_id, type__in=['expense']).aggregate(Sum('total_amount'))['total_amount__sum']
            # print('total_amount ::: ',total_amount)
        else:
            total_amount = Transaction.objects.filter(user_id=user_id, created_on__range=[start_date, end_date], type__in=['expense']).aggregate(Sum('total_amount'))['total_amount__sum']
            # print('total_amount ::: ',total_amount)

        return Response(total_amount)


### TOTAL RECIVED AMOUNT
@api_view(['POST'])
def TotalAmount(request):
    if request.method == 'POST':
        user_id = request.data.get('user_id', None)
        # print('user_id ::: ', user_id)
        data = {
            # "you'll recived" : [],
            # "you'll pay": [],
        }
        total_recived = 0
        total_paied = 0
        customers = Customer.objects.filter(user_id=user_id)
        for customer in customers:
            # print("Single Customer ::: ",customer)
            # print("Customer ID ::: ",customer.id)
        
            total_recived_amount = Transaction.objects.filter(customer_id=customer.id, type__in=['sale','event_sale','payment_out']).aggregate(Sum('total_amount'))['total_amount__sum']
            total_recived_amount = total_recived_amount if total_recived_amount is not None else 0
            # print("TOTAL RECEIVED AMOUNT ::: ",total_recived_amount)

            total_pay_amount = Transaction.objects.filter(customer_id=customer.id, type__in=['purchase','event_purchase','payment_in']).aggregate(Sum('total_amount'))['total_amount__sum']
            total_pay_amount = total_pay_amount if total_pay_amount is not None else 0
            # print("TOTAL PAY AMOUNT ::: ",total_pay_amount)

            total = total_recived_amount - total_pay_amount
            # print("TOTAL ::: ",total)

            if total > 0:
                # data["you'll recived"].append({'customer_name': customer.full_name,
                #                                'amount':total})
                total_recived = total_recived + total
            elif total < 0:
                # data["you'll pay"].append({'customer_name': customer.full_name,
                #                            'amount':total})
                total_paied = total_paied + (-total)

        data['total_recived'] = total_recived
        data['total_paied'] = total_paied

        return Response(data)


### TOTAL PURCHASE
@api_view(['POST'])
def TotalPurchase(request):
    if request.method == 'POST':
        user_id = request.data.get('user_id', None)
        # print('user_id ::: ', user_id)
        start_date = request.data.get('start_date', None)
        # print("START ::", start_date)
        end_date = request.data.get('end_date', None)
        # print("END ::", end_date)

        if start_date is None and end_date is None:
            total_amount = Transaction.objects.filter(user_id=user_id, type__in=['purchase','event_purchase']).aggregate(Sum('total_amount'))['total_amount__sum']
            # print('total_amount ::: ',total_amount)
        else:
            total_amount = Transaction.objects.filter(user_id=user_id, created_on__range=[start_date, end_date], type__in=['purchase','event_purchase']).aggregate(Sum('total_amount'))['total_amount__sum']
            # print('total_amount ::: ',total_amount)

        return Response(total_amount)


### ConversationReport
@api_view(['POST'])
def ConversationRateReport(request):
    if request.method == 'POST':
        user = request.data.get('user_id')
        # print("USER ::", user)
        start_date = request.data.get('start_date', None)
        # print("START ::", start_date)
        end_date = request.data.get('end_date', None)
        # print("END ::", end_date)

        report = {}

        total = Transaction.objects.filter(user_id = user, type='estimate').count()
        # print("Total ::", total)
        report['total'] = total

        if start_date is None and end_date is None:
            not_converted = Transaction.objects.filter(user_id = user, type='estimate', is_converted=False).count()
            # print("not_converted ::: ",not_converted)
            report['not_converted'] = not_converted

            converted = Transaction.objects.filter(user_id = user, type='estimate', is_converted=True).count()
            # print("converted ::: ",converted)
            report['converted'] = converted
        else:
            not_converted = Transaction.objects.filter(user_id = user, type='estimate', is_converted=False, created_on__range=[start_date, end_date]).count()
            # print("not_converted ::: ",not_converted)
            report['not_converted'] = not_converted

            converted = Transaction.objects.filter(user_id = user, type='estimate', is_converted=True, created_on__range=[start_date, end_date]).count()
            # print("converted ::: ",converted)
            report['converted'] = converted

        return Response(report)


### Invoice Status
@api_view(['POST'])
def InvoiceStatusReport(request):
    if request.method == 'POST':
        user = request.data.get('user_id')
        # print("USER ::", user)
        start_date = request.data.get('start_date', None)
        # print("START ::", start_date)
        end_date = request.data.get('end_date', None)
        # print("END ::", end_date)

        report = {}
        report['completed'] = 0
        report['pending'] = 0

        if start_date is None and end_date is None:
            transactions = Transaction.objects.filter(user_id=user, type__in=['event_sale','sale','event_purchase','purchase'])
            # print("Transactions :: ",transactions)
        else:
            transactions = Transaction.objects.filter(user_id=user, type__in=['event_sale','sale','event_purchase','purchase'], created_on__range=[start_date, end_date])
            # print("Transactions :: ",transactions)

        for transaction in transactions:
            # print('transaction :: ', transaction)
            # print("STATUS :: ", transaction.total_amount == (transaction.recived_or_paid_amount + transaction.settled_amount))
            if transaction.total_amount == (transaction.recived_or_paid_amount + transaction.settled_amount):
                report['completed'] += 1
            else:
                report['pending'] += 1

        return Response(report)


### Invoice Panding for Completion
@api_view(['POST'])
def CompletionReport(request):
    if request.method == 'POST':
        user = request.data.get('user_id')
        # print("USER ::", user)
        start_date = request.data.get('start_date', None)
        # print("START ::", start_date)
        end_date = request.data.get('end_date', None)
        # print("END ::", end_date)
        
        data = []

        if start_date is None and end_date is None:
            transactions = Transaction.objects.filter(user_id=user, type='event_sale')
            # print("TRANSACTIONS ::", transactions)
        else:
            transactions = Transaction.objects.filter(user_id=user, created_on__range=[start_date, end_date], type__in=['event_sale', 'estimate'])
            # print("TRANSACTIONS ::", transactions)

        for transaction in transactions:
            # print("Transaction ::", transaction)
            # print("Quotation ID ::", transaction.quotation_id.id)

            quotation = Quotation.objects.get(pk=transaction.quotation_id.id)
            # print("Quotation ::", quotation)
            # print("Quotation ID ::", quotation.id)

            eventdays = EventDay.objects.filter(quotation_id=quotation.id)
            # print("Event Days ::", eventdays)

            for eventday in eventdays:
                # print("Event Day ::", eventday)
                # print("Event Day ID ::", eventday.id)

                inventorydetails = InventoryDetails.objects.filter(eventday_id=eventday.id)
                # print("Inventory Details ::", inventorydetails)

                for inventorydetail in inventorydetails:
                    # print("Inventory Detail ::", inventorydetail)
                    # print("Inventory Detail ID ::", inventorydetail.id)

                    exposuredetails = ExposureDetails.objects.filter(inventorydetails_id=inventorydetail.id)
                    # print("LENGTH ::", len(exposuredetails))
                    if len(exposuredetails) == 0:
                        data.append(transaction)
                        break

        print("DATA :: ",data)
        return Response(TransactionSerializer(data, many=True).data)


### Cash & Bank 
@api_view(['POST'])
def CashAndBank(request):
    if request.method == 'POST':
        user = request.data.get('user_id')
        print("USER ::", user)


        cash_payment_in = Transaction.objects.filter(user_id=user, payment_type='cash', type__in=['payment_in']).aggregate(Sum('total_amount'))['total_amount__sum']
        cash_payment_in = cash_payment_in if cash_payment_in is not None else 0
        print("cash_payment_in ::", cash_payment_in)
        cash_payment_out = Transaction.objects.filter(user_id=user, payment_type='cash', type__in=['payment_out']).aggregate(Sum('total_amount'))['total_amount__sum']
        cash_payment_out = cash_payment_out if cash_payment_out is not None else 0
        print("cash_payment_out ::", cash_payment_out)
        cash_sale = Transaction.objects.filter(user_id=user, payment_type='cash', type__in=['sale','event_sale']).aggregate(Sum('advance_amount'))['advance_amount__sum']
        cash_sale = cash_sale if cash_sale is not None else 0
        print("cash_sale ::", cash_sale)
        cash_purchase = Transaction.objects.filter(user_id=user, payment_type='cash', type__in=['purchase','event_purchase']).aggregate(Sum('advance_amount'))['advance_amount__sum']
        cash_purchase = cash_purchase if cash_purchase is not None else 0
        print("cash_purchase ::", cash_purchase)
        

        cheque_payment_in = Transaction.objects.filter(user_id=user, payment_type='cheque', type__in=['payment_in']).aggregate(Sum('total_amount'))['total_amount__sum']
        cheque_payment_in = cheque_payment_in if cheque_payment_in is not None else 0
        print("cheque_payment_in ::", cheque_payment_in)
        cheque_payment_out = Transaction.objects.filter(user_id=user, payment_type='cheque', type__in=['payment_out']).aggregate(Sum('total_amount'))['total_amount__sum']
        cheque_payment_out = cheque_payment_out if cheque_payment_out is not None else 0
        print("cheque_payment_out ::", cheque_payment_out)
        cheque_sale = Transaction.objects.filter(user_id=user, payment_type='cheque', type__in=['sale','event_sale']).aggregate(Sum('advance_amount'))['advance_amount__sum']
        cheque_sale = cheque_sale if cheque_sale is not None else 0
        print("cheque_sale ::", cheque_sale)
        cheque_purchase = Transaction.objects.filter(user_id=user, payment_type='cheque', type__in=['purchase','event_purchase']).aggregate(Sum('advance_amount'))['advance_amount__sum']
        cheque_purchase = cheque_purchase if cheque_purchase is not None else 0
        print("cheque_purchase ::", cheque_purchase)


        net_banking_payment_in = Transaction.objects.filter(user_id=user, payment_type='net_banking', type__in=['payment_in']).aggregate(Sum('total_amount'))['total_amount__sum']
        net_banking_payment_in = net_banking_payment_in if net_banking_payment_in is not None else 0
        print("net_banking_payment_in ::", net_banking_payment_in)
        net_banking_payment_out = Transaction.objects.filter(user_id=user, payment_type='net_banking', type__in=['payment_out']).aggregate(Sum('total_amount'))['total_amount__sum']
        net_banking_payment_out = net_banking_payment_out if net_banking_payment_out is not None else 0
        print("net_banking_payment_out ::", net_banking_payment_out)
        net_banking_sale = Transaction.objects.filter(user_id=user, payment_type='net_banking', type__in=['sale','event_sale']).aggregate(Sum('advance_amount'))['advance_amount__sum']
        net_banking_sale = net_banking_sale if net_banking_sale is not None else 0
        print("net_banking_sale ::", net_banking_sale)
        net_banking_purchase = Transaction.objects.filter(user_id=user, payment_type='net_banking', type__in=['purchase','event_purchase']).aggregate(Sum('advance_amount'))['advance_amount__sum']
        net_banking_purchase = net_banking_purchase if net_banking_purchase is not None else 0
        print("net_banking_purchase ::", net_banking_purchase)


        upi_payment_in = Transaction.objects.filter(user_id=user, payment_type='upi', type__in=['payment_in']).aggregate(Sum('total_amount'))['total_amount__sum']
        upi_payment_in = upi_payment_in if upi_payment_in is not None else 0
        print("upi_payment_in ::", upi_payment_in)
        upi_payment_out = Transaction.objects.filter(user_id=user, payment_type='upi', type__in=['payment_out']).aggregate(Sum('total_amount'))['total_amount__sum']
        upi_payment_out = upi_payment_out if upi_payment_out is not None else 0
        print("upi_payment_out ::", upi_payment_out)
        upi_sale = Transaction.objects.filter(user_id=user, payment_type='upi', type__in=['sale','event_sale']).aggregate(Sum('advance_amount'))['advance_amount__sum']
        upi_sale = upi_sale if upi_sale is not None else 0
        print("upi_sale ::", upi_sale)
        upi_purchase = Transaction.objects.filter(user_id=user, payment_type='upi', type__in=['purchase','event_purchase']).aggregate(Sum('advance_amount'))['advance_amount__sum']
        upi_purchase = upi_purchase if upi_purchase is not None else 0
        print("upi_purchase ::", upi_purchase)


        data = {'total_cash': (cash_payment_in + cash_sale) - (cash_payment_out + cash_purchase),
                'total_cheque': (cheque_payment_in + cheque_sale) - (cheque_payment_out + cheque_purchase),
                'total_net_banking': (net_banking_payment_in + net_banking_sale) - (net_banking_payment_out + net_banking_purchase),
                'total_upi': (upi_payment_in + upi_sale) - (upi_payment_out + upi_purchase)}

        print("DATA ::: ",data)
        return Response(data)



# @api_view(['POST'])
# def MonthylyEarningReport(request):
#     if request.method == 'POST':
#         data = []
#         user = request.data.get('user_id')
#         # print("USER ::", user)
#         start_date = request.data.get('start_date', None)
#         # print("START ::", start_date)
#         end_date = request.data.get('end_date', None)
#         # print("END ::", end_date)

#         if start_date is None and end_date is None:
#             result = Transaction.objects.filter(quotation_id__user_id=user).annotate(month=TruncMonth('date')).values('month').annotate(total_amount=Sum('amount')).order_by('month')
#             for entry in result:
#                 data.append({"month": entry['month'].strftime('%B %Y'),
#                              "total_amount":entry['total_amount']})
#                 # print(f"Month: {entry['month'].strftime('%B %Y')}, Total Amount: {entry['total_amount']}")
#         else:
#             result = Transaction.objects.filter(quotation_id__user_id=user, 
#                                                 date__range=[start_date, end_date]).annotate(month=TruncMonth('date')).values('month').annotate(total_amount=Sum('amount')).order_by('month')
#             for entry in result:
#                 data.append({"month": entry['month'].strftime('%B %Y'),
#                              "total_amount":entry['total_amount']})
#                 # print(f"Month: {entry['month'].strftime('%B %Y')}, Total Amount: {entry['total_amount']}")
        
#         return Response(data)


# @api_view(['POST'])
# def InvoiceCreationReport(request):
#     if request.method == 'POST':
#         data = []
#         user = request.data.get('user_id')
#         # print("USER ::", user)
#         start_date = request.data.get('start_date', None)
#         # print("START ::", start_date)
#         end_date = request.data.get('end_date', None)
#         # print("END ::", end_date)
#         type = request.data.get('type')
#         # print("TYPE ::", type)

#         if start_date is None and end_date is None:

#             if type == 'per_month':
#                 result = Quotation.objects.filter(user_id=user, 
#                                                    is_converted=True).annotate(month=TruncMonth('converted_on')).values('month').annotate(converted_count=Count('id')).order_by('month')
                
#                 for entry in result:
#                     data.append({"month": entry['month'].strftime('%B %Y'),
#                              "converted_count":entry['converted_count']})
#                     # print(f"Month: {entry['month'].strftime('%B %Y')}, Converted Count: {entry['converted_count']}")
            
#             if type == 'per_year':
#                 result = Quotation.objects.filter(user_id=user,
#                                                     is_converted=True).annotate(year=TruncYear('converted_on')).values('year').annotate(converted_count=Count('id')).order_by('year')
                
#                 for entry in result:
#                     data.append({"year": entry['year'].strftime('%Y'),
#                              "converted_count":entry['converted_count']})
#                     # print(f"Year: {entry['year'].strftime('%Y')}, Converted Count: {entry['converted_count']}")
#         else:

#             if type == 'per_month':
#                 result = Quotation.objects.filter(user_id=user,
#                                                     is_converted=True, 
#                                                     converted_on__range=[start_date, end_date]).annotate(month=TruncMonth('converted_on')).values('month').annotate(converted_count=Count('id')).order_by('month')
                
#                 for entry in result:
#                     data.append({"month": entry['month'].strftime('%B %Y'),
#                              "converted_count":entry['converted_count']})
#                     # print(f"Month: {entry['month'].strftime('%B %Y')}, Converted Count: {entry['converted_count']}")
            
#             if type == 'per_year':
#                 result = Quotation.objects.filter(user_id=user, 
#                                                    is_converted=True, 
#                                                    converted_on__range=[start_date, end_date]).annotate(year=TruncYear('converted_on')).values('year').annotate(converted_count=Count('id')).order_by('year')
                
#                 for entry in result:
#                     data.append({"year": entry['year'].strftime('%Y'),
#                              "converted_count":entry['converted_count']})
#                     # print(f"Year: {entry['year'].strftime('%Y')}, Converted Count: {entry['converted_count']}")

#         return Response(data)
    
