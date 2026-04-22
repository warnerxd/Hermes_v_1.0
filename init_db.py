from database import SessionLocal, engine, Base
from models import UsuarioDB, VehiculoDB, ProveedorDB, HistorialVehiculoDB
import bcrypt

def _hash(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

# Crear las tablas
Base.metadata.drop_all(bind=engine)  # Limpiar tablas anteriores
Base.metadata.create_all(bind=engine)

# Crear sesión
db = SessionLocal()

# Agregar usuarios de ejemplo
usuarios_ejemplo = [
    UsuarioDB(nombre="Demo", email="demo@demo.com", contraseña=_hash("123456"), proveedor="Transportes XYZ", rol="usuario"),
    UsuarioDB(nombre="Eduar Vargas", email="eduar.vargas@deprisa.com", contraseña=_hash("123456"), proveedor="Deprisa", rol="admin"),
    
]

db.add_all(usuarios_ejemplo)
db.commit()

# Agregar vehículos de ejemplo para los usuarios (ahora con nuevos campos)
vehiculos_ejemplo = [
    VehiculoDB(
        usuario_id=1, 
        placa="ABC-123", 
        tonelaje="5000 kg",
        ciudad="Bogotá",
        marca="Volvo",
        modelo="2016",
        cedula="1234567890",
        mes_inscripcion=1, 
        año_inscripcion=2024
    ),
    VehiculoDB(
        usuario_id=1, 
        placa="XYZ-789", 
        tonelaje="3000 kg",
        ciudad="Medellín",
        marca="Hino",
        modelo="2022",
        cedula="9876543210",
        mes_inscripcion=6, 
        año_inscripcion=2023
    ),
    VehiculoDB(
        usuario_id=2, 
        placa="DEF-456", 
        tonelaje="7000 kg",
        ciudad="Cali",
        marca="Scania",
        modelo="2020",
        cedula="5555555555",
        mes_inscripcion=3, 
        año_inscripcion=2025
    ),
]

db.add_all(vehiculos_ejemplo)
db.commit()

# Agregar proveedores de ejemplo
proveedores_ejemplo = [
    ProveedorDB(proveedor="Transportes XYZ"),
    ProveedorDB(proveedor="Logística ABC"),
    ProveedorDB(proveedor="Empresa de Fletes"),
    ProveedorDB(proveedor="Distribuidora Rápida"),
    ProveedorDB(proveedor="P&P"),
    ProveedorDB(proveedor="Vercurrier"),
    ProveedorDB(proveedor="Logiex"),
    ProveedorDB(proveedor="Triffit"),
    ProveedorDB(proveedor="DistriTransport"),
]

db.add_all(proveedores_ejemplo)
db.commit()

# Agregar historial de ejemplo para los vehículos
historial_ejemplo = [
    HistorialVehiculoDB(vehiculo_id=1, mes=1, año=2026, descripcion="Documentos enero"),
    HistorialVehiculoDB(vehiculo_id=1, mes=2, año=2026, descripcion="Documentos febrero"),
    HistorialVehiculoDB(vehiculo_id=2, mes=1, año=2026, descripcion="Comprobantes enero"),
    HistorialVehiculoDB(vehiculo_id=3, mes=2, año=2026, descripcion="Reportes febrero"),
]

db.add_all(historial_ejemplo)
db.commit()

print("✅ Base de datos inicializada exitosamente")
print("\nUsuarios de prueba:")
print("- Email: demo@demo.com / Contraseña: 123456")
print("- Email: eduar.vargas.com / Contraseña: 123456")
print("\n📦 Proveedores registrados: 9")
print("📋 Vehículos con nueva estructura: 3")
print("📅 Registros de historial: 4")
print("\n✨ Nuevos campos disponibles:")
print("   - Ciudad, Marca, Modelo, Cédula")
print("   - PDFs separados: Certificado Aliado, Certificado Latin, NIT")

db.close()