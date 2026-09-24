# Organizador de Eventos Independientes — Backend

API REST desarrollada para gestionar eventos y sus gestiones logísticas dentro del proyecto Organizador de Eventos Independientes.

## Tecnologías

* Python
* Django
* Django REST Framework
* PostgreSQL
* Supabase
* drf-spectacular (Swagger / OpenAPI)
* django-cors-headers

## Funcionalidades

* Crear, consultar, actualizar y eliminar eventos.
* Crear gestiones logísticas asociadas a un evento.
* Consultar las gestiones de un evento.
* Actualizar y eliminar gestiones logísticas.
* Validar los datos recibidos por la API.
* Validar que las horas estimadas de una gestión sean mayores que 0.
* Persistir la información en PostgreSQL.
* Documentar la API mediante Swagger/OpenAPI.

## Estructura principal

```text
organizador-eventos-backend/
├── config/
│   ├── settings.py
│   └── urls.py
├── eventos/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── migrations/
├── manage.py
├── requirements.txt
└── README.md
```

## Instalación

Crear y activar el entorno virtual:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Instalar las dependencias:

```powershell
pip install -r requirements.txt
```

Aplicar las migraciones:

```powershell
python manage.py migrate
```

## Ejecución

Iniciar el servidor de desarrollo:

```powershell
python manage.py runserver
```

La API estará disponible en:

```text
http://127.0.0.1:8000/
```

## API

Los principales recursos disponibles son:

### Eventos

```text
GET    /api/eventos/
POST   /api/eventos/
GET    /api/eventos/{id}/
PUT    /api/eventos/{id}/
PATCH  /api/eventos/{id}/
DELETE /api/eventos/{id}/
```

### Gestiones logísticas

```text
GET    /api/eventos/{id}/subtareas/
POST   /api/eventos/{id}/subtareas/
GET    /api/subtareas/
POST   /api/subtareas/
GET    /api/subtareas/{id}/
PUT    /api/subtareas/{id}/
PATCH  /api/subtareas/{id}/
DELETE /api/subtareas/{id}/
```

## Documentación de la API

La API cuenta con documentación interactiva mediante Swagger:

```text
http://127.0.0.1:8000/api/docs/
```

También se puede consultar el esquema OpenAPI:

```text
http://127.0.0.1:8000/api/schema/
```

## Base de datos

El proyecto utiliza PostgreSQL como sistema gestor de base de datos. La base de datos se encuentra alojada mediante Supabase.

No se deben incluir credenciales, contraseñas ni variables de entorno sensibles dentro del repositorio.

## Integración con el Frontend

El Backend proporciona los servicios REST consumidos por el Frontend desarrollado en React.

La comunicación permite realizar el flujo:

**React → API REST Django → PostgreSQL/Supabase → API REST → React**

Esto permite que los eventos y gestiones logísticas creados desde la aplicación queden almacenados de forma persistente.

## Proyecto académico

Proyecto desarrollado como parte del Proyecto Integrador de Desarrollo de Software para la gestión y planificación de eventos independientes.
