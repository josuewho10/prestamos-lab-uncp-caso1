# 🖥️ Sistema de Gestión de Préstamos de Equipos de Laboratorio - UNCP

**Desarrollo de Aplicaciones Web - Semana 12 (CASO 1)**  
Universidad Nacional del Centro del Perú - Facultad de Ingeniería de Sistemas

## 👥 Integrantes

- **Integrante 1:** Andrade Egoavil Ingrid
- **Integrante 2:** Yaranga Ruiz Josue

## 🎯 Descripción

Sistema web para la gestión digital de préstamos de equipos de laboratorio, con control de usuarios por roles, auditoría completa y validaciones avanzadas.

## 🚀 Instalación

```bash
# Clonar repositorio
git clone <URL>
cd prestamos_lab

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt

# Migraciones
python manage.py makemigrations
python manage.py migrate

# Datos de prueba
python manage.py seed_data

# Ejecutar
python manage.py runserver
```
