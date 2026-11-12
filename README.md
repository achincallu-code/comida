# Sazón Express

Panel de administración de restaurante y delivery construido con Flask, Python, SQLite/PostgreSQL, HTML, CSS y JavaScript. La interfaz incluye dashboard, registro de pedidos, seguimiento y estadísticas calculadas con los pedidos guardados.

## Funciones

- Dashboard con pedidos recientes, ventas, estados y gráficas de los últimos siete días.
- Portal para consumidores con el menú y formulario seguro para registrar pedidos.
- Vista de cocina para trabajadores con cola de órdenes, búsqueda, filtros e indicadores de estado.
- Catálogo con los platillos y precios originales del sistema.
- Registro de cliente, teléfono, cantidad, entrega y notas; el servidor valida los datos y calcula el importe.
- Búsqueda por cliente, producto o teléfono y filtro por estado.
- Cambio de estado entre Pendiente, Preparando, Entregado y Cancelado.
- Eliminación de pedidos con confirmación.
- Estadísticas con ventas no canceladas, estados y actividad reciente.
- Almacenamiento local en SQLite o PostgreSQL con Neon.
- Marca y fondo ilustrado del restaurante con tarjetas y controles Liquid Glass responsivos.

## Requisitos

- Python 3.9 o posterior.
- Las dependencias listadas en `requirements.txt`.

## Ejecutar en Windows

Desde PowerShell, en la carpeta del proyecto:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Abre <http://127.0.0.1:5000/>.

La aplicación utiliza `pedidos.db` en esta carpeta cuando `DATABASE_URL` no está definida. Si se configura `DATABASE_URL`, conecta con PostgreSQL (por ejemplo, Neon). En ambos motores solo crea la tabla si aún no existe; no borra ni reinicia los pedidos.

## Conectar Neon y desplegar en Render

1. Crea una base de datos/proyecto en Neon y copia su cadena de conexión PostgreSQL. Mantén su configuración SSL y no la publiques en el repositorio.
2. Sube este proyecto a un repositorio Git y crea un Web Service en Render conectándolo a ese repositorio. Render puede detectar la configuración de `render.yaml`.
3. En las variables de entorno del servicio de Render, configura `DATABASE_URL` con la URL de Neon. Render genera `SECRET_KEY`; conserva `FLASK_DEBUG=false`.
4. Render instala las dependencias, crea la tabla con `CREATE TABLE IF NOT EXISTS` y arranca Gunicorn. La creación reintenta hasta cuatro veces ante desconexiones transitorias de PostgreSQL. `/health` está configurado como health check.

Si el despliegue falla con `SSL connection has been closed unexpectedly`, verifica en Render que `DATABASE_URL` sea la cadena copiada del proyecto de Neon (incluye `sslmode=require`), que el endpoint/proyecto de Neon esté activo y que el valor se haya guardado sin comillas, espacios ni saltos de línea. No compartas esa cadena en logs públicos ni en chats. El reintento cubre cortes momentáneos durante el arranque; no corrige una URL, contraseña o endpoint incorrectos.

Para conectar desde PowerShell, define las variables antes de ejecutar la app:

```powershell
$env:DATABASE_URL = "tu-url-de-conexion-de-neon"
$env:SECRET_KEY = "una-clave-local-larga-y-aleatoria"
python app.py
```

Sin `DATABASE_URL`, la aplicación sigue usando `pedidos.db`.

**Importante sobre los pedidos guardados:** cambiar de SQLite a Neon cambia el destino de las lecturas y escrituras. Los pedidos existentes en `pedidos.db` permanecen intactos en tu equipo, pero no se copian automáticamente a Neon. Antes de usar Neon, migra/exporta esos pedidos explícitamente si necesitas que aparezcan en la base remota. No subas `pedidos.db` al repositorio.
