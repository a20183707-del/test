# Video: captura real y guion académico

La [captura real local](../output/playwright/demo-real-gemini.webm) dura **3:47,08** (227,08 segundos): WebM VP8, 1536 × 1024, sin audio. Muestra ejecución fácil, caso difícil/fallo, revisor, intentos, continuidad, tasa y tokens del lote real. El archivo está ignorado por Git y no se publica como binario en el repositorio. La explicación académica final y narración quedan pendientes; esta captura ya acredita los segmentos de ejecución.

SHA-256: `BD62DDF5DE0CF9E6644E27439294371D3BBB229A152919DC327CBE1D3112007B`. El fotograma de 195 segundos se decodificó e inspeccionó: muestra datos, evidencia del revisor y 30.912 tokens. La credencial se configuró fuera del video.

El lote grabado terminó con **1 exitoso, 3 parciales y 1 fallido: 20% automático**, 18 llamadas reales y 30.912 tokens totales informados. No se cambiaron los ejemplos ni la referencia para elevar la tasa. La captura no convierte los contratos sintéticos en documentos originales reales ni mide exactitud humana.

Guion previsto para el video académico completo: 28 minutos; límite: 30 minutos. La versión explicativa final debe contextualizar dominio, esquema, causas de parciales/fallo y límites de medición, conservando los resultados grabados.

## Antes de grabar

- Ejecutar `iniciar.bat` y comprobar que la aplicación abre.
- Usar los contratos sintéticos de `examples/contracts/` para evitar exponer datos personales.
- Definir manualmente el esquema y revisar la referencia elaborada. Dejar explícito si sigue pendiente la revisión humana independiente. La aplicación no propone campos mediante Gemini.
- Usar la configuración actual autorizada y el reporte real final: 20%, un exitoso, tres parciales y un fallido. El bloqueo del proyecto anterior es histórico.
- Mantener cualquier ingreso de credencial fuera de captura, con el campo de contraseña. No mostrarla en terminal, código, variables, registros ni capturas.
- Identificar cada captura y prueba por su ejecución efectiva. Completar la explicación académica sobre la captura real verificada; distinguir las pruebas inyectadas del lote de Gemini.

## Secuencia de grabación

| Tiempo | Pantalla y acción | Evidencia que se explica |
|---|---|---|
| 00:00–02:00 | Presentar la aplicación y la consigna | Recibe archivos o texto libre, usa un esquema explícito y entrega resultados validados por documento. Aclarar que estos contratos son sintéticos. |
| 02:00–06:00 | Cargar cinco TXT y revisar los nueve campos | Mostrar numérico, fecha y categorías; distinguir obligatorios y opcionales. Explicar `null` y la prohibición de inventar valores. |
| 06:00–09:00 | Pegar un texto de otro documento y definir campos manualmente | Demostrar que el flujo admite otros dominios. Confirmar el esquema antes de analizar; mostrar configuración secundaria y estado «Sin ejecutar». |
| 09:00–13:00 | Ejecutar un contrato completo con Gemini | Capturar los estados reales de lectura, extracción, validación y revisión; mostrar campo, valor y evidencia del resultado efectivamente obtenido. |
| 13:00–17:00 | Analizar el contrato sin tarifa y el formulario vacío | Mostrar ausencia, resultado parcial o fallo y motivo. Verificar que los demás documentos siguen procesándose. Conservar lo que realmente ocurra. |
| 17:00–20:00 | Ejecutar pruebas automatizadas de errores inyectados | Mostrar recuperación ante JSON inválido, error de tipos/proveedor, discrepancia y límite de intentos. Identificar claramente que son pruebas deterministas; no decir que Gemini produjo esos fallos. |
| 20:00–23:00 | Abrir revisión, historial de intentos y supervisión | Mostrar pregunta neutral, comprobación de la fuente, evidencia, severidad y propuesta. Comparar versiones y registrar revisión humana conservando el resultado automático. Explicar el aviso bajo 70% de éxito, visible desde tres procesados o al cerrar un lote no vacío. Si no existe una discrepancia real, usar la prueba inyectada con su etiqueta. |
| 23:00–26:00 | Exportar JSON/CSV y revisar métricas e histórico de tokens | Definir éxito como exitosos/procesados, separar parciales y fallidos. Mostrar actualización al finalizar cada llamada y consumo por extracción, revisión y comprobación, con intento, modelo, tiempo y acumulado de sesión. Distinguir estimación de texto, metadatos reales, «—» desconocido y «≥» incompleto. Comparar con referencia explícita y declarar su estado de revisión. |
| 26:00–28:00 | Mostrar estructura modular y evidencia de pruebas | Explicar entrada, esquema, proveedor, validación, revisor, pipeline y reportes; señalar límites y pendientes concretos. |

## Criterios de cierre de la grabación

El video debe conservar los resultados que realmente produjo la ejecución, aunque no todos sean exitosos. No editar la pantalla para aparentar otra tasa. El caso de fallo manejado y la continuidad del lote deben ser visibles. Los datos sintéticos, los fallos inyectados y las extracciones reales del proveedor requieren etiquetas diferentes.

Una corrección humana no eleva la tasa automática ni modifica su historial. La estimación por caracteres no incluye todo el costo del proceso y no equivale a una factura; las llamadas sin metadatos conservan el estado desconocido. Mostrar cierre de sesión sin capturar una credencial.

Los segmentos reales de ejecución están grabados y verificados en el WebM indicado. Queda completar la explicación académica final, incluyendo dominio/esquema y causas: el segundo contrato agotó intentos por discrepancia de negación en renovación; el tercero no tiene tarifa; el cuarto es ambiguo; el quinto está vacío. Después de añadir narración, medir nuevamente la duración final y comprobar que no supera 30 minutos. No se presenta una animación ni una prueba inyectada como ejecución real.
