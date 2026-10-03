# Migración desde otras configuraciones de AVAMET

Esta integración configura las estaciones desde la interfaz. No importa
automáticamente entradas de otros componentes, paquetes YAML, IDs de entidad
o historiales. Los nombres de las nuevas entidades pueden ser distintos.

No es necesario borrar bases de datos, `.storage` ni estadísticas para migrar.
Si solo se quiere añadir una estación nueva, seguir la [instalación](../README.md#instalación).

## Preparación

1. Crear una copia recuperable de la configuración anterior.
2. Anotar los IDs de estación y las entidades utilizadas en paneles,
   automatizaciones y scripts.
3. Revisar otros cambios pendientes antes de reiniciar: el reinicio también
   puede aplicar configuración ajena a AVAMET.

## Desde un script o sensores YAML

1. Instalar la integración mediante HACS o manualmente y reiniciar Home Assistant.
2. Añadir **AVAMET** desde **Ajustes → Dispositivos y servicios**, con el ID
   de la estación. Verificar nombre, fecha, mediciones y diagnósticos.
3. Sustituir las referencias a las entidades antiguas en paneles,
   automatizaciones y scripts por las nuevas.
4. Retirar únicamente la configuración del recolector anterior: su inclusión
   de paquete, sensores de comandos o plantillas y tareas programadas, según
   corresponda. Conservar cualquier configuración no relacionada con AVAMET.
5. Validar la configuración con la herramienta disponible para el tipo de
   instalación. Si se dispone de la CLI de Home Assistant, usar `ha core check`.
   Aplicar la recarga o el reinicio que requieran las plataformas modificadas.
6. Confirmar que las nuevas entidades siguen actualizándose antes de archivar
   el script, sus archivos auxiliares o su caché.

Se puede comparar brevemente con el recolector anterior, pero ambos consultarían
la web. Limitar ese periodo y retirar el recolector antiguo al terminar.

## Desde otro componente con dominio `avamet`

Dos integraciones con el mismo dominio no pueden convivir. Esto incluye
ArnyminerZ/ha-avamet: comparten la carpeta `custom_components/avamet`, pero no
se garantiza que sus entradas de configuración sean compatibles.

1. Tras crear la copia de seguridad y anotar las referencias, eliminar las
   entradas de la integración anterior desde **Dispositivos y servicios**.
2. Desinstalar el componente anterior mediante su procedimiento de instalación.
   No sobrescribir su carpeta mientras siga cargado.
3. Instalar este repositorio, reiniciar y crear nuevas entradas con los IDs
   de estación. Seguir la [guía de instalación](../README.md#instalación).
4. Revisar los IDs de las entidades y actualizar paneles y automatizaciones.
   No asumir que se conservarán el registro ni el histórico anteriores.

## Lluvia y paneles

- El sensor de estado usa `raining` / `dry`, traducidos en la interfaz a
  «Lloviendo» / «No llueve». Las automatizaciones no deben comparar las traducciones.
- El binario usa `on` / `off`, sin clase `moisture`. Sustituir disparadores
  dependientes de esa clase por disparadores de estado. Una transición explícita
  `off` → `on` excluye recuperaciones desde `unknown` o `unavailable`.
- La lluvia reciente se refiere a los últimos diez minutos observados,
  no al acumulado diario ni a un detector instantáneo en la vivienda.
- La entidad `weather` publica observaciones, no previsiones. Usar
  `show_forecast: false` y tener en cuenta que su condición puede ser desconocida
  aunque las mediciones numéricas sean válidas.

Ver los [ejemplos de tarjetas y automatización](../README.md#ejemplos).

## Histórico y recuperación

Renombrar una entidad no garantiza la fusión de historiales. Si el ID de destino
ya se utilizó, revisar las advertencias de Home Assistant antes de reutilizarlo.
Si se desea eliminar histórico, hacerlo solo para las entidades seleccionadas
mediante las funciones de Home Assistant, nunca borrando la base de datos completa.

Si falla la instalación, desactivar o retirar la nueva entrada y restaurar
la configuración anterior desde la copia. Para volver a otro componente con
el mismo dominio, retirar primero este componente y restaurar los archivos y
entradas anteriores. Validar y aplicar la recarga o reinicio necesarios.
No sobrescribir cambios posteriores del usuario al recuperar la copia.
