"""
Vistas del sistema (RF2, RF3).
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from .models import Equipo, Prestamo, Laboratorio, LogAuditoria
from .forms import EquipoForm, PrestamoForm, DevolucionForm
from .decorators import admin_requerido, asistente_o_admin, docente_o_asistente_o_admin


# ============================================================
# AUTENTICACIÓN (RF3)
# ============================================================
def login_view(request):
    """Login con credenciales institucionales UNCP."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            LogAuditoria.objects.create(
                usuario=user, accion='LOGIN',
                descripcion='Inicio de sesión exitoso',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f'¡Bienvenido, {user.get_full_name() or user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Credenciales inválidas. Intente nuevamente.')

    return render(request, 'registration/login.html')


def logout_view(request):
    """Logout con registro de auditoría."""
    if request.user.is_authenticated:
        LogAuditoria.objects.create(
            usuario=request.user, accion='LOGOUT',
            descripcion='Cierre de sesión',
            ip_address=request.META.get('REMOTE_ADDR')
        )
    logout(request)
    messages.info(request, 'Ha cerrado sesión correctamente.')
    return redirect('login')


# ============================================================
# DASHBOARD
# ============================================================
def dashboard(request):
    """Panel principal según rol. Invitados van al catálogo público."""
    # RF3: Invitado solo puede ver catálogo (lectura)
    if not request.user.is_authenticated:
        return redirect('equipo_list')

    context = {}
    if request.user.es_admin:
        context['total_equipos'] = Equipo.objects.count()
        context['equipos_operativos'] = Equipo.objects.filter(estado='operativo').count()
        context['prestamos_activos'] = Prestamo.objects.filter(estado='activo').count()
        context['prestamos_vencidos'] = Prestamo.objects.filter(estado='vencido').count()
        context['logs_recientes'] = LogAuditoria.objects.all()[:10]
    elif request.user.es_asistente:
        context['prestamos_activos'] = Prestamo.objects.filter(estado='activo').count()
        context['prestamos_vencidos'] = Prestamo.objects.filter(estado='vencido').count()
    else:  # docente
        context['mis_prestamos'] = Prestamo.objects.filter(docente=request.user)
        context['prestamos_activos'] = context['mis_prestamos'].filter(estado='activo').count()
        context['prestamos_vencidos'] = context['mis_prestamos'].filter(estado='vencido').count()
    return render(request, 'core/dashboard.html', context)


# ============================================================
# GESTIÓN DE EQUIPOS (RF1)
# ============================================================
def equipo_list(request):
    """
    Listado de equipos con búsqueda y filtros (RF1).
    Accesible para Invitados (solo lectura), pero acciones restringidas.
    """
    # Optimización con select_related para evitar N+1 queries (RNF)
    equipos = Equipo.objects.select_related('laboratorio').all()

    # Búsqueda
    q = request.GET.get('q', '')
    if q:
        equipos = equipos.filter(
            Q(codigo_patrimonial__icontains=q) |
            Q(nombre__icontains=q) |
            Q(categoria__icontains=q)
        )

    # Filtros
    laboratorio = request.GET.get('laboratorio')
    if laboratorio:
        equipos = equipos.filter(laboratorio_id=laboratorio)

    estado = request.GET.get('estado')
    if estado:
        equipos = equipos.filter(estado=estado)

    context = {
        'equipos': equipos,
        'laboratorios': Laboratorio.objects.all(),
        'q': q,
        'estado_seleccionado': estado,
        'lab_seleccionado': laboratorio,
    }
    return render(request, 'core/equipo_list.html', context)


@admin_requerido
def equipo_create(request):
    """Crear equipo (solo admin)."""
    if request.method == 'POST':
        form = EquipoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Equipo registrado correctamente.')
            return redirect('equipo_list')
    else:
        form = EquipoForm()
    return render(request, 'core/equipo_form.html', {'form': form, 'titulo': 'Registrar Equipo'})


@admin_requerido
def equipo_edit(request, pk):
    """Editar equipo (solo admin)."""
    equipo = get_object_or_404(Equipo, pk=pk)
    if request.method == 'POST':
        form = EquipoForm(request.POST, instance=equipo)
        if form.is_valid():
            form.save()
            messages.success(request, 'Equipo actualizado correctamente.')
            return redirect('equipo_list')
    else:
        form = EquipoForm(instance=equipo)
    return render(request, 'core/equipo_form.html', {'form': form, 'titulo': 'Editar Equipo'})


@admin_requerido
def equipo_delete(request, pk):
    """Eliminar equipo (solo admin) - RF3."""
    equipo = get_object_or_404(Equipo, pk=pk)
    if request.method == 'POST':
        equipo.delete()
        messages.success(request, 'Equipo eliminado correctamente.')
        return redirect('equipo_list')
    return render(request, 'core/equipo_confirm_delete.html', {'equipo': equipo})


# ============================================================
# SISTEMA DE PRÉSTAMOS (RF2)
# ============================================================
@login_required
def prestamo_create(request):
    """Solicitar préstamo (docente) o registrar (asistente/admin)."""
    if request.method == 'POST':
        form = PrestamoForm(request.POST, user=request.user)
        if form.is_valid():
            prestamo = form.save(commit=False)
            prestamo.registrado_por = request.user
            prestamo.save()
            messages.success(request, 'Préstamo registrado correctamente.')
            return redirect('mis_prestamos' if request.user.es_docente else 'prestamo_list')
    else:
        form = PrestamoForm(user=request.user)
    return render(request, 'core/prestamo_form.html', {'form': form})


@login_required
def prestamo_list(request):
    """Listado de préstamos (visión según rol)."""
    prestamos = Prestamo.objects.select_related('docente', 'equipo', 'equipo__laboratorio')
    if request.user.es_docente:
        prestamos = prestamos.filter(docente=request.user)

    estado = request.GET.get('estado')
    if estado:
        prestamos = prestamos.filter(estado=estado)

    context = {'prestamos': prestamos, 'estado_seleccionado': estado}
    return render(request, 'core/prestamo_list.html', context)


@login_required
def mis_prestamos(request):
    """Docentes ven solo sus préstamos (RF3)."""
    prestamos = Prestamo.objects.filter(docente=request.user).select_related('equipo')
    context = {'prestamos': prestamos}
    return render(request, 'core/mis_prestamos.html', context)


@asistente_o_admin
def prestamo_devolver(request, pk):
    """Registrar devolución (solo asistente/admin) - RF3."""
    prestamo = get_object_or_404(Prestamo, pk=pk, estado__in=['activo', 'vencido'])
    if request.method == 'POST':
        form = DevolucionForm(request.POST, instance=prestamo)
        if form.is_valid():
            p = form.save(commit=False)
            p.estado = 'devuelto'
            p.fecha_devolucion_real = timezone.now()
            # Actualizar estado del equipo si cambió
            if p.estado_equipo_retorno and p.estado_equipo_retorno != p.equipo.estado:
                p.equipo.estado = p.estado_equipo_retorno
                p.equipo.save()
            p.save()
            messages.success(request, 'Devolución registrada correctamente.')
            return redirect('prestamo_list')
    else:
        form = DevolucionForm(instance=prestamo)
    return render(request, 'core/prestamo_devolucion.html', {'form': form, 'prestamo': prestamo})


# ============================================================
# AUDITORÍA (RF4)
# ============================================================
@admin_requerido
def auditoria_logs(request):
    """Logs accesibles solo para administradores (RNF)."""
    logs = LogAuditoria.objects.select_related('usuario').all()[:100]
    return render(request, 'core/auditoria.html', {'logs': logs})


# ============================================================
# CSRF FAILURE VIEW
# ============================================================
def csrf_failure(request, reason=""):
    """Vista personalizada para errores CSRF."""
    return render(request, 'core/csrf_error.html', {'reason': reason}, status=403)