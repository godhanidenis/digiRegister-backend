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
import logging
import sys

# Create your views here.

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-id').distinct()
    serializer_class = UserSerializer
    pagination_class = MyPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields ={
        'full_name':['icontains'],
        'mobile_no':['icontains'],
        'email':['icontains'],
        'address':['icontains'],
        'shop_name':['icontains'],
        'type_of_user':['in']
    }

    def retrieve(self, request, *args, **kwarge):
        try:
            instance = self.get_object()
            terms = TermsAndConditions.objects.filter(user_id=instance.id)

            return Response({'user_data' : UserSerializer(instance).data,
                            'terms' : TermsAndConditionsSerializer(terms, many=True).data})
        except Exception as e:
            logger.error(f"API: User Retrieve - An error occurred: {str(e)}", exc_info=True)
            return Response({"error": "An error occurred while retrieving the object."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, pk=None, *args, **kwargs):
        try:
            user = User.objects.get(pk=pk)
            old_pic = f"profile_pic/{os.path.basename(user.profile_pic)}" if user.profile_pic else None
            old_signature = f"signature/{os.path.basename(user.signature)}" if user.signature else None

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
                            aws_secret_access_key=config('wasabisys_secret_access_key'))

            ## ADD USER PROFILE PIC IN BUCKET ##
            if 'profile_pic' in request.data:
                profile_pic = request.data['profile_pic']

                if profile_pic == '':
                    print("profile_pic is Null")
                    # DELETE OLD PIC FORM BUCKET #
                    if old_pic:
                        s3.delete_object(Bucket = bucket_name, 
                                        Key=old_pic)
                else:
                    print("profile_pic is not Null")
                    # DELETE OLD PIC FORM BUCKET #
                    if old_pic:
                        s3.delete_object(Bucket = bucket_name, 
                                        Key=old_pic)
                    
                    file = request.data['profile_pic']
                    file_name = f"profile_pic/{uuid.uuid4().hex}.jpg"

                    # ADD NEW PIC IN BUCKET #
                    s3.upload_fileobj(file, bucket_name, file_name)
                    s3_file_url = f"https://s3.{region}.wasabisys.com/{bucket_name}/{file_name}"
                    request.data['profile_pic'] = s3_file_url

            ## ADD USER SIGNATURE IN BUCKET ##
            if 'signature' in request.data:
                signature = request.data['signature']
                
                if signature == '':
                    print("Signature is Null")
                    # DELETE OLD SIGNATURE FORM BUCKET #
                    if old_signature:
                        s3.delete_object(Bucket = bucket_name, 
                                        Key=old_signature)
                else:
                    print("Signature is not Null")
                    # DELETE OLD SIGNATURE FORM BUCKET #
                    if old_signature:
                        s3.delete_object(Bucket = bucket_name, 
                                        Key=old_signature)
                    
                    file = request.data['signature']
                    file_name = f"signature/{uuid.uuid4().hex}.jpg"

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
        
        except Exception as e:
            logger.error(f"API: User Update - An error occurred: {str(e)}.\nRequest data: {request.data}", exc_info=True)
            return Response({"error": "An error occurred while updating the object."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TermsAndConditionsViewSet(viewsets.ModelViewSet):
    queryset = TermsAndConditions.objects.all().order_by('-id').distinct()
    serializer_class = TermsAndConditionsSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields ={
        'user_id__id':['exact'],
    }

    # def retrieve(self, request, pk=None):
    #     logger.info(f"Retrieving object with ID {pk}.")
    #     try:
    #         return super().retrieve(request, pk)
    #     except Exception as e:
    #         # logger.error(f"Error retrieving object with ID {pk}: {str(e)}")
    #         logger.error(f"API: Terms And Conditions Retrieve - An error occurred: {str(e)}.\nPK : {pk}", exc_info=True)
    #         return Response({"error": "An error occurred while retrieving the object."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
        'id':['exact'],
        'user_id__id':['exact'],
        'full_name':['icontains'],
        'mobile_no':['icontains'],
        'email':['icontains'],
        'address':['icontains']
    }

    def list(self, request):
        try:
            querysets = self.filter_queryset(self.get_queryset())
            paginator = MyPagination()  
            paginated_queryset = paginator.paginate_queryset(querysets, request)
            data = []
            for queryset in paginated_queryset:
                total_amount = Balance.objects.filter(customer_id=queryset.id).aggregate(Sum('amount'))['amount__sum']
                data.append({'customer': CustomerSerializer(queryset).data,
                            'total_amount': total_amount })
            
            return paginator.get_paginated_response(data)
        
        except Exception as e:
            logger.error(f"API: Customer List - An error occurred: {str(e)}", exc_info=True)
            return Response({"error": "An error occurred while listing the object."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class InventoryViewSet(viewsets.ModelViewSet):
    queryset = Inventory.objects.all().order_by('-id').distinct()
    serializer_class = InventorySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'user_id__id':['exact'],
        'type':['exact'],
        'name':['icontains']
    }

    # def dispatch(self, request, *args, **kwargs):
    #     try:
    #         return super().dispatch(request, *args, **kwargs)
    #     except Exception as e:
    #         # Log the exception using the logger
    #         logger.error('An error occurred in InventoryViewSet', exc_info=e)
    #         logger.error(f"API: Inventory View Set - An error occurred: {str(e)}", exc_info=True)
    #         raise


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
        try:
            querysets = self.filter_queryset(self.get_queryset())
            data = []
            for queryset in querysets:
                total_amount = Balance.objects.filter(staff_id=queryset.id).aggregate(Sum('amount'))['amount__sum']

                data.append({'staff': StaffSerializer(queryset).data, 
                            'total_amount': total_amount}) 
                
            return Response(data)
        except Exception as e:
            logger.error(f"API: Staff List - An error occurred: {str(e)}", exc_info=True)
            return Response({"error": "An error occurred while listing the object."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, *args, **kwarge):
        try:
            instance = self.get_object()
            staff_id = instance.id
            staffskill = StaffSkill.objects.filter(staff_id=staff_id)
            data = {"staff_data" : StaffSerializer(instance).data,
                    "staffskill_data" : StaffSkillSerializer(staffskill, many=True).data}

            return Response(data)
        except Exception as e:
            logger.error(f"API: Staff Retrieve - An error occurred: {str(e)}", exc_info=True)
            return Response({"error": "An error occurred while retrieving the object."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, *args, **kwargs):
        try:
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

                response_data = {'staff': staffSerializer.data,
                                'skills': StaffSkillSerializer(staff_skill_instances, many=True).data}
                
                return Response(response_data, status=status.HTTP_201_CREATED)
            else:
                return Response(staffSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"API: Staff Create - An error occurred: {str(e)}.\nRequest data: {request.data}", exc_info=True)
            return Response({"error": "An error occurred while creating the object."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, pk=None, *args, **kwargs):
        try:
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
        except Exception as e:
            logger.error(f"API: Staff Update - An error occurred: {str(e)}.\nRequest data: {request.data}", exc_info=True)
            return Response({"error": "An error occurred while updating the object."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
                queryset = queryset.filter(converted_on__range=[from_date, to_date])
            except ValueError:
                pass

        return queryset

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()

            return Response(quotation_get(instance.id))
        except Exception as e:
            logger.error(f"API: Quotation Retrieve - An error occurred: {str(e)}", exc_info=True)
            return Response({"error": "An error occurred while retrieving the object."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, *args, **kwargs):
        try:
            quotation =request.data['quotation_data']
            datas = request.data['datas']
            transaction = request.data['transaction_data']
            linktransaction_data = request.data.get('linktransaction_data', None)

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

            # quotation_data(quotation_instance.id, datas)

            for data in datas:
                ### FOR ADD EVENT DAY DATA ###
                eventdate_data = {'event_date': data['event_date'],
                                'quotation_id':quotation_instance.id}
                eventdaySerializer = EventDaySerializer(data=eventdate_data)
                if eventdaySerializer.is_valid():
                    eventday_instance = eventdaySerializer.save()
                    final_evnetday_data.append(eventday_instance)
                else:
                    return Response(eventdaySerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                ### FOR ADD EVENT DETAILS DATA ###
                eventdetails_datas = data['event_details']
                for eventdetails_data in eventdetails_datas:
                    eventdetails_data['eventday_id'] = eventday_instance.id
                    eventdetails_data['quotation_id'] = quotation_instance.id

                    eventdetailsSerializer = EventDetailsSerializer(data=eventdetails_data)
                    if eventdetailsSerializer.is_valid():
                        eventdetails_instance = eventdetailsSerializer.save()
                        final_eventdetails_data.append(eventdetails_instance)
                    else:
                        return Response(eventdetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                descriptions = data['descriptions']
                for description in descriptions:
                    ### FOR INVENTORY DETAILS DATA ###
                    inventorydetails_data = {
                        'inventory_id':description.pop('inventory_id'),
                        'price':description.pop('price'),
                        'qty':description.pop('qty'),
                        'profit':description.pop('profit'),
                        'eventday_id':eventday_instance.id}
                    
                    inventorydetailsSerializer = InventoryDetailsSerializer(data=inventorydetails_data)
                    if inventorydetailsSerializer.is_valid():
                        inventorydetails_instance = inventorydetailsSerializer.save()
                        final_inventorydetails_data.append(inventorydetails_instance)
                    else:
                        return Response(inventorydetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    
                    inventory = Inventory.objects.get(pk=inventorydetails_data['inventory_id'])
                    if inventory.type == 'service':
                        ### FOR EXPOSURE DETAILS DATA ###
                        exposuredetails = description.get('exposure', None)
                        if exposuredetails is not None:
                            for exposuredetail in exposuredetails:
                                evnetdetials =[]
                                allocations = exposuredetail['allocation']
                                for i in range(len(final_eventdetails_data)):
                                    single_eventdetails = final_eventdetails_data.pop(0)
                                    for allocation in allocations:
                                        event_id = single_eventdetails.event_id.id
                                        if event_id == int(allocation):
                                            evnetdetials.append(single_eventdetails.id)
                                exposuredetails_data = {
                                    'staff_id':exposuredetail['staff_id'],
                                    'price':exposuredetail['price'],
                                    'eventdetails':evnetdetials,
                                    'inventorydetails_id':inventorydetails_instance.id}
                                exposuredetailsSerializer = ExposureDetailsSerializer(data=exposuredetails_data)
                                if exposuredetailsSerializer.is_valid():
                                    exposuredetails_instance = exposuredetailsSerializer.save()
                                    final_exposuredetails_data.append(exposuredetails_instance)
                                else:
                                    return Response(exposuredetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

            ### FOR ADD TRANSACTION DATA ###
            if transaction['is_converted'] == 'true':
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
                balance_amount(quotation_instance.customer_id.id, None, 0 , new_amount, transaction_instance.type)

            ### LINK TRNASACTION 
            if transaction['is_converted'] == 'true' and linktransaction_data is not None:
                link_transaction(transaction_instance.id, linktransaction_data, transaction_instance.type)

            ### ADD BILL FOR EXOISURE ###

            updated_exposuredetails_data = remove_exposure(final_exposuredetails_data)
            # print("updated_exposuredetails_data :: ",updated_exposuredetails_data)

            if transaction['is_converted'] == 'true':
                finall_instance = []
                for i in updated_exposuredetails_data:
                    i_transaction_data = {
                        'user_id' : transaction['user_id'],
                        'type' : "event_purchase",
                        'staff_id' : i['staff_id'],
                        'total_amount' : i["price_sum"],
                        'exposuredetails_ids' : i["exposuredetails_ids"],
                        'parent_transaction' : transaction_instance.id,
                        'date': date.today()}
                    i_transactionSerializer = TransactionSerializer(data=i_transaction_data)
                    if i_transactionSerializer.is_valid():
                        t_instance = i_transactionSerializer.save()
                        finall_instance.append(t_instance)
                    else:
                        return Response(i_transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    
                    new_amount = t_instance.total_amount - t_instance.recived_or_paid_amount
                    balance_amount(None, t_instance.staff_id.id, 0 , new_amount, t_instance.type)

            return Response(quotation_get(quotation_instance.id))
        except Exception as e:
            logger.error(f"API: Quotation Create - An error occurred: {str(e)}.\nRequest data: {request.data}", exc_info=True)
            return Response({"error": "An error occurred while creating the object."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, pk=None, *args, **kwargs):
        try:
            quotation_data = request.data.get('quotation_data', None)
            copy_quotation_data = quotation_data
            datas = request.data.get('datas', None)
            copy_datas = datas
            delete_exposures = request.data.get('delete_exposure', None)
            delete_inventorys = request.data.get('delete_inventory', None)
            delete_events = request.data.get('delete_event', None)
            delete_eventdays = request.data.get('delete_eventday', None)
            transaction_data = request.data.get('transaction_data', None)
            linktransaction_data = request.data.get('linktransaction_data', None)

            transaction = Transaction.objects.get(quotation_id = pk)
            old_amount = transaction.total_amount - transaction.recived_or_paid_amount

            ### NOT CONVERTED TRANSACTION ###
            if transaction.is_converted == False:
                convert_status = transaction_data['is_converted']
                ### FOR UPDATE QUOTATION DATA ###
                quotation = Quotation.objects.get(pk=pk)
                q_serializer = QuotationSerializer(quotation, data=quotation_data, partial=True)
                if q_serializer.is_valid():
                    quotation_instance = q_serializer.save()
                else:
                    return Response(q_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                final_eventdetails_data = []
                final_inventorydetails_data = []
                final_exposuredetails_data = []

                ### FOR ADD AND UPDATE OTHER DATA ### 
                if datas is not None:
                    for data in datas:
                        ### FOR ADD AND UPDATE EVENT DAY ###
                        eventdate_data = {
                            'id': data['id'],
                            'event_date': data['event_date'],
                            'quotation_id':quotation_instance.id}

                        if eventdate_data['id'] == '':
                            # print(":::: NEW DAY ADDED ::::")
                            eventdate_data.pop('id')
                            n_eventdaySerializer = EventDaySerializer(data=eventdate_data)
                            if n_eventdaySerializer.is_valid():
                                eventday_instance = n_eventdaySerializer.save()
                            else:
                                return Response(n_eventdaySerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                            
                            ### FOR ADD EVENT DETAILS DATA ###
                            eventdetails_datas = data['event_details']
                            for eventdetails_data in eventdetails_datas:
                                eventdetails_data['eventday_id'] = eventday_instance.id
                                eventdetails_data['quotation_id'] = quotation_instance.id
                                eventdetailsSerializer = EventDetailsSerializer(data=eventdetails_data)
                                if eventdetailsSerializer.is_valid():
                                    eventdetails_instance = eventdetailsSerializer.save()
                                    final_eventdetails_data.append(eventdetails_instance)
                                else:
                                    return Response(eventdetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                            
                            descriptions = data['descriptions']
                            for description in descriptions:
                                ### FOR INVENTORY DETAILS DATA ###
                                inventorydetails_data = {
                                    'inventory_id':description['inventory_id'],
                                    'price':description['price'],
                                    'qty':description['qty'],
                                    'profit':description['profit'],
                                    'eventday_id':eventday_instance.id}

                                inventorydetailsSerializer = InventoryDetailsSerializer(data=inventorydetails_data)
                                if inventorydetailsSerializer.is_valid():
                                    inventorydetails_instance = inventorydetailsSerializer.save()
                                    final_inventorydetails_data.append(inventorydetails_instance)
                                else:
                                    return Response(inventorydetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                                
                                inventory = Inventory.objects.get(pk=inventorydetails_data['inventory_id'])
                                if inventory.type == 'service':
                                    ### FOR EXPOSURE DETAILS DATA ###
                                    exposuredetails = description.get('exposure', None)
                                    if exposuredetails is not None:
                                        for exposuredetail in exposuredetails:
                                            evnetdetials =[]
                                            allocations = exposuredetail['allocation']
                                            for i in range(len(final_eventdetails_data)):
                                                single_eventdetails = final_eventdetails_data.pop(0)
                                                for allocation in allocations:
                                                    event_id = single_eventdetails.event_id.id
                                                    if event_id == int(allocation):
                                                        evnetdetials.append(single_eventdetails.id)

                                            exposuredetails_data = {
                                                'staff_id':exposuredetail['staff_id'],
                                                'price':exposuredetail['price'],
                                                'eventdetails':evnetdetials,
                                                'inventorydetails_id':inventorydetails_instance.id}
                                            
                                            exposuredetailsSerializer = ExposureDetailsSerializer(data=exposuredetails_data)
                                            if exposuredetailsSerializer.is_valid():
                                                exposuredetails_instance = exposuredetailsSerializer.save()
                                                final_exposuredetails_data.append(exposuredetails_instance)
                                            else:
                                                return Response(exposuredetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)                    
                                
                        else:
                            # print(":::: OLD DAY UPDATED ::::")
                            o_eventday = EventDay.objects.get(pk=eventdate_data['id'])
                            o_eventdaySerializer = EventDaySerializer(o_eventday, data=eventdate_data, partial=True)
                            if o_eventdaySerializer.is_valid():
                                o_eventdaySerializer.save()
                            else:
                                return Response(o_eventdaySerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                                    
                            eventdetails_datas = data['event_details']
                            for eventdetails_data in eventdetails_datas:
                                if eventdetails_data['id'] == '':
                                    # print("::: NEW EVENT DETAILS :::")
                                    eventdetails_data.pop('id')
                                    n_eventdetailsSerializer = EventDetailsSerializer(data=eventdetails_data)
                                    if n_eventdetailsSerializer.is_valid():
                                        eventdetails_instance = n_eventdetailsSerializer.save()
                                        final_eventdetails_data.append(eventdetails_instance)
                                    else:
                                        return Response(n_eventdetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                                else:
                                    # print("::: OLD EVENT DETAILS :::")
                                    o_eventdetail = EventDetails.objects.get(pk=eventdetails_data['id'])
                                    o_eventdetailsSerializer = EventDetailsSerializer(o_eventdetail, data=eventdetails_data, partial=True)
                                    if o_eventdetailsSerializer.is_valid():
                                        eventdetails_instance = o_eventdetailsSerializer.save()
                                        final_eventdetails_data.append(eventdetails_instance)
                                    else:
                                        return Response(o_eventdetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                                    
                            descriptions = data['descriptions']
                            for description in descriptions:
                                inventorydetails_data = {
                                    'id':description['id'],
                                    'inventory_id':description['inventory_id'],
                                    'price':description['price'],
                                    'qty':description['qty'],
                                    'profit':description['profit'],
                                    'eventday_id':description['eventday_id']}

                                if inventorydetails_data['id'] == '':
                                    # print("::: NEW INVENTORY DETAILS :::")
                                    inventorydetails_data.pop('id')
                                    n_inventorydetailsSerializer = InventoryDetailsSerializer(data=inventorydetails_data)
                                    if n_inventorydetailsSerializer.is_valid():
                                        inventorydetails_instance = n_inventorydetailsSerializer.save()
                                        final_inventorydetails_data.append(inventorydetails_instance)
                                    else:
                                        return Response(n_inventorydetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                                else:
                                    # print("::: OLD INVENTORY DETAILS :::")
                                    o_inventorydetails = InventoryDetails.objects.get(pk=inventorydetails_data['id'])
                                    o_inventorydetailsSerializer = InventoryDetailsSerializer(o_inventorydetails, data=inventorydetails_data, partial=True)
                                    if o_inventorydetailsSerializer.is_valid():
                                        inventorydetails_instance = o_inventorydetailsSerializer.save()
                                        final_inventorydetails_data.append(inventorydetails_instance)
                                    else:
                                        return Response(o_inventorydetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                                    
                                inventory = Inventory.objects.get(pk=inventorydetails_data['inventory_id'])
                                if inventory.type == 'service':
                                    exposuredetails = description.get('exposure', None)
                                    if exposuredetails is not None:
                                        for exposuredetail in exposuredetails:
                                            evnetdetials =[]
                                            allocations = exposuredetail['allocation']
                                            for i in range(len(final_eventdetails_data)):
                                                single_eventdetails = final_eventdetails_data.pop(0)
                                                for allocation in allocations:
                                                    event_id = single_eventdetails.event_id.id
                                                    if event_id == int(allocation):
                                                        evnetdetials.append(single_eventdetails.id)

                                            exposuredetails_data = {
                                                'id':exposuredetail['id'],
                                                'staff_id':exposuredetail['staff_id'],
                                                'price':exposuredetail['price'],
                                                'inventorydetails_id':inventorydetails_instance.id,
                                                'eventdetails':evnetdetials}
                                            
                                            if exposuredetails_data['id'] == '':
                                                # print("::: NEW EXPOSURE DETAILS :::")
                                                exposuredetails_data.pop('id')
                                                n_exposuredetailsSerializer = ExposureDetailsSerializer(data=exposuredetails_data)
                                                if n_exposuredetailsSerializer.is_valid():
                                                    exposuredetails_instance = n_exposuredetailsSerializer.save()
                                                    final_exposuredetails_data.append(exposuredetails_instance)
                                                else:
                                                    return Response(n_exposuredetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                                            else:
                                                # print("::: NEW OLD DETAILS :::")
                                                o_exposuredetails = ExposureDetails.objects.get(pk=exposuredetails_data['id'])
                                                o_exposuredetailsSerializer = ExposureDetailsSerializer(o_exposuredetails, data=exposuredetails_data, partial=True)
                                                if o_exposuredetailsSerializer.is_valid():
                                                    exposuredetails_instance = o_exposuredetailsSerializer.save()
                                                    final_exposuredetails_data.append(exposuredetails_instance)
                                                else:
                                                    return Response(o_exposuredetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

                ### DELETE EXPOSURES DETAILS ###
                if delete_exposures is not None:
                    for delete_exposure in delete_exposures:
                        d_exposure = ExposureDetails.objects.get(pk=delete_exposure)
                        d_exposure.delete()

                ### DELETE INVENTORYS DETAILS ###
                if delete_inventorys is not None:
                    for delete_inventory in delete_inventorys:
                        d_inventory = InventoryDetails.objects.get(pk=delete_inventory)
                        d_inventory.delete()

                ### DELETE EVENTS DETAILS ###
                if delete_events is not None:
                    for delete_event in delete_events:
                        d_event = EventDetails.objects.get(pk=delete_event)
                        d_event.delete()

                ### DELETE EVENT DAY DETAILS ###
                if delete_eventdays is not None:
                    for delete_eventday in delete_eventdays:
                        d_eventday = EventDay.objects.get(pk=delete_eventday)
                        d_eventday.delete()

                ## UPDATE TRANSACTON DETAILS ###
                if transaction_data is not None:
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

                ### MAKE A COPY OF TRANSACTION AND QUOTATION ###
                if convert_status == 'true':
                    ### QUOTATION COPY ###
                    copy_quotationSerializer = QuotationSerializer(data=copy_quotation_data)
                    if copy_quotationSerializer.is_valid():
                        copy_quotation_instance = copy_quotationSerializer.save()
                    else:
                        return Response(copy_quotationSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    
                    copy_final_eventdetails_data = []
                    copy_final_inventorydetails_data = []
                    copy_final_exposuredetails_data = []

                    for copy_data in copy_datas:
                        ### FOR ADD EVENT DAY DATA ###
                        copy_eventdate_data = {
                            'event_date': copy_data['event_date'],
                            'quotation_id':copy_quotation_instance.id}
                        copy_eventdaySerializer = EventDaySerializer(data=copy_eventdate_data)
                        if copy_eventdaySerializer.is_valid():
                            copy_eventday_instance = copy_eventdaySerializer.save()
                        else:
                            return Response(copy_eventdaySerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                        
                        ### FOR ADD EVENT DETAILS DATA ###
                        copy_eventdetails_datas = copy_data['event_details']
                        for copy_eventdetails_data in copy_eventdetails_datas:
                            copy_eventdetails_data['eventday_id'] = copy_eventday_instance.id
                            copy_eventdetails_data['quotation_id'] = copy_quotation_instance.id
                            copy_eventdetailsSerializer = EventDetailsSerializer(data=copy_eventdetails_data)
                            if copy_eventdetailsSerializer.is_valid():
                                copy_eventdetails_instance = copy_eventdetailsSerializer.save()
                                copy_final_eventdetails_data.append(copy_eventdetails_instance)
                            else:
                                return Response(copy_eventdetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                        
                        copy_descriptions = copy_data['descriptions']
                        for copy_description in copy_descriptions:
                            ### FOR INVENTORY DETAILS DATA ###
                            copy_inventorydetails_data = {
                                'inventory_id':copy_description['inventory_id'],
                                'price':copy_description['price'],
                                'qty':copy_description['qty'],
                                'profit':copy_description['profit'],
                                'eventday_id':copy_eventday_instance.id}
                            
                            copy_inventorydetailsSerializer = InventoryDetailsSerializer(data=copy_inventorydetails_data)
                            if copy_inventorydetailsSerializer.is_valid():
                                copy_inventorydetails_instance = copy_inventorydetailsSerializer.save()
                                copy_final_inventorydetails_data.append(copy_inventorydetails_instance)
                            else:
                                return Response(copy_inventorydetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                            
                            copy_inventory = Inventory.objects.get(pk=copy_inventorydetails_data['inventory_id'])
                            if copy_inventory.type == 'service':

                                ### FOR EXPOSURE DETAILS DATA ###
                                copy_exposuredetails = copy_description.get('exposure', None)
                                if copy_exposuredetails is not None:
                                    for copy_exposuredetail in copy_exposuredetails:
                                        copy_evnetdetials =[]
                                        copy_allocations = copy_exposuredetail['allocation']
                                        for i in range(len(copy_final_eventdetails_data)):
                                            copy_single_eventdetails = copy_final_eventdetails_data.pop(0)
                                            for copy_allocation in copy_allocations:
                                                copy_event_id = copy_single_eventdetails.event_id.id
                                                if copy_event_id == int(copy_allocation):
                                                    copy_evnetdetials.append(copy_single_eventdetails.id)

                                        copy_exposuredetails_data = {
                                            'staff_id':copy_exposuredetail['staff_id'],
                                            'price':copy_exposuredetail['price'],
                                            'eventdetails':copy_evnetdetials,
                                            'inventorydetails_id':copy_inventorydetails_instance.id}
                                        
                                        copy_exposuredetailsSerializer = ExposureDetailsSerializer(data=copy_exposuredetails_data)
                                        if copy_exposuredetailsSerializer.is_valid():
                                            copy_exposuredetails_instance = copy_exposuredetailsSerializer.save()
                                            copy_final_exposuredetails_data.append(copy_exposuredetails_instance)
                                        else:
                                            return Response(copy_exposuredetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

                    ### TRANSACTION COPY ###
                    # print("ADD TRANSACTION COPY")
                    transaction_data.pop('id')
                    transaction_data['is_converted'] = True
                    transaction_data['type'] = 'event_sale'
                    transaction_data['quotation_id'] = copy_quotation_instance.id
                    transaction_data['customer_id'] = copy_quotation_instance.customer_id.id
                    copy_transactionSerializer = TransactionSerializer(data=transaction_data)
                    if copy_transactionSerializer.is_valid():
                        copy_transaction_instance = copy_transactionSerializer.save()
                    else:
                        return Response(copy_transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

                    new_amount = copy_transaction_instance.total_amount - copy_transaction_instance.recived_or_paid_amount
                    balance_amount(copy_transaction_instance.customer_id.id, None, 0 , new_amount, copy_transaction_instance.type)

                    ### LINK TRNASACTION 
                    linktransaction_data = request.data.get('linktransaction_data', None)
                    if linktransaction_data is not None:
                        link_transaction(copy_transaction_instance.id, linktransaction_data, copy_transaction_instance.type)

                    ### ADD BILL FOR EXOISURE ###

                    updated_exposuredetails_data = remove_exposure(final_exposuredetails_data)
                    print("updated_exposuredetails_data :: ",updated_exposuredetails_data)

                    finall_instance = []
                    for i in updated_exposuredetails_data:
                        i_transaction_data = {
                            'user_id' : transaction.user_id.id,
                            'type' : "event_purchase",
                            'staff_id' : i['staff_id'],
                            'total_amount' : i["price_sum"],
                            'exposuredetails_ids' : i["exposuredetails_ids"],
                            'transaction_instance' : copy_transaction_instance.id, 
                            'date': date.today()}
                        
                        i_transactionSerializer = TransactionSerializer(data=i_transaction_data)
                        if i_transactionSerializer.is_valid():
                            t_instance = i_transactionSerializer.save()
                            finall_instance.append(t_instance)
                        else:
                            return Response(i_transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                        
                        new_amount = t_instance.total_amount - t_instance.recived_or_paid_amount
                        balance_amount(None, t_instance.staff_id.id, 0 , new_amount, t_instance.type)

            ### CONVERTED TRANSACTION ###
            else:
                quotation = Quotation.objects.get(pk=pk)
                q_serializer = QuotationSerializer(quotation, data=quotation_data, partial=True)
                if q_serializer.is_valid():
                    quotation_instance = q_serializer.save()
                else:
                    return Response(q_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                final_eventdetails_data = []
                final_inventorydetails_data = []
                final_exposuredetails_data = []

                ### FOR ADD AND UPDATE OTHER DATA ### 
                if datas is not None:
                    for data in datas:

                        ### FOR ADD AND UPDATE EVENT DAY ###
                        eventdate_data = {
                            'id': data['id'],
                            'event_date': data['event_date'],
                            'quotation_id':quotation_instance.id}

                        if eventdate_data['id'] == '':
                            eventdate_data.pop('id')
                            n_eventdaySerializer = EventDaySerializer(data=eventdate_data)
                            if n_eventdaySerializer.is_valid():
                                eventday_instance = n_eventdaySerializer.save()
                            else:
                                return Response(n_eventdaySerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                            
                            ### FOR ADD EVENT DETAILS DATA ###
                            eventdetails_datas = data['event_details']
                            for eventdetails_data in eventdetails_datas:
                                eventdetails_data['eventday_id'] = eventday_instance.id
                                eventdetails_data['quotation_id'] = quotation_instance.id
                                eventdetailsSerializer = EventDetailsSerializer(data=eventdetails_data)
                                if eventdetailsSerializer.is_valid():
                                    eventdetails_instance = eventdetailsSerializer.save()
                                    final_eventdetails_data.append(eventdetails_instance)
                                else:
                                    return Response(eventdetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                            
                            descriptions = data['descriptions']
                            for description in descriptions:
                                ### FOR INVENTORY DETAILS DATA ###
                                inventorydetails_data = {
                                    'inventory_id':description['inventory_id'],
                                    'price':description['price'],
                                    'qty':description['qty'],
                                    'profit':description['profit'],
                                    'eventday_id':eventday_instance.id}
                                
                                inventorydetailsSerializer = InventoryDetailsSerializer(data=inventorydetails_data)
                                if inventorydetailsSerializer.is_valid():
                                    inventorydetails_instance = inventorydetailsSerializer.save()
                                    final_inventorydetails_data.append(inventorydetails_instance)
                                else:
                                    return Response(inventorydetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                                
                                inventory = Inventory.objects.get(pk=inventorydetails_data['inventory_id'])
                                if inventory.type == 'service':
                                    ### FOR EXPOSURE DETAILS DATA ###
                                    exposuredetails = description.get('exposure', None)
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
                                                'staff_id':exposuredetail['staff_id'],
                                                'price':exposuredetail['price'],
                                                'eventdetails':evnetdetials,
                                                'inventorydetails_id':inventorydetails_instance.id}
                                            
                                            exposuredetailsSerializer = ExposureDetailsSerializer(data=exposuredetails_data)
                                            if exposuredetailsSerializer.is_valid():
                                                exposuredetails_instance = exposuredetailsSerializer.save()
                                                final_exposuredetails_data.append(exposuredetails_instance)
                                            else:
                                                return Response(exposuredetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)                    
                                
                        else:
                            # print(":::: OLD DAY UPDATED ::::")
                            o_eventday = EventDay.objects.get(pk=eventdate_data['id'])
                            o_eventdaySerializer = EventDaySerializer(o_eventday, data=eventdate_data, partial=True)
                            if o_eventdaySerializer.is_valid():
                                o_eventdaySerializer.save()
                            else:
                                return Response(o_eventdaySerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                                    
                            eventdetails_datas = data['event_details']
                            for eventdetails_data in eventdetails_datas:
                                if eventdetails_data['id'] == '':
                                    # print("::: NEW EVENT DETAILS :::")
                                    eventdetails_data.pop('id')
                                    n_eventdetailsSerializer = EventDetailsSerializer(data=eventdetails_data)
                                    if n_eventdetailsSerializer.is_valid():
                                        eventdetails_instance = n_eventdetailsSerializer.save()
                                        final_eventdetails_data.append(eventdetails_instance)
                                    else:
                                        return Response(n_eventdetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                                else:
                                    # print("::: OLD EVENT DETAILS :::")
                                    o_eventdetail = EventDetails.objects.get(pk=eventdetails_data['id'])
                                    o_eventdetailsSerializer = EventDetailsSerializer(o_eventdetail, data=eventdetails_data, partial=True)
                                    if o_eventdetailsSerializer.is_valid():
                                        eventdetails_instance = o_eventdetailsSerializer.save()
                                        final_eventdetails_data.append(eventdetails_instance)
                                    else:
                                        return Response(o_eventdetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                                    
                            descriptions = data['descriptions']
                            for description in descriptions:
                                inventorydetails_data = {
                                    'id':description['id'],
                                    'inventory_id':description['inventory_id'],
                                    'price':description['price'],
                                    'qty':description['qty'],
                                    'profit':description['profit'],
                                    'eventday_id':description['eventday_id']}

                                if inventorydetails_data['id'] == '':
                                    # print("::: NEW INVENTORY DETAILS :::")
                                    inventorydetails_data.pop('id')
                                    n_inventorydetailsSerializer = InventoryDetailsSerializer(data=inventorydetails_data)
                                    if n_inventorydetailsSerializer.is_valid():
                                        inventorydetails_instance = n_inventorydetailsSerializer.save()
                                        final_inventorydetails_data.append(inventorydetails_instance)
                                    else:
                                        return Response(n_inventorydetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                                else:
                                    # print("::: OLD INVENTORY DETAILS :::")
                                    o_inventorydetails = InventoryDetails.objects.get(pk=inventorydetails_data['id'])
                                    o_inventorydetailsSerializer = InventoryDetailsSerializer(o_inventorydetails, data=inventorydetails_data, partial=True)
                                    if o_inventorydetailsSerializer.is_valid():
                                        inventorydetails_instance = o_inventorydetailsSerializer.save()
                                        final_inventorydetails_data.append(inventorydetails_instance)
                                    else:
                                        return Response(o_inventorydetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                                    
                                inventory = Inventory.objects.get(pk=inventorydetails_data['inventory_id'])
                                if inventory.type == 'service':
                                    exposuredetails = description['exposure']
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
                                            'eventdetails':evnetdetials}
                                        
                                        if exposuredetails_data['id'] == '':
                                            # print("::: NEW EXPOSURE DETAILS :::")
                                            exposuredetails_data.pop('id')
                                            n_exposuredetailsSerializer = ExposureDetailsSerializer(data=exposuredetails_data)
                                            if n_exposuredetailsSerializer.is_valid():
                                                exposuredetails_instance = n_exposuredetailsSerializer.save()
                                                final_exposuredetails_data.append(exposuredetails_instance)
                                            else:
                                                return Response(n_exposuredetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                                        else:
                                            # print("::: NEW OLD DETAILS :::")
                                            o_exposuredetails = ExposureDetails.objects.get(pk=exposuredetails_data['id'])
                                            o_exposuredetailsSerializer = ExposureDetailsSerializer(o_exposuredetails, data=exposuredetails_data, partial=True)
                                            if o_exposuredetailsSerializer.is_valid():
                                                exposuredetails_instance = o_exposuredetailsSerializer.save()
                                                final_exposuredetails_data.append(exposuredetails_instance)
                                            else:
                                                return Response(o_exposuredetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

                ### DELETE EXPOSURES DETAILS ###
                if delete_exposures is not None:
                    for delete_exposure in delete_exposures:
                        d_exposure = ExposureDetails.objects.get(pk=delete_exposure)
                        # exposure_bill = Transaction.objects.get(exposuredetails_id=delete_exposure)

                        balance = Balance.objects.get(staff_id=d_exposure.staff_id.id)
                        # balance.amount = balance.amount + exposure_bill.total_amount
                        balance.save()

                        d_exposure.delete()

                ### DELETE INVENTORYS DETAILS ###
                if delete_inventorys is not None:
                    for delete_inventory in delete_inventorys:
                        d_inventory = InventoryDetails.objects.get(pk=delete_inventory)
                        d_inventory.delete()

                ### DELETE EVENTS DETAILS ###
                if delete_events is not None:
                    for delete_event in delete_events:
                        d_event = EventDetails.objects.get(pk=delete_event)
                        d_event.delete()

                ### DELETE EVENT DAY DETAILS ###
                if delete_eventdays is not None:
                    for delete_eventday in delete_eventdays:
                        d_eventday = EventDay.objects.get(pk=delete_eventday)
                        d_eventday.delete()

                ## UPDATE TRANSACTON DETAILS ###
                if transaction_data is not None:
                    t_serializer = TransactionSerializer(transaction, data=transaction_data, partial=True)
                    if t_serializer.is_valid():
                        update_transaction = t_serializer.save()
                    else:
                        return Response(t_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                    new_amount = update_transaction.total_amount - update_transaction.recived_or_paid_amount
                    balance_amount(update_transaction.customer_id.id, None, old_amount , new_amount, update_transaction.type)

                ### LINK TRNASACTION 
                if linktransaction_data is not None:
                    link_transaction(transaction_data['id'], linktransaction_data, update_transaction.type)

                updated_exposuredetails_data = remove_exposure(final_exposuredetails_data)
                print("updated_exposuredetails_data :: ",updated_exposuredetails_data)

                finall_instance = []
                for i in updated_exposuredetails_data:
                    try:
                        # bill = Transaction.objects.get(exposuredetails_id = i.id)
                        bill = Transaction.objects.get(parent_transaction = update_transaction.id , staff_id__id = i['staff_id'])
                        old_amount = bill.total_amount - bill.recived_or_paid_amount
                    except:
                        bill = None

                    i_transaction_data = {
                            'user_id' : transaction.user_id.id,
                            'type' : "event_purchase",
                            'staff_id' : i['staff_id'],
                            'total_amount' : i["price_sum"],
                            'exposuredetails_ids': i["exposuredetails_ids"],
                            'parent_transaction' : update_transaction.id,
                            'date': date.today()}

                    if bill is not None:
                        # print("OLD BILL")
                        i_transactionSerializer = TransactionSerializer(bill, data=i_transaction_data, partial=True)
                        if i_transactionSerializer.is_valid():
                            t_instance = i_transactionSerializer.save()
                            finall_instance.append(t_instance)
                        else:
                            return Response(i_transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                        
                        new_amount = t_instance.total_amount - t_instance.recived_or_paid_amount
                        balance_amount(None, t_instance.staff_id.id, old_amount, new_amount, t_instance.type)

                    else:
                        # print("NEW BILL")
                        i_transactionSerializer = TransactionSerializer(data=i_transaction_data)
                        if i_transactionSerializer.is_valid():
                            t_instance = i_transactionSerializer.save()
                            finall_instance.append(t_instance)
                        else:
                            return Response(i_transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                        
                        new_amount = t_instance.total_amount - t_instance.recived_or_paid_amount
                        balance_amount(None, t_instance.staff_id.id, 0 , new_amount, t_instance.type)

            return Response({"quotation_data":QuotationSerializer(quotation_instance).data,})
        except Exception as e:
            logger.error(f"API: Quotation Update - An error occurred: {str(e)}.\nRequest data: {request.data}", exc_info=True)
            return Response({"error": "An error occurred while updating the object."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
        try:
            inventory_datas = request.data['inventory_data']
            transaction_data = request.data['transaction_data']
            linktransaction_data = request.data.get('linktransaction_data', None)

            all_instance = []
            inventorydescription_ids = []

            for inventory_data in inventory_datas:
                inventorySerializer = InventoryDescriptionSerializer(data=inventory_data)
                if inventorySerializer.is_valid():
                    inventory_instance = inventorySerializer.save()
                    all_instance.append(inventory_instance)
                else:
                    return Response(inventorySerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                inventorydescription_ids.append(inventory_instance.id)

            transaction_data['inventorydescription'] = inventorydescription_ids
            transactionSerializer = TransactionSerializer(data = transaction_data)
            if transactionSerializer.is_valid():
                transaction_instance = transactionSerializer.save()
            else:
                return Response(transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            customer_id = transaction_instance.customer_id.id if transaction_instance.customer_id is not None else None
            staff_id = transaction_instance.staff_id.id if transaction_instance.staff_id is not None else None
            
            new_amount = transaction_instance.total_amount - transaction_instance.recived_or_paid_amount
            balance_amount(customer_id, staff_id, 0, new_amount, transaction_instance.type)
            
            if linktransaction_data is not None:
                link_transaction(transaction_instance.id, linktransaction_data, transaction_instance.type)

            return Response({"inventorydescription": InventoryDescriptionSerializer(all_instance, many=True).data,
                            "transaction": TransactionSerializer(transaction_instance).data})
        except Exception as e:
            logger.error(f"API: Inventory Description Create - An error occurred: {str(e)}.\nRequest data: {request.data}", exc_info=True)
            return Response({"error": "An error occurred while creating the object."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
                queryset = queryset.filter(created_date__range=[start_date, end_date])
            except ValueError:
                pass

        return queryset

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            data = {}
            data['transaction_data'] = TransactionSerializer(instance).data

            inventory_descriptions = instance.inventorydescription.all()
            if len(inventory_descriptions) != 0:
                data['inventory_data'] = InventoryDescriptionSerializer(inventory_descriptions, many=True).data

            linktransaction = LinkTransaction.objects.filter(from_transaction_id=instance.id)
            if len(linktransaction) != 0:
                data['linktransaction_data'] = LinkTransactionSerializer(linktransaction, many=True).data

            exposuredetails = instance.exposuredetails_ids.all()
            if exposuredetails is not None:
                data['exposuredetails'] = ExposureDetailsSerializer(exposuredetails, many=True).data
                details = []
                for exposure in exposuredetails:
                    inventory_data = InventoryDetailsSerializer(exposure.inventorydetails_id).data
                    eventday = EventDay.objects.get(pk = inventory_data["eventday_id"])
                    eventday_data = EventDaySerializer(eventday).data
                    event_data = EventDetailsSerializer(exposure.eventdetails.all(), many=True).data
                    details.append({
                        "inventorydetails": inventory_data,
                        "eventdetails": event_data,
                        "eventday_data" : eventday_data
                    })
                data['details'] = details

            return Response(data)
        except Exception as e:
            logger.error(f"API: Transaction Retrieve - An error occurred: {str(e)}", exc_info=True)
            return Response({"error": "An error occurred while retrieving the object."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request, *args, **kwargs):
        try:
            transaction_data = request.data['transaction_data']
            linktransaction_data = request.data.get('linktransaction_data', None)

            data = {}

            transactionSerializer = TransactionSerializer(data=transaction_data)
            if transactionSerializer.is_valid():
                transaction_instance = transactionSerializer.save()
            else:
                return Response(transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

            data['transaction_data'] = TransactionSerializer(transaction_instance).data

            customer_id = transaction_data.get('customer_id', None)
            staff_id = transaction_data.get('staff_id', None)

            new_amount = transaction_instance.total_amount - transaction_instance.used_amount
            balance_amount(customer_id, staff_id, 0, new_amount, transaction_instance.type)

            if linktransaction_data is not None:
                link_transaction(transaction_instance.id, linktransaction_data, transaction_instance.type)

            return Response(data)
        except Exception as e:
            logger.error(f"API: Transaction Create - An error occurred: {str(e)}.\nRequest data: {request.data}", exc_info=True)
            return Response({"error": "An error occurred while creating the object."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def update(self, request, pk=None, *args, **kwargs):
        try:
            key = request.data.get('key')
            transaction = Transaction.objects.get(pk=pk)

            if transaction.type in ('payment_in', 'payment_out'):
                old_amount = transaction.total_amount - transaction.used_amount
            else:
                old_amount = transaction.total_amount - transaction.recived_or_paid_amount

            data={}

            if key == 'inventorydescription_update':
                inventory_datas = request.data.get('inventory_data', None)
                copy_inventory_datas = inventory_datas
                transaction_data = request.data.get('transaction_data')
                delete_inventorys = request.data.get('delete_inventory', None)
                linktransaction_data = request.data.get('linktransaction_data', None)

                all_inventory = []
                inventorydescription_ids = []

                ### NOT CONVERTED TRANSACTION ###
                if transaction.is_converted == False:
                    convert_status = transaction_data.get('is_converted', None)

                    if delete_inventorys is not None:
                        for delete_inventory in delete_inventorys:
                            d_inventory = InventoryDescription.objects.get(pk=delete_inventory)
                            d_inventory.delete()
                    
                    for inventory_data in inventory_datas:
                        if inventory_data['id'] == '':
                            inventory_data.pop('id')
                            n_inventory = InventoryDescriptionSerializer(data=inventory_data)
                            if n_inventory.is_valid():
                                new_inventory = n_inventory.save()
                                inventorydescription_ids.append(new_inventory.id)
                                all_inventory.append(new_inventory)
                            else:
                                return Response(n_inventory.errors, status=status.HTTP_400_BAD_REQUEST)
                        else:
                            inventory = InventoryDescription.objects.get(id=inventory_data['id'])
                            o_inventory = InventoryDescriptionSerializer(inventory, data=inventory_data, partial=True)
                            if o_inventory.is_valid():
                                old_inventory = o_inventory.save()
                                inventorydescription_ids.append(old_inventory.id)
                                all_inventory.append(old_inventory)
                            else:
                                return Response(o_inventory.errors, status=status.HTTP_400_BAD_REQUEST)
                            
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
                    staff_id = transaction_instance.staff_id.id if transaction_instance.staff_id is not None else None
                    
                    new_amount = transaction_instance.total_amount - transaction_instance.recived_or_paid_amount
                    balance_amount(customer_id, staff_id, old_amount, new_amount, transaction_instance.type)

                    if convert_status is not None:
                        if convert_status == 'true':
                            copy_all_instance = []
                            copy_inventorydescription_ids = []

                            for copy_inventory_data in copy_inventory_datas:
                                copy_inventorySerializer = InventoryDescriptionSerializer(data=copy_inventory_data)
                                if copy_inventorySerializer.is_valid():
                                    copy_inventory_instance = copy_inventorySerializer.save()
                                    copy_all_instance.append(copy_inventory_instance)
                                else:
                                    return Response(copy_inventorySerializer.errors, status=status.HTTP_400_BAD_REQUEST)

                                copy_inventorydescription_ids.append(copy_inventory_instance.id)

                            if transaction_data['type'] == 'purchase_order':
                                transaction_data['type'] = 'purchase'
                            if transaction_data['type'] == 'sale_order':
                                transaction_data['type'] = 'sale'
                            transaction_data['is_converted'] = True
                            transaction_data['inventorydescription'] = copy_inventorydescription_ids
                            copy_transactionSerializer = TransactionSerializer(data = transaction_data)
                            if copy_transactionSerializer.is_valid():
                                copy_trnasaction_instance = copy_transactionSerializer.save()
                            else:
                                return Response(copy_transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                            
                            customer_id = copy_trnasaction_instance.customer_id.id if copy_trnasaction_instance.customer_id is not None else None
                            staff_id = copy_trnasaction_instance.staff_id.id if copy_trnasaction_instance.staff_id is not None else None
                            
                            new_amount = copy_trnasaction_instance.total_amount - copy_trnasaction_instance.recived_or_paid_amount
                            balance_amount(copy_trnasaction_instance.customer_id.id, None, 0 , new_amount, copy_trnasaction_instance.type)

                else:
                    if delete_inventorys is not None:
                        for delete_inventory in delete_inventorys:
                            d_inventory = InventoryDescription.objects.get(pk=delete_inventory)
                            d_inventory.delete()
                    
                    for inventory_data in inventory_datas:
                        if inventory_data['id'] == '':
                            inventory_data.pop('id')
                            n_inventory = InventoryDescriptionSerializer(data=inventory_data)
                            if n_inventory.is_valid():
                                new_inventory = n_inventory.save()
                                inventorydescription_ids.append(new_inventory.id)
                                all_inventory.append(new_inventory)
                            else:
                                return Response(n_inventory.errors, status=status.HTTP_400_BAD_REQUEST)
                        else:
                            inventory = InventoryDescription.objects.get(id=inventory_data['id'])
                            o_inventory = InventoryDescriptionSerializer(inventory, data=inventory_data, partial=True)
                            if o_inventory.is_valid():
                                old_inventory = o_inventory.save()
                                inventorydescription_ids.append(old_inventory.id)
                                all_inventory.append(old_inventory)
                            else:
                                return Response(o_inventory.errors, status=status.HTTP_400_BAD_REQUEST)

                    transaction_data['inventorydescription'] = inventorydescription_ids 
                    transaction_data['is_converted'] = True
                    transactionSerializer = TransactionSerializer(transaction, data=transaction_data, partial=True)
                    if transactionSerializer.is_valid():
                        transaction_instance = transactionSerializer.save()
                    else:
                        return Response(transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    
                    customer_id = transaction_instance.customer_id.id if transaction_instance.customer_id is not None else None
                    staff_id = transaction_instance.staff_id.id if transaction_instance.staff_id is not None else None
                    
                    new_amount = transaction_instance.total_amount - transaction_instance.recived_or_paid_amount
                    balance_amount(transaction_instance.customer_id.id, None, old_amount, new_amount, transaction_instance.type)

                if linktransaction_data is not None:
                    link_transaction(pk, linktransaction_data, transaction_instance.type)

                data['tranasaction_data'] = TransactionSerializer(transaction_instance).data
                data['inventorydescription_data'] = InventoryDescriptionSerializer(all_inventory, many=True).data

            if key == 'transaction_update':
                transaction_data = request.data.get('transaction_data')
                linktransaction_data = request.data.get('linktransaction_data', None)

                transactionSerializer = TransactionSerializer(transaction, data=transaction_data, partial=True)
                if transactionSerializer.is_valid():
                    transaction_instance = transactionSerializer.save()
                else:
                    return Response(transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                data['tranasaction_data'] = TransactionSerializer(transaction_instance).data

                customer_id = transaction_instance.customer_id.id if transaction_instance.customer_id is not None else None
                staff_id = transaction_instance.staff_id.id if transaction_instance.staff_id is not None else None

                new_amount = transaction_instance.total_amount - transaction_instance.used_amount
                balance_amount(customer_id, staff_id, old_amount, new_amount, transaction_instance.type)

                if linktransaction_data is not None:
                    link_transaction(pk, linktransaction_data, transaction.type)
                    ### WE ADD TRANSACTION TYPE BECAUSE OF IF TO TRANSACTION AND UPDATE TRASACTION IS SAME THEN WE DON'T NEED TO EDIT USED AMOUNT
    
            if key == 'exposure_bill_update':
                transaction_data = request.data.get('transaction_data')

                transactionSerializer = TransactionSerializer(transaction, data=transaction_data, partial=True)
                if transactionSerializer.is_valid():
                    transaction_instance = transactionSerializer.save()
                else:
                    return Response(transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                customer_id = transaction_instance.customer_id.id if transaction_instance.customer_id is not None else None
                staff_id = transaction_instance.staff_id.id if transaction_instance.staff_id is not None else None
                
                new_amount = transaction_instance.total_amount - transaction_instance.recived_or_paid_amount
                balance_amount(customer_id, staff_id, old_amount, new_amount, transaction_instance.type)

                data['tranasaction_data'] = TransactionSerializer(transaction_instance).data
            
            return Response(data)
        except Exception as e:
            logger.error(f"API: Transaction Update - An error occurred: {str(e)}.\nRequest data: {request.data}", exc_info=True)
            return Response({"error": "An error occurred while updating the object."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def destroy(self, request, pk=None, *args, **kwargs):
        try:
            transaction_object = Transaction.objects.get(pk=pk)

            customer_id = transaction_object.customer_id.id if transaction_object.customer_id is not None else None
            staff_id = transaction_object.staff_id.id if transaction_object.staff_id is not None else None

            if transaction_object.type == 'estimate':
                quotation_id = transaction_object.quotation_id
                quotation = Quotation.objects.get(pk=quotation_id.id)
                quotation.delete()
                
            if transaction_object.type == 'payment_in':
                linktrasactions = LinkTransaction.objects.filter(from_transaction_id=pk)
                for link in linktrasactions:
                    to_transaction_id = link.to_transaction_id
                    new_amount = link.linked_amount
                    to_transaction = Transaction.objects.get(pk=to_transaction_id.id)

                    if to_transaction.type in ('payment_in', 'payment_out'):
                        to_transaction.used_amount = to_transaction.used_amount - link.linked_amount
                    else:
                        to_transaction.recived_or_paid_amount = to_transaction.recived_or_paid_amount - link.linked_amount
                    to_transaction.save()

                    balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

                to_linktrasactions = LinkTransaction.objects.filter(to_transaction_id=pk)
                print("ALL LINKED TRANSACTION :: ", linktrasactions)
                for to_link in to_linktrasactions:
                    from_transaction_id = to_link.from_transaction_id
                    new_amount = to_link.linked_amount
                    from_trasaction = Transaction.objects.get(pk=from_transaction_id.id)

                    if from_trasaction.type in ('payment_in', 'payment_out'):
                        from_trasaction.used_amount = from_trasaction.used_amount - to_link.linked_amount
                    else:
                        from_trasaction.recived_or_paid_amount = from_trasaction.recived_or_paid_amount - to_link.linked_amount
                    from_trasaction.save()

                    print("New Amount ::: ", new_amount)
                    balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

                new_amount = transaction_object.total_amount - transaction_object.used_amount
                print("New Amount ::: ", new_amount)
                balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

            if transaction_object.type == 'payment_out':
                linktrasactions = LinkTransaction.objects.filter(from_transaction_id=pk)
                for link in linktrasactions:
                    to_transaction_id = link.to_transaction_id
                    new_amount = link.linked_amount          
                    to_transaction = Transaction.objects.get(pk=to_transaction_id.id)

                    if to_transaction.type in ('payment_in', 'payment_out'):
                        to_transaction.used_amount = to_transaction.used_amount - link.linked_amount
                    else:
                        to_transaction.recived_or_paid_amount = to_transaction.recived_or_paid_amount - link.linked_amount
                    to_transaction.save()

                    balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

                to_linktrasactions = LinkTransaction.objects.filter(to_transaction_id=pk)
                for to_link in to_linktrasactions:
                    from_transaction_id = to_link.from_transaction_id
                    new_amount = to_link.linked_amount
                    from_trasaction = Transaction.objects.get(pk=from_transaction_id.id)

                    if from_trasaction.type in ('payment_in', 'payment_out'):
                        from_trasaction.used_amount = from_trasaction.used_amount - to_link.linked_amount
                    else:
                        from_trasaction.recived_or_paid_amount = from_trasaction.recived_or_paid_amount - to_link.linked_amount
                    
                    from_trasaction.save()

                    balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

                new_amount = transaction_object.total_amount - transaction_object.used_amount
                balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

            if transaction_object.type == 'sale_order':
                pass
                
            if transaction_object.type == 'sale':
                linktrasactions = LinkTransaction.objects.filter(to_transaction_id=pk)
                for link in linktrasactions:
                    from_transaction_id = link.from_transaction_id
                    new_amount = link.linked_amount
                    from_transaction = Transaction.objects.get(pk=from_transaction_id.id)

                    if from_transaction.type in ('payment_in', 'payment_out'):
                        from_transaction.used_amount = from_transaction.used_amount - link.linked_amount
                    else:
                        from_transaction.recived_or_paid_amount = from_transaction.recived_or_paid_amount - link.linked_amount
                    
                    from_transaction.save()
                    balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

                from_linktrasactions = LinkTransaction.objects.filter(from_transaction_id=pk)
                for from_link in from_linktrasactions:
                    to_transaction_id = from_link.to_transaction_id
                    new_amount = from_link.linked_amount
                    to_trasaction = Transaction.objects.get(pk=to_transaction_id.id)

                    if to_trasaction.type in ('payment_in', 'payment_out'):
                        to_trasaction.used_amount = to_trasaction.used_amount - from_link.linked_amount
                    else:
                        to_trasaction.recived_or_paid_amount = to_trasaction.recived_or_paid_amount - from_link.linked_amount
                    
                    to_trasaction.save()
                    balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

                new_amount = transaction_object.total_amount - transaction_object.recived_or_paid_amount
                balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

            if transaction_object.type == 'event_sale':
                linktrasactions = LinkTransaction.objects.filter(to_transaction_id=pk)
                for link in linktrasactions:
                    from_transaction_id = link.from_transaction_id
                    new_amount = link.linked_amount
                    from_transaction = Transaction.objects.get(pk=from_transaction_id.id)

                    if from_transaction.type in ('payment_in', 'payment_out'):
                        from_transaction.used_amount = from_transaction.used_amount - link.linked_amount
                    else:
                        from_transaction.recived_or_paid_amount = from_transaction.recived_or_paid_amount - link.linked_amount
                    
                    from_transaction.save()
                    balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

                from_linktrasactions = LinkTransaction.objects.filter(from_transaction_id=pk)
                for from_link in from_linktrasactions:
                    to_transaction_id = from_link.to_transaction_id
                    new_amount = from_link.linked_amount
                    to_trasaction = Transaction.objects.get(pk=to_transaction_id.id)

                    if to_trasaction.type in ('payment_in', 'payment_out'):
                        to_trasaction.used_amount = to_trasaction.used_amount - from_link.linked_amount
                    else:
                        to_trasaction.recived_or_paid_amount = to_trasaction.recived_or_paid_amount - from_link.linked_amount
                    
                    to_trasaction.save()
                    balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)
                    
                # new_amount = transaction_object.total_amount - transaction_object.recived_or_paid_amount
                # balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

                quotation_id = transaction_object.quotation_id
                quotation = Quotation.objects.get(pk=quotation_id.id)

                eventdays = EventDay.objects.filter(quotation_id=quotation_id.id)
                for eventday in eventdays:
                    inventorydetails = InventoryDetails.objects.filter(eventday_id=eventday.id)
                    for inventorydetail in inventorydetails:
                        exposuredetails = ExposureDetails.objects.filter(inventorydetails_id=inventorydetail.id)
                        # for exposuredetail in exposuredetails:
                        #     print("exposuredetails :: ", exposuredetail)
                        #     print("exposuredetail.staff_id.id :: ", exposuredetail.staff_id.id)
                        #     transaction = Transaction.objects.get(staff_id=exposuredetail.staff_id.id, parent_transaction=transaction_object.id)


                        for exposuredetail in exposuredetails:
                            transaction = Transaction.objects.get(staff_id=exposuredetail.staff_id.id, parent_transaction=transaction_object.id)
                            new_amount = transaction.total_amount - transaction.recived_or_paid_amount
                            balance_delete_amount(None, transaction.staff_id.id, 0 , new_amount, transaction.type)
                            balance = Balance.objects.get(staff_id=transaction.staff_id.id)
                            balance.amount = balance.amount + float(transaction.total_amount)
                            balance.save()
                            transaction.delete()
                    eventday.delete()
                quotation.delete()

            if transaction_object.type == 'purchase_order':
                pass
                
            if transaction_object.type == 'purchase':
                linktrasactions = LinkTransaction.objects.filter(to_transaction_id=pk)
                for link in linktrasactions:
                    from_transaction_id = link.from_transaction_id
                    new_amount = link.linked_amount
                    from_transaction = Transaction.objects.get(pk=from_transaction_id.id)

                    if from_transaction.type in ('payment_in', 'payment_out'):
                        from_transaction.used_amount = from_transaction.used_amount - link.linked_amount
                    else:
                        from_transaction.recived_or_paid_amount = from_transaction.recived_or_paid_amount - link.linked_amount
                    
                    from_transaction.save()
                    balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)
                
                from_linktrasactions = LinkTransaction.objects.filter(from_transaction_id=pk)
                for from_link in from_linktrasactions:
                    to_transaction_id = from_link.to_transaction_id
                    new_amount = from_link.linked_amount
                    to_trasaction = Transaction.objects.get(pk=to_transaction_id.id)

                    if to_trasaction.type in ('payment_in', 'payment_out'):
                        to_trasaction.used_amount = to_trasaction.used_amount - from_link.linked_amount
                    else:
                        to_trasaction.recived_or_paid_amount = to_trasaction.recived_or_paid_amount - from_link.linked_amount
                    
                    to_trasaction.save()
                    balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)
                
                new_amount = transaction_object.total_amount - transaction_object.recived_or_paid_amount
                balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

            if transaction_object.type == 'event_purchase':
                linktrasactions = LinkTransaction.objects.filter(to_transaction_id=pk)
                for link in linktrasactions:
                    from_transaction_id = link.from_transaction_id
                    new_amount = link.linked_amount
                    from_transaction = Transaction.objects.get(pk=from_transaction_id.id)

                    if from_transaction.type in ('payment_in', 'payment_out'):
                        from_transaction.used_amount = from_transaction.used_amount - link.linked_amount
                    else:
                        from_transaction.recived_or_paid_amount = from_transaction.recived_or_paid_amount - link.linked_amount
                    
                    from_transaction.save()
                    balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

                from_linktrasactions = LinkTransaction.objects.filter(from_transaction_id=pk)
                for from_link in from_linktrasactions:
                    to_transaction_id = from_link.to_transaction_id
                    new_amount = from_link.linked_amount
                    to_trasaction = Transaction.objects.get(pk=to_transaction_id.id)

                    if to_trasaction.type in ('payment_in', 'payment_out'):
                        to_trasaction.used_amount = to_trasaction.used_amount - from_link.linked_amount
                    else:
                        to_trasaction.recived_or_paid_amount = to_trasaction.recived_or_paid_amount - from_link.linked_amount
                    
                    to_trasaction.save()
                    balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

                new_amount = transaction_object.total_amount - transaction_object.recived_or_paid_amount
                balance_delete_amount(customer_id, staff_id, 0 , new_amount, transaction_object.type)

            transaction_object.delete()

            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"API: Transaction Link - An error occurred: {str(e)}", exc_info=True)
            return Response({"error": "An error occurred while deleting the object."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


### API USED FOR GET TRASACTION AND LINK TRANSACTION ###
@api_view(['POST'])
def TransactionLink(request):
    if request.method == 'POST':
        try:
            data = {}
            customer_id = request.data.get('customer_id', None)
            staff_id = request.data.get('staff_id', None)
            transaction_type = request.data.get('transaction_type', None)
            transaction_id = request.data.get('transaction_id', None)

            if customer_id is not None:
                if transaction_type is not None:
                    transaction = Transaction.objects.filter(Q(customer_id=customer_id), Q(type__in=transaction_type))
                else:
                    transaction = Transaction.objects.filter(customer_id=customer_id)

            if staff_id is not None:
                if transaction_type is not None:
                    transaction = Transaction.objects.filter(Q(staff_id=staff_id), Q(type__in=transaction_type))
                else:
                    transaction = Transaction.objects.filter(staff_id=staff_id)
            data['transaction_data'] = TransactionSerializer(transaction, many=True).data

            if transaction_id is not None:
                linktransaction = LinkTransaction.objects.filter(Q(from_transaction_id=transaction_id) 
                                                                | Q(to_transaction_id=transaction_id))
                data['linktransaction'] = LinkTransactionSerializer(linktransaction, many=True).data

            return Response(data)
        
        except Exception as e:
            logger.error(f"API: Transaction Link - An error occurred: {str(e)}", exc_info=True)
            return Response({"error": "An error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response({"error": "Invalid request"}, status=400)


### API FOR STAFF AVAILABLE STATUS ###
@api_view(['GET', 'POST'])
def StaffStatus(request):
    logger.info("StaffStatus view function called.")
    if request.method == 'GET':
        try:
            user_id = request.query_params.get("user_id")

            current_utc_datetime = datetime.datetime.utcnow()
            itc_timezone = pytz.timezone('Asia/Kolkata')
            current_itc_datetime = current_utc_datetime.astimezone(itc_timezone)
            current_itc_date = current_itc_datetime.date()

            staffs = Staff.objects.filter(user_id=user_id)
            data = []
            for staff in staffs:
                detail ={'staff_detail': {},
                        'event_data': []}
                
                staffskill = StaffSkill.objects.filter(staff_id=staff.id)
                detail['staff_detail'] = {"staff_data" : StaffSerializer(staff).data,
                                        "staffskill_data" : StaffSkillSerializer(staffskill, many=True).data}

                exposuredetails = ExposureDetails.objects.filter(staff_id=staff.id)
                for exposuredetail in exposuredetails:
                    event_details = exposuredetail.eventdetails.all()
                
                    for event_detail in event_details:
                        details ={}
                        eventday = EventDay.objects.get(pk=event_detail.eventday_id.id)
                        if eventday.event_date >= current_itc_date:
                            # print("EVENT DATE IS GREATER THAN CURRENT DATE")
                            details = {'event_date': eventday.event_date.strftime('%Y-%m-%d'),
                                    'event_venue': event_detail.event_venue,
                                    'start_time': event_detail.start_time.strftime('%H:%M:%S'),
                                    'end_time': event_detail.end_time.strftime('%H:%M:%S')}
                            
                            detail['event_data'].append(details)
                data.append(detail)

            return Response(data)
        except Exception as e:
            logger.error(f"API: Staff Status - An error occurred: {str(e)}", exc_info=True)
            return Response({"error": "An error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response({"error": "Invalid request"}, status=400)


### API FOR TODAY'S EVENT DETAILS ###
@api_view(['POST'])
def EventDetail(request):
    if request.method == 'POST':
        try:
            today = request.data.get('today', None)
            user_id = request.data.get('user_id', None)

            eventdays = EventDay.objects.filter(event_date=today)
            print("EventDays :: ", eventdays)
            data = []

            for eventday in eventdays:
                print("EventDay :: ", eventday)
                print("eventday.quotation_id :: ", eventday.quotation_id.id)
                transaction = Transaction.objects.get(quotation_id=eventday.quotation_id.id)
                print("Transaction :: ", transaction)
                if transaction.type == 'event_sale' and transaction.user_id.id == user_id:
                    eventdetails = EventDetails.objects.filter(eventday_id=eventday.id)
                    for eventdetail in eventdetails:
                        event_detail_data = {
                            'eventdetail_id': eventdetail.event_id.id,
                            'event_name': eventdetail.event_id.event_name,
                            'event_venue': eventdetail.event_venue,
                            'start_time': eventdetail.start_time,
                            'end_time': eventdetail.end_time}

                        exposuredetails = ExposureDetails.objects.filter(eventdetails__id=eventdetail.id)
                        if len(exposuredetails) == 0:
                            exposuredetail_data = {
                                    'staff_name': '',
                                    'staff_mobile_no': '',
                                    'event_detail': [event_detail_data]}
                            
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
                                    'exposuredetails_data': [exposuredetail_data]})
                        else:
                            for exposuredetail in exposuredetails:
                                exposuredetail_data = {
                                    'staff_name': exposuredetail.staff_id.full_name,
                                    'staff_mobile_no': exposuredetail.staff_id.mobile_no,
                                    'event_detail': [event_detail_data]}

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
                                        'exposuredetails_data': [exposuredetail_data]})

            return Response(data)
        
        except Exception as e:
            logger.error(f"API: Event Detail - An error occurred: {str(e)}", exc_info=True)
            return Response({"error": "An error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response({"error": "Invalid request"}, status=400)


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
        to_date = self.request.query_params.get('to_date')

        if from_date and to_date:
            try:
                queryset = queryset.filter(converted_on__range=[from_date, to_date])
            except ValueError:
                pass

        return queryset

    def list(self, request):
        try:
            querysets = self.filter_queryset(self.get_queryset())
            paid_amount = 0
            total = 0
            for queryset in querysets:
                total_amount = Transaction.objects.filter(quotation_id=queryset.id).aggregate(Sum('amount'))['amount__sum']
                total_amount = total_amount if total_amount is not None else 0
                s_transaction = Transaction.objects.filter(quotation_id=queryset.id)
                payable_amount = queryset.final_amount - queryset.discount
                
                paid_amount += total_amount
                total += payable_amount
            
            data = {"paid_amount":paid_amount,
                    "total":total}
            
            return Response(data)
        except Exception as e:
            logger.error(f"API: Event Detail - An error occurred: {str(e)}", exc_info=True)
            return Response({"error": "An error occurred while listing the object."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
        try:
            s3_bucket_url = request.data.get('s3_bucket_url', None)
            if s3_bucket_url is not None:
                response = requests.get(s3_bucket_url)
                image_data = response.content
                base64_image = base64.b64encode(image_data).decode()
                data_url = f"data:image/jpeg;base64,{base64_image}"
            
            return Response(data_url)
        except Exception as e:
            logger.error(f"API: Convert Bucket URL - An error occurred: {str(e)}", exc_info=True)
            return Response({"error": "An error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return Response({"error": "Invalid request"}, status=400)

# import os, sys
# import logging

# logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)

# f = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s - %(lineno)d')

# fh = logging.FileHandler('test.log')
# fh.setFormatter(f)

# logger.addHandler(fh)

# logger.info('Test logging')

### TOTAL SALE
@api_view(['POST'])
def TotalSale(request):
    if request.method == 'POST':
        try:
            user_id = request.data.get('user_id', None)
            start_date = request.data.get('start_date', None)
            end_date = request.data.get('end_date', None)

            if start_date is None and end_date is None:
                total_amount = Transaction.objects.filter(user_id=user_id, type__in=['sale', 'event_sale']).aggregate(Sum('total_amount'))['total_amount__sum']
            else:
                total_amount = Transaction.objects.filter(user_id=user_id, created_on__range=[start_date, end_date], type__in=['sale', 'event_sale']).aggregate(Sum('total_amount'))['total_amount__sum']
                # print('total_amount ::: ',total_amount)
            # logger.info('Successfully')

            return Response(total_amount)
    
        except Exception as e:
            # exc_type, exc_obj, exc_tb = sys.exc_info()
            # fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            # print(exc_type, fname, exc_tb.tb_lineno)
            # logger.error(f'{exc_type}{fname},{exc_tb.tb_lineno}')
            # logger.error('Error occurred:', exc_info=False)
            logger.error(f"API: Total Sale - An error occurred: {str(e)}", exc_info=True)
            return Response({"error": "An error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    return Response({"error": "Invalid request"}, status=400)


### TOTAL EXPENSES
@api_view(['POST'])
def TotalExpense(request):
    if request.method == 'POST':
        try:
            user_id = request.data.get('user_id', None)
            start_date = request.data.get('start_date', None)
            end_date = request.data.get('end_date', None)

            if start_date is None and end_date is None:
                total_amount = Transaction.objects.filter(user_id=user_id, type__in=['expense']).aggregate(Sum('total_amount'))['total_amount__sum']
            else:
                total_amount = Transaction.objects.filter(user_id=user_id, created_on__range=[start_date, end_date], type__in=['expense']).aggregate(Sum('total_amount'))['total_amount__sum']

            return Response(total_amount)
        
        except Exception as e:
            logger.error(f"API: Total Expense - An error occurred: {str(e)}", exc_info=True)
            return Response({"error": "An error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    return Response({"error": "Invalid request"}, status=400)


### TOTAL RECIVED AMOUNT
@api_view(['POST'])
def TotalAmount(request):
    if request.method == 'POST':
        try:
            user_id = request.data.get('user_id', None)

            total_recived = 0
            total_paied = 0

            customers = Customer.objects.filter(user_id=user_id)
            for customer in customers:
                total_recived_amount = Transaction.objects.filter(customer_id=customer.id, type__in=['sale','event_sale','payment_out']).aggregate(Sum('total_amount'))['total_amount__sum']
                total_recived_amount = total_recived_amount if total_recived_amount is not None else 0

                total_pay_amount = Transaction.objects.filter(customer_id=customer.id, type__in=['purchase','event_purchase','payment_in']).aggregate(Sum('total_amount'))['total_amount__sum']
                total_pay_amount = total_pay_amount if total_pay_amount is not None else 0

                total = total_recived_amount - total_pay_amount

                if total > 0:
                    total_recived = total_recived + total
                elif total < 0:
                    total_paied = total_paied + (-total)

            data = {'total_recived' : total_recived,
                    'total_paied' : total_paied}

            return Response(data)
        
        except Exception as e:
            logger.error(f"API: Total Amount - An error occurred: {str(e)}", exc_info=True)
            return Response({"error": "An error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    return Response({"error": "Invalid request"}, status=400)      


### TOTAL PURCHASE
@api_view(['POST'])
def TotalPurchase(request):
    if request.method == 'POST':
        try:
            user_id = request.data.get('user_id', None)
            start_date = request.data.get('start_date', None)
            end_date = request.data.get('end_date', None)

            if start_date is None and end_date is None:
                total_amount = Transaction.objects.filter(user_id=user_id, type__in=['purchase','event_purchase']).aggregate(Sum('total_amount'))['total_amount__sum']
            else:
                total_amount = Transaction.objects.filter(user_id=user_id, created_on__range=[start_date, end_date], type__in=['purchase','event_purchase']).aggregate(Sum('total_amount'))['total_amount__sum']

            return Response(total_amount)
        
        except Exception as e:
            logger.error(f"API: Total Purchase - An error occurred: {str(e)}", exc_info=True)
            return Response({"error": "An error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    return Response({"error": "Invalid request"}, status=400)


### ConversationReport
@api_view(['POST'])
def ConversationRateReport(request):
    if request.method == 'POST':
        try:
            user = request.data.get('user_id')
            start_date = request.data.get('start_date', None)
            end_date = request.data.get('end_date', None)

            report = {}

            total = Transaction.objects.filter(user_id = user, type='estimate').count()
            report['total'] = total

            if start_date is None and end_date is None:
                not_converted = Transaction.objects.filter(user_id = user, type='estimate', is_converted=False).count()
                report['not_converted'] = not_converted

                converted = Transaction.objects.filter(user_id = user, type='estimate', is_converted=True).count()
                report['converted'] = converted
            else:
                not_converted = Transaction.objects.filter(user_id = user, type='estimate', is_converted=False, created_on__range=[start_date, end_date]).count()
                report['not_converted'] = not_converted

                converted = Transaction.objects.filter(user_id = user, type='estimate', is_converted=True, created_on__range=[start_date, end_date]).count()
                report['converted'] = converted

            return Response(report)
        
        except Exception as e:
            logger.error(f"API: Conversation Rate Report - An error occurred: {str(e)}", exc_info=True)
            return Response({"error": "An error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    return Response({"error": "Invalid request"}, status=400)


### Invoice Status
@api_view(['POST'])
def InvoiceStatusReport(request):
    if request.method == 'POST':
        try:
            user = request.data.get('user_id')
            start_date = request.data.get('start_date', None)
            end_date = request.data.get('end_date', None)

            report = {}
            report['completed'] = 0
            report['pending'] = 0

            if start_date is None and end_date is None:
                transactions = Transaction.objects.filter(user_id=user, type__in=['event_sale','sale','event_purchase','purchase'])
            else:
                transactions = Transaction.objects.filter(user_id=user, type__in=['event_sale','sale','event_purchase','purchase'], created_on__range=[start_date, end_date])

            for transaction in transactions:
                if transaction.total_amount == (transaction.recived_or_paid_amount + transaction.settled_amount):
                    report['completed'] += 1
                else:
                    report['pending'] += 1

            return Response(report)
        
        except Exception as e:
            logger.error(f"API: Invoice Status Report - An error occurred: {str(e)}", exc_info=True)
            return Response({"error": "An error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    return Response({"error": "Invalid request"}, status=400)


### Invoice Panding for Completion
@api_view(['POST'])
def CompletionReport(request):
    if request.method == 'POST':
        try:
            user = request.data.get('user_id')
            start_date = request.data.get('start_date', None)
            end_date = request.data.get('end_date', None)

            data = []

            if start_date is None and end_date is None:
                transactions = Transaction.objects.filter(user_id=user, type='event_sale')
            else:
                transactions = Transaction.objects.filter(user_id=user, created_on__range=[start_date, end_date], type__in=['event_sale', 'estimate'])

            for transaction in transactions:
                quotation = Quotation.objects.get(pk=transaction.quotation_id.id)
                eventdays = EventDay.objects.filter(quotation_id=quotation.id)

                add_transaction = True

                for eventday in eventdays:
                    inventorydetails = InventoryDetails.objects.filter(eventday_id=eventday.id)

                    for inventorydetail in inventorydetails:
                        exposuredetails = ExposureDetails.objects.filter(inventorydetails_id=inventorydetail.id)

                        if len(exposuredetails) == 0:
                            add_transaction = False
                            break

                if not add_transaction:
                    data.append(transaction)

            return Response(TransactionSerializer(data, many=True).data)

        except Exception as e:
            logger.error(f"API: Completion Report - An error occurred: {str(e)}", exc_info=True)
            return Response({"error": "An error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({"error": "Invalid request"}, status=400)


### Cash & Bank 
@api_view(['POST'])
def CashAndBank(request):
    if request.method == 'POST':
        try:
            user = request.data.get('user_id')

            cash_payment_in = Transaction.objects.filter(user_id=user, payment_type='cash', type__in=['payment_in']).aggregate(Sum('total_amount'))['total_amount__sum']
            cash_payment_in = cash_payment_in if cash_payment_in is not None else 0
            cash_payment_out = Transaction.objects.filter(user_id=user, payment_type='cash', type__in=['payment_out']).aggregate(Sum('total_amount'))['total_amount__sum']
            cash_payment_out = cash_payment_out if cash_payment_out is not None else 0
            cash_sale = Transaction.objects.filter(user_id=user, payment_type='cash', type__in=['sale','event_sale']).aggregate(Sum('advance_amount'))['advance_amount__sum']
            cash_sale = cash_sale if cash_sale is not None else 0
            cash_purchase = Transaction.objects.filter(user_id=user, payment_type='cash', type__in=['purchase','event_purchase']).aggregate(Sum('advance_amount'))['advance_amount__sum']
            cash_purchase = cash_purchase if cash_purchase is not None else 0


            cheque_payment_in = Transaction.objects.filter(user_id=user, payment_type='cheque', type__in=['payment_in']).aggregate(Sum('total_amount'))['total_amount__sum']
            cheque_payment_in = cheque_payment_in if cheque_payment_in is not None else 0
            cheque_payment_out = Transaction.objects.filter(user_id=user, payment_type='cheque', type__in=['payment_out']).aggregate(Sum('total_amount'))['total_amount__sum']
            cheque_payment_out = cheque_payment_out if cheque_payment_out is not None else 0
            cheque_sale = Transaction.objects.filter(user_id=user, payment_type='cheque', type__in=['sale','event_sale']).aggregate(Sum('advance_amount'))['advance_amount__sum']
            cheque_sale = cheque_sale if cheque_sale is not None else 0
            cheque_purchase = Transaction.objects.filter(user_id=user, payment_type='cheque', type__in=['purchase','event_purchase']).aggregate(Sum('advance_amount'))['advance_amount__sum']
            cheque_purchase = cheque_purchase if cheque_purchase is not None else 0


            net_banking_payment_in = Transaction.objects.filter(user_id=user, payment_type='net_banking', type__in=['payment_in']).aggregate(Sum('total_amount'))['total_amount__sum']
            net_banking_payment_in = net_banking_payment_in if net_banking_payment_in is not None else 0
            net_banking_payment_out = Transaction.objects.filter(user_id=user, payment_type='net_banking', type__in=['payment_out']).aggregate(Sum('total_amount'))['total_amount__sum']
            net_banking_payment_out = net_banking_payment_out if net_banking_payment_out is not None else 0
            net_banking_sale = Transaction.objects.filter(user_id=user, payment_type='net_banking', type__in=['sale','event_sale']).aggregate(Sum('advance_amount'))['advance_amount__sum']
            net_banking_sale = net_banking_sale if net_banking_sale is not None else 0
            net_banking_purchase = Transaction.objects.filter(user_id=user, payment_type='net_banking', type__in=['purchase','event_purchase']).aggregate(Sum('advance_amount'))['advance_amount__sum']
            net_banking_purchase = net_banking_purchase if net_banking_purchase is not None else 0


            upi_payment_in = Transaction.objects.filter(user_id=user, payment_type='upi', type__in=['payment_in']).aggregate(Sum('total_amount'))['total_amount__sum']
            upi_payment_in = upi_payment_in if upi_payment_in is not None else 0
            upi_payment_out = Transaction.objects.filter(user_id=user, payment_type='upi', type__in=['payment_out']).aggregate(Sum('total_amount'))['total_amount__sum']
            upi_payment_out = upi_payment_out if upi_payment_out is not None else 0
            upi_sale = Transaction.objects.filter(user_id=user, payment_type='upi', type__in=['sale','event_sale']).aggregate(Sum('advance_amount'))['advance_amount__sum']
            upi_sale = upi_sale if upi_sale is not None else 0
            upi_purchase = Transaction.objects.filter(user_id=user, payment_type='upi', type__in=['purchase','event_purchase']).aggregate(Sum('advance_amount'))['advance_amount__sum']
            upi_purchase = upi_purchase if upi_purchase is not None else 0


            data = {'total_cash' : (cash_payment_in + cash_sale) - (cash_payment_out + cash_purchase),
                    'total_cheque' : {'received' : (cheque_payment_in + cheque_sale),
                                    'paid' : (cheque_payment_out + cheque_purchase)},
                    'total_net_banking' : (net_banking_payment_in + net_banking_sale) - (net_banking_payment_out + net_banking_purchase),
                    'total_upi' : (upi_payment_in + upi_sale) - (upi_payment_out + upi_purchase)}

            return Response(data)
        
        except Exception as e:
            logger.error(f"API: Cash And Bank - An error occurred: {str(e)}", exc_info=True)
            return Response({"error": "An error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    return Response({"error": "Invalid request"}, status=400)



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
    
