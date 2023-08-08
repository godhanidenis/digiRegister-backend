from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractUser
# Create your models here.

class UserManager(BaseUserManager):
    
    def create_user(self, email, password):
        """
        Create and save a User with the given email and password.
        """
        # if not email:
        #     raise ValueError(('The email must be set'))
        user = self.model(email=email ,password=password, is_staff=True, is_superuser=True, is_active=True)      
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password):

        # extra_fields.setdefault('userid', userid), 
        # extra_fields.setdefault('is_staff', True)
        # extra_fields.setdefault('is_superuser', True)
        # extra_fields.setdefault('is_active', True)

        user = self.create_user(
            email,
            password,
            # **extra_fields
        )

        # user.is_staff = True
        # user.is_superuser = True
        # user.is_active = True
        # user.save()

        return user
    

class User(AbstractUser):
    ROLE = (
        ("super_admin", "SUPER_ADMIN"),
        ("company_owner", "COMANY_OWNER"),
        )
    username = models.CharField(max_length=10, default='', null=True, blank=True)
    shop_name = models.CharField(max_length=200, null=True, blank=True)
    full_name = models.CharField(max_length=100, null=True, blank=True)
    mobile_no = models.CharField(max_length=15, null=True, blank=True)
    email = models.EmailField(max_length=100, unique=True)
    type_of_user = models.CharField(choices=ROLE, default="super_admin", max_length=20)
    address = models.CharField(max_length=200, null=True, blank=True)
    is_active = models.BooleanField(default=False)
    instagram_id = models.CharField(max_length=100, null=True, blank=True)
    you_tube = models.CharField(max_length=100, null=True, blank=True)
    facebook_id = models.CharField(max_length=100, null=True, blank=True)
    profile_pic = models.CharField(max_length=150, null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    # def __str__(self):
    #     return self.full_name
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def save(self, *args, **kwargs):
        if not self.id:
            if self.type_of_user != 'super_admin':
                self.set_password(self.password)
        super().save(*args, **kwargs)


class Customer(models.Model):
    user_id = models.ForeignKey(User,null=True, blank=True, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100, null=True, blank=True)
    mobile_no = models.CharField(max_length=15, unique=True)
    email = models.EmailField(max_length=100, null=True, blank=True)
    address = models.CharField(max_length=200, null=True, blank=True)

    def _str__(self):
        return self.full_name
    
    class Meta:
        unique_together = ['user_id', 'mobile_no']


class Inventory(models.Model):
    TYPE = (
        ("service","SERVICE"),
        ("product","PRODUCT"),
    )
    user_id = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    type = models.CharField(choices=TYPE, default="service", max_length=20)
    name = models.CharField(max_length=100)
    qty = models.IntegerField(null=True, blank=True)
    base_price = models.FloatField(max_length=10, null=True, blank=True)
    sell_price = models.FloatField(max_length=10, null=True, blank=True)
    
    def _str__(self):
        return self.name


class Staff(models.Model):
    user_id = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100, null=True, blank=True)
    mobile_no = models.CharField(max_length=15,unique=True)
    email = models.EmailField(max_length=100, null=True, blank=True)
    address = models.CharField(max_length=200, null=True, blank=True)
    studio_name = models.CharField(max_length=150, null=True, blank=True)
    social_media = models.CharField(max_length=100, null=True, blank=True)


    def _str__(self):
        return self.full_name
    
    class Meta:
        unique_together = ['user_id', 'mobile_no']


class StaffSkill(models.Model):
    inventory_id = models.ForeignKey(Inventory, null=True, blank=True, on_delete=models.CASCADE)
    staff_id = models.ForeignKey(Staff, null=True, blank=True, on_delete=models.CASCADE)
    price = models.FloatField(max_length=10)


class Event(models.Model):
    user_id = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    event_name = models.CharField(max_length=100)

    def __str__(self):
        return self.event_name


class Quotation(models.Model):
    user_id = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    customer_id = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.CASCADE)
    event_id = models.ForeignKey(Event, null=True, blank=True, on_delete=models.CASCADE)
    event_venue = models.CharField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    is_converted = models.BooleanField(default=False)
    json_data = models.JSONField(blank=True, null=True)
    created_on = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    converted_on = models.DateTimeField(null=True, blank=True)
    final_amount = models.IntegerField(default=0)
    discount = models.IntegerField(default=0)


class Transaction(models.Model):
    quotation_id = models.ForeignKey(Quotation, null=True, blank=True, on_delete=models.CASCADE)
    notes = models.CharField(max_length=250, null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    amount = models.IntegerField(null=True, blank=True)



