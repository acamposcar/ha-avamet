# Arquitectura

Una entrada de configuración representa una estación. Su ID normalizado es la
identidad estable tanto de la entrada como del dispositivo y sus entidades.
Dos estaciones no comparten datos, caché ni temporizadores; añadir el mismo ID
dos veces se rechaza antes de consultar la red.

```text
config_flow → AvametClient → parser → Observation
                                  ↓
                        AvametCoordinator / Snapshot
                                  ↓
                     sensor · binary_sensor · weather
```

## Responsabilidades

- `parser.py`: HTML público a observación tipada, números europeos, campos
  opcionales, acumulados de lluvia y cobertura temporal de la gráfica. Sin
  acceso a red, disco o Home Assistant.
- `models.py`: observaciones inmutables, fechas reales y estado del transporte.
  Una lectura no se mezcla con campos de observaciones anteriores.
- `api.py`: sesión HTTP compartida, HTTPS fijo, ID validado, respuesta limitada
  a 2 MiB, dos intentos de ocho segundos y pausa de un segundo. Los errores 4xx,
  redirecciones, HTML inválido y respuestas demasiado grandes no se reintentan.
  El analizador se ejecuta fuera del bucle de eventos.
- `coordinator.py`: una descarga por estación y ciclo, recuperación automática
  y caché exclusivamente en memoria. Respeta `Retry-After` numérico de HTTP
  429, limitado entre cinco minutos y una hora.
- `entity.py`: identidad del dispositivo y disponibilidad compartida.
- Plataformas: describen unidades y clases de sensores; no descargan datos.
- `diagnostics.py`: solo información de esta estación y sus opciones, nunca
  configuración general de Home Assistant, credenciales ni archivos privados.

## Antigüedad y fallos

La frescura se calcula con `observed_at`, no con la hora de descarga. Un
temporizador hace que las entidades caduquen al alcanzar el límite incluso
cuando el intervalo de consulta es más largo. Se cancela al recibir otra
observación o descargar la entrada.

Si falla la red o el formato, una última observación reciente puede mantener
temperatura, humedad, viento y acumulados, con `from_cache: true`. Lluvia
reciente, estado de lluvia y condición meteorológica pasan a desconocidos.
Sin caché reciente, las entidades quedan no disponibles. Una página accesible
pero con una observación congelada tampoco mantiene sensores disponibles.

No se persiste esta caché ni se restaura tras reiniciar. El alta inicial
fallida utiliza el reintento de configuración de Home Assistant.

## Estaciones parciales

El nombre, la fecha y al menos una medida interpretable son obligatorios.
Presión, humedad, viento, temperaturas extremas y lluvia son opcionales. Solo
se crean las entidades de medidas presentes en la primera lectura. Las de
lluvia reciente se crean para estaciones con pluviómetro, pero permanecen no
disponibles si falta una gráfica válida. Una estación sin temperatura no
crea `weather`.

Si una medida ya creada desaparece, esa entidad queda no disponible: no se
rellena con cero ni con el valor de otra lectura. Si la estación incorpora
hardware nuevo, recargar su entrada redetecta las capacidades.

## Lluvia y condiciones

La gráfica representa un acumulado diario. La lluvia reciente se calcula por
diferencias, contempla el reinicio a medianoche y rechaza huecos mayores de
siete minutos, gráficas retrasadas, valores negativos y bajadas del acumulado
dentro del mismo día. «Lloviendo» representa precipitación registrada en los
últimos diez minutos de la observación; no es un detector instantáneo en casa.

`weather` reconoce `rainy` y `windy`, con prioridad para lluvia y umbral de
viento configurable. Los demás casos tienen condición desconocida. La fuente
no informa de nubes, niebla, rayos ni visibilidad y no se deducen de la hora o
de la ausencia de lluvia. La racha máxima diaria no es la racha instantánea.
No se ofrece un pronóstico de AVAMET ni se añaden proveedores externos.

## Cambio de fuente

La API de proyectos de AVAMET exige credenciales que no tenemos. Cuando haya
acceso, se puede añadir otro transporte y analizador que produzcan
`Observation`, sin reescribir las entidades ni su control de caducidad.

## Calidad

Las pruebas usan clases reales de Home Assistant y configuración temporal:
analizador, transporte acotado, coordinador, formularios, identidad de estación,
entidades, diagnósticos y ciclo completo de carga/descarga. Las pruebas de red
usan respuestas simuladas; las comprobaciones contra AVAMET son manuales y
no forman parte de CI para evitar dependencia de su disponibilidad.
