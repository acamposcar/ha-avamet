# Cambios

## 0.1.0

- Integración nativa de Home Assistant con entrada y dispositivo por estación.
- Configuración por ID desde la interfaz y prevención de duplicados.
- Sensores opcionales según las capacidades de cada estación.
- Entidades de lluvia binaria y enum traducido, sin clase `moisture`.
- `weather` de observaciones, sin condiciones del cielo ni previsiones inventadas.
- Coordinador asíncrono, descargas acotadas, un reintento, caché reciente en
  memoria y caducidad por hora de observación.
- Traducciones en español, valenciano/catalán e inglés; icono propio.
- Estructura HACS, validadores de CI y pruebas automatizadas.
