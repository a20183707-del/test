# Lista de verificación para la entrega

Estado revisado el 4 de octubre de 2026. Esta lista registra evidencia disponible; no asigna una nota ni declara completadas las pruebas pendientes.

## Fuentes comprobadas

- [Consigna oficial en Markdown](https://github.com/arojaspa76/Repo-Fundamentos-Arquitectura-LLM/blob/main/projects/Proyecto_03_Extractor_de_Datos_Estructurados_desde_Documentos.md): leída completa, incluidas las doce secciones y la rúbrica.
- [Consigna oficial en DOCX](https://github.com/arojaspa76/Repo-Fundamentos-Arquitectura-LLM/blob/main/projects/Proyecto_03_Extractor_de_Datos_Estructurados_desde_Documentos.docx): descargada y leída completa mediante `consigna-docx.txt`. SHA-256: `904765217588EBD344D1088714AD14B815B18ED577A5CAD1AFC97D57BA3D39E3`. El original se conserva fuera del repositorio; el hash identifica la versión revisada.
- Ambas versiones establecen los mismos requisitos sustantivos. No se detectaron exigencias adicionales ni diferencias de pesos entre ellas. Los controles extra solicitados por el usuario se distinguen al final.

**Estados:** «Verificado local» acredita código o ejecución de pruebas locales; «Preparado» acredita un archivo disponible; «Pendiente real» exige ejecutar y conservar evidencia del proveedor o de la grabación. Un doble de pruebas no se considera una extracción real.

El lote final real terminó con **1 exitoso, 3 parciales y 1 fallido: 20% automático**, 18 llamadas y 30.912 tokens totales informados. Las cinco fuentes son contratos sintéticos; su carga mantuvo procedencia no declarada y no se infieren originales reales. La denegación del proyecto anterior y el error de esquema del revisor son antecedentes superados en la configuración actual. `GEMINI_LIVE_CHECK.md` conserva esa secuencia y `REAL_GEMINI_BATCH_REPORT.json`/`.csv` el resultado final, sin secretos. La referencia y los textos no se modificaron para elevar la tasa.

## Requisitos funcionales y arquitectura

| Requisito de la consigna | Evidencia disponible | Estado | Trabajo pendiente |
|---|---|---|---|
| Convertir texto libre de un dominio en registros JSON y explicar los fallos | Aplicación genérica; reporte real sobre cinco contratos con datos, estados y motivos | Verificado local y real | Incorporar resultado en el video académico. |
| Esquema explícito de al menos seis campos, con número, fecha y categoría | `schema.fields.json` y `schema.json`: nueve campos, tipos variados, obligatoriedad y `null` documentados | Verificado local | Presentar el esquema utilizado en el video. |
| Utilizar salida estructurada nativa del proveedor | Adaptador, pruebas y lote final real con esquema nativo corregido | Verificado local y real | Explicar la adaptación sin retirar límites locales. |
| Validar la respuesta por código, independientemente del proveedor | `validation.py`; pruebas y validación efectiva del lote real | Verificado local y real | Explicar campos ausentes y reglas en el video. |
| Procesar cinco documentos distintos; sintéticos realistas admitidos | Cinco contratos TXT con hashes distintos y reporte real completo | Verificado local y real | Ninguno para el procesamiento; narración pendiente. |
| Preparar casos deliberadamente difíciles | Lote real: ausencia de tarifa, ambigüedad y formulario vacío; soporte discrepante | Verificado local y real | Mostrar y narrar un caso difícil en el video final. |
| Reportar resultado completo, incompleto o fallido por documento y su motivo | Reporte real: uno exitoso, tres parciales y uno fallido, con razones | Verificado local y real | Ninguno para el reporte; explicación audiovisual pendiente. |
| Aislar un fallo y continuar con los documentos siguientes | Prueba de JSON inválido seguida de éxito; lote real completo e historial de rechazos aislados | Verificado local y real | Incorporar continuidad en el video final. |
| Reintentar JSON inválido con un máximo definido | Tests de JSON inválido y límites; contrato 02 agotó tres extracciones por discrepancia semántica real | Verificado local y agotamiento real | Distinguir JSON inválido inyectado de la discrepancia real al narrar. |
| Separar esquema, extracción, validación/reintento y reportes | `src/bsg_extractor/schema.py`, `providers.py`, `validation.py`, `pipeline.py`, `reports.py` | Verificado local | Mostrar la separación y explicar decisiones en la presentación. |
| Ejecutar el lote y calcular la tasa final | Reporte final real: 1/5, 20%; ausencias, ambigüedad, discrepancia y formulario vacío | Verificado local y real | Narrar causas y aclarar que tasa no es exactitud. |
| Manejar credenciales de forma segura | `SECURITY_REVIEW.md`, sesiones efímeras, clave en cabecera, errores sanitizados y pruebas de no exposición; catálogo aceptado HTTP 200 | Verificado local y consulta real | Mantener la misma protección al repetir generación; no publicar la key. |

## Entregables y rúbrica

| Entregable / criterio | Peso del curso | Evidencia disponible | Estado y pendiente |
|---|---:|---|---|
| Repositorio: funcionamiento y código | 30 | Código modular, esquema, cinco documentos, pruebas y reporte real final | Verificado local y real; sincronización final con GitHub pendiente del cierre. |
| Seguridad y separación de responsabilidades | 20 | Revisión independiente, correcciones y regresiones; auditoría de dependencias; módulos separados | Verificado local dentro del alcance documentado. No constituye una certificación ni garantiza seguridad absoluta. |
| Extracción validada y manejo de errores | 25 | Pruebas, revisión real, ausencia, ambigüedad, agotamiento y fallo documentados | 100 pruebas consolidadas pasaron, una advertencia de desarrollo. Lote final verificado; narración del video pendiente. |
| Documentación de esquema y validación | 10 | `examples/contracts/README.md`, esquema, notas de referencia, `TASK_SPEC.md` y `SECURITY_REVIEW.md` | Preparado; actualizar cualquier pendiente únicamente al obtener evidencia. |
| Video de hasta treinta minutos | 15 | WebM real de 3:47,08 con extracción, revisión, fallo, continuidad, intentos, tasa y tokens; guion académico en `VIDEO.md` | Captura verificada sin audio. Explicación académica final/narración pendiente; medir nuevamente la versión final. |
| Reporte del lote completo | Entregable obligatorio | JSON/CSV deterministas separados del reporte real final: 20%, tres parciales y un fallido | Preparado y verificado real. Conserva los resultados efectivos sin alterar fixtures ni referencia. |

Los pesos suman 100 puntos. La evidencia registrada no implica una calificación concedida por el profesor.

## Contenido obligatorio del video

| Lo que debe verse o explicarse | Evidencia preparada | Estado |
|---|---|---|
| Dominio elegido y justificación del esquema | Contratos de servicios: identidad, partes, fechas, importe, moneda, servicio y renovación | Guion preparado; explicación académica final pendiente. |
| Extracción correcta de un documento fácil en vivo | Contrato 01 exitoso real; el 02 quedó parcial por discrepancia | Ejecución y captura verificadas; narración final pendiente. |
| Documento difícil en vivo y respuesta del sistema | Contratos 03/04 parciales y 05 fallido reales; tests inyectados separados | Ejecución y captura verificadas; narración final pendiente. |
| Tasa del lote completo y causas comunes de los fallos | Reporte y captura final 20%; ausencia, ambigüedad, negación discrepante y campos vacíos | Resultado y tasa grabados; explicación final de causas pendiente. |
| Duración máxima | Captura real medida: 3:47,08; guion académico de 28 minutos | Captura bajo el máximo. Revalidar duración tras completar narración. |

## Verificación de cierre

- [x] Esquema formal y validación programática comprobados localmente.
- [x] Fallo controlado con continuidad demostrado mediante pruebas deterministas identificadas.
- [x] Reporte local distingue los tres estados y sus motivos.
- [x] Intento real del lote de cinco documentos con Gemini y reporte de rechazo conservado.
- [x] Resultado final del lote completo con extracción y revisión independientes verificadas.
- [x] Captura real con documento fácil, caso difícil, continuidad, tasa, intentos y tokens; duración comprobada de 3:47,08.
- [ ] Explicación académica final/narración de la captura real y comprobación de la versión final del video.
- [ ] Sincronización final del código y los entregables autorizados con GitHub, sin secretos ni datos privados.

## Alcance adicional solicitado por el usuario

La interfaz genérica define campos manualmente y conserva intentos. El revisor y la comprobación neutral contrastan el original en contextos separados; no certifican autenticidad. `LIVE_FLOW_VERIFICATION.json` muestra avance de llamadas/tokens, revisión aprobada real, versiones preservadas y bloqueo de JSON inválido en revisión humana. El lote registró 7 extracciones, 7 revisiones y 4 comprobaciones; 30.912 tokens totales informados en 18 llamadas. Supervisión bajo 70% visible; sus correcciones no elevan la tasa automática. Cero errores observados de navegador y móvil de 390 px sin desbordamiento. El bloqueo del proyecto anterior es histórico.

La aplicación local y la validación visual cuentan con evidencia en `UI_VERIFICATION.json` y `LIVE_FLOW_VERIFICATION.json`; el arranque Windows se consolida en el cierre. La referencia sintética aún no tiene revisión humana independiente; ello limita comparar exactitud, sin añadir exigencias a la rúbrica. `EDIFICA.md` conserva sólo historial; sus originales no son un requisito adicional ni condición de la aplicación genérica.

Captura local: `output/playwright/demo-real-gemini.webm`, WebM VP8 1536 × 1024 sin audio. SHA-256 `BD62DDF5DE0CF9E6644E27439294371D3BBB229A152919DC327CBE1D3112007B`; no se sube como binario a Git. El pendiente audiovisual se limita a la explicación académica final/narración y comprobación de esa versión, no a las ejecuciones ya capturadas.
