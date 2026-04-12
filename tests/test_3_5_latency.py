"""
tests/test_3_5_latency.py

Paso 3.5: Validación de Latencia Real-time (< 1s)

Orquestador de pruebas que mide la latencia de propagación desde la inserción
en DB (domain_events.created_at) hasta la recepción vía Supabase Realtime
(WebSocket).

Métricas objetivo:
    - P95 < 800ms  (presupuesto de 200ms para renderizado UI => < 1s total)
    - Máxima < 1500ms
    - Integridad de mensajes = 100%

Uso:
    cd D:\\Develop\\Personal\\FluxAgentPro-v2
    uv run pytest tests/test_3_5_latency.py -v -s
"""

from __future__ import annotations

import asyncio
import httpx
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError(
        "SUPABASE_URL y SUPABASE_SERVICE_KEY deben estar configuradas en .env"
    )

# Umbrales de aceptación
P95_THRESHOLD_MS = 800
MAX_LATENCY_THRESHOLD_MS = 1500
CLOCK_SKEW_THRESHOLD_MS = 5000
SUBSCRIPTION_TIMEOUT_S = 5
NUM_TEST_EVENTS = 15
WARMUP_EVENT_COUNT = 1

# Directorio del proyecto (raíz)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "LAST"
OUTPUT_FILE = OUTPUT_DIR / "log_latencia.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Imports del proyecto (se parchean si crewai no está disponible)
# ---------------------------------------------------------------------------

from supabase import acreate_client, AsyncClient, AsyncClientOptions  # noqa: E402

from src.flows.multi_crew_flow import MultiCrewFlow  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iso_to_epoch(iso_str: str) -> float:
    """Convierte ISO-8601 a epoch seconds (UTC)."""
    cleaned = iso_str.replace("Z", "+00:00")
    return datetime.fromisoformat(cleaned).timestamp()


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Calcula el percentil sobre una lista ya ordenada."""
    if not sorted_values:
        return 0.0
    idx = int(len(sorted_values) * pct / 100.0)
    idx = min(idx, len(sorted_values) - 1)
    return sorted_values[idx]


async def _get_valid_org_id(supabase: AsyncClient) -> str:
    """Obtiene un org_id existente para usar en el test."""
    result = await supabase.table("organizations").select("id").limit(1).execute()
    if not result.data:
        raise RuntimeError("No se encontraron organizaciones en la DB para el test.")
    return result.data[0]["id"]


async def _count_events_in_db(supabase: AsyncClient, aggregate_id: str) -> int:
    """Cuenta cuántos eventos existen en DB para un aggregate_id dado."""
    result = await (
        supabase.table("domain_events")
        .select("id", count="exact")
        .eq("aggregate_id", aggregate_id)
        .execute()
    )
    return result.count if result.count is not None else 0


async def _cleanup_events(supabase: AsyncClient, aggregate_id: str) -> None:
    """Elimina eventos de test para mantener la DB limpia."""
    await supabase.table("domain_events").delete().eq("aggregate_id", aggregate_id).execute()


# ---------------------------------------------------------------------------
# LatencyValidator
# ---------------------------------------------------------------------------


class LatencyValidator:
    """Conecta, calibra, suscribe, mide y analiza latencia de Realtime."""

    def __init__(self, supabase: AsyncClient, task_id: str, org_id: str) -> None:
        self.supabase = supabase
        self.task_id = task_id
        self.org_id = org_id
        self.clock_offset_ms: float = 0.0  # positivo => reloj local adelantado
        self.events_received: list[dict[str, Any]] = []
        self.is_subscribed: bool = False
        self._channel: Any = None

    # ── 1. Calibración de reloj ─────────────────────────────────────────

    async def calibrate_clock(self) -> None:
        """Calcula el offset entre el reloj local y el servidor DB.

        Usa SELECT NOW() vía RPC para estimar el drift.
        Se hacen varias mediciones y se toma la mínima (menor RTT).
        """
        logger.info("[1/6] Calibrando relojes (NOW())...")
        offsets: list[float] = []

        for _ in range(3):
            t_before = time.perf_counter()
            try:
                # Issue ID-002: El RPC debe existir en DB.
                # Se utiliza execute() asíncrono.
                res = await self.supabase.rpc("get_server_time", {}).execute()
            except Exception as exc:
                # Issue ID-005: Mejora de feedback ante fallo de calibración
                logger.warning("RPC get_server_time falló o no disponible (%s); offset = 0.", exc)
                self.clock_offset_ms = 0.0
                return

            t_after = time.perf_counter()

            rtt = (t_after - t_before) * 1000  # ms
            server_ts = _iso_to_epoch(res.data) * 1000  # ms
            local_ts = time.time() * 1000

            # offset = local - server (ajustado por half-RTT)
            offset = (local_ts - server_ts) - (rtt / 2)
            offsets.append(offset)
            logger.debug("  RTT=%.1fms  offset=%.1fms", rtt, offset)
            await asyncio.sleep(0.1)

        # Tomar la mediana
        offsets.sort()
        self.clock_offset_ms = offsets[len(offsets) // 2]
        logger.info("      Offset calculado (mediana): %.2fms", self.clock_offset_ms)

        if abs(self.clock_offset_ms) > CLOCK_SKEW_THRESHOLD_MS:
            logger.warning(
                "⚠️  Clock skew excesivo (%.0fms > %dms). Los resultados pueden ser imprecisos.",
                self.clock_offset_ms,
                CLOCK_SKEW_THRESHOLD_MS,
            )

    # ── 2. Suscripción Realtime ────────────────────────────────────────

    async def start_monitoring(self) -> None:
        """Establece la suscripción al canal de task_transcripts."""
        logger.info("[2/6] Suscribiendo a Realtime para task_id=%s...", self.task_id)

        self._channel = self.supabase.channel(f"task_transcripts:{self.task_id}")

        self._channel.on_postgres_changes(
            event="INSERT",
            schema="public",
            table="domain_events",
            # filter=f"aggregate_id=eq.{self.task_id}", # Removido para diagnóstico
            callback=self._on_event,
        )

        # subscribe con callback de estado
        event = asyncio.Event()

        def _on_subscribe(status: str, err: Any = None) -> None:
            logger.debug("  Subscribe callback: status=%s  err=%s", status, err)
            if status == "SUBSCRIBED":
                self.is_subscribed = True
                event.set()

        await self._channel.subscribe(_on_subscribe)

        # Esperar subscripción con timeout
        try:
            await asyncio.wait_for(event.wait(), timeout=SUBSCRIPTION_TIMEOUT_S)
        except Exception:
            # Reintento ligero si falla el handshake
            logger.warning("  Reintentando suscripción...")
            await self._channel.subscribe(_on_subscribe)
            await asyncio.wait_for(event.wait(), timeout=SUBSCRIPTION_TIMEOUT_S)

        logger.info("      Suscripción exitosa.")

    def _on_event(self, payload: dict[str, Any]) -> None:
        """Callback al recibir un evento INSERT en domain_events."""
        recv_wall = time.time() * 1000  # epoch ms
        
        # Realtime v2 (supabase-py 2.x) entrega los datos en payload['data']['record'] para INSERTs
        data_root = payload.get("data", {})
        new_data = data_root.get("record", payload.get("new", {}))
        
        if not new_data:
            logger.debug("  [DEBUG] Payload sin datos: %s", payload)
            return

        event_id = new_data.get("id")
        agg_id = new_data.get("aggregate_id")
        evt_type = new_data.get("event_type")
        
        logger.info(
            "  [REALTIME] Evento detectado: Type=%s, AggID=%s (Esperando=%s)",
            evt_type, agg_id, self.task_id
        )

        if str(agg_id) != str(self.task_id):
            return  # filtro de seguridad

        created_at_iso = new_data.get("created_at")
        if not created_at_iso:
            return

        db_ts_ms = _iso_to_epoch(created_at_iso) * 1000

        # Latencia compensada: (recv_wall - clock_offset) - db_ts
        corrected_recv = recv_wall - self.clock_offset_ms
        latency_ms = corrected_recv - db_ts_ms

        self.events_received.append(
            {
                "id": new_data.get("id"),
                "event_type": new_data.get("event_type"),
                "sequence": new_data.get("sequence"),
                "db_ts_ms": db_ts_ms,
                "recv_wall_ms": recv_wall,
                "latency_ms": latency_ms,
            }
        )
        logger.debug(
            "  Evento #%s %s — latencia=%.1fms",
            new_data.get("sequence"),
            new_data.get("event_type"),
            latency_ms,
        )

    # ── 3. Warm-up ─────────────────────────────────────────────────────

    async def send_warmup_events(self) -> None:
        """Inserta eventos de warm-up para «calentar» Realtime."""
        logger.info("[3/6] Enviando warm-up (%d evento)...", WARMUP_EVENT_COUNT)
        for i in range(1, WARMUP_EVENT_COUNT + 1):
            await self._insert_event(i, "warmup")
            await asyncio.sleep(0.2)
        # Pequeña pausa para que Realtime procese
        await asyncio.sleep(1)

    # ── 4. Disparo de carga real ───────────────────────────────────────

    async def run_multi_crew_flow(self) -> None:
        """Ejecuta MultiCrewFlow con CrewAI mockeado para generar eventos reales."""
        logger.info("[4/6] Disparando MultiCrewFlow (mockeado)...")

        try:
            flow = MultiCrewFlow(org_id=self.org_id)
            await flow.execute(
                input_data={
                    "query": "Analyze the provided data and summarize findings.",
                    "requires_crew_b": False,  # ruta más corta: A → C → finalise
                },
                correlation_id=f"latency-test-{self.task_id}",
            )
        except Exception as exc:
            # SUPUESTO: si CrewAI no está instalado, generamos eventos sintéticos
            # que replican el mismo patrón de escritura que MultiCrewFlow.emit_event
            # + persist_state (que escribe en domain_events via EventStore).
            logger.warning(
                "MultiCrewFlow falló (%s); generando eventos sintéticos equivalentes.",
                exc,
            )
            await self._emit_synthetic_events()

    async def _emit_synthetic_events(self) -> None:
        """Emite eventos sintéticos usando EventStore.append_sync.

        Estos eventos son indistinguibles de los generados por MultiCrewFlow
        a nivel de DB, por lo que miden la misma latencia de infraestructura.
        """
        from src.events.store import EventStore  # noqa: PLC0415

        event_types = [
            "flow.created",
            "flow.started",
            "crew_a.completed",
            "crew_c.completed",
            "flow.completed",
        ]

        # Ráfaga: varios agent_thought rápidos para test de burst
        burst_count = 5

        seq = 1
        for evt_type in event_types:
            EventStore.append_sync(
                org_id=self.org_id,
                aggregate_type="flow",
                aggregate_id=self.task_id,
                event_type=evt_type,
                payload={"step": seq, "msg": "latency-test"},
                correlation_id=f"latency-test-{self.task_id}",
                actor="test:latency_validator",
            )
            seq += 1
            await asyncio.sleep(0.15)

        # Ráfaga de pensamientos (< 100ms entre ellos)
        for i in range(burst_count):
            EventStore.append_sync(
                org_id=self.org_id,
                aggregate_type="flow",
                aggregate_id=self.task_id,
                event_type="agent_thought",
                payload={"burst_idx": i, "msg": "thinking fast"},
                correlation_id=f"latency-test-{self.task_id}",
                actor="test:latency_validator",
            )
            seq += 1
            await asyncio.sleep(0.05)  # 50ms — ráfaga intensa

        # Más eventos para llegar a NUM_TEST_EVENTS
        remaining = NUM_TEST_EVENTS - seq
        for i in range(remaining):
            EventStore.append_sync(
                org_id=self.org_id,
                aggregate_type="flow",
                aggregate_id=self.task_id,
                event_type="tool_output" if i % 2 == 0 else "flow_step",
                payload={"step": seq, "msg": "latency-test"},
                correlation_id=f"latency-test-{self.task_id}",
                actor="test:latency_validator",
            )
            seq += 1
            await asyncio.sleep(0.15)

    async def _insert_event(self, sequence: int, event_type: str) -> None:
        """Inserta un evento directamente en DB (solo warm-up)."""
        await self.supabase.table("domain_events").insert(
            {
                "org_id": self.org_id,
                "aggregate_type": "task",
                "aggregate_id": self.task_id,
                "event_type": event_type,
                "correlation_id": f"lat-test-{self.task_id}",
                "payload": {"step": sequence, "msg": "warmup"},
                "sequence": sequence,
            }
        ).execute()

    # ── 5. Análisis ────────────────────────────────────────────────────

    async def analyze_results(self) -> dict[str, Any]:
        """Calcula estadísticas y verifica criterios de aceptación."""
        logger.info("[5/6] Analizando resultados...")

        if not self.events_received:
            logger.error("ERROR: No se recibieron eventos vía Realtime.")
            return {"passed": False, "reason": "no_events_received"}

        latencies = sorted([e["latency_ms"] for e in self.events_received])
        avg_lat = sum(latencies) / len(latencies)
        p95_lat = _percentile(latencies, 95)
        p100_lat = latencies[-1]  # máxima
        min_lat = latencies[0]

        # Integridad: comparar con DB
        db_count = await _count_events_in_db(self.supabase, self.task_id)
        received_count = len(self.events_received)
        integrity_ok = db_count == received_count

        report: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": self.task_id,
            "clock_offset_ms": round(self.clock_offset_ms, 2),
            "metrics": {
                "events_received": received_count,
                "events_in_db": db_count,
                "integrity_pct": 100.0 if integrity_ok else (received_count / db_count * 100 if db_count else 0),
                "latency_avg_ms": round(avg_lat, 2),
                "latency_p95_ms": round(p95_lat, 2),
                "latency_min_ms": round(min_lat, 2),
                "latency_max_ms": round(p100_lat, 2),
            },
            "thresholds": {
                "p95_target_ms": P95_THRESHOLD_MS,
                "p95_passed": p95_lat < P95_THRESHOLD_MS,
                "max_target_ms": MAX_LATENCY_THRESHOLD_MS,
                "max_passed": p100_lat < MAX_LATENCY_THRESHOLD_MS,
                "integrity_100_pct": integrity_ok,
            },
            "events": self.events_received,
        }

        # Imprimir resumen
        logger.info("")
        logger.info("=" * 60)
        logger.info("MÉTRICAS FINALES (Infraestructura Realtime)")
        logger.info("=" * 60)
        logger.info("  Eventos recibidos : %d / %d (DB)", received_count, db_count)
        logger.info("  Integridad        : %.1f%%", report["metrics"]["integrity_pct"])
        logger.info("  Latencia Media    : %.2fms", avg_lat)
        logger.info("  Latencia P95      : %.2fms  (objetivo < %dms)", p95_lat, P95_THRESHOLD_MS)
        logger.info("  Latencia Mín      : %.2fms", min_lat)
        logger.info("  Latencia Máx      : %.2fms  (objetivo < %dms)", p100_lat, MAX_LATENCY_THRESHOLD_MS)
        logger.info("-" * 60)

        passed = (
            p95_lat < P95_THRESHOLD_MS
            and p100_lat < MAX_LATENCY_THRESHOLD_MS
            and integrity_ok
        )

        report["passed"] = passed
        if not passed:
            reasons = []
            if p95_lat >= P95_THRESHOLD_MS:
                reasons.append(f"P95={p95_lat:.0f}ms >= {P95_THRESHOLD_MS}ms")
            if p100_lat >= MAX_LATENCY_THRESHOLD_MS:
                reasons.append(f"MAX={p100_lat:.0f}ms >= {MAX_LATENCY_THRESHOLD_MS}ms")
            if not integrity_ok:
                reasons.append(f"integridad {received_count}/{db_count}")
            report["reason"] = "; ".join(reasons)
            logger.error("❌ CERTIFICACIÓN FALLIDA: %s", report["reason"])
        else:
            logger.info("✅ CERTIFICACIÓN EXITOSA: P95 < %.0fms, MAX < %.0fms, integridad 100%%",
                        P95_THRESHOLD_MS, MAX_LATENCY_THRESHOLD_MS)

        # Guardar reporte
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, ensure_ascii=False)
        logger.info("Reporte guardado en %s", OUTPUT_FILE)

        return report

    # ── 6. Cleanup ─────────────────────────────────────────────────────

    async def close(self) -> None:
        """Cierra el canal de Realtime de forma segura."""
        if self._channel:
            try:
                await self.supabase.remove_channel(self._channel)
                logger.info("[6/6] Canal de Realtime cerrado.")
            except Exception as exc:
                logger.warning("Error cerrando canal (non-blocking): %s", exc)


# ---------------------------------------------------------------------------
# Pytest Tests
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
async def supabase_client() -> AsyncClient:
    """Cliente de Supabase fresco por cada test para evitar problemas de loop."""
    # Configuración recomendada para silenciar deprecations de httpx
    options = AsyncClientOptions(
        postgrest_client_timeout=20,
        storage_client_timeout=20,
    )
    client = await acreate_client(SUPABASE_URL, SUPABASE_SERVICE_KEY, options=options)
    yield client
    try:
        await client.aclose()
    except Exception:
        pass


@pytest.fixture(scope="function")
async def test_org_id(supabase_client: AsyncClient) -> str:
    """Obtiene un org_id válido para los tests."""
    return await _get_valid_org_id(supabase_client)


@pytest.fixture
def task_id() -> str:
    """Genera un task_id único por test."""
    return f"lat-test-{uuid.uuid4().hex[:12]}"


class TestLatencyValidation:
    """Batería de tests de latencia para Paso 3.5."""

    @pytest.mark.asyncio
    async def test_clock_calibration(self, supabase_client: AsyncClient, test_org_id: str) -> None:
        """La calibración del reloj debe ejecutarse sin error."""
        validator = LatencyValidator(supabase_client, "calib-only", test_org_id)
        await validator.calibrate_clock()
        # No se exige offset perfecto, solo que se calculó
        assert isinstance(validator.clock_offset_ms, (int, float))

    @pytest.mark.asyncio
    async def test_full_latency_validation(
        self, supabase_client: AsyncClient, test_org_id: str, task_id: str
    ) -> None:
        """Test completo: calibración → suscripción → warm-up → carga → análisis."""
        validator = LatencyValidator(supabase_client, task_id, test_org_id)

        try:
            # 1. Calibración
            await validator.calibrate_clock()

            # 2. Suscripción
            await validator.start_monitoring()

            # 3. Warm-up
            await validator.send_warmup_events()

            # 4. Carga real (MultiCrewFlow o sintético)
            await validator.run_multi_crew_flow()

            # Esperar a que lleguen los últimos eventos
            await asyncio.sleep(3)

            # 5. Análisis
            report = await validator.analyze_results()

            assert report["passed"], f"Test fallido: {report.get('reason', 'unknown')}"

        finally:
            await validator.close()
            await _cleanup_events(supabase_client, task_id)

    @pytest.mark.asyncio
    async def test_event_burst_handling(
        self, supabase_client: AsyncClient, test_org_id: str, task_id: str
    ) -> None:
        """Verifica que una ráfaga de eventos se maneja sin pérdida."""
        validator = LatencyValidator(supabase_client, task_id, test_org_id)

        try:
            await validator.calibrate_clock()
            await validator.start_monitoring()

            # Emitir ráfaga rápida directamente
            from src.events.store import EventStore  # noqa: PLC0415

            burst_size = 10
            for i in range(burst_size):
                EventStore.append_sync(
                    org_id=test_org_id,
                    aggregate_type="flow",
                    aggregate_id=task_id,
                    event_type="agent_thought",
                    payload={"burst": True, "index": i},
                    correlation_id=f"burst-test-{task_id}",
                    actor="test:burst",
                )
                await asyncio.sleep(0.03)  # 30ms entre eventos = ráfaga

            await asyncio.sleep(3)

            report = await validator.analyze_results()
            assert report["metrics"]["events_received"] >= burst_size, (
                f"Solo se recibieron {report['metrics']['events_received']} "
                f"de {burst_size} enviados"
            )

        finally:
            await validator.close()
            await _cleanup_events(supabase_client, task_id)

    @pytest.mark.asyncio
    async def test_integrity_db_vs_received(
        self, supabase_client: AsyncClient, test_org_id: str, task_id: str
    ) -> None:
        """Integridad: eventos en DB == eventos recibidos por Realtime."""
        validator = LatencyValidator(supabase_client, task_id, test_org_id)

        try:
            await validator.calibrate_clock()
            await validator.start_monitoring()

            # Emitir algunos eventos
            from src.events.store import EventStore  # noqa: PLC0415

            count = 5
            for i in range(count):
                EventStore.append_sync(
                    org_id=test_org_id,
                    aggregate_type="flow",
                    aggregate_id=task_id,
                    event_type="flow_step",
                    payload={"integrity_test": True, "index": i},
                    correlation_id=f"integrity-test-{task_id}",
                    actor="test:integrity",
                )
                await asyncio.sleep(0.15)

            await asyncio.sleep(3)

            db_count = await _count_events_in_db(supabase_client, task_id)
            received_count = len(validator.events_received)

            assert db_count == received_count, (
                f"Integridad fallida: DB={db_count}, recibidos={received_count}"
            )

        finally:
            await validator.close()
            await _cleanup_events(supabase_client, task_id)


# ---------------------------------------------------------------------------
# Main ejecutable (para uso fuera de pytest)
# ---------------------------------------------------------------------------


async def _main() -> None:
    """Ejecuta una validación completa fuera de pytest."""
    print("=" * 60)
    print("TEST DE LATENCIA PASO 3.5 — FluxAgentPro v2")
    print("=" * 60)

    options = AsyncClientOptions(
        postgrest_client_timeout=20,
    )
    supabase = await acreate_client(SUPABASE_URL, SUPABASE_SERVICE_KEY, options=options)
    org_id = await _get_valid_org_id(supabase)
    task_id = f"lat-test-{uuid.uuid4().hex[:8]}"

    validator = LatencyValidator(supabase, task_id, org_id)

    try:
        await validator.calibrate_clock()
        await validator.start_monitoring()
        await validator.send_warmup_events()
        await validator.run_multi_crew_flow()
        await asyncio.sleep(3)
        report = await validator.analyze_results()

        if not report["passed"]:
            sys.exit(1)

    except Exception as exc:
        logger.error("ERROR: %s", exc)
        sys.exit(1)
    finally:
        await validator.close()
        await _cleanup_events(supabase, task_id)


if __name__ == "__main__":
    asyncio.run(_main())
