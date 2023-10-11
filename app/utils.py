from rest_framework import status
from rest_framework.response import Response

from .serializers import *

from datetime import datetime
import pytz

def balance_amount(customer_id, staff_id, old_amount, new_amount, type):
    # print("customer_id :: ",customer_id)
    # print("staff_id :: ",staff_id)
    # print("old_amount :: ",old_amount)
    # print("new_amount :: ",new_amount)
    # print("type :: ",type)

    if customer_id is not None:
        try:
            balance = Balance.objects.get(customer_id=customer_id)
        except:
            balance = None

        if type in ('sale', 'event_sale', 'payment_out'):
            if balance is None:
                balance_data = {'customer_id': customer_id,
                                'amount': new_amount}
                # print("Balance DATA ::: ", balance_data)
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
                # print("Balance DATA ::: ", balance_data)
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
                # print("Balance DATA ::: ", balance_data)
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
                # print("Balance DATA ::: ", balance_data)
                balanceSerializer = BalanceSerializer(data = balance_data)
                if balanceSerializer.is_valid():
                    balanceSerializer.save()
                else:
                    return Response(balanceSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
            else:
                balance.amount = balance.amount - (new_amount - old_amount)
                balance.save()



def balance_delete_amount(customer_id, staff_id, old_amount, new_amount, type):
    # print("customer_id :: ",customer_id)
    # print("staff_id :: ",staff_id)
    # print("old_amount :: ",old_amount)
    # print("new_amount :: ",new_amount)
    # print("type :: ",type)

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



def quotation_get(quotation_id):
    quotation_id = quotation_id
    # print("Quotation ID :: ",quotation_id)
    quotation = Quotation.objects.get(id=quotation_id)
    # print("Quotation :: ",quotation)

    data = {"quotation_data": QuotationSerializer(quotation).data,
             "datas": []}

    eventdays = EventDay.objects.filter(quotation_id=quotation.id)
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
            # print("exposuredetails :: ",exposuredetails)
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

            eventday_data["description"].append({"inventory_details": InventoryDetailsSerializer(inventorydetail).data,
                                                    "exposure_details": ExposureDetailsSerializer(exposuredetails, many=True).data})
            
        data["datas"].append(eventday_data)

    transaction_data = Transaction.objects.get(quotation_id=quotation.id)
    # print("Transaction data :: ", transaction_data)
    data['transaction_data'] = TransactionSerializer(transaction_data).data

    # print(data)
    return data



def convert_time_utc_to_local(timezone, data):
    if data is not None:
        utc_datetime = datetime.strptime(data, "%Y-%m-%dT%H:%M:%SZ")
        target_timezone = pytz.timezone(timezone)
        converted_time = utc_datetime.replace(tzinfo=pytz.utc).astimezone(target_timezone)
        final_time = converted_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        return final_time



def link_transaction(transaction_id, linktransaction_data, transaction_type=None):
    # print("Transaction ID ::", transaction_id)
    # print("Link Transaction Data ::", linktransaction_data)
    new_linktransactions = linktransaction_data.get('new_linktransaction', None)
    # print("new_linktransaction ::", new_linktransactions)
    update_linktransactions = linktransaction_data.get('update_linktransaction', None)
    # print("update_linktransaction ::", update_linktransactions)
    delete_linktransactions = linktransaction_data.get('delete_linktransaction', None)
    # print("delete_linktransaction ::", delete_linktransactions)

    # print("len(new_linktransactions) :::::", len(new_linktransactions))
    if new_linktransactions is not None:
        all_linktransaction = []
        # print("*** --- ADD LINK TRANSACTION --- ***")
        for new_single in new_linktransactions:
            new_single['from_transaction_id'] = transaction_id
            # print("new_single :: ", new_single)
            linktransactionSerializer = LinkTransactionSerializer(data=new_single)
            if linktransactionSerializer.is_valid():
                linktransaction_instance = linktransactionSerializer.save()
                all_linktransaction.append(linktransaction_instance)
            else:
                return Response(linktransactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        for linktransaction in all_linktransaction:
            print("Single transaction :: ", linktransaction)
            print("FROM TRANSACTION ID :: ", linktransaction.from_transaction_id.id)
            print("TO TRANSACTION ID :: ",linktransaction.to_transaction_id.id)
            print("AMOUNT :: ", linktransaction.linked_amount, "TYPE :: ", type(linktransaction.linked_amount))

            from_transaction = Transaction.objects.get(id=linktransaction.from_transaction_id.id)
            print("From Transaction :: ", from_transaction)
            print("From Transaction Type :: ", from_transaction.type)
            
            transaction = Transaction.objects.get(id = linktransaction.to_transaction_id.id)
            print("Transaction :: ", transaction)
            print("Transaction Type :: ", transaction.type)

            to_customer_id = transaction.customer_id.id if transaction.customer_id is not None else None
            # print("to_customer_id :::",to_customer_id)
            to_staff_id = transaction.staff_id.id if transaction.staff_id is not None else None
            # print("to_staff_id :::",to_staff_id)

            if transaction.type in ('payment_in', 'payment_out'):
                to_old_amount = transaction.total_amount - transaction.used_amount
            else:
                to_old_amount = transaction.total_amount - transaction.recived_or_paid_amount

            if from_transaction.type in ('payment_in' , 'event_purchase' , 'purchase'):
                
                if transaction.type in ('event_sale', 'sale'):
                    # print("RESCIVED AMOUNT :: ", transaction.recived_or_paid_amount, "TYPE :: ", type(transaction.recived_or_paid_amount))
                    # print("AMOUNT :: ", linktransaction.linked_amount, "TYPE :: ", type(linktransaction.linked_amount))
                    transaction.recived_or_paid_amount = transaction.recived_or_paid_amount + linktransaction.linked_amount
                    # print("transaction.recived_or_paid_amount ::: ", transaction.recived_or_paid_amount)
                    transaction.save()

                    to_new_amount = transaction.total_amount - transaction.recived_or_paid_amount
                    print("to_new_amount ::: ", to_new_amount)
                    balance_amount(to_customer_id, to_staff_id, to_old_amount, to_new_amount, transaction.type)

                elif transaction.type == 'payment_out':
                    # print("RESCIVED AMOUNT :: ", transaction.used_amount, "TYPE :: ", type(transaction.used_amount))
                    # print("AMOUNT :: ", linktransaction.linked_amount, "TYPE :: ", type(linktransaction.linked_amount))
                    transaction.used_amount = transaction.used_amount + linktransaction.linked_amount
                    # print("transaction.used_amount ::: ",transaction.used_amount)
                    transaction.save()

                    to_new_amount = transaction.total_amount - transaction.used_amount
                    print("to_new_amount ::: ", to_new_amount)
                    balance_amount(to_customer_id, to_staff_id, to_old_amount, to_new_amount, transaction.type)
            
            elif from_transaction.type in ('payment_out', 'event_sale', 'sale'):

                if transaction.type in ('event_purchase', 'purchase'):
                    # print("RESCIVED AMOUNT :: ", transaction.recived_or_paid_amount, "TYPE :: ", type(transaction.recived_or_paid_amount))
                    # print("AMOUNT :: ", linktransaction.linked_amount, "TYPE :: ", type(linktransaction.linked_amount))
                    transaction.recived_or_paid_amount = transaction.recived_or_paid_amount + linktransaction.linked_amount
                    # print("transaction.recived_or_paid_amount ::: ", transaction.recived_or_paid_amount)                    
                    transaction.save()

                    to_new_amount = transaction.total_amount - transaction.recived_or_paid_amount
                    print("to_new_amount ::: ", to_new_amount)
                    balance_amount(to_customer_id, to_staff_id, to_old_amount, to_new_amount, transaction.type)

                elif transaction.type == 'payment_in':
                    # print("RESCIVED AMOUNT :: ", transaction.used_amount, "TYPE :: ", type(transaction.used_amount))
                    # print("AMOUNT :: ", linktransaction.linked_amount, "TYPE :: ", type(linktransaction.linked_amount))
                    transaction.used_amount = transaction.used_amount + linktransaction.linked_amount
                    # print("transaction.used_amount ::: ",transaction.used_amount)
                    transaction.save()

                    to_new_amount = transaction.total_amount - transaction.used_amount
                    print("to_new_amount ::: ", to_new_amount)
                    balance_amount(to_customer_id, to_staff_id, to_old_amount, to_new_amount, transaction.type)

    if update_linktransactions is not None:
        all_linktransaction = []
        # print("*** --- UPDATE LINK TRANSACTION --- ***")
        for update_single in update_linktransactions:
            # print("update_single :: ", update_single)
            link = LinkTransaction.objects.get(pk=update_single['id'])
            # print("LINK TRANSACTION :: ", link)
            old_amount = link.linked_amount
            # print("OLD AMOUNT :: ", old_amount)

            linktransactionSerializer = LinkTransactionSerializer(link, data=update_single, partial=True)
            if linktransactionSerializer.is_valid():
                linktransaction_instance = linktransactionSerializer.save()
                # print("linktransaction_instance ::: ",linktransaction_instance)
                all_linktransaction.append(linktransaction_instance)
            else:
                return Response(linktransactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

            new_amount = linktransaction_instance.linked_amount
            # print("NEW AMOUNT :: ",new_amount)

            from_transaction = Transaction.objects.get(id = linktransaction_instance.from_transaction_id.id)
            # print("From Transaction :: ", from_transaction)
            # print("From Transaction Type :: ", from_transaction.type)

            transaction = Transaction.objects.get(id = linktransaction_instance.to_transaction_id.id)
            # print("Transaction :: ", transaction)
            # print("Transaction Type :: ", transaction.type)

            to_customer_id = transaction.customer_id.id if transaction.customer_id is not None else None
            print("to_customer_id :::",to_customer_id)
            to_staff_id = transaction.staff_id.id if transaction.staff_id is not None else None
            print("to_staff_id :::",to_staff_id)

            if transaction.type in ('payment_in', 'payment_out'):
                to_old_amount = transaction.total_amount - transaction.used_amount
            else:
                to_old_amount = transaction.total_amount - transaction.recived_or_paid_amount
            

            if from_transaction.type in ('payment_in', 'event_purchase', 'purchase'):

                if transaction.type in ('event_sale', 'sale'):

                    # print("RESCIVED AMOUNT :: ", transaction.recived_or_paid_amount, "TYPE :: ", type(transaction.recived_or_paid_amount))
                    if (old_amount - new_amount) > 0:
                        differnece =  old_amount - new_amount
                        # print("DIFFERNECE :: ", differnece)
                        updated_amount = transaction.recived_or_paid_amount - differnece
                        # print("UPDATED AMOUNT :: ", updated_amount)
                        transaction.recived_or_paid_amount = transaction.recived_or_paid_amount - differnece
                        transaction.save()
                        
                    if (new_amount - old_amount) > 0:
                        differnece =  new_amount - old_amount
                        # print("DIFFERNECE :: ", differnece)
                        updated_amount = transaction.recived_or_paid_amount + differnece
                        # print("UPDATED AMOUNTTTTTT :: ", updated_amount)
                        transaction.recived_or_paid_amount = transaction.recived_or_paid_amount + differnece
                        transaction.save()

                    to_new_amount = transaction.total_amount - transaction.recived_or_paid_amount
                    print("to_new_amount ::: ", to_new_amount)
                    balance_amount(to_customer_id, to_staff_id, to_old_amount, to_new_amount, transaction.type)

                elif transaction.type == 'payment_out':
                    
                    # print("RESCIVED AMOUNT :: ", transaction.used_amount, "TYPE :: ", type(transaction.used_amount))
                    if (old_amount - new_amount) > 0:
                        differnece =  old_amount - new_amount
                        # print("DIFFERNECE :: ", differnece)
                        updated_amount = transaction.used_amount - differnece
                        # print("UPDATED AMOUNT :: ", updated_amount)
                        transaction.used_amount = transaction.used_amount - differnece
                        transaction.save()
                        
                    if (new_amount - old_amount) > 0:
                        differnece =  new_amount - old_amount
                        # print("DIFFERNECE :: ", differnece)
                        updated_amount = transaction.used_amount + differnece
                        # print("UPDATED AMOUNTTTTTT :: ", updated_amount)
                        transaction.used_amount = transaction.used_amount + differnece
                        transaction.save()

                    to_new_amount = transaction.total_amount - transaction.used_amount
                    print("to_new_amount ::: ", to_new_amount)
                    balance_amount(to_customer_id, to_staff_id, to_old_amount, to_new_amount, transaction.type)

            elif from_transaction.type in ('payment_out', 'event_sale', 'sale'):

                if transaction.type in ('event_purchase', 'purchase'):
                    # print("RESCIVED AMOUNT :: ", transaction.recived_or_paid_amount, "TYPE :: ", type(transaction.recived_or_paid_amount))
                    if (old_amount - new_amount) > 0:
                        differnece =  old_amount - new_amount
                        # print("DIFFERNECE :: ", differnece)
                        updated_amount = transaction.recived_or_paid_amount - differnece
                        # print("UPDATED AMOUNT :: ", updated_amount)
                        transaction.recived_or_paid_amount = transaction.recived_or_paid_amount - differnece
                        transaction.save()
                        
                    if (new_amount - old_amount) > 0:
                        differnece =  new_amount - old_amount
                        # print("DIFFERNECE :: ", differnece)
                        updated_amount = transaction.recived_or_paid_amount + differnece
                        # print("UPDATED AMOUNTTTTTT :: ", updated_amount)
                        transaction.recived_or_paid_amount = transaction.recived_or_paid_amount + differnece
                        transaction.save()

                    to_new_amount = transaction.total_amount - transaction.recived_or_paid_amount
                    print("to_new_amount ::: ", to_new_amount)
                    balance_amount(to_customer_id, to_staff_id, to_old_amount, to_new_amount, transaction.type)

                elif transaction.type == 'payment_in':
                    # print("RESCIVED AMOUNT :: ", transaction.used_amount, "TYPE :: ", type(transaction.used_amount))
                    if (old_amount - new_amount) > 0:
                        differnece =  old_amount - new_amount
                        # print("DIFFERNECE :: ", differnece)
                        updated_amount = transaction.used_amount - differnece
                        # print("UPDATED AMOUNT :: ", updated_amount)
                        transaction.used_amount = transaction.used_amount - differnece
                        transaction.save()
                        
                    if (new_amount - old_amount) > 0:
                        differnece =  new_amount - old_amount
                        # print("DIFFERNECE :: ", differnece)
                        updated_amount = transaction.used_amount + differnece
                        # print("UPDATED AMOUNTTTTTT :: ", updated_amount)
                        transaction.used_amount = transaction.used_amount + differnece
                        transaction.save()

                    to_new_amount = transaction.total_amount - transaction.used_amount
                    print("to_new_amount ::: ", to_new_amount)
                    balance_amount(to_customer_id, to_staff_id, to_old_amount, to_new_amount, transaction.type)

    if delete_linktransactions is not None:
        # print("*** --- DELETE LINK TRANSACTION --- ***")
        for single_delete in delete_linktransactions:
            # print("single_delete :: ", single_delete)

            d_linktransaction = LinkTransaction.objects.get(pk = single_delete)
            # print("Link Transaction :: ", d_linktransaction.to_transaction_id.id)
            # print("LINK AMOUNT ::: ", d_linktransaction.linked_amount)

            from_transaction = Transaction.objects.get(id = d_linktransaction.from_transaction_id.id)

            from_customer_id = from_transaction.customer_id.id if from_transaction.customer_id is not None else None
            # print("to_customer_id :::",to_customer_id)
            from_staff_id = from_transaction.staff_id.id if from_transaction.staff_id is not None else None
            # print("to_staff_id :::",to_staff_id)

            from_old_amount = from_transaction.total_amount - from_transaction.used_amount
            
            if from_transaction.type in ('event_sale', 'sale', 'event_purchase', 'purchase'):
                from_transaction.recived_or_paid_amount = from_transaction.recived_or_paid_amount - d_linktransaction.linked_amount
                from_transaction.save()
            # else:
            #     from_transaction.used_amount = from_transaction.used_amount - d_linktransaction.linked_amount
            #     from_transaction.save()


            transaction = Transaction.objects.get(id = d_linktransaction.to_transaction_id.id)
            # print("Transaction :: ", transaction)
            # print("Transaction Type :: ", transaction.type)

            
            to_customer_id = transaction.customer_id.id if transaction.customer_id is not None else None
            # print("to_customer_id :::",to_customer_id)
            to_staff_id = transaction.staff_id.id if transaction.staff_id is not None else None
            # print("to_staff_id :::",to_staff_id)

            if transaction.type in ('payment_in', 'payment_out'):
                to_old_amount = transaction.total_amount - transaction.used_amount
            else:
                to_old_amount = transaction.total_amount - transaction.recived_or_paid_amount

            if transaction.type in ('event_sale', 'sale', 'event_purchase', 'purchase'):
                if from_transaction.type in ('payment_in', 'payment_out'):
                    from_transaction.used_amount = from_transaction.used_amount - d_linktransaction.linked_amount
                    from_transaction.save()

                    from_new_amount = from_transaction.total_amount - from_transaction.used_amount
                    print("from_new_amount ::: ", from_new_amount)
                    balance_amount(from_customer_id, from_staff_id, from_old_amount, from_new_amount, from_transaction.type)
                else:

                    # print("RESCIVED AMOUNT :: ", transaction.recived_or_paid_amount, "TYPE :: ", type(transaction.recived_or_paid_amount))
                    # print("LINKED AMOUNT :: ", d_linktransaction.linked_amount, "TYPE :: ", type(d_linktransaction.linked_amount))
                    transaction.recived_or_paid_amount = transaction.recived_or_paid_amount - d_linktransaction.linked_amount
                    print("transaction.recived_or_paid_amount :::",transaction.recived_or_paid_amount)
                    transaction.save()

                to_new_amount = transaction.total_amount - transaction.recived_or_paid_amount
                print("to_new_amount ::: ", to_new_amount)
                balance_amount(to_customer_id, to_staff_id, to_old_amount, to_new_amount, transaction.type)


            elif transaction.type in ('payment_in', 'payment_out'):
                if transaction_type is not None:
                    if transaction.type != transaction_type:
                        # print("RESCIVED AMOUNT :: ", transaction.used_amount, "TYPE :: ", type(transaction.used_amount))
                        # print("LINKED AMOUNT :: ", d_linktransaction.linked_amount, "TYPE :: ", type(d_linktransaction.linked_amount))
                        transaction.used_amount = transaction.used_amount - d_linktransaction.linked_amount
                        # print("transaction.used_amount :::",transaction.used_amount)
                        transaction.save()

                        to_new_amount = transaction.total_amount - transaction.used_amount
                        print("to_new_amount ::: ", to_new_amount)
                        balance_amount(to_customer_id, to_staff_id, to_old_amount, to_new_amount, transaction.type)
                else:
                    # print("RESCIVED AMOUNT :: ", transaction.used_amount, "TYPE :: ", type(transaction.used_amount))
                        # print("LINKED AMOUNT :: ", d_linktransaction.linked_amount, "TYPE :: ", type(d_linktransaction.linked_amount))
                        transaction.used_amount = transaction.used_amount - d_linktransaction.linked_amount
                        # print("transaction.used_amount :::",transaction.used_amount)
                        transaction.save()

                        to_new_amount = transaction.total_amount - transaction.used_amount
                        print("to_new_amount ::: ", to_new_amount)
                        balance_amount(to_customer_id, to_staff_id, to_old_amount, to_new_amount, transaction.type)

                if transaction_type is not None:
                    if from_transaction.type != transaction_type:
                        # print("From Transaction ::: ",from_transaction)
                        # print("FROM TRASACTION TYPE :::", from_transaction.type)
                        # print("RESCIVED AMOUNT :: ", from_transaction.used_amount, "TYPE :: ", type(from_transaction.used_amount))
                        # print("LINKED AMOUNT :: ", d_linktransaction.linked_amount, "TYPE :: ", type(d_linktransaction.linked_amount))
                        from_transaction.used_amount = from_transaction.used_amount - d_linktransaction.linked_amount
                        # print("from_transaction.used_amount :::",from_transaction.used_amount)
                        from_transaction.save()

                        from_new_amount = from_transaction.total_amount - from_transaction.used_amount
                        print("from_new_amount ::: ", from_new_amount)
                        balance_amount(from_customer_id, from_staff_id, from_old_amount, from_new_amount, from_transaction.type)

            d_linktransaction.delete()




