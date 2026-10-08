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
* Reprogramar la fecha objetivo de una gestión logística (US-06).
* Detectar conflicto por sobrecarga diaria al reprogramar (US-07), según el límite diario de horas de cada organizador (US-12).
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
PATCH  /api/subtareas/{id}/reprogramar/
```

### Reprogramar una gestión (US-06)

```text
PATCH  /api/subtareas/{id}/reprogramar/    { "plazo": "YYYY-MM-DD", "horas_estimadas"?: número }
```

Cambia la fecha objetivo y, si se envían, las horas estimadas (para reducirlas y resolver un conflicto de US-07); otros campos se ignoran. La nueva fecha debe ser válida y no anterior a hoy (sí se puede mover una gestión que ya está vencida).

* `200`: la gestión con la misma forma que en la vista "Hoy" (`{ id, evento, evento_titulo, nombre, plazo, horas_estimadas }`). Desde ese momento `GET /api/subtareas/hoy/` la devuelve en el grupo que le corresponde a su nueva fecha.
* `400`: `{ "detail": "No se pudo reprogramar.", "plazo": ["motivo"] }`. La fecha guardada no cambia.
* `404`: la gestión no existe o es de otro organizador.
* `409`: conflicto por sobrecarga diaria (US-07). No se guarda nada.

### Conflicto por sobrecarga diaria (US-07)

Al reprogramar se suman las horas de todas las gestiones del organizador (de todos sus eventos) con esa fecha, más las de la gestión que se mueve. Un día sin gestiones empieza en 0 h. Si el total **supera** el límite diario (llegar justo al límite está permitido), responde `409`:

```json
{
  "detail": "Quedarías con 7h de gestión planificadas (límite 6h)",
  "conflicto": {
    "fecha": "2026-10-13",
    "limite": "6.00",
    "planificadas": "5.00",
    "horas_gestion": "2.00",
    "total": "7.00",
    "horas_disponibles": "1.00",
    "siguiente_dia_disponible": "2026-10-14",
    "gestiones_del_dia": [{ "id": 4, "evento": 1, "evento_titulo": "Boda Ana y Luis", "nombre": "Reservar salón", "plazo": "2026-10-13", "horas_estimadas": "5.00" }]
  }
}
```

Datos para resolverlo:

* **Mover a otro día**: volver a llamar con otra fecha.
* **Reducir horas estimadas**: `horas_disponibles` es lo máximo que cabe ese día (0 si ya está lleno). Se envía en `horas_estimadas` junto con la misma fecha.
* **Posponer**: `siguiente_dia_disponible` es el primer día después del elegido en el que la gestión cabe. Es `null` si la gestión sola ya supera el límite.

### Límite diario (US-12)

```text
GET    /api/configuracion/    -> { "limite_horas_diarias": "6.00", "por_defecto": true }
PATCH  /api/configuracion/    { "limite_horas_diarias": 4 }
```

Cada organizador tiene su propio límite de horas de gestión por día, y US-07 usa siempre el del organizador autenticado. Si nunca lo guardó vale 6 h y `por_defecto` es `true` (consultarlo no guarda nada).

El límite debe estar **entre 1 y 16 horas**, ambos incluidos, con máximo 2 decimales. Si no lo está, no se guarda y responde `400`: `{ "limite_horas_diarias": ["El límite debe estar entre 1 y 16 horas."] }`. El mismo rango se aplica al cambiarlo desde `/admin/`.

### Vista "Hoy" (US-04 y US-05)

```text
GET    /api/subtareas/hoy/
```

Devuelve las gestiones del organizador autenticado agrupadas según su plazo respecto a hoy (zona horaria `America/Bogota`):

```json
{
  "fecha": "2026-10-02",
  "vencidas": [{ "id": 4, "evento": 1, "evento_titulo": "Boda Ana y Luis", "nombre": "Pagar DJ", "plazo": "2026-09-30", "horas_estimadas": "2.00" }],
  "hoy": [],
  "proximas": []
}
```

* **vencidas**: plazo anterior a hoy. **hoy**: plazo igual a hoy. **proximas**: plazo posterior a hoy.
* Dentro de cada grupo: plazo más cercano primero; si coinciden, la de menos horas estimadas.

Filtros opcionales (se pueden combinar y no cambian el orden):

* `evento=<id>`: solo las gestiones de ese evento.
* `estado=vencidas|hoy|proximas`: solo ese grupo; los demás llegan vacíos.
* `dias=<n>`: limita las próximas a las que vencen en los próximos `n` días.

Un filtro no válido (estado desconocido, `dias` menor que 1, evento inexistente o de otro organizador) responde `400` con el error en ese campo.

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
