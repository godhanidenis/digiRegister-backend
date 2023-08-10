from import_export import resources, fields
from app.models import *
from import_export.widgets import ForeignKeyWidget, DateTimeWidget, DateWidget, BooleanWidget, JSONWidget, IntegerWidget

class QuotationResource(resources.ModelResource):
    id = fields.Field(column_name='id', attribute='id')
    user_id = fields.Field(column_name='user_id', attribute='user_id', widget=ForeignKeyWidget(User, 'shop_name'))
    customer_id = fields.Field(column_name='customer_id', attribute='customer_id', widget=ForeignKeyWidget(Customer, 'full_name'))
    event_id = fields.Field(column_name='event_id', attribute='event_id', widget=ForeignKeyWidget(Event, 'event_name'))
    event_venue = fields.Field(column_name='event_venue', attribute='event_venue')
    couple_name = fields.Field(column_name='couple_name', attribute='couple_name')
    start_date = fields.Field(column_name='start_date', attribute='start_date', widget=DateWidget(format=None))
    end_date = fields.Field(column_name='end_date', attribute='end_date', widget=DateWidget(format=None))
    due_date = fields.Field(column_name='due_date', attribute='due_date', widget=DateWidget(format=None))
    # is_converted = fields.Field(column_name='is_converted', attribute='is_converted', widget=BooleanWidget())
    # json_data = fields.Field(column_name='json_data', attribute='json_data' ,widget=JSONWidget())
    created_on = fields.Field(column_name='created_on', attribute='created_on', widget=DateTimeWidget(format=None))
    converted_on = fields.Field(column_name='converted_on', attribute='converted_on', widget=DateTimeWidget(format=None))
    final_amount = fields.Field(column_name='final_amount', attribute='final_amount', widget=IntegerWidget(coerce_to_string=False))
    discount = fields.Field(column_name='discount', attribute='discount', widget=IntegerWidget(coerce_to_string=False))
    # transactions = fields.Field(column_name='transactions', attribute='transactions')
    
    # def dehydrate_override(self, Quotation):
    #     if Quotation.is_converted:
    #         return 'Yes'
    #     return 'No'

    # def dehydrate_transaction_data(self, quotation):
    #     transactions = Transaction.objects.filter(quotation_id=quotation)
    #     print("Transaction ::", transaction)
    #     transaction_strings = []
    #     for transaction in transactions:
    #         transaction_strings.append(
    #             f"{transaction.date} - {transaction.amount} - {transaction.notes}"
    #         )
    #     print("ENDDDD")
    #     return '\n'.join(transaction_strings)

    class Meta:
        model = Quotation
        fields = '__all__'


class TransactionResource(resources.ModelResource):
    quotation_id = fields.Field(column_name='quotation_id', attribute='quotation_id',widget=ForeignKeyWidget(Quotation, 'quotation_id'))
    notes = fields.Field(column_name='notes', attribute='notes')
    date = fields.Field(column_name='date', attribute='date', widget=DateWidget(format=None))
    amount = fields.Field(column_name='amount', attribute='amount', widget=IntegerWidget(coerce_to_string=False))
    
    class Meta:
        model = Transaction
        fields = '__all__'