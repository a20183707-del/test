# Requisitos de la entrega y estado de verificación

Fuente del curso: [Proyecto 03 — Extractor de Datos Estructurados desde Documentos](https://github.com/arojaspa76/Repo-Fundamentos-Arquitectura-LLM/blob/main/projects/Proyecto_03_Extractor_de_Datos_Estructurados_desde_Documentos.md). Se revisaron íntegramente el Markdown y `consigna.docx` el 4 de octubre de 2026; no hay diferencias sustantivas en requisitos. `CHECKLIST_PROFESOR.md` conserva el hash del DOCX y la relación estricta entre requisito, evidencia y pendiente.

La consigna pide un pipeline sobre documentos libres, un esquema de seis campos o más con número, fecha y categoría, salida estructurada nativa y validación programática. El lote debe incluir cinco documentos distintos, casos difíciles, reporte de éxito/parcial/fallo, reintentos acotados y continuidad ante fallos. Los módulos separan esquema, proveedor, validación y reporte. El video dura hasta 30 minutos y muestra extracción fácil, fallo difícil y tasa final. La rúbrica asigna 30 puntos a funcionalidad, 20 a seguridad/arquitectura, 25 a errores y validación, 10 a documentación y 15 al video.

## Alcance acordado de la aplicación local

El producto es genérico: permite archivos y texto pegado, campos personalizados y exportación. Los campos se definen manualmente y se confirman antes del análisis; por la última indicación del usuario se retiró la propuesta de esquema por Gemini. La interfaz muestra flujo, evidencia, revisión independiente, versiones y reintentos. El histórico de tokens se actualiza al finalizar cada llamada y acumula la sesión, conservando mediciones incompletas o desconocidas. Los documentos reales y las credenciales permanecen privados. La configuración actual completó el lote real sobre cinco contratos sintéticos: un exitoso, tres parciales y un fallido, 20% de éxito automático. Una incompatibilidad del esquema del revisor fue corregida sin retirar la validación local. Ningún resultado inyectado se presenta como una llamada real.

La última indicación del usuario retiró plantillas y código de Edifica. La aplicación mantiene propósito general; `EDIFICA.md` conserva sólo el historial de acceso inicial y no añade funcionalidades ni condiciones de entrega.

## Evidencia preparada

| Requisito | Evidencia o estado |
|---|---|
| Esquema explícito con tipos variados | `examples/contracts/schema.fields.json` y `schema.json`: nueve campos, número, fecha, enum y booleano; obligatorios y opcionales definidos. |
| Cinco documentos distintos y difíciles | Cinco TXT marcados sintéticos: completos, presupuesto rechazado, tarifa ausente, condiciones ambiguas y formulario vacío. |
| Referencia para comparar campos | `references.json` contiene todos los campos por documento. Fue elaborada junto con los ejemplos; revisión humana independiente pendiente. |
| Integridad de fixtures | `FIXTURE_VALIDATION.json`: lectura de cinco TXT y validación de sus nueve campos esperados ejecutadas; cero llamadas al proveedor. La referencia produjo dos estados completos, dos parciales y uno fallido al validar. Esto no mide extracción real. |
| Pipeline con fixtures inyectados | `SYNTHETIC_BATCH_REPORT.json` y `.csv`: ejecución determinista del pipeline sobre los cinco contratos, con proveedor y revisor de pruebas. Modo `test_injected`, cinco fuentes sintéticas y cero llamadas externas; no se calcula exactitud frente a una referencia humana. |
| Reporte real final | `REAL_GEMINI_BATCH_REPORT.json`/`.csv`: cinco contratos sintéticos, un exitoso, tres parciales y un fallido; 20% automático. La carga mantuvo procedencia no declarada, sin inferir originales reales. `GEMINI_LIVE_CHECK.md` distingue este resultado del rechazo histórico. |
| Pruebas de errores y continuidad | Ejecución consolidada: 100 pruebas pasaron, una advertencia de desarrollo. Cubre reintentos, fallos, continuidad, revisión, API local y seguridad. El lote real conserva ausencia, ambigüedad, agotamiento de intentos y formulario vacío; los errores inyectados se identifican como tales. |
| Salida nativa, validación y revisor | Corregido `maxItems` sólo en el esquema enviado; Pydantic conserva el máximo local. Lote final con extracción, revisión y comprobación reales, registros validados, evidencia y versiones. La referencia humana independiente sigue pendiente. |
| Interfaz y Windows | Aplicación local verificada con carga/pegado, campos manuales, seguimiento y exportación. `UI_VERIFICATION.json` verifica formatos y móvil; `LIVE_FLOW_VERIFICATION.json` verifica el flujo real sin errores de navegador ni desbordamiento a 390 px. |
| Tokens por llamada y acumulados | Lote final: 18 llamadas, 30.912 tokens totales informados en las 18. Ledger incremental observado en 0 llamadas sin conteo, 5/7.852 tokens, 6/8.791 y 18/30.912. Los errores históricos sin metadatos siguen desconocidos y no se suman a este lote. |
| Supervisión humana | Aviso bajo 70% de éxito tras tres procesados o al finalizar un lote no vacío. Revisión humana validada y trazable sin sustituir el resultado ni elevar la tasa automática. |
| Seguridad y dependencias | `SECURITY_REVIEW.md` registra controles, correcciones, siete regresiones independientes y límites. `DEPENDENCY_AUDIT.json`: npm/OSV sin avisos conocidos tras actualización; no constituye una certificación ni validación real de Gemini. |
| Repositorio limpio | Revisar secretos, datos privados, exclusiones y commits. Las credenciales no van en Git, registros ni almacenamiento persistente del navegador. |
| Video | TXT local, excluido de Git: speech exacto de 8–10 minutos, acciones y variantes según resultados visibles. Grabación personal y presentación pendientes del estudiante. Las capturas de QA son internas y no se cuentan como el video entregable del usuario. |

## Cierre comprobable

La entrega está completa cuando el repositorio contiene código modular, esquema, ejemplos autorizados y evidencia de pruebas ejecutadas; la aplicación local funciona; un lote produce reportes verificables; y el video muestra en vivo éxito, fallo y continuidad. La tasa de éxito operativo no equivale a exactitud de campos ni a confianza del modelo.

La denegación del proyecto anterior es histórica y no bloquea la configuración actual. El lote final y sus exportaciones reales están verificados. Código sincronizado con GitHub en `970943e47fad62eedfbc14f406a1a456ef1745dd`; las actualizaciones documentales se publican al cierre. Quedan pendientes grabación personal y presentación del estudiante. La revisión humana independiente de la referencia limita medir exactitud, sin añadirse como requisito del curso. Edifica es únicamente un anexo histórico. La tasa real no se eleva modificando los fixtures ni la referencia después de observar el resultado.
