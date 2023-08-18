from import_export import resources, fields
from app.models import *
from import_export.widgets import ForeignKeyWidget, DateTimeWidget, DateWidget, BooleanWidget, JSONWidget, IntegerWidget

class CustomerResource(resources.ModelResource):
    id = fields.Field(column_name='ID', attribute='id')
    # user_id = fields.Field(column_name='User ID', attribute='user_id',widget=ForeignKeyWidget(User, 'id'))
    full_name = fields.Field(column_name='Full Name', attribute='full_name')
    mobile_no = fields.Field(column_name='Mobile No.', attribute='mobile_no')
    email = fields.Field(column_name='Email', attribute='email')
    address = fields.Field(column_name='Address', attribute='address')
    social_media = fields.Field(column_name='Social Media Link', attribute='social_media')

    class Meta:
        model = Customer
        fields = '__all__'


class QuotationResource(resources.ModelResource):
    id = fields.Field(column_name='ID', attribute='id')
    user_id = fields.Field(column_name='User ID', attribute='user_id', widget=ForeignKeyWidget(User, 'shop_name'))
    customer_id = fields.Field(column_name='Customer Name', attribute='customer_id', widget=ForeignKeyWidget(Customer, 'full_name'))
    event_id = fields.Field(column_name='Event Name', attribute='event_id', widget=ForeignKeyWidget(Event, 'event_name'))
    event_venue = fields.Field(column_name='Event Venue', attribute='event_venue')
    couple_name = fields.Field(column_name='Couple Name', attribute='couple_name')
    start_date = fields.Field(column_name='Start Date', attribute='start_date', widget=DateWidget(format=None))
    end_date = fields.Field(column_name='End Date', attribute='end_date', widget=DateWidget(format=None))
    due_date = fields.Field(column_name='Due Date', attribute='due_date', widget=DateWidget(format=None))
    # is_converted = fields.Field(column_name='is_converted', attribute='is_converted', widget=BooleanWidget())
    # json_data = fields.Field(column_name='json_data', attribute='json_data' ,widget=JSONWidget())
    created_on = fields.Field(column_name='Created On', attribute='created_on', widget=DateTimeWidget(format=None))
    converted_on = fields.Field(column_name='Converted On', attribute='converted_on', widget=DateTimeWidget(format=None))
    final_amount = fields.Field(column_name='Final Amount', attribute='final_amount', widget=IntegerWidget(coerce_to_string=False))
    discount = fields.Field(column_name='Discount', attribute='discount', widget=IntegerWidget(coerce_to_string=False))
    payment_status = fields.Field(column_name='Payment Status', attribute='payment_status')
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
    quotation_id = fields.Field(column_name='Quotation ID', attribute='quotation_id',widget=ForeignKeyWidget(Quotation, 'id'))
    notes = fields.Field(column_name='Notes', attribute='notes')
    date = fields.Field(column_name='Date', attribute='date', widget=DateWidget(format=None))
    amount = fields.Field(column_name='Amount', attribute='amount', widget=IntegerWidget(coerce_to_string=False))
    
    class Meta:
        model = Transaction
        fields = '__all__'