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
* Registrarse, iniciar y cerrar sesión con usuario y contraseña (US-11); cada organizador solo ve sus propios eventos y gestiones.
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

Los organizadores crean su cuenta desde el registro del frontend (`/registro`). Para entrar a `/admin/` hace falta un superusuario:

```powershell
python manage.py createsuperuser
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

### Autenticación (US-11)

```text
POST   /api/auth/registro/  { nombre, username, password } -> 201 { token, usuario: { id, username, nombre } }
POST   /api/auth/login/     { username, password } -> { token, usuario: { id, username, nombre } }
POST   /api/auth/logout/    invalida el token actual
```

El registro guarda el usuario en la tabla de usuarios de Django (`auth_user`), con la contraseña cifrada, y deja la sesión iniciada. Responde `400` con `{ campo: ["mensaje"] }` si falta un dato, si el usuario ya existe (sin distinguir mayúsculas) o si la contraseña no cumple las reglas de `AUTH_PASSWORD_VALIDATORS`: mínimo 8 caracteres, no muy común, no solo números y no parecida al usuario o al nombre.

El resto de la API exige la cabecera `Authorization: Token <token>`; sin ella responde `401`. Cada organizador solo ve y modifica sus propios eventos y gestiones: los de otro responden `404`, como si no existieran. Si el usuario o la contraseña no son correctos, el login responde `400` con `{ "detail": "Credenciales inválidas." }`, sin indicar cuál de los dos falló.

Los eventos creados antes de esta versión no tienen organizador y no aparecen para nadie. Para recuperarlos hay que asignarles un organizador desde `/admin/` (Eventos → campo *Organizador*).

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
