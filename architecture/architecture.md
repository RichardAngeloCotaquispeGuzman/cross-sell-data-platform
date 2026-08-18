# Arquitectura de la plataforma

## Objetivo y alcance

La plataforma convierte movimientos comerciales sintéticos en datasets
analíticos y oportunidades explicables de cross-selling. Integra dos fuentes,
ejecuta un ETL incremental y publica una arquitectura Bronze/Silver/Gold en
Parquet. Azure Blob Storage es la nube elegida; local y Azurite permiten
desarrollar y probar sin costo cloud.

## Diseño lógico

Los diagramas se mantienen en **Mermaid** porque GitHub los renderiza
directamente, es gratuito y permite versionarlos como texto junto al código.

~~~mermaid
flowchart LR
    subgraph SRC["1. Fuentes"]
        N[("Neon PostgreSQL<br/>5 tablas de negocio")]
        A["Nager.Date API<br/>feriados de Perú"]
        W[("control.pipeline_watermarks")]
    end

    subgraph PY["2. Pipeline Python"]
        E["Extract<br/>SQL incremental + API retry/cache"]
        Q{"Data Quality<br/>columnas, PK, FK, tipos"}
        T["Transform<br/>integración y reglas de negocio"]
        R["Reglas de asociación<br/>support, confidence, lift"]
    end

    subgraph MED["3. Lakehouse Parquet + Snappy"]
        B["Bronze<br/>raw e inmutable<br/>ingestion_date + run_id"]
        S["Silver current<br/>dimensiones + fact_sales"]
        G["Gold current<br/>resúmenes + pares +<br/>recomendaciones + customer_360"]
    end

    subgraph DST["4. Destinos configurables"]
        L["Disco local<br/>desarrollo"]
        Z["Azurite + Docker<br/>emulación gratuita"]
        AZ["Azure Blob Storage<br/>destino cloud"]
    end

    subgraph OPS["5. Operación"]
        GH["GitHub Actions<br/>CI + ejecución manual"]
        TF["Terraform<br/>infraestructura como código"]
        LOG["Logs JSON<br/>run_id, filas, errores, duración"]
    end

    N --> E
    A --> E
    W --> E
    E --> B
    B --> Q
    Q --> T
    T --> S
    S --> R
    R --> G
    E -. "actualiza solo después del éxito" .-> W
    B & S & G --> L
    B & S & G --> Z
    B & S & G --> AZ
    GH --> E
    TF -. "aprovisiona RG, Storage Account y container" .-> AZ
    E & Q & T & R --> LOG
~~~

Los fuentes editables están en
[`diagrams/pipeline.mmd`](diagrams/pipeline.mmd) y
[`diagrams/incremental-flow.mmd`](diagrams/incremental-flow.mmd).

## Flujo incremental

La extracción incremental evita releer PostgreSQL, pero Gold no analiza
solamente el último lote: Silver se reconstruye con todo el historial
consolidado de Bronze y Gold recalcula las recomendaciones vigentes.

~~~mermaid
sequenceDiagram
    actor Trigger as Usuario / GitHub Actions
    participant P as Pipeline Python
    participant C as control.pipeline_watermarks
    participant N as Neon source.ventas
    participant B as Bronze Parquet
    participant A as Nager.Date API / cache
    participant S as Silver current
    participant G as Gold current

    Trigger->>P: Ejecutar pipeline
    P->>C: Leer last_processed_at
    C-->>P: Watermark actual
    P->>N: WHERE ts_movimiento > watermark
    N-->>P: Solo movimientos nuevos

    alt Hay movimientos nuevos
        P->>B: Escribir ingestion_date + run_id
        P->>B: Leer todo el histórico Bronze
        P->>A: Obtener feriados por año
        A-->>P: API o caché local
        P->>S: Validar y reemplazar snapshot completo
        P->>G: Recalcular usando todo Silver
        P->>C: Avanzar watermark después del éxito
        P-->>Trigger: pipeline_succeeded
    else No hay movimientos nuevos
        P-->>Trigger: pipeline_no_changes
    end

    Note over P,C: Ante cualquier fallo,<br/>el watermark no avanza.
~~~

## Responsabilidades por capa

### Bronze — Raw

- Conserva las columnas de origen y añade metadata técnica.
- Particiona por `ingestion_date=YYYY-MM-DD` y luego por `run_id`.
- Las dimensiones son snapshots completos; ventas es incremental.
- Es inmutable y permite auditoría y reconstrucción.

### Silver — Curated

- Valida columnas, claves únicas, claves foráneas y jerarquías.
- Normaliza fechas y números.
- Clasifica `sale`, `return` y `zero_value`.
- Integra cliente, destinatario, producto, jerarquía y calendario.
- Publica un snapshot completo bajo `current`.

### Gold — Serving

- `sales_summary`: ventas positivas agregadas.
- `product_pairs`: pares no ordenados por factura.
- `cross_sell_recommendations`: oportunidades vigentes por cliente.
- `customer_360`: comportamiento acumulado del cliente.

Los pares eliminan productos repetidos dentro de una factura. Las
recomendaciones usan support, confidence y lift, y excluyen productos ya
comprados. No se usa un modelo de machine learning opaco ni un servicio pagado.

## Mapeo físico a Azure

| Responsabilidad | Implementación actual | Equivalente administrado a escala |
|---|---|---|
| Fuentes | Neon PostgreSQL + Nager.Date | Azure Database/API Management |
| Ingesta | Python en WSL o GitHub Actions | Azure Functions/Container Apps |
| Bronze/Silver/Gold | Azure Blob, Parquet Snappy | ADLS Gen2 |
| Transformación | Python + pandas | Databricks o Synapse |
| Serving | Parquet Gold tipo lakehouse | Synapse SQL/Power BI |
| Orquestación | CLI/Make/GitHub Actions | Azure Data Factory |
| Observabilidad | Logs JSON de aplicación | Azure Monitor |

Gold se publica en Parquet como parte de la arquitectura lakehouse adoptada.
Usar servicios administrados adicionales no aportaría valor al volumen actual
y generaría costos cloud innecesarios.

## Persistencia, particionado e idempotencia

- Bronze: histórico por `ingestion_date` y `run_id`; no se limpia
  automáticamente.
- Silver/Gold: snapshot vigente en `current`, reemplazado de forma
  determinística.
- Watermark: estado vivo y monotónico en Neon.
- `--full-refresh`: inicializa un destino vacío.
- `--force-rebuild`: recalcula Silver/Gold desde Bronze.
- El lector acepta tanto el layout original por `run_id` como el nuevo layout
  particionado, por compatibilidad con las corridas existentes.

Particionar Bronze por fecha permite localizar corridas y aplicar políticas de
retención. Silver y Gold permanecen como snapshot único porque el volumen actual
es pequeño y sus consumidores necesitan la vista completa vigente.

## Observabilidad propuesta

Cada evento se escribe como una línea JSON con:

- timestamp UTC;
- nivel y nombre del logger;
- `run_id` y destino;
- filas publicadas por capa/dataset;
- cantidad de objetos y duración total;
- stack trace en `pipeline_failed`.

En producción se añadirían métricas de duración por etapa, filas rechazadas,
retraso del watermark y alertas. Para este proyecto los logs permanecen en el
runner y no requieren Azure Monitor.

## Riesgos y mitigaciones

| Riesgo | Mitigación implementada |
|---|---|
| API lenta o temporalmente caída | Timeout, reintentos con backoff y caché |
| Cambio de esquema | Contratos JSON, columnas obligatorias y fallo explícito |
| Duplicados por reintento | Clave factura-item y deduplicación determinística |
| Relaciones huérfanas | Validaciones de cliente, destinatario, producto y jerarquía |
| Pérdida de datos incremental | Watermark avanza solo al terminar con éxito |
| Secreto expuesto | Archivo privado, GitHub Secrets y `.gitignore` |
| Ejecución cloud no deseada | Cron protegido por variable y `terraform apply` manual tras revisar el plan |
| Crecimiento de Bronze | Partición por fecha y futura política de retención |
| Preferencias antiguas | Futuro filtro temporal o ponderación por recencia |
