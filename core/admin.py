"""
Django Admin personalizado (RF5).
Incluye list_display, list_filter, search_fields, acciones masivas, campos calculados.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse
from .models import Usuario, Laboratorio, Equipo, Prestamo, LogAuditoria


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'get_full_name', 'rol', 'is_active', 'fecha_creacion')
    list_filter = ('rol', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'codigo_uncp')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Información UNCP', {'fields': ('rol', 'codigo_uncp', 'telefono')}),
    )


@admin.register(Laboratorio)
class LaboratorioAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'ubicacion', 'responsable')
    search_fields = ('codigo', 'nombre')


@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = (
        'codigo_patrimonial', 'nombre', 'marca', 'modelo',
        'categoria', 'color_estado', 'laboratorio', 'dias_mantenimiento'
    )
    list_filter = ('estado', 'categoria', 'laboratorio')
    search_fields = ('codigo_patrimonial', 'nombre', 'marca', 'modelo')
    actions = ['marcar_mantenimiento', 'marcar_operativo']

    @admin.display(description='Estado')
    def color_estado(self, obj):
        colores = {'operativo': '#28a745', 'mantenimiento': '#ffc107', 'baja': '#dc3545'}
        return format_html(
            '<span style="background:{}; color:white; padding:4px 10px; border-radius:4px;">{}</span>',
            colores.get(obj.estado, '#6c757d'), obj.get_estado_display()
        )

    @admin.display(description='Días desde mant.')
    def dias_mantenimiento(self, obj):
        dias = obj.dias_desde_mantenimiento
        if dias is None:
            return '—'
        color = '#dc3545' if dias > 180 else '#ffc107' if dias > 90 else '#28a745'
        return format_html('<span style="color:{}; font-weight:bold;">{} días</span>', color, dias)

    @admin.action(description='Marcar seleccionados como EN MANTENIMIENTO')
    def marcar_mantenimiento(self, request, queryset):
        count = queryset.update(estado='mantenimiento')
        self.message_user(request, f'{count} equipo(s) marcado(s) en mantenimiento.')

    @admin.action(description='Marcar seleccionados como OPERATIVO')
    def marcar_operativo(self, request, queryset):
        count = queryset.update(estado='operativo')
        self.message_user(request, f'{count} equipo(s) marcado(s) como operativos.')


@admin.register(Prestamo)
class PrestamoAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'docente', 'equipo', 'fecha_prestamo',
        'fecha_devolucion_esperada', 'estado_badge', 'dias_retraso_display'
    )
    list_filter = ('estado', 'fecha_prestamo', 'docente')
    search_fields = ('equipo__codigo_patrimonial', 'docente__username', 'docente__first_name')
    actions = ['enviar_recordatorio']
    readonly_fields = ('fecha_prestamo',)

    @admin.display(description='Estado')
    def estado_badge(self, obj):
        colores = {'activo': '#0d6efd', 'devuelto': '#28a745', 'vencido': '#dc3545'}
        return format_html(
            '<span style="background:{}; color:white; padding:4px 10px; border-radius:4px;">{}</span>',
            colores.get(obj.estado, '#6c757d'), obj.get_estado_display()
        )

    @admin.display(description='Días de Retraso', ordering='fecha_devolucion_esperada')
    def dias_retraso_display(self, obj):
        dias = obj.dias_retraso
        if dias > 0:
            return format_html('<span style="color:#dc3545; font-weight:bold;">{} días</span>', dias)
        return '—'

    @admin.action(description='📧 Enviar recordatorio de devolución')
    def enviar_recordatorio(self, request, queryset):
        activos = queryset.filter(estado__in=['activo', 'vencido'])
        count = activos.count()
        self.message_user(
            request,
            f'Se enviaría recordatorio a {count} docente(s). (Simulado)'
        )


@admin.register(LogAuditoria)
class LogAuditoriaAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'usuario', 'accion', 'ip_address', 'ruta')
    list_filter = ('accion', 'fecha')
    search_fields = ('usuario__username', 'descripcion', 'ip_address')
    readonly_fields = ('usuario', 'accion', 'descripcion', 'ip_address', 'fecha', 'ruta')
    date_hierarchy = 'fecha'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False