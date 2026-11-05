from django.contrib import admin
from django.contrib.auth import views as auth
from django.urls import path
from exchange import views

urlpatterns = [
    path('', views.home),
    path('login/', auth.LoginView.as_view(template_name='exchange/login.html')),
    path('logout/', auth.LogoutView.as_view()),
    path('admin/', admin.site.urls),
    path('api/state/', views.state),
    path('api/action/<str:action>/', views.action),
    path('receipt/<int:order_id>/', views.receipt_document),
    path('evidence/<int:photo_id>/', views.evidence),
]
