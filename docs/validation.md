# Validación de la versión inicial

Comprobada el 3 de octubre de 2026 con Home Assistant 2026.9.2 y Python 3.14.8
en un entorno aislado, sin usar configuración privada ni credenciales.

- 77 pruebas automatizadas pasan; cobertura del componente: aproximadamente 98 %.
- Ruff: análisis y formato correctos.
- Hassfest oficial de Home Assistant 2026.9.2: una integración revisada,
  cero integraciones inválidas; manifest, traducciones, dependencias y
  configuración aceptados.
- Prueba de ciclo completo: registro de 17 entidades para una estación
  completa, una consulta inicial compartida y descarga con limpieza del
  temporizador. También se comprueba el reintento de alta cuando falla la red.
- Transporte probado con un servidor HTTP local real, además de respuestas
  y fallos simulados.
- Consultas públicas manuales a `c13m207e02` (IES Rafelbunyol) y `c24m072e02`
  (Càmping Mariola): nombres limpios, fechas recientes y mediciones válidas.
- Estaciones parciales comprobadas con ejemplos sintéticos: temperatura
  sin humedad/presión/viento y pluviómetro sin temperatura. No se afirma
  haber probado todas las estaciones de AVAMET.

Las pruebas cubren acumulados diarios, medianoche, gráficas retrasadas,
huecos, valores inválidos, reintentos acotados, errores HTTP, cancelación,
límite de descarga, caché, caducidad, IDs duplicados y opciones fuera de rango.
La caducidad usa tiempo transcurrido en UTC, también durante el cambio horario.

## Publicación y validación en GitHub

El repositorio público [acamposcar/ha-avamet](https://github.com/acamposcar/ha-avamet)
contiene únicamente el proyecto de la integración, no la configuración privada
de Home Assistant. Se conserva el historial de los commits locales.

La [validación de GitHub Actions](https://github.com/acamposcar/ha-avamet/actions/runs/37128266134)
ha superado las pruebas con dependencias bloqueadas, Ruff, hassfest y HACS.
La primera comprobación de HACS detectó que faltaban la descripción y los temas
del repositorio; tras añadir esos metadatos, el reintento terminó correctamente.
La comprobación de marcas externas se omite porque el icono propio se distribuye
dentro del componente y no se ha solicitado su inclusión en el catálogo oficial.

## Pendiente en Home Assistant

- Confirmar la instalación y descarga efectiva desde HACS. Tener su
  estructura y metadatos no equivale a estar en su catálogo por defecto.
- Migrar la instalación existente de Home Assistant tras revisar el efecto
  del reinicio y recibir autorización para aplicarlo.

La versión anterior no se ha retirado de la instalación existente, no se ha
borrado historial y no se ha reiniciado Core durante esta preparación.
