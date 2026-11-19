"""
Middlewares personalizados (RF4):
- SessionTimeoutMiddleware: timeout de 30 minutos
- AuditoriaMiddleware: registra acciones críticas
- PrestamosVencidosMiddleware: alerta de préstamos vencidos
"""
import logging
from django.utils import timezone
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from .models import LogAuditoria, Prestamo

logger = logging.getLogger(__name__)


class SessionTimeoutMiddleware:
    """
    Cierra la sesión tras 30 minutos de inactividad (RF3).
    Aprovecha SESSION_SAVE_EVERY_REQUEST de settings.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            last_activity = request.session.get('last_activity')
            if last_activity:
                elapsed = (timezone.now().timestamp() - last_activity)
                if elapsed > 1800:  # 30 minutos
                    from django.contrib.auth import logout
                    logout(request)
                    messages.warning(request, 'Su sesión ha expirado por inactividad.')
                    return redirect('login')
            request.session['last_activity'] = timezone.now().timestamp()
        return self.get_response(request)


class AuditoriaMiddleware:
    """
    Registra acciones críticas: préstamos, devoluciones, eliminaciones (RF4).
    También registra intentos de acceso no autorizado.
    """

    ACCIONES_POR_RUTA = {
        'prestamo_crear': 'PRESTAMO_CREADO',
        'prestamo_devolver': 'PRESTAMO_DEVUELTO',
        'equipo_crear': 'EQUIPO_CREADO',
        'equipo_editar': 'EQUIPO_MODIFICADO',
        'equipo_eliminar': 'EQUIPO_ELIMINADO',
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Registrar acceso denegado (403 o redirección a login por falta de permisos)
        if request.user.is_authenticated and response.status_code == 403:
            self._registrar(
                request, 'ACCESO_DENEGADO',
                f"Intento de acceso a {request.path}"
            )

        # Registrar acciones críticas en POST
        if request.method == 'POST' and request.user.is_authenticated:
            ruta_nombre = request.resolver_match.url_name if request.resolver_match else ''
            if ruta_nombre in self.ACCIONES_POR_RUTA:
                accion = self.ACCIONES_POR_RUTA[ruta_nombre]
                self._registrar(
                    request, accion,
                    f"{accion} en {request.path}"
                )

        return response

    def _registrar(self, request, accion, descripcion):
        ip = self._get_client_ip(request)
        LogAuditoria.objects.create(
            usuario=request.user if request.user.is_authenticated else None,
            accion=accion,
            descripcion=descripcion,
            ip_address=ip,
            ruta=request.path
        )
        logger.info(f"[AUDITORÍA] {accion} - {request.user} - IP: {ip}")

    @staticmethod
    def _get_client_ip(request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class PrestamosVencidosMiddleware:
    """
    Verifica si el usuario tiene préstamos vencidos al iniciar sesión y muestra alerta (RF4).
    Solo muestra la alerta una vez por sesión.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.rol == 'docente':
            # Mostrar alerta solo una vez por sesión
            if not request.session.get('alerta_vencidos_mostrada'):
                prestamos_vencidos = Prestamo.objects.filter(
                    docente=request.user, estado='vencido'
                ).count()
                if prestamos_vencidos > 0:
                    messages.warning(
                        request,
                        f'⚠️ Tiene {prestamos_vencidos} préstamo(s) vencido(s). '
                        'Por favor regularice su situación.'
                    )
                    request.session['alerta_vencidos_mostrada'] = True
        return self.get_response(request)