# Pruebas y validación

La [validación continua](https://github.com/acamposcar/ha-avamet/actions/workflows/ci.yml)
ejecuta las pruebas, Ruff, hassfest y la comprobación de HACS. El resultado
de cada ejecución indica qué commit se ha validado; no implica compatibilidad
con todas las versiones futuras de Home Assistant ni con todas las estaciones.

## Ejecutar las comprobaciones

Se necesita Python 3.14 y [uv](https://docs.astral.sh/uv/). Desde la raíz del
repositorio:

```bash
uv sync --locked --group dev
uv run ruff check .
uv run ruff format --check .
uv run pytest --cov --cov-report=term-missing
```

La versión de Home Assistant utilizada en las pruebas se declara en
[`pyproject.toml`](../pyproject.toml); `uv.lock` fija las dependencias. La cobertura
mínima exigida está en la configuración de pytest-cov del mismo archivo.
El número de pruebas y su cobertura actual se muestran en cada ejecución de CI.

## Qué se comprueba

- Analizador: medidas opcionales, números europeos, fechas, contenido inválido,
  acumulados de lluvia, reinicio a medianoche, huecos y gráficas retrasadas.
- Transporte: tiempos de espera, reintentos acotados, errores HTTP, cancelación
  y límites de descarga, con respuestas simuladas y un servidor HTTP local.
- Coordinador: consultas compartidas, caché en memoria, caducidad de las
  observaciones y gestión de temporizadores, incluido el cambio horario.
- Configuración: validación de IDs, estaciones duplicadas y opciones fuera de rango.
- Entidades: medidas disponibles, unidades, lluvia, condiciones meteorológicas,
  diagnósticos y estaciones con capacidades parciales.
- Ciclo de vida: carga y descarga de una entrada y recuperación del alta
  cuando falla la conexión.

Las pruebas usan clases reales de Home Assistant y directorios temporales.
No consultan AVAMET ni acceden a instalaciones de usuarios. Los casos de estaciones
parciales son sintéticos: no prueban que cualquier estación real esté operativa.

## Validadores de integración

El [workflow](../.github/workflows/ci.yml) ejecuta hassfest para comprobar los
metadatos, traducciones y estructura de la integración, y la acción de HACS
para validar sus requisitos como repositorio personalizado.

La comprobación de marcas externas de HACS se omite porque el icono propio
se distribuye dentro del componente. Pasar estos validadores no incorpora
automáticamente el proyecto al catálogo por defecto de HACS.

## Comprobación manual de una estación

Después de instalar y añadir la integración:

1. Comparar el nombre, la fecha y las mediciones con la página pública de la estación.
2. Comprobar que solo se crean las entidades que admite la estación.
3. Verificar que «Última observación» avanza con las publicaciones de AVAMET.
4. Contrastar la lluvia reciente con la gráfica, no con el acumulado del día.
5. Revisar los diagnósticos y la disponibilidad de las entidades si la fuente
   no se actualiza o falla una consulta.

Estas comprobaciones son independientes de CI. Una lectura válida no garantiza
disponibilidad continua ni que la estructura del HTML no cambie.
