# Operational Spine Agent — Project Plan

> **Codename:** SpineAgent
> **Tipo de proyecto:** Agente autónomo sobre el objeto operativo raíz de un negocio
> **Scope del hackathon:** MVP funcional con 2 MCP servers reales (ejemplos Tiendanube + WhatsApp Business)
> **Base de datos de demo:** AdventureWorks for Postgres (OLTP)

---

## 1. Visión del sistema

El sistema es un **agente que opera sobre el objeto central de un negocio** — la entidad que atraviesa múltiples áreas funcionales y arrastra trabajo a través de la organización. Puede ser una orden, un deal, un caso, un proyecto, una póliza. Lo que importa no es el nombre sino la **propiedad estructural**: es el objeto con mayor densidad de referencias cruzadas entre dominios funcionalmente distintos.

### 1.1 Lo que esto es

- Un agente **activo, stateful y auto-mejorable** que acumula contexto del negocio con el tiempo.
- Un sistema que **razona sobre el estado del objeto raíz**, planifica secuencias de acciones, y puede construir nuevas capacidades cuando las necesita.
- Un sistema donde el humano deja de ser el **relay** que mueve información entre áreas y pasa a ser el **aprobador** del output final.

### 1.2 Lo que esto NO es

- **No es un dashboard.** Un dashboard muestra información — este sistema actúa sobre ella.
- **No es una plataforma de automatización.** Una automatización ejecuta una regla fija cuando se cumple una condición. Este sistema razona, planifica y genera nuevas capacidades.
- **No es un chatbot.** Un chatbot responde preguntas en una sesión que luego se olvida. Este sistema tiene memoria persistente del negocio, opera proactivamente, y su valor aumenta con el tiempo.

---

## 2. Arquitectura por capas

La arquitectura se descompone en 7 capas verticales claramente definidas, cada una con responsabilidades aisladas.

### Capa 1 — Operational Spine (Objeto operativo raíz)

**Responsabilidad:** Identificar, modelar y mantener la representación unificada del objeto raíz del negocio.

**Componentes:**
- **Spine Identifier:** Antes de operar, el sistema necesita saber cuál es el objeto raíz y cómo se representa en cada área funcional. Si existe un system of record, lo infiere leyendo el grafo de dependencias. Si no existe, lo reconstruye desde trazas fragmentadas (emails, PDFs, planillas).
- **Dominio A..N (representaciones parciales):** Cada dominio funcional tiene su propia representación parcial del objeto raíz. El spine las unifica.
- **Objeto raíz unificado:** La representación mínima unificada que es la base de todo lo demás. Para el hackathon: **una orden de venta en Tiendanube** (SalesOrderHeader/Detail en AdventureWorks).

**Decisiones técnicas para el hackathon:**
- El objeto raíz es `SalesOrder` de AdventureWorks.
- Los dominios son: Sales, Production, Purchasing, Person (cliente).
- El spine se modela como un grafo de relaciones entre tablas de AdventureWorks.

**Tareas:**
- [ ] Levantar PostgreSQL con AdventureWorks (Docker).
- [ ] Mapear el esquema de AdventureWorks e identificar las tablas que representan el spine de una orden.
- [ ] Diseñar el schema del `unified_spine_object` (JSON/structured) que unifica la información de una orden a través de dominios.
- [ ] Implementar queries SQL que reconstruyen el estado completo de una orden dada.

---

### Capa 2 — Context Store (Memoria persistente del negocio)

**Responsabilidad:** Mantener una memoria estructurada del negocio que se acumula con el tiempo — no una sesión de chat.

**Qué almacena:**
- El estado actual de cada instancia del objeto raíz.
- Las decisiones que se tomaron sobre él.
- Los patrones históricos.
- Las reglas implícitas del negocio.
- El resultado de cada acción que el agente ejecutó.

**Propiedades clave:**
- Con cada interacción, el store se actualiza.
- Después de N interacciones, el agente sabe cosas sobre el negocio que ningún empleado nuevo sabría.
- Combina **embeddings** (para búsqueda semántica) con **structured state** (para queries determinísticas).

**Decisiones técnicas para el hackathon:**
- PostgreSQL como store principal (ya está con AdventureWorks).
- Tabla `context_entries` con: `id`, `spine_object_id`, `entry_type` (decision | pattern | rule | action_result | state_snapshot), `content` (JSONB), `embedding` (vector), `created_at`, `source` (human | agent | system).
- pgvector para embeddings y búsqueda semántica.
- Opción: usar un modelo de embeddings local o API para generar los vectores.

**Tareas:**
- [ ] Instalar y configurar pgvector en PostgreSQL.
- [ ] Diseñar el schema de `context_entries`.
- [ ] Implementar funciones de inserción y búsqueda (semántica + structured).
- [ ] Implementar el mecanismo de actualización automática del context store después de cada interacción del agente.
- [ ] Definir la estrategia de embedding (modelo, dimensiones, chunking).

---

### Capa 3 — Modos del agente

El agente opera en **tres modos** sobre el mismo objeto. Los tres modos comparten el context store y el skill registry.

#### 3.1 Modo Assist

**Responsabilidad:** Responder preguntas activando la skill del dominio relevante al objeto consultado.

**Flujo:**
1. El usuario hace una pregunta sobre el estado de un objeto (ej: "¿Cuál es el estado de la orden #43659?").
2. El agente busca en el spine.
3. Activa la skill correspondiente al dominio relevante.
4. Responde con contexto real del context store, no con una búsqueda genérica.

**Tareas:**
- [ ] Implementar el router de intención: dado un mensaje, determinar qué dominio del spine es relevante.
- [ ] Implementar la consulta al spine + context store para armar el contexto de la respuesta.
- [ ] Implementar la selección de skill basada en el dominio detectado.
- [ ] Implementar la generación de respuesta con el LLM usando el contexto real.

#### 3.2 Modo Act

**Responsabilidad:** Recibir un objetivo y planificar de forma autónoma la cadena de skills necesaria para lograrlo.

**Flujo:**
1. El usuario da un objetivo (ej: "Necesito que esta orden se envíe hoy y se le notifique al cliente por WhatsApp").
2. El agente detecta qué información necesita.
3. La consulta.
4. Razona sobre ella.
5. Produce un output accionable.
6. Lo presenta al humano para **aprobación** antes de ejecutar cualquier acción con efecto externo.

**Propiedades clave:**
- No ejecuta una tarea aislada — planifica una **cadena**.
- El humano deja de ser el relay y pasa a ser el aprobador.

**Tareas:**
- [ ] Implementar el planner: dado un objetivo, descomponerlo en pasos y mapear cada paso a una skill.
- [ ] Implementar el executor: ejecutar la cadena de skills en secuencia, pasando el output de una como input de la siguiente.
- [ ] Implementar la presentación del plan + output al humano para aprobación.
- [ ] Implementar el mecanismo de confirmación/rechazo/edición del plan.

#### 3.3 Modo Monitor

**Responsabilidad:** Correr en background sin que nadie lo active. Observar el spine continuamente.

**Qué detecta:**
- Estado incoherente de un objeto.
- Eventos relevantes que ocurrieron.
- Situaciones en desarrollo que van a requerir una decisión.

**Propiedades clave:**
- Produce alertas o artefactos proactivamente — no espera que alguien le pregunte.
- Se ejecuta con un **hook horario/periódico** para no consumir tokens persistentemente.

**Tareas:**
- [ ] Definir las condiciones de monitoreo (reglas de coherencia del spine, umbrales, patrones anómalos).
- [ ] Implementar el scheduler/cron que dispara el monitor periódicamente.
- [ ] Implementar la detección de anomalías/incoherencias en el estado del spine.
- [ ] Implementar la generación de alertas y artefactos proactivos.
- [ ] Implementar el routing de alertas a los canales correspondientes (WhatsApp, dashboard, etc.).

---

### Capa 4 — Skill Registry

**Responsabilidad:** Almacenar, indexar y servir las skills que el agente puede ejecutar.

**Tipos de skills:**

| Tipo | Descripción | Ejemplo |
|------|-------------|---------|
| **Persistentes** | Corren continuamente como parte del monitoreo | Detectar órdenes estancadas > 48h |
| **On-demand** | Se disparan por eventos o solicitudes del usuario | Consultar estado de envío en Tiendanube |
| **AutoSkill (generadas)** | Creadas por el agente cuando detecta un gap | Integrar una nueva API de logística |

**Estructura de una skill:**
```
skill/
├── spec.yaml          # nombre, descripción, inputs, outputs, dominio, trigger_type
├── code.py            # implementación ejecutable
├── tests/             # tests de validación
└── metadata.json      # fecha de creación, autor (human|agent), versión, uso histórico
```

**Tareas:**
- [ ] Diseñar el schema del skill registry (tabla en PostgreSQL + filesystem para código).
- [ ] Implementar CRUD de skills.
- [ ] Implementar el mecanismo de búsqueda de skills por dominio, trigger, descripción semántica.
- [ ] Implementar al menos 5-8 skills iniciales para el demo:
  - [ ] `query_order_status` — consultar estado de una orden en AdventureWorks.
  - [ ] `get_customer_info` — obtener info del cliente asociado a una orden.
  - [ ] `list_order_items` — listar los items de una orden con detalles de producto.
  - [ ] `check_inventory` — verificar stock de productos.
  - [ ] `send_whatsapp_notification` — enviar mensaje al cliente via WhatsApp Business API.
  - [ ] `get_tiendanube_order` — consultar orden en Tiendanube via MCP.
  - [ ] `detect_stale_orders` — detectar órdenes sin actividad (para Monitor).
  - [ ] `generate_order_summary` — generar resumen ejecutivo de una orden.

---

### Capa 5 — AutoSkill Loop

**Responsabilidad:** Cuando el agente recibe una tarea para la que no tiene skill disponible, no falla silenciosamente. Detecta el gap, investiga, genera, valida y persiste una nueva skill.

**Flujo:**
```
Gap detectado → Research (docs, APIs) → Generar skill (spec + código) → Validar (sandbox) → Persist en registry
     ↑                                                                                           |
     └───────────────────────────── reutiliza ◄──────────────────────────────────────────────────┘
```

**Propiedades clave:**
- Es cíclico. La próxima vez que aparezca esa necesidad, la skill ya existe.
- Con el tiempo, el registry se convierte en **conocimiento institucional acumulado**: integraciones, reglas de negocio, patrones específicos de esa organización.

**Tareas:**
- [ ] Implementar el detector de gap: cuando el planner no encuentra skill para un paso, dispara el loop.
- [ ] Implementar el módulo de research: dado un gap, buscar documentación relevante (APIs, docs internos).
- [ ] Implementar el generador de skills: dado el research, generar spec.yaml + code.py usando el LLM.
- [ ] Implementar el sandbox de validación: ejecutar los tests generados en un entorno aislado.
- [ ] Implementar la persistencia: si pasa validación, registrar en el skill registry.
- [ ] Implementar el feedback loop: si falla validación, iterar con el LLM.

---

### Capa 6 — Canales de interacción

**Responsabilidad:** Interfaz entre el agente y los humanos/sistemas externos.

| Canal | Uso principal | Implementación hackathon |
|-------|--------------|--------------------------|
| **Mensajería (WhatsApp)** | Aprobaciones móviles, notificaciones al cliente | ✅ MCP Server WhatsApp Business (Twilio/Meta) |
| **Chat interno** | Alertas del equipo, interacción con el agente | Terminal/CLI o web simple |
| **Dashboard** | Análisis complejos, visualización del spine | Opcional: Streamlit o similar |
| **Webhooks / API** | Eventos del sistema, integraciones | Endpoints REST para triggers |

**Tareas:**
- [ ] Implementar MCP Server para Tiendanube (API pública con docs).
- [ ] Implementar MCP Server para WhatsApp Business (Twilio o Meta API).
- [ ] Implementar interfaz de chat CLI para interacción con el agente.
- [ ] Implementar el routing de mensajes: entrada del usuario → modo correcto del agente.
- [ ] (Opcional) Implementar dashboard web con Streamlit para visualizar el spine y las alertas.

---

### Capa 7 — Human-in-the-Loop Gate (Gate de aprobación)

**Responsabilidad:** Toda acción con efecto externo pasa por un gate de aprobación.

**Regla operativa:**
```
read  / analyze  = AUTÓNOMO         (el agente puede hacerlo sin pedir permiso)
write / send / change = APROBACIÓN  (requiere que un humano lo apruebe explícitamente)
```

**Propiedades clave:**
- Este gate NO es una limitación transitoria del sistema.
- Es el **mecanismo de confianza** que hace que el negocio pueda delegar cada vez más trabajo al agente sin perder control.
- Con el tiempo, el nivel de autonomía puede aumentar (whitelist de acciones auto-aprobadas), pero el gate siempre existe como fallback.

**Tareas:**
- [ ] Diseñar el schema de `pending_approvals` (acción propuesta, contexto, estado, aprobador, timestamp).
- [ ] Implementar el flujo de aprobación: agente propone → humano revisa → aprueba/rechaza/edita → agente ejecuta.
- [ ] Implementar la clasificación automática de acciones en read vs write.
- [ ] Implementar la notificación al humano cuando hay una acción pendiente de aprobación (via WhatsApp o chat).
- [ ] Implementar el timeout / escalación si la aprobación no llega en un tiempo razonable.

---

## 3. Integraciones (MCP Servers)

### 3.1 MCP Server — Ejemplo Tiendanube

**Objetivo:** Conectar al agente con la plataforma de e-commerce Tiendanube para leer y operar sobre órdenes reales.

**API:** Tiendanube tiene API pública REST con documentación.

**Tools a exponer via MCP:**
- `get_order(order_id)` — obtener detalle de una orden.
- `list_orders(filters)` — listar órdenes con filtros (estado, fecha, cliente).
- `get_product(product_id)` — obtener detalle de un producto.
- `get_customer(customer_id)` — obtener info del cliente.
- `update_order_status(order_id, status)` — actualizar estado (requiere aprobación).
- `get_store_info()` — información general de la tienda.

**Tareas:**
- [ ] Leer la documentación de la API de Tiendanube.
- [ ] Implementar el MCP server siguiendo el protocolo MCP.
- [ ] Implementar autenticación (OAuth/API Key).
- [ ] Implementar cada tool con manejo de errores.
- [ ] Testear contra una tienda de desarrollo/sandbox.

### 3.2 MCP Server — WhatsApp Business

**Objetivo:** Permitir al agente enviar mensajes al cliente y recibir respuestas via WhatsApp.

**API:** Twilio WhatsApp API o Meta WhatsApp Business API.

**Tools a exponer via MCP:**
- `send_message(phone, message)` — enviar mensaje de texto (requiere aprobación).
- `send_template(phone, template_id, params)` — enviar mensaje con template pre-aprobado.
- `get_message_status(message_id)` — verificar estado de entrega.
- `receive_webhook(payload)` — procesar mensaje entrante del cliente.

**Tareas:**
- [ ] Configurar cuenta de Twilio/Meta para WhatsApp Business.
- [ ] Implementar el MCP server siguiendo el protocolo MCP.
- [ ] Implementar autenticación y manejo de webhooks.
- [ ] Implementar cada tool con manejo de errores.
- [ ] Testear envío/recepción de mensajes.

---

## 4. Base de datos — AdventureWorks

### Setup

```bash
# 1. Clonar el repo
git clone https://github.com/lorint/AdventureWorks-for-Postgres.git
cd AdventureWorks-for-Postgres

# 2. Bajar los CSVs originales de Microsoft
#    (el README del repo te da el link a AdventureWorks 2014 OLTP Script)
#    Extraés el .zip adentro del directorio del repo.

# 3. Ejecutar el script ruby que convierte los CSVs
ruby update_csvs.rb

# 4. Levantar postgres (Docker es lo más rápido)
docker run --name aw-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:16

# 5. Crear la DB y cargar
psql -h localhost -U postgres -c "CREATE DATABASE \"Adventureworks\";"
psql -h localhost -U postgres -d Adventureworks < install.sql
```

### Tablas clave del Spine (SalesOrder como objeto raíz)

| Schema | Tabla | Rol en el spine |
|--------|-------|-----------------|
| `sales` | `salesorderheader` | Objeto raíz principal |
| `sales` | `salesorderdetail` | Line items de la orden |
| `production` | `product` | Productos referenciados |
| `production` | `productinventory` | Stock disponible |
| `person` | `person` | Cliente / contacto |
| `person` | `emailaddress` | Email del cliente |
| `person` | `phonenumber` | Teléfono del cliente |
| `purchasing` | `purchaseorderheader` | Órdenes de compra (supply chain) |
| `sales` | `customer` | Entidad cliente |
| `humanresources` | `employee` | Vendedor asignado |

---

## 5. Stack tecnológico

| Componente | Tecnología | Justificación |
|------------|-----------|---------------|
| **LLM** | Claude API (Anthropic) | Razonamiento de alta calidad, tool use nativo, context window grande |
| **Base de datos** | PostgreSQL 16 + pgvector | AdventureWorks ya viene para Postgres, pgvector para embeddings |
| **MCP Framework** | Python MCP SDK | Protocolo estándar para tool use |
| **Runtime del agente** | Python 3.11+ | Ecosistema de ML/AI, async nativo |
| **Scheduler** | APScheduler o Celery Beat | Para el modo Monitor (hook horario) |
| **Messaging** | Twilio / Meta WhatsApp Business API | Para el MCP server de WhatsApp |
| **E-commerce** | Tiendanube API (REST) | Para el MCP server de Tiendanube |
| **Interfaz de demo** | CLI + (opcional) Streamlit | Rápido de implementar para hackathon |
| **Containerización** | Docker Compose | PostgreSQL + app en un solo comando |

---

## 6. Estructura del proyecto

```
spine-agent/
├── docker-compose.yml              # PostgreSQL + pgvector + app
├── README.md
├── requirements.txt
│
├── agent/                           # Core del agente
│   ├── __init__.py
│   ├── core.py                      # Orquestador principal
│   ├── spine.py                     # Módulo de Operational Spine
│   ├── context_store.py             # Context Store (memoria persistente)
│   ├── planner.py                   # Planificador de cadenas de skills
│   ├── executor.py                  # Ejecutor de skills
│   ├── router.py                    # Router de intención (Assist/Act/Monitor)
│   ├── approval_gate.py             # Human-in-the-loop gate
│   └── autoskill/                   # AutoSkill Loop
│       ├── detector.py              # Detector de gaps
│       ├── researcher.py            # Research de docs/APIs
│       ├── generator.py             # Generador de skills
│       ├── validator.py             # Validador en sandbox
│       └── templates/               # Templates para generación de skills
│
├── skills/                          # Skill Registry
│   ├── registry.py                  # CRUD + búsqueda de skills
│   ├── base_skill.py                # Clase base para skills
│   └── builtin/                     # Skills pre-construidas
│       ├── query_order_status.py
│       ├── get_customer_info.py
│       ├── list_order_items.py
│       ├── check_inventory.py
│       ├── send_whatsapp_notification.py
│       ├── get_tiendanube_order.py
│       ├── detect_stale_orders.py
│       └── generate_order_summary.py
│
├── mcp_servers/                     # MCP Server implementations
│   ├── tiendanube/
│   │   ├── server.py
│   │   ├── tools.py
│   │   └── auth.py
│   └── whatsapp/
│       ├── server.py
│       ├── tools.py
│       └── webhook.py
│
├── db/                              # Database
│   ├── schema.sql                   # Tablas adicionales (context_store, skills, approvals)
│   ├── migrations/
│   └── seeds/                       # Datos de demo
│
├── monitor/                         # Modo Monitor
│   ├── scheduler.py                 # Cron/scheduler
│   ├── rules.py                     # Reglas de coherencia
│   └── alerts.py                    # Generación de alertas
│
├── interfaces/                      # Canales de interacción
│   ├── cli.py                       # Chat por terminal
│   ├── api.py                       # REST API para webhooks
│   └── dashboard.py                 # (Opcional) Streamlit dashboard
│
└── tests/
    ├── test_spine.py
    ├── test_context_store.py
    ├── test_planner.py
    ├── test_skills.py
    └── test_mcp_servers.py
```

---

## 7. Flujos de demo (hackathon)

### Demo 1 — Modo Assist

**Escenario:** Un operador pregunta por el estado de una orden.

```
Usuario: "¿Cuál es el estado de la orden 43659?"

Agente:
  1. Router detecta: modo Assist, dominio Sales.
  2. Busca en el spine: SalesOrderHeader #43659.
  3. Activa skill `query_order_status`.
  4. Consulta context store por historial de esa orden.
  5. Responde: "La orden #43659 está en estado 'Shipped'. Fue creada el 2011-05-31
     para el cliente 'Christy Zhu'. Contiene 12 items por un total de $20,565.62.
     El envío se procesó el 2011-06-07."
```

### Demo 2 — Modo Act

**Escenario:** El operador pide notificar al cliente.

```
Usuario: "Avisale al cliente de la orden 43659 que su pedido ya fue despachado."

Agente:
  1. Router detecta: modo Act.
  2. Planner descompone:
     a. get_customer_info(order=43659) → obtener nombre y teléfono
     b. generate_order_summary(order=43659) → resumen para el mensaje
     c. send_whatsapp_notification(phone, message) → enviar via WhatsApp
  3. Ejecuta pasos a y b (read = autónomo).
  4. Presenta al humano:
     "Voy a enviar este mensaje a Christy Zhu (+54 11 1234-5678):
      'Hola Christy, tu pedido #43659 ya fue despachado. Estimamos entrega
      en 3-5 días hábiles. ¿Necesitás algo más?'"
  5. Gate de aprobación: [Aprobar] [Editar] [Rechazar]
  6. Humano aprueba → ejecuta send_whatsapp_notification.
  7. Actualiza context store con el resultado.
```

### Demo 3 — Modo Monitor

**Escenario:** El agente detecta una anomalía en background.

```
Monitor (cron cada 1h):
  1. Ejecuta skill `detect_stale_orders`.
  2. Encuentra: orden #43660 lleva 7 días en estado "Processing" sin actividad.
  3. Consulta context store: no hay decisiones registradas sobre esta orden.
  4. Genera alerta:
     "⚠️ Orden #43660 está en 'Processing' hace 7 días sin actividad.
      Cliente: Jon Yang. Total: $3,578.27.
      Recomendación: verificar con producción el estado del fulfillment."
  5. Envía alerta al canal configurado (chat interno o WhatsApp del responsable).
```

### Demo 4 — AutoSkill Loop

**Escenario:** El usuario pide algo para lo que no hay skill.

```
Usuario: "¿Cuánto margen tiene la orden 43659?"

Agente:
  1. Router detecta: modo Assist, dominio Sales.
  2. Busca skill para calcular margen → NO EXISTE.
  3. AutoSkill Loop se activa:
     a. Gap detectado: "calcular margen de una orden".
     b. Research: analiza schema de AdventureWorks, encuentra `StandardCost` en
        `Production.Product` y `UnitPrice` en `Sales.SalesOrderDetail`.
     c. Genera skill: `calculate_order_margin.py` con spec y tests.
     d. Valida en sandbox: tests pasan.
     e. Persiste en registry.
  4. Ejecuta la nueva skill.
  5. Responde: "El margen de la orden #43659 es de $8,234.50 (40.1%).
     El item con menor margen es 'Mountain Bike Socks' (12.3%)."
```

---

## 8. Milestones del hackathon

### M0 — Infraestructura (primeras horas)

- [ ] Docker Compose con PostgreSQL 16 + pgvector funcionando.
- [ ] AdventureWorks cargada y verificada.
- [ ] Schema adicional creado (context_store, skill_registry, pending_approvals).
- [ ] Estructura del proyecto creada.
- [ ] Conexión a Claude API verificada.

### M1 — Spine + Context Store 

- [ ] Módulo spine.py: dado un `order_id`, reconstruir el objeto unificado.
- [ ] Módulo context_store.py: insert, query semántica, query structured.
- [ ] 3-4 skills básicas funcionando (query_order_status, get_customer_info, list_order_items, check_inventory).
- [ ] Skill registry básico funcionando (registro, búsqueda por dominio).

### M2 — Modo Assist funcional 

- [ ] Router de intención funcionando.
- [ ] Flujo completo: pregunta → router → skill → context → respuesta.
- [ ] Demo 1 ejecutándose end-to-end.

### M3 — MCP Servers + Modo Act 

- [ ] MCP Server de Tiendanube funcionando (al menos get_order, list_orders).
- [ ] MCP Server de WhatsApp funcionando (al menos send_message).
- [ ] Planner básico: descomponer objetivo en pasos.
- [ ] Approval gate funcional.
- [ ] Demo 2 ejecutándose end-to-end.

### M4 — Monitor + AutoSkill 

- [ ] Scheduler corriendo el monitor periódicamente.
- [ ] Skill `detect_stale_orders` funcional.
- [ ] Generación de alertas y routing a canales.
- [ ] AutoSkill loop básico: detectar gap → generar → validar → persistir.
- [ ] Demo 3 y Demo 4 ejecutándose end-to-end.

### M5 — Polish + Presentación (Últimas horas)

- [ ] Pulir la interfaz CLI.
- [ ] Preparar script de demo reproducible.
- [ ] (Opcional) Dashboard en Streamlit.
- [ ] Documentación del README.
- [ ] Preparar presentación / pitch.

---

## 9. Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| API de Tiendanube no disponible o rate-limited | Media | Alto | Implementar mock server con datos de AdventureWorks. Tener respuestas cacheadas. |
| Latencia de Claude API durante el demo | Media | Alto | Cachear respuestas comunes. Tener fallback con respuestas pre-computadas. |
| AutoSkill genera skills inválidas | Alta | Medio | Sandbox estricto. Limitar a skills de lectura para el demo. Si falla, mostrar el flujo sin el resultado final. |
| AdventureWorks no levanta correctamente | Baja | Alto | Tener un dump SQL de backup listo. Verificar en M0. |
| Configuración de WhatsApp Business tarda demasiado | Media | Medio | Twilio Sandbox es más rápido de configurar. Si no funciona, mockear el envío y mostrar el log. |
| El planner del modo Act genera planes incorrectos | Media | Medio | Limitar el demo a 2-3 flujos probados. Hacer few-shot prompting con ejemplos del plan correcto. |

---

## 10. Notas de diseño

### Principio fundamental: Read es autónomo, Write requiere aprobación

Este principio no es negociable. El agente puede observar, razonar y proponer sin restricción. Pero enviar un mensaje, modificar un registro, ejecutar una transacción — eso requiere que un humano lo apruebe explícitamente. Este es el mecanismo que permite escalar la confianza con el tiempo.

### El context store es el activo más valioso

A diferencia de un chatbot, este sistema **acumula valor**. Cada interacción enriquece el context store. Después de semanas de uso, el agente tiene una comprensión del negocio que ningún empleado nuevo tendría. El demo debería mostrar esto: precargar el context store con historial simulado para que las respuestas sean ricas en contexto.

### Las skills son conocimiento institucional

El skill registry no es solo código — es la codificación de cómo opera el negocio. Cuando el AutoSkill genera una skill para calcular margen, eso es conocimiento que antes solo existía en la cabeza de alguien. El demo debería enfatizar este punto.

### El spine es la innovación clave

Lo que diferencia a este sistema de "otro wrapper de LLM" es que opera sobre una **abstracción estructural del negocio** (el spine), no sobre texto libre. El agente no solo "entiende" lenguaje natural — entiende la **topología del negocio**: qué objetos existen, cómo se relacionan, qué estado tienen y qué acciones son posibles sobre ellos.
