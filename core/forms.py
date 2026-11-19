"""
Formularios con validaciones avanzadas (RF2).
Incluye clean(), clean_<campo>(), sanitización y validaciones cruzadas.
"""
import re
from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Equipo, Prestamo, Usuario


class EquipoForm(forms.ModelForm):
    """Formulario para crear/editar equipos (RF1)."""

    class Meta:
        model = Equipo
        fields = [
            'codigo_patrimonial', 'nombre', 'marca', 'modelo',
            'categoria', 'estado', 'laboratorio', 'descripcion',
            'fecha_adquisicion', 'ultimo_mantenimiento'
        ]
        widgets = {
            'fecha_adquisicion': forms.DateInput(attrs={'type': 'date'}),
            'ultimo_mantenimiento': forms.DateInput(attrs={'type': 'date'}),
            'descripcion': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_codigo_patrimonial(self):
        """Validación: código patrimonial con formato válido."""
        codigo = self.cleaned_data.get('codigo_patrimonial', '').strip().upper()
        if not re.match(r'^[A-Z0-9\-]{3,30}$', codigo):
            raise ValidationError(
                'El código patrimonial solo puede contener letras, números y guiones (3-30 caracteres).'
            )
        return codigo

    def clean_nombre(self):
        """Sanitización del nombre."""
        nombre = self.cleaned_data.get('nombre', '').strip()
        nombre = re.sub(r'<[^>]+>', '', nombre)  # Elimina HTML
        if len(nombre) < 3:
            raise ValidationError('El nombre debe tener al menos 3 caracteres.')
        return nombre

    def clean_ultimo_mantenimiento(self):
        """Validación: fecha de mantenimiento no puede ser futura."""
        fecha = self.cleaned_data.get('ultimo_mantenimiento')
        if fecha and fecha > timezone.now().date():
            raise ValidationError('La fecha de último mantenimiento no puede ser futura.')
        return fecha


class PrestamoForm(forms.ModelForm):
    """
    Formulario de solicitud de préstamo (RF2).
    Validaciones:
    - Docente no puede tener más de 3 préstamos activos
    - Fecha devolución > fecha préstamo
    - Equipo debe estar operativo
    - Stock disponible vs cantidad solicitada
    """

    class Meta:
        model = Prestamo
        fields = ['docente', 'equipo', 'cantidad', 'fecha_devolucion_esperada', 'observaciones']
        widgets = {
            'fecha_devolucion_esperada': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'observaciones': forms.Textarea(attrs={'rows': 3}),
            'docente': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Solo mostrar equipos operativos
        self.fields['equipo'].queryset = Equipo.objects.filter(estado='operativo')
        # Solo mostrar docentes
        self.fields['docente'].queryset = Usuario.objects.filter(rol='docente')
        # Si es docente, limitar a sí mismo
        if self.user and self.user.rol == 'docente':
            self.fields['docente'].queryset = Usuario.objects.filter(pk=self.user.pk)
            self.fields['docente'].initial = self.user

    def clean_observaciones(self):
        """Sanitización de comentarios (RF2)."""
        obs = self.cleaned_data.get('observaciones', '')
        obs = re.sub(r'<[^>]+>', '', obs)  # Elimina HTML
        obs = obs.strip()
        if len(obs) > 500:
            raise ValidationError('Las observaciones no pueden exceder 500 caracteres.')
        return obs

    def clean_fecha_devolucion_esperada(self):
        """Validación: fecha de devolución debe ser posterior a la actual."""
        fecha_dev = self.cleaned_data.get('fecha_devolucion_esperada')
        if fecha_dev and fecha_dev <= timezone.now():
            raise ValidationError('La fecha de devolución debe ser posterior a la fecha actual.')
        return fecha_dev

    def clean(self):
        """Validaciones cruzadas (RF2)."""
        cleaned_data = super().clean()
        docente = cleaned_data.get('docente')
        equipo = cleaned_data.get('equipo')
        cantidad = cleaned_data.get('cantidad', 1)

        # Validación 1: Docente no puede tener más de 3 préstamos activos
        if docente:
            prestamos_activos = Prestamo.objects.filter(
                docente=docente, estado__in=['activo', 'vencido']
            ).count()
            if prestamos_activos >= 3:
                raise ValidationError(
                    f'El docente {docente.get_full_name()} ya tiene {prestamos_activos} '
                    'préstamos activos. Máximo permitido: 3.'
                )

        # Validación 2: Equipo debe estar operativo
        if equipo and equipo.estado != 'operativo':
            raise ValidationError(
                f'El equipo "{equipo.nombre}" no está disponible '
                f'(estado actual: {equipo.get_estado_display()}).'
            )

        # Validación 3: Validación cruzada de stock (simplificada a 1 unidad por equipo)
        if equipo and cantidad > 1:
            raise ValidationError('Solo se puede solicitar 1 unidad por equipo.')

        return cleaned_data


class DevolucionForm(forms.ModelForm):
    """Formulario de devolución con registro de estado (RF2)."""

    class Meta:
        model = Prestamo
        fields = ['estado_equipo_retorno', 'observaciones_devolucion']
        widgets = {
            'observaciones_devolucion': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_observaciones_devolucion(self):
        """Sanitización de observaciones."""
        obs = self.cleaned_data.get('observaciones_devolucion', '')
        obs = re.sub(r'<[^>]+>', '', obs)
        return obs.strip()