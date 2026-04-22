from database import SessionLocal
from models import ProveedorDB

db = SessionLocal()
proveedores = db.query(ProveedorDB).all()

print(f'Total proveedores en BD: {len(proveedores)}')
if len(proveedores) > 0:
    for p in proveedores:
        print(f'- {p.proveedor}: {p.placa} ({p.tonelaje})')
else:
    print('NO HAY PROVEEDORES EN LA BASE DE DATOS')

db.close()
