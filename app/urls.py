from django.urls import path, include

from rest_framework import routers

from app import views
from app.views import *

router = routers.DefaultRouter()
router.register(r'user',views.UserViewSet)
router.register(r'customer',views.CustomerViewSet)
router.register(r'inventory',views.InventoryViewSet)
router.register(r'staff',views.StaffViewSet)
router.register(r'staffskill',views.StaffSkillViewSet)
router.register(r'event',views.EventViewSet)
router.register(r'quotation',views.QuotationViewSet)
router.register(r'transaction',views.TransactionViewSet)
router.register(r'exportquotation',views.QuotationExport)
router.register(r'exporttransaction',views.TransactionExport)
router.register(r'exportinvoice',views.InvoiceExport)

urlpatterns =[
    path('',include(router.urls)),
    path('report/',views.Report, name='report'),
]