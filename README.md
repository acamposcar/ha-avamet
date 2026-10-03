# AVAMET para Home Assistant

Integración de observaciones públicas de AVAMET, configurable desde la interfaz
y preparada para HACS como repositorio personalizado. Un dispositivo por
estación y una consulta compartida por sus entidades.

> Proyecto independiente, no oficial de AVAMET. Versión inicial 0.1.0.
> La publicación en GitHub y la migración de la instalación existente son
> pasos separados; este código no reinicia ni modifica Home Assistant por sí solo.

## Qué ofrece

- Añadir varias estaciones por ID, con detección de duplicados.
- Crear solo los sensores que admite cada estación: temperatura, mínima y
  máxima, humedad, presión, viento, dirección y precipitación diaria,
  mensual y anual.
- Lluvia de los últimos cinco y diez minutos, cuando la gráfica lo permite.
- Estado «Lloviendo / No llueve» y binario para automatizaciones.
- Entidad `weather` para estaciones con temperatura.
- Reintento ante fallos breves y caducidad real de las observaciones.
- Diagnósticos, dispositivo agrupado, traducciones en español,
  valenciano/catalán e inglés, e icono propio.
- Sin procesos externos, plantillas YAML por estación ni dependencias de
  Python adicionales a las de Home Assistant.

«Lloviendo» significa lluvia registrada en los últimos diez minutos de la
observación. No se deduce del acumulado del día ni de la humedad.

## Instalación

Requiere Home Assistant **2026.9 o posterior**; las pruebas se ejecutan con
2026.9.2 y Python 3.14.

### HACS

El repositorio público está disponible en
[acamposcar/ha-avamet](https://github.com/acamposcar/ha-avamet):

1. Abrir **HACS → Repositorios personalizados**.
2. Añadir `https://github.com/acamposcar/ha-avamet`, categoría **Integración**.
3. Descargar y reiniciar Home Assistant.
4. Ir a **Ajustes → Dispositivos y servicios → Añadir integración → AVAMET**.
5. Introducir el ID de la estación, por ejemplo `c13m207e02`.

Es compatibilidad con repositorios personalizados, no inclusión automática
en el catálogo por defecto de HACS. El repositorio debe ser público y contener
únicamente esta integración.

### Manual

Copiar la carpeta `custom_components/avamet` a la carpeta
`custom_components` de la configuración de Home Assistant. Validar, reiniciar
y añadir la integración desde la interfaz.

No instalar junto a ArnyminerZ/ha-avamet: ambas usan el dominio `avamet`.
Para pasar del script anterior, consultar [Migración](docs/migration.md).

## Configuración

El ID aparece en la URL de la estación de AVAMET:
`https://www.avamet.org/mxo_i.php?id=c13m207e02`.

No hay un ID predeterminado ni nombres de entidad ligados al IES Rafelbunyol.
Se admiten IDs con el formato público de AVAMET; la estación debe devolver
nombre, fecha y al menos una medida válida. Esto no garantiza que cualquier
ID existente esté en línea o que todas las estaciones tengan los mismos datos.

En las opciones de cada entrada:

| Opción | Predeterminado | Rango |
| --- | --- | --- |
| Intervalo de consulta | 5 minutos | 5–60 minutos |
| Antigüedad máxima | 20 minutos | 5–120 minutos |
| Umbral de viento fuerte | 40 km/h | 1–200 km/h |

El límite de antigüedad se aplica también entre consultas. Si cambia el
equipamiento de una estación, recargar su entrada redetecta las capacidades.

## Datos y disponibilidad

Una observación válida alimenta todas las entidades sin descargas individuales.
Se conservan sus fechas reales de observación y de descarga.

Ante un fallo de red o formato se puede reutilizar la última lectura reciente
**solo en memoria**. Los datos meteorológicos disponibles permanecen, pero la
lluvia reciente y su estado quedan desconocidos. La entidad «Última observación»
expone `from_cache`, `last_error`, `rain_error`, fechas y URL de origen.
Una respuesta HTTP 429 respeta el tiempo de espera y deja la actualización
fallida visible a Home Assistant.

Cuando la observación caduca, las entidades quedan no disponibles, aunque la
web siga respondiendo. No se persiste la caché ni se recupera después de reiniciar.

Una medida ausente no se convierte en cero. Si la gráfica de lluvia falta,
está retrasada o tiene huecos, no se ocultan temperatura, humedad u otras
medidas correctas.

### Condición meteorológica

`weather` publica temperatura, humedad, presión, velocidad y dirección del
viento cuando existen. Su condición puede ser:

- `rainy`: lluvia registrada en los últimos diez minutos.
- `windy`: sin lluvia registrada y viento actual por encima del umbral.
- Desconocida: las mediciones no permiten determinar otra condición.

No llueve **no significa soleado**. Esta página no aporta nubosidad,
visibilidad, niebla o rayos; no se inventan `sunny`, `cloudy` ni `clear-night`.
La racha máxima del día es un atributo aparte, no la racha instantánea.
No incluye pronóstico ni consulta proveedores externos.

El enum de lluvia usa estados internos `raining` / `dry`, traducidos en la
interfaz. Para automatizaciones, usar preferentemente el binario `on` / `off`
y comprobar que esté disponible.

### Panel

Las entidades aparecen agrupadas en el dispositivo de cada estación.
Una tarjeta de tiempo debe utilizar `show_forecast: false`, porque aquí se
publican observaciones, no previsiones. Para el estado «No llueve», añadir
el sensor de estado de lluvia: la condición `weather` puede ser desconocida
mientras los valores numéricos siguen disponibles.

## Desarrollo

```bash
uv sync --locked --group dev
uv run ruff check .
uv run ruff format --check .
uv run pytest --cov --cov-report=term-missing
```

Las pruebas no consultan AVAMET ni acceden a una instalación real. Utilizan
clases reales de Home Assistant con configuración temporal y transporte
simulado. CI incluye también hassfest y la validación de HACS.

Todo lo necesario en tiempo de ejecución está dentro de
`custom_components/avamet`. No se instalan bibliotecas nuevas, no se leen
credenciales y los diagnósticos no exportan configuración privada.

Ver [Arquitectura](docs/architecture.md) y [Cambios](CHANGELOG.md).

## Fuente y API

Actualmente se analiza el HTML público de AVAMET. Sigue existiendo el riesgo
de que cambie su estructura, pero está aislado en el analizador y cubierto por
pruebas.

La [API de proyectos de AVAMET documentada por Deltares](https://publicwiki.deltares.nl/spaces/FEWSDOC/pages/343966199/AVAMET)
exige `proj_id` y `token`; no se ha encontrado una API anónima documentada
para estas observaciones. Para sustituir HTML hace falta acceso autorizado
y confirmar los campos y el histórico de precipitación disponibles.
[Contacto de AVAMET](https://www.avamet.org/avamet.php?id=s06c00t01).

## Referencias y licencia

[ArnyminerZ/ha-avamet](https://github.com/ArnyminerZ/ha-avamet) sirvió como
referencia del enfoque nativo y HACS. Al revisar el proyecto no declaraba una
licencia de reutilización, por lo que este componente no copia su código ni
sus imágenes. Conserva y refactoriza los cálculos del script propio.

Código e icono propios bajo [licencia MIT](LICENSE). No incorpora logotipos
oficiales ni afirma relación o aprobación de AVAMET o Home Assistant.
