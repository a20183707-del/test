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
| Convertir texto libre de un dominio en registros JSON y explicar los fallos | Aplicación genérica; reporte real sobre cinco contratos con datos, estados y motivos | Verificado local y real | Grabar la presentación personal usando el speech preparado. |
| Esquema explícito de al menos seis campos, con número, fecha y categoría | `schema.fields.json` y `schema.json`: nueve campos, tipos variados, obligatoriedad y `null` documentados | Verificado local | Explicarlo en la grabación personal. |
| Utilizar salida estructurada nativa del proveedor | Adaptador, pruebas y lote final real con esquema nativo corregido | Verificado local y real | Ninguno en código; explicación preparada. |
| Validar la respuesta por código, independientemente del proveedor | `validation.py`; pruebas y validación efectiva del lote real | Verificado local y real | Ninguno en código; explicación preparada. |
| Procesar cinco documentos distintos; sintéticos realistas admitidos | Cinco contratos TXT con hashes distintos y reporte real completo | Verificado local y real | Ninguno para el procesamiento. |
| Preparar casos deliberadamente difíciles | Lote real: ausencia de tarifa, ambigüedad y formulario vacío; soporte discrepante | Verificado local y real | Mostrar los resultados reales en el video personal. |
| Reportar resultado completo, incompleto o fallido por documento y su motivo | Reporte real: uno exitoso, tres parciales y uno fallido, con razones | Verificado local y real | Ninguno para el reporte. |
| Aislar un fallo y continuar con los documentos siguientes | Prueba de JSON inválido seguida de éxito; lote real completo e historial de rechazos aislados | Verificado local y real | Mostrar continuidad en el video personal. |
| Reintentar JSON inválido con un máximo definido | Tests de JSON inválido y límites; contrato 02 agotó tres extracciones por discrepancia semántica real | Verificado local y agotamiento real | Distinguir pruebas inyectadas de la discrepancia real al presentar. |
| Separar esquema, extracción, validación/reintento y reportes | `src/bsg_extractor/schema.py`, `providers.py`, `validation.py`, `pipeline.py`, `reports.py` | Verificado local | Ninguno en arquitectura; explicación preparada. |
| Ejecutar el lote y calcular la tasa final | Reporte final real: 1/5, 20%; ausencias, ambigüedad, discrepancia y formulario vacío | Verificado local y real | Si se ejecuta otro lote, presentar sus cifras efectivas. |
| Manejar credenciales de forma segura | `SECURITY_REVIEW.md`, sesiones efímeras, clave en cabecera, errores sanitizados y pruebas de no exposición; catálogo aceptado HTTP 200 | Verificado local y consulta real | Mantener la misma protección al repetir generación; no publicar la key. |

## Entregables y rúbrica

| Entregable / criterio | Peso del curso | Evidencia disponible | Estado y pendiente |
|---|---:|---|---|
| Repositorio: funcionamiento y código | 30 | Código modular, esquema, cinco documentos, pruebas y reporte real final | Verificado local y real. Código sincronizado con GitHub en `970943e47fad62eedfbc14f406a1a456ef1745dd`. |
| Seguridad y separación de responsabilidades | 20 | Revisión independiente, correcciones y regresiones; auditoría de dependencias; módulos separados | Verificado local dentro del alcance documentado. No constituye una certificación ni garantiza seguridad absoluta. |
| Extracción validada y manejo de errores | 25 | Pruebas, revisión real, ausencia, ambigüedad, agotamiento y fallo documentados | 100 pruebas consolidadas pasaron, una advertencia de desarrollo. Lote real verificado. |
| Documentación de esquema y validación | 10 | `examples/contracts/README.md`, esquema, notas de referencia, `TASK_SPEC.md` y `SECURITY_REVIEW.md` | Preparado; actualizar cualquier pendiente únicamente al obtener evidencia. |
| Video de hasta treinta minutos | 15 | Speech exacto de 8–10 minutos con acciones y frases condicionales en el TXT local entregado al estudiante, excluido de Git | Grabación personal y presentación pendientes del estudiante. El material interno de QA no se cuenta como su video entregado. |
| Reporte del lote completo | Entregable obligatorio | JSON/CSV deterministas separados del reporte real final: 20%, tres parciales y un fallido | Preparado y verificado real. Conserva los resultados efectivos sin alterar fixtures ni referencia. |

Los pesos suman 100 puntos. La evidencia registrada no implica una calificación concedida por el profesor.

## Lectura orientativa del código como evaluador

Funcionalidad, arquitectura, validación/manejo de errores y documentación cuentan con evidencia verificable. La tasa automática de 20% no implica que el pipeline se haya detenido: procesó los cinco documentos, conservó ausencias y discrepancias y reportó sus causas. Los límites de seguridad y de exactitud están documentados; cien tests no certifican seguridad absoluta ni precisión humana.

El criterio de video queda provisionalmente sin acreditar (**0/15 en esta autoevaluación**) hasta que el estudiante grabe y presente su explicación. Los demás pesos no se convierten automáticamente en puntos concedidos y no se asigna una nota oficial. Esta lectura es una autoevaluación orientativa basada en los archivos y ejecuciones descritos.

## Contenido obligatorio del video

| Lo que debe verse o explicarse | Evidencia preparada | Estado |
|---|---|---|
| Dominio elegido y justificación del esquema | Speech: contratos como ejemplos de una herramienta genérica; nueve campos y sus tipos | Preparado para leer; grabación personal pendiente. |
| Extracción correcta de un documento fácil en vivo | Contrato 01 exitoso histórico; variantes del speech según estado nuevo | Código/resultado verificados; mostrar resultado efectivo en la grabación personal. |
| Documento difícil en vivo y respuesta del sistema | Contratos 03/04 parciales y 05 fallido históricos; tests inyectados separados | Código/resultado verificados; grabación personal pendiente. |
| Tasa del lote completo y causas comunes de los fallos | Histórico real 20%; ausencia, ambigüedad, negación discrepante y campos vacíos | Speech preparado. Si hay nuevo lote, sus cifras mandan. |
| Duración máxima | Speech previsto de 8–10 minutos | Medir la grabación personal final y comprobar hasta 30 minutos. No se exige pista de audio en la consigna. |

## Verificación de cierre

- [x] Esquema formal y validación programática comprobados localmente.
- [x] Fallo controlado con continuidad demostrado mediante pruebas deterministas identificadas.
- [x] Reporte local distingue los tres estados y sus motivos.
- [x] Intento real del lote de cinco documentos con Gemini y reporte de rechazo conservado.
- [x] Resultado final del lote completo con extracción y revisión independientes verificadas.
- [x] Speech exacto y acciones de demostración preparados para la grabación personal.
- [x] Código sincronizado con GitHub: `970943e47fad62eedfbc14f406a1a456ef1745dd` verificado.
- [ ] Grabación personal y presentación del video por el estudiante, hasta 30 minutos.

## Alcance adicional solicitado por el usuario

La interfaz genérica define campos manualmente y conserva intentos. El revisor y la comprobación neutral contrastan el original en contextos separados; no certifican autenticidad. `LIVE_FLOW_VERIFICATION.json` muestra avance de llamadas/tokens, revisión aprobada real, versiones preservadas y bloqueo de JSON inválido en revisión humana. El lote registró 7 extracciones, 7 revisiones y 4 comprobaciones; 30.912 tokens totales informados en 18 llamadas. Supervisión bajo 70% visible; sus correcciones no elevan la tasa automática. Cero errores observados de navegador y móvil de 390 px sin desbordamiento. El bloqueo del proyecto anterior es histórico.

La aplicación local y la validación visual cuentan con evidencia en `UI_VERIFICATION.json` y `LIVE_FLOW_VERIFICATION.json`; el arranque Windows se consolida en el cierre. La referencia sintética aún no tiene revisión humana independiente; ello limita comparar exactitud, sin añadir exigencias a la rúbrica. `EDIFICA.md` conserva sólo historial; sus originales no son un requisito adicional ni condición de la aplicación genérica.

Las capturas internas de QA acreditan verificaciones de desarrollo y permanecen locales. No se promocionan como un entregable solicitado por el usuario. El estudiante realizará la grabación personal y su presentación en la plataforma del curso. La revisión humana de la referencia sólo queda pendiente para evaluar exactitud frente a ella; no se añade como requisito académico.
