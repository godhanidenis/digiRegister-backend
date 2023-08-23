from django.db import models
from app.models import User
# Create your models here.

class Category(models.Model):
    user_id = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Item(models.Model):
    # category_id = models.ForeignKey(Category, null=True, blank=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    price = models.IntegerField(default=0)

    def __str__(self):
        return self.name


class Expense(models.Model):
    date = models.DateField(null=True, blank=True)
    amount = models.IntegerField(default=0)


class ExpenseItem(models.Model):
    expense_id = models.ForeignKey(Expense, null=True, blank=True, on_delete=models.CASCADE) 
    category_id = models.ForeignKey(Category, null=True, blank=True, on_delete=models.CASCADE)
    item_id = models.ForeignKey(Item, null=True, blank=True, on_delete=models.CASCADE)
    amount = models.IntegerField(default=0)

