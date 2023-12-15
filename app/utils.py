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

message = "An error occurred."

### Function for Add Quotation Datas
def add_quotation_data(quotation_id, datas):
    final_evnetday_data = []
    final_inventorydetails_data = []
    final_exposuredetails_data = []

    for data in datas:
        ### FOR ADD EVENT DAY DATA ###
        eventdate_data = {'event_date': data['event_date'],
                        'quotation_id':quotation_id}
        eventdaySerializer = EventDaySerializer(data=eventdate_data)
        if eventdaySerializer.is_valid():
            eventday_instance = eventdaySerializer.save()
            final_evnetday_data.append(eventday_instance)
        else:
            return Response(eventdaySerializer.errors, status=status.HTTP_400_BAD_REQUEST)

        final_eventdetails_data = []
        ### FOR ADD EVENT DETAILS DATA ###
        eventdetails_datas = data['event_details']
        for eventdetails_data in eventdetails_datas:
            eventdetails_data['eventday_id'] = eventday_instance.id
            eventdetails_data['quotation_id'] = quotation_id

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
                        c_final_eventdetails_data = list(final_eventdetails_data)
                        evnetdetials =[]
                        allocations = exposuredetail['allocation']
                        for i in range(len(c_final_eventdetails_data)):
                            single_eventdetails = c_final_eventdetails_data.pop(0)
                            for allocation in allocations:
                                event_id = single_eventdetails.event_id.id
                                if event_id == int(allocation):
                                    evnetdetials.append(single_eventdetails.id)
                        exposuredetails_data = {
                            'staff_id':exposuredetail['staff_id'],
                            'price':exposuredetail['price'],
                            'eventdetails':evnetdetials,
                            'inventorydetails_id':inventorydetails_instance.id
                            }

                        exposuredetailsSerializer = ExposureDetailsSerializer(data=exposuredetails_data)
                        if exposuredetailsSerializer.is_valid():
                            exposuredetails_instance = exposuredetailsSerializer.save()
                            final_exposuredetails_data.append(exposuredetails_instance)
                        else:
                            return Response(exposuredetailsSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

    return final_exposuredetails_data


### Function for Add Inventory Datas for Quotation
def add_inventory_data(quotation_id, datas):
    for data in datas:
        data['quotation_id'] = quotation_id
        inventorySerializer = InventoryDescriptionSerializer(data=data)
        if inventorySerializer.is_valid():
            inventorySerializer.save()
        else:
            return Response(inventorySerializer.errors, status=status.HTTP_400_BAD_REQUEST)


### Function for Add Event Expense Data for Quotation
def add_expense_data(quotation_id, data):
    data['quotation_id'] = quotation_id
    expenseSerializer = EventExpenseSerializer(data=data)
    if expenseSerializer.is_valid():
        expenseSerializer.save()
    else:
        return Response(expenseSerializer.errors, status=status.HTTP_400_BAD_REQUEST)


### Function for Update Quotation Datas
def update_quotation_data(quotation_id, datas):
    final_inventorydetails_data = []
    final_exposuredetails_data = []

    for data in datas:
        ### FOR ADD AND UPDATE EVENT DAY ###
        eventdate_data = {
            'id': data['id'],
            'event_date': data['event_date'],
            'quotation_id':quotation_id}

        if eventdate_data['id'] == '':
            # print(":::: NEW DAY ADDED ::::")
            eventdate_data.pop('id')
            n_eventdaySerializer = EventDaySerializer(data=eventdate_data)
            if n_eventdaySerializer.is_valid():
                eventday_instance = n_eventdaySerializer.save()
            else:
                return Response(n_eventdaySerializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            final_eventdetails_data = []
            ### FOR ADD EVENT DETAILS DATA ###
            eventdetails_datas = data['event_details']
            for eventdetails_data in eventdetails_datas:
                eventdetails_data['eventday_id'] = eventday_instance.id
                eventdetails_data['quotation_id'] = quotation_id
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
                    
            final_eventdetails_data = []
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
                            c_final_eventdetails_data = list(final_eventdetails_data)
                            evnetdetials =[]
                            allocations = exposuredetail['allocation']
                            for i in range(len(c_final_eventdetails_data)):
                                single_eventdetails = c_final_eventdetails_data.pop(0)
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

    return final_exposuredetails_data


### Delete Details for Update Quotations
def delete_details(delete_inventorys=None, delete_events=None, delete_eventdays=None):
    ### DELETE INVENTORYS DETAILS ###
    if delete_inventorys:
        for delete_inventory in delete_inventorys:
            d_inventory = InventoryDetails.objects.get(pk=delete_inventory)
            d_inventory.delete()

    ### DELETE EVENTS DETAILS ###
    if delete_events:
        for delete_event in delete_events:
            d_event = EventDetails.objects.get(pk=delete_event)
            d_event.delete()

    ### DELETE EVENT DAY DETAILS ###
    if delete_eventdays:
        for delete_eventday in delete_eventdays:
            d_eventday = EventDay.objects.get(pk=delete_eventday)
            d_eventday.delete()


### Function for Update Inventory Datas for Quotation
def update_inventory_data(quotation_id, data):
    inventories = data.get("inventories", None)
    delete_inventories = data.get("delete_inventories", None)

    if delete_inventories is not None:
        for delete_inventory in delete_inventories:
            d_inventory = InventoryDescription.objects.get(pk=delete_inventory)
            d_inventory.delete()
    
    if inventories is not None:
        for inventory in inventories:
            if inventory['id'] == '':
                inventory.pop('id')
                inventory["quotation_id"] = quotation_id
                n_inventory = InventoryDescriptionSerializer(data=inventory)
                if n_inventory.is_valid():
                    n_inventory.save()
                else:
                    return Response(n_inventory.errors, status=status.HTTP_400_BAD_REQUEST)
            else:
                get_inventory = InventoryDescription.objects.get(id=inventory['id'])
                o_inventory = InventoryDescriptionSerializer(get_inventory, data=inventory, partial=True)
                if o_inventory.is_valid():
                    o_inventory.save()
                else:
                    return Response(o_inventory.errors, status=status.HTTP_400_BAD_REQUEST)


### Function for Update Event Expense Data for Quotation
def update_expense_data(quotation_id, data):
    expense_id = data.get('id', None)
    item_data = data.get('item_data', None)
    price = data.get('price', None)

    if item_data is None and price is None:
        pass

    if expense_id is None:
        data['quotation_id'] = quotation_id
        expenseSerializer = EventExpenseSerializer(data=data)
        if expenseSerializer.is_valid():
            expenseSerializer.save()
        else:
            return Response(expenseSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
    else:
        eventexpense = EventExpense.objects.get(pk=data['id'])
        if item_data is None and price is None:
            eventexpense.delete()
        else:
            expenseSerializer = EventExpenseSerializer(eventexpense, data=data, partial=True)
            if expenseSerializer.is_valid():
                expenseSerializer.save()
            else:
                return Response(expenseSerializer.errors, status=status.HTTP_400_BAD_REQUEST)


### Function for Add Inventory and Event Expense Data for Quotation
def add_copy(quotation_id, data, eventexpense):
    inventories = data.get("inventories", None)

    if inventories is not None:
        for inventory in inventories:
            inventory.pop('id')
            inventory['quotation_id'] = quotation_id
            inventorySerializer = InventoryDescriptionSerializer(data=inventory)
            if inventorySerializer.is_valid():
                inventorySerializer.save()
            else:
                return Response(inventorySerializer.errors, status=status.HTTP_400_BAD_REQUEST)

    if eventexpense is not None:
        eventexpense['quotation_id'] = quotation_id
        expenseSerializer = EventExpenseSerializer(data=eventexpense)
        if expenseSerializer.is_valid():
            expenseSerializer.save()
        else:
            return Response(expenseSerializer.errors, status=status.HTTP_400_BAD_REQUEST)


### Balance Serializer 
def balance_serializer(balance_data):
    balanceSerializer = BalanceSerializer(data = balance_data)
    if balanceSerializer.is_valid():
        balanceSerializer.save()
    else:
        return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)


### Add Balance Amount for Customer and Staff
def balance_amount(customer_id, staff_id, old_amount, new_amount, type):
    try:
        if customer_id is not None:
            try:
                balance = Balance.objects.get(customer_id=customer_id)
            except:
                balance = None

            if type in ('sale', 'event_sale', 'payment_out'):
                if balance is None:
                    balance_data = {'customer_id': customer_id, 'amount': new_amount}

                    balance_serializer(balance_data)

                    # balanceSerializer = BalanceSerializer(data = balance_data)
                    # if balanceSerializer.is_valid():
                    #     balanceSerializer.save()
                    # else:
                    #     return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

                else:
                    balance.amount = balance.amount + (new_amount - old_amount)
                    balance.save()

            if type in ('purchase', 'event_purchase', 'payment_in'):
                if balance is None:
                    balance_data = {'customer_id': customer_id, 'amount': - new_amount}

                    balance_serializer(balance_data)

                    # balanceSerializer = BalanceSerializer(data = balance_data)
                    # if balanceSerializer.is_valid():
                    #     balanceSerializer.save()
                    # else:
                    #     return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
                    balance_data = {'staff_id': staff_id, 'amount': new_amount}

                    balance_serializer(balance_data)

                    # balanceSerializer = BalanceSerializer(data = balance_data)
                    # if balanceSerializer.is_valid():
                    #     balanceSerializer.save()
                    # else:
                    #     return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

                else:
                    balance.amount = balance.amount + (new_amount - old_amount)
                    balance.save()

            if type in ('purchase', 'event_purchase', 'payment_in'):
                if balance is None:
                    balance_data = {'staff_id': staff_id, 'amount': - new_amount}

                    balance_serializer(balance_data)

                    # balanceSerializer = BalanceSerializer(data = balance_data)
                    # if balanceSerializer.is_valid():
                    #     balanceSerializer.save()
                    # else:
                    #     return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

                else:
                    balance.amount = balance.amount - (new_amount - old_amount)
                    balance.save()
    
    except Exception as e:
        logger.error(f"Function: Balance Amount - An error occurred: {str(e)}.\n Data:(customer_id:{customer_id}, staff_id:{staff_id}, old_amount:{old_amount}, new_amount:{new_amount}, type:{type})", exc_info=True)
        return Response({"error": message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


### Remove Balance Amount for Customer and Staff
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
        return Response({"error": message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


### Get Quotation Data 
def quotation_get(quotation_id):
    try:
        quotation_id = quotation_id
        quotation = Quotation.objects.get(id=quotation_id)

        data = {"quotation_data": QuotationSerializer(quotation).data,
                "datas": []}

        #Get All Events for Quotation
        eventdays = EventDay.objects.filter(quotation_id=quotation.id)
        for eventday in eventdays:
            eventday_data = {
                "event_day": EventDaySerializer(eventday).data,
                "event_details": [],
                "description": []}

            #Get All Event Details for Single Event
            eventdetails = EventDetails.objects.filter(eventday_id=eventday.id)
            for eventdetail in eventdetails:
                eventday_data["event_details"].append(EventDetailsSerializer(eventdetail).data)

            #Get All Inventory Details for Single Event
            inventorydetails = InventoryDetails.objects.filter(eventday_id = eventday.id)
            for inventorydetail in inventorydetails:
                #Get All Exposuer Details for Single Inventory Detail
                exposuredetails = ExposureDetails.objects.filter(inventorydetails_id=inventorydetail.id)

                eventday_data["description"].append({"inventory_details": InventoryDetailsSerializer(inventorydetail).data,
                                                        "exposure_details": ExposureDetailsSerializer(exposuredetails, many=True).data})
                
            data["datas"].append(eventday_data)

        # Get Transaction Details for That Quotation
        transaction_data = Transaction.objects.get(quotation_id=quotation.id)
        data['transaction_data'] = TransactionSerializer(transaction_data).data

        # Get Inventory Details for That Quotation
        inventory = InventoryDescription.objects.filter(quotation_id=quotation.id)
        if len(inventory) != 0:
            data['inventory_datas'] = InventoryDescriptionSerializer(inventory, many=True).data

        # Get Event Expense for That Quotation
        try:
            expense = EventExpense.objects.get(quotation_id=quotation.id)
            data['eventexpense_data'] = EventExpenseSerializer(expense).data
        except:
            pass

        return data
    except Exception as e:
        logger.error(f"Function: Quotation Get - An error occurred: {str(e)}.\n Data:quotation_id:{quotation_id}", exc_info=True)
        return Response({"error": message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


### Convert UTC time to local time
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
        return Response({"error": message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


### Link Transaction
def link_transaction(transaction_id, linktransaction_data, transaction_type=None):
    try:
        new_linktransactions = linktransaction_data.get('new_linktransaction', None)
        update_linktransactions = linktransaction_data.get('update_linktransaction', None)
        delete_linktransactions = linktransaction_data.get('delete_linktransaction', None)

        # Add New Link Transactions
        if new_linktransactions is not None:
            all_linktransaction = []

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

        # Update Link Transactions
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

        # Delete Link Transactions
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
        return Response({"error": message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

### Remove Extra Exposure Data
def remove_exposure(exposure_details):
    try:
        final_exposuredetails_data = ExposureDetailsSerializer(exposure_details, many=True).data
        # print("final_exposuredetails_data :: ",final_exposuredetails_data)

        staff_data = {}

        for item in final_exposuredetails_data:
            staff_id = item['staff_id']
            price = item['price']
            exposuredetails_id = item['id']

            if staff_id not in staff_data:
                staff_data[staff_id] = {
                    'staff_id': staff_id,
                    'price_sum': price,
                    'exposuredetails_ids': [exposuredetails_id],
                }
            else:
                staff_data[staff_id]['price_sum'] += price
                staff_data[staff_id]['exposuredetails_ids'].append(exposuredetails_id)

        result = list(staff_data.values())

        return result
    
    except Exception as e:
        logger.error(f"Function: Remove Exposure - An error occurred: {str(e)}.", exc_info=True)
        return Response({"error": message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


### Delete Link transaction for from transaction data  
def from_transaction_delete(trasaction_id, trasaction_type, customer_id, staff_id):

    linktrasactions = LinkTransaction.objects.filter(from_transaction_id=trasaction_id)
    for link in linktrasactions:
        to_transaction_id = link.to_transaction_id
        new_amount = link.linked_amount
        to_transaction = Transaction.objects.get(pk=to_transaction_id.id)

        if to_transaction.type in ('payment_in', 'payment_out'):
            to_transaction.used_amount = to_transaction.used_amount - link.linked_amount
        else:
            to_transaction.recived_or_paid_amount = to_transaction.recived_or_paid_amount - link.linked_amount
        to_transaction.save()

        balance_delete_amount(customer_id, staff_id, 0 , new_amount, trasaction_type)


### Delete Link transaction for to transaction data 
def to_transaction_delete(trasaction_id, trasaction_type, customer_id, staff_id):

    to_linktrasactions = LinkTransaction.objects.filter(to_transaction_id=trasaction_id)
    for to_link in to_linktrasactions:
        from_transaction_id = to_link.from_transaction_id
        new_amount = to_link.linked_amount
        from_trasaction = Transaction.objects.get(pk=from_transaction_id.id)

        if from_trasaction.type in ('payment_in', 'payment_out'):
            from_trasaction.used_amount = from_trasaction.used_amount - to_link.linked_amount
        else:
            from_trasaction.recived_or_paid_amount = from_trasaction.recived_or_paid_amount - to_link.linked_amount
        from_trasaction.save()

        balance_delete_amount(customer_id, staff_id, 0 , new_amount, trasaction_type)

