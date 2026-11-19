"""
Comando para generar datos de prueba (mínimo 10 equipos, 5 usuarios, 15 préstamos).
Uso: python manage.py seed_data
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import Usuario, Laboratorio, Equipo, Prestamo


class Command(BaseCommand):
    help = 'Genera datos de prueba para el sistema de préstamos'

    def handle(self, *args, **options):
        self.stdout.write('🌱 Generando datos de prueba...')

        # Usuarios
        admin, _ = Usuario.objects.get_or_create(
            username='admin', defaults={
                'email': 'admin@uncp.edu.pe', 'rol': 'admin',
                'first_name': 'Jorge', 'last_name': 'Labrador',
                'codigo_uncp': '20200001', 'is_staff': True, 'is_superuser': True
            }
        )
        admin.set_password('admin123')
        admin.save()

        asistente, _ = Usuario.objects.get_or_create(
            username='asistente', defaults={
                'email': 'asistente@uncp.edu.pe', 'rol': 'asistente',
                'first_name': 'María', 'last_name': 'Ramos',
                'codigo_uncp': '20200002'
            }
        )
        asistente.set_password('asist123')
        asistente.save()

        docentes_data = [
            ('docente1', 'Carlos', 'Huamán', '20200010'),
            ('docente2', 'Ana', 'Quispe', '20200011'),
            ('docente3', 'Luis', 'Mendoza', '20200012'),
        ]
        docentes = []
        for uname, fn, ln, cod in docentes_data:
            d, _ = Usuario.objects.get_or_create(
                username=uname, defaults={
                    'email': f'{uname}@uncp.edu.pe', 'rol': 'docente',
                    'first_name': fn, 'last_name': ln, 'codigo_uncp': cod
                }
            )
            d.set_password('doc123')
            d.save()
            docentes.append(d)

        # Laboratorios
        labs_data = [
            ('LAB-01', 'Laboratorio de Redes', 'Pab. A - 2do piso'),
            ('LAB-02', 'Laboratorio de Software', 'Pab. A - 3er piso'),
            ('LAB-03', 'Laboratorio de IoT', 'Pab. B - 1er piso'),
        ]
        labs = []
        for cod, nom, ubi in labs_data:
            lab, _ = Laboratorio.objects.get_or_create(
                codigo=cod, defaults={'nombre': nom, 'ubicacion': ubi, 'responsable': admin}
            )
            labs.append(lab)

        # Equipos (mínimo 10)
        equipos_data = [
            ('EQ-001', 'Laptop Dell Latitude', 'Dell', 'Latitude 5520', 'laptop', labs[0]),
            ('EQ-002', 'Laptop HP ProBook', 'HP', 'ProBook 450', 'laptop', labs[0]),
            ('EQ-003', 'Proyector Epson', 'Epson', 'PowerLite X49', 'proyector', labs[1]),
            ('EQ-004', 'Cámara Canon', 'Canon', 'EOS M50', 'camara', labs[1]),
            ('EQ-005', 'Kit Arduino Uno', 'Arduino', 'Uno R3', 'arduino', labs[2]),
            ('EQ-006', 'Router Cisco', 'Cisco', 'RV340', 'router', labs[0]),
            ('EQ-007', 'Switch TP-Link', 'TP-Link', 'TL-SG1024', 'switch', labs[0]),
            ('EQ-008', 'Laptop Lenovo', 'Lenovo', 'ThinkPad E14', 'laptop', labs[1]),
            ('EQ-009', 'Kit Arduino Mega', 'Arduino', 'Mega 2560', 'arduino', labs[2]),
            ('EQ-010', 'Proyector Sony', 'Sony', 'VPL-X4001', 'proyector', labs[2]),
            ('EQ-011', 'Laptop Asus', 'Asus', 'VivoBook 15', 'laptop', labs[1]),
            ('EQ-012', 'Cámara GoPro', 'GoPro', 'Hero 11', 'camara', labs[2]),
        ]
        equipos = []
        for cod, nom, marca, modelo, cat, lab in equipos_data:
            eq, _ = Equipo.objects.get_or_create(
                codigo_patrimonial=cod, defaults={
                    'nombre': nom, 'marca': marca, 'modelo': modelo,
                    'categoria': cat, 'estado': 'operativo', 'laboratorio': lab,
                    'ultimo_mantenimiento': (timezone.now() - timedelta(days=60)).date()
                }
            )
            equipos.append(eq)

        # Préstamos (mínimo 15)
        Prestamo.objects.all().delete()
        now = timezone.now()
        prestamos_data = [
            (docentes[0], equipos[0], 'activo', -5),
            (docentes[0], equipos[1], 'devuelto', -10),
            (docentes[0], equipos[2], 'vencido', -15),
            (docentes[1], equipos[3], 'activo', -3),
            (docentes[1], equipos[4], 'devuelto', -20),
            (docentes[1], equipos[5], 'activo', -7),
            (docentes[2], equipos[6], 'devuelto', -30),
            (docentes[2], equipos[7], 'activo', -2),
            (docentes[2], equipos[8], 'vencido', -25),
            (docentes[0], equipos[9], 'devuelto', -40),
            (docentes[1], equipos[10], 'activo', -1),
            (docentes[2], equipos[11], 'devuelto', -15),
            (docentes[0], equipos[3], 'activo', -4),
            (docentes[1], equipos[7], 'devuelto', -50),
            (docentes[2], equipos[1], 'activo', -6),
        ]
        for doc, eq, est, dias in prestamos_data:
            fecha_p = now + timedelta(days=dias)
            fecha_d = fecha_p + timedelta(days=7)
            fecha_real = fecha_d - timedelta(days=1) if est == 'devuelto' else None
            Prestamo.objects.create(
                docente=doc, equipo=eq, cantidad=1,
                fecha_prestamo=fecha_p,
                fecha_devolucion_esperada=fecha_d,
                fecha_devolucion_real=fecha_real,
                estado=est,
                registrado_por=asistente,
                observaciones='Préstamo de prueba'
            )

        self.stdout.write(self.style.SUCCESS(
            f'✅ Datos creados:\n'
            f'  - {Usuario.objects.count()} usuarios\n'
            f'  - {Laboratorio.objects.count()} laboratorios\n'
            f'  - {Equipo.objects.count()} equipos\n'
            f'  - {Prestamo.objects.count()} préstamos\n\n'
            f'🔑 Credenciales:\n'
            f'  admin / admin123\n'
            f'  asistente / asist123\n'
            f'  docente1 / doc123\n'
            f'  docente2 / doc123\n'
            f'  docente3 / doc123'
        ))