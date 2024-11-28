from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.core.files.storage import default_storage
from django.utils import timezone
from django.conf import settings
from django.db.models import Sum

from .models import Producto, Venta, Usuario, CierreCaja, DetalleVenta, Categoria

from sistemaVenta.firebase_config import get_db
from firebase_admin import firestore

import json
from datetime import datetime
import uuid


def inicio(request):
    # Verificar si hay una sesión activa
    if "user_id" in request.session and "rol" in request.session:
        print(
            f"Sesión activa - ID: {request.session['user_id']}, Rol: {request.session['rol']}"
        )
        if request.session["rol"] == "cajero":
            return redirect("inventario:registro_venta")
        elif request.session["rol"] == "admin":
            return redirect("inventario:admin_inventario")

    return render(
        request,
        "inventario/inicio.html",
        {"FIREBASE_CONFIG": settings.FIREBASE_CONFIG, "es_usuario_autenticado": False},
    )


@login_required
def lista_productos(request):
    db = get_db()
    productos_ref = db.collection("productos").stream()
    categorias_ref = db.collection("categorias").stream()

    productos_lista = []
    categorias_lista = []

    for producto in productos_ref:
        prod_dict = producto.to_dict()
        prod_dict["id"] = producto.id
        productos_lista.append(prod_dict)

    for categoria in categorias_ref:
        cat_dict = categoria.to_dict()
        cat_dict["id"] = categoria.id
        categorias_lista.append(cat_dict)

    context = {"productos": productos_lista, "categorias": categorias_lista}
    return render(request, "inventario/productos.html", context)


@csrf_exempt
@login_required
def registro_venta(request):
    if request.session.get("rol") != "cajero":
        return redirect("inicio")  # Redirige si no es cajero

    db = get_db()
    productos_ref = db.collection("productos").stream()

    productos_lista = []

    for producto in productos_ref:
        prod_dict = producto.to_dict()
        prod_dict["id"] = producto.id
        productos_lista.append(prod_dict)

    return render(request, "inventario/venta.html", {"productos": productos_lista})


@login_required
def cierre_caja(request):

    if request.method == "POST":
        try:
            db = get_db()
            # Obtener ventas del día actual
            hoy = datetime.now()
            inicio_dia = datetime(hoy.year, hoy.month, hoy.day)

            # Consultar ventas del día
            ventas_ref = (
                db.collection("ventas").where("fechaVenta", ">=", inicio_dia).stream()
            )

            # Calcular totales
            ventas_efectivo = 0
            ventas_tarjeta = 0

            for venta in ventas_ref:
                venta_data = venta.to_dict()
                if venta_data["metodoPago"] == "efectivo":
                    ventas_efectivo += float(venta_data["montoPagado"])
                else:
                    ventas_tarjeta += float(venta_data["montoPagado"])

            # Crear documento de cierre en Firebase
            cierre_data = {
                "fechaCierre": firestore.SERVER_TIMESTAMP,
                "montoEfectivo": ventas_efectivo,
                "montoTarjeta": ventas_tarjeta,
                "totalVentas": ventas_efectivo + ventas_tarjeta,
            }

            db.collection("cierres_caja").add(cierre_data)

            return JsonResponse({"success": True})

        except Exception as e:
            print(f"Error en cierre_caja: {str(e)}")
            return JsonResponse({"success": False, "error": str(e)})

    # Para GET request, mostrar el formulario
    try:
        db = get_db()
        hoy = datetime.now()
        inicio_dia = datetime(hoy.year, hoy.month, hoy.day)

        # Consultar ventas del día
        ventas_ref = (
            db.collection("ventas").where("fechaVenta", ">=", inicio_dia).stream()
        )

        ventas_efectivo = 0
        ventas_tarjeta = 0
        num_transacciones = 0

        for venta in ventas_ref:
            venta_data = venta.to_dict()
            if venta_data["metodoPago"] == "efectivo":
                ventas_efectivo += float(venta_data["montoPagado"])
            else:
                ventas_tarjeta += float(venta_data["montoPagado"])
            num_transacciones += 1

        context = {
            "efectivo": ventas_efectivo,
            "tarjeta": ventas_tarjeta,
            "total_ventas": ventas_efectivo + ventas_tarjeta,
            "num_transacciones": num_transacciones,
        }

        return render(request, "inventario/cierrecaja.html", context)

    except Exception as e:
        print(f"Error al cargar cierre_caja: {str(e)}")
        return render(
            request,
            "inventario/cierrecaja.html",
            {"error": "Error al cargar los datos"},
        )


@login_required
def historial_ventas(request):
    db = get_db()
    ventas_ref = (
        db.collection("ventas")
        .order_by("fechaVenta", direction=firestore.Query.DESCENDING)
        .stream()
    )

    ventas_lista = []
    for venta in ventas_ref:
        venta_dict = venta.to_dict()
        venta_dict["id"] = venta.id
        # El timestamp ya viene como DatetimeWithNanoseconds, no necesita conversión
        ventas_lista.append(venta_dict)

    print("Ventas desde Firebase:", ventas_lista)  # Para debug
    return render(request, "inventario/historial.html", {"ventas": ventas_lista})


@csrf_exempt
def finalizar_venta(request):
    if request.method == "POST":
        try:
            db = get_db()
            data = json.loads(request.body)
            productos = data.get("productos", [])
            metodoPago = data.get("metodoPago", "efectivo")

            if not productos:
                return JsonResponse(
                    {"success": False, "error": "No hay productos en el carrito"}
                )

            # Verificar stock en Firebase
            for producto in productos:
                prod_ref = db.collection("productos").document(producto["id"])
                prod_doc = prod_ref.get()

                if not prod_doc.exists:
                    return JsonResponse(
                        {"success": False, "error": f"Producto no encontrado"}
                    )

                prod_data = prod_doc.to_dict()
                if prod_data["stockActual"] < producto["cantidad"]:
                    return JsonResponse(
                        {
                            "success": False,
                            "error": f'Stock insuficiente para {prod_data["nombreProducto"]}',
                        }
                    )

            # Crear venta en Firebase
            venta_data = {
                "metodoPago": metodoPago,
                "montoPagado": sum(
                    float(p["precioVenta"]) * p["cantidad"] for p in productos
                ),
                "fechaVenta": firestore.SERVER_TIMESTAMP,
                "productos": productos,
            }

            # Guardar venta y actualizar stock
            venta_ref = db.collection("ventas").add(venta_data)

            # Actualizar stock de productos
            for producto in productos:
                prod_ref = db.collection("productos").document(producto["id"])
                prod_ref.update(
                    {"stockActual": firestore.Increment(-producto["cantidad"])}
                )

            return JsonResponse({"success": True})

        except Exception as e:
            print(f"Error en finalizar_venta: {str(e)}")
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Método no permitido"}, status=405)


def registrar_usuario(request):
    if request.method == "POST":
        rut = request.POST.get("rut")
        nombre = request.POST.get("nombre")
        apellidoPaterno = request.POST.get("apellidoPaterno")
        apellidoMaterno = request.POST.get("apellidoMaterno")
        email = request.POST.get("email")
        contraseña = request.POST.get("contraseña")
        rol = request.POST.get("rol")

        try:
            # Verificar si el email ya existe
            db = get_db()
            usuarios_ref = db.collection("usuarios")
            query = usuarios_ref.where("email", "==", email).get()

            if len(list(query)) > 0:
                return render(
                    request,
                    "inventario/inicio.html",
                    {
                        "error": "El email ya está registrado",
                        "FIREBASE_CONFIG": settings.FIREBASE_CONFIG,
                    },
                )

            # Guardar usuario directamente en Firestore
            usuario_data = {
                "rut": rut,
                "nombre": nombre,
                "apellidoPaterno": apellidoPaterno,
                "apellidoMaterno": apellidoMaterno,
                "rol": rol,
                "email": email,
                "contraseña": contraseña,  # Agregar contraseña
                "fechaCreacion": firestore.SERVER_TIMESTAMP,
            }

            # Guardar en Firestore
            nuevo_usuario = db.collection("usuarios").add(usuario_data)

            return render(
                request,
                "inventario/inicio.html",
                {
                    "success_message": f"Usuario {nombre} registrado exitosamente.",
                    "FIREBASE_CONFIG": settings.FIREBASE_CONFIG,
                },
            )

        except Exception as e:
            print(f"Error al registrar usuario: {str(e)}")
            return render(
                request,
                "inventario/inicio.html",
                {
                    "error": f"Error al registrar usuario: {str(e)}",
                    "FIREBASE_CONFIG": settings.FIREBASE_CONFIG,
                },
            )

    return render(
        request, "inventario/inicio.html", {"FIREBASE_CONFIG": settings.FIREBASE_CONFIG}
    )


@csrf_exempt
@require_http_methods(["GET", "POST"])
def iniciar_sesion(request):
    if request.method == "GET":
        return render(
            request,
            "inventario/inicio.html",
            {
                "FIREBASE_CONFIG": settings.FIREBASE_CONFIG,
                "es_usuario_autenticado": False,
            },
        )

    elif request.method == "POST":
        try:
            print("\n=== INICIO DE SESIÓN ===")
            data = json.loads(request.body)
            email = data.get("email")
            password = data.get("contraseña")

            print(f"Email recibido: {email}")

            # Autenticación con Django
            user = authenticate(username=email, password=password)

            if user is not None:
                login(request, user)

                # Determinar rol y redirección basado en grupos
                if user.groups.filter(name="cajeros").exists():
                    request.session["rol"] = "cajero"
                    request.session["user_id"] = user.id
                    redirect_url = "/inventario/ventas/"
                else:
                    request.session["rol"] = "admin"
                    request.session["user_id"] = user.id
                    redirect_url = "/inventario/admin/inventario/"

                print(f"Login exitoso - ID: {user.id}, Rol: {request.session['rol']}")
                print(f"Redirigiendo a: {redirect_url}")

                return JsonResponse(
                    {
                        "success": True,
                        "rol": request.session["rol"],
                        "redirect_url": redirect_url,
                    }
                )
            else:
                print("Credenciales inválidas")
                return JsonResponse(
                    {"success": False, "error": "Credenciales inválidas"}
                )

        except Exception as e:
            print(f"Error en inicio de sesión: {str(e)}")
            return JsonResponse({"success": False, "error": str(e)})


def cerrar_sesion(request):
    logout(request)  # Cierra la sesión del usuario
    return redirect("inventario:inicio")  # Redirige a la página de inicio


@login_required
def admin_dashboard(request):
    if request.session.get("rol") != "admin":
        return redirect("inicio")  # Redirigir si no es admin
    # Lógica para la vista del administrador


@login_required
def cajero_dashboard(request):
    if request.session.get("rol") != "cajero":
        return redirect("inicio")  # Redirigir si no es cajero
    # Lógica para la vista del cajero


@login_required
def admin_inventario(request):
    db = get_db()
    productos_ref = db.collection('productos').stream()
    categorias_ref = db.collection('categorias').stream()
    
    # Primero, crear un diccionario de categorías para búsqueda rápida
    categorias_dict = {}
    categorias = []
    
    for categoria in categorias_ref:
        cat_data = categoria.to_dict()
        cat_data['id'] = categoria.id
        categorias.append(cat_data)
        categorias_dict[categoria.id] = cat_data.get('nombreCategoria', '')
    
    # Luego, procesar los productos reemplazando IDs por nombres
    productos = []
    for producto in productos_ref:
        prod_dict = producto.to_dict()
        prod_dict['id'] = producto.id
        
        # Reemplazar el ID de categoría por su nombre
        categoria_id = prod_dict.get('nombreCategoria', '')
        prod_dict['nombreCategoria'] = categorias_dict.get(categoria_id, categoria_id)
        
        productos.append(prod_dict)
    
    return render(request, 'inventario/admin/inventario.html', {
        'productos': productos,
        'categorias': categorias
    })


@login_required
def admin_reportes(request):
    if request.session.get("rol") != "admin":
        return redirect("inicio")

    db = get_db()
    ventas = db.collection("ventas").get()
    productos = db.collection("productos").get()

    # Calcular totales
    total_ventas = sum(v.to_dict().get("montoPagado", 0) for v in ventas)
    productos_sin_stock = sum(
        1 for p in productos if p.to_dict().get("stockActual", 0) == 0
    )

    context = {
        "total_ventas": total_ventas,
        "productos_sin_stock": productos_sin_stock,
        "total_productos": len(list(productos)),
    }
    return render(request, "inventario/admin/reportes.html", context)


@login_required
def reporte_ventas(request):
    if request.session.get("rol") != "admin":
        return redirect("inicio")

    db = get_db()
    ventas = (
        db.collection("ventas")
        .order_by("fechaVenta", direction=firestore.Query.DESCENDING)
        .limit(30)
        .get()
    )

    ventas_lista = []
    for venta in ventas:
        venta_dict = venta.to_dict()
        venta_dict["id"] = venta.id
        ventas_lista.append(venta_dict)

    context = {"ventas": ventas_lista}
    return render(request, "inventario/admin/reporte_ventas.html", context)


@login_required
def nuevo_producto(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            db = get_db()
            
            # Obtener el nombre de la categoría seleccionada
            categoria_seleccionada = data['nombreCategoria']
            
            # Guardar directamente en Firestore con el nombre de la categoría
            doc_ref = db.collection('productos').add({
                'nombreProducto': data['nombreProducto'],
                'nombreCategoria': categoria_seleccionada,  # Guardamos el nombre directamente
                'costoProducto': float(data['costoProducto']),
                'precioVenta': float(data['precioVenta']),
                'stockActual': int(data['stockActual']),
                'stockUmbral': int(data['stockUmbral']),
                'imagen_url': data['imagen_url'],
                'fechaCreacion': firestore.SERVER_TIMESTAMP
            })
            
            return JsonResponse({'success': True, 'message': 'Producto agregado correctamente'})
            
        except Exception as e:
            print(f"Error al crear producto: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})


@login_required
def obtener_producto(request, producto_id):
    if request.session.get("rol") != "admin":
        return JsonResponse({"error": "No autorizado"}, status=403)

    db = get_db()
    producto = db.collection("productos").document(producto_id).get()

    if producto.exists:
        return JsonResponse(producto.to_dict() | {"id": producto.id})
    return JsonResponse({"error": "Producto no encontrado"}, status=404)


@csrf_exempt
def actualizar_sesion(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            email = data.get("email")
            print(f"Email recibido: {email}")  # Debug log

            db = get_db()
            usuarios_ref = (
                db.collection("usuarios").where("email", "==", email).limit(1).get()
            )

            for usuario in usuarios_ref:
                rol = usuario.to_dict().get("rol", "")
                print(f"Rol encontrado: {rol}")  # Debug log
                request.session["rol"] = rol
                return JsonResponse({"success": True, "rol": rol})

            return JsonResponse({"success": False, "error": "Usuario no encontrado"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Método no permitido"})


@login_required
def nueva_categoria(request):
    if request.session.get('rol') != 'admin':
        return redirect('inicio')
    
    if request.method == 'POST':
        try:
            categoria_data = {
                'nombreCategoria': request.POST.get('nombreCategoria'),
                'descripcion': request.POST.get('descripcion'),
                'fechaCreacion': firestore.SERVER_TIMESTAMP
            }
            
            db = get_db()
            db.collection('categorias').add(categoria_data)
            messages.success(request, 'Categoría creada exitosamente')
            
        except Exception as e:
            messages.error(request, f'Error al crear categoría: {str(e)}')
    
    return redirect('inventario:admin_inventario')


@login_required
@csrf_exempt
def actualizar_producto(request, producto_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            db = get_db()
            
            # Actualizar el producto en Firestore
            producto_ref = db.collection('productos').document(producto_id)
            producto_ref.update({
                'nombreProducto': data['nombreProducto'],
                'nombreCategoria': data['nombreCategoria'],
                'costoProducto': float(data['costoProducto']),
                'precioVenta': float(data['precioVenta']),
                'stockActual': int(data['stockActual']),
                'stockUmbral': int(data['stockUmbral']),
                'imagen_url': data.get('imagen_url', '')
            })
            
            return JsonResponse({'success': True, 'message': 'Producto actualizado correctamente'})
            
        except Exception as e:
            print(f"Error al actualizar producto: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})
