from django.contrib import admin
from .models import*
# Register your models here.


class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'type_of_user']
admin.site.register(User, UserAdmin)

class CustomerAdmin(admin.ModelAdmin):
    list_display = ['email', 'full_name']
admin.site.register(Customer, CustomerAdmin)

class StaffAdmin(admin.ModelAdmin):
    list_display = ['email', 'full_name']
admin.site.register(Staff, StaffAdmin)

# class SkillAdmin(admin.ModelAdmin):
#     list_display = ['email', 'type_of_user']
# admin.site.register(Skill, SkillAdmin)
admin.site.register(StaffSkill)

class EventAdmin(admin.ModelAdmin):
    list_display = ['event_name']
admin.site.register(Event, EventAdmin)

class QuotationAdmin(admin.ModelAdmin):
    list_display = ['event_id', 'start_date', 'end_date']
admin.site.register(Quotation, QuotationAdmin)

class InventoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'base_price', 'sell_price']
admin.site.register(Inventory, InventoryAdmin)

class TransactionAdmin(admin.ModelAdmin):
    list_display = ['notes', 'amount','quotation_id']
admin.site.register(Transaction, TransactionAdmin)