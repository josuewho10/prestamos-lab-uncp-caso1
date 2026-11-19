"""
Decoradores para control de acceso por rol (RF3).
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from .models import LogAuditoria


def rol_requerido(*roles_permitidos):
    """
    Decorador que restringe vistas a roles específicos.
    Uso: @rol_requerido('admin', 'asistente')
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.rol not in roles_permitidos and not request.user.is_superuser:
                # Registrar intento de acceso no autorizado
                LogAuditoria.objects.create(
                    usuario=request.user,
                    accion='ACCESO_DENEGADO',
                    descripcion=f"Rol '{request.user.rol}' intentó acceder a {request.path}",
                    ip_address=request.META.get('REMOTE_ADDR'),
                    ruta=request.path
                )
                messages.error(request, 'No tiene permisos para acceder a esta sección.')
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def admin_requerido(view_func):
    """Solo administradores."""
    return rol_requerido('admin')(view_func)


def asistente_o_admin(view_func):
    """Asistentes o administradores."""
    return rol_requerido('asistente', 'admin')(view_func)


def docente_o_asistente_o_admin(view_func):
    """Cualquier rol autenticado."""
    return rol_requerido('docente', 'asistente', 'admin')(view_func)