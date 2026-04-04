-- ============================================================
-- Migration 017: Seed flow_presentations for all known flows
-- Uses a placeholder org_id — replace with real org_id or use
-- scripts/seed_flow_presentations.py for programmatic seeding.
-- ============================================================

-- NOTE: This migration inserts for ALL orgs that exist.
-- In production, use the Python seed script for targeted org seeding.

-- PreventaFlow: cotización con opciones de precio
INSERT INTO flow_presentations (org_id, flow_type, presentation_config)
SELECT o.id, 'PreventaFlow', '{
  "card": {
    "title": { "from": "$.evento_id" },
    "amount": { "from": "$.opcion_recomendada", "format": "currency_ars" }
  },
  "detail": {
    "sections": [
      {
        "type": "fields",
        "title": "Cotización",
        "fields": [
          { "label": "Evento", "from": "$.evento_id" },
          { "label": "Cotización", "from": "$.cotizacion_id" },
          { "label": "Bartenders", "from": "$.bartenders_necesarios" },
          { "label": "Factor Climático", "from": "$.factor_climatico", "format": "pct" }
        ]
      },
      {
        "type": "key_value_list",
        "title": "Opciones de Precio",
        "from": "$.opciones_precio"
      },
      {
        "type": "fields",
        "title": "Escandallo",
        "fields": [
          { "label": "Básica", "from": "$.opcion_basica", "format": "currency_ars" },
          { "label": "Recomendada", "from": "$.opcion_recomendada", "format": "currency_ars" },
          { "label": "Premium", "from": "$.opcion_premium", "format": "currency_ars" },
          { "label": "Escandallo Total", "from": "$.escandallo_total", "format": "currency_ars" }
        ]
      }
    ]
  }
}'::jsonb
FROM organizations o
ON CONFLICT (org_id, flow_type) DO NOTHING;

-- ReservaFlow: confirmación de reserva
INSERT INTO flow_presentations (org_id, flow_type, presentation_config)
SELECT o.id, 'ReservaFlow', '{
  "card": {
    "title": { "from": "$.evento_id" },
    "icon": {
      "from": "$.status",
      "map": { "confirmado": "✅", "pendiente": "⏳" }
    }
  },
  "detail": {
    "sections": [
      {
        "type": "fields",
        "title": "Reserva",
        "fields": [
          { "label": "Evento", "from": "$.evento_id" },
          { "label": "Estado", "from": "$.status" },
          { "label": "Necesita Head", "from": "$.necesita_head", "format": "boolean_yn" },
          { "label": "Stock OK", "from": "$.stock_ok", "format": "boolean_yn" }
        ]
      },
      {
        "type": "key_value_list",
        "title": "Bartenders Asignados",
        "from": "$.bartenders"
      },
      {
        "type": "accordion",
        "title": "Hoja de Ruta",
        "default": "collapsed",
        "from": "$.hoja_de_ruta"
      }
    ]
  }
}'::jsonb
FROM organizations o
ON CONFLICT (org_id, flow_type) DO NOTHING;

-- AlertaClimaFlow: alerta meteorológica
INSERT INTO flow_presentations (org_id, flow_type, presentation_config)
SELECT o.id, 'AlertaClimaFlow', '{
  "card": {
    "title": { "from": "$.evento_id" },
    "icon": {
      "from": "$.alerta_roja",
      "map": { "true": "🔴", "false": "🟢" }
    },
    "amount": { "from": "$.total_ars", "format": "currency_ars" }
  },
  "detail": {
    "sections": [
      {
        "type": "fields",
        "title": "Alerta Climática",
        "fields": [
          { "label": "Evento", "from": "$.evento_id" },
          { "label": "Alerta Roja", "from": "$.alerta_roja", "format": "boolean_yn" },
          { "label": "Acción", "from": "$.accion" },
          { "label": "Orden", "from": "$.orden_id" },
          { "label": "Total", "from": "$.total_ars", "format": "currency_ars" }
        ]
      },
      {
        "type": "fields",
        "title": "Mensaje",
        "fields": [
          { "label": "Detalle", "from": "$.mensaje" }
        ]
      }
    ]
  }
}'::jsonb
FROM organizations o
ON CONFLICT (org_id, flow_type) DO NOTHING;

-- CierreFlow: cierre de evento
INSERT INTO flow_presentations (org_id, flow_type, presentation_config)
SELECT o.id, 'CierreFlow', '{
  "card": {
    "title": { "from": "$.evento_id" },
    "amount": { "from": "$.ganancia_neta", "format": "currency_ars" }
  },
  "detail": {
    "sections": [
      {
        "type": "fields",
        "title": "Cierre de Evento",
        "fields": [
          { "label": "Evento", "from": "$.evento_id" },
          { "label": "Estado", "from": "$.status" },
          { "label": "Auditoría", "from": "$.auditoria_id" },
          { "label": "Margen", "from": "$.margen_pct", "format": "pct" },
          { "label": "Ganancia Neta", "from": "$.ganancia_neta", "format": "currency_ars" },
          { "label": "Próximo Contacto", "from": "$.proxima_contacto", "format": "date" }
        ]
      }
    ]
  }
}'::jsonb
FROM organizations o
ON CONFLICT (org_id, flow_type) DO NOTHING;

-- CotizacionFlow: cotización CoctelPro
INSERT INTO flow_presentations (org_id, flow_type, presentation_config)
SELECT o.id, 'CotizacionFlow', '{
  "card": {
    "title": { "from": "$.evento_id", "label": "Cotización" },
    "amount": { "from": "$.total", "format": "currency_ars" }
  },
  "detail": {
    "sections": [
      {
        "type": "fields",
        "title": "Cotización",
        "fields": [
          { "label": "Evento", "from": "$.evento_id" },
          { "label": "Total", "from": "$.total", "format": "currency_ars" },
          { "label": "Descuento", "from": "$.descuento", "format": "pct" }
        ]
      }
    ]
  }
}'::jsonb
FROM organizations o
ON CONFLICT (org_id, flow_type) DO NOTHING;

-- architect_flow and multi_crew: no config (fallback)
-- Intentionally left without presentation_config.
-- The dashboard will use the generic fallback renderer.
