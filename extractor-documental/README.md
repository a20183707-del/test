# Extractor documental BSG

Carga documentos o pega texto de cualquier dominio, define sólo los campos que necesitas y confirma el esquema. El pipeline devuelve un JSON por documento y clasifica el resultado como **exitoso**, **parcial** o **fallido**, con sus motivos. La aplicación comienza sin campos predefinidos y no propone campos con Gemini.

## Inicio en Windows

Requisitos: Python 3.11 o posterior y Node.js 20.19+, 22.12+ o posterior compatible con Vite; Node 21 no está admitido. Se verificó en Windows con Python 3.11.9 y Node 22.17.0. Internet es necesario durante la primera instalación y para analizar con Gemini.

1. Ejecuta `iniciar.bat`, desde esta carpeta o desde la raíz del repositorio.
2. Abre `http://127.0.0.1:8765`. Mantén la ventana del servidor abierta; `Ctrl+C` lo detiene.
3. En **Configurar Gemini**, pega la API key y pulsa **Guardar en memoria**. Los modelos se encuentran en la sección secundaria de configuración.
4. Carga TXT, PDF, DOCX, PNG, JPEG o WebP, o usa **Pegar texto**.
5. Agrega campos, elige sus tipos y obligatoriedad; precisa significado, categorías y límites sólo cuando sean necesarios. Pulsa **Confirmar campos** y **Analizar documentos**.
6. Revisa documento original, datos, evidencia del revisor, motivos, intentos e histórico de tokens. Exporta el lote a JSON o CSV.

El launcher crea `.venv`, instala versiones fijadas en `requirements.lock.txt`, usa `npm ci` y compila el frontend. En inicios posteriores reutiliza lo preparado mientras no cambien dependencias o fuentes. El servidor sólo escucha en loopback y reutiliza una instancia activa de esta aplicación.

### Instalación manual reproducible

Desde esta carpeta, en PowerShell:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
Set-Location web
npm.cmd ci
npm.cmd run build
Set-Location ..
.venv\Scripts\python.exe -m uvicorn bsg_extractor.server:app --host 127.0.0.1 --port 8765 --no-access-log --log-level warning
```

La aplicación no lee archivos `.env`. Acepta como alternativa `GEMINI_API_KEY` ya presente en el entorno del proceso; para el uso local se recomienda el campo de contraseña, que no crea archivos. No escribas una clave literal en comandos, código ni documentación.

## Esquema y resultados

Los tipos disponibles son texto, número, entero, fecha ISO `YYYY-MM-DD`, categoría y booleano. Todos los nombres deben estar presentes en el JSON; un dato ausente se representa con `null`. Un campo obligatorio ausente produce parcial o fallo, aunque el JSON sea válido. Se rechazan claves extra, JSON mal formado, claves duplicadas, booleanos donde se esperan números, fechas imposibles, categorías incorrectas y valores no finitos.

El revisor recibe el original en un contexto nuevo. Una discrepancia requiere otra lectura con una pregunta neutral, sin el candidato ni el valor sugerido. Sus propuestas no cambian datos silenciosamente: la nueva extracción se valida y conserva versiones. La revisión humana registra propuesta, motivo, fecha y validación aparte del resultado automático.

Cada documento admite hasta **3 extracciones** y **6 llamadas de revisión/comprobación**. Los fallos se aíslan y los demás documentos continúan. Un error permanente de autenticación, permisos o cuota no se reintenta dentro del documento. El porcentaje es `exitosos / procesados × 100`; no mide confianza ni exactitud. Bajo 70%, tras tres procesados o al terminar un lote no vacío, se solicita supervisión humana.

Los tokens se registran al terminar cada solicitud, con rol, modelo, intento, tiempo y estado. El histórico acumula todos los lotes de la sesión. **«—»** significa desconocido; **«≥»**, consumo conocido incompleto. La estimación local `caracteres / 4` sólo corresponde al texto de entrada y no al costo total. PDF e imágenes requieren datos del proveedor. No se presenta el consumo como una factura.

## Ejemplos y pruebas

[Contratos sintéticos](examples/contracts/README.md): cinco documentos distintos y nueve campos, incluyendo número, fecha y categorías. Sirven como dominio de la entrega y no forman parte de la lógica del producto. Los casos contienen información completa, ausencias, ambigüedad y un formulario vacío.

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe examples/contracts/check_offline.py
```

Las pruebas y `check_offline.py` utilizan respuestas inyectadas, claramente identificadas; no llaman a Gemini ni demuestran su precisión. La referencia de los ejemplos fue elaborada junto con los documentos: su revisión humana independiente sigue pendiente. La comparación por campos permite registrar esa procedencia y no convierte la tasa operativa en exactitud certificada.

## Evidencia y entrega

- [Verificación ejecutada](docs/VERIFICATION.md): pruebas, UI, formatos, Windows y limitaciones.
- [Prueba real de Gemini](docs/GEMINI_LIVE_CHECK.md): lote completo con extracción, revisor, comprobación neutral y reintentos; historial de incidencias corregidas.
- [Seguridad y calidad](docs/SECURITY_REVIEW.md) y [auditoría de dependencias](docs/DEPENDENCY_AUDIT.json).
- [Arquitectura y decisiones](ARCHITECTURE.md) y [continuación](HANDOFF.md).
- Reportes `docs/SYNTHETIC_BATCH_REPORT.json/.csv`: prueba determinista con cero llamadas externas. `docs/REAL_GEMINI_BATCH_REPORT.json/.csv`: ejecución de solicitudes reales sobre documentos sintéticos; conservar sus resultados aunque sean fallidos.

El lote real de cinco contratos sintéticos produjo **1 exitoso, 3 parciales y 1 fallido (20%)**, con **18 llamadas y 30 912 tokens**. Se conservaron siete intentos de extracción y se activó supervisión humana. El estudiante grabará su video; el TXT local, excluido de Git, contiene el texto exacto para leer y las acciones que debe mostrar. Esa grabación y su presentación siguen pendientes. Las capturas internas de QA no se cuentan como su entrega audiovisual. La referencia de los ejemplos requiere revisión humana independiente para afirmar exactitud.

## Privacidad y límites

Clave, originales y resultados permanecen en memoria durante la sesión. No hay base de datos ni almacenamiento persistente del navegador. **Cerrar y borrar sesión** descarta sus referencias; la sesión expira tras 60 minutos de inactividad. Exportar crea archivos descargados que el usuario debe conservar de forma segura. Gemini recibe los originales al analizar, no al cargarlos.

Límites: 12 MiB por archivo, 25 MiB por solicitud, 20 documentos y 96 MiB de originales por sesión. DOCX se lee como texto; para incluir imágenes incrustadas, expórtalo a PDF. No se admiten PDF cifrados. El esquema es un objeto plano de hasta 40 campos; no admite estructuras arbitrarias anidadas. Cualquier dominio es compatible dentro de esos tipos y formatos.

El revisor verifica contenido y evidencia; no certifica autenticidad. Los parsers tienen límites, pero no aislamiento de proceso ni un límite duro de CPU para PDF. La aplicación está diseñada para un equipo local, no para exposición pública multiusuario. La revisión de seguridad documenta controles, pruebas y estos límites.
