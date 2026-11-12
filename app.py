from contextlib import contextmanager
from datetime import date, datetime, timedelta
import os
from pathlib import Path
import sqlite3

import psycopg
from psycopg.rows import dict_row
from flask import Flask, flash, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "pedidos.db"
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "local-development-key-not-for-production")


def usa_postgresql():
    return bool(os.environ.get("DATABASE_URL", "").strip())

MENU = {
    "Hamburguesa clásica": 85.00,
    "Pizza individual": 99.00,
    "Tacos (orden)": 75.00,
    "Ensalada fresca": 68.00,
    "Papas a la francesa": 45.00,
    "Combo especial": 135.00
}
ENTREGAS = ["En el local", "Para recoger", "A domicilio"]
ESTADOS = ["Pendiente", "Preparando", "Entregado", "Cancelado"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
         "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


@contextmanager
def conectar():
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if database_url:
        if database_url.startswith("postgres://"):
            database_url = "postgresql://" + database_url.removeprefix("postgres://")
        elif database_url.startswith("postgresql+psycopg://"):
            database_url = "postgresql://" + database_url.removeprefix("postgresql+psycopg://")
        if not database_url.startswith("postgresql://"):
            raise RuntimeError("DATABASE_URL debe ser una URL de PostgreSQL de Neon.")
        conn = psycopg.connect(
            database_url,
            row_factory=dict_row,
            connect_timeout=10,
            prepare_threshold=None,
        )
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def ejecutar(conn, consulta, parametros=()):
    if isinstance(conn, sqlite3.Connection):
        return conn.execute(consulta, parametros)
    return conn.execute(consulta.replace("?", "%s"), parametros)


def crear_tabla():
    id_sql = "BIGSERIAL PRIMARY KEY" if usa_postgresql() else "INTEGER PRIMARY KEY AUTOINCREMENT"
    total_sql = "DOUBLE PRECISION NOT NULL" if usa_postgresql() else "REAL NOT NULL"
    with conectar() as conn:
        ejecutar(conn, f"""
            CREATE TABLE IF NOT EXISTS pedidos (
                id {id_sql},
                cliente TEXT NOT NULL,
                telefono TEXT NOT NULL,
                producto TEXT NOT NULL,
                cantidad INTEGER NOT NULL,
                entrega TEXT NOT NULL,
                notas TEXT,
                total {total_sql},
                estado TEXT DEFAULT 'Pendiente',
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def obtener_resumen():
    with conectar() as conn:
        fila = ejecutar(conn, """
            SELECT COUNT(*) AS pedidos,
                COALESCE(SUM(CASE WHEN estado = 'Pendiente' THEN 1 ELSE 0 END), 0) AS pendientes,
                COALESCE(SUM(CASE WHEN estado = 'Entregado' THEN 1 ELSE 0 END), 0) AS entregados,
                COALESCE(SUM(CASE WHEN estado != 'Cancelado' THEN total ELSE 0 END), 0) AS ventas
            FROM pedidos
        """).fetchone()
    return dict(fila)


def obtener_actividad(dias=7):
    hoy = date.today()
    fechas = [(hoy - timedelta(days=offset)) for offset in range(dias - 1, -1, -1)]
    postgres = usa_postgresql()
    desde = fechas[0] if postgres else fechas[0].isoformat()
    fecha_sql = "CAST(fecha AS DATE)" if postgres else "date(fecha)"
    with conectar() as conn:
        filas = ejecutar(conn, f"""
            SELECT {fecha_sql} AS dia, COUNT(*) AS pedidos,
                COALESCE(SUM(CASE WHEN estado != 'Cancelado' THEN total ELSE 0 END), 0) AS ventas
            FROM pedidos
            WHERE {fecha_sql} >= ?
            GROUP BY {fecha_sql}
            ORDER BY dia
        """, (desde,)).fetchall()
    por_fecha = {
        fila["dia"].isoformat() if isinstance(fila["dia"], date) else fila["dia"]: dict(fila)
        for fila in filas
    }
    return {
        "labels": [f"{fecha.day:02d} {MESES[fecha.month - 1][:3]}" for fecha in fechas],
        "pedidos": [por_fecha.get(fecha.isoformat(), {}).get("pedidos", 0) for fecha in fechas],
        "ventas": [por_fecha.get(fecha.isoformat(), {}).get("ventas", 0) for fecha in fechas],
    }


def procesar_pedido(destino="pedidos"):
    cliente = request.form.get("cliente", "").strip()
    telefono = request.form.get("telefono", "").strip()
    producto = request.form.get("producto", "")
    entrega = request.form.get("entrega", "")
    notas = request.form.get("notas", "").strip()
    try:
        cantidad = int(request.form.get("cantidad", "0"))
    except ValueError:
        cantidad = 0

    if not cliente or not telefono or not producto or not entrega:
        flash("Completa todos los campos obligatorios.", "error")
    elif len(cliente) < 3:
        flash("El nombre debe tener al menos 3 caracteres.", "error")
    elif not telefono.isdigit() or len(telefono) != 10:
        flash("El teléfono debe tener exactamente 10 dígitos.", "error")
    elif producto not in MENU or entrega not in ENTREGAS:
        flash("Selecciona opciones válidas del menú.", "error")
    elif cantidad < 1 or cantidad > 10:
        flash("La cantidad debe estar entre 1 y 10.", "error")
    else:
        total = MENU[producto] * cantidad
        with conectar() as conn:
            ejecutar(conn, """
                INSERT INTO pedidos (cliente, telefono, producto, cantidad, entrega, notas, total)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (cliente, telefono, producto, cantidad, entrega, notas, total))
        flash(f"Pedido registrado. Total: ${total:.2f}", "success")
        return redirect(url_for(destino))

    return render_template("index.html", menu=MENU, entregas=ENTREGAS, datos=request.form)


@app.route("/", methods=["GET", "POST"])
def inicio():
    if request.method == "POST":
        return procesar_pedido()
    with conectar() as conn:
        recientes = ejecutar(conn, "SELECT * FROM pedidos ORDER BY id DESC LIMIT 6").fetchall()
    ahora = datetime.now()
    return render_template(
        "dashboard.html",
        resumen=obtener_resumen(),
        recientes=recientes,
        actividad=obtener_actividad(),
        fecha_actual=(
            f"{DIAS[ahora.weekday()]}, {ahora.day:02d} de "
            f"{MESES[ahora.month - 1]} de {ahora.year}"
        ),
    )


@app.route("/nuevo-pedido", methods=["GET", "POST"])
def nuevo_pedido():
    if request.method == "POST":
        return procesar_pedido()
    return render_template("index.html", menu=MENU, entregas=ENTREGAS, datos={})


@app.route("/consumidores", methods=["GET", "POST"])
def consumidores():
    if request.method == "POST":
        return procesar_pedido(destino="consumidores")
    return render_template("index.html", menu=MENU, entregas=ENTREGAS, datos={})


@app.route("/trabajadores")
def trabajadores():
    busqueda = request.args.get("q", "").strip()
    estado = request.args.get("estado", "").strip()
    sql = "SELECT * FROM pedidos WHERE (cliente LIKE ? OR producto LIKE ? OR telefono LIKE ?)"
    params = [f"%{busqueda}%", f"%{busqueda}%", f"%{busqueda}%"]
    if estado in ESTADOS:
        sql += " AND estado = ?"
        params.append(estado)
    sql += " ORDER BY CASE estado WHEN 'Pendiente' THEN 0 WHEN 'Preparando' THEN 1 ELSE 2 END, id ASC"
    with conectar() as conn:
        registros = ejecutar(conn, sql, params).fetchall()
        resumen = ejecutar(conn, """
            SELECT COUNT(*) AS total,
                COALESCE(SUM(CASE WHEN estado = 'Pendiente' THEN 1 ELSE 0 END), 0) AS pendientes,
                COALESCE(SUM(CASE WHEN estado = 'Preparando' THEN 1 ELSE 0 END), 0) AS preparando
            FROM pedidos
            WHERE estado != 'Cancelado'
        """).fetchone()
    return render_template(
        "trabajadores.html",
        registros=registros,
        resumen=dict(resumen),
        busqueda=busqueda,
        estado=estado,
        estados=ESTADOS,
    )


@app.route("/pedidos")
def pedidos():
    busqueda = request.args.get("q", "").strip()
    estado = request.args.get("estado", "").strip()
    sql = "SELECT * FROM pedidos WHERE (cliente LIKE ? OR producto LIKE ? OR telefono LIKE ?)"
    params = [f"%{busqueda}%", f"%{busqueda}%", f"%{busqueda}%"]
    if estado in ESTADOS:
        sql += " AND estado = ?"
        params.append(estado)
    sql += " ORDER BY id DESC"
    with conectar() as conn:
        registros = ejecutar(conn, sql, params).fetchall()
    resumen = obtener_resumen()
    return render_template(
        "pedidos.html",
        registros=registros,
        total=resumen["pedidos"],
        ventas=resumen["ventas"],
        busqueda=busqueda,
        estado=estado,
        estados=ESTADOS,
    )


@app.route("/estadisticas")
def estadisticas():
    with conectar() as conn:
        recientes = ejecutar(conn, "SELECT * FROM pedidos ORDER BY id DESC LIMIT 8").fetchall()
    return render_template(
        "estadisticas.html",
        resumen=obtener_resumen(),
        actividad=obtener_actividad(14),
        recientes=recientes,
    )


@app.route("/estado/<int:pedido_id>", methods=["POST"])
def cambiar_estado(pedido_id):
    nuevo = request.form.get("estado", "")
    if nuevo in ESTADOS:
        with conectar() as conn:
            ejecutar(conn, "UPDATE pedidos SET estado = ? WHERE id = ?", (nuevo, pedido_id))
        flash("Estado del pedido actualizado.", "success")
    else:
        flash("Estado no válido.", "error")
    if request.form.get("origen") == "trabajadores":
        return redirect(url_for(
            "trabajadores",
            q=request.form.get("q", ""),
            estado=request.form.get("filtro_estado", ""),
        ))
    return redirect(url_for("pedidos", q=request.form.get("q", ""), estado=request.form.get("filtro_estado", "")))


@app.route("/eliminar/<int:pedido_id>", methods=["POST"])
def eliminar(pedido_id):
    with conectar() as conn:
        ejecutar(conn, "DELETE FROM pedidos WHERE id = ?", (pedido_id,))
    flash("Pedido eliminado.", "success")
    return redirect(url_for("pedidos", q=request.form.get("q", ""), estado=request.form.get("filtro_estado", "")))


@app.route("/health")
def health():
    return {"status": "ok", "app": "Pedido de alimentos"}


if __name__ == "__main__":
    crear_tabla()
    debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=debug)
