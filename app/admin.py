from django.contrib import admin
from .models import*
# Register your models here.


class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'type_of_user']
admin.site.register(User, UserAdmin)


class StudioDetailsAdmin(admin.ModelAdmin):
    list_display = ['name', 'email']
admin.site.register(StudioDetails, StudioDetailsAdmin)


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

class TransactionAdmin(admin.ModelAdmin):
    list_display = ['notes', 'amount','payment_type']
admin.site.register(Transaction, TransactionAdmin)

class QuotationAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'final_amount', 'payment_status']
admin.site.register(Quotation, QuotationAdmin)

class EventDayAdmin(admin.ModelAdmin):
    list_display = ['quotation_id', 'event_date']
admin.site.register(EventDay, EventDayAdmin)

class InventoryDetailsAdmin(admin.ModelAdmin):
    list_display = ['eventday_id', 'inventory_id', 'price']
admin.site.register(InventoryDetails, InventoryDetailsAdmin)

class EventDetailsAdmin(admin.ModelAdmin):
    list_display = ['eventday_id', 'quotation_id', 'event_id']
admin.site.register(EventDetails, EventDetailsAdmin)

class ExposureDetailsAdmin(admin.ModelAdmin):
    list_display = ['staff_id', 'price']
admin.site.register(ExposureDetails, ExposureDetailsAdmin)


class InventoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'base_price', 'sell_price']
admin.site.register(Inventory, InventoryAdmin)

