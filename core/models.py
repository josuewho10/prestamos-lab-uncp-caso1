"""
Modelos del Sistema de Gestión de Préstamos de Equipos de Laboratorio.
UNCP - Facultad de Ingeniería de Sistemas
"""
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.urls import reverse


class Usuario(AbstractUser):
    """
    Modelo de usuario personalizado con roles (RF3).
    Roles: admin, docente, asistente
    """
    ROL_CHOICES = (
        ('admin', 'Administrador (Jefe de Laboratorio)'),
        ('docente', 'Docente'),
        ('asistente', 'Asistente'),
    )
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default='docente')
    codigo_uncp = models.CharField(max_length=20, unique=True, blank=True, null=True)
    telefono = models.CharField(max_length=15, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_rol_display()})"

    @property
    def es_admin(self):
        return self.rol == 'admin' or self.is_superuser

    @property
    def es_docente(self):
        return self.rol == 'docente'

    @property
    def es_asistente(self):
        return self.rol == 'asistente'


class Laboratorio(models.Model):
    """Laboratorios de cómputo de la facultad."""
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=20, unique=True)
    ubicacion = models.CharField(max_length=200)
    responsable = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='laboratorios_responsables'
    )

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Equipo(models.Model):
    """
    Equipos del laboratorio (RF1).
    Estados: operativo, mantenimiento, baja
    """
    ESTADO_CHOICES = (
        ('operativo', 'Operativo'),
        ('mantenimiento', 'En Mantenimiento'),
        ('baja', 'Dado de Baja'),
    )
    CATEGORIA_CHOICES = (
        ('laptop', 'Laptop'),
        ('proyector', 'Proyector'),
        ('camara', 'Cámara'),
        ('arduino', 'Kit Arduino'),
        ('router', 'Router'),
        ('switch', 'Switch'),
        ('otro', 'Otro'),
    )

    codigo_patrimonial = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=150)
    marca = models.CharField(max_length=100)
    modelo = models.CharField(max_length=100)
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='operativo')
    laboratorio = models.ForeignKey(
        Laboratorio, on_delete=models.PROTECT, related_name='equipos'
    )
    descripcion = models.TextField(blank=True)
    fecha_adquisicion = models.DateField(null=True, blank=True)
    ultimo_mantenimiento = models.DateField(null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Equipo'
        verbose_name_plural = 'Equipos'
        ordering = ['codigo_patrimonial']

    def __str__(self):
        return f"[{self.codigo_patrimonial}] {self.nombre} - {self.marca} {self.modelo}"

    @property
    def dias_desde_mantenimiento(self):
        """Campo calculado: días desde el último mantenimiento."""
        if self.ultimo_mantenimiento:
            return (timezone.now().date() - self.ultimo_mantenimiento).days
        return None

    @property
    def color_estado(self):
        """Estado visual con colores (RF1)."""
        colores = {
            'operativo': 'success',
            'mantenimiento': 'warning',
            'baja': 'danger',
        }
        return colores.get(self.estado, 'secondary')


class Prestamo(models.Model):
    """
    Préstamo de equipos (RF2).
    Estados: activo, devuelto, vencido
    """
    ESTADO_CHOICES = (
        ('activo', 'Activo'),
        ('devuelto', 'Devuelto'),
        ('vencido', 'Vencido'),
    )

    docente = models.ForeignKey(
        Usuario, on_delete=models.PROTECT,
        related_name='prestamos', limit_choices_to={'rol': 'docente'}
    )
    equipo = models.ForeignKey(Equipo, on_delete=models.PROTECT, related_name='prestamos')
    cantidad = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    fecha_prestamo = models.DateTimeField(auto_now_add=True)
    fecha_devolucion_esperada = models.DateTimeField()
    fecha_devolucion_real = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activo')
    estado_equipo_retorno = models.CharField(
        max_length=20, choices=Equipo.ESTADO_CHOICES,
        blank=True, null=True,
        help_text="Estado del equipo al momento de la devolución"
    )
    observaciones = models.TextField(blank=True, help_text="Observaciones del préstamo")
    observaciones_devolucion = models.TextField(blank=True)
    registrado_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True,
        related_name='prestamos_registrados'
    )

    class Meta:
        verbose_name = 'Préstamo'
        verbose_name_plural = 'Préstamos'
        ordering = ['-fecha_prestamo']

    def __str__(self):
        return f"Préstamo #{self.pk} - {self.equipo} a {self.docente}"

    @property
    def dias_retraso(self):
        """Campo calculado: días de retraso (RF5)."""
        if self.estado in ('activo', 'vencido'):
            if timezone.now() > self.fecha_devolucion_esperada:
                return (timezone.now() - self.fecha_devolucion_esperada).days
        return 0

    @property
    def esta_vencido(self):
        return self.estado == 'activo' and timezone.now() > self.fecha_devolucion_esperada

    def save(self, *args, **kwargs):
        # Actualiza automáticamente el estado a "vencido" si corresponde
        if self.estado == 'activo' and self.esta_vencido:
            self.estado = 'vencido'
        super().save(*args, **kwargs)


class LogAuditoria(models.Model):
    """Registro de auditoría para acciones críticas (RF4)."""
    ACCION_CHOICES = (
        ('PRESTAMO_CREADO', 'Préstamo Creado'),
        ('PRESTAMO_DEVUELTO', 'Préstamo Devuelto'),
        ('EQUIPO_CREADO', 'Equipo Registrado'),
        ('EQUIPO_MODIFICADO', 'Equipo Modificado'),
        ('EQUIPO_ELIMINADO', 'Equipo Eliminado'),
        ('LOGIN', 'Inicio de Sesión'),
        ('LOGOUT', 'Cierre de Sesión'),
        ('ACCESO_DENEGADO', 'Acceso No Autorizado'),
    )

    usuario = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True
    )
    accion = models.CharField(max_length=30, choices=ACCION_CHOICES)
    descripcion = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    ruta = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'Log de Auditoría'
        verbose_name_plural = 'Logs de Auditoría'
        ordering = ['-fecha']

    def __str__(self):
        return f"[{self.fecha}] {self.usuario} - {self.get_accion_display()}"