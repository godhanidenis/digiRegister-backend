from rest_framework import status
from rest_framework.response import Response

from .serializers import *

from datetime import datetime
import pytz
import logging
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# def quotation_data(quotation_id, datas):
#     final_evnetday_data = []
#     final_eventdetails_data = []
#     final_inventorydetails_data = []
#     final_exposuredetails_data = []

#     for data in datas:
#         ### FOR ADD EVENT DAY DATA ###
#         eventdate_data = {'event_date': data['event_date'],
#                             'quotation_id':quotation_id}
#         eventdaySerializer = EventDaySerializer(data=eventdate_data)
#         if eventdaySerializer.is_valid():
#             eventday_instance = eventdaySerializer.save()
#             final_evnetday_data.append(eventday_instance)
#         else:
#             return Response(eventdaySerializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
#         ### FOR ADD EVENT DETAILS DATA ###
#         eventdetails_datas = data['event_details']
#         for eventdetails_data in eventdetails_datas:
#             eventdetails_data['eventday_id'] = eventday_instance.id
#             eventdetails_data['quotation_id'] = quotation_id

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
#                 'eventday_id':eventday_instance.id}
            
#             inventorydetailsSerializer = InventoryDetailsSerializer(data=inventorydetails_data)
#             if inventorydetailsSerializer.is_valid():
#                 inventorydetails_instance = inventorydetailsSerializer.save()
#                 final_inventorydetails_data.append(inventorydetails_instance)
#             else:
#                 return Response(inventorydetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
#             inventory = Inventory.objects.get(pk=inventorydetails_data['inventory_id'])
#             if inventory.type == 'service':
#                 ### FOR EXPOSURE DETAILS DATA ###
#                 exposuredetails = description.get('exposure', None)
#                 if exposuredetails is not None:
#                     for exposuredetail in exposuredetails:
#                         evnetdetials =[]
#                         allocations = exposuredetail['allocation']
#                         for allocation in allocations:
#                             for single_eventdetails in final_eventdetails_data:
#                                 event_id = single_eventdetails.event_id.id
#                                 if event_id == int(allocation):
#                                     evnetdetials.append(single_eventdetails.id)

#                         exposuredetails_data = {
#                             'staff_id':exposuredetail['staff_id'],
#                             'price':exposuredetail['price'],
#                             'eventdetails':evnetdetials,
#                             'inventorydetails_id':inventorydetails_instance.id}
                        
#                         exposuredetailsSerializer = ExposureDetailsSerializer(data=exposuredetails_data)
#                         if exposuredetailsSerializer.is_valid():
#                             exposuredetails_instance = exposuredetailsSerializer.save()
#                             final_exposuredetails_data.append(exposuredetails_instance)
#                         else:
#                             return Response(exposuredetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

#     return Response({"final_evnetday_data" : final_evnetday_data,
#                      "final_eventdetails_data" : final_eventdetails_data,
#                      "final_inventorydetails_data" : final_inventorydetails_data,
#                      "final_exposuredetails_data" : final_exposuredetails_data})



def balance_amount(customer_id, staff_id, old_amount, new_amount, type):
    try:
        if customer_id is not None:
            try:
                balance = Balance.objects.get(customer_id=customer_id)
            except:
                balance = None

            if type in ('sale', 'event_sale', 'payment_out'):
                if balance is None:
                    balance_data = {'customer_id': customer_id,
                                    'amount': new_amount}
                    balanceSerializer = BalanceSerializer(data = balance_data)
                    if balanceSerializer.is_valid():
                        balanceSerializer.save()
                    else:
                        return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                else:
                    balance.amount = balance.amount + (new_amount - old_amount)
                    balance.save()

            if type in ('purchase', 'event_purchase', 'payment_in'):
                if balance is None:
                    balance_data = {'customer_id': customer_id,
                                    'amount': - new_amount}
                    balanceSerializer = BalanceSerializer(data = balance_data)
                    if balanceSerializer.is_valid():
                        balanceSerializer.save()
                    else:
                        return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                else:
                    balance.amount = balance.amount - (new_amount - old_amount)
                    balance.save()

        if staff_id is not None:
            try:
                balance = Balance.objects.get(staff_id=staff_id)
            except:
                balance = None

            if type in ('sale', 'event_sale', 'payment_out'):
                if balance is None:
                    balance_data = {'staff_id': staff_id,
                                    'amount': new_amount}
                    balanceSerializer = BalanceSerializer(data = balance_data)
                    if balanceSerializer.is_valid():
                        balanceSerializer.save()
                    else:
                        return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                else:
                    balance.amount = balance.amount + (new_amount - old_amount)
                    balance.save()

            if type in ('purchase', 'event_purchase', 'payment_in'):
                if balance is None:
                    balance_data = {'staff_id': staff_id,
                                    'amount': - new_amount}
                    balanceSerializer = BalanceSerializer(data = balance_data)
                    if balanceSerializer.is_valid():
                        balanceSerializer.save()
                    else:
                        return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                else:
                    balance.amount = balance.amount - (new_amount - old_amount)
                    balance.save()
    except Exception as e:
        logger.error(f"Function: Balance Amount - An error occurred: {str(e)}.\n Data:(customer_id:{customer_id}, staff_id:{staff_id}, old_amount:{old_amount}, new_amount:{new_amount}, type:{type})", exc_info=True)

        return Response()


def balance_delete_amount(customer_id, staff_id, old_amount, new_amount, type):
    try:
        if customer_id is not None:
            try:
                balance = Balance.objects.get(customer_id=customer_id)
            except:
                balance = None

            if type in ('sale', 'event_sale', 'payment_out'):
                if balance is not None:
                    balance.amount = balance.amount - (new_amount - old_amount)
                    balance.save()

            if type in ('purchase', 'event_purchase', 'payment_in'):
                if balance is not None:
                    balance.amount = balance.amount + (new_amount - old_amount)
                    balance.save()

        if staff_id is not None:
            try:
                balance = Balance.objects.get(staff_id=staff_id)
            except:
                balance = None

            if type in ('sale', 'event_sale', 'payment_out'):
                if balance is not None:
                    balance.amount = balance.amount - (new_amount - old_amount)
                    balance.save()

            if type in ('purchase', 'event_purchase', 'payment_in'):
                if balance is not None:
                    balance.amount = balance.amount + (new_amount - old_amount)
                    balance.save()
    except Exception as e:
        logger.error(f"Function: Balance Delete Amount - An error occurred: {str(e)}.\n Data:(customer_id:{customer_id}, staff_id:{staff_id}, old_amount:{old_amount}, new_amount:{new_amount}, type:{type})", exc_info=True)

        return Response()


def quotation_get(quotation_id):
    try:
        quotation_id = quotation_id
        quotation = Quotation.objects.get(id=quotation_id)

        data = {"quotation_data": QuotationSerializer(quotation).data,
                "datas": []}

        eventdays = EventDay.objects.filter(quotation_id=quotation.id)
        for eventday in eventdays:
            eventday_data = {
                "event_day": EventDaySerializer(eventday).data,
                "event_details": [],
                "description": []}

            eventdetails = EventDetails.objects.filter(eventday_id=eventday.id)
            for eventdetail in eventdetails:
                eventday_data["event_details"].append(EventDetailsSerializer(eventdetail).data)

            inventorydetails = InventoryDetails.objects.filter(eventday_id = eventday.id)
            
            for inventorydetail in inventorydetails:
                exposuredetails = ExposureDetails.objects.filter(inventorydetails_id=inventorydetail.id)

                eventday_data["description"].append({"inventory_details": InventoryDetailsSerializer(inventorydetail).data,
                                                        "exposure_details": ExposureDetailsSerializer(exposuredetails, many=True).data})
                
            data["datas"].append(eventday_data)

        transaction_data = Transaction.objects.get(quotation_id=quotation.id)
        data['transaction_data'] = TransactionSerializer(transaction_data).data

        return data
    except Exception as e:
        logger.error(f"Function: Quotation Get - An error occurred: {str(e)}.\n Data:quotation_id:{quotation_id}", exc_info=True)

        return Response()


def convert_time_utc_to_local(timezone, data):
    try:
        if data is not None:
            utc_datetime = datetime.strptime(data, "%Y-%m-%dT%H:%M:%SZ")
            target_timezone = pytz.timezone(timezone)
            converted_time = utc_datetime.replace(tzinfo=pytz.utc).astimezone(target_timezone)
            final_time = converted_time.strftime("%Y-%m-%dT%H:%M:%SZ")

            return final_time
    except Exception as e:
        logger.error(f"Function: Convert Time UTC To Local - An error occurred: {str(e)}.\n Data:(timezone:{timezone}, data:{data})", exc_info=True)

        return Response()


def link_transaction(transaction_id, linktransaction_data, transaction_type=None):
    try:
        new_linktransactions = linktransaction_data.get('new_linktransaction', None)
        update_linktransactions = linktransaction_data.get('update_linktransaction', None)
        delete_linktransactions = linktransaction_data.get('delete_linktransaction', None)

        if new_linktransactions is not None:
            all_linktransaction = []
            # print("*** --- ADD LINK TRANSACTION --- ***")
            for new_single in new_linktransactions:
                new_single['from_transaction_id'] = transaction_id
                linktransactionSerializer = LinkTransactionSerializer(data=new_single)
                if linktransactionSerializer.is_valid():
                    linktransaction_instance = linktransactionSerializer.save()
                    all_linktransaction.append(linktransaction_instance)
                else:
                    return Response(linktransactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
            for linktransaction in all_linktransaction:
                from_transaction = Transaction.objects.get(id=linktransaction.from_transaction_id.id)
                transaction = Transaction.objects.get(id = linktransaction.to_transaction_id.id)

                to_customer_id = transaction.customer_id.id if transaction.customer_id is not None else None
                to_staff_id = transaction.staff_id.id if transaction.staff_id is not None else None

                if transaction.type in ('payment_in', 'payment_out'):
                    to_old_amount = transaction.total_amount - transaction.used_amount
                else:
                    to_old_amount = transaction.total_amount - transaction.recived_or_paid_amount

                if from_transaction.type in ('payment_in' , 'event_purchase' , 'purchase'):
                    
                    if transaction.type in ('event_sale', 'sale'):
                        transaction.recived_or_paid_amount = transaction.recived_or_paid_amount + linktransaction.linked_amount
                        transaction.save()

                        to_new_amount = transaction.total_amount - transaction.recived_or_paid_amount
                        balance_amount(to_customer_id, to_staff_id, to_old_amount, to_new_amount, transaction.type)

                    elif transaction.type == 'payment_out':
                        transaction.used_amount = transaction.used_amount + linktransaction.linked_amount
                        transaction.save()

                        to_new_amount = transaction.total_amount - transaction.used_amount
                        balance_amount(to_customer_id, to_staff_id, to_old_amount, to_new_amount, transaction.type)
                
                elif from_transaction.type in ('payment_out', 'event_sale', 'sale'):

                    if transaction.type in ('event_purchase', 'purchase'):
                        transaction.recived_or_paid_amount = transaction.recived_or_paid_amount + linktransaction.linked_amount
                        transaction.save()

                        to_new_amount = transaction.total_amount - transaction.recived_or_paid_amount
                        balance_amount(to_customer_id, to_staff_id, to_old_amount, to_new_amount, transaction.type)

                    elif transaction.type == 'payment_in':
                        transaction.used_amount = transaction.used_amount + linktransaction.linked_amount
                        transaction.save()

                        to_new_amount = transaction.total_amount - transaction.used_amount
                        balance_amount(to_customer_id, to_staff_id, to_old_amount, to_new_amount, transaction.type)

        if update_linktransactions is not None:
            all_linktransaction = []

            for single_update in update_linktransactions:
                u_linktransaction = LinkTransaction.objects.get(pk=single_update['id'])
                old_linkedamount = u_linktransaction.linked_amount

                linktransactionSerializer = LinkTransactionSerializer(u_linktransaction, data=single_update, partial=True)
                if linktransactionSerializer.is_valid():
                    linktransaction_instance = linktransactionSerializer.save()
                    all_linktransaction.append(linktransaction_instance)
                else:
                    return Response(linktransactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

                new_linkedamount = linktransaction_instance.linked_amount

                from_transaction = Transaction.objects.get(id=linktransaction_instance.from_transaction_id.id)

                from_customer_id = from_transaction.customer_id.id if from_transaction.customer_id is not None else None
                from_staff_id = from_transaction.staff_id.id if from_transaction.staff_id is not None else None
                from_type = from_transaction.type

                if from_transaction.type in ('payment_in', 'payment_out'):
                    from_old_amount = from_transaction.total_amount - from_transaction.used_amount
                else:
                    from_old_amount = from_transaction.total_amount - from_transaction.recived_or_paid_amount


                to_transaction = Transaction.objects.get(id=linktransaction_instance.to_transaction_id.id)

                to_customer_id = to_transaction.customer_id.id if to_transaction.customer_id is not None else None
                to_staff_id = to_transaction.staff_id.id if to_transaction.staff_id is not None else None
                to_type = to_transaction.type
                
                if to_transaction.type in ('payment_in', 'payment_out'):
                    to_old_amount = to_transaction.total_amount - to_transaction.used_amount
                else:
                    to_old_amount = to_transaction.total_amount - to_transaction.recived_or_paid_amount

                if transaction_type in ('event_sale', 'sale', 'payment_out'):

                    if from_type in ('event_sale', 'sale', 'payment_out'):
                        if to_type in ('purchase', 'event_purchase'):
                            to_transaction.recived_or_paid_amount = (to_transaction.recived_or_paid_amount - old_linkedamount) + new_linkedamount
                            to_transaction.save()

                            to_new_amount = to_transaction.total_amount - to_transaction.recived_or_paid_amount
                            balance_amount(to_customer_id, to_staff_id, to_old_amount, to_new_amount, to_transaction.type)
                        else:
                            to_transaction.used_amount = (to_transaction.used_amount - old_linkedamount) + new_linkedamount
                            to_transaction.save()

                            to_new_amount = to_transaction.total_amount - to_transaction.used_amount
                            balance_amount(to_customer_id, to_staff_id, to_old_amount, to_new_amount, to_transaction.type)

                    elif to_type in ('event_sale', 'sale', 'payment_out'):
                        if from_type in ('purchase', 'event_purchase'):
                            from_transaction.recived_or_paid_amount = (from_transaction.recived_or_paid_amount - old_linkedamount) + new_linkedamount
                            from_transaction.save()

                            from_new_amount = from_transaction.total_amount - from_transaction.used_amount
                            balance_amount(from_customer_id, from_staff_id, from_old_amount, from_new_amount, from_transaction.type)
                        else:
                            from_transaction.used_amount = (from_transaction.used_amount - old_linkedamount) + new_linkedamount
                            from_transaction.save()

                            from_new_amount = from_transaction.total_amount - from_transaction.used_amount
                            balance_amount(from_customer_id, from_staff_id, from_old_amount, from_new_amount, from_transaction.type)

                elif transaction_type in ('payment_in' , 'event_purchase' , 'purchase'):

                    if from_type in ('payment_in' , 'event_purchase' , 'purchase'):
                        if to_type in ('sale', 'event_sale'):
                            to_transaction.recived_or_paid_amount = (to_transaction.recived_or_paid_amount - old_linkedamount) + new_linkedamount
                            to_transaction.save()

                            to_new_amount = to_transaction.total_amount - to_transaction.recived_or_paid_amount
                            balance_amount(to_customer_id, to_staff_id, to_old_amount, to_new_amount, to_transaction.type)
                        else:
                            to_transaction.used_amount = (to_transaction.used_amount - old_linkedamount) + new_linkedamount
                            to_transaction.save()

                            to_new_amount = to_transaction.total_amount - to_transaction.used_amount
                            balance_amount(to_customer_id, to_staff_id, to_old_amount, to_new_amount, to_transaction.type)

                    elif to_type in ('payment_in' , 'event_purchase' , 'purchase'):
                        if from_type in ('sale', 'event_sale'):
                            from_transaction.recived_or_paid_amount = (from_transaction.recived_or_paid_amount - old_linkedamount) + new_linkedamount
                            from_transaction.save()

                            from_new_amount = from_transaction.total_amount - from_transaction.used_amount
                            balance_amount(from_customer_id, from_staff_id, from_old_amount, from_new_amount, from_transaction.type)
                        else:
                            from_transaction.used_amount = (from_transaction.used_amount - old_linkedamount) + new_linkedamount
                            from_transaction.save()

                            from_new_amount = from_transaction.total_amount - from_transaction.used_amount
                            balance_amount(from_customer_id, from_staff_id, from_old_amount, from_new_amount, from_transaction.type)

        if delete_linktransactions is not None:
            for single_delete in delete_linktransactions:
                d_linktransaction = LinkTransaction.objects.get(pk = single_delete)

                from_transaction = Transaction.objects.get(id=d_linktransaction.from_transaction_id.id)

                from_customer_id = from_transaction.customer_id.id if from_transaction.customer_id is not None else None
                from_staff_id = from_transaction.staff_id.id if from_transaction.staff_id is not None else None
                from_type = from_transaction.type

                if from_transaction.type in ('payment_in', 'payment_out'):
                    from_old_amount = from_transaction.total_amount - from_transaction.used_amount
                else:
                    from_old_amount = from_transaction.total_amount - from_transaction.recived_or_paid_amount

                to_transaction = Transaction.objects.get(id=d_linktransaction.to_transaction_id.id)

                to_customer_id = to_transaction.customer_id.id if to_transaction.customer_id is not None else None
                to_staff_id = to_transaction.staff_id.id if to_transaction.staff_id is not None else None
                to_type = to_transaction.type
                
                if to_transaction.type in ('payment_in', 'payment_out'):
                    to_old_amount = to_transaction.total_amount - to_transaction.used_amount
                else:
                    to_old_amount = to_transaction.total_amount - to_transaction.recived_or_paid_amount

                if transaction_type in ('event_sale', 'sale', 'payment_out'):

                    if from_type in ('event_sale', 'sale', 'payment_out'):
                        if to_type in ('purchase', 'event_purchase'):
                            to_transaction.recived_or_paid_amount = to_transaction.recived_or_paid_amount - d_linktransaction.linked_amount
                            to_transaction.save()

                            to_new_amount = to_transaction.total_amount - to_transaction.recived_or_paid_amount
                            balance_amount(to_customer_id, to_staff_id, to_old_amount, to_new_amount, to_transaction.type)
                        else:
                            to_transaction.used_amount = to_transaction.used_amount - d_linktransaction.linked_amount
                            to_transaction.save()

                            to_new_amount = to_transaction.total_amount - to_transaction.used_amount
                            balance_amount(to_customer_id, to_staff_id, to_old_amount, to_new_amount, to_transaction.type)

                    elif to_type in ('event_sale', 'sale', 'payment_out'):
                        if from_type in ('purchase', 'event_purchase'):
                            from_transaction.recived_or_paid_amount = from_transaction.recived_or_paid_amount - d_linktransaction.linked_amount
                            from_transaction.save()

                            from_new_amount = from_transaction.total_amount - from_transaction.recived_or_paid_amount
                            balance_amount(from_customer_id, from_staff_id, from_old_amount, from_new_amount, from_transaction.type)
                        else:
                            from_transaction.used_amount = from_transaction.used_amount - d_linktransaction.linked_amount
                            from_transaction.save()

                            from_new_amount = from_transaction.total_amount - from_transaction.used_amount
                            balance_amount(from_customer_id, from_staff_id, from_old_amount, from_new_amount, from_transaction.type)

                elif transaction_type in ('payment_in' , 'event_purchase' , 'purchase'):

                    if from_type in ('payment_in' , 'event_purchase' , 'purchase'):
                        if to_type in ('sale', 'event_sale'):
                            to_transaction.recived_or_paid_amount = to_transaction.recived_or_paid_amount - d_linktransaction.linked_amount
                            to_transaction.save()

                            to_new_amount = to_transaction.total_amount - to_transaction.recived_or_paid_amount
                            balance_amount(to_customer_id, to_staff_id, to_old_amount, to_new_amount, to_transaction.type)
                        else:
                            to_transaction.used_amount = to_transaction.used_amount - d_linktransaction.linked_amount
                            to_transaction.save()

                            to_new_amount = to_transaction.total_amount - to_transaction.used_amount
                            balance_amount(to_customer_id, to_staff_id, to_old_amount, to_new_amount, to_transaction.type)

                    elif to_type in ('payment_in' , 'event_purchase' , 'purchase'):
                        if from_type in ('sale', 'event_sale'):
                            from_transaction.recived_or_paid_amount = from_transaction.recived_or_paid_amount - d_linktransaction.linked_amount
                            from_transaction.save()

                            from_new_amount = from_transaction.total_amount - from_transaction.recived_or_paid_amount
                            balance_amount(from_customer_id, from_staff_id, from_old_amount, from_new_amount, from_transaction.type)
                        else:
                            from_transaction.used_amount = from_transaction.used_amount - d_linktransaction.linked_amount
                            from_transaction.save()

                            from_new_amount = from_transaction.total_amount - from_transaction.used_amount
                            balance_amount(from_customer_id, from_staff_id, from_old_amount, from_new_amount, from_transaction.type)


                d_linktransaction.delete()
    except Exception as e:
        logger.error(f"Function: Link Transaction - An error occurred: {str(e)}.\n Data:(transaction_id:{transaction_id}, linktransaction_data:{linktransaction_data}, transaction_type:{transaction_type})", exc_info=True)

        return Response()
