from django.contrib import admin
from .models import Categoria, Producto, Usuario, Venta, DetalleVenta, CierreCaja, Oferta

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombreCategoria', 'descripcion')
    search_fields = ['nombreCategoria']

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombreProducto', 'idCategoria', 'precioVenta', 'stockActual', 'stockUmbral')
    list_filter = ('idCategoria',)
    search_fields = ['nombreProducto']
    list_editable = ['precioVenta', 'stockActual', 'stockUmbral']
    fields = ['nombreProducto', 'imagen', 'idCategoria', 'costoProducto', 'precioVenta', 'margenGanancia', 'stockActual', 'stockUmbral']

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellidoPaterno', 'rol', 'fechaCreacion')
    list_filter = ('rol',)
    search_fields = ['nombre', 'rut']

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'metodoPago', 'montoPagado', 'fechaVenta')
    list_filter = ('metodoPago', 'fechaVenta')