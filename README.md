# Flask Multi Auth Example - API

> **Aviso:** este proyecto es **codigo de ejemplo** con fines didacticos. Puede contener errores, simplificaciones o decisiones de diseno discutibles. Si se usa como base para un trabajo practico u otro entregable, **debe adaptarse a las buenas practicas y consignas especificas de la materia/catedra** (estilo de codigo, manejo de errores, validaciones, tests, estructura, etc.).

## Motivacion

Este proyecto es el **backend** (API REST) de un ejemplo integrador que muestra como construir una autenticacion **con multiples flujos**:

1. **Registro** con email + password.
2. **Login clasico** con email + password.
3. **Olvido de password**: el usuario pide un link, lo recibe por email y elige un nuevo password.
4. **Login passwordless**: en lugar de password, el usuario pide un **codigo numerico de un solo uso** que le llega por email y lo ingresa para iniciar sesion.

Ademas, los endpoints sensibles estan protegidos con **reCAPTCHA v2** (validado server-side contra Google).

La API **no envia emails ni renderiza templates**: se limita a generar los tokens/codigos, guardarlos en la base con sus hashes correspondientes y devolver el valor crudo al frontend para que sea el frontend el que arme y envie el email (porque alli viven los templates Jinja).

## Arquitectura

```
  Frontend (flask-multi-auth-example-web, puerto 5001)
     |
     |  requests.post(JSON) con recaptcha_token, email, password/codigo, ...
     v
  Flask API (este proyecto, puerto 5000)
     |
     +--> Google reCAPTCHA (verificacion del token)
     |
     v
  MySQL (usuarios, password_reset_tokens, login_codes)
```

## Estructura del proyecto

```
flask-multi-auth-example-api/
├── app.py                              # Entry point Flask (puerto 5000)
├── requirements.txt                    # Dependencias Python
├── .env.example                        # Variables de entorno de ejemplo
├── docker-compose.yml                  # MySQL 8 con init_db.sql montado
├── db/
│   └── init_db.sql                     # DDL: usuarios + password_reset_tokens + login_codes
├── docs/
│   └── swagger.yaml                    # Documentacion OpenAPI 3.0 de la API
└── flask_multi_auth_example/
    ├── constants.py                    # URLs, claves JWT, recaptcha, error codes
    ├── db.py                           # Queries SQLAlchemy
    ├── utils.py                        # Errores, validaciones, JWT, bcrypt, recaptcha
    ├── routes/
    │   ├── auth.py                     # /register /login /password-reset/* /login-code/*
    │   └── usuarios.py                 # /me
    ├── services/
    │   ├── auth.py                     # Logica de los 4 flujos de autenticacion
    │   └── usuarios.py
    └── validators/
        └── auth.py                     # Validacion de cada body
```

## Documentacion (Swagger / OpenAPI)

La especificacion completa de la API en formato OpenAPI 3.0 vive en
[`docs/swagger.yaml`](docs/swagger.yaml). Incluye el esquema `BearerAuth` para los
endpoints protegidos por JWT y todos los schemas de request/response (con ejemplos
de body para captcha, tokens de reset y codigos de login). Se puede visualizar de
varias formas:

- Pegando el contenido del archivo en [editor.swagger.io](https://editor.swagger.io).
- Abriendolo con la extension "Swagger Viewer" (o similar) en VSCode.
- Sirviendolo con cualquier renderer compatible con OpenAPI 3.

## Requisitos previos

- Python 3.10+
- **Una** de las dos opciones para correr MySQL:
  - Docker + Docker Compose (recomendado), o
  - Una instalacion local de MySQL 8
- Una **clave secret de reCAPTCHA v2** generada en <https://www.google.com/recaptcha/admin> (o usar las claves de test de Google en desarrollo)

## Configuracion

### 1. Variables de entorno

Copiar `.env.example` a `.env` (los defaults ya funcionan para desarrollo local):

```bash
cp .env.example .env
```

```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=root
DB_NAME=multi_auth

JWT_SECRET=change-me-please
JWT_EXP_HORAS=8

RECAPTCHA_SECRET=change-me-please
RECAPTCHA_DISABLED=false
```

> **Importante:** en cualquier ambiente que no sea desarrollo local, definir un `JWT_SECRET` propio y largo. Es la clave con la que se firman todos los tokens.

> **Sobre `RECAPTCHA_DISABLED`:** si esta en `true`, la API saltea la verificacion del captcha (util para tests automatizados o cuando todavia no se generaron las claves). **No usar en produccion.**

### 2. Base de datos MySQL

Eleg **una** de las dos opciones segun lo que tengas instalado.

#### Opcion A: con Docker (recomendado)

`docker-compose.yml` levanta MySQL 8 y monta `db/init_db.sql` como script de inicializacion, creando las tablas `usuarios`, `password_reset_tokens` y `login_codes` automaticamente la **primera** vez:

```bash
docker compose up -d
```

Verificar que el contenedor este listo (puede tardar unos segundos):

```bash
docker compose logs -f mysql
# Buscar la linea: "ready for connections"
```

Apagar el contenedor manteniendo los datos en el volumen:

```bash
docker compose down
```

Apagar y **borrar** los datos (la proxima vez se vuelve a correr `init_db.sql`):

```bash
docker compose down -v
```

#### Opcion B: con MySQL instalado localmente

Si ya tenes MySQL 8 corriendo en tu maquina (puerto `3306` por default):

1. Crear la base de datos y cargar el esquema:

   ```bash
   # Linux / macOS / WSL
   mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS multi_auth;"
   mysql -u root -p multi_auth < db/init_db.sql
   ```

   ```powershell
   # Windows PowerShell
   mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS multi_auth;"
   Get-Content db\init_db.sql | mysql -u root -p multi_auth
   ```

2. Verificar que las tablas se hayan creado:

   ```bash
   mysql -u root -p -e "USE multi_auth; SHOW TABLES;"
   ```

   Deberias ver: `usuarios`, `password_reset_tokens`, `login_codes`.

3. Si tu usuario, password, puerto o nombre de base no coinciden con los defaults, actualiza el `.env` antes de levantar la API.

### 3. Entorno virtual, instalacion y ejecucion

El proyecto incluye scripts de setup que crean el entorno virtual, instalan las dependencias y levantan la API.

**Con virtualenv:**

```bash
# Windows
setup_virtualenv.bat

# Linux / macOS
chmod +x setup_virtualenv.sh
./setup_virtualenv.sh
```

**Con pipenv:**

```bash
# Windows
setup_pipenv.bat

# Linux / macOS
chmod +x setup_pipenv.sh
./setup_pipenv.sh
```

Una vez iniciada, la API estara disponible en `http://localhost:5000/flask_multi_auth_example_api`.

### 4. Crear el primer usuario

La tabla `usuarios` arranca vacia. Para crear el primer usuario (con `RECAPTCHA_DISABLED=true` para no tener que generar un token valido):

```bash
curl -X POST http://localhost:5000/flask_multi_auth_example_api/register \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","nombre":"Alice","password":"clave-de-8-o-mas","recaptcha_token":""}'
```

> En condiciones normales el frontend resuelve el captcha por vos y manda el token resuelto en `recaptcha_token`. Ver el README del web para el flujo completo.

## Endpoints

Todos los endpoints estan bajo el prefijo `/flask_multi_auth_example_api`. Las respuestas son JSON; los errores siguen el formato:

```json
{
    "errors": [
        {
            "code": "<codigo>",
            "message": "<mensaje breve>",
            "level": "error",
            "description": "<descripcion detallada>"
        }
    ]
}
```

| Metodo | Endpoint                     | Auth | Descripcion                                                       |
|--------|------------------------------|------|-------------------------------------------------------------------|
| POST   | `/register`                  | -    | Crea un usuario nuevo (captcha)                                   |
| POST   | `/login`                     | -    | Login con email + password (captcha) → devuelve JWT               |
| POST   | `/password-reset/request`    | -    | Pide reseteo de password (captcha) → devuelve token al frontend   |
| POST   | `/password-reset/confirm`    | -    | Cambia el password usando el token recibido por email             |
| POST   | `/login-code/request`        | -    | Pide un codigo de login (captcha) → devuelve codigo al frontend   |
| POST   | `/login-code/verify`         | -    | Canjea el codigo por un JWT                                       |
| GET    | `/me`                        | JWT  | Devuelve el usuario autenticado                                   |

### `POST /register`

```bash
curl -X POST http://localhost:5000/flask_multi_auth_example_api/register \
  -H "Content-Type: application/json" \
  -d '{
        "email":           "alice@example.com",
        "nombre":          "Alice",
        "password":        "una-clave-secreta",
        "recaptcha_token": "03AGdBq25..."
      }'
```

Respuesta `201 Created`:

```json
{ "id": 1, "email": "alice@example.com", "nombre": "Alice" }
```

Posibles errores: `400` (body invalido / captcha invalido), `409` (email ya registrado).

### `POST /login`

```bash
curl -X POST http://localhost:5000/flask_multi_auth_example_api/login \
  -H "Content-Type: application/json" \
  -d '{
        "email":           "alice@example.com",
        "password":        "una-clave-secreta",
        "recaptcha_token": "03AGdBq25..."
      }'
```

Respuesta `200 OK`:

```json
{ "token": "eyJ...", "usuario": { "id": 1, "email": "...", "nombre": "..." } }
```

Posibles errores: `400` (captcha invalido), `401` (credenciales invalidas).

### `POST /password-reset/request`

```bash
curl -X POST http://localhost:5000/flask_multi_auth_example_api/password-reset/request \
  -H "Content-Type: application/json" \
  -d '{ "email": "alice@example.com", "recaptcha_token": "03AGdBq25..." }'
```

Respuesta `200 OK`:

```json
{
  "token":     "Yzg5...",
  "expira_en": "2026-05-27T01:30:00+00:00",
  "usuario":   { "id": 1, "email": "...", "nombre": "..." }
}
```

> **Nota didactica:** la API devuelve el `token` al cliente para que el frontend pueda armar la URL del email. En un sistema "puro" el backend mandaria el email el mismo y nunca expondria el token al cliente. La decision aca es consciente: el web tiene los templates Jinja y dispara el envio, la API solo orquesta los datos.

Posibles errores: `400` (captcha invalido), `404` (email no registrado; el frontend lo traduce a un mensaje neutro).

### `POST /password-reset/confirm`

```bash
curl -X POST http://localhost:5000/flask_multi_auth_example_api/password-reset/confirm \
  -H "Content-Type: application/json" \
  -d '{ "token": "Yzg5...", "password": "nueva-clave" }'
```

Respuesta `200 OK`:

```json
{ "usuario": { "id": 1, "email": "...", "nombre": "..." } }
```

Posibles errores: `400` (token invalido, expirado o ya usado).

### `POST /login-code/request`

```bash
curl -X POST http://localhost:5000/flask_multi_auth_example_api/login-code/request \
  -H "Content-Type: application/json" \
  -d '{ "email": "alice@example.com", "recaptcha_token": "03AGdBq25..." }'
```

Respuesta `200 OK`:

```json
{
  "codigo":    "473201",
  "expira_en": "2026-05-27T01:10:00+00:00",
  "usuario":   { "id": 1, "email": "...", "nombre": "..." }
}
```

Posibles errores: `400` (captcha invalido), `404` (email no registrado).

### `POST /login-code/verify`

```bash
curl -X POST http://localhost:5000/flask_multi_auth_example_api/login-code/verify \
  -H "Content-Type: application/json" \
  -d '{ "email": "alice@example.com", "codigo": "473201" }'
```

Respuesta `200 OK`:

```json
{ "token": "eyJ...", "usuario": { "id": 1, "email": "...", "nombre": "..." } }
```

Posibles errores: `400` (codigo invalido, expirado o ya usado).

### `GET /me`

```bash
curl http://localhost:5000/flask_multi_auth_example_api/me \
  -H "Authorization: Bearer <token>"
```

Respuesta `200 OK`:

```json
{ "id": 1, "email": "alice@example.com", "nombre": "Alice" }
```

Posibles errores: `401` (token faltante, invalido o expirado), `404` (usuario no encontrado).

## Patron de queries literales

Este proyecto usa SQLAlchemy **sin ORM**, ejecutando SQL directamente con `text()`:

```python
from sqlalchemy import create_engine, text

motor = create_engine(DB_URL)

# SELECT
with motor.connect() as conexion:
    resultado = conexion.execute(text(sql), {'email': 'alice@example.com'})

# INSERT/UPDATE/DELETE (con commit automatico)
with motor.begin() as conexion:
    resultado = conexion.execute(text(sql), parametros)
```

Ver `flask_multi_auth_example/db.py` para todos los ejemplos.

## Patron de autenticacion

- El **password** se hashea con `bcrypt` antes de guardarlo (`utils.hashear_password`). bcrypt es lento por diseno y resistente a fuerza bruta.
- Los **reset tokens** y los **login codes** se guardan con **SHA-256** del valor crudo (`utils.hashear_token`). No usamos bcrypt aca porque son valores random de alta entropia y se comparan por igualdad exacta de hash, no por verificacion lenta.
- En el login se compara el password recibido contra el hash con `bcrypt.checkpw` (`utils.verificar_password`).
- Si las credenciales son validas, se genera un JWT (`utils.generar_jwt`) con:
  - `sub`: id del usuario
  - `exp`: expiracion en `JWT_EXP_HORAS` horas
- Los endpoints protegidos usan el decorador `@requiere_auth()` de `utils.py`, que:
  1. extrae el token del header `Authorization: Bearer <token>`,
  2. lo decodifica y valida con el `JWT_SECRET`,
  3. inyecta el payload en `request.usuario_actual` para que la vista lo use.
- Cuando se genera un token/codigo nuevo del mismo usuario, todos los anteriores **vigentes** se marcan como usados, para que no convivan multiples links/codigos activos.

Toda la auth es **stateless**: la API no guarda sesiones; cada request se valida con el JWT.

## Patron de reCAPTCHA

`utils.validar_recaptcha(token)` hace un POST a `https://www.google.com/recaptcha/api/siteverify` con `RECAPTCHA_SECRET` y el token recibido del frontend. Si Google rechaza el token, se devuelve un 400 con `code: recaptcha.invalid`.

El frontend renderiza el widget con la `RECAPTCHA_SITE_KEY` (publica), obtiene el `g-recaptcha-response` cuando el usuario completa el desafio y lo manda en el body como `recaptcha_token`. **La validacion contra Google la hace siempre la API**, nunca el web, porque:

- El token de reCAPTCHA es **de un solo uso**. Si lo validara primero el web, el segundo intento de validacion (en la API) fallaria.
- La API es el limite real de seguridad: si solo lo validara el web, un atacante podria pegar directo contra los endpoints `/register`, `/login`, etc.

## Glosario de terminos

- **API REST**: estilo de arquitectura para servicios web que expone recursos via HTTP (GET, POST, PUT, DELETE) usando JSON como formato de intercambio.
- **Endpoint**: ruta concreta de la API (por ejemplo `POST /login`) que responde a un metodo HTTP y realiza una accion sobre un recurso.
- **Request / Response**: par de mensajes HTTP. La **request** es lo que envia el cliente; la **response** es lo que devuelve el servidor.
- **Status code**: codigo numerico de la respuesta HTTP. Por ejemplo: `200 OK`, `201 Created`, `400 Bad Request`, `401 Unauthorized`, `404 Not Found`, `409 Conflict`.
- **Bearer token**: esquema de autenticacion HTTP donde el JWT viaja en el header `Authorization: Bearer <token>`.
- **JSON**: formato de texto para representar datos estructurados.
- **Flask**: micro framework web de Python.
- **Frontend**: aplicacion que renderiza las paginas HTML y consume la API. Corre en el puerto 5001 (`flask-multi-auth-example-web`).
- **Backend / API**: servicio HTTP REST (este proyecto). Corre en el puerto 5000.
- **Blueprint (Flask)**: mecanismo de Flask para agrupar rutas relacionadas en modulos.
- **Decorador (`@requiere_auth`)**: funcion de Python que envuelve a otra para agregarle comportamiento. Aca se usa para exigir un JWT valido antes de ejecutar la vista.
- **Autenticacion**: proceso de verificar **quien** es el usuario.
- **Autorizacion**: proceso de verificar **que** puede hacer el usuario autenticado.
- **JWT (JSON Web Token)**: token firmado que contiene informacion del usuario. La API lo emite en el login y el cliente lo envia en cada request protegida.
- **Claim**: cada uno de los campos dentro del payload de un JWT (`sub` = subject/id, `exp` = expiracion, etc.).
- **Stateless**: la API **no** guarda sesiones; cada request se autentica de cero validando el JWT.
- **`JWT_SECRET`**: clave secreta con la que se firman y verifican los tokens.
- **Hashing**: transformacion **unidireccional** de un valor en una cadena de longitud fija. No se puede revertir.
- **bcrypt**: algoritmo de hashing pensado para passwords. Incluye un **salt** aleatorio y un factor de costo configurable.
- **SHA-256**: hash criptografico rapido. Aca se usa para los reset tokens y login codes porque son valores random de alta entropia.
- **Salt**: valor aleatorio que se mezcla con la password antes de hashearla para que dos passwords iguales generen hashes distintos.
- **Token de reset**: cadena random de un solo uso enviada por email para autorizar el cambio de password.
- **Login code / OTP (One-Time Password)**: codigo numerico corto, de un solo uso, enviado por email como alternativa al password.
- **Passwordless**: estrategia de autenticacion en la que el usuario no usa password; en su lugar prueba que controla un canal (email, SMS, app) recibiendo un codigo o link.
- **reCAPTCHA v2**: widget de Google con la opcion "No soy un robot". Genera un token que el cliente manda al servidor; el servidor lo valida contra Google.
- **Site key / Secret key**: par de claves que genera Google para cada dominio. La **site key** es publica (la usa el frontend); el **secret** es privado y solo lo conoce el backend.
- **SQLAlchemy**: libreria de Python para hablar con bases SQL. Aca se usa **sin ORM**, ejecutando SQL literal con `text()`.
- **ORM (Object Relational Mapper)**: capa que mapea tablas a clases/objetos. Este proyecto **no** lo usa para mantener el SQL explicito.
- **Query parametrizada**: query SQL en la que los valores se pasan como parametros (`:email`) y no concatenados al string, evitando **SQL injection**.
- **SQL injection**: vulnerabilidad por la que un atacante inyecta SQL malicioso a traves de inputs no sanitizados.
- **Migracion / esquema**: definicion de la estructura de la base (tablas, columnas). Aca vive en `db/init_db.sql`.
- **Docker / Docker Compose**: herramientas para correr servicios (en este caso MySQL) en contenedores aislados.
- **Contenedor**: instancia en ejecucion de una imagen Docker.
- **Volumen (Docker)**: almacenamiento persistente del contenedor; permite hacer `down` sin perder los datos.
- **`.env` / variables de entorno**: archivo con configuracion sensible que **no** se commitea al repo. `.env.example` es la plantilla.
- **Entorno virtual**: directorio aislado con la version de Python y las dependencias del proyecto.
- **virtualenv / `venv`**: herramienta estandar de Python para crear entornos virtuales. Dependencias en `requirements.txt`.
- **pipenv**: alternativa que combina entorno virtual + dependencias en un solo flujo (`Pipfile` y `Pipfile.lock`).
- **`pip`**: gestor de paquetes de Python.
- **CORS (Cross-Origin Resource Sharing)**: mecanismo del navegador que controla que dominios pueden consumir la API.
- **Validator**: funcion que valida el body de la request y devuelve un dict limpio o levanta un error API.
- **Service**: capa con la logica de negocio. Vive en `services/` y es invocada desde las routes.
- **DTO (Data Transfer Object)**: estructura usada para pasar datos entre capas. En este proyecto se modelan como `dict` de Python.
