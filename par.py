from datetime import datetime
from urllib.parse import urlencode
from repositories.canchas import obtener_cancha_por_id
from repositories.socios import obtener_socio_por_id
from repositories.reservas import (
    existe_superposicion, obtener_reserva_por_id,
    actualizar_estado, crear_reserva as crear_reserva_db, listar_reservas as listar_reservas_db,
)
from validators.reservas import validar_body_reserva, validar_body_estado
from utils import construir_error_api

def construir_links(url_base, filtros, limit, offset, total):
    def href(nuevo_offset):
        params = dict(filtros)
        params['_limit'] = limit
        params['_offset'] = nuevo_offset
        return f'{url_base}?{urlencode(params)}'

    links = {'_first': {'href': href(0)}}
    if offset > 0:
        links['_prev'] = {'href': href(max(offset - limit, 0))}
    if offset + limit < total:
        links['_next'] = {'href': href(offset + limit)}
    if total > 0:
        ultimo_offset = ((total - 1) // limit) * limit
        links['_last'] = {'href': href(ultimo_offset)}
    return links

def construir_reserva_dto(reserva):
    return {
        'id': reserva['id'],
        'id_socio': reserva['socio_id'],
        'id_cancha': reserva['cancha_id'],
        'fecha_hora_inicio': reserva['inicio'].strftime('%Y-%m-%dT%H:%M:%S.%f-03:00'),
        'fecha_hora_fin': reserva['fin'].strftime('%Y-%m-%dT%H:%M:%S.%f-03:00'),
        'estado': reserva['estado'],
        'precio_hora': reserva['tarifa_hora'],
        'precio_total': reserva['total'],
    }

def crear_reserva(body):
    datos = validar_body_reserva(body)

    cancha = obtener_cancha_por_id(datos['id_cancha'])
    if cancha is None or not cancha['activa']:
        raise ValueError(construir_error_api(
            code='cancha.not_found', message='Cancha no encontrada',
            description=f"No existe una cancha activa con el id {datos['id_cancha']}"
        ), 404)

    socio = obtener_socio_por_id(datos['id_socio'])
    if socio is None or not socio['activo']:
        raise ValueError(construir_error_api(
            code='socio.not_found', message='Socio no encontrado',
            description=f"No existe un socio activo con el id {datos['id_socio']}"
        ), 404)

    if existe_superposicion(datos['id_cancha'], datos['id_socio'], datos['inicio'], datos['fin']):
        raise ValueError(construir_error_api(
            code='reserva.conflicto_horario', message='Horario no disponible',
            description='La cancha o el socio ya tienen una reserva en ese horario'
        ), 409)

    horas = (datos['fin'] - datos['inicio']).total_seconds() / 3600
    tarifa_hora = cancha['precio_hora']
    total = int(tarifa_hora * horas)

    id_reserva = crear_reserva_db(datos['id_socio'], datos['id_cancha'], datos['inicio'], datos['fin'], tarifa_hora, total)
    return construir_reserva_dto(obtener_reserva_por_id(id_reserva))

def obtener_reserva(id_reserva):
    reserva = obtener_reserva_por_id(id_reserva)
    if reserva is None:
        raise ValueError(construir_error_api(
            code='reserva.not_found', message='Reserva no encontrada',
            description=f'No existe una reserva con el id {id_reserva}'
        ), 404)
    return construir_reserva_dto(reserva)

def es_transicion_valida(estado_actual, estado_nuevo, reserva):
    ahora = datetime.now()
    if estado_actual == 'confirmada' and estado_nuevo == 'cancelada':
        return ahora < reserva['inicio']
    if estado_actual == 'confirmada' and estado_nuevo == 'finalizada':
        return ahora >= reserva['fin']
    return False

def cambiar_estado_reserva(id_reserva, body):
    nuevo_estado = validar_body_estado(body)
    reserva = obtener_reserva_por_id(id_reserva)
    if reserva is None:
        raise ValueError(construir_error_api(
            code='reserva.not_found', message='Reserva no encontrada',
            description=f'No existe una reserva con el id {id_reserva}'
        ), 404)

    if nuevo_estado == reserva['estado']:
        return

    if not es_transicion_valida(reserva['estado'], nuevo_estado, reserva):
        raise ValueError(construir_error_api(
            code='reserva.transicion_invalida', message='Transición de estado no permitida',
            description=f"No se puede pasar de '{reserva['estado']}' a '{nuevo_estado}' en este momento"
        ), 409)

    actualizar_estado(id_reserva, nuevo_estado)

def listar_reservas(query_args, url_base):
    limit = int(query_args.get('_limit', 10))
    offset = int(query_args.get('_offset', 0))

    filtros = {
        'id_cancha': query_args.get('id_cancha'),
        'id_socio': query_args.get('id_socio'),
        'estado': query_args.get('estado'),
        'fecha_desde': query_args.get('fecha_desde'),
        'fecha_hasta': query_args.get('fecha_hasta'),
    }

    reservas, total = listar_reservas_db(filtros, limit, offset)

    filtros_para_links = {}
    for clave, valor in filtros.items():
        if valor:
            filtros_para_links[clave] = valor

    reservas_dto = [construir_reserva_dto(r) for r in reservas]

    return {
        'reservas': reservas_dto,
        '_links': construir_links(url_base, filtros_para_links, limit, offset, total),
    }