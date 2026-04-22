from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Date, CheckConstraint, Index
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class ProveedorDB(Base):
    __tablename__ = "proveedores"

    id        = Column(Integer, primary_key=True, index=True)
    proveedor = Column(String, unique=True, index=True, nullable=False)

    # Relaciones inversas
    usuarios  = relationship("UsuarioDB", back_populates="proveedor_rel")


class UsuarioDB(Base):
    __tablename__ = "usuarios"

    id           = Column(Integer, primary_key=True, index=True)
    email        = Column(String, unique=True, index=True, nullable=False)
    contraseña   = Column(String, nullable=False)
    nombre       = Column(String, index=True)
    proveedor    = Column(String, nullable=True)   # string de compatibilidad — usar proveedor_id
    proveedor_id = Column(
                       Integer,
                       ForeignKey("proveedores.id", ondelete="SET NULL"),
                       nullable=True,
                       index=True
                   )
    rol          = Column(String, default="usuario", nullable=False)   # "usuario" | "admin"
    telefono     = Column(String(20), nullable=True, unique=True)

    # Relaciones
    vehiculos           = relationship("VehiculoDB",          back_populates="propietario",  cascade="all, delete-orphan")
    tokens_recuperacion = relationship("TokenRecuperacionDB", back_populates="usuario",      cascade="all, delete-orphan")
    proveedor_rel       = relationship("ProveedorDB",         back_populates="usuarios")


class TokenRecuperacionDB(Base):
    __tablename__ = "tokens_recuperacion"

    id               = Column(Integer, primary_key=True, index=True)
    usuario_id       = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    codigo           = Column(String, unique=True, index=True, nullable=False)
    fecha_creacion   = Column(DateTime, default=datetime.utcnow)
    fecha_expiracion = Column(DateTime, nullable=False)
    usado            = Column(Integer, default=0, nullable=False)   # 0=pendiente | 1=usado

    # Relación
    usuario = relationship("UsuarioDB", back_populates="tokens_recuperacion")


class VehiculoDB(Base):
    __tablename__ = "vehiculos"

    id           = Column(Integer, primary_key=True, index=True)
    usuario_id   = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False, index=True)
    placa        = Column(String, unique=True, index=True, nullable=False)
    tonelaje     = Column(String, nullable=False)
    proveedor    = Column(String, nullable=True)
    marca        = Column(String, nullable=True, index=True)
    modelo       = Column(Integer, nullable=True)   # año del modelo (ej. 2019)
    ciudad       = Column(String, nullable=True)
    cedula       = Column(String, nullable=True)

    # Mes / año de inscripción con validación a nivel de BD
    mes_inscripcion = Column(
        Integer,
        CheckConstraint("mes_inscripcion >= 1 AND mes_inscripcion <= 12", name="ck_vehiculos_mes"),
        nullable=True
    )
    año_inscripcion = Column(
        Integer,
        CheckConstraint("año_inscripcion >= 1990 AND año_inscripcion <= 2100", name="ck_vehiculos_año"),
        nullable=True
    )

    soat                   = Column(Date, nullable=True)
    tecnomecanica          = Column(Date, nullable=True)

    # Rutas PDF por tipo de documento
    pdf_ruta               = Column(String, nullable=True)
    pdf_certificado_aliado = Column(String, nullable=True)
    pdf_certificado_latin  = Column(String, nullable=True)
    pdf_nit                = Column(String, nullable=True)
    pdf_soat               = Column(String, nullable=True)
    pdf_tecnomecanica      = Column(String, nullable=True)

    # Estado con índice para búsquedas rápidas en admin
    # -1 = rechazado | 0 = pendiente | 1 = activo
    activo               = Column(Integer, default=0, nullable=False, index=True)
    motivo_rechazo       = Column(String, nullable=True)
    motivo_pendiente     = Column(String, nullable=True)
    fecha_desactivacion  = Column(DateTime, nullable=True)

    # Relaciones
    propietario = relationship("UsuarioDB",         back_populates="vehiculos")
    historial   = relationship("HistorialVehiculoDB", back_populates="vehiculo", cascade="all, delete-orphan")
    auditoria   = relationship("AuditoriaDB",        back_populates="vehiculo",  cascade="all, delete-orphan")

    # Índice compuesto: búsquedas frecuentes de admin (estado + proveedor)
    __table_args__ = (
        Index("ix_vehiculos_activo_proveedor", "activo", "proveedor"),
    )


class HistorialVehiculoDB(Base):
    __tablename__ = "historial_vehiculos"

    id          = Column(Integer, primary_key=True, index=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id", ondelete="CASCADE"), nullable=False, index=True)
    mes         = Column(
        Integer,
        CheckConstraint("mes >= 1 AND mes <= 12", name="ck_historial_mes"),
        nullable=False
    )
    año         = Column(
        Integer,
        CheckConstraint("año >= 2000 AND año <= 2100", name="ck_historial_año"),
        nullable=False
    )
    descripcion  = Column(String, nullable=True)
    fecha_carga  = Column(DateTime, default=datetime.utcnow)

    # PDFs operacionales mensuales
    pdf_preoperacional        = Column(String, nullable=True)
    pdf_mantenimiento         = Column(String, nullable=True)
    pdf_mantenimiento_correctivo     = Column(String, nullable=True)   # primero cargado — usado para estadísticas
    pdfs_correctivo_adicionales      = Column(String, nullable=True)   # JSON array de cargas extras

    # Relación con carga de objetos optimizada
    vehiculo = relationship("VehiculoDB", back_populates="historial", lazy="joined")

    # Índice compuesto: evita duplicados mes/año por vehículo y acelera consultas
    __table_args__ = (
        Index("ix_historial_vehiculo_mes_año", "vehiculo_id", "mes", "año", unique=True),
    )


class PreoperacionalDiarioDB(Base):
    """Checklist vehicular diario — un registro por vehículo por día."""
    __tablename__ = "preoperacional_diario"

    id          = Column(Integer, primary_key=True, index=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id", ondelete="CASCADE"), nullable=False, index=True)
    usuario_id  = Column(Integer, ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    fecha       = Column(Date, nullable=False, index=True)

    # Sección 1 — Seguridad del vehículo
    frenos      = Column(Integer, default=0, nullable=False)
    llantas     = Column(Integer, default=0, nullable=False)
    direccion   = Column(Integer, default=0, nullable=False)
    sin_fugas   = Column(Integer, default=0, nullable=False)

    # Sección 2 — Visibilidad y señales
    luces_delanteras = Column(Integer, default=0, nullable=False)
    luces_traseras   = Column(Integer, default=0, nullable=False)
    direccionales    = Column(Integer, default=0, nullable=False)

    # Sección 3 — Motor y funcionamiento
    nivel_aceite      = Column(Integer, default=0, nullable=False)
    temperatura_motor = Column(Integer, default=0, nullable=False)

    # Sección 4 — Seguridad obligatoria
    extintor = Column(Integer, default=0, nullable=False)

    # Sección 5 — Documentación
    soat_doc_vigente  = Column(Integer, default=0, nullable=False)
    revision_tecnica  = Column(Integer, default=0, nullable=False)
    licencia_conduccion = Column(Integer, default=0, nullable=False)

    # Sección 6 — Conductor
    sin_alcohol_drogas   = Column(Integer, default=0, nullable=False)
    conductor_descansado = Column(Integer, default=0, nullable=False)

    observaciones   = Column(String, nullable=True)
    fecha_registro  = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_preop_vehiculo_fecha", "vehiculo_id", "fecha", unique=True),
    )


class HistorialEstadoVehiculoDB(Base):
    """Log inmutable de activaciones / desactivaciones por proveedor o admin."""
    __tablename__ = "historial_estado_vehiculo"

    id          = Column(Integer, primary_key=True, index=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id", ondelete="CASCADE"), nullable=False, index=True)
    usuario_id  = Column(Integer, ForeignKey("usuarios.id",  ondelete="SET NULL"), nullable=True,  index=True)
    accion      = Column(String, nullable=False)   # "activado" | "desactivado"
    fecha       = Column(DateTime, nullable=False)

    vehiculo = relationship("VehiculoDB", backref="historial_estado")
    usuario  = relationship("UsuarioDB",  foreign_keys=[usuario_id])


class AuditoriaDB(Base):
    """
    Registro inmutable de acciones admin sobre vehículos.
    Quién aprobó / rechazó, cuándo y por qué.
    """
    __tablename__ = "auditoria"

    id          = Column(Integer, primary_key=True, index=True)
    vehiculo_id = Column(Integer, ForeignKey("vehiculos.id", ondelete="CASCADE"), nullable=False, index=True)
    admin_id    = Column(Integer, ForeignKey("usuarios.id",  ondelete="SET NULL"), nullable=True,  index=True)
    accion      = Column(String, nullable=False)    # "aprobado" | "rechazado" | "pendiente"
    detalle     = Column(String, nullable=True)     # motivo del rechazo u observación
    fecha       = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relaciones
    vehiculo = relationship("VehiculoDB", back_populates="auditoria")
    admin    = relationship("UsuarioDB",  foreign_keys=[admin_id])