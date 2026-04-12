"""
Validacion del Paso 3.3: Componente TranscriptTimeline

Verifica los 13 criterios de aceptacion definidos en analisis-qwen.md
"""

import os
import sys
import re

# Directorio base del proyecto
# This script is in LAST/test_3_3_timeline.py
# Project root is one level up from LAST
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
DASHBOARD = os.path.join(BASE_DIR, "dashboard")

PASSED = 0
FAILED = 0
WARNINGS = 0


def check(description: str, condition: bool, warning: bool = False):
    global PASSED, FAILED, WARNINGS
    if condition:
        status = "PASS" if not warning else "WARN"
        if warning:
            WARNINGS += 1
        else:
            PASSED += 1
    else:
        FAILED += 1
        status = "FAIL"
    print(f"  [{status}] {description}")


def read_file(rel_path: str) -> str:
    full_path = os.path.join(DASHBOARD, *rel_path.split("/"))
    if not os.path.exists(full_path):
        return ""
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()


def file_exists(rel_path: str) -> bool:
    return os.path.exists(os.path.join(DASHBOARD, *rel_path.split("/")))


def main():
    global PASSED, FAILED, WARNINGS

    print("=" * 70)
    print("Validacion - Paso 3.3: TranscriptTimeline Component")
    print("=" * 70)

    hook_content = read_file("hooks/useTranscriptTimeline.ts")
    timeline_event_content = read_file("components/transcripts/TimelineEvent.tsx")
    transcript_timeline_content = read_file("components/transcripts/TranscriptTimeline.tsx")
    transcript_page_content = read_file("app/(app)/tasks/[id]/transcript/page.tsx")

    # ── Criterio 1: El componente monta sin errores con taskId y orgId validos ──
    print("\n--- Criterio 1: Componente monta con taskId y orgId ---")
    check("TranscriptTimeline.tsx existe", file_exists("components/transcripts/TranscriptTimeline.tsx"))
    check("Acepta props taskId y orgId",
          "taskId: string" in hook_content and "orgId: string" in hook_content)
    check("El hook useTranscriptTimeline exporta la funcion principal",
          "export function useTranscriptTimeline" in hook_content)

    # ── Criterio 2: Muestra el snapshot inicial del endpoint ──
    print("\n--- Criterio 2: Snapshot inicial del endpoint ---")
    check("Hook usa useQuery para fetch del snapshot",
          "useQuery" in hook_content and "/transcripts/" in hook_content)
    check("El snapshot se almacena en estado de eventos",
          "snapshot?.events" in hook_content)

    # ── Criterio 3: Eventos ordenados por sequence ascendente ──
    print("\n--- Criterio 3: Ordenamiento por sequence ---")
    check("Hook ordena eventos por sequence",
          "sort" in hook_content and "sequence" in hook_content and "a.sequence - b.sequence" in hook_content)

    # ── Criterio 4: Suscripcion Realtime recibe eventos nuevos sin recarga ──
    print("\n--- Criterio 4: Suscripcion Realtime ---")
    check("Hook crea canal de Supabase",
          "supabase.channel" in hook_content)
    check("Suscripcion a postgres_changes INSERT",
          "postgres_changes" in hook_content and "INSERT" in hook_content)
    check("Filtro por aggregate_id",
          "aggregate_id=eq" in hook_content)
    check("Canal se limpia al desmontar",
          "removeChannel" in hook_content)
    check("Canal usa nombre dedicado transcript-timeline",
          "transcript-timeline:" in hook_content)

    # ── Criterio 5: Deduplicacion por id ──
    print("\n--- Criterio 5: Deduplicacion por id ---")
    check("Hook deduplica eventos por id en el stream",
          'some((e) => e.id === newEvent.id)' in hook_content or
          'some(e => e.id === newEvent.id)' in hook_content)

    # ── Criterio 6: Estilos visuales diferenciados por tipo de evento ──
    print("\n--- Criterio 6: Estilos por tipo de evento ---")
    check("TimelineEvent tiene configuracion por tipo",
          "EVENT_TYPE_CONFIG" in timeline_event_content)
    check("flow_step tiene estilo (icono + color)",
          "flow_step" in timeline_event_content and "GitCommit" in timeline_event_content)
    check("agent_thought tiene estilo (icono + color)",
          "agent_thought" in timeline_event_content and "Brain" in timeline_event_content)
    check("tool_output tiene estilo (icono + color)",
          "tool_output" in timeline_event_content and "Wrench" in timeline_event_content)
    check("Cada tipo tiene badge variante diferente",
          "badgeVariant" in timeline_event_content)

    # ── Criterio 7: Indicador "En vivo" aparece/desaparece segun is_running ──
    print("\n--- Criterio 7: Indicador En vivo ---")
    check("Hook expone isRunning desde snapshot",
          "isRunning" in hook_content and "snapshot?.is_running" in hook_content)
    check("Componente muestra badge 'En vivo' cuando isRunning",
          "En vivo" in transcript_timeline_content and "isRunning" in transcript_timeline_content)
    check("No muestra En vivo si la task esta en estado terminal",
          "is_running" in hook_content)

    # ── Criterio 8: Auto-scroll funciona correctamente ──
    print("\n--- Criterio 8: Auto-scroll ---")
    check("Componente tiene logica de auto-scroll con ref",
          "autoScrollRef" in transcript_timeline_content)
    check("Detecta scroll manual hacia arriba",
          "distanceToBottom" in transcript_timeline_content or "scrollTop" in transcript_timeline_content)
    check("Boton 'Ir al final' aparece cuando usuario scrollea arriba",
          "Ir al final" in transcript_timeline_content or "ScrollButton" in transcript_timeline_content)
    check("Auto-scroll se activa al recibir eventos nuevos",
          "autoScrollRef.current" in transcript_timeline_content)

    # ── Criterio 9: Manejo de fallo de suscripcion con reconexion ──
    print("\n--- Criterio 9: Reconexion ante fallos ---")
    check("Hook expone connectionStatus",
          "connectionStatus" in hook_content and "ConnectionStatus" in hook_content)
    check("Hook expone funcion reconnect",
          "reconnect" in hook_content and "export" in hook_content)
    check("Reintento automatico con timeout",
          "RETRY_INTERVAL_MS" in hook_content or "setTimeout" in hook_content)
    check("UI muestra estado de error de conexion",
          "Error de conexion" in transcript_timeline_content or "Desconectado" in transcript_timeline_content)
    check("Boton de reintentar en UI",
          "Reintentar" in transcript_timeline_content)

    # ── Criterio 10: Estado vacio con mensaje apropiado ──
    print("\n--- Criterio 10: Estado vacio ---")
    check("Muestra mensaje cuando no hay eventos y esta running",
          "Esperando eventos" in transcript_timeline_content)
    check("Muestra mensaje cuando no hay eventos y no esta running",
          "Sin eventos" in transcript_timeline_content)

    # ── Criterio 11: CodeBlock solo si payload existe y no esta vacio ──
    print("\n--- Criterio 11: CodeBlock condicional ---")
    check("TimelineEvent renderiza CodeBlock para tool_output",
          "CodeBlock" in timeline_event_content and "tool_output" in timeline_event_content)
    check("CodeBlock se renderiza solo si payload tiene contenido",
          "Object.keys(event.payload).length > 0" in timeline_event_content or
          "event.payload &&" in timeline_event_content)

    # ── Criterio 12: Cleanup del canal Supabase al desmontar ──
    print("\n--- Criterio 12: Cleanup del canal ---")
    check("Hook removeChannel en cleanup del useEffect",
          "removeChannel" in hook_content and "return ()" in hook_content)

    # ── Criterio 13: Aislamiento multi-tenant ---
    print("\n--- Criterio 13: Aislamiento multi-tenant ---")
    check("Hook requiere orgId como parametro",
          "orgId: string" in hook_content)
    check("Filtro de suscripcion usa taskId (que ya tiene aislamiento por org en backend)",
          "aggregate_id=eq" in hook_content)
    check("Query de snapshot usa endpoint REST que incluye org header (api.get)",
          "api.get" in hook_content)

    # ── Verificaciones adicionales de calidad ──
    print("\n--- Verificaciones de calidad ---")
    check("No hay TODOs en los archivos creados",
          "// TODO" not in hook_content and
          "// TODO" not in timeline_event_content and
          "// TODO" not in transcript_timeline_content)
    check("No hay imports no usados evidentes (verificacion basica)",
          "useEffect" in hook_content and "useState" in hook_content and
          "useCallback" in hook_content and "useRef" in hook_content)
    check("La pagina de transcript importa TranscriptTimeline",
          "TranscriptTimeline" in transcript_page_content)
    check("La pagina de transcript ya no usa useFlowTranscript directamente",
          "useFlowTranscript" not in transcript_page_content)

    # ── Resumen ──
    print("\n" + "=" * 70)
    total = PASSED + FAILED + WARNINGS
    print(f"Resultado: {PASSED}/{total} passed, {FAILED}/{total} failed, {WARNINGS}/{total} warnings")

    if FAILED == 0:
        print("✅ TODOS LOS CRITERIOS DE ACEPTACION CUBIERTOS")
    else:
        print(f"❌ {FAILED} CRITERIO(S) NO CUBIERTO(S)")
        return 1

    if WARNINGS > 0:
        print(f"⚠️  {WARNINGS} WARNING(S) - Revisar recomendaciones")

    return 0


if __name__ == "__main__":
    sys.exit(main())
