from django.contrib import admin
from .models import Categoria, Producto, Usuario, Venta, DetalleVenta, CierreCaja, Oferta

class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombreCategoria', 'descripcion')
    search_fields = ['nombreCategoria']

class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombreProducto', 'idCategoria', 'precioVenta', 'stockActual', 'stockUmbral')
    list_filter = ('idCategoria',)
    search_fields = ['nombreProducto']
    list_editable = ['precioVenta', 'stockActual', 'stockUmbral']
    fields = ['nombreProducto', 'imagen', 'idCategoria', 'costoProducto', 'precioVenta', 'margenGanancia', 'stockActual', 'stockUmbral']

class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'apellidoPaterno', 'rol', 'fechaCreacion')
    list_filter = ('rol',)
    search_fields = ['nombre', 'rut']

class VentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'metodoPago', 'montoPagado', 'fechaVenta')
    list_filter = ('metodoPago', 'fechaVenta')

# Registrar los modelos
admin.site.register(Categoria, CategoriaAdmin)
admin.site.register(Producto, ProductoAdmin)
admin.site.register(Usuario, UsuarioAdmin)
admin.site.register(Venta, VentaAdmin)