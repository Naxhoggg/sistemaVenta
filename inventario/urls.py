from django.urls import path
from . import views

app_name = "inventario"

urlpatterns = [
    path("inicio/", views.inicio, name="inicio"),
    path("", views.inicio, name="inicio"),
    path("productos/", views.lista_productos, name="lista_productos"),
    path("ventas/", views.registro_venta, name="registro_venta"),
    path("cierre-caja/", views.cierre_caja, name="cierre_caja"),
    path("historial/", views.historial_ventas, name="historial_ventas"),
    path("finalizar-venta/", views.finalizar_venta, name="finalizar_venta"),
    path("registrar/", views.registrar_usuario, name="registrar_usuario"),
    path("iniciar-sesion/", views.iniciar_sesion, name="iniciar_sesion"),
    path("cerrar-sesion/", views.cerrar_sesion, name="cerrar_sesion"),
    path("actualizar-sesion/", views.actualizar_sesion, name="actualizar_sesion"),
    # URLs de administración
    path("admin/inventario/", views.admin_inventario, name="admin_inventario"),
    path("admin/producto/nuevo/", views.nuevo_producto, name="nuevo_producto"),
    path("admin/reportes/", views.admin_reportes, name="admin_reportes"),
    path("admin/reportes/ventas/", views.reporte_ventas, name="reporte_ventas"),
    path(
        "admin/producto/<str:producto_id>/",
        views.obtener_producto,
        name="obtener_producto",
    ),
    path('admin/nueva-categoria/', views.nueva_categoria, name='nueva_categoria'),
    path('admin/nuevo-producto/', views.nuevo_producto, name='nuevo_producto'),
    path('admin/producto/<str:producto_id>/actualizar/', views.actualizar_producto, name='actualizar_producto'),
]
