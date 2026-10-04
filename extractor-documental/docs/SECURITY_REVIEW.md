# Revisión independiente de seguridad y calidad

Revisión manual de código y pruebas ejecutada el 4 de octubre de 2026. Alcance: aplicación local, entrada de documentos, sesiones, credenciales, Gemini REST, validación, revisor, pipeline, reportes, interfaz React y arranque Windows. El código estaba en desarrollo durante la revisión; los hallazgos se coordinaron con los responsables de cada módulo y se verificaron sobre los archivos corregidos.

No se ejecutó un escaneo formal de Codex Security Cloud ni una certificación. La revisión y las pruebas reducen riesgos conocidos; no demuestran seguridad absoluta. Las regresiones independientes utilizaron credenciales ficticias y documentos sintéticos. Las comprobaciones posteriores del proveedor real se registran por separado en `GEMINI_LIVE_CHECK.md`, sin publicar secretos ni documentos privados.

## Hallazgos corregidos y evidencia

| Hallazgo | Corrección y comprobación |
|---|---|
| El filtro de declaraciones XML de DOCX podía evadirse mediante UTF-16. Una prueba segura expandió una entidad interna antes de la corrección. | Se normalizan bytes NUL antes de bloquear `DOCTYPE` y `ENTITY`. Seis regresiones cubren UTF-16/UTF-32 con y sin marca de orden de bytes. No se intentó leer archivos ni hacer solicitudes externas. |
| Borrar la clave o vencer la sesión podía dejar programadas llamadas posteriores de un lote en ejecución. | Cada extracción, revisión y comprobación verifica que la sesión y la credencial siguen activas. El test de borrado de clave interrumpe futuras llamadas inyectadas; una solicitud ya enviada no se puede retirar. |
| Un error al construir el proveedor/revisor podía dejar el lote permanentemente en ejecución. | La inicialización está dentro del manejo de fallos; el test de excepción de configuración termina el lote con error genérico. |
| El texto pegado, aún sin cargar, podía permanecer visible después de cerrar la sesión. | El panel de documentos se remonta al cambiar el token de sesión y descarta su borrador local. Comprobación de código; la captura de interfaz corresponde a la validación visual de la aplicación. |
| El entorno inicial contenía versiones de `pip` y `setuptools` con avisos conocidos. | Actualizados a `pip 26.2.1` y `setuptools 84.0.0`; el launcher exige esos mínimos. La nueva consulta OSV de los 26 paquetes instalados no devolvió avisos. El registro conserva el resultado inicial y su resolución. |
| Había dependencias y rutas que ya no correspondían al producto genérico. | Se eliminó `python-docx`, se trasladó `httpx` al grupo de desarrollo y se retiró la propuesta de campos por Gemini. Los campos se definen manualmente. |
| El mensaje HTTP 403 genérico podía confundirse con una clave inválida, aunque Google denegaba generación al proyecto. | El adaptador distingue únicamente el mensaje fijo conocido y devuelve un diagnóstico local de proyecto sin repetir detalles remotos. Lectura del error limitada a 16 KiB; las regresiones verifican sanitización y ausencia de reintentos. |
| El esquema nativo del revisor incluía `maxItems: 40` y las llamadas reales recibieron HTTP 400. | Se omite `maxItems` en el esquema enviado; Pydantic conserva localmente el máximo de 40 y la cobertura de campos. El diagnóstico real corregido obtuvo HTTP 200 y una revisión aprobada. |

También se corrigieron problemas de calidad: el marcador de compilación dejó de participar en su propio hash, la comparación de referencias acepta valores numéricos equivalentes sin confundir booleanos y los eventos de pruebas inyectadas no afirman ser ejecuciones de Gemini.

## Controles revisados

- **Credenciales:** campo de contraseña y limpieza del valor al enviar. La clave ingresa al servidor mediante el cuerpo JSON de un POST local en loopback y se conserva en memoria; hacia Gemini viaja sólo en la cabecera `x-goog-api-key`. No se incluye en URLs, JSON enviado a Gemini, exportaciones, respuestas, registros ni mensajes de error. El cliente no usa almacenamiento persistente del navegador. Las excepciones inesperadas no devuelven trazas ni contenido de la petición.
- **Red:** servidor limitado a `127.0.0.1:8765`, lista estricta de Host, comprobación de Origin y token CSRF para mutaciones. Cookie `HttpOnly` y `SameSite=Strict`, sin CORS permisivo. Gemini usa un origen HTTPS fijo, identificadores de modelo restringidos y no sigue redirecciones. La regresión HTTP local recibió sólo la solicitud inicial; la URL de destino no recibió otra petición.
- **Interfaz:** texto y resultados se renderizan como contenido React, sin inserción de HTML del documento. CSP, `nosniff`, `no-store` y política de referencia reducen exposición. La API no acepta HTML como documento.
- **Entradas y retención:** solicitudes hasta 25 MiB, archivos hasta 12 MiB, texto hasta 300 000 caracteres, 20 documentos y 96 MiB de originales por sesión. DOCX limita entradas ZIP y tamaños descomprimidos, rechaza cifrado y declaraciones XML y no extrae archivos al disco. PDF limita páginas y vista textual. Originales, resultados y clave permanecen en memoria; cerrar la sesión los descarta y la expiración tras 60 minutos de inactividad se comprueba periódicamente.
- **Llamadas y concurrencia:** hasta tres extracciones y seis llamadas del revisor por documento; un lote activo por sesión, diez lotes por sesión y ocho sesiones. Timeout de proveedor de 90 segundos, respuesta hasta 2 MiB y salida hasta 8192 tokens. No existen reintentos ocultos en el adaptador REST.
- **Validación y revisión:** rechazo de JSON inválido, claves duplicadas, valores no finitos, claves extras, tipos, fechas y categorías incorrectas. La revisión debe cubrir todos los campos y aporta evidencia; una comprobación neutral consulta el original sin recibir el candidato. Errores del revisor no se convierten en aprobación y cada intento conserva su versión.
- **Reportes:** CSV neutraliza prefijos de fórmulas y separa campos de datos con `data.`. El éxito automático se calcula sobre documentos procesados; las correcciones humanas se registran por separado. El histórico de tokens incluye llamadas con error y diferencia consumo desconocido de cero. El aviso de supervisión aparece bajo 70% de éxito después de tres procesados o al cerrar un lote no vacío.

## Verificación ejecutada

`python -m pytest -q`: **100 pruebas pasaron en la ejecución consolidada**, con una advertencia del TestClient de desarrollo. Incluye siete regresiones independientes de `tests/test_security_review.py` y las pruebas de sesiones, Host/Origin/CSRF, aislamiento de originales, credenciales, límites, continuidad, revisor, CSV, contabilidad incremental y supervisión. Estas pruebas usan dobles explícitos o un servidor HTTP local; no sustituyen las comprobaciones reales ni miden precisión semántica.

`python -m pip check` no encontró requisitos rotos. Existe una advertencia de obsolescencia de `httpx` en el TestClient de desarrollo; no representa un fallo del servidor en ejecución.

`npm audit --json` informó cero vulnerabilidades conocidas en 69 dependencias. La consulta de versiones instaladas a la [API de OSV](https://google.github.io/osv.dev/api/#post-v1querybatch) informó cero paquetes afectados tras actualizar el bootstrap. `DEPENDENCY_AUDIT.json` registra inventario, fecha, resultados y alcance. Estos resultados describen los avisos publicados al consultar; no prueban ausencia de vulnerabilidades nuevas.

Una búsqueda de firmas de secretos de alta confianza no encontró coincidencias en los archivos seleccionados del checkout. Excluyó rutas ignoradas y no inspeccionó todo el historial Git, memoria ni archivos ajenos al repositorio. Esta búsqueda no sustituye el control de lo que se agrega a cada commit.

## Límites y verificación pendiente

- El primer proyecto aceptó catálogo y denegó generación; es un antecedente. La configuración actual completó extracción/revisión/comprobación reales: un exitoso, tres parciales y un fallido, 20%, 18 llamadas y 30.912 tokens totales informados. `GEMINI_LIVE_CHECK.md` y el reporte final conservan la evidencia. Las fuentes son contratos sintéticos, aunque su carga conservó procedencia no declarada; no se infieren documentos originales reales. El consumo informado y la revisión del modelo no acreditan exactitud humana.
- `LIVE_FLOW_VERIFICATION.json` comprobó el avance incremental de llamadas/tokens, aviso de supervisión, versiones preservadas, bloqueo de JSON inválido en revisión humana y vista móvil de 390 px sin desbordamiento; no se observaron errores de navegador.
- Python elimina referencias de memoria; no ofrece borrado criptográfico de strings. El borrado impide nuevas llamadas, pero no revoca las ya enviadas. La configuración opcional mediante variable de entorno pertenece al proceso y se elimina al detenerlo; borrar la clave de sesión no modifica esa variable.
- El procesamiento PDF tiene límites de bytes/páginas/texto, pero no aislamiento de proceso ni un presupuesto duro de CPU o memoria descomprimida. Un archivo especialmente costoso todavía puede consumir recursos antes de alcanzar el límite textual.
- DOCX se lee como texto y sus imágenes embebidas requieren exportar a PDF para incluirlas. La revisión multimodal y la comprobación literal de citas tienen límites cuando no existe texto extraíble. Ningún revisor certifica autenticidad ni elimina por completo la posibilidad de instrucciones adversarias dentro de un documento.
- El equipo local, sus extensiones del navegador y el proveedor son límites de confianza externos. La aplicación utiliza HTTP sólo en loopback y no debe exponerse a una red como servicio multiusuario sin adaptar autenticación, transporte y aislamiento.
- Las referencias sintéticas fueron elaboradas junto con los ejemplos; revisión humana independiente pendiente. `EDIFICA.md` es sólo un anexo histórico de acceso; el usuario retiró sus plantillas y código del alcance del producto.
