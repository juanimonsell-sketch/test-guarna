from db import obtener_conexion


def existe_superposicion(id_cancha, id_socio, inicio, fin):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        """SELECT 1 FROM reservas
           WHERE estado = 'confirmada'
             AND (cancha_id = %s OR socio_id = %s)
             AND inicio < %s AND fin > %s
           LIMIT 1""",
        (id_cancha, id_socio, fin, inicio)
    )
    resultado = cursor.fetchone()
    cursor.close()
    conexion.close()
    return resultado is not None


def existe_reserva_confirmada_superpuesta(id_cancha, inicio, fin):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        """SELECT 1 FROM reservas
           WHERE estado = 'confirmada'
             AND cancha_id = %s
             AND inicio < %s AND fin > %s
           LIMIT 1""",
        (id_cancha, fin, inicio)
    )
    resultado = cursor.fetchone()
    cursor.close()
    conexion.close()
    return resultado is not None


def crear_reserva(id_socio, id_cancha, inicio, fin, tarifa_hora, total):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        """INSERT INTO reservas (socio_id, cancha_id, inicio, fin, estado, tarifa_hora, total)
           VALUES (%s, %s, %s, %s, 'confirmada', %s, %s)""",
        (id_socio, id_cancha, inicio, fin, tarifa_hora, total)
    )
    conexion.commit()
    id_reserva = cursor.lastrowid
    cursor.close()
    conexion.close()
    return id_reserva


def obtener_reserva_por_id(id_reserva):
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT * FROM reservas WHERE id = %s", (id_reserva,))
    reserva = cursor.fetchone()
    cursor.close()
    conexion.close()
    return reserva


def actualizar_estado(id_reserva, nuevo_estado):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("UPDATE reservas SET estado = %s WHERE id = %s", (nuevo_estado, id_reserva))
    conexion.commit()
    cursor.close()
    conexion.close()


def listar_reservas(filtros, limit, offset):
    condiciones = []
    params = []

    if filtros.get('id_cancha'):
        condiciones.append("cancha_id = %s")
        params.append(filtros['id_cancha'])
    if filtros.get('id_socio'):
        condiciones.append("socio_id = %s")
        params.append(filtros['id_socio'])
    if filtros.get('estado'):
        condiciones.append("estado = %s")
        params.append(filtros['estado'])
    if filtros.get('fecha_desde'):
        condiciones.append("DATE(inicio) >= %s")
        params.append(filtros['fecha_desde'])
    if filtros.get('fecha_hasta'):
        condiciones.append("DATE(inicio) <= %s")
        params.append(filtros['fecha_hasta'])

    where = ""
    if condiciones:
        where = "WHERE " + " AND ".join(condiciones)

    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)

    cursor.execute(f"SELECT COUNT(*) AS total FROM reservas {where}", params)
    total = cursor.fetchone()['total']

    cursor.execute(
        f"SELECT * FROM reservas {where} ORDER BY inicio LIMIT %s OFFSET %s",
        params + [limit, offset]
    )
    reservas = cursor.fetchall()

    cursor.close()
    conexion.close()
    return reservas, total
