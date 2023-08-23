from django.contrib import admin
from .models import*

# Register your models here.

class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name']
admin.site.register(Category, CategoryAdmin)


class ItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'price']
admin.site.register(Item, ItemAdmin)


class ExpenseAdmin(admin.ModelAdmin):
    list_display = ['date', 'amount']
admin.site.register(Expense, ExpenseAdmin)


class ExpenseItemAdmin(admin.ModelAdmin):
    list_display = ['expense_id', 'category_id', 'item_id', 'amount']