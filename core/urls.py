from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    # Autenticación
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    # Equipos
    path('equipos/', views.equipo_list, name='equipo_list'),
    path('equipos/nuevo/', views.equipo_create, name='equipo_create'),
    path('equipos/<int:pk>/editar/', views.equipo_edit, name='equipo_edit'),
    path('equipos/<int:pk>/eliminar/', views.equipo_delete, name='equipo_delete'),
    # Préstamos
    path('prestamos/', views.prestamo_list, name='prestamo_list'),
    path('prestamos/nuevo/', views.prestamo_create, name='prestamo_crear'),
    path('prestamos/mis-prestamos/', views.mis_prestamos, name='mis_prestamos'),
    path('prestamos/<int:pk>/devolver/', views.prestamo_devolver, name='prestamo_devolver'),
    # Auditoría
    path('auditoria/', views.auditoria_logs, name='auditoria_logs'),
]