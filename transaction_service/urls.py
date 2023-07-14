from django.urls import include, path

urlpatterns = [
    path('transaction_status/', include('transaction_status.urls')),
]
