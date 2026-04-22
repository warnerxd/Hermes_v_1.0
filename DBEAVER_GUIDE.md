# Guía Rápida: SQLite + DBeaver

## Paso 1: Verificar que la Base de Datos existe

Después de ejecutar `python init_db.py`, verificar que existe el archivo:
```
c:\Users\skate\Documents\fast_api\usuarios.db
```

## Paso 2: Iniciar el Servidor
```bash
uvicorn main:app --reload
```

Abrirá automáticamente en: http://127.0.0.1:8000

## Paso 3: Probar la API

- Agrega, edita y elimina usuarios desde la interfaz visual
- Todos los cambios se guardan en la BD SQLite

## Paso 4: Visualizar en DBeaver

1. Abre DBeaver
2. Conecta a `usuarios.db` (ver README.md para pasos detallados)
3. Verás la tabla `usuarios` con todos los datos
4. Puedes hacer consultas SQL directamente

## Comandos Útiles en DBeaver

```sql
-- Ver estructura de la tabla
PRAGMA table_info(usuarios);

-- Insertar usuario manualmente
INSERT INTO usuarios (nombre, email, edad) VALUES ('Carlos', 'carlos@example.com', 28);

-- Actualizar usuario
UPDATE usuarios SET edad = 26 WHERE nombre = 'Juan';

-- Eliminar usuario
DELETE FROM usuarios WHERE id = 1;

-- Ver total de usuarios
SELECT COUNT(*) FROM usuarios;
```

## Notas

- La BD se crea automáticamente en SQLite
- Los datos persisten entre ejecuciones
- Puedes usar DBeaver para ver/editar directamente
- Los cambios en DBeaver se reflejan en la API inmediatamente
