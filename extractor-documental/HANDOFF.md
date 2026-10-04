# Avance inicial — pendiente de completar

Estado al 4 de octubre de 2026. Este commit preserva un borrador incompleto para continuar en Codex local. No se ha ejecutado Gemini ni pruebas; no hay frontend, servidor, pipeline ni reportes. No se han descargado los comprobantes originales. No contiene API keys.

## Existe

Esquema Pydantic de pagos, modelos de juez/historial/métricas, validación local, lector de archivos y un adaptador Gemini preliminar.

## Pendiente

Generalizar a dominios y esquemas personalizados; revisar y adaptar la API de Gemini con documentación oficial; implementar pipeline, juez con comprobación independiente, reintentos, eventos, servidor local, interfaz, exportación, pruebas y entregables. El adaptador conserva el contrato inicial basado en PaymentRecord: revisar compatibilidad antes de usarlo. Dependencias y nombres de modelo requieren verificación. No presentar este borrador como terminado.

## Decisiones del usuario

Aplicación local Windows y repositorio privado. Entrada libre, no sólo pagos. Recibos Edifica como caso real de prueba. Gemini (key pendiente). Juez independiente similar a EVAP; hallazgos trazables y revisión humana. Interfaz visual del flujo y tasa de éxito real, pocos parámetros. Código limpio y modular.

## Continuación

Leer ../PROMPT_CODEX_LOCAL.txt y la consigna enlazada. El repo tenía sólo .gitkeep en main; se conserva intacto. Trabajar en esta rama sin sobrescribir cambios del usuario.
