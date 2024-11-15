from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Producto, Venta, Usuario, CierreCaja, DetalleVenta, Categoria
import json

def inicio(request):
    return render(request, 'inventario/inicio.html')

def lista_productos(request):
    productos = Producto.objects.all()
    categorias = Categoria.objects.all()
    context = {
        'productos': productos,
        'categorias': categorias
    }
    return render(request, 'inventario/productos.html', context)

def registro_venta(request):
    productos = Producto.objects.all()
    print("Productos:", productos)  # Para debug
    return render(request, 'inventario/venta.html', {'productos': productos})

def cierre_caja(request):
    return render(request, 'inventario/cierre_caja.html')

def historial_ventas(request):
    ventas = Venta.objects.all().order_by('-fechaVenta')
    return render(request, 'inventario/historial.html', {'ventas': ventas})

@csrf_exempt
def finalizar_venta(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            productos = data.get('productos', [])
            
            if not productos:
                return JsonResponse({'success': False, 'error': 'No hay productos en el carrito'}, status=400)
            
            # Crear la venta
            venta = Venta.objects.create(
                idUsuario_id=1,
                metodoPago='efectivo',
                montoPagado=sum(float(p['precioVenta']) for p in productos)
            )
            
            # Crear los detalles de venta y actualizar stock
            for producto in productos:
                DetalleVenta.objects.create(
                    idVenta=venta,
                    idProducto_id=producto['id'],
                    cantidadVendida=1,
                    precioUnitario=producto['precioVenta'],
                    totalProducto=producto['precioVenta']
                )
                
                prod = Producto.objects.get(id=producto['id'])
                prod.stockActual -= 1
                prod.save()
            
            return JsonResponse({'success': True})
            
        except Exception as e:
            print(f"Error en finalizar_venta: {str(e)}")  # Para debugging
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)


