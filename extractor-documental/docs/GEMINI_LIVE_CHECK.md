# Comprobación real de acceso a Gemini

Comprobaciones del 4 de octubre de 2026 contra el servicio de Google. Este documento conserva resultados sanitizados; no incluye claves, identificadores de proyectos ni respuestas crudas. Las solicitudes reales se distinguen de las pruebas inyectadas y los contratos utilizados siguen siendo sintéticos.

## Historial: primer proyecto con generación denegada

| Operación real | Resultado observado | Lo que acredita |
|---|---|---|
| `GET models` | HTTP 200; la respuesta devolvió 50 modelos y contenía los modelos configurados para extractor y revisor | La credencial fue aceptada para consultar el catálogo. |
| `POST generateContent` | HTTP 403, estado `PERMISSION_DENIED`; Google indicó: «Your project has been denied access. Please contact support.» | Google deniega la generación de contenido al proyecto asociado. No se recibió una extracción. |

La consulta aceptada no garantizaba permiso para generar contenido. Esa evidencia identificó un bloqueo del primer proyecto; no demostraba falta de clave. No se conoce aquí su causa administrativa ni se atribuye a cuota, facturación o contenido sin evidencia. Es un antecedente: la configuración actual ya obtuvo generación HTTP 200 desde otro proyecto autorizado por el usuario.

## Historial: lote de cinco denegaciones

El primer intento sobre cinco contratos sintéticos terminó con cinco fallidos, cero exitosos, cero parciales y 0% de éxito. La denegación ocurrió antes de obtener datos y el revisor no ejecutó llamadas. Ese intento es histórico; `REAL_GEMINI_BATCH_REPORT.json` y `.csv` contienen ahora la ejecución final corregida descrita abajo.

El histórico del lote registra cinco solicitudes de extracción con error. Google no informó consumo: los tokens se conservan como desconocidos, no como cero. Las comprobaciones de catálogo y diagnóstico se distinguen de las cinco llamadas del lote y no se agregan retrospectivamente a su ledger.

El primer reporte utilizó un mensaje local genérico de credencial/permisos. La comprobación posterior permite precisar el diagnóstico como bloqueo de generación del proyecto Google. El adaptador distingue una credencial inválida de esta denegación reconocida, con lectura acotada y un mensaje local sin detalles sensibles de la respuesta. El reporte original no debe interpretarse como prueba de que la clave sea incorrecta.

## Nueva configuración: extracción y compatibilidad del revisor

El usuario proporcionó una nueva credencial de otro proyecto. Cinco solicitudes de extracción obtuvieron HTTP 200 y devolvieron JSON real. Los totales informados por esas respuestas fueron **869, 850, 844, 874 y 779 tokens**, respectivamente. Una respuesta JSON recibida no significa por sí sola que el documento tenga estado final exitoso: todavía debe validarse y revisarse.

Las primeras cinco llamadas del revisor devolvieron HTTP 400 por el esquema de respuesta. El diagnóstico comparó el esquema nativo con `maxItems: 40` frente al mismo esquema sin esa restricción: el primero recibió HTTP 400; el segundo obtuvo HTTP 200, una decisión `approved` y **343 tokens informados**. Es evidencia de compatibilidad del esquema probado y de una revisión real individual, no de la tasa final del lote.

El adaptador omite `maxItems` al construir el esquema nativo. La validación local Pydantic conserva el máximo de 40 campos y los controles de cobertura. Las pruebas verifican ambas propiedades.

## Resultado final del lote corregido

El lote real terminó con **1 exitoso, 3 parciales y 1 fallido: 20% de éxito automático**. Se procesaron las cinco fuentes sin detener el lote. `REAL_GEMINI_BATCH_REPORT.json` y `.csv` conservan registros, motivos, evidencia del revisor y versiones.

| Documento sintético | Estado real | Motivo principal |
|---|---|---|
| 01 — contrato de limpieza | Exitoso | JSON y reglas locales válidos; campos contrastados por el revisor. |
| 02 — contrato de soporte | Parcial | Discrepancia sobre la negación en `auto_renewal`; agotó tres extracciones y seis llamadas de revisión/comprobación. |
| 03 — tarifa ausente | Parcial | No aparece `monthly_fee`, obligatorio. |
| 04 — condiciones ambiguas | Parcial | Fecha, tarifa y moneda sin valor inequívoco acordado. |
| 05 — formulario vacío | Fallido | No se recuperaron datos utilizables. |

Se registraron **18 llamadas reales: 7 extracciones, 7 revisiones y 4 comprobaciones**, con **30.912 tokens totales informados** y siete intentos de extracción. El total estuvo informado en las 18 llamadas; no se inventaron los desgloses de razonamiento o caché ausentes. Las llamadas de diagnóstico e intentos anteriores no se suman a este lote.

Las fuentes son los cinco contratos sintéticos preparados. La carga de la interfaz no declaró procedencia, por lo que el reporte conserva `undeclared_documents: 5` y no infiere originales reales. La procedencia conocida de estas fuentes se documenta aquí; llamadas reales al proveedor no convierten los documentos en originales reales.

`LIVE_FLOW_VERIFICATION.json` registra el avance observado de 0 llamadas sin conteo a 5/7.852 tokens, 6/8.791 y 18/30.912. Se comprobó aviso de supervisión bajo 70%, versiones conservadas, rechazo de JSON inválido en revisión humana, ausencia de errores de navegador y vista móvil de 390 px sin desbordamiento horizontal.

El resultado real difiere del esperado por las pruebas inyectadas. La referencia y los textos no se alteraron para elevar la tasa. La discrepancia del segundo contrato requiere revisión humana independiente; 20% es éxito operativo, no exactitud de campos frente a una referencia humana.

## Estado de los entregables

- Verificado históricamente: rechazo controlado, continuidad, reporte de cinco fallos, tasa de 0%, consumo desconocido y supervisión humana del primer intento.
- Verificado en la nueva configuración: extracción, revisión y comprobación reales; lote completo corregido, reportes JSON/CSV, 20% automático y 30.912 tokens informados.
- Verificado localmente: 100 pruebas pasaron, con una advertencia del TestClient de desarrollo.
- QA visual interno: se comprobó el flujo real, estados, versiones, tokens y casos difíciles. Sus capturas permanecen como evidencia local de desarrollo; no se cuentan como el video académico del usuario.
- Presentación personal: speech exacto preparado en el TXT local entregado al estudiante, excluido de Git; grabación y presentación pendientes del estudiante. Si ejecuta un nuevo lote, el guion identifica sus resultados visibles y distingue las cifras históricas.
- Pendiente de comparación: revisión humana independiente de la referencia elaborada. No se acredita exactitud humana por el solo juicio del modelo.

El bloqueo de generación del proyecto anterior ya no impide la ejecución actual. La nueva configuración está autorizada por el usuario; no se solicitan claves adicionales para completar el lote. Las correcciones y los resultados se documentan sin publicar secretos.
