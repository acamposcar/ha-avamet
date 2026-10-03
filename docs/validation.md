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

## Pendiente para distribución y activación

- Publicar el repositorio público autorizado y ejecutar allí los workflows
  de GitHub, incluida la comprobación de HACS.
- Confirmar la instalación y descarga efectiva desde HACS. Tener su
  estructura y metadatos no equivale a estar en su catálogo por defecto.
- Migrar la instalación existente de Home Assistant tras revisar el efecto
  del reinicio y recibir autorización para aplicarlo.

La versión anterior no se ha retirado de la instalación existente, no se ha
borrado historial y no se ha reiniciado Core durante esta preparación.
