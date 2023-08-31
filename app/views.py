from django.shortcuts import render
from django.db.models import Sum, Count, F, Q , Value, CharField
from django.db.models.functions import Concat
from django.contrib.postgres.aggregates import ArrayAgg
from django.http import  HttpResponse
from django.db.models.functions import TruncMonth, TruncYear

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

    def retrieve(self, request, *args, **kwarge):
        instance = self.get_object()
        # print("INSTANCE ::", instance)
        staff_id = instance.id
        # print("STAFF ID ::", staff_id)

        staffskill = StaffSkill.objects.filter(staff_id=staff_id)
        # print("STAFFskill ::", staffskill)

        data = {
            "staff_data" : StaffSerializer(instance).data,
            "staffskill_data" : StaffSkillSerializer(staffskill, many=True).data
        }

        return Response(data)

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
        # 'event_id__id':['exact'],
        'customer_id__full_name':['icontains'],
        # 'event_id__event_name':['icontains'],
        'customer_id__mobile_no':['icontains'],
        # 'start_date':['exact'],
        'due_date':['exact'],
        'invoice_type':['exact'],
        'converted_on':['gt'],
        # 'event_venue':['icontains'],
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

    # def retrieve(self, request, *args, **kwargs):
    #     instance = self.get_object()
    #     # print("INSTANCE :",instance)

    #     data = {}
    #     data['quotation_data'] = QuotationSerializer(instance).data
    #     quotation_id = instance.id
    #     # print("QUOTATION ID :",quotation_id)

    #     datas = []
    #     eventdays = EventDay.objects.filter(quotation_id = instance.id)
    #     # print("EVENT DAY ::",eventdays)
    #     for eventday in eventdays:
    #         eventday_data = {
    #             "event_data": EventDaySerializer(eventday).data,
    #             "event_details": [],
    #             "descriptions": {
    #                 "inventory_details":[],
    #                 "exposure_details":[]
    #             }
    #         }
    #         eventday_id = eventday.id
    #         # print("Event Day ID ::",eventday_id)
    #         eventdetails = EventDetails.objects.filter(quotation_id = instance.id)
    #         # print("Event Detail ::",eventdetails)
    #         eventday_data['event_details'].append(EventDetailsSerializer(eventdetails, many=True).data)
    #         inventorydetails = InventoryDetails.objects.filter(eventday_id = eventday_id)
    #         # print("Inventory Details ::",inventorydetails)
    #         # eventday_data['descriptions']['inventory_details']:{}
    #         eventday_data['descriptions']['inventory_details'].append(InventoryDetailsSerializer(inventorydetails, many=True).data)            
    #         # eventday_data['descriptions']['exposure_details'].append([])
    #         for eventdetail in eventdetails:
    #             eventdetail_id = eventdetail.id
    #             # print("Event Detail ::",eventdetail_id)
    #             exposuredetails = ExposureDetails.objects.filter(eventdetails_id = eventdetail_id)
    #             # print("Exposure Details ::",exposuredetails)
    #             eventday_data['descriptions']['exposure_details'].append(ExposureDetailsSerializer(exposuredetails, many=True).data)

    #         datas.append(eventday_data)
    #     data['datas'] = datas

    #     # data['eventdays_data'] = EventDaySerializer(eventdays, many=True).data
    #     # data['event_details'] = EventDetailsSerializer(eventdetails, many=True).data
    #     # data['inventory_details'] = InventoryDetailsSerializer(inventorydetails, many=True).data
    #     # data['exposure_details'] = ExposureDetailsSerializer(exposuredetails, many=True).data
    #     return Response(data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        data = {
            "quotation_data": QuotationSerializer(instance).data, 
            "datas": []
            }

        eventdays = EventDay.objects.filter(quotation_id=instance.id)
        for eventday in eventdays:
            eventday_data = {
                "event_day": EventDaySerializer(eventday).data,
                "event_details": [],
                "description": []
            }

            eventdetails = EventDetails.objects.filter(eventday_id=eventday.id)
            for eventdetail in eventdetails:
                eventday_data["event_details"].append(EventDetailsSerializer(eventdetail).data)

            inventorydetails = InventoryDetails.objects.filter(eventday_id = eventday.id)
            
            for inventorydetail in inventorydetails:
                exposuredetails = ExposureDetails.objects.filter(inventorydetails_id=inventorydetail.id)
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
        return Response(data)


    def create(self, request, *args, **kwargs):
        quotation =request.data['quotation_data']
        datas = request.data['datas']
        transaction = request.data['transaction_data']
        print("TRANSACTION :::", transaction)

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
            eventdate_data = {
                'event_date': data['event_date'],
                'quotation_id':quotation_instance.id
            }
            eventdaySerializer = EventDaySerializer(data=eventdate_data)
            if eventdaySerializer.is_valid():
                eventday_instance = eventdaySerializer.save()
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
                    'eventday_id':eventday_instance.id
                }

                inventorydetailsSerializer = InventoryDetailsSerializer(data=inventorydetails_data)
                if inventorydetailsSerializer.is_valid():
                    inventorydetails_instance = inventorydetailsSerializer.save()
                    final_inventorydetails_data.append(inventorydetails_instance)
                else:
                    return Response(inventorydetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                inventory = Inventory.objects.get(pk=inventorydetails_data['inventory_id'])
                print("INVENTORY ::", inventory)
                if inventory.type == 'service':

                    ### FOR EXPOSURE DETAILS DATA ###
                    exposuredetails = description['exposure']
                    for exposuredetail in exposuredetails:
                        allocations = exposuredetail['allocation']
                        for allocation in allocations:
                            for single_eventdetails in final_eventdetails_data:
                                event_id = single_eventdetails.event_id.id
                                if event_id == int(allocation):
                                    exposuredetails_data = {
                                        'staff_id':exposuredetail['staff_id'],
                                        'price':exposuredetail['price'],
                                        'eventdetails_id':single_eventdetails.id,
                                        'inventorydetails_id':inventorydetails_instance.id
                                    }
                                    exposuredetailsSerializer = ExposureDetailsSerializer(data=exposuredetails_data)
                                    if exposuredetailsSerializer.is_valid():
                                        exposuredetails_instance = exposuredetailsSerializer.save()
                                        final_exposuredetails_data.append(exposuredetails_instance)
                                    else:
                                        return Response(exposuredetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)                    
                    
                    # print("FINAL Exposure Details DATA :::",final_exposuredetails_data)

        transaction['quotation_id'] = quotation_instance.id
        transactionSerializer = TransactionSerializer(data = transaction)
        if transactionSerializer.is_valid():
            transactionSerializer.save()
        else:
            return Response(transactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response({"quotation_data":QuotationSerializer(quotation_instance).data,
                         "eventday_data":EventDaySerializer(eventday_instance).data,
                         "eventdetails_data":EventDetailsSerializer(final_eventdetails_data, many=True).data,
                         "inventorydetails_data":InventoryDetailsSerializer(final_inventorydetails_data, many=True).data,
                         "exposuredetails_data":ExposureDetailsSerializer(final_exposuredetails_data, many=True).data,
                         "transaction_data":transactionSerializer.data})


    def update(self, request, pk=None, *args, **kwargs):
        quotation_data = request.data.get('quotation_data', None)
        print("Quotation data :", quotation_data)
        datas = request.data.get('datas', None)
        print("Datas :", datas)
        delete_exposures = request.data.get('delete_exposure', None)
        print("Delete Exposure :", delete_exposures)
        delete_inventorys = request.data.get('delete_inventory', None)
        print("Delete Inventory :", delete_inventorys)
        delete_events = request.data.get('delete_event', None)
        print("Delete Event :", delete_events)
        delete_eventdays = request.data.get('delete_eventday', None)
        print("Delete Eventday :", delete_eventdays)
        transaction_data= request.data.get('transaction_data', None)
        print("Transaction Data :", transaction_data)

        print("*************************************************")
        ### FOR UPDATE QUOTATION DATA ###
        quotation = Quotation.objects.get(pk=pk)
        print("Quotation ::", quotation)
        q_serializer = QuotationSerializer(quotation, data=quotation_data, partial=True)
        if q_serializer.is_valid():
            quotation_instance = q_serializer.save()
            print("Quotation Instance saved ::", quotation_instance)
        else:
            return Response(q_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        final_eventdetails_data = []
        final_inventorydetails_data = []
        final_exposuredetails_data = []
        print("*************************************************")
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
                    print(":::: NEW DAY ADDED ::::")
                    eventdate_data.pop('id')
                    print("eventdate_data ::", eventdate_data)
                    n_eventdaySerializer = EventDaySerializer(data=eventdate_data)
                    if n_eventdaySerializer.is_valid():
                        eventday_instance = n_eventdaySerializer.save()
                    else:
                        return Response(n_eventdaySerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    
                    ### FOR ADD EVENT DETAILS DATA ###
                    eventdetails_datas = data['event_details']
                    print("eventdetails_datas ::", eventdetails_datas)
                    for eventdetails_data in eventdetails_datas:
                        eventdetails_data['eventday_id'] = eventday_instance.id
                        eventdetails_data['quotation_id'] = quotation_instance.id
                        print("eventdetails_data ::", eventdetails_data)
                        eventdetailsSerializer = EventDetailsSerializer(data=eventdetails_data)
                        if eventdetailsSerializer.is_valid():
                            eventdetails_instance = eventdetailsSerializer.save()
                            final_eventdetails_data.append(eventdetails_instance)
                        else:
                            return Response(eventdetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    
                    descriptions = data['descriptions']
                    print("descriptions ::", descriptions)
                    for description in descriptions:
                        ### FOR INVENTORY DETAILS DATA ###
                        inventorydetails_data = {
                            'inventory_id':description.pop('inventory_id'),
                            'price':description.pop('price'),
                            'qty':description.pop('qty'),
                            'profit':description.pop('profit'),
                            'eventday_id':eventday_instance.id
                        }
                        print("inventorydetails_data ::", inventorydetails_data)
                        inventorydetailsSerializer = InventoryDetailsSerializer(data=inventorydetails_data)
                        if inventorydetailsSerializer.is_valid():
                            inventorydetails_instance = inventorydetailsSerializer.save()
                            final_inventorydetails_data.append(inventorydetails_instance)
                        else:
                            return Response(inventorydetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

                        ### FOR EXPOSURE DETAILS DATA ###
                        exposuredetails = description['exposure']
                        print("exposuredetails ::", exposuredetails)
                        for exposuredetail in exposuredetails:
                            allocations = exposuredetail['allocation']
                            print("allocations ::", allocations)
                            for allocation in allocations:
                                for single_eventdetails in final_eventdetails_data:
                                    event_id = single_eventdetails.event_id.id
                                    if event_id == int(allocation):
                                        exposuredetails_data = {
                                            'staff_id':exposuredetail['staff_id'],
                                            'price':exposuredetail['price'],
                                            'eventdetails_id':single_eventdetails.id,
                                            'inventorydetails_id':inventorydetails_instance.id
                                        }
                                        print("exposuredetails_data ::", exposuredetails_data)
                                        exposuredetailsSerializer = ExposureDetailsSerializer(data=exposuredetails_data)
                                        if exposuredetailsSerializer.is_valid():
                                            exposuredetails_instance = exposuredetailsSerializer.save()
                                            final_exposuredetails_data.append(exposuredetails_instance)
                                        else:
                                            return Response(exposuredetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                else:
                    print("*************************************************")

                    print(":::: OLD DAY UPDATED ::::")
                    o_eventday = EventDay.objects.get(pk=eventdate_data['id'])
                    print("o_eventday ::::: ",o_eventday)
                    print("eventdate_data ::::: ",eventdate_data)
                    o_eventdaySerializer = EventDaySerializer(o_eventday, data=eventdate_data, partial=True)
                    if o_eventdaySerializer.is_valid():
                        o_eventdaySerializer.save()
                    else:
                        return Response(o_eventdaySerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                            
                    eventdetails_datas = data['event_details']
                    for eventdetails_data in eventdetails_datas:
                        print("Event Details Data :::::",eventdetails_data)

                        if eventdetails_data['id'] == '':
                            print("::: NEW EVENT DETAILS :::")
                            eventdetails_data.pop('id')
                            print("eventdetails_data ::::: ",eventdetails_data)
                            n_eventdetailsSerializer = EventDetailsSerializer(data=eventdetails_data)
                            if n_eventdetailsSerializer.is_valid():
                                eventdetails_instance = n_eventdetailsSerializer.save()
                                final_eventdetails_data.append(eventdetails_instance)
                                print("Event Details Instance saved :::", eventdetails_instance)
                            else:
                                return Response(n_eventdetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                        else:
                            print("::: OLD EVENT DETAILS :::")
                            print("eventdetails_data :::::",eventdetails_data)
                            o_eventdetail = EventDetails.objects.get(pk=eventdetails_data['id'])
                            o_eventdetailsSerializer = EventDetailsSerializer(o_eventdetail, data=eventdetails_data, partial=True)
                            if o_eventdetailsSerializer.is_valid():
                                eventdetails_instance = o_eventdetailsSerializer.save()
                                final_eventdetails_data.append(eventdetails_instance)
                                print("Event Details Instance saved :::::", eventdetails_instance)
                            else:
                                return Response(o_eventdetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                            
                    descriptions = data['descriptions']
                    print("Descriptions :::::", descriptions)

                    for description in descriptions:
                        inventorydetails_data = {
                            'id':description.pop('id'),
                            'inventory_id':description.pop('inventory_id'),
                            'price':description.pop('price'),
                            'qty':description.pop('qty'),
                            'profit':description.pop('profit'),
                            'eventday_id':description.pop('eventday_id')
                        }

                        if inventorydetails_data['id'] == '':
                            print("::: NEW INVENTORY DETAILS :::")
                            inventorydetails_data.pop('id')
                            print("inventorydetails_data :::::",inventorydetails_data)
                            n_inventorydetailsSerializer = InventoryDetailsSerializer(data=inventorydetails_data)
                            if n_inventorydetailsSerializer.is_valid():
                                inventorydetails_instance = n_inventorydetailsSerializer.save()
                                # final_inventorydetails_data.append(inventorydetails_instance)
                                print("Inventory Details Instance saved ::::::", inventorydetails_instance)
                            else:
                                return Response(n_inventorydetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                        else:
                            print("::: OLD INVENTORY DETAILS :::")
                            print("inventorydetails_data ::::: ",inventorydetails_data)
                            o_inventorydetails = InventoryDetails.objects.get(pk=inventorydetails_data['id'])
                            print("o_inventorydetails ::::: ",o_inventorydetails)
                            o_inventorydetailsSerializer = InventoryDetailsSerializer(o_inventorydetails, data=inventorydetails_data, partial=True)
                            if o_inventorydetailsSerializer.is_valid():
                                inventorydetails_instance = o_inventorydetailsSerializer.save()
                                final_inventorydetails_data.append(inventorydetails_instance)
                                # print("Inventory Details Instance saved ::::::", inventorydetails_instance)
                            else:
                                return Response(o_inventorydetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                        
                        exposuredetails = description['exposure']
                        print("exposuredetails ::::: ",exposuredetails)
                        for exposuredetail in exposuredetails:
                            allocations = exposuredetail['allocation']
                            for allocation in allocations:
                                for single_eventdetails in final_eventdetails_data:
                                    event_id = single_eventdetails.event_id.id
                                    if event_id == int(allocation):
                                        exposuredetails_data = {
                                            'id':exposuredetail['id'],
                                            'staff_id':exposuredetail['staff_id'],
                                            'price':exposuredetail['price'],
                                            'eventdetails_id':single_eventdetails.id
                                        }
                                        if exposuredetails_data['id'] == '':
                                            print("::: NEW EXPOSURE DETAILS :::")
                                            print("exposuredetails_data :::::",exposuredetails_data)
                                            n_exposuredetailsSerializer = ExposureDetailsSerializer(data=exposuredetails_data)
                                            if n_exposuredetailsSerializer.is_valid():
                                                exposuredetails_instance = n_exposuredetailsSerializer.save()
                                                final_exposuredetails_data.append(exposuredetails_instance)
                                                # print("Inventory Details Instance saved ::::::::", exposuredetails_instance)
                                            else:
                                                return Response(n_exposuredetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                                        else:
                                            print("::: NEW OLD DETAILS :::")
                                            print("exposuredetails_data ::::: ",exposuredetails_data)
                                            o_exposuredetails = ExposureDetails.objects.get(pk=exposuredetails_data['id'])
                                            print("o_exposuredetails ::::: ",o_exposuredetails)
                                            o_exposuredetailsSerializer = ExposureDetailsSerializer(o_exposuredetails, data=exposuredetails_data, partial=True)
                                            if o_exposuredetailsSerializer.is_valid():
                                                exposuredetails_instance = o_exposuredetailsSerializer.save()
                                                final_exposuredetails_data.append(exposuredetails_instance)
                                                print("Inventory Details Instance saved ::::::::", exposuredetails_instance)
                                            else:
                                                return Response(o_exposuredetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
        

        print("*************************************************")
        ### DELETE EXPOSURES DETAILS ###
        if delete_exposures is not None:
            for delete_exposure in delete_exposures:
                print("Delete Exposure ::", delete_exposure)
                staff_id = delete_exposure['staff_id']
                print("staff_id :::",staff_id)
                eventdetail_id = delete_exposure['eventdetails_id']
                print("eventdetail_id :::",eventdetail_id)
                inventorydetails_id = delete_exposure['inventorydetails_id']
                print("inventorydetails_id :::",inventorydetails_id)

                d_exposure = ExposureDetails.objects.get(staff_id=staff_id, eventdetails_id=eventdetail_id, inventorydetails_id=inventorydetails_id)
                print("d_exposure :::",d_exposure)
                # d_exposure = ExposureDetails.objects.get(pk=delete_exposure)
                # print("Exposure ::", d_exposure)
                d_exposure.delete()

        print("*************************************************")
        ### DELETE INVENTORYS DETAILS ###
        if delete_inventorys is not None:
            for delete_inventory in delete_inventorys:
                print("Delete Inventory ::", delete_inventory)
                d_inventory = InventoryDetails.objects.get(pk=delete_inventory)
                print("Inventory ::", d_inventory)
                d_inventory.delete()
        
        print("*************************************************")
        ### DELETE EVENTS DETAILS ###
        if delete_events is not None:
            for delete_event in delete_events:
                print("Delete Event ::", delete_event)
                d_event = EventDetails.objects.get(pk=delete_event)
                print("EVENT ::", d_event)
                d_event.delete()
        
        print("*************************************************")
        ### DELETE EVENT DAY DETAILS ###
        if delete_eventdays is not None:
            for delete_eventday in delete_eventdays:
                print("Delete Event Day ::", delete_eventday)
                d_eventday = EventDay.objects.get(pk=delete_eventday)
                print("EVENT DAY ::", d_eventday)
                d_eventday.delete()

        print("*************************************************")
        ### UPDATE TRANSACTION DATA ###
        if transaction_data is not None:
            transaction = Transaction.objects.get(pk=transaction_data['id'])
            print("Transaction :::", transaction)
            print("Transaction ID :::", transaction_data['id'])

            t_serializer = TransactionSerializer(transaction, data=transaction_data, partial=True)
            if t_serializer.is_valid():
                t_serializer.save()
            else:
                return Response(t_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # if quotation_data['is_converted'] == True:
        #     quotationSerializer1 = QuotationSerializer(data=quotation)
        #     if quotationSerializer1.is_valid():
        #         quotation_instance1 = quotationSerializer1.save()
        #     else:
        #         return Response(quotationSerializer1.errors, status=status.HTTP_400_BAD_REQUEST)
            
        #     final_eventdetails_data1 = []
        #     final_inventorydetails_data1 = []
        #     final_exposuredetails_data1 = []

        #     for data in datas:
        #         ### FOR ADD EVENT DAY DATA ###
        #         eventdate_data1 = {
        #             'event_date': data['event_date'],
        #             'quotation_id':quotation_instance1.id
        #         }
        #         eventdaySerializer1 = EventDaySerializer(data=eventdate_data1)
        #         if eventdaySerializer1.is_valid():
        #             eventday_instance = eventdaySerializer1.save()
        #         else:
        #             return Response(eventdaySerializer1.errors, status=status.HTTP_400_BAD_REQUEST)
                
        #         ### FOR ADD EVENT DETAILS DATA ###
        #         eventdetails_datas1 = data['event_details']
        #         for eventdetails_data in eventdetails_datas1:
        #             eventdetails_data['eventday_id'] = eventday_instance.id
        #             eventdetails_data['quotation_id'] = quotation_instance.id
        #             eventdetailsSerializer = EventDetailsSerializer(data=eventdetails_data)
        #             if eventdetailsSerializer.is_valid():
        #                 eventdetails_instance = eventdetailsSerializer.save()
        #                 final_eventdetails_data.append(eventdetails_instance)
        #             else:
        #                 return Response(eventdetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        #         descriptions = data['descriptions']
        #         for description in descriptions:
        #             ### FOR INVENTORY DETAILS DATA ###
        #             inventorydetails_data = {
        #                 'inventory_id':description.pop('inventory_id'),
        #                 'price':description.pop('price'),
        #                 'qty':description.pop('qty'),
        #                 'profit':description.pop('profit'),
        #                 'eventday_id':eventday_instance.id
        #             }

        #             inventorydetailsSerializer = InventoryDetailsSerializer(data=inventorydetails_data)
        #             if inventorydetailsSerializer.is_valid():
        #                 inventorydetails_instance = inventorydetailsSerializer.save()
        #                 final_inventorydetails_data.append(inventorydetails_instance)
        #             else:
        #                 return Response(inventorydetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                    
        #             inventory = Inventory.objects.get(pk=inventorydetails_data['inventory_id'])
        #             print("INVENTORY ::", inventory)
        #             if inventory.type == 'service':

        #                 ### FOR EXPOSURE DETAILS DATA ###
        #                 exposuredetails = description['exposure']
        #                 for exposuredetail in exposuredetails:
        #                     allocations = exposuredetail['allocation']
        #                     for allocation in allocations:
        #                         for single_eventdetails in final_eventdetails_data:
        #                             event_id = single_eventdetails.event_id.id
        #                             if event_id == int(allocation):
        #                                 exposuredetails_data = {
        #                                     'staff_id':exposuredetail['staff_id'],
        #                                     'price':exposuredetail['price'],
        #                                     'eventdetails_id':single_eventdetails.id,
        #                                     'inventorydetails_id':inventorydetails_instance.id
        #                                 }
        #                                 exposuredetailsSerializer = ExposureDetailsSerializer(data=exposuredetails_data)
        #                                 if exposuredetailsSerializer.is_valid():
        #                                     exposuredetails_instance = exposuredetailsSerializer.save()
        #                                     final_exposuredetails_data.append(exposuredetails_instance)
        #                                 else:
        #                                     return Response(exposuredetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)                    
                        
        #                 # print("FINAL Exposure Details DATA :::",final_exposuredetails_data)


        return Response({"quotation_data":QuotationSerializer(quotation_instance).data})


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


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all().order_by('-id').distinct()
    serializer_class = TransactionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {
        'quotation_id__user_id__id':['exact'],
        'quotation_id__id':['exact'],
        'customer_id__id':['exact'],
        'notes':['icontains'],
        'quotation_id__customer_id__full_name':['icontains'],
        # 'quotation_id__event_id__event_name':['icontains'],
        'payment_type':['exact'],
        'type':['exact'],
    }

    # def create(self, request, *args, **kwargs):
    #     # print("POST DATA ::", request.data)
    #     data = {}
    #     serializer = self.get_serializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #     self.perform_create(serializer)
    #     data['transaction_data'] = serializer.data

    #     quotation_id = request.data.get('quotation_id', None)
    #     # print("Quotation ID ::", quotation_id)
    #     if quotation_id is not None:
    #         quotation = Quotation.objects.get(id=quotation_id)
    #         # print("Quotation ::", quotation)
    #         total_amount = Transaction.objects.filter(quotation_id=quotation_id).aggregate(Sum('amount'))['amount__sum']
    #         payable_amount = quotation.final_amount - quotation.discount

    #         data['payable_amount'] = payable_amount
    #         data['received_amount'] = total_amount

    #         # print("Final amount :::", quotation.final_amount)
    #         # print("Discount amount :::", quotation.discount)
    #         # print("Total amount :::", total_amount)
    #         # print("Payable amount :::",payable_amount)

    #         if payable_amount == total_amount:
    #             # print("PAID")
    #             quotation.payment_status = 'paid'
    #             quotation.save()
    #         else:
    #             # print("PENDING")
    #             quotation.payment_status = 'pending'
    #             quotation.save()

    #     return Response(data)

    #     # return Response({"transaction_data":serializer.data,
    #     #                  "payable_amount":payable_amount,
    #     #                  "received_amount":total_amount})

    # def update(self, request, pk=None, *args, **kwargs):
    #     # print("POST DATA ::", request.data)
    #     data = {}
    #     transaction = Transaction.objects.get(pk=pk)
    #     # print("DATA ::", transaction)
    #     t_serializer = TransactionSerializer(transaction, data=request.data, partial=True)
    #     if t_serializer.is_valid():
    #         t_serializer.save()
    #         data['transaction_data'] = t_serializer.data
    #     else:
    #         return Response(t_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    #     quotation_id = transaction.quotation_id.id if transaction.quotation_id is not None else None
    #     # print("Quotation ID ::", quotation_id)
    #     if quotation_id is not None:
    #         quotation = Quotation.objects.get(id=quotation_id)
    #         # print("Quotation ::", quotation)
    #         total_amount = Transaction.objects.filter(quotation_id=quotation_id).aggregate(Sum('amount'))['amount__sum']
    #         payable_amount = quotation.final_amount - quotation.discount

    #         data['payable_amount'] = payable_amount
    #         data['received_amount'] = total_amount

    #         # print("Final amount :::", quotation.final_amount)
    #         # print("Discount amount :::", quotation.discount)
    #         # print("Total amount :::", total_amount)
    #         # print("Payable amount :::",payable_amount)

    #         if payable_amount == total_amount:
    #             # print("PAID")
    #             quotation.payment_status = 'paid'
    #             quotation.save()
    #         else:
    #             # print("PENDING")
    #             quotation.payment_status = 'pending'
    #             quotation.save()

    #     return Response(data)

    #     # return Response({"transaction_data":t_serializer.data,
    #     #                  "payable_amount":payable_amount,
    #     #                  "received_amount":total_amount})

    # def destroy(self, request, pk=None, *args, **kwargs):
    #     transaction = Transaction.objects.get(pk=pk)
    #     transaction.delete()
    #     # print("DATA ::", transaction)
        
    #     quotation_id = transaction.quotation_id.id if transaction.quotation_id is not None else None
    #     # print("Quotation ID ::", quotation_id)
    #     if quotation_id is not None:
    #         quotation = Quotation.objects.get(id=quotation_id)
    #         # print("Quotation ::", quotation)
    #         total_amount = Transaction.objects.filter(quotation_id=quotation_id).aggregate(Sum('amount'))['amount__sum']
    #         total_amount = total_amount if total_amount is not None else 0
    #         payable_amount = quotation.final_amount - quotation.discount

    #         # print("Final amount :::", quotation.final_amount)
    #         # print("Discount amount :::", quotation.discount)
    #         # print("Total amount :::", total_amount)
    #         # print("Payable amount :::",payable_amount)

    #         if payable_amount == total_amount:
    #             # print("PAID")
    #             quotation.payment_status = 'paid'
    #             quotation.save()
    #         else:
    #             # print("PENDING")
    #             quotation.payment_status = 'pending'
    #             quotation.save()

    #         return Response({"payable_amount":payable_amount,
    #                         "received_amount":total_amount})
        
    #     return Response(status=status.HTTP_204_NO_CONTENT)
    

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