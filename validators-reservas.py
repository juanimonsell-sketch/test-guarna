import re       #Libreria nativa para trabajar con Regular Expresions
from datetime import datetime
from utils import construir_error_api

PATRON_FECHA = re.compile(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}-03:00$')
CAMPOS_RESERVA = ('id_socio', 'id_cancha', 'fecha_hora_inicio', 'fecha_hora_fin')
ESTADOS_VALIDOS = ('confirmada', 'cancelada', 'finalizada')

def parsear_fecha(valor, nombre):
    if not PATRON_FECHA.match(str(valor)):
        raise ValueError(construir_error_api(
            code=f'reserva.{nombre}.formato_invalido',
            message=f"Formato inválido en '{nombre}'",
            description="Debe tener el formato YYYY-MM-DDTHH:MM:SS.ffffff-03:00"
        ), 400)
    # Eliminamos la zona horaria del final (-03:00) para quedarnos unicamente con la fecha y la hora
    return datetime.strptime(valor[:-6], '%Y-%m-%dT%H:%M:%S.%f')

def validar_body_reserva(body):
    for campo in CAMPOS_RESERVA:
        if campo not in body:
            raise ValueError(construir_error_api(
                code=f'required.{campo}',
                message=f"Campo requerido: '{campo}'",
                description=f"El campo '{campo}' es obligatorio"
            ), 400)

    inicio = parsear_fecha(body['fecha_hora_inicio'], 'fecha_hora_inicio')
    fin = parsear_fecha(body['fecha_hora_fin'], 'fecha_hora_fin')

    if inicio.minute != 0 or inicio.second != 0 or fin.minute != 0 or fin.second != 0:
        raise ValueError(construir_error_api(
            code='reserva.horario_invalido',
            message='El horario debe ser en punto',
            description="Los minutos y segundos deben ser 00"
        ), 400)

    if inicio >= fin:
        raise ValueError(construir_error_api(
            code='reserva.intervalo_invalido',
            message='El inicio debe ser anterior al fin',
            description="fecha_hora_inicio tiene que ser menor a fecha_hora_fin"
        ), 400)

    if inicio.date() != fin.date():
        raise ValueError(construir_error_api(
            code='reserva.atraviesa_medianoche',
            message='La reserva no puede atravesar la medianoche',
            description="fecha_hora_inicio y fecha_hora_fin deben ser del mismo día"
        ), 400)

    duracion_horas = (fin - inicio).total_seconds() / 3600
    if duracion_horas < 1 or duracion_horas > 3:
        raise ValueError(construir_error_api(
            code='reserva.duracion_invalida',
            message='Duración fuera de rango',
            description="La reserva debe durar entre 1 y 3 horas"
        ), 400)

    if inicio.hour < 8 or fin.hour > 23:
        raise ValueError(construir_error_api(
            code='reserva.fuera_de_horario',
            message='Fuera del horario permitido',
            description="El club opera de 08:00 a 23:00"
        ), 400)

    if inicio <= datetime.now():
        raise ValueError(construir_error_api(
            code='reserva.fecha_pasada',
            message='La reserva debe ser a futuro',
            description="fecha_hora_inicio ya pasó"
        ), 400)

    return {'id_socio': body['id_socio'], 'id_cancha': body['id_cancha'], 'inicio': inicio, 'fin': fin}

def validar_body_estado(body):
    estado = body.get('estado')
    if estado not in ESTADOS_VALIDOS:
        raise ValueError(construir_error_api(
            code='reserva.estado_invalido',
            message='Estado inválido',
            description=f"El estado debe ser uno de: {', '.join(ESTADOS_VALIDOS)}"
        ), 400)
    return estado
