from rest_framework import status
from rest_framework.response import Response

from .serializers import *

from datetime import datetime
import pytz

def convert_time_utc_to_local(timezone, data):
    if data is not None:
        # print("DATA ::", data)
        utc_datetime = datetime.strptime(data, "%Y-%m-%dT%H:%M:%SZ")
        # print("utc_datetime",utc_datetime)
        target_timezone = pytz.timezone(timezone)
        # print("target_timezone",target_timezone)
        converted_time = utc_datetime.replace(tzinfo=pytz.utc).astimezone(target_timezone)
        # print("converted_time",converted_time)
        final_time = converted_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        # print("final_time",final_time)

        return final_time
    


def link_transaction(transaction_id, linktransaction_data):
    print("Transaction ID ::", transaction_id)
    print("Link Transaction Data ::", linktransaction_data)
    new_linktransactions = linktransaction_data.get('new_linktransaction', None)
    print("new_linktransaction ::", new_linktransactions)
    update_linktransactions = linktransaction_data.get('update_linktransaction', None)
    print("update_linktransaction ::", update_linktransactions)
    delete_linktransactions = linktransaction_data.get('delete_linktransaction', None)
    print("delete_linktransaction ::", delete_linktransactions)

    if new_linktransactions is not None:
        all_linktransaction = []
        print("ADD LINK TRANSACTION")
        for new_single in new_linktransactions:
            new_single['from_transaction_id'] = transaction_id
            print("new_single :: ", new_single)
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
            

            if from_transaction.type in ('payment_in' , 'event_purchase' , 'purchase'):
                if transaction.type in ('event_sale', 'sale'):
                    print("RESCIVED AMOUNT :: ", transaction.recived_or_paid_amount, "TYPE :: ", type(transaction.recived_or_paid_amount))
                    transaction.recived_or_paid_amount = transaction.recived_or_paid_amount + linktransaction.linked_amount
                    transaction.save()

                elif transaction.type == 'payment_out':
                    print("RESCIVED AMOUNT :: ", transaction.used_amount, "TYPE :: ", type(transaction.used_amount))
                    transaction.used_amount = transaction.used_amount + linktransaction.linked_amount
                    transaction.save()
            
            elif from_transaction.type == ('payment_out', 'event_sale', 'sale'):
                if transaction.type in ('event_purchase', 'purchase'):
                    print("RESCIVED AMOUNT :: ", transaction.recived_or_paid_amount, "TYPE :: ", type(transaction.recived_or_paid_amount))
                    transaction.recived_or_paid_amount = transaction.recived_or_paid_amount + linktransaction.linked_amount
                    transaction.save()

                elif transaction.type == 'payment_in':
                    print("RESCIVED AMOUNT :: ", transaction.used_amount, "TYPE :: ", type(transaction.used_amount))
                    transaction.used_amount = transaction.used_amount + linktransaction.linked_amount
                    transaction.save()


    if update_linktransactions is not None:
        all_linktransaction = []
        print("UPDATE LINK TRANSACTION")
        for update_single in update_linktransactions:
            print("update_single :: ", update_single)
            link = LinkTransaction.objects.get(pk=update_single['id'])
            print("LINK TRANSACTION :: ", link)
            old_amount = link.linked_amount
            print("OLD AMOUNT :: ", old_amount)

            linktransactionSerializer = LinkTransactionSerializer(link, data=update_single, partial=True)
            if linktransactionSerializer.is_valid():
                linktransaction_instance = linktransactionSerializer.save()
                print("linktransaction_instance ::: ",linktransaction_instance)
                all_linktransaction.append(linktransaction_instance)
            else:
                return Response(linktransactionSerializer.errors, status=status.HTTP_400_BAD_REQUEST)

            new_amount = linktransaction_instance.linked_amount
            print("NEW AMOUNT :: ",new_amount)

            from_transaction = Transaction.objects.get(id = linktransaction_instance.from_transaction_id.id)
            print("From Transaction :: ", from_transaction)
            print("From Transaction Type :: ", from_transaction.type)

            transaction = Transaction.objects.get(id = linktransaction_instance.to_transaction_id.id)
            print("Transaction :: ", transaction)
            print("Transaction Type :: ", transaction.type)
            print("RESCIVED AMOUNT :: ", transaction.recived_or_paid_amount, "TYPE :: ", type(transaction.recived_or_paid_amount))

            if from_transaction.type in ('payment_in', 'event_purchase', 'purchase'):
                if transaction.type in ('event_sale', 'sale'):
                    print("RESCIVED AMOUNT :: ", transaction.recived_or_paid_amount, "TYPE :: ", type(transaction.recived_or_paid_amount))

                    if (old_amount - new_amount) > 0:
                        differnece =  old_amount - new_amount
                        print("DIFFERNECE :: ", differnece)
                        updated_amount = transaction.recived_or_paid_amount - differnece
                        print("UPDATED AMOUNT :: ", updated_amount)

                    if (new_amount - old_amount) > 0:
                        differnece =  new_amount - old_amount
                        print("DIFFERNECE :: ", differnece)
                        updated_amount = transaction.recived_or_paid_amount + differnece
                        print("UPDATED AMOUNTTTTTT :: ", updated_amount)

                    transaction.recived_or_paid_amount = updated_amount
                    transaction.save()

                elif transaction.type == 'payment_out':
                    print("RESCIVED AMOUNT :: ", transaction.used_amount, "TYPE :: ", type(transaction.used_amount))

                    if (old_amount - new_amount) > 0:
                        differnece =  old_amount - new_amount
                        print("DIFFERNECE :: ", differnece)
                        updated_amount = transaction.used_amoun - differnece
                        print("UPDATED AMOUNT :: ", updated_amount)
                        
                    if (new_amount - old_amount) > 0:
                        differnece =  new_amount - old_amount
                        print("DIFFERNECE :: ", differnece)
                        updated_amount = transaction.used_amoun + differnece
                        print("UPDATED AMOUNTTTTTT :: ", updated_amount)

                    transaction.used_amount = updated_amount
                    transaction.save()
            
            elif from_transaction.type == ('payment_out', 'event_sale', 'sale'):
                if transaction.type in ('event_purchase', 'purchase'):
                    print("RESCIVED AMOUNT :: ", transaction.recived_or_paid_amount, "TYPE :: ", type(transaction.recived_or_paid_amount))
                    if (old_amount - new_amount) > 0:
                        differnece =  old_amount - new_amount
                        print("DIFFERNECE :: ", differnece)
                        updated_amount = transaction.recived_or_paid_amount - differnece
                        print("UPDATED AMOUNT :: ", updated_amount)

                    if (new_amount - old_amount) > 0:
                        differnece =  new_amount - old_amount
                        print("DIFFERNECE :: ", differnece)
                        updated_amount = transaction.recived_or_paid_amount + differnece
                        print("UPDATED AMOUNTTTTTT :: ", updated_amount)

                    transaction.recived_or_paid_amount = updated_amount
                    transaction.save()

                elif transaction.type == 'payment_in':
                    print("RESCIVED AMOUNT :: ", transaction.used_amount, "TYPE :: ", type(transaction.used_amount))
                    if (old_amount - new_amount) > 0:
                        differnece =  old_amount - new_amount
                        print("DIFFERNECE :: ", differnece)
                        updated_amount = transaction.used_amoun - differnece
                        print("UPDATED AMOUNT :: ", updated_amount)
                        
                    if (new_amount - old_amount) > 0:
                        differnece =  new_amount - old_amount
                        print("DIFFERNECE :: ", differnece)
                        updated_amount = transaction.used_amoun + differnece
                        print("UPDATED AMOUNTTTTTT :: ", updated_amount)

                    transaction.used_amount = updated_amount
                    transaction.save()


    if delete_linktransactions is not None:
        print("DELETE LINK TRANSACTION")
        for single_delete in delete_linktransactions:
            print("single_delete :: ", single_delete)

            d_linktransaction = LinkTransaction.objects.get(pk = single_delete)
            print("Link Transaction :: ", d_linktransaction.to_transaction_id.id)

            transaction = Transaction.objects.get(id = d_linktransaction.to_transaction_id.id)
            print("Transaction :: ", transaction)
            print("Transaction Type :: ", transaction.type)
            

            if transaction.type in ('event_sale', 'sale', 'event_purchase', 'purchase'):
                print("RESCIVED AMOUNT :: ", transaction.recived_or_paid_amount, "TYPE :: ", type(transaction.recived_or_paid_amount))
                transaction.recived_or_paid_amount = transaction.recived_or_paid_amount - d_linktransaction.linked_amount
                transaction.save()

            elif transaction.type in ('payment_out', 'payment_out'):
                print("RESCIVED AMOUNT :: ", transaction.used_amount, "TYPE :: ", type(transaction.used_amount))
                transaction.used_amount = transaction.used_amount - d_linktransaction.linked_amount
                transaction.save()

            d_linktransaction.delete()