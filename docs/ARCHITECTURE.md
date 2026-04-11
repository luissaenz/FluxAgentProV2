# Arquitectura Técnica de FluxAgentPro-v2

Este documento describe el flujo de vida de una solicitud dentro del sistema, identificando las "puertas" de entrada y salida, y la interacción entre los componentes core.

## Mapa de Ejecución (Lifecycle)

```mermaid
graph LR
    %% Definición de Estilos
    classDef door fill:#4ade80,stroke:#22c55e,stroke-width:2px,color:#000
    classDef brain fill:#a855f7,stroke:#7e22ce,stroke-width:2px,color:#fff
    classDef storage fill:#3b82f6,stroke:#2563eb,stroke-width:2px,color:#fff
    classDef exit fill:#ef4444,stroke:#dc2626,stroke-width:2px,color:#fff

    subgraph "Nivel A: ENTRADA (Input Gates)"
        T[<b>User Dashboard</b><br/>Interaction] -->|Action: Execute| API[<b>FastAPI Router</b><br/>/tickets/{id}/execute]
        EXT[<b>Webhooks</b><br/>External Signal] --> API
    end

    subgraph "Nivel B: ORQUESTACIÓN (The Engine)"
        API -->|1. Lookup| REG[<b>FlowRegistry</b><br/>registry.py]
        REG -->|2. Instantiate| BF[<b>BaseFlow</b><br/>Business Logic]
        BF -->|3. Delegate| MCF[<b>MultiCrewFlow</b><br/>Engine @Protected]
        MCF -->|4. Power| AG[<b>PydanticAI Agents</b><br/>Tools & LLM]
    end

    subgraph "Nivel C: REGISTRO (Memory & States)"
        AG -->|Emit| EV[<b>DomainEvents</b><br/>domain_events table]
        BF -->|Update| TST[<b>Task Status</b><br/>tasks table]
        TST -->|Link| TKT[<b>Ticket Result</b><br/>tickets table]
    end

    subgraph "Nivel D: SALIDA (Real-time Feedback)"
        EV -->|Supabase Realtime| OBS[<b>Live Transcripts</b><br/>UI Viewer]
        TKT -->|Status Update| NOT[<b>System Notification</b>]
    end

    %% Asignación de Clases
    class API,EXT door
    class BF,MCF,AG brain
    class EV,TST,TKT storage
    class OBS,NOT exit
```

## Las 4 Dimensiones del Sistema

### 1. Puertas de ENTRADA (Input Gates) - [Color Verde]
Son los únicos puntos donde el sistema acepta comandos. 
- **API Router:** Valida la autenticación y el `org_id`.
- **Registry:** Asegura que el flujo solicitado existe antes de gastar recursos.

### 2. El MOTOR (The Brain) - [Color Púrpura]
Donde vive la inteligencia.
- **BaseFlow:** Es el "Director de Orquesta". Sabe qué agentes llamar.
- **MultiCrewFlow:** Es el motor de ejecución técnica (aislado y protegido).
- **Agentes:** Ejecutan herramientas (`Tools`) y procesan lenguaje natural.

### 3. La MEMORIA (Persistence) - [Color Azul]
Todo lo que ocurre se graba.
- **`domain_events`:** Logs detallados de cada pensamiento y acción del agente.
- **`tasks`:** El registro oficial de que un trabajo se está realizando.
- **`tickets`:** La entidad de alto nivel que el usuario final ve.

### 4. Puertas de SALIDA (Feedback) - [Color Rojo]
Cómo el sistema se comunica contigo.
- **Supabase Realtime:** Empuja los eventos a tu pantalla sin que tengas que refrescar.
- **Notificaciones de Estado:** Avisa cuando un ticket pasa de `in_progress` a `done` o `blocked`.

---
*Este documento es una referencia técnica para el desarrollo del MVP.*
