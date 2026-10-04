# Contratos sintéticos de servicios

Los cinco TXT fueron creados por Codex para verificar el software. No proceden de Edifica ni de contratos reales y no contienen datos personales. La referencia también fue elaborada por Codex a partir de esos textos; **todavía no tiene revisión humana independiente**.

`schema.fields.json` contiene la definición editable que usa la aplicación: nueve campos, con tarifa numérica, fechas y categorías. `schema.json` es su equivalente JSON Schema. Todas las claves deben estar presentes; un dato ausente vale `null`. La obligatoriedad semántica se declara en la definición de campos y determina si el resultado es parcial. El esquema JSON permite `null` para comunicar ausencias sin inventar datos.

`references.json` asocia cada nombre de TXT con sus nueve valores esperados. Al comparar un lote, asociar cada referencia con el identificador que la aplicación asignó al documento correspondiente; el nombre del archivo sólo sirve para localizar la referencia y no es evidencia para extraer campos. `reference-notes.json` declara la procedencia y la revisión pendiente.

| Documento | Objetivo de prueba | Estado determinista esperado |
|---|---|---|
| 01 | Datos explícitos completos | Exitoso |
| 02 | Excluir un presupuesto rechazado y leer la tarifa acordada | Exitoso |
| 03 | Tarifa obligatoria ausente y opcionales ausentes | Parcial |
| 04 | Fecha ambigua y ofertas incompatibles sin aceptación | Parcial |
| 05 | Formulario sin datos utilizables | Fallido |

Esos estados describen la validación de los registros elaborados. Una ejecución real de Gemini y su revisor puede arrojar resultados distintos, que deben conservarse y explicarse. El conjunto aún no demuestra la precisión de Gemini.

Para una ejecución real, cargar los cinco TXT en la aplicación, confirmar estos campos, ingresar la API key en la configuración segura y analizar. Exportar el reporte obtenido; no publicar una tabla de resultados esperados como si fuera una ejecución.

Las pruebas con JSON mal formado, tipos erróneos, error del proveedor, discrepancias del revisor y agotamiento de intentos deben identificarse como **fallos inyectados de software**. Sus métricas se reportan por separado de las ejecuciones del proveedor real.

Para reproducir la integridad de los fixtures y los reportes sintéticos después de instalar el proyecto, ejecutar desde `extractor-documental`:

```powershell
.venv\Scripts\python.exe examples\contracts\check_offline.py
```

El script devuelve las referencias elaboradas mediante un extractor inyectado y usa un revisor de pruebas. Escribe `docs/FIXTURE_VALIDATION.json` y `docs/SYNTHETIC_BATCH_REPORT.json`/`.csv`; no consulta Gemini, no estima su exactitud y no acredita revisión humana.
