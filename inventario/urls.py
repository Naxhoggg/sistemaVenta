from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('productos/', views.lista_productos, name='lista_productos'),
    path('ventas/', views.registro_venta, name='registro_venta'),
    path('cierre-caja/', views.cierre_caja, name='cierre_caja'),
    path('historial/', views.historial_ventas, name='historial_ventas'),
    path('finalizar-venta/', views.finalizar_venta, name='finalizar_venta'),  # Nueva línea
]