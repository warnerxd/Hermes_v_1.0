from fastapi import FastAPI, Depends, File, UploadFile, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt as pyjwt
from pydantic import BaseModel
from typing import Optional, List
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from dotenv import load_dotenv
import os
import shutil

load_dotenv()
from sqlalchemy.orm import Session
from database import engine, get_db, Base
from models import UsuarioDB, VehiculoDB, ProveedorDB, HistorialVehiculoDB, TokenRecuperacionDB, PreoperacionalDiarioDB, HistorialEstadoVehiculoDB
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

def hoy_colombia():
    """Fecha actual en zona horaria Colombia (UTC-5)."""
    return datetime.now(ZoneInfo("America/Bogota")).date()
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import bcrypt
import requests

# ==================== Configuración de Email ====================
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "gmail")
EMAIL_ADDRESS  = os.getenv("EMAIL_ADDRESS",  "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
SMTP_CONFIG = {
    "gmail":   {"server": "smtp.gmail.com",      "port": 587},
    "outlook": {"server": "smtp.office365.com",  "port": 587},
    "hotmail": {"server": "smtp.office365.com",  "port": 587},
    "yahoo":   {"server": "smtp.mail.yahoo.com", "port": 587},
    "zoho":    {"server": "smtp.zoho.com",        "port": 587},
    "custom":  {"server": "smtp.tu-dominio.com",  "port": 587},
}
_cfg = SMTP_CONFIG.get(EMAIL_PROVIDER, SMTP_CONFIG["custom"])
SMTP_SERVER = _cfg["server"]
SMTP_PORT   = _cfg["port"]

# ==================== Contexto para hashear contraseñas ====================
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    if not hashed.startswith("$2b$"):
        return password == hashed
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# ==================== JWT ====================
JWT_SECRET = os.getenv("JWT_SECRET", "cambia_esta_clave_secreta_en_produccion")
JWT_ALGORITHM = "HS256"
JWT_EXP_HOURS = 24
_bearer = HTTPBearer()

def crear_token(usuario_id: int, email: str, rol: str) -> str:
    from datetime import timezone
    payload = {
        "sub": str(usuario_id),
        "email": email,
        "rol": rol,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXP_HOURS),
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def _decode_token(token: str) -> dict:
    try:
        return pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

def get_usuario_actual(credentials: HTTPAuthorizationCredentials = Security(_bearer)) -> dict:
    return _decode_token(credentials.credentials)

def get_admin_actual(credentials: HTTPAuthorizationCredentials = Security(_bearer)) -> dict:
    payload = _decode_token(credentials.credentials)
    if payload.get("rol") != "admin":
        raise HTTPException(status_code=403, detail="Acceso solo para administradores")
    return payload


def notificar_nuevo_vehiculo(datos_vehiculo: dict, db=None):
    """Notifica a todos los admins con teléfono registrado vía WhatsApp, y al webhook n8n si está configurado."""
    # 1. WhatsApp a todos los admins con teléfono
    if db is not None:
        try:
            from twilio_config import enviar_whatsapp
            admins = db.query(UsuarioDB).filter(
                UsuarioDB.rol == "admin",
                UsuarioDB.telefono != None
            ).all()
            mensaje = (
                f"🚛 Nueva placa pendiente de revisión:\n"
                f"Placa: {datos_vehiculo.get('placa')}\n"
                f"Proveedor: {datos_vehiculo.get('proveedor')}\n"
                f"Marca/Modelo: {datos_vehiculo.get('marca')} {datos_vehiculo.get('modelo')}\n"
                f"Registrado por: {datos_vehiculo.get('nombre')} ({datos_vehiculo.get('usuario_email')})"
            )
            for admin in admins:
                resultado = enviar_whatsapp(admin.telefono, mensaje)
                print(f"Notificación admin {admin.email}: {resultado}")
        except Exception as e:
            print(f"Error notificando admins por WhatsApp: {e}")

    # 2. Webhook n8n (opcional, se mantiene por compatibilidad)
    webhook_url = os.getenv("N8N_WEBHOOK_NUEVO_VEHICULO", "")
    try:
        if webhook_url:
            requests.post(webhook_url, json=datos_vehiculo, timeout=2)
    except Exception as e:
        print(f"Error al notificar a n8n: {e}")


def generar_codigo():
    """Generar código de 6 dígitos aleatorio"""
    return ''.join(random.choices(string.digits, k=6))

def enviar_email_recuperacion(destinatario: str, codigo: str, nombre: str):
    """Enviar email con código de recuperación"""
    try:
        mensaje = MIMEMultipart()
        mensaje['From'] = EMAIL_ADDRESS
        mensaje['To'] = destinatario
        mensaje['Subject'] = "Código de Recuperación de Contraseña - Sistema de Vehículos"
        
        cuerpo = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
                <div style="background-color: white; padding: 30px; border-radius: 10px; max-width: 600px; margin: 0 auto;">
                    <h2 style="color: #667eea; text-align: center;">🔐 Recuperar Contraseña</h2>
                    
                    <p style="color: #333; font-size: 16px;">
                        Hola <strong>{nombre}</strong>,
                    </p>
                    
                    <p style="color: #666; font-size: 14px;">
                        Hemos recibido una solicitud para recuperar tu contraseña. 
                        Usa el siguiente código para cambiarla:
                    </p>
                    
                    <div style="background-color: #f0f2ff; padding: 20px; border-radius: 5px; text-align: center; margin: 20px 0;">
                        <p style="font-size: 32px; font-weight: bold; color: #667eea; margin: 0; letter-spacing: 5px;">
                            {codigo}
                        </p>
                    </div>
                    
                    <p style="color: #999; font-size: 12px;">
                        ⏰ Este código expira en 30 minutos.
                    </p>
                    
                    <p style="color: #999; font-size: 12px;">
                        Si no solicitaste esto, ignora este email.
                    </p>
                    
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    
                    <p style="color: #999; font-size: 12px; text-align: center;">
                        Sistema de Gestión de Vehículos © 2026
                    </p>
                </div>
            </body>
        </html>
        """
        
        mensaje.attach(MIMEText(cuerpo, 'html'))
        
        # Conectar y enviar
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as servidor:
            servidor.starttls()
            servidor.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            servidor.send_message(mensaje)
        
        return True
    except Exception as e:
        print(f"Error al enviar email: {str(e)}")
        return False

# Crear las tablas en la base de datos
Base.metadata.create_all(bind=engine)

# Crear la aplicación FastAPI
app = FastAPI(title="Sistema de Vehículos", version="1.0.0")

# Crear carpeta de uploads si no existe
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Modelos Pydantic ====================

class RegistroUsuario(BaseModel):
    email: str
    nombre: str
    contraseña: str
    proveedor: str
    telefono: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    contraseña: str

class CrearUsuarioAdmin(BaseModel):
    email: str
    nombre: str
    contraseña: str
    proveedor: Optional[str] = None
    telefono: Optional[str] = None
    rol: str = "usuario"

class LoginResponse(BaseModel):
    id: int
    email: str
    nombre: str
    proveedor: str
    token: str

class SolicitarRecuperacion(BaseModel):
    telefono: str

class VerificarCodigo(BaseModel):
    telefono: str
    codigo: str

class ResetearContrasena(BaseModel):
    telefono: str
    codigo: str
    nueva_contrasena: str

class CrearVehiculo(BaseModel):
    placa: str
    tonelaje: str
    marca: Optional[str] = None
    modelo: Optional[int] = None
    ciudad: Optional[str] = None
    cedula: Optional[str] = None
    proveedor: Optional[str] = None
    mes_inscripcion: Optional[int] = None
    año_inscripcion: Optional[int] = None
    soat: Optional[date] = None
    tecnomecanica: Optional[date] = None

class VehiculoResponse(BaseModel):
    id: int
    marca: str
    modelo: str
    año: int
    placa: str
    color: str
    descripcion: Optional[str]
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True

class CrearProveedor(BaseModel):
    proveedor: str

class ProveedorResponse(BaseModel):
    id: int
    proveedor: str
    
    class Config:
        from_attributes = True

class CrearHistorialVehiculo(BaseModel):
    mes: int
    año: int
    descripcion: Optional[str] = None

class HistorialVehiculoResponse(BaseModel):
    id: int
    vehiculo_id: int
    mes: int
    año: int
    pdf_ruta: Optional[str]
    descripcion: Optional[str]
    fecha_carga: datetime
    
    class Config:
        from_attributes = True

# ==================== Endpoints de Autenticación ====================

@app.post("/admin/crear-usuario")
def admin_crear_usuario(datos: CrearUsuarioAdmin, db: Session = Depends(get_db), _: dict = Depends(get_admin_actual)):
    if datos.rol not in ("admin", "usuario"):
        return {"error": "Rol inválido. Usa 'admin' o 'usuario'"}
    if db.query(UsuarioDB).filter(UsuarioDB.email == datos.email).first():
        return {"error": "El email ya está registrado"}
    if datos.telefono and db.query(UsuarioDB).filter(UsuarioDB.telefono == datos.telefono).first():
        return {"error": "Ese número de WhatsApp ya está registrado"}
    try:
        nuevo = UsuarioDB(
            email=datos.email,
            nombre=datos.nombre,
            contraseña=hash_password(datos.contraseña),
            proveedor=datos.proveedor,
            rol=datos.rol,
            telefono=datos.telefono,
        )
        db.add(nuevo)
        db.commit()
        db.refresh(nuevo)
        return {
            "mensaje": "Usuario creado exitosamente",
            "usuario": {"id": nuevo.id, "email": nuevo.email, "nombre": nuevo.nombre, "rol": nuevo.rol}
        }
    except Exception as e:
        db.rollback()
        return {"error": f"Error al crear usuario: {str(e)}"}

@app.post("/auth/registro")
def registro(datos: RegistroUsuario, db: Session = Depends(get_db)):
    # Verificar email duplicado
    if db.query(UsuarioDB).filter(UsuarioDB.email == datos.email).first():
        return {"error": "El email ya está registrado"}
    
    # Verificar teléfono duplicado
    if datos.telefono and db.query(UsuarioDB).filter(UsuarioDB.telefono == datos.telefono).first():
        return {"error": "Ese número de WhatsApp ya está registrado"}
    
    try:
        nuevo_usuario = UsuarioDB(
            email=datos.email,
            nombre=datos.nombre,
            contraseña=hash_password(datos.contraseña),
            proveedor=datos.proveedor,
            rol="usuario",
            telefono=datos.telefono
        )
        db.add(nuevo_usuario)
        db.commit()
        db.refresh(nuevo_usuario)
        return {
            "mensaje": "Usuario registrado exitosamente",
            "usuario": {
                "id": nuevo_usuario.id,
                "email": nuevo_usuario.email,
                "nombre": nuevo_usuario.nombre,
                "proveedor": nuevo_usuario.proveedor,
                "telefono": nuevo_usuario.telefono
            }
        }
    except Exception as e:
        db.rollback()
        return {"error": f"Error al registrar: {str(e)}"}

@app.post("/auth/login")
def login(datos: LoginRequest, db: Session = Depends(get_db)):
    """Login de usuario"""
    usuario = db.query(UsuarioDB).filter(UsuarioDB.email == datos.email).first()
    
    if not usuario:
        return {"error": "Usuario no encontrado"}
    
    if not verify_password(datos.contraseña, usuario.contraseña):
        return {"error": "Contraseña incorrecta"}
    
    rol = usuario.rol if hasattr(usuario, "rol") else "usuario"
    token = crear_token(usuario.id, usuario.email, rol)

    return {
        "id": usuario.id,
        "email": usuario.email,
        "nombre": usuario.proveedor or usuario.nombre,
        "proveedor": usuario.proveedor,
        "rol": rol,
        "token": token
    }

# ==================== Endpoints de Recuperación de Contraseña ====================

@app.post("/auth/solicitar-recuperacion")
def solicitar_recuperacion(datos: SolicitarRecuperacion, db: Session = Depends(get_db)):
    print(f"Recibida solicitud para teléfono: {datos.telefono}")
    usuario = db.query(UsuarioDB).filter(UsuarioDB.telefono == datos.telefono).first()
    
    if not usuario:
        print("Usuario no encontrado")
        return {"error": "No existe una cuenta con ese número de WhatsApp"}
    
    print(f"Usuario encontrado: {usuario.email}, teléfono: {usuario.telefono}")
    codigo = generar_codigo()
    print(f"Código generado: {codigo}")
    
    # Crear token de recuperación
    fecha_expiracion = datetime.utcnow() + timedelta(minutes=30)
    
    # Eliminar tokens anteriores no usados
    tokens_viejos = db.query(TokenRecuperacionDB).filter(
        TokenRecuperacionDB.usuario_id == usuario.id,
        TokenRecuperacionDB.usado == 0
    ).all()
    for token in tokens_viejos:
        db.delete(token)
    
    token = TokenRecuperacionDB(
        usuario_id=usuario.id,
        codigo=codigo,
        fecha_expiracion=fecha_expiracion
    )
    db.add(token)
    db.commit()
    
    # Enviar WhatsApp
    try:
        from twilio_config import enviar_whatsapp
        mensaje = f"Hola {usuario.nombre}, tu código de recuperación de Hermes es: {codigo}. Válido por 30 minutos."
        resultado = enviar_whatsapp(usuario.telefono, mensaje)
        print(f"Resultado de Twilio: {resultado}")   # <--- NUEVA LÍNEA
        if resultado.get("status") == "ok":
            return {"mensaje": "Código enviado por WhatsApp"}
        else:
            return {"error": "Error al enviar el mensaje. Intenta de nuevo."}
    except Exception as e:
        print(f"Error enviando WhatsApp: {e}")
        return {"error": "Error al enviar el mensaje. Intenta de nuevo."}

@app.post("/auth/verificar-codigo")
def verificar_codigo(datos: VerificarCodigo, db: Session = Depends(get_db)):
    """Verificar código de recuperación"""
    usuario = db.query(UsuarioDB).filter(UsuarioDB.telefono == datos.telefono).first()
    
    if not usuario:
        return {"error": "Usuario no encontrado"}
    
    # Buscar el token
    token = db.query(TokenRecuperacionDB).filter(
        TokenRecuperacionDB.usuario_id == usuario.id,
        TokenRecuperacionDB.codigo == datos.codigo,
        TokenRecuperacionDB.usado == 0
    ).first()
    
    if not token:
        return {"error": "Código inválido"}
    
    # Verificar si expiró
    if datetime.utcnow() > token.fecha_expiracion:
        return {"error": "El código ha expirado. Solicita uno nuevo."}
    
    return {"mensaje": "Código válido", "valido": True}

@app.post("/auth/resetear-contrasena")
def resetear_contrasena(datos: ResetearContrasena, db: Session = Depends(get_db)):
    """Cambiar contraseña usando código de recuperación"""
    usuario = db.query(UsuarioDB).filter(UsuarioDB.telefono == datos.telefono).first()
    
    if not usuario:
        return {"error": "Usuario no encontrado"}
    
    # Buscar el token
    token = db.query(TokenRecuperacionDB).filter(
        TokenRecuperacionDB.usuario_id == usuario.id,
        TokenRecuperacionDB.codigo == datos.codigo,
        TokenRecuperacionDB.usado == 0
    ).first()
    
    if not token:
        return {"error": "Código inválido"}
    
    # Verificar si expiró
    if datetime.utcnow() > token.fecha_expiracion:
        return {"error": "El código ha expirado"}
    
    # Validar contraseña
    if not datos.nueva_contrasena or len(datos.nueva_contrasena) < 4:
        return {"error": "La contraseña debe tener al menos 4 caracteres"}
    
    usuario.contraseña = hash_password(datos.nueva_contrasena)
    token.usado = 1
    
    db.commit()
    db.refresh(usuario)
    
    return {
        "mensaje": "Contraseña actualizada exitosamente",
        "exito": True
    }

# ==================== Endpoints de Vehículos ====================

@app.post("/vehiculos")
def crear_vehiculo(usuario_id: int, vehiculo: CrearVehiculo, db: Session = Depends(get_db)):
    """Crear nuevo vehículo"""
    usuario = db.query(UsuarioDB).filter(UsuarioDB.id == usuario_id).first()
    if not usuario:
        return {"error": "Usuario no encontrado"}
    
    placa_existente = db.query(VehiculoDB).filter(VehiculoDB.placa == vehiculo.placa).first()
    if placa_existente:
        return {"error": "La placa ya está registrada"}
    
    nuevo_vehiculo = VehiculoDB(
        usuario_id=usuario_id,
        placa=vehiculo.placa.upper(),
        tonelaje=vehiculo.tonelaje,
        marca=vehiculo.marca,
        modelo=vehiculo.modelo,
        ciudad=vehiculo.ciudad,
        cedula=vehiculo.cedula,
        proveedor=vehiculo.proveedor or usuario.proveedor,
        mes_inscripcion=vehiculo.mes_inscripcion,
        año_inscripcion=vehiculo.año_inscripcion,
        soat=vehiculo.soat,
        tecnomecanica=vehiculo.tecnomecanica,
        activo=0
    )
     
    db.add(nuevo_vehiculo)
    db.commit()
    db.refresh(nuevo_vehiculo)
    
    notificar_nuevo_vehiculo({
        "placa": nuevo_vehiculo.placa,
        "proveedor": nuevo_vehiculo.proveedor,
        "marca": nuevo_vehiculo.marca,
        "modelo": nuevo_vehiculo.modelo,
        "usuario_email": usuario.email,
        "nombre": usuario.nombre or usuario.proveedor or usuario.email
    }, db=db)
    return {
        "mensaje": "Vehículo registrado. Pendiente de aprobación.",
        "vehiculo": {
            "id": nuevo_vehiculo.id,
            "placa": nuevo_vehiculo.placa,
            "tonelaje": nuevo_vehiculo.tonelaje,
            "marca": nuevo_vehiculo.marca,
            "modelo": nuevo_vehiculo.modelo,
            "ciudad": nuevo_vehiculo.ciudad,
            "cedula": nuevo_vehiculo.cedula,
            "proveedor": nuevo_vehiculo.proveedor,
            "mes_inscripcion": nuevo_vehiculo.mes_inscripcion,
            "año_inscripcion": nuevo_vehiculo.año_inscripcion,
            "soat": nuevo_vehiculo.soat.isoformat() if nuevo_vehiculo.soat else None,
            "tecnomecanica": nuevo_vehiculo.tecnomecanica.isoformat() if nuevo_vehiculo.tecnomecanica else None
        }
    }

@app.get("/vehiculos/{usuario_id}")
def obtener_vehiculos(usuario_id: int, db: Session = Depends(get_db)):
    """Obtener vehículos de un usuario"""
    usuario = db.query(UsuarioDB).filter(UsuarioDB.id == usuario_id).first()
    if not usuario:
        return {"error": "Usuario no encontrado"}
    
    vehiculos = db.query(VehiculoDB).filter(VehiculoDB.usuario_id == usuario_id).all()
    
    return {
        "usuario": usuario.proveedor or usuario.nombre,
        "proveedor": usuario.proveedor,
        "vehiculos": [
            {
                "id": v.id, "placa": v.placa, "tonelaje": v.tonelaje,
                "marca": v.marca, "modelo": v.modelo,
                "ciudad": v.ciudad,
                "cedula": v.cedula, "proveedor": v.proveedor or usuario.proveedor,
                "mes_inscripcion": v.mes_inscripcion, "año_inscripcion": v.año_inscripcion,
                "soat": v.soat.isoformat() if v.soat else None,
                "tecnomecanica": v.tecnomecanica.isoformat() if v.tecnomecanica else None,
                "pdf_ruta": v.pdf_ruta, "pdf_certificado_aliado": v.pdf_certificado_aliado,
                "pdf_certificado_latin": v.pdf_certificado_latin, "pdf_nit": v.pdf_nit,
                "pdf_soat": v.pdf_soat, "pdf_tecnomecanica": v.pdf_tecnomecanica,
                "activo": getattr(v, "activo", 0),
                "motivo_rechazo": getattr(v, "motivo_rechazo", None),
                "fecha_desactivacion": v.fecha_desactivacion.isoformat() if v.fecha_desactivacion else None
            }
            for v in vehiculos
        ]
    }

@app.get("/admin/todos-vehiculos")
def obtener_todos_vehiculos(db: Session = Depends(get_db), _: dict = Depends(get_admin_actual)):
    vehiculos = db.query(VehiculoDB).all()
    resultado = []
    for v in vehiculos:
        u = db.query(UsuarioDB).filter(UsuarioDB.id == v.usuario_id).first()
        resultado.append({"id": v.id, "placa": v.placa, "tonelaje": v.tonelaje,
            "marca": v.marca, "modelo": v.modelo,
            "ciudad": v.ciudad, "cedula": v.cedula,
            "proveedor": v.proveedor, "activo": v.activo,
            "soat": v.soat.isoformat() if v.soat else None,
            "tecnomecanica": v.tecnomecanica.isoformat() if v.tecnomecanica else None,
            "usuario_nombre": u.proveedor or u.nombre if u else "—", "usuario_email": u.email if u else "—",
            "pdf_certificado_aliado": v.pdf_certificado_aliado,
            "pdf_certificado_latin": v.pdf_certificado_latin, "pdf_nit": v.pdf_nit,
            "pdf_soat": v.pdf_soat, "pdf_tecnomecanica": v.pdf_tecnomecanica,
            "fecha_desactivacion": v.fecha_desactivacion.isoformat() if v.fecha_desactivacion else None})
    return {"total": len(resultado), "vehiculos": resultado}

@app.get("/vehiculos-pendientes")
def obtener_vehiculos_pendientes(db: Session = Depends(get_db), _: dict = Depends(get_admin_actual)):
    vehiculos = db.query(VehiculoDB).filter(VehiculoDB.activo == 0).all()
    resultado = []
    for v in vehiculos:
        u = db.query(UsuarioDB).filter(UsuarioDB.id == v.usuario_id).first()
        resultado.append({"id": v.id, "placa": v.placa, "tonelaje": v.tonelaje,
            "marca": v.marca, "modelo": v.modelo,
            "ciudad": v.ciudad, "cedula": v.cedula,
            "proveedor": v.proveedor, "activo": v.activo,
            "soat": v.soat.isoformat() if v.soat else None,
            "tecnomecanica": v.tecnomecanica.isoformat() if v.tecnomecanica else None,
            "usuario_nombre": u.proveedor or u.nombre if u else "—", "usuario_email": u.email if u else "—",
            "pdf_certificado_aliado": v.pdf_certificado_aliado,
            "pdf_certificado_latin": v.pdf_certificado_latin, "pdf_nit": v.pdf_nit,
            "pdf_soat": v.pdf_soat, "pdf_tecnomecanica": v.pdf_tecnomecanica, "pdf_ruta": v.pdf_ruta,
            "fecha_desactivacion": v.fecha_desactivacion.isoformat() if v.fecha_desactivacion else None})
    return {"total": len(resultado), "vehiculos": resultado}

@app.put("/vehiculos/{vehiculo_id}/activar")
def activar_vehiculo(vehiculo_id: int, usuario_id: int = 0, db: Session = Depends(get_db), _: dict = Depends(get_admin_actual)):
    v = db.query(VehiculoDB).filter(VehiculoDB.id == vehiculo_id).first()
    if not v: return {"error": "Vehículo no encontrado"}
    ahora = datetime.now(ZoneInfo("America/Bogota")).replace(tzinfo=None)
    v.activo = 1
    v.fecha_desactivacion = None
    db.add(HistorialEstadoVehiculoDB(
        vehiculo_id=vehiculo_id,
        usuario_id=usuario_id or None,
        accion="activado",
        fecha=ahora
    ))
    db.commit(); db.refresh(v)
    return {"mensaje": "Vehículo activado", "id": v.id, "placa": v.placa, "activo": v.activo}

@app.put("/vehiculos/{vehiculo_id}/desactivar")
def desactivar_vehiculo(vehiculo_id: int, usuario_id: int = 0, db: Session = Depends(get_db), _: dict = Depends(get_admin_actual)):
    v = db.query(VehiculoDB).filter(VehiculoDB.id == vehiculo_id).first()
    if not v: return {"error": "Vehículo no encontrado"}
    ahora = datetime.now(ZoneInfo("America/Bogota")).replace(tzinfo=None)
    v.activo = 0
    v.fecha_desactivacion = ahora
    db.add(HistorialEstadoVehiculoDB(
        vehiculo_id=vehiculo_id,
        usuario_id=usuario_id or None,
        accion="desactivado",
        fecha=ahora
    ))
    db.commit(); db.refresh(v)
    return {
        "mensaje": "Vehículo desactivado", "id": v.id, "placa": v.placa, "activo": v.activo,
        "fecha_desactivacion": v.fecha_desactivacion.isoformat() if v.fecha_desactivacion else None
    }

@app.get("/vehiculos/{vehiculo_id}/historial-estado")
def historial_estado_vehiculo(vehiculo_id: int, db: Session = Depends(get_db)):
    """Log de activaciones y desactivaciones de un vehículo."""
    registros = db.query(HistorialEstadoVehiculoDB).filter(
        HistorialEstadoVehiculoDB.vehiculo_id == vehiculo_id
    ).order_by(HistorialEstadoVehiculoDB.fecha.desc()).all()
    return {"vehiculo_id": vehiculo_id, "total": len(registros), "registros": [
        {
            "id": r.id, "accion": r.accion,
            "fecha": r.fecha.isoformat(),
            "usuario": r.usuario.nombre or r.usuario.email if r.usuario else "Sistema"
        }
        for r in registros
    ]}

class MotivoRechazo(BaseModel):
    motivo: str

@app.put("/vehiculos/{vehiculo_id}/rechazar")
def rechazar_vehiculo(vehiculo_id: int, body: MotivoRechazo, db: Session = Depends(get_db), _: dict = Depends(get_admin_actual)):
    """Rechazar vehículo con motivo — queda activo=-1 y conserva sus datos"""
    v = db.query(VehiculoDB).filter(VehiculoDB.id == vehiculo_id).first()
    if not v:
        return {"error": "Vehículo no encontrado"}
    v.activo = -1
    v.motivo_rechazo = body.motivo.strip()
    db.commit(); db.refresh(v)
    return {"mensaje": "Vehículo rechazado", "id": v.id, "placa": v.placa,
            "activo": v.activo, "motivo_rechazo": v.motivo_rechazo}

@app.get("/admin/soat-alertas")
def soat_alertas(db: Session = Depends(get_db), _: dict = Depends(get_admin_actual)):
    """Vehículos con SOAT vencido (> 1 año) o sin SOAT registrado"""
    hoy = hoy_colombia()
    vehiculos = db.query(VehiculoDB).all()
    alertas = []
    for v in vehiculos:
        u = db.query(UsuarioDB).filter(UsuarioDB.id == v.usuario_id).first()
        vencido = False
        dias_vencido = None
        if v.soat is None:
            vencido = True
        else:
            delta = (hoy - v.soat).days
            if delta > 365:
                vencido = True
                dias_vencido = delta - 365
        if vencido:
            alertas.append({
                "id": v.id,
                "placa": v.placa,
                "proveedor": v.proveedor,
                "soat": v.soat.isoformat() if v.soat else None,
                "dias_vencido": dias_vencido,
                "usuario_nombre": u.proveedor or u.nombre if u else "—",
                "usuario_email": u.email if u else "—"
            })
    return {"total": len(alertas), "alertas": alertas}

@app.delete("/vehiculos/{vehiculo_id}")
def eliminar_vehiculo(vehiculo_id: int, usuario_id: int, db: Session = Depends(get_db)):
    """Eliminar un vehículo — solo admin"""
    solicitante = db.query(UsuarioDB).filter(UsuarioDB.id == usuario_id).first()
    if not solicitante or solicitante.rol != "admin":
        return {"error": "No tienes permisos para eliminar vehículos"}
    vehiculo = db.query(VehiculoDB).filter(VehiculoDB.id == vehiculo_id).first()
    if not vehiculo:
        return {"error": "Vehículo no encontrado"}

    # Primero eliminar historial para evitar ForeignKeyViolation
    db.query(HistorialVehiculoDB).filter(
        HistorialVehiculoDB.vehiculo_id == vehiculo_id
    ).delete(synchronize_session=False)

    db.delete(vehiculo)
    db.commit()

    return {"mensaje": "Vehículo eliminado exitosamente"}

@app.put("/vehiculos/{vehiculo_id}")
def actualizar_vehiculo(vehiculo_id: int, vehiculo: CrearVehiculo, db: Session = Depends(get_db)):
    """Actualizar vehículo y resetear a pendiente"""
    db_vehiculo = db.query(VehiculoDB).filter(VehiculoDB.id == vehiculo_id).first()
    if not db_vehiculo: return {"error": "Vehículo no encontrado"}
    if vehiculo.placa.upper() != db_vehiculo.placa:
        if db.query(VehiculoDB).filter(VehiculoDB.placa == vehiculo.placa.upper()).first():
            return {"error": "La placa ya está registrada"}
    db_vehiculo.placa = vehiculo.placa.upper(); db_vehiculo.tonelaje = vehiculo.tonelaje
    db_vehiculo.marca = vehiculo.marca; db_vehiculo.modelo = vehiculo.modelo
    db_vehiculo.ciudad = vehiculo.ciudad; db_vehiculo.cedula = vehiculo.cedula
    db_vehiculo.activo = 0
    if vehiculo.soat is not None: db_vehiculo.soat = vehiculo.soat
    if vehiculo.tecnomecanica is not None: db_vehiculo.tecnomecanica = vehiculo.tecnomecanica
    if vehiculo.mes_inscripcion is not None: db_vehiculo.mes_inscripcion = vehiculo.mes_inscripcion
    if vehiculo.año_inscripcion is not None: db_vehiculo.año_inscripcion = vehiculo.año_inscripcion
    db.commit(); db.refresh(db_vehiculo)
    u = db.query(UsuarioDB).filter(UsuarioDB.id == db_vehiculo.usuario_id).first()
    return {"mensaje": "Actualizado. Pendiente de aprobación.", "vehiculo": {
        "id": db_vehiculo.id, "placa": db_vehiculo.placa, "activo": db_vehiculo.activo,
        "proveedor": db_vehiculo.proveedor or (u.proveedor if u else "")
    }}

# ==================== Endpoints de Proveedores ====================

@app.post("/proveedores")
def crear_proveedor(proveedor: CrearProveedor, db: Session = Depends(get_db), _: dict = Depends(get_admin_actual)):
    """Crear nuevo proveedor"""
    # Verificar si ya existe un proveedor con el mismo nombre
    proveedor_existente = db.query(ProveedorDB).filter(ProveedorDB.proveedor == proveedor.proveedor).first()
    if proveedor_existente:
        return {"error": "Este proveedor ya está registrado"}
    
    nuevo_proveedor = ProveedorDB(
        proveedor=proveedor.proveedor
    )
    db.add(nuevo_proveedor)
    db.commit()
    db.refresh(nuevo_proveedor)
    
    return {
        "mensaje": "Proveedor registrado exitosamente",
        "proveedor": {
            "id": nuevo_proveedor.id,
            "proveedor": nuevo_proveedor.proveedor
        }
    }

@app.get("/proveedores")
def obtener_proveedores(db: Session = Depends(get_db)):
    """Obtener todos los proveedores"""
    proveedores = db.query(ProveedorDB).all()
    
    result = {
        "total": len(proveedores),
        "proveedores": [
            {
                "id": p.id,
                "proveedor": p.proveedor
            }
            for p in proveedores
        ]
    }
    
    print(f"DEBUG: Devolviendo {len(proveedores)} proveedores")
    for p in proveedores:
        print(f"  - {p.proveedor}")
    
    return result

@app.get("/debug/proveedores")
def debug_proveedores(db: Session = Depends(get_db)):
    """Endpoint de debug para proveedores"""
    proveedores = db.query(ProveedorDB).all()
    return {
        "count": len(proveedores),
        "data": [{"id": p.id, "name": p.proveedor} for p in proveedores]
    }

@app.get("/proveedores/{proveedor_id}")
def obtener_proveedor(proveedor_id: int, db: Session = Depends(get_db)):
    """Obtener un proveedor específico"""
    proveedor = db.query(ProveedorDB).filter(ProveedorDB.id == proveedor_id).first()
    if not proveedor:
        return {"error": "Proveedor no encontrado"}
    
    return {
        "id": proveedor.id,
        "proveedor": proveedor.proveedor
    }

@app.put("/proveedores/{proveedor_id}")
def actualizar_proveedor(proveedor_id: int, datos: CrearProveedor, db: Session = Depends(get_db), _: dict = Depends(get_admin_actual)):
    """Actualizar un proveedor"""
    proveedor = db.query(ProveedorDB).filter(ProveedorDB.id == proveedor_id).first()
    if not proveedor:
        return {"error": "Proveedor no encontrado"}
    
    # Verificar si el nuevo nombre ya existe (y no es el mismo proveedor)
    if datos.proveedor != proveedor.proveedor:
        nombre_existente = db.query(ProveedorDB).filter(ProveedorDB.proveedor == datos.proveedor).first()
        if nombre_existente:
            return {"error": "El nombre de proveedor ya está en uso"}
    
    proveedor.proveedor = datos.proveedor
    
    db.commit()
    db.refresh(proveedor)
    
    return {
        "mensaje": "Proveedor actualizado",
        "proveedor": {
            "id": proveedor.id,
            "proveedor": proveedor.proveedor
        }
    }

@app.delete("/proveedores/{proveedor_id}")
def eliminar_proveedor(proveedor_id: int, db: Session = Depends(get_db), _: dict = Depends(get_admin_actual)):
    """Eliminar un proveedor"""
    proveedor = db.query(ProveedorDB).filter(ProveedorDB.id == proveedor_id).first()
    if not proveedor:
        return {"error": "Proveedor no encontrado"}
    
    db.delete(proveedor)
    db.commit()
    
    return {"mensaje": "Proveedor eliminado exitosamente"}

# ==================== Endpoints de Historial de Vehículos ====================

@app.post("/historial-vehiculos")
def crear_historial(vehiculo_id: int, historial: CrearHistorialVehiculo, db: Session = Depends(get_db)):
    """Crear un registro de historial para un vehículo (mes específico)"""
    # Verificar que el vehículo exista
    vehiculo = db.query(VehiculoDB).filter(VehiculoDB.id == vehiculo_id).first()
    if not vehiculo:
        return {"error": "Vehículo no encontrado"}
    
    # Validar mes y año
    if not (1 <= historial.mes <= 12):
        return {"error": "El mes debe ser entre 1 y 12"}
    
    if historial.año < 2000 or historial.año > 2100:
        return {"error": "El año debe ser válido"}
    
    # Verificar si ya existe un registro para ese mes y año
    registro_existente = db.query(HistorialVehiculoDB).filter(
        HistorialVehiculoDB.vehiculo_id == vehiculo_id,
        HistorialVehiculoDB.mes == historial.mes,
        HistorialVehiculoDB.año == historial.año
    ).first()
    
    if registro_existente:
        return {"error": f"Ya existe un registro para {historial.mes}/{historial.año}"}
    
    nuevo_historial = HistorialVehiculoDB(
        vehiculo_id=vehiculo_id,
        mes=historial.mes,
        año=historial.año,
        descripcion=historial.descripcion,
        pdf_preoperacional=None,
        pdf_mantenimiento=None,
        pdf_mantenimiento_correctivo=None
    )
    db.add(nuevo_historial)
    db.commit()
    db.refresh(nuevo_historial)
    
    return {
        "mensaje": "Registro de historial creado exitosamente",
        "historial": {
            "id": nuevo_historial.id,
            "vehiculo_id": nuevo_historial.vehiculo_id,
            "mes": nuevo_historial.mes,
            "año": nuevo_historial.año,
            "descripcion": nuevo_historial.descripcion,
            "pdf_preoperacional": nuevo_historial.pdf_preoperacional,
            "pdf_mantenimiento": nuevo_historial.pdf_mantenimiento,
            "pdf_mantenimiento_correctivo": nuevo_historial.pdf_mantenimiento_correctivo
        }
    }

@app.get("/historial-vehiculos/{vehiculo_id}")
def obtener_historial_vehiculo(vehiculo_id: int, db: Session = Depends(get_db)):
    """Obtener historial completo de un vehículo"""
    # Verificar que el vehículo exista
    vehiculo = db.query(VehiculoDB).filter(VehiculoDB.id == vehiculo_id).first()
    if not vehiculo:
        return {"error": "Vehículo no encontrado"}
    
    historial = db.query(HistorialVehiculoDB).filter(
        HistorialVehiculoDB.vehiculo_id == vehiculo_id
    ).order_by(HistorialVehiculoDB.año.desc(), HistorialVehiculoDB.mes.desc()).all()
    
    return {
        "vehiculo_id": vehiculo_id,
        "placa": vehiculo.placa,
        "total_registros": len(historial),
        "historial": [
            {
                "id": h.id,
                "mes": h.mes,
                "año": h.año,
                "descripcion": h.descripcion,
                "pdf_preoperacional": h.pdf_preoperacional,
                "pdf_mantenimiento": h.pdf_mantenimiento,
                "pdf_mantenimiento_correctivo": h.pdf_mantenimiento_correctivo,
                "pdfs_correctivo_adicionales": h.pdfs_correctivo_adicionales,
                "fecha_carga": h.fecha_carga.isoformat()
            }
            for h in historial
        ]
    }

@app.put("/historial-vehiculos/{historial_id}")
def actualizar_historial(historial_id: int, datos: CrearHistorialVehiculo, db: Session = Depends(get_db)):
    """Actualizar descripción del historial"""
    historial = db.query(HistorialVehiculoDB).filter(HistorialVehiculoDB.id == historial_id).first()
    if not historial:
        return {"error": "Registro de historial no encontrado"}
    
    historial.descripcion = datos.descripcion
    db.commit()
    db.refresh(historial)
    
    return {
        "mensaje": "Historial actualizado",
        "historial": {
            "id": historial.id,
            "mes": historial.mes,
            "año": historial.año,
            "descripcion": historial.descripcion
        }
    }

@app.delete("/historial-vehiculos/{historial_id}")
def eliminar_historial(historial_id: int, db: Session = Depends(get_db)):
    """Eliminar un registro del historial"""
    historial = db.query(HistorialVehiculoDB).filter(HistorialVehiculoDB.id == historial_id).first()
    if not historial:
        return {"error": "Registro de historial no encontrado"}
    
    db.delete(historial)
    db.commit()
    
    return {"mensaje": "Registro de historial eliminado exitosamente"}

@app.post("/historial-vehiculos/{historial_id}/upload-pdf")
async def upload_pdf_historial(historial_id: int, tipo: str = "preoperacional", file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Cargar PDF operacional para un registro específico del historial"""
    if file.content_type != "application/pdf":
        return {"error": "Solo se permiten archivos PDF"}
    
    historial = db.query(HistorialVehiculoDB).filter(HistorialVehiculoDB.id == historial_id).first()
    if not historial:
        return {"error": "Registro de historial no encontrado"}
    
    try:
        # Crear nombre único para el archivo según el tipo
        vehiculo = db.query(VehiculoDB).filter(VehiculoDB.id == historial.vehiculo_id).first()
        
        import json as _json

        tipo_nombre = {
            "preoperacional": "preop",
            "mantenimiento": "mant",
            "mantenimiento_correctivo": "mant_corr"
        }.get(tipo, "preop")

        # Para correctivos adicionales, usar sufijo numérico en el nombre de archivo
        if tipo == "mantenimiento_correctivo" and historial.pdf_mantenimiento_correctivo:
            try:
                adicionales = _json.loads(historial.pdfs_correctivo_adicionales or "[]")
            except Exception:
                adicionales = []
            idx = len(adicionales) + 2  # 2, 3, 4…
            tipo_nombre = f"mant_corr_{idx}"

        filename = f"historial_{historial_id}_{vehiculo.placa.replace('-', '')}_mes{historial.mes}_{historial.año}_{tipo_nombre}.pdf"
        filepath = os.path.join(UPLOADS_DIR, filename)

        # Guardar el archivo
        with open(filepath, "wb") as f:
            content = await file.read()
            f.write(content)

        pdf_ruta = f"/uploads/{filename}"

        # Actualizar la ruta PDF en la base de datos según el tipo
        if tipo == "preoperacional":
            historial.pdf_preoperacional = pdf_ruta
        elif tipo == "mantenimiento":
            historial.pdf_mantenimiento = pdf_ruta
        elif tipo == "mantenimiento_correctivo":
            if historial.pdf_mantenimiento_correctivo is None:
                # Primera carga — va al campo principal (usado para estadísticas)
                historial.pdf_mantenimiento_correctivo = pdf_ruta
            else:
                # Carga adicional — se acumula en el array JSON con fecha
                try:
                    adicionales = _json.loads(historial.pdfs_correctivo_adicionales or "[]")
                except Exception:
                    adicionales = []
                adicionales.append({"ruta": pdf_ruta, "fecha": datetime.utcnow().isoformat()})
                historial.pdfs_correctivo_adicionales = _json.dumps(adicionales)

        db.commit()

        # Contar total de correctivos para devolver al frontend
        total_correctivos = 0
        if tipo == "mantenimiento_correctivo":
            total_correctivos = 1 if historial.pdf_mantenimiento_correctivo else 0
            try:
                total_correctivos += len(_json.loads(historial.pdfs_correctivo_adicionales or "[]"))
            except Exception:
                pass

        return {
            "mensaje": f"PDF {tipo} cargado exitosamente",
            "pdf_ruta": pdf_ruta,
            "tipo": tipo,
            "total_correctivos": total_correctivos
        }
    except Exception as e:
        return {"error": f"Error al cargar el PDF: {str(e)}"}

@app.delete("/historial-vehiculos/{historial_id}/delete-pdf")
def eliminar_pdf_historial(historial_id: int, tipo: str, idx: int = -1, db: Session = Depends(get_db)):
    """Eliminar un PDF de historial.
    - tipo=preoperacional|mantenimiento|mantenimiento_correctivo → elimina el principal
    - tipo=mantenimiento_correctivo_adicional&idx=N → elimina el adicional en posición N
    Al eliminar el principal de correctivo, el primer adicional (si existe) asciende a principal.
    """
    import json as _json
    historial = db.query(HistorialVehiculoDB).filter(HistorialVehiculoDB.id == historial_id).first()
    if not historial:
        return {"error": "Registro de historial no encontrado"}

    def _borrar_fisico(ruta):
        if ruta:
            fp = os.path.join(os.path.dirname(os.path.abspath(__file__)), ruta.lstrip("/"))
            if os.path.exists(fp):
                try: os.remove(fp)
                except: pass

    if tipo == "preoperacional":
        _borrar_fisico(historial.pdf_preoperacional)
        historial.pdf_preoperacional = None

    elif tipo == "mantenimiento":
        _borrar_fisico(historial.pdf_mantenimiento)
        historial.pdf_mantenimiento = None

    elif tipo == "mantenimiento_correctivo":
        # Eliminar el principal; promover primer adicional si existe
        _borrar_fisico(historial.pdf_mantenimiento_correctivo)
        try:
            adicionales = _json.loads(historial.pdfs_correctivo_adicionales or "[]")
        except Exception:
            adicionales = []
        if adicionales:
            primero = adicionales.pop(0)
            # Soporta formato antiguo (string) y nuevo ({ruta, fecha})
            historial.pdf_mantenimiento_correctivo = primero["ruta"] if isinstance(primero, dict) else primero
            historial.pdfs_correctivo_adicionales = _json.dumps(adicionales) if adicionales else None
        else:
            historial.pdf_mantenimiento_correctivo = None

    elif tipo == "mantenimiento_correctivo_adicional":
        try:
            adicionales = _json.loads(historial.pdfs_correctivo_adicionales or "[]")
        except Exception:
            adicionales = []
        if 0 <= idx < len(adicionales):
            entrada = adicionales[idx]
            # Soporta formato antiguo (string) y nuevo ({ruta, fecha})
            ruta_fisica = entrada["ruta"] if isinstance(entrada, dict) else entrada
            _borrar_fisico(ruta_fisica)
            adicionales.pop(idx)
            historial.pdfs_correctivo_adicionales = _json.dumps(adicionales) if adicionales else None
        else:
            return {"error": "Índice de adicional inválido"}
    else:
        return {"error": "Tipo inválido"}

    db.commit()
    return {"mensaje": f"PDF eliminado exitosamente"}

# ==================== Endpoint de Carga de PDF ====================

@app.post("/vehiculos/{vehiculo_id}/upload-pdf")
async def upload_pdf_vehiculo(vehiculo_id: int, tipo: str = "general", file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Cargar PDF para un vehículo - soporta diferentes tipos"""
    # Validar que el archivo sea PDF
    if file.content_type != "application/pdf":
        return {"error": "Solo se permiten archivos PDF"}
    
    # Buscar el vehículo
    vehiculo = db.query(VehiculoDB).filter(VehiculoDB.id == vehiculo_id).first()
    if not vehiculo:
        return {"error": "Vehículo no encontrado"}
    
    try:
        # Crear nombre único para el archivo según el tipo
        tipo_nombre = {
            "general": "general",
            "certificado_aliado": "cert_aliado",
            "certificado_latin": "cert_latin",
            "nit": "nit",
            "soat": "soat",
            "tecnomecanica": "tecnomecanica"
        }.get(tipo, "general")
        
        filename = f"vehiculo_{vehiculo_id}_{vehiculo.placa.replace('-', '')}_{tipo_nombre}.pdf"
        filepath = os.path.join(UPLOADS_DIR, filename)
        
        # Guardar el archivo
        with open(filepath, "wb") as f:
            content = await file.read()
            f.write(content)
        
        pdf_ruta = f"/uploads/{filename}"
        
        # Actualizar la ruta PDF en la base de datos según el tipo
        if tipo == "certificado_aliado":
            vehiculo.pdf_certificado_aliado = pdf_ruta
        elif tipo == "certificado_latin":
            vehiculo.pdf_certificado_latin = pdf_ruta
        elif tipo == "nit":
            vehiculo.pdf_nit = pdf_ruta
        elif tipo == "soat":
            vehiculo.pdf_soat = pdf_ruta
        elif tipo == "tecnomecanica":
            vehiculo.pdf_tecnomecanica = pdf_ruta
        else:
            vehiculo.pdf_ruta = pdf_ruta
        
        db.commit()
        
        return {
            "mensaje": f"PDF {tipo} cargado exitosamente",
            "pdf_ruta": pdf_ruta,
            "tipo": tipo
        }
    except Exception as e:
        return {"error": f"Error al cargar el PDF: {str(e)}"}

@app.post("/upload-pdf")
async def upload_pdf(vehiculo_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Cargar PDF general para un vehículo (compatibilidad)"""
    return await upload_pdf_vehiculo(vehiculo_id, "general", file, db)

# ==================== Servir archivos estáticos (uploads) ====================

@app.get("/uploads/{filename}")
def descargar_pdf(filename: str):
    """Descargar un PDF"""
    filepath = os.path.join(UPLOADS_DIR, filename)
    if os.path.exists(filepath):
        return FileResponse(filepath, media_type="application/pdf", filename=filename)
    return {"error": "Archivo no encontrado"}

# ==================== Preoperacional Diario ====================

class RegistrarPreoperacional(BaseModel):
    vehiculo_id: int
    usuario_id: int
    fecha: date
    frenos: int = 0
    llantas: int = 0
    direccion: int = 0
    sin_fugas: int = 0
    luces_delanteras: int = 0
    luces_traseras: int = 0
    direccionales: int = 0
    nivel_aceite: int = 0
    temperatura_motor: int = 0
    extintor: int = 0
    soat_doc_vigente: int = 0
    revision_tecnica: int = 0
    licencia_conduccion: int = 0
    sin_alcohol_drogas: int = 0
    conductor_descansado: int = 0
    observaciones: Optional[str] = None

def _preop_to_dict(p):
    total = sum([p.frenos, p.llantas, p.direccion, p.sin_fugas,
                 p.luces_delanteras, p.luces_traseras, p.direccionales,
                 p.nivel_aceite, p.temperatura_motor, p.extintor,
                 p.soat_doc_vigente, p.revision_tecnica, p.licencia_conduccion,
                 p.sin_alcohol_drogas, p.conductor_descansado])
    return {
        "id": p.id, "vehiculo_id": p.vehiculo_id, "usuario_id": p.usuario_id,
        "fecha": p.fecha.isoformat(),
        "frenos": p.frenos, "llantas": p.llantas, "direccion": p.direccion,
        "sin_fugas": p.sin_fugas, "luces_delanteras": p.luces_delanteras,
        "luces_traseras": p.luces_traseras, "direccionales": p.direccionales,
        "nivel_aceite": p.nivel_aceite, "temperatura_motor": p.temperatura_motor,
        "extintor": p.extintor, "soat_doc_vigente": p.soat_doc_vigente,
        "revision_tecnica": p.revision_tecnica, "licencia_conduccion": p.licencia_conduccion,
        "sin_alcohol_drogas": p.sin_alcohol_drogas, "conductor_descansado": p.conductor_descansado,
        "observaciones": p.observaciones,
        "fecha_registro": p.fecha_registro.isoformat(),
        "total_ok": total, "total_items": 15
    }

@app.post("/preoperacional-diario")
def registrar_preoperacional(datos: RegistrarPreoperacional, db: Session = Depends(get_db)):
    """Registrar checklist diario — uno por vehículo por día"""
    existente = db.query(PreoperacionalDiarioDB).filter(
        PreoperacionalDiarioDB.vehiculo_id == datos.vehiculo_id,
        PreoperacionalDiarioDB.fecha == datos.fecha
    ).first()
    if existente:
        # Actualizar si ya existe para el mismo día
        for campo in ["frenos","llantas","direccion","sin_fugas","luces_delanteras",
                      "luces_traseras","direccionales","nivel_aceite","temperatura_motor",
                      "extintor","soat_doc_vigente","revision_tecnica","licencia_conduccion",
                      "sin_alcohol_drogas","conductor_descansado","observaciones"]:
            setattr(existente, campo, getattr(datos, campo))
        db.commit(); db.refresh(existente)
        return {"mensaje": "Preoperacional actualizado", "preoperacional": _preop_to_dict(existente)}
    nuevo = PreoperacionalDiarioDB(
        vehiculo_id=datos.vehiculo_id, usuario_id=datos.usuario_id, fecha=datos.fecha,
        frenos=datos.frenos, llantas=datos.llantas, direccion=datos.direccion,
        sin_fugas=datos.sin_fugas, luces_delanteras=datos.luces_delanteras,
        luces_traseras=datos.luces_traseras, direccionales=datos.direccionales,
        nivel_aceite=datos.nivel_aceite, temperatura_motor=datos.temperatura_motor,
        extintor=datos.extintor, soat_doc_vigente=datos.soat_doc_vigente,
        revision_tecnica=datos.revision_tecnica, licencia_conduccion=datos.licencia_conduccion,
        sin_alcohol_drogas=datos.sin_alcohol_drogas, conductor_descansado=datos.conductor_descansado,
        observaciones=datos.observaciones
    )
    db.add(nuevo); db.commit(); db.refresh(nuevo)
    return {"mensaje": "Preoperacional registrado", "preoperacional": _preop_to_dict(nuevo)}

@app.get("/preoperacional-diario/{vehiculo_id}")
def obtener_preoperacional(vehiculo_id: int, db: Session = Depends(get_db)):
    """Obtener todos los preoperacionales de un vehículo"""
    registros = db.query(PreoperacionalDiarioDB).filter(
        PreoperacionalDiarioDB.vehiculo_id == vehiculo_id
    ).order_by(PreoperacionalDiarioDB.fecha.desc()).all()
    return {"vehiculo_id": vehiculo_id, "total": len(registros),
            "registros": [_preop_to_dict(p) for p in registros]}

@app.get("/admin/preoperacional-alertas")
def preoperacional_alertas(db: Session = Depends(get_db), _: dict = Depends(get_admin_actual)):
    """Vehículos activos sin preoperacional hoy"""
    hoy = hoy_colombia()
    vehiculos_activos = db.query(VehiculoDB).filter(VehiculoDB.activo == 1).all()
    sin_preop = []
    for v in vehiculos_activos:
        tiene_hoy = db.query(PreoperacionalDiarioDB).filter(
            PreoperacionalDiarioDB.vehiculo_id == v.id,
            PreoperacionalDiarioDB.fecha == hoy
        ).first()
        if not tiene_hoy:
            u = db.query(UsuarioDB).filter(UsuarioDB.id == v.usuario_id).first()
            sin_preop.append({
                "id": v.id, "placa": v.placa, "proveedor": v.proveedor,
                "usuario_nombre": u.proveedor or u.nombre if u else "—",
                "usuario_email": u.email if u else "—"
            })
    return {"fecha": hoy.isoformat(), "total_sin_preop": len(sin_preop), "vehiculos": sin_preop}

# ==================== Health Check ====================

@app.get("/health")
def health():
    """Verificar que la API está funcionando"""
    return {"status": "ok"}

# ==================== Servir HTML (al final para dar prioridad a endpoints de API) ====================

@app.get("/")
def servir_interfaz():
    """Redirigir a login.html"""
    return FileResponse(os.path.join(os.path.dirname(os.path.abspath(__file__)), "login.html"), media_type="text/html")

@app.get("/favicon.ico")
def favicon():
    """Servir favicon"""
    archivo_favicon = os.path.join(os.path.dirname(os.path.abspath(__file__)), "favicon.ico")
    if os.path.exists(archivo_favicon):
        return FileResponse(archivo_favicon, media_type="image/x-icon")
    return {"status": "ok"}

@app.get("/ala.png")
def servir_logo():
    archivo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ala.png")
    if os.path.exists(archivo):
        return FileResponse(archivo, media_type="image/png")
    return {"error": "Logo no encontrado"}

@app.get("/styles.css")
def servir_css():
    archivo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "styles.css")
    if os.path.exists(archivo):
        return FileResponse(archivo, media_type="text/css")
    return {"error": "CSS no encontrado"}

@app.get("/sw.js")
def servir_sw():
    archivo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sw.js")
    if os.path.exists(archivo):
        return FileResponse(archivo, media_type="application/javascript")
    return {"error": "sw.js no encontrado"}

@app.get("/manifest.json")
def servir_manifest():
    archivo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manifest.json")
    if os.path.exists(archivo):
        return FileResponse(archivo, media_type="application/json")
    return {"error": "manifest no encontrado"}

@app.get("/deprisa.png")
def servir_deprisa():
    archivo = os.path.join(os.path.dirname(os.path.abspath(__file__)), "deprisa.png")
    if os.path.exists(archivo):
        return FileResponse(archivo, media_type="image/png")
    return {"error": "imagen no encontrada"}

@app.get("/{filename}")
def servir_pagina(filename: str):
    """Servir archivos HTML específicos - Colocado al FINAL para no interferir con endpoints de API"""
    archivos_permitidos = ["login.html", "crear_vehiculo.html", "ver_vehiculos.html", "historial_vehiculos.html", "index.html", "recuperar_contrasena.html", "admin.html","registro.html","recuperar_contrasena.html"]
    
    if filename not in archivos_permitidos:
        return {"error": "Página no encontrada"}
    
    archivo_html = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    if os.path.exists(archivo_html):
        return FileResponse(archivo_html, media_type="text/html")
    return {"error": f"{filename} no encontrado"}

# Si ejecutas este archivo directamente
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)