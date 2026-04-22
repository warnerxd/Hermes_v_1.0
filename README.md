# Sistema de Gestión de Vehículos — Hermes VPS

Aplicación web completa para registrar y gestionar vehículos con autenticación JWT, panel de administración, historial operativo y documentos de cumplimiento.

---

## Stack Tecnológico

| Capa | Tecnología |
|---|---|
| Backend | FastAPI 0.135 + Uvicorn |
| Base de datos | PostgreSQL 16 |
| ORM | SQLAlchemy 2.0 |
| Autenticación | JWT (PyJWT) + bcrypt |
| Frontend | HTML5, CSS3, JavaScript Vanilla |
| Contenedores | Docker + Docker Compose |
| Notificaciones | Twilio WhatsApp |- desactivado HTML recuperar_contrasena.html

---

## Instalación

Hay dos formas de correr el proyecto. Elije la que más se adapte a tu entorno.

---

### Opción A — Local con entorno virtual (sin Docker)

**Requisitos:** Git, Python 3.11+, PostgreSQL 15+

#### 1. Clonar el repositorio

```cmd
git clone https://github.com/warnerxd/Hermes_Vps.git
cd Hermes_Vps
```

#### 2. Crear el entorno virtual

```cmd
python -m venv venv_api
venv_api\Scripts\activate
```


> Si usás PowerShell y da error de permisos:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

#### 3. Instalar dependencias

```cmd
pip install -r requirements.txt
```

#### 4. Crear la base de datos en PostgreSQL

```cmd
psql -U postgres
```

```sql
CREATE DATABASE demo;
\q
```

#### 5. Configurar el archivo .env

```cmd
copy .env.example .env
```

Editá `.env` con tus datos: los datos son puramente para demo

```env
JWT_SECRET=clave_larga_y_aleatoria_para_produccion

DB_USER=postgres
DB_PASSWORD=TU_CONTRASEÑA_POSTGRES
DB_HOST=localhost
DB_PORT=5432
DB_NAME=demo

EMAIL_PROVIDER=gmail
EMAIL_ADDRESS=tu_correo@gmail.com
EMAIL_PASSWORD=tu_contraseña_app

TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_FROM=
N8N_WEBHOOK_NUEVO_VEHICULO=
```

> Twilio, email y N8N son opcionales para desarrollo local. mejoras futuras 

#### 6. Inicializar la base de datos

```cmd
python init_db.py
```

> Este comando borra y recrea todas las tablas. Usarlo solo la primera vez o para resetear datos.

#### 7. Iniciar el servidor

```cmd
uvicorn main:app --reload
```

---
>consultas sobre puesta en produccion en imagen de Nginex, cuento con proyecto adicional ya que las pruebas .
>se realizaron en un server con ubuntu y la opcion de implementacion A. 
---


### Opción B — Docker con contenedores separados (recomendado) para produccion 


#### Arquitectura

```
Red interna hermes_net
  ├── postgres (postgres:16-alpine) → volumen postgres_data
  └── app     (python:3.11-slim)   → expone puerto 8000
```

#### 1. Clonar el repositorio

```cmd
git clone https://github.com/warnerxd/Hermes_Vps.git
cd Hermes_Vps
```

#### 2. Configurar el archivo .env

```cmd
copy .env.example .env
```

Editá `.env` — el `DB_HOST` puede quedar como `localhost`, Docker lo sobreescribe internamente:

```env
JWT_SECRET=clave_larga_y_aleatoria_para_produccion

DB_USER=postgres
DB_PASSWORD=7826567
DB_HOST=localhost
DB_PORT=5432
DB_NAME=demo

TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_FROM=
N8N_WEBHOOK_NUEVO_VEHICULO=
```

#### 3. Construir y levantar los contenedores

```cmd
docker compose up -d --build
```

Docker levanta PostgreSQL primero, espera que esté up, luego levanta la app.

#### 4. Inicializar la base de datos

```cmd
docker compose exec app python init_db.py
```

#### 5. Verificar que todo esté corriendo

```cmd
docker compose exec postgres psql -U postgres -d demo -c "SELECT id, email, nombre, rol FROM usuarios;"
```

---

## Acceso a la Aplicación
 recomindo usar postman para validacion de cabeceras 

| URL | Descripción |
|---|---|
| `http://localhost:8000` | Aplicación principal |
| `http://localhost:8000/docs` | Swagger UI — API interactiva |
| `http://localhost:8000/redoc` | ReDoc — documentación alternativa |


>consultas sobre puesta en produccion en imagen de Nginex, cuento con proyecto adicional ya que las pruebas .
>se realizaron en un server con ubuntu y la opcion de implementacion A. 
---

## Usuarios de Prueba

| Email | Contraseña | Rol |
|---|---|---|
| `demo@demo.com` | `123456` | Usuario |
| `eduar.vargas@deprisa.com` | `123456` | Admin |


---

## Comandos Docker de Referencia

```cmd
# Levantar en segundo plano
docker compose up -d --build

# Ver logs en tiempo real
docker compose logs -f

# Ver logs solo de la app
docker compose logs -f app

# Detener contenedores (datos se conservan)
docker compose stop

# Detener y eliminar contenedores (datos en volumen se conservan)
docker compose down

# Resetear TODO incluyendo la base de datos
docker compose down -v

# Reiniciar solo la app
docker compose restart app

# Consola de PostgreSQL
docker compose exec postgres psql -U postgres -d demo

# Reinicializar datos de prueba
docker compose exec app python init_db.py
```

---

## Estructura del Proyecto

```
Hermes_Vps/
├── main.py                   # API FastAPI — todos los endpoints
├── models.py                 # Modelos SQLAlchemy
├── database.py               # Configuración de conexión PostgreSQL
├── init_db.py                # Script de inicialización y seed
├── twilio_config.py          # Configuración Twilio WhatsApp
├── Dockerfile                # Imagen Docker de la app
├── docker-compose.yml        # Orquestación de contenedores
├── requirements.txt          # Dependencias Python
├── .env.example              # Plantilla de variables de entorno
├── uploads/                  # PDFs subidos por usuarios
├── login.html
├── registro.html
├── index.html
├── admin.html
├── ver_vehiculos.html
├── crear_vehiculo.html
├── historial_vehiculos.html
└── recuperar_contrasena.html
```

---

## Tablas de la Base de Datos

| Tabla | Descripción |
|---|---|
| `usuarios` | Cuentas con roles admin/usuario |
| `vehiculos` | Registro de vehículos con documentos |
| `proveedores` | Empresas transportadoras |
| `historial_vehiculos` | Historial mensual operativo |
| `preoperacional_diario` | Lista de chequeo diaria |
| `historial_estado_vehiculo` | Auditoría de activaciones/desactivaciones |
| `tokens_recuperacion` | Tokens de recuperación de contraseña |
| `auditoria` | Registro inmutable de acciones admin |

---

### Documentos de Registro del Vehículo

Al registrar un vehículo se pueden adjuntar hasta 4 PDFs de cumplimiento:

| PDF | Descripción |
|---|---|
| `pdf_certificado_aliado` | Certificado de aliado |
| `pdf_certificado_latin` | Certificado Latin |
| `pdf_nit` | NIT de la empresa |
| `pdf_ruta` | Documento de ruta |

---

## Endpoints Principales

### Autenticación
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/auth/registro` | Registrar nuevo usuario |
| POST | `/auth/login` | Iniciar sesión |
| POST | `/auth/solicitar-recuperacion` | Solicitar reset de contraseña |
| POST | `/auth/resetear-contrasena` | Cambiar contraseña con código |

### Vehículos
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/vehiculos` | Crear vehículo |
| GET | `/vehiculos/{usuario_id}` | Vehículos de un usuario |
| PUT | `/vehiculos/{vehiculo_id}` | Actualizar vehículo |
| DELETE | `/vehiculos/{vehiculo_id}` | Eliminar vehículo |

### Historial y Preoperacional
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/historial-vehiculos` | Agregar registro mensual |
| GET | `/historial-vehiculos/{vehiculo_id}` | Historial de un vehículo |
| POST | `/preoperacional-diario` | Registrar checklist del día |
| GET | `/preoperacional-diario/{vehiculo_id}` | Historial de preoperacionales |

### Administración
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/admin/crear-usuario` | Crear usuario (admin) |
| GET | `/admin/todos-vehiculos` | Ver todos los vehículos |
| PUT | `/vehiculos/{id}/activar` | Aprobar vehículo |
| PUT | `/vehiculos/{id}/desactivar` | Desactivar vehículo |
| PUT | `/vehiculos/{id}/rechazar` | Rechazar con motivo |
| GET | `/admin/soat-alertas` | Vehículos con SOAT vencido o sin SOAT |
| GET | `/admin/preoperacional-alertas` | Vehículos activos sin preoperacional hoy |

---

## Solución de Problemas

**`ModuleNotFoundError` en local**
El entorno virtual no está activo: `venv_api\Scripts\activate`

**`could not connect to server` (PostgreSQL local)**
El servicio no está corriendo. Abrí `services.msc` y arrancá `postgresql-x64-16`.

**`password authentication failed`**
La contraseña en `.env` no coincide con la de PostgreSQL. Verificá `DB_PASSWORD`.

**`[WinError 10048]` — puerto en uso**
Cambiá el puerto: `uvicorn main:app --reload --port 8001`

**`database files are incompatible with server` (Docker)**
El volumen fue creado con otra versión de PostgreSQL:
```cmd
docker compose down -v
docker compose up -d --build
docker compose exec app python init_db.py
```

**`port is already allocated` — puerto 5432 ocupado**
PostgreSQL local ya usa ese puerto. Detené el servicio en `services.msc`.

**`no configuration file provided` al usar docker compose**
Estás en la carpeta equivocada. Siempre corré desde `C:\Users\skate\Documents\Hermes_Vps`.

**Los datos no aparecen en DBeaver**
Presioná **F5** o click derecho sobre la tabla → Refresh. DBeaver no se actualiza automáticamente.

**Los contenedores están detenidos**
`docker compose up -d` para levantarlos sin reconstruir.
