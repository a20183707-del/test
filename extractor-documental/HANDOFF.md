# Continuación local — estado verificado

Actualizado el 4 de octubre de 2026. Rama codex/extractor-documental-juez del repositorio privado a20183707-del/test. Se preservó el commit inicial y su historial. PROMPT_CODEX_LOCAL.txt conserva el encargo original; las indicaciones posteriores ajustan el producto: genérico, campos manuales, sin propuesta Gemini ni plantillas Edifica.

## Aplicación ejecutada

iniciar.bat inicia http://127.0.0.1:8765 con instalación y compilación cacheadas. Paquete Python bsg_extractor; frontend React/Vite/TypeScript. Archivos y texto, campos confirmados, Gemini nativo, validación estricta, revisor separado, comprobación neutral, versiones, JSON/CSV y revisión humana. Máximos: tres extracciones y seis revisiones por documento.

La clave se ingresa en configuración y permanece sólo en memoria. No está en Git, archivos, registros, capturas ni almacenamiento persistente del navegador. Reiniciar el servidor o borrar/vencer la sesión exige ingresarla otra vez; no escribir una clave en código.

## Evidencia comprobada

- 100 pruebas aprobadas; una advertencia de obsolescencia de Starlette/httpx en el TestClient.
- Lote real sobre cinco contratos sintéticos: 1 exitoso, 3 parciales, 1 fallido; 20%; 18 llamadas; 30 912 tokens. Extracción, revisión y comprobación neutral reales; tres intentos agotados en un caso ambiguo.
- Acumulación real observada: 0 llamadas, 5 / 7852 tokens, 6 / 8791 y 18 / 30912. No se confunde desconocido con cero.
- Supervisión activada bajo 70%; correcciones humanas no elevan la tasa automática.
- Chrome escritorio 1536×1024 y móvil 390×844, sin desborde horizontal ni errores JS; originales cotejados por hash y texto. DOCX muestra texto sin formato; PDF ofrece visor del navegador y texto de respaldo.
- Speech exacto y acciones de pantalla en el TXT local de speech, excluido de Git. Por indicación expresa del usuario, él grabará el video del curso. Su grabación y presentación permanecen pendientes; las capturas internas de QA ignoradas por Git no se cuentan como ese entregable.
- GEMINI_LIVE_CHECK.md, VERIFICATION.md y reportes conservan evidencia y límites. El checklist y la autoevaluación personales permanecen locales y excluidos de Git.

Los rechazos iniciales de autenticación/proyecto pertenecieron a configuraciones anteriores. La última credencial ejecutó el lote. Se corrigió una incompatibilidad de maxItems omitiéndolo sólo del request nativo; Pydantic mantiene máximo cuarenta campos.

## Pendientes reales

1. Grabación del video por el estudiante: leer el speech y mostrar la aplicación funcionando, un caso fácil, uno difícil y la tasa final. Límite: treinta minutos. Conservar el resultado observado; no presentar ejemplos inyectados como llamadas reales.
2. Revisión humana independiente de referencias para afirmar exactitud de campos. La comparación elaborada no acredita esa independencia; esa revisión no es un requisito adicional inventado de la rúbrica.

Originales Edifica recuperados: cero. docs/EDIFICA.md sólo conserva historial; no hay funcionalidad específica ni campos de pagos en el runtime ni condición de entrega ligada a ese caso.

## Sincronización comprobada

Código, pruebas y reportes sincronizados en GitHub y checkout local mediante el commit 970943e47fad62eedfbc14f406a1a456ef1745dd, hijo del original a0f4ba919ea73ae86aa1225fbe5996db80289d0f. El cierre documental del video se registra como un commit posterior en la misma rama, sin reescribir el historial.

## Retomar

Leer README y ARCHITECTURE. Ejecutar iniciar.bat y las pruebas indicadas. Para otro dominio, cargar su documento y definir campos manualmente. Conservar límites, validación y versiones. Actualizar locks/evidencia sólo después de verificar. No reemplazar resultados reales por fixtures ni publicar originales/resultados privados ni documentos personales de preparación.
