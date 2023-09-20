from django.shortcuts import render
from django.db.models import Sum, Count, Q

from django.http import  HttpResponse
from django.db.models.functions import TruncMonth, TruncYear

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from app.utils import convert_time_utc_to_local, link_transaction
from .models import *
from .serializers import *
from .pagination import MyPagination
from .resource import *

from datetime import date
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
        user = User.objects.get(pk=pk)
        old_pic = f"digi_profile_pic/{os.path.basename(user.profile_pic)}" if user.profile_pic else None

        ## SET NEW PASSWORD AS PASSWORD ##
        if 'password' in request.data:
            user.set_password(request.data['password'])
            user.save()
            request.data.pop('password')

        ## ADD USER PROFILE PIC IN BUCKET ##
        if 'profile_pic' in request.data:
            bucket_name = config('wasabisys_bucket_name')
            region = config('wasabisys_region')
            s3 = boto3.client('s3',
                          endpoint_url=config('wasabisys_endpoint_url'),
                          aws_access_key_id=config('wasabisys_access_key_id'),
                          aws_secret_access_key=config('wasabisys_secret_access_key')
                          )
            
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

    # def list(self, request):
    #     querysets = self.filter_queryset(self.get_queryset())
    #     paginator = MyPagination()  
    #     paginated_queryset = paginator.paginate_queryset(querysets, request)
    #     data = []
    #     for queryset in paginated_queryset:
    #         total_amount = Transaction.objects.filter(quotation_id=queryset.id).aggregate(Sum('amount'))['amount__sum']
    #         total_amount = total_amount if total_amount is not None else 0
    #         s_transaction = Transaction.objects.filter(quotation_id=queryset.id)
    #         serializers = QuotationSerializer(queryset)
    #         transaction = TransactionSerializer(s_transaction, many=True)
    #         payable_amount = queryset.final_amount - queryset.discount
    #         data.append({"quotation":serializers.data,
    #                      "transaction":transaction.data,
    #                      "payable_amount":payable_amount,
    #                      "received_amount":total_amount})

    #     return paginator.get_paginated_response(data)


    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # print("Instance ::", instance)
        data = {
            "quotation_data": QuotationSerializer(instance).data, 
            "datas": []
            }

        eventdays = EventDay.objects.filter(quotation_id=instance.id)
        # print("EventDays ::", eventdays)
        for eventday in eventdays:
            eventday_data = {
                "event_day": EventDaySerializer(eventday).data,
                "event_details": [],
                "description": []
            }

            eventdetails = EventDetails.objects.filter(eventday_id=eventday.id)
            # print("EventDetails :: ", eventdetails)
            for eventdetail in eventdetails:
                eventday_data["event_details"].append(EventDetailsSerializer(eventdetail).data)

            inventorydetails = InventoryDetails.objects.filter(eventday_id = eventday.id)
            # print("inventorydetails :: ",inventorydetails)
            
            for inventorydetail in inventorydetails:
                exposuredetails = ExposureDetails.objects.filter(inventorydetails_id=inventorydetail.id)
                print("exposuredetails :: ",exposuredetails)
                # exposure_details_list = []

                # grouped_exposure_details = exposuredetails.values('staff_id','inventorydetails_id','price').annotate(event_ids_list=ArrayAgg('eventdetails_id'))
                # exposure = {}

                # for entry in grouped_exposure_details:
                #     exposure = {
                #     "staff_id" : entry['staff_id'],
                #     "inventorydetails_id" : entry['inventorydetails_id'],
                #     "event_ids_list" : entry['event_ids_list'],
                #     "price" : entry['price'],
                #     }
                #     exposure_details_list.append(exposure)

                eventday_data["description"].append({
                    "inventory_details": InventoryDetailsSerializer(inventorydetail).data,
                    "exposure_details": ExposureDetailsSerializer(exposuredetails, many=True).data
                })
                
            data["datas"].append(eventday_data)

        transaction_data = Transaction.objects.get(quotation_id=instance.id)
        # print("Transaction data :: ", transaction_data)
        data['transaction_data'] = TransactionSerializer(transaction_data).data

        # print(data)
        return Response(data)


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
        
        final_eventdetails_data = []
        final_inventorydetails_data = []
        final_exposuredetails_data = []

        
        for data in datas:
            ### FOR ADD EVENT DAY DATA ###
            # print("DATA ::",data)
            eventdate_data = {
                'event_date': data['event_date'],
                'quotation_id':quotation_instance.id
            }
            # print("Event Date Data ::",eventdate_data)
            eventdaySerializer = EventDaySerializer(data=eventdate_data)
            if eventdaySerializer.is_valid():
                eventday_instance = eventdaySerializer.save()
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

        if transaction['is_converted'] == 'true' and linktransaction_data is not None:
            link_transaction(transaction_instance.id, linktransaction_data)

        if transaction['is_converted'] == 'true':
            ### ADD BILL FOR EXOISURE ###
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
            # print("FINAL INSTANCE :: ", finall_instance)

        advance_amount = transaction.get('recived_or_paid_amount', None)
        if advance_amount is not None:
            try:
                balance = Balance.objects.get(customer_id=quotation_instance.customer_id.id)
            except:
                balance = None

            # print("BALANCE :: ",balance)

            if balance is None:
                balance_data = {
                    'customer_id' : quotation_instance.customer_id.id,
                    'amount' : advance_amount
                }
                # print("Balance Data :: ", balance_data)
                balanceSerializer = BalanceSerializer(data=balance_data)
                if balanceSerializer.is_valid():
                    balanceSerializer.save()
                else:
                    return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
            else:
                balance_data = {
                    'customer_id' : quotation_instance.customer_id.id,
                    'amount' : balance.amount + float(advance_amount)
                }
                # print("Balance Data :: ", balance_data)
                balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                if balanceSerializer.is_valid():
                    balanceSerializer.save()
                else:
                    return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "quotation_data":QuotationSerializer(quotation_instance).data,
            "eventday_data":EventDaySerializer(eventday_instance).data,
            "eventdetails_data":EventDetailsSerializer(final_eventdetails_data, many=True).data,
            "inventorydetails_data":InventoryDetailsSerializer(final_inventorydetails_data, many=True).data,
            "exposuredetails_data":ExposureDetailsSerializer(final_exposuredetails_data, many=True).data,
            "transaction_data":TransactionSerializer(transaction_instance).data})


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
                            print("inventorydetails_instance :::", copy_inventorydetails_instance)
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

                linktransaction_data = request.data.get('linktransaction_data', None)
                # print("link_transaction_data :: ", linktransaction_data)
                if linktransaction_data is not None:
                    link_transaction(copy_transaction_instance.id, linktransaction_data)

                advance_amount = transaction_data.get('recived_or_paid_amount', None)
                if advance_amount is not None:
                    try:
                        balance = Balance.objects.get(customer_id=copy_quotation_instance.customer_id.id)
                    except:
                        balance = None

                    # print("BALANCE :: ",balance)

                    if balance is None:
                        balance_data = {
                            'customer_id' : copy_quotation_instance.customer_id.id,
                            'amount' : advance_amount
                        }
                        # print("Balance Data :: ", balance_data)
                        balanceSerializer = BalanceSerializer(data=balance_data)
                        if balanceSerializer.is_valid():
                            balanceSerializer.save()
                        else:
                            return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        # print("OLD BILL")
                        old_amount = transaction.total_amount
                        # print("OLD AMOUNT :: ", old_amount)
                        new_amount = float(advance_amount)
                        # print("NEW AMOUNT :: ", new_amount)
                        # print("(old_amount - new_amount) > 0 ::: ", (old_amount - new_amount) > 0)
                        if (old_amount - new_amount) > 0:
                            differnece =  old_amount - new_amount
                            # print("DIFFERNECE :: ", differnece)
                            # updated_amount = transaction.recived_or_paid_amount - differnece
                            # print("UPDATED AMOUNT :: ", updated_amount)
                            amount = balance.amount - differnece
                            # print("Amount :: ", amount)

                        # print("(new_amount - old_amount) > 0 ::: ", (new_amount - old_amount) > 0)
                        if (new_amount - old_amount) > 0:
                            differnece =  new_amount - old_amount
                            # print("DIFFERNECE :: ", differnece)
                            # updated_amount = transaction.recived_or_paid_amount + differnece
                            # print("UPDATED AMOUNTTTTTT :: ", updated_amount)
                            amount = balance.amount + differnece
                            # print("Amount :: ", amount)

                        balance_data = {
                            'customer_id' : copy_quotation_instance.customer_id.id,
                            'amount' : amount
                            # 'amount' : balance.amount + float(advance_amount)
                        }
                        # print("Balance Data :: ", balance_data)
                        balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                        if balanceSerializer.is_valid():
                            balanceSerializer.save()
                        else:
                            return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

                
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
                t_serializer = TransactionSerializer(transaction, data=transaction_data, partial=True)
                if t_serializer.is_valid():
                    t_serializer.save()
                else:
                    return Response(t_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
                advance_amount = transaction_data.get('recived_or_paid_amount', None)
                if advance_amount is not None:
                    try:
                        balance = Balance.objects.get(customer_id=quotation_instance.customer_id.id)
                    except:
                        balance = None

                    # print("BALANCE :: ",balance)

                    if balance is None:
                        balance_data = {
                            'customer_id' : quotation_instance.customer_id.id,
                            'amount' : advance_amount
                        }
                        # print("Balance Data :: ", balance_data)
                        balanceSerializer = BalanceSerializer(data=balance_data)
                        if balanceSerializer.is_valid():
                            balanceSerializer.save()
                        else:
                            return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        # print("OLD BILL")
                        old_amount = transaction.total_amount
                        # print("OLD AMOUNT :: ", old_amount)
                        new_amount = float(advance_amount)
                        # print("NEW AMOUNT :: ", new_amount)
                        # print("(old_amount - new_amount) > 0 ::: ", (old_amount - new_amount) > 0)
                        if (old_amount - new_amount) > 0:
                            differnece =  old_amount - new_amount
                            # print("DIFFERNECE :: ", differnece)
                            # updated_amount = transaction.recived_or_paid_amount - differnece
                            # print("UPDATED AMOUNT :: ", updated_amount)
                            amount = balance.amount - differnece
                            # print("Amount :: ", amount)

                        # print("(new_amount - old_amount) > 0 ::: ", (new_amount - old_amount) > 0)
                        if (new_amount - old_amount) > 0:
                            differnece =  new_amount - old_amount
                            # print("DIFFERNECE :: ", differnece)
                            # updated_amount = transaction.recived_or_paid_amount + differnece
                            # print("UPDATED AMOUNTTTTTT :: ", updated_amount)
                            amount = balance.amount + differnece
                            # print("Amount :: ", amount)

                        balance_data = {
                            'customer_id' : quotation_instance.customer_id.id,
                            'amount' : amount,
                            # 'amount' : balance.amount + float(advance_amount)
                        }
                        # print("Balance Data :: ", balance_data)
                        balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                        if balanceSerializer.is_valid():
                            balanceSerializer.save()
                        else:
                            return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
                else:
                    # print("NEW BILL")
                    i_transactionSerializer = TransactionSerializer(data=i_transaction_data)
                    if i_transactionSerializer.is_valid():
                        t_instance = i_transactionSerializer.save()
                        finall_instance.append(t_instance)
                    else:
                        return Response(i_transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
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
        
        if linktransaction_data is not None:
            link_transaction(transaction_instance.id, linktransaction_data)

        advance_amount = transaction_data.get('recived_or_paid_amount', None)
        if advance_amount is not None:
            try:
                balance = Balance.objects.get(customer_id=transaction_data['customer_id'])
            except:
                balance = None

            # print("BALANCE :: ",balance)

            if balance is None:
                balance_data = {
                    'customer_id' : transaction_data['customer_id'],
                    'amount' : advance_amount
                }
                # print("Balance Data :: ", balance_data)
                balanceSerializer = BalanceSerializer(data=balance_data)
                if balanceSerializer.is_valid():
                    balanceSerializer.save()
                else:
                    return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
            else:
                balance_data = {
                    'customer_id' : transaction_data['customer_id'],
                    'amount' : balance.amount + float(advance_amount)
                }
                # print("Balance Data :: ", balance_data)
                balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                if balanceSerializer.is_valid():
                    balanceSerializer.save()
                else:
                    return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

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

        if linktransaction_data is not None:
            link_transaction(transaction_instance.id, linktransaction_data)

        # transaction_type = transaction_data.get('type')
        # if transaction_type in ('sale', 'event_sale', 'payment_out'):

        #     # customer_id = transaction_data.get('customer_id', None)
        #     # # print("CUSTOMER ID :: ", customer_id)
        #     # if customer_id is not None:
        #     #     # print("ADD BALANCE FOR CUSTOMER")
        #     #     try:
        #     #         balance = Balance.objects.get(customer_id=customer_id)
        #     #     except:
        #     #         balance = None

        #     #     # print("BALANCE :: ",balance)

        #     #     if balance is None:
        #     #         balance_data = {
        #     #             'customer_id' : customer_id,
        #     #             'amount' : transaction_data.get('total_amount')
        #     #         }
        #     #         # print("Balance Data :: ", balance_data)
        #     #         balanceSerializer = BalanceSerializer(data=balance_data)
        #     #         if balanceSerializer.is_valid():
        #     #             balanceSerializer.save()
        #     #         else:
        #     #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
        #     #     else:
        #     #         balance_data = {
        #     #             'customer_id' : customer_id,
        #     #             'amount' : balance.amount + float(transaction_data.get('total_amount'))
        #     #         }
        #     #         # print("Balance Data :: ", balance_data)
        #     #         balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
        #     #         if balanceSerializer.is_valid():
        #     #             balanceSerializer.save()
        #     #         else:
        #     #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

        #     # staff_id = transaction_data.get('staff_id', None)
        #     # # print("STAFF ID :: ",staff_id)
        #     # if staff_id is not None:
        #     #     # print("ADD BALANCE FOR STAFF")
        #     #     try:
        #     #         balance = Balance.objects.get(staff_id=staff_id)
        #     #     except:
        #     #         balance = None

        #     #     # print("BALANCE :: ",balance)
        #     #     # print("Amount :: ", balance.amount)
        #     #     if balance is None:
        #     #         balance_data = {
        #     #             'staff_id' : staff_id,
        #     #             'amount' : transaction_data.get('total_amount')
        #     #         }
        #     #         # print("Balance Data :: ", balance_data)
                    
        #     #         balanceSerializer = BalanceSerializer(data=balance_data)
        #     #         if balanceSerializer.is_valid():
        #     #             balanceSerializer.save()
        #     #         else:
        #     #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
        #     #     else:
        #     #         balance_data = {
        #     #             'staff_id' : staff_id,
        #     #             'amount' : balance.amount + float(transaction_data.get('total_amount'))
        #     #         }
        #     #         # print("Balance Data :: ", balance_data)
        #     #         balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
        #     #         if balanceSerializer.is_valid():
        #     #             balanceSerializer.save()
        #     #         else:
        #     #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

        #     pass

        # if transaction_type in ('payment_in', 'event_purchase', 'purchase'):

        #     # customer_id = transaction_data.get('customer_id', None)
        #     # # print("CUSTOMER ID :: ", customer_id)
        #     # if customer_id is not None:
        #     #     # print("ADD BALANCE FOR CUSTOMER")
        #     #     try:
        #     #         balance = Balance.objects.get(customer_id=customer_id)
        #     #     except:
        #     #         balance = None

        #     #     # print("BALANCE :: ",balance)

        #     #     if balance is None:
        #     #         balance_data = {
        #     #             'customer_id' : customer_id,
        #     #             'amount' : transaction_data.get('total_amount')
        #     #         }
        #     #         # print("Balance Data :: ", balance_data)
        #     #         balanceSerializer = BalanceSerializer(data=balance_data)
        #     #         if balanceSerializer.is_valid():
        #     #             balanceSerializer.save()
        #     #         else:
        #     #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
        #     #     else:
        #     #         balance_data = {
        #     #             'customer_id' : customer_id,
        #     #             'amount' : balance.amount - float(transaction_data.get('total_amount'))
        #     #         }
        #     #         # print("Balance Data :: ", balance_data)
        #     #         balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
        #     #         if balanceSerializer.is_valid():
        #     #             balanceSerializer.save()
        #     #         else:
        #     #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

        #     # staff_id = transaction_data.get('staff_id', None)
        #     # # print("STAFF ID :: ",staff_id)
        #     # if staff_id is not None:
        #     #     # print("ADD BALANCE FOR STAFF")
        #     #     try:
        #     #         balance = Balance.objects.get(staff_id=staff_id)
        #     #     except:
        #     #         balance = None

        #     #     # print("BALANCE :: ",balance)
        #     #     # print("Amount :: ", balance.amount)
        #     #     if balance is None:
        #     #         balance_data = {
        #     #             'staff_id' : staff_id,
        #     #             'amount' : transaction_data.get('total_amount')
        #     #         }
        #     #         # print("Balance Data :: ", balance_data)
                    
        #     #         balanceSerializer = BalanceSerializer(data=balance_data)
        #     #         if balanceSerializer.is_valid():
        #     #             balanceSerializer.save()
        #     #         else:
        #     #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
        #     #     else:
        #     #         balance_data = {
        #     #             'staff_id' : staff_id,
        #     #             'amount' : balance.amount - float(transaction_data.get('total_amount'))
        #     #         }
        #     #         # print("Balance Data :: ", balance_data)
        #     #         balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
        #     #         if balanceSerializer.is_valid():
        #     #             balanceSerializer.save()
        #     #         else:
        #     #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

        #     pass

        # staff_id = transaction_data.get('staff_id', None)
        # # print("STAFF ID :: ",staff_id)
        # if staff_id is not None:
        #     # print("ADD BALANCE FOR STAFF")
        #     try:
        #         balance = Balance.objects.get(staff_id=staff_id)
        #     except:
        #         balance = None

        #     # print("BALANCE :: ",balance)
        #     # print("Amount :: ", balance.amount)
        #     if balance is None:
        #         balance_data = {
        #             'staff_id' : staff_id,
        #             'amount' : transaction_data.get('total_amount')
        #         }
        #         # print("Balance Data :: ", balance_data)
                
        #         balanceSerializer = BalanceSerializer(data=balance_data)
        #         if balanceSerializer.is_valid():
        #             balanceSerializer.save()
        #         else:
        #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
        #     else:
        #         balance_data = {
        #             'staff_id' : staff_id,
        #             'amount' : balance.amount + float(transaction_data.get('total_amount'))
        #         }
        #         # print("Balance Data :: ", balance_data)
        #         balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
        #         if balanceSerializer.is_valid():
        #             balanceSerializer.save()
        #         else:
        #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
        # customer_id = transaction_data.get('customer_id', None)
        # # print("CUSTOMER ID :: ", customer_id)
        # if customer_id is not None:
        #     # print("ADD BALANCE FOR CUSTOMER")
        #     try:
        #         balance = Balance.objects.get(customer_id=customer_id)
        #     except:
        #         balance = None

        #     # print("BALANCE :: ",balance)

        #     if balance is None:
        #         balance_data = {
        #             'customer_id' : customer_id,
        #             'amount' : transaction_data.get('total_amount')
        #         }
        #         # print("Balance Data :: ", balance_data)
        #         balanceSerializer = BalanceSerializer(data=balance_data)
        #         if balanceSerializer.is_valid():
        #             balanceSerializer.save()
        #         else:
        #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
        #     else:
        #         balance_data = {
        #             'customer_id' : customer_id,
        #             'amount' : balance.amount + float(transaction_data.get('total_amount'))
        #         }
        #         # print("Balance Data :: ", balance_data)
        #         balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
        #         if balanceSerializer.is_valid():
        #             balanceSerializer.save()
        #         else:
        #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
        # all_linktransaction = []
        # if linktransaction_datas is not None:
        #     # print("ADD LINK TRANSACTION")
        #     for linktransaction_data in linktransaction_datas:
        #         linktransaction_data['from_transaction_id'] = transaction_instance.id
        #         # print("linktransaction_data :: ", linktransaction_data)
        #         linktransactionSerializer = LinkTransactionSerializer(data=linktransaction_data)
        #         if linktransactionSerializer.is_valid():
        #             linktransaction_instance = linktransactionSerializer.save()
        #             all_linktransaction.append(linktransaction_instance)
        #         else:
        #             return Response(linktransactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        # for linktransaction in all_linktransaction:
        #     # print("Single transaction :: ", linktransaction)
        #     # print("TO TRANSACTION ID :: ",linktransaction.to_transaction_id.id)
        #     # print("AMOUNT :: ", linktransaction.linked_amount, "TYPE :: ", type(linktransaction.linked_amount))

        #     transaction = Transaction.objects.get(id = linktransaction.to_transaction_id.id)
        #     # print("Transaction :: ", transaction)
        #     # print("RESCIVED AMOUNT :: ", transaction.recived_or_paid_amount, "TYPE :: ", type(transaction.recived_or_paid_amount))
        #     transaction.recived_or_paid_amount = transaction.recived_or_paid_amount + linktransaction.linked_amount
        #     transaction.save()

        return Response(data)

    def update(self, request, pk=None, *args, **kwargs):
        key = request.data.get('key')

        transaction = Transaction.objects.get(pk=pk)
        # print("Transaction :: ", transaction)
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
            print("Link Transaction Data :: ",linktransaction_data)

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
                        
                        advance_amount = transaction_data.get('recived_or_paid_amount', None)
                        if advance_amount is not None:

                            if transaction_data['type'] == 'sale':
                                if transaction_data['customer_id'] is not None:
                                    try:
                                        balance = Balance.objects.get(customer_id=transaction_data['customer_id'])
                                    except:
                                        balance = None

                                    if balance is None:
                                        balance_data = {
                                            'customer_id' : transaction_data['customer_id'],
                                            'amount' : advance_amount
                                        }
                                        # print("Balance Data :: ", balance_data)
                                        balanceSerializer = BalanceSerializer(data=balance_data)
                                        if balanceSerializer.is_valid():
                                            balanceSerializer.save()
                                        else:
                                            return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                                    else:
                                        # print("OLD BILL")
                                        old_amount = transaction.total_amount
                                        # print("OLD AMOUNT :: ", old_amount)
                                        new_amount = float(advance_amount)
                                        # print("NEW AMOUNT :: ", new_amount)
                                        # print("(old_amount - new_amount) > 0 ::: ", (old_amount - new_amount) > 0)
                                        if (old_amount - new_amount) > 0:
                                            differnece =  old_amount - new_amount
                                            # print("DIFFERNECE :: ", differnece)
                                            # updated_amount = transaction.recived_or_paid_amount - differnece
                                            # print("UPDATED AMOUNT :: ", updated_amount)
                                            amount = balance.amount - differnece
                                            # print("Amount :: ", amount)

                                        # print("(new_amount - old_amount) > 0 ::: ", (new_amount - old_amount) > 0)
                                        if (new_amount - old_amount) > 0:
                                            differnece =  new_amount - old_amount
                                            # print("DIFFERNECE :: ", differnece)
                                            # updated_amount = transaction.recived_or_paid_amount + differnece
                                            # print("UPDATED AMOUNTTTTTT :: ", updated_amount)
                                            amount = balance.amount + differnece
                                            # print("Amount :: ", amount)

                                        balance_data = {
                                            'customer_id' : transaction_data['customer_id'],
                                            'amount' : amount
                                            # 'amount' : balance.amount + float(advance_amount)
                                        }
                                        # print("Balance Data :: ", balance_data)
                                        balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                                        if balanceSerializer.is_valid():
                                            balanceSerializer.save()
                                        else:
                                            return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

                                if transaction_data['staff_id'] is not None:
                                    try:
                                        balance = Balance.objects.get(staff_id=transaction_data['staff_id'])
                                    except:
                                        balance = None

                                    if balance is None:
                                        balance_data = {
                                            'customer_id' : transaction_data['staff_id'],
                                            'amount' : advance_amount
                                        }
                                        # print("Balance Data :: ", balance_data)
                                        balanceSerializer = BalanceSerializer(data=balance_data)
                                        if balanceSerializer.is_valid():
                                            balanceSerializer.save()
                                        else:
                                            return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                                    else:
                                        # print("OLD BILL")
                                        old_amount = transaction.total_amount
                                        # print("OLD AMOUNT :: ", old_amount)
                                        new_amount = float(advance_amount)
                                        # print("NEW AMOUNT :: ", new_amount)
                                        # print("(old_amount - new_amount) > 0 ::: ", (old_amount - new_amount) > 0)
                                        if (old_amount - new_amount) > 0:
                                            differnece =  old_amount - new_amount
                                            # print("DIFFERNECE :: ", differnece)
                                            # updated_amount = transaction.recived_or_paid_amount - differnece
                                            # print("UPDATED AMOUNT :: ", updated_amount)
                                            amount = balance.amount - differnece
                                            # print("Amount :: ", amount)

                                        # print("(new_amount - old_amount) > 0 ::: ", (new_amount - old_amount) > 0)
                                        if (new_amount - old_amount) > 0:
                                            differnece =  new_amount - old_amount
                                            # print("DIFFERNECE :: ", differnece)
                                            # updated_amount = transaction.recived_or_paid_amount + differnece
                                            # print("UPDATED AMOUNTTTTTT :: ", updated_amount)
                                            amount = balance.amount + differnece
                                            # print("Amount :: ", amount)

                                        balance_data = {
                                            'customer_id' : transaction_data['staff_id'],
                                            'amount' : amount
                                            # 'amount' : balance.amount + float(advance_amount)
                                        }
                                        # print("Balance Data :: ", balance_data)
                                        balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                                        if balanceSerializer.is_valid():
                                            balanceSerializer.save()
                                        else:
                                            return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                            
                            if transaction_data['type'] == 'purchase': 
                                if transaction_data['customer_id'] is not None:
                                    try:
                                        balance = Balance.objects.get(customer_id=transaction_data['customer_id'])
                                    except:
                                        balance = None

                                    if balance is None:
                                        balance_data = {
                                            'customer_id' : transaction_data['customer_id'],
                                            'amount' : advance_amount
                                        }
                                        # print("Balance Data :: ", balance_data)
                                        balanceSerializer = BalanceSerializer(data=balance_data)
                                        if balanceSerializer.is_valid():
                                            balanceSerializer.save()
                                        else:
                                            return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                                    else:
                                        # print("OLD BILL")
                                        old_amount = transaction.total_amount
                                        # print("OLD AMOUNT :: ", old_amount)
                                        new_amount = float(advance_amount)
                                        # print("NEW AMOUNT :: ", new_amount)
                                        # print("(old_amount - new_amount) > 0 ::: ", (old_amount - new_amount) > 0)
                                        if (old_amount - new_amount) > 0:
                                            differnece =  old_amount - new_amount
                                            # print("DIFFERNECE :: ", differnece)
                                            # updated_amount = transaction.recived_or_paid_amount - differnece
                                            # print("UPDATED AMOUNT :: ", updated_amount)
                                            amount = balance.amount + differnece
                                            # print("Amount :: ", amount)

                                        # print("(new_amount - old_amount) > 0 ::: ", (new_amount - old_amount) > 0)
                                        if (new_amount - old_amount) > 0:
                                            differnece =  new_amount - old_amount
                                            # print("DIFFERNECE :: ", differnece)
                                            # updated_amount = transaction.recived_or_paid_amount + differnece
                                            # print("UPDATED AMOUNTTTTTT :: ", updated_amount)
                                            amount = balance.amount - differnece
                                            # print("Amount :: ", amount)

                                        balance_data = {
                                            'customer_id' : transaction_data['customer_id'],
                                            'amount' : amount
                                            # 'amount' : balance.amount + float(advance_amount)
                                        }
                                        # print("Balance Data :: ", balance_data)
                                        balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                                        if balanceSerializer.is_valid():
                                            balanceSerializer.save()
                                        else:
                                            return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

                                if transaction_data['staff_id'] is not None:
                                    try:
                                        balance = Balance.objects.get(staff_id=transaction_data['staff_id'])
                                    except:
                                        balance = None

                                    if balance is None:
                                        balance_data = {
                                            'customer_id' : transaction_data['staff_id'],
                                            'amount' : advance_amount
                                        }
                                        # print("Balance Data :: ", balance_data)
                                        balanceSerializer = BalanceSerializer(data=balance_data)
                                        if balanceSerializer.is_valid():
                                            balanceSerializer.save()
                                        else:
                                            return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                                    else:
                                        # print("OLD BILL")
                                        old_amount = transaction.total_amount
                                        # print("OLD AMOUNT :: ", old_amount)
                                        new_amount = float(advance_amount)
                                        # print("NEW AMOUNT :: ", new_amount)
                                        # print("(old_amount - new_amount) > 0 ::: ", (old_amount - new_amount) > 0)
                                        if (old_amount - new_amount) > 0:
                                            differnece =  old_amount - new_amount
                                            # print("DIFFERNECE :: ", differnece)
                                            # updated_amount = transaction.recived_or_paid_amount - differnece
                                            # print("UPDATED AMOUNT :: ", updated_amount)
                                            amount = balance.amount - differnece
                                            # print("Amount :: ", amount)

                                        # print("(new_amount - old_amount) > 0 ::: ", (new_amount - old_amount) > 0)
                                        if (new_amount - old_amount) > 0:
                                            differnece =  new_amount - old_amount
                                            # print("DIFFERNECE :: ", differnece)
                                            # updated_amount = transaction.recived_or_paid_amount + differnece
                                            # print("UPDATED AMOUNTTTTTT :: ", updated_amount)
                                            amount = balance.amount + differnece
                                            # print("Amount :: ", amount)

                                        balance_data = {
                                            'customer_id' : transaction_data['staff_id'],
                                            'amount' : amount
                                            # 'amount' : balance.amount + float(advance_amount)
                                        }
                                        # print("Balance Data :: ", balance_data)
                                        balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                                        if balanceSerializer.is_valid():
                                            balanceSerializer.save()
                                        else:
                                            return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

                        # if advance_amount is not None:
                        #     try:
                        #         balance = Balance.objects.get(customer_id=transaction_data['customer_id'])
                        #     except:
                        #         balance = None

                        #     # print("BALANCE :: ",balance)

                        #     if balance is None:
                        #         balance_data = {
                        #             'customer_id' : transaction_data['customer_id'],
                        #             'amount' : advance_amount
                        #         }
                        #         # print("Balance Data :: ", balance_data)
                        #         balanceSerializer = BalanceSerializer(data=balance_data)
                        #         if balanceSerializer.is_valid():
                        #             balanceSerializer.save()
                        #         else:
                        #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                        #     else:
                        #         # print("OLD BILL")
                        #         old_amount = transaction.total_amount
                        #         # print("OLD AMOUNT :: ", old_amount)
                        #         new_amount = float(advance_amount)
                        #         # print("NEW AMOUNT :: ", new_amount)
                        #         # print("(old_amount - new_amount) > 0 ::: ", (old_amount - new_amount) > 0)
                        #         if (old_amount - new_amount) > 0:
                        #             differnece =  old_amount - new_amount
                        #             # print("DIFFERNECE :: ", differnece)
                        #             # updated_amount = transaction.recived_or_paid_amount - differnece
                        #             # print("UPDATED AMOUNT :: ", updated_amount)
                        #             amount = balance.amount - differnece
                        #             # print("Amount :: ", amount)

                        #         # print("(new_amount - old_amount) > 0 ::: ", (new_amount - old_amount) > 0)
                        #         if (new_amount - old_amount) > 0:
                        #             differnece =  new_amount - old_amount
                        #             # print("DIFFERNECE :: ", differnece)
                        #             # updated_amount = transaction.recived_or_paid_amount + differnece
                        #             # print("UPDATED AMOUNTTTTTT :: ", updated_amount)
                        #             amount = balance.amount + differnece
                        #             # print("Amount :: ", amount)

                        #         balance_data = {
                        #             'customer_id' : transaction_data['customer_id'],
                        #             'amount' : amount
                        #             # 'amount' : balance.amount + float(advance_amount)
                        #         }
                        #         # print("Balance Data :: ", balance_data)
                        #         balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
                        #         if balanceSerializer.is_valid():
                        #             balanceSerializer.save()
                        #         else:
                        #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
                        

                transaction_data['inventorydescription'] = inventorydescription_ids 
                transactionSerializer = TransactionSerializer(transaction, data=transaction_data, partial=True)
                if transactionSerializer.is_valid():
                    transaction_instance = transactionSerializer.save()
                else:
                    return Response(transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

            print("PKKKK :: ",pk)
            if linktransaction_data is not None:
                link_transaction(pk, linktransaction_data)

            data['tranasaction_data'] = TransactionSerializer(transaction_instance).data
            data['inventorydescription_data'] = InventoryDescriptionSerializer(all_inventory, many=True).data

        if key == 'transaction_update':
            transaction_data = request.data.get('transaction_data')
            # print("Trnasaction Data :: ",transaction_data)
            linktransaction_data = request.data.get('linktransaction_data', None)
            print("Link Transaction Data :: ",linktransaction_data)
            # delete_linktransaction_datas = request.data.get('delete_linktransaction', None)
            # print("Delete Transaction Data :: ",delete_linktransaction_datas)

            # old_amount = transaction.recived_or_paid_amount
            # print("OLD AMOUNT :: ",old_amount)

            transactionSerializer = TransactionSerializer(transaction, data=transaction_data, partial=True)
            if transactionSerializer.is_valid():
                transaction_instance = transactionSerializer.save()
            else:
                return Response(transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            print("PKKKK :: ",pk)
            if linktransaction_data is not None:
                print("LINK TRASACTION FUNCTION")
                link_transaction(pk, linktransaction_data, transaction.type)

            # new_amount = float(transaction_data.get('total_amount'))

            # if transaction_data['customer_id'] is not None:
            #     try:
            #         balance = Balance.objects.get(customer_id=transaction_data['customer_id'])
            #     except:
            #         balance = None

            #     if balance is None:
            #         balance_data = {
            #             'customer_id' : transaction_data['customer_id'],
            #             'amount' : advance_amount
            #         }
            #         print("Balance Data :: ", balance_data)
            #         balanceSerializer = BalanceSerializer(data=balance_data)
            #         if balanceSerializer.is_valid():
            #             balanceSerializer.save()
            #         else:
            #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
            #     else:
            #         print("OLD BILL")
            #         old_amount = transaction.total_amount
            #         print("OLD AMOUNT :: ", old_amount)
            #         new_amount = float(advance_amount)
            #         print("NEW AMOUNT :: ", new_amount)
            #         print("(old_amount - new_amount) > 0 ::: ", (old_amount - new_amount) > 0)
            #         if (old_amount - new_amount) > 0:
            #             differnece =  old_amount - new_amount
            #             print("DIFFERNECE :: ", differnece)
            #             updated_amount = transaction.recived_or_paid_amount - differnece
            #             print("UPDATED AMOUNT :: ", updated_amount)
            #             amount = balance.amount - differnece
            #             print("Amount :: ", amount)

            #         print("(new_amount - old_amount) > 0 ::: ", (new_amount - old_amount) > 0)
            #         if (new_amount - old_amount) > 0:
            #             differnece =  new_amount - old_amount
            #             print("DIFFERNECE :: ", differnece)
            #             updated_amount = transaction.recived_or_paid_amount + differnece
            #             print("UPDATED AMOUNTTTTTT :: ", updated_amount)
            #             amount = balance.amount + differnece
            #             print("Amount :: ", amount)

            #         balance_data = {
            #             'customer_id' : transaction_data['customer_id'],
            #             'amount' : amount
            #             # 'amount' : balance.amount + float(advance_amount)
            #         }
            #         print("Balance Data :: ", balance_data)
            #         balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
            #         if balanceSerializer.is_valid():
            #             balanceSerializer.save()
            #         else:
            #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # if transaction_data['staff_id'] is not None:
            #     try:
            #         balance = Balance.objects.get(staff_id=transaction_data['staff_id'])
            #     except:
            #         balance = None

            #     if balance is None:
            #         balance_data = {
            #             'customer_id' : transaction_data['staff_id'],
            #             'amount' : advance_amount
            #         }
            #         print("Balance Data :: ", balance_data)
            #         balanceSerializer = BalanceSerializer(data=balance_data)
            #         if balanceSerializer.is_valid():
            #             balanceSerializer.save()
            #         else:
            #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
            #     else:
            #         print("OLD BILL")
            #         old_amount = transaction.total_amount
            #         print("OLD AMOUNT :: ", old_amount)
            #         new_amount = float(advance_amount)
            #         print("NEW AMOUNT :: ", new_amount)
            #         print("(old_amount - new_amount) > 0 ::: ", (old_amount - new_amount) > 0)
            #         if (old_amount - new_amount) > 0:
            #             differnece =  old_amount - new_amount
            #             print("DIFFERNECE :: ", differnece)
            #             updated_amount = transaction.recived_or_paid_amount - differnece
            #             print("UPDATED AMOUNT :: ", updated_amount)
            #             amount = balance.amount - differnece
            #             print("Amount :: ", amount)

            #         print("(new_amount - old_amount) > 0 ::: ", (new_amount - old_amount) > 0)
            #         if (new_amount - old_amount) > 0:
            #             differnece =  new_amount - old_amount
            #             print("DIFFERNECE :: ", differnece)
            #             updated_amount = transaction.recived_or_paid_amount + differnece
            #             print("UPDATED AMOUNTTTTTT :: ", updated_amount)
            #             amount = balance.amount + differnece
            #             print("Amount :: ", amount)

            #         balance_data = {
            #             'customer_id' : transaction_data['staff_id'],
            #             'amount' : amount
            #             # 'amount' : balance.amount + float(advance_amount)
            #         }
            #         print("Balance Data :: ", balance_data)
            #         balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
            #         if balanceSerializer.is_valid():
            #             balanceSerializer.save()
            #         else:
            #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

                        #############   

            # if linktransaction_datas is not None:
            #     all_linktransaction = []
            #     for linktransaction_data in linktransaction_datas:
            #         # print("Single link transaction :: ", linktransaction_data)
            #         if linktransaction_data['id'] == '':
            #             # print("New Link Transaction")
            #             linktransaction_data['from_transaction_id'] = transaction_instance.id
            #             # print("linktransaction_data :: ", linktransaction_data)
            #             linktransactionSerializer = LinkTransactionSerializer(data=linktransaction_data)
            #             if linktransactionSerializer.is_valid():
            #                 linktransaction_instance = linktransactionSerializer.save()
            #                 all_linktransaction.append(linktransaction_instance)
            #             else:
            #                 return Response(linktransactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                        
            #             transaction = Transaction.objects.get(id = linktransaction_instance.to_transaction_id.id)
            #             # print("Transaction :: ", transaction)
            #             # print("RESCIVED AMOUNT :: ", transaction.recived_or_paid_amount, "TYPE :: ", type(transaction.recived_or_paid_amount))
            #             transaction.recived_or_paid_amount = transaction.recived_or_paid_amount + linktransaction_instance.linked_amount
            #             transaction.save()

            #         else:
            #             # print("Old Link Transaction")
            #             # print("linktransaction_data :: ", linktransaction_data)
            #             link = LinkTransaction.objects.get(pk=linktransaction_data['id'])
            #             # print("LINK TRANSACTION :: ",link)
            #             old_amount = link.linked_amount
            #             # print("OLD AMOUNT :: ",old_amount)

            #             linktransactionSerializer = LinkTransactionSerializer(link, data=linktransaction_data, partial=True)
            #             if linktransactionSerializer.is_valid():
            #                 linktransaction_instance = linktransactionSerializer.save()
            #                 # print("linktransaction_instance ::: ",linktransaction_instance)
            #                 all_linktransaction.append(linktransaction_instance)
            #             else:
            #                 return Response(linktransactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                        
            #             new_amount = linktransaction_instance.linked_amount
            #             # print("NEW AMOUNT :: ",new_amount)
                        
            #             transaction = Transaction.objects.get(id = linktransaction_instance.to_transaction_id.id)
            #             # print("Transaction :: ", transaction)
            #             # print("RESCIVED AMOUNT :: ", transaction.recived_or_paid_amount, "TYPE :: ", type(transaction.recived_or_paid_amount))

            #             # print("old_amount - new_amount :: ",old_amount - new_amount)
            #             # print("(old_amount - new_amount) > 0 :: ", (old_amount - new_amount) > 0)
                        
                        
            #             if (old_amount - new_amount) > 0:
            #                 differnece =  old_amount - new_amount
            #                 # print("DIFFERNECE :: ", differnece)
            #                 updated_amount = transaction.recived_or_paid_amount - differnece
            #                 # print("UPDATED AMOUNT :: ", updated_amount)
            #                 transaction.recived_or_paid_amount = transaction.recived_or_paid_amount - differnece
            #                 transaction.save()
                            
            #             if (new_amount - old_amount) > 0:
            #                 differnece =  new_amount - old_amount
            #                 # print("DIFFERNECE :: ", differnece)
            #                 updated_amount = transaction.recived_or_paid_amount + differnece
            #                 # print("UPDATED AMOUNTTTTTT :: ", updated_amount)
            #                 transaction.recived_or_paid_amount = transaction.recived_or_paid_amount + differnece
            #                 transaction.save()
                            

            #     data['linktransaction_data'] = LinkTransactionSerializer(all_linktransaction, many=True).data

            # data['tranasaction_data'] = TransactionSerializer(transaction_instance).data

            # if delete_linktransaction_datas is not None:
            #     for delete_linktransaction_data in delete_linktransaction_datas:
            #         # print("Delete Link Transaction :: ", delete_linktransaction_data)
            #         d_linktransaction = LinkTransaction.objects.get(pk = delete_linktransaction_data)
            #         # print("Link Transaction :: ", d_linktransaction.to_transaction_id.id)

            #         transaction = Transaction.objects.get(id = d_linktransaction.to_transaction_id.id)
            #         # print("Transaction :: ", transaction)
            #         # print("RESCIVED AMOUNT :: ", transaction.recived_or_paid_amount, "TYPE :: ", type(transaction.recived_or_paid_amount))
            #         transaction.recived_or_paid_amount = transaction.recived_or_paid_amount - d_linktransaction.linked_amount
            #         transaction.save()

            #         d_linktransaction.delete()

            # staff_id = transaction_data.get('staff_id', None)
            # # print("STAFF ID :: ",staff_id)
            # if staff_id is not None:
            #     # print("ADD BALANCE FOR STAFF")
            #     try:
            #         balance = Balance.objects.get(staff_id=staff_id)
            #     except:
            #         balance = None

            #     # print("BALANCE :: ",balance)
            #     # print("Amount :: ", balance.amount)
            #     if balance is None:
            #         balance_data = {
            #             'staff_id' : staff_id,
            #             'amount' : transaction_data.get('total_amount')
            #         }
            #         # print("Balance Data :: ", balance_data)
                    
            #         balanceSerializer = BalanceSerializer(data=balance_data)
            #         if balanceSerializer.is_valid():
            #             balanceSerializer.save()
            #         else:
            #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
            #     else:
            #         # print("OLD BILL")
            #         old_amount = transaction.total_amount
            #         # print("OLD AMOUNT :: ", old_amount)
            #         new_amount = float(transaction_data.get('total_amount'))
            #         # print("NEW AMOUNT :: ", new_amount)
            #         # print("(old_amount - new_amount) > 0 ::: ", (old_amount - new_amount) > 0)
            #         if (old_amount - new_amount) > 0:
            #             differnece =  old_amount - new_amount
            #             # print("DIFFERNECE :: ", differnece)
            #             # updated_amount = transaction.recived_or_paid_amount - differnece
            #             # print("UPDATED AMOUNT :: ", updated_amount)
            #             amount = balance.amount - differnece
            #             # print("Amount :: ", amount)

            #         # print("(new_amount - old_amount) > 0 ::: ", (new_amount - old_amount) > 0)
            #         if (new_amount - old_amount) > 0:
            #             differnece =  new_amount - old_amount
            #             # print("DIFFERNECE :: ", differnece)
            #             # updated_amount = transaction.recived_or_paid_amount + differnece
            #             # print("UPDATED AMOUNTTTTTT :: ", updated_amount)
            #             amount = balance.amount + differnece
            #             # print("Amount :: ", amount)


            #         balance_data = {
            #             'staff_id' : staff_id,
            #             'amount' : float(amount)
            #             # 'amount' : balance.amount + float(transaction_data.get('total_amount'))
            #         }
            #         # print("Balance Data :: ", balance_data)
            #         balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
            #         if balanceSerializer.is_valid():
            #             balanceSerializer.save()
            #         else:
            #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
            # customer_id = transaction_data.get('customer_id', None)
            # # print("CUSTOMER ID :: ", customer_id)
            # if customer_id is not None:
            #     # print("ADD BALANCE FOR CUSTOMER")
            #     try:
            #         balance = Balance.objects.get(customer_id=customer_id)
            #     except:
            #         balance = None

            #     # print("BALANCE :: ",balance)

            #     if balance is None:
            #         balance_data = {
            #             'customer_id' : customer_id,
            #             'amount' : transaction_data.get('total_amount')
            #         }
            #         # print("Balance Data :: ", balance_data)
            #         balanceSerializer = BalanceSerializer(data=balance_data)
            #         if balanceSerializer.is_valid():
            #             balanceSerializer.save()
            #         else:
            #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
            #     else:
            #         # print("OLD BILL")
            #         old_amount = transaction.total_amount
            #         # print("OLD AMOUNT :: ", old_amount)
            #         new_amount = float(transaction_data.get('total_amount'))
            #         # print("NEW AMOUNT :: ", new_amount)
            #         # print("(old_amount - new_amount) > 0 ::: ", (old_amount - new_amount) > 0)
            #         if (old_amount - new_amount) > 0:
            #             differnece =  old_amount - new_amount
            #             # print("DIFFERNECE :: ", differnece)
            #             # updated_amount = transaction.recived_or_paid_amount - differnece
            #             # print("UPDATED AMOUNT :: ", updated_amount)
            #             amount = balance.amount - differnece
            #             # print("Amount :: ", amount)

            #         # print("(new_amount - old_amount) > 0 ::: ", (new_amount - old_amount) > 0)
            #         if (new_amount - old_amount) > 0:
            #             differnece =  new_amount - old_amount
            #             # print("DIFFERNECE :: ", differnece)
            #             # updated_amount = transaction.recived_or_paid_amount + differnece
            #             # print("UPDATED AMOUNTTTTTT :: ", updated_amount)
            #             amount = balance.amount + differnece
            #             # print("Amount :: ", amount)

            #         balance_data = {
            #             'customer_id' : customer_id,
            #             'amount' : float(amount)
            #             # 'amount' : balance.amount + float(transaction_data.get('total_amount'))
            #         }
            #         # print("Balance Data :: ", balance_data)
            #         balanceSerializer = BalanceSerializer(balance, data=balance_data, partial=True)
            #         if balanceSerializer.is_valid():
            #             balanceSerializer.save()
            #         else:
            #             return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
               
        if key == 'exposure_bill_update':
            transaction_data = request.data.get('transaction_data')
            # print("Trnasaction Data :: ",transaction_data)

            transactionSerializer = TransactionSerializer(transaction, data=transaction_data, partial=True)
            if transactionSerializer.is_valid():
                transaction_instance = transactionSerializer.save()
            else:
                return Response(transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

            data['tranasaction_data'] = TransactionSerializer(transaction_instance).data
        
        return Response(data)

    def destroy(self, request, pk=None, *args, **kwargs):
        transaction_object = Transaction.objects.get(pk=pk)
        # print("TRANSACTION :: ",transaction_object)
        # print("TRANSACTION TYPE :: ",transaction_object.type)

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
                # print("SINGLE TRANACTION :: ", link)
                to_transaction_id = link.to_transaction_id
                # print("TO TRANACTION ID :: ", to_transaction_id)
                # print("LINKED AMOUNT ::", link.linked_amount, "type :: ",type(link.linked_amount))
                to_transaction = Transaction.objects.get(pk=to_transaction_id.id)
                # print("TO TRANACTION :: ", to_transaction)
                to_transaction.recived_or_paid_amount = to_transaction.recived_or_paid_amount - link.linked_amount
                to_transaction.save()
            
            staff_id = transaction_object.staff_id
            # print("STAFF ID :: ",staff_id)
            if staff_id is not None:
                try:
                    balance = Balance.objects.get(staff_id=staff_id)
                    # print("BALANCE :: ",balance)
                except:
                    balance = None
                if balance is not None:
                    balance.amount = balance.amount + transaction_object.total_amount
                    balance.save()

            customer_id = transaction_object.customer_id
            # print("CUSTOMER ID :: ",customer_id)
            if customer_id is not None:
                try:
                    balance = Balance.objects.get(customer_id=customer_id)
                    # print("BALANCE :: ",balance)
                except:
                    balance = None
                if balance is not None:
                    balance.amount = balance.amount + transaction_object.total_amount
                    balance.save()


        if transaction_object.type == 'payment_out':
            # print("PAYMENT IN TYPE")
            linktrasactions = LinkTransaction.objects.filter(from_transaction_id=pk)
            # print("ALL LINKED TRANSACTION :: ", linktrasactions)
            for link in linktrasactions:
                # print("SINGLE TRANACTION :: ", link)
                to_transaction_id = link.to_transaction_id
                # print("TO TRANACTION ID :: ", to_transaction_id)
                # print("LINKED AMOUNT ::", link.linked_amount)               
                to_transaction = Transaction.objects.get(pk=to_transaction_id.id)
                # print("TO TRANACTION :: ", to_transaction)
                to_transaction.recived_or_paid_amount = to_transaction.recived_or_paid_amount - link.linked_amount
                to_transaction.save()
            
            staff_id = transaction_object.staff_id
            # print("STAFF ID :: ",staff_id)
            if staff_id is not None:
                try:
                    balance = Balance.objects.get(staff_id=staff_id)
                    # print("BALANCE :: ",balance)
                except:
                    balance = None
                if balance is not None:
                    balance.amount = balance.amount - transaction_object.total_amount
                    balance.save()

            customer_id = transaction_object.customer_id
            # print("CUSTOMER ID :: ",customer_id)
            if customer_id is not None:
                try:
                    balance = Balance.objects.get(customer_id=customer_id)
                    # print("BALANCE :: ",balance)
                except:
                    balance = None
                if balance is not None:
                    balance.amount = balance.amount - transaction_object.total_amount
                    balance.save()


        if transaction_object.type == 'sale_order':
            # print("SALE ORDER TYPE")
            pass
            

        if transaction_object.type == 'sale':
            # print("SALE TYPE")
            linktrasactions = LinkTransaction.objects.filter(to_transaction_id=pk)
            # print("ALL LINKED TRANSACTION :: ", linktrasactions)
            for link in linktrasactions:
                # print("SINGLE TRANACTION :: ", link)
                from_transaction_id = link.from_transaction_id
                # print("FROM TRANACTION ID :: ", from_transaction_id)
                # print("LINKED AMOUNT ::", link.linked_amount)
                from_transaction = Transaction.objects.get(pk=from_transaction_id.id)
                # print("TO TRANACTION :: ", from_transaction)
                from_transaction.used_amount = from_transaction.used_amount - link.linked_amount
                from_transaction.save()
            
            staff_id = transaction_object.staff_id
            # print("STAFF ID :: ",staff_id)
            if staff_id is not None:
                try:
                    balance = Balance.objects.get(staff_id=staff_id)
                    # print("BALANCE :: ",balance)
                except:
                    balance = None
                if balance is not None:
                    balance.amount = balance.amount - transaction_object.total_amount
                    balance.save()

            customer_id = transaction_object.customer_id
            # print("CUSTOMER ID :: ",customer_id)
            if customer_id is not None:
                try:
                    balance = Balance.objects.get(customer_id=customer_id)
                    # print("BALANCE :: ",balance)
                except:
                    balance = None
                if balance is not None:
                    balance.amount = balance.amount - transaction_object.total_amount
                    balance.save()
        
        
        if transaction_object.type == 'event_sale':
            print("EVENT SALE TYPE")
            linktrasactions = LinkTransaction.objects.filter(to_transaction_id=pk)
            print("ALL LINKED TRANSACTION :: ", linktrasactions)
            for link in linktrasactions:
                print("SINGLE TRANACTION :: ", link)
                from_transaction_id = link.from_transaction_id
                print("FROM TRANACTION ID :: ", from_transaction_id)
                print("LINKED AMOUNT ::", link.linked_amount)
                from_transaction = Transaction.objects.get(pk=from_transaction_id.id)
                print("TO TRANACTION :: ", from_transaction)
                from_transaction.used_amount = from_transaction.used_amount - link.linked_amount
                from_transaction.save()
            
            staff_id = transaction_object.staff_id
            # print("STAFF ID :: ",staff_id)
            if staff_id is not None:
                try:
                    balance = Balance.objects.get(staff_id=staff_id)
                    # print("BALANCE :: ",balance)
                except:
                    balance = None
                if balance is not None:
                    balance.amount = balance.amount - transaction_object.total_amount
                    balance.save()

            customer_id = transaction_object.customer_id
            # print("CUSTOMER ID :: ",customer_id)
            if customer_id is not None:
                try:
                    balance = Balance.objects.get(customer_id=customer_id)
                    # print("BALANCE :: ",balance)
                except:
                    balance = None
                if balance is not None:
                    balance.amount = balance.amount - transaction_object.total_amount
                    balance.save()


        if transaction_object.type == 'purchase_order':
            # print("PURCHASE ORDER TYPE")
            pass
            

        if transaction_object.type == 'purchase':
            # print("PURCHASE TYPE")
            linktrasactions = LinkTransaction.objects.filter(to_transaction_id=pk)
            # print("ALL LINKED TRANSACTION :: ", linktrasactions)
            for link in linktrasactions:
                # print("SINGLE TRANACTION :: ", link)
                from_transaction_id = link.from_transaction_id
                # print("FROM TRANACTION ID :: ", from_transaction_id)
                # print("LINKED AMOUNT ::", link.linked_amount)
                from_transaction = Transaction.objects.get(pk=from_transaction_id.id)
                # print("TO TRANACTION :: ", from_transaction)
                from_transaction.used_amount = from_transaction.used_amount - link.linked_amount
                from_transaction.save()
            
            staff_id = transaction_object.staff_id
            # print("STAFF ID :: ",staff_id)
            if staff_id is not None:
                try:
                    balance = Balance.objects.get(staff_id=staff_id)
                    # print("BALANCE :: ",balance)
                except:
                    balance = None
                if balance is not None:
                    balance.amount = balance.amount + transaction_object.total_amount
                    balance.save()

            customer_id = transaction_object.customer_id
            # print("CUSTOMER ID :: ",customer_id)
            if customer_id is not None:
                try:
                    balance = Balance.objects.get(customer_id=customer_id)
                    # print("BALANCE :: ",balance)
                except:
                    balance = None
                if balance is not None:
                    balance.amount = balance.amount + transaction_object.total_amount
                    balance.save()


        if transaction_object.type == 'event_purchase':
            # print("EVENT PURCHASE TYPE")
            linktrasactions = LinkTransaction.objects.filter(to_transaction_id=pk)
            # print("ALL LINKED TRANSACTION :: ", linktrasactions)
            for link in linktrasactions:
                # print("SINGLE TRANACTION :: ", link)
                from_transaction_id = link.from_transaction_id
                # print("FROM TRANACTION ID :: ", from_transaction_id)
                # print("LINKED AMOUNT ::", link.linked_amount)
                from_transaction = Transaction.objects.get(pk=from_transaction_id.id)
                # print("TO TRANACTION :: ", from_transaction)
                from_transaction.used_amount = from_transaction.used_amount - link.linked_amount
                from_transaction.save()
                
            staff_id = transaction_object.staff_id
            # print("STAFF ID :: ",staff_id)
            if staff_id is not None:
                try:
                    balance = Balance.objects.get(staff_id=staff_id)
                    # print("BALANCE :: ",balance)
                except:
                    balance = None
                if balance is not None:
                    balance.amount = balance.amount + transaction_object.total_amount
                    balance.save()

            customer_id = transaction_object.customer_id
            # print("CUSTOMER ID :: ",customer_id)
            if customer_id is not None:
                try:
                    balance = Balance.objects.get(customer_id=customer_id)
                    # print("BALANCE :: ",balance)
                except:
                    balance = None
                if balance is not None:
                    balance.amount = balance.amount + transaction_object.total_amount
                    balance.save()


        # staff_id = transaction_object.staff_id
        # # print("STAFF ID :: ",staff_id)
        # if staff_id is not None:
        #     try:
        #         balance = Balance.objects.get(staff_id=staff_id)
        #         # print("BALANCE :: ",balance)
        #     except:
        #         balance = None
        #     if balance is not None:
        #         balance.amount = balance.amount - transaction_object.total_amount
        #         balance.save()

        # customer_id = transaction_object.customer_id
        # # print("CUSTOMER ID :: ",customer_id)
        # if customer_id is not None:
        #     try:
        #         balance = Balance.objects.get(customer_id=customer_id)
        #         # print("BALANCE :: ",balance)
        #     except:
        #         balance = None
        #     if balance is not None:
        #         balance.amount = balance.amount - transaction_object.total_amount
        #         balance.save()

        transaction_object.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


### API USED FOR GET TRASACTION AND LINK TRANSACTION ###
@api_view(['POST'])
def TransactionLink(request):
    if request.method == 'POST':
        data = {}
        customer_id = request.data.get('customer_id', None)
        print("Customer ID :: ", customer_id)
        staff_id = request.data.get('staff_id', None)
        print("Staff ID :: ", staff_id)
        transaction_type = request.data.get('transaction_type', None)
        print("TYPE :: ", transaction_type)
        # from_transaction_id = request.data.get('from_transaction_id', None)
        # print("From Transaction ID :: ",from_transaction_id)
        # to_transaction_id = request.data.get('to_transaction_id', None)
        # print("To Transaction ID :: ",to_transaction_id)
        transaction_id = request.data.get('transaction_id', None)
        print("Transaction ID :: ",transaction_id)

        if customer_id is not None:
            if transaction_type is not None:
                transaction = Transaction.objects.filter(
                                                        Q(customer_id=customer_id), 
                                                        Q(type__in=transaction_type)
                                                        )
            else:
                transaction = Transaction.objects.filter(customer_id=customer_id)
                print("transaction ::", transaction)

        if staff_id is not None:
            if transaction_type is not None:
                transaction = Transaction.objects.filter(
                                                        Q(staff_id=staff_id), 
                                                        Q(type__in=transaction_type)
                                                        )
            else:
                transaction = Transaction.objects.filter(staff_id=staff_id)
                print("transaction ::", transaction)
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


@api_view(['POST'])
def ConversationRateReport(request):
    if request.method == 'POST':
        report = {}
        # report['completed'] = 0
        # report['pending'] = 0

        user = request.data.get('user_id')
        # print("USER ::", user)
        start_date = request.data.get('start_date', None)
        # print("START ::", start_date)
        end_date = request.data.get('end_date', None)
        # print("END ::", end_date)

        if start_date is None and end_date is None:
            total = Quotation.objects.filter(user_id=user)
            report['total'] = len(total)

            not_converted = Quotation.objects.filter(user_id=user, is_converted=False)
            report['not_converted'] = len(not_converted)

            converted = Quotation.objects.filter(user_id=user, is_converted=True)
            report['converted'] = len(converted)
            # print("Converted :: ", converted)
            # for i in converted:
            #     if i.payment_status == 'paid':
            #         report['completed'] += 1
            #     else:
            #         report['pending'] += 1
        else:
            total = Quotation.objects.filter(user_id=user, created_on__range=[start_date, end_date])
            report['total'] = len(total)

            not_converted = Quotation.objects.filter(user_id=user, is_converted=False, created_on__range=[start_date, end_date])
            report['not_converted'] = len(not_converted)

            converted = Quotation.objects.filter(user_id=user, is_converted=True, created_on__range=[start_date, end_date])
            report['converted'] = len(converted)
            # print("Converted :: ", converted)
            # for i in converted:
            #     if i.payment_status == 'paid':
            #         report['completed'] += 1
            #     else:
            #         report['pending'] += 1

        return Response(report)
    

@api_view(['POST'])
def InvoiceStatusReport(request):
    if request.method == 'POST':
        report = {}
        report['completed'] = 0
        report['pending'] = 0

        user = request.data.get('user_id')
        # print("USER ::", user)
        start_date = request.data.get('start_date', None)
        # print("START ::", start_date)
        end_date = request.data.get('end_date', None)
        # print("END ::", end_date)

        if start_date is None and end_date is None:
            converted = Quotation.objects.filter(user_id=user, is_converted=True)
            # report['converted'] = len(converted)
            # print("Converted :: ", converted)
            for i in converted:
                if i.payment_status == 'paid':
                    report['completed'] += 1
                else:
                    report['pending'] += 1
        else:
            converted = Quotation.objects.filter(user_id=user, is_converted=True, created_on__range=[start_date, end_date])
            report['converted'] = len(converted)
            # print("Converted :: ", converted)
            for i in converted:
                if i.payment_status == 'paid':
                    report['completed'] += 1
                else:
                    report['pending'] += 1
        
        return Response(report)


@api_view(['POST'])
def MonthylyEarningReport(request):
    if request.method == 'POST':
        data = []
        user = request.data.get('user_id')
        # print("USER ::", user)
        start_date = request.data.get('start_date', None)
        # print("START ::", start_date)
        end_date = request.data.get('end_date', None)
        # print("END ::", end_date)

        if start_date is None and end_date is None:
            result = Transaction.objects.filter(quotation_id__user_id=user).annotate(month=TruncMonth('date')).values('month').annotate(total_amount=Sum('amount')).order_by('month')
            for entry in result:
                data.append({"month": entry['month'].strftime('%B %Y'),
                             "total_amount":entry['total_amount']})
                # print(f"Month: {entry['month'].strftime('%B %Y')}, Total Amount: {entry['total_amount']}")
        else:
            result = Transaction.objects.filter(quotation_id__user_id=user, 
                                                date__range=[start_date, end_date]).annotate(month=TruncMonth('date')).values('month').annotate(total_amount=Sum('amount')).order_by('month')
            for entry in result:
                data.append({"month": entry['month'].strftime('%B %Y'),
                             "total_amount":entry['total_amount']})
                # print(f"Month: {entry['month'].strftime('%B %Y')}, Total Amount: {entry['total_amount']}")
        
        return Response(data)


@api_view(['POST'])
def InvoiceCreationReport(request):
    if request.method == 'POST':
        data = []
        user = request.data.get('user_id')
        # print("USER ::", user)
        start_date = request.data.get('start_date', None)
        # print("START ::", start_date)
        end_date = request.data.get('end_date', None)
        # print("END ::", end_date)
        type = request.data.get('type')
        # print("TYPE ::", type)

        if start_date is None and end_date is None:

            if type == 'per_month':
                result = Quotation.objects.filter(user_id=user, 
                                                   is_converted=True).annotate(month=TruncMonth('converted_on')).values('month').annotate(converted_count=Count('id')).order_by('month')
                
                for entry in result:
                    data.append({"month": entry['month'].strftime('%B %Y'),
                             "converted_count":entry['converted_count']})
                    print(f"Month: {entry['month'].strftime('%B %Y')}, Converted Count: {entry['converted_count']}")
            
            if type == 'per_year':
                result = Quotation.objects.filter(user_id=user,
                                                    is_converted=True).annotate(year=TruncYear('converted_on')).values('year').annotate(converted_count=Count('id')).order_by('year')
                
                for entry in result:
                    data.append({"year": entry['year'].strftime('%Y'),
                             "converted_count":entry['converted_count']})
                    # print(f"Year: {entry['year'].strftime('%Y')}, Converted Count: {entry['converted_count']}")
        else:

            if type == 'per_month':
                result = Quotation.objects.filter(user_id=user,
                                                    is_converted=True, 
                                                    converted_on__range=[start_date, end_date]).annotate(month=TruncMonth('converted_on')).values('month').annotate(converted_count=Count('id')).order_by('month')
                
                for entry in result:
                    data.append({"month": entry['month'].strftime('%B %Y'),
                             "converted_count":entry['converted_count']})
                    # print(f"Month: {entry['month'].strftime('%B %Y')}, Converted Count: {entry['converted_count']}")
            
            if type == 'per_year':
                result = Quotation.objects.filter(user_id=user, 
                                                   is_converted=True, 
                                                   converted_on__range=[start_date, end_date]).annotate(year=TruncYear('converted_on')).values('year').annotate(converted_count=Count('id')).order_by('year')
                
                for entry in result:
                    data.append({"year": entry['year'].strftime('%Y'),
                             "converted_count":entry['converted_count']})
                    # print(f"Year: {entry['year'].strftime('%Y')}, Converted Count: {entry['converted_count']}")

        return Response(data)