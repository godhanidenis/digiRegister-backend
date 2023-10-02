from django.urls import path, include

from rest_framework import routers

from app import views
from app.views import *

router = routers.DefaultRouter()
router.register(r'user',views.UserViewSet)
router.register(r'studiodetails',views.StudioDetailsViewSet)
router.register(r'customer',views.CustomerViewSet)
router.register(r'inventory',views.InventoryViewSet)
router.register(r'staff',views.StaffViewSet)
router.register(r'staffskill',views.StaffSkillViewSet)
router.register(r'event',views.EventViewSet)

router.register(r'transaction',views.TransactionViewSet)

router.register(r'quotation',views.QuotationViewSet)
router.register(r'eventday',views.EventDayViewSet)
router.register(r'inventorydetails',views.InventoryDetailsViewSet)
router.register(r'eventdetails',views.EventDetailsViewSet)
router.register(r'exposuredetails',views.ExposureDetailsViewSet)

router.register(r'linktransaction',views.LinkTransactionViewSet)
router.register(r'inventorydescription',views.InventoryDescriptionViewSet)
router.register(r'balance',views.BalanceViewSet)


router.register(r'amountreport',views.AmountReportViewSet)

router.register(r'exportcustomer',views.CustomerExport)
router.register(r'exportquotation',views.QuotationExport)
router.register(r'exporttransaction',views.TransactionExport)
router.register(r'exportinvoice',views.InvoiceExport)


urlpatterns =[
    path('',include(router.urls)),  
    path('transactionlink/',views.TransactionLink, name='transactionlink'),
    path('staffstatus/',views.StaffStatus, name='staffstatus'),
    path('eventdetail/',views.EventDetail, name='eventdetail'),
    path('converturl/',views.ConvertBucketURL, name='convertbucketurl'),
    # path('totalsale/',views.TotalSale, name='totalsale'),
    # path('totalexpense/',views.TotalExpense, name='totalexpense'),
    # path('totalamount/',views.TotalAmount, name='totalamount'),
    # path('totalpurchase/',views.TotalPurchase, name='totalpurchase'),



    
    path('conversationreport/',views.ConversationRateReport, name='conversationratereport'),
    path('statusreport/',views.InvoiceStatusReport, name='invoicestatusreport'),
    path('earningreport/',views.MonthylyEarningReport, name='monthylyearningreport'),
    path('creationreport/',views.InvoiceCreationReport, name='invoicecreationreport'),
]       