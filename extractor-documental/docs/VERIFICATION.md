# Verificación de la entrega local

Revisión del 4 de octubre de 2026. La evidencia distingue pruebas deterministas, solicitudes reales a Gemini y tareas que requieren revisión humana.

## Código y arranque

- Suite final: **100 pruebas pasaron**. Una advertencia de desarrollo de Starlette/httpx sobre TestClient; no fue un fallo de prueba.
- Frontend: TypeScript y compilación de producción correctos. Código sin errores de espacios en la comprobación Git. Los ejemplos originales conservan sus líneas finales para mantener los hashes de las ejecuciones; se excluye sólo `blank-at-eof` de esa comprobación.
- `pip check`: dependencias compatibles. Auditorías npm y OSV sin vulnerabilidades conocidas en las versiones consultadas; detalle en `DEPENDENCY_AUDIT.json`. Esto no certifica ausencia de vulnerabilidades.
- `iniciar.bat` ejecutado realmente en Windows: prepara el entorno, compila y abre `http://127.0.0.1:8765/`. Una segunda preparación reutilizó las dependencias y la compilación sin trabajo innecesario. El servidor permanece disponible en loopback.
- La sesión visible del usuario tiene la credencial autorizada en memoria. La clave no se conserva al cerrar/borrar la sesión ni al reiniciar el servidor.

## Flujo real y consumo

`REAL_GEMINI_BATCH_REPORT.json` y `.csv` conservan el lote final real, con cinco contratos sintéticos diferentes: **1 exitoso, 3 parciales, 1 fallido; 20% de éxito automático**. La carga mantuvo procedencia no declarada: el reporte cuenta cinco `undeclared_documents`, sin inferir originales reales por haberlos subido.

Hubo **18 llamadas**: siete extracciones, siete revisiones y cuatro comprobaciones neutrales. Gemini informó **30.912 tokens totales** en las 18 llamadas. El registro incremental pasó de cero llamadas y consumo desconocido a 7.852, 8.791 y 30.912 tokens. `LIVE_FLOW_VERIFICATION.json` conserva capturas de los valores de API y pantalla durante la ejecución.

El primer contrato terminó aprobado. El segundo agotó tres extracciones y seis revisiones/comprobaciones por una discrepancia de negación sobre renovación. Los siguientes tuvieron tarifa ausente, condiciones ambiguas y formulario vacío. Los ejemplos y referencias permanecieron intactos para no elevar artificialmente el resultado. La supervisión bajo 70% apareció; las versiones se conservaron y la revisión humana rechazó JSON inválido. Éxito operativo no equivale a exactitud contra una referencia humana.

`REFERENCE_COMPARISON_DRAFT.json` compara los 45 campos con la referencia sintética preparada. Declara `independent_human_review: false` y `certified_accuracy: false`; la frase ambigua del segundo contrato requiere revisión humana. No se presenta ese borrador como evaluación certificada.

Las pruebas de errores inyectados se documentan por separado en `FIXTURE_VALIDATION.json` y `SYNTHETIC_BATCH_REPORT.*`, con modo `test_injected` y cero llamadas externas.

## Navegador e interfaz

Se probaron Chrome de escritorio a 1536 × 1024 y móvil a 390 × 844, sin errores de navegador observados ni desbordamiento horizontal. Las vistas de datos, revisor, intentos y JSON se contrastaron con el reporte. La opción de proponer campos con Gemini no existe en la interfaz ni en la API.

TXT, DOCX, PDF y PNG conservaron bytes originales comprobados mediante hash. Se verificó el texto completo leído de TXT/DOCX/PDF y la carga efectiva de píxeles de PNG. DOCX se identifica como texto sin formato; PDF ofrece visor nativo, enlace al original y texto leído como alternativa. Se pegó un CV sintético de otro dominio y se rechazó HTML no admitido. `UI_VERIFICATION.json` registra estas comprobaciones y distingue el bloqueo histórico del proyecto anterior del lote final que sí generó contenido.

Se consideraron las direcciones ejecutiva, técnico-operativa y SaaS. Se eligió un flujo operativo con composición SaaS: entrada y original a la izquierda, campos/resultados en el centro, estados y consumo a la derecha. La jerarquía conserva una acción principal; el esquema confirmado se contrae para priorizar resultados. El concepto visual inicial se adaptó a los requisitos posteriores de campos manuales y aplicación genérica. Se revisaron estados vacío, carga, error, éxito, foco y vista móvil.

Las comprobaciones visuales se apoyan en capturas internas de QA bajo `output/`, ignoradas por Git. La grabación del video del curso la realizará el estudiante y permanece pendiente. El TXT local, excluido de Git, contiene el speech exacto y las acciones necesarias; el QA interno no se declara como su entrega audiovisual.

## Seguridad y límites

La revisión está documentada en `SECURITY_REVIEW.md`. Se comprobaron protección de sesión/Host/Origin/CSRF, límites de archivos y memoria, sanitización de errores, bloqueo de redirecciones que podrían filtrar credenciales, borrado de sesión y rechazo de XML peligroso incluso en UTF-16/32. Las regresiones están incluidas en las 100 pruebas.

No se ejecutó una certificación formal de seguridad. El análisis de PDF carece de aislamiento duro de CPU/memoria; el revisor usa otra llamada/modelo de Gemini y no otro proveedor; la evidencia multimodal tiene límites semánticos. La referencia requiere revisión humana independiente para afirmar exactitud. La grabación y presentación del video corresponden al estudiante y siguen pendientes.

## GitHub

El commit `970943e47fad62eedfbc14f406a1a456ef1745dd` se publicó en `codex/extractor-documental-juez` y se comprobó mediante la referencia remota y el objeto de commit. El árbol GitHub coincide exactamente con el índice local. Es hijo del commit original, preservando el historial; el cierre documental del video continúa esa rama. El análisis de firmas de secretos incluyó los archivos elegibles y los locks, con cero coincidencias de alta confianza; no incluyó el historial de Git ni los archivos locales ignorados.

Los cinco hashes SHA-256 del reporte real coinciden con los bytes de los TXT locales y con los blobs del índice Git. `.gitattributes` fija LF para esos documentos, conservando sus hashes también al hacer checkout en Windows.
