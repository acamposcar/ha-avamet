# Migración desde el script y las plantillas

La integración nueva utiliza IDs únicos por estación y puede crear entidades
con nombres distintos a los del paquete antiguo. No intenta fusionar ni
migrar historiales. No es necesario borrar bases de datos, `.storage` ni
estadísticas de otras integraciones para empezar con las nuevas entidades.

1. Instalar `custom_components/avamet` mediante HACS o manualmente.
2. Validar la configuración antes del reinicio y revisar cualquier otro cambio
   pendiente: reiniciar Core también aplica cambios ajenos a AVAMET.
3. Reiniciar y añadir **AVAMET** desde **Ajustes → Dispositivos y servicios**,
   con el ID `c13m207e02` u otra estación. Verificar dispositivo, entidades,
   fecha observada y diagnósticos.
4. Sustituir las referencias al paquete antiguo en paneles y automatizaciones.
   El sensor de texto nuevo usa un enum `raining` / `dry`, traducido en la
   interfaz a «Lloviendo» / «No llueve». En automatizaciones se debe utilizar
   el binario `on` / `off`, comprobando disponibilidad.
5. Desactivar la inclusión del paquete `packages/avamet_rafelbunyol.yaml`.
   Crear una copia recuperable, validar YAML y ejecutar `ha core check` antes
   de aplicar los cambios; recargar solo lo necesario.
6. Tras comprobar la integración nueva, archivar el antiguo script y su caché.
   Si se desea eliminar historial, hacerlo solo para entidades AVAMET mediante
   las funciones de Home Assistant, nunca borrando la base de datos completa.

Se puede probar inicialmente junto al paquete antiguo, pero ambos consultarían
la web: conviene limitar ese periodo y retirar uno cuando la migración termine.
No instalar simultáneamente ArnyminerZ/ha-avamet: usa el mismo dominio `avamet`.

## Recuperación

Si falla la instalación, retirar o desactivar la nueva entrada, restaurar la
copia del paquete antiguo, validar y recargar las plataformas necesarias.
No sobrescribir archivos modificados por el usuario durante la migración.
