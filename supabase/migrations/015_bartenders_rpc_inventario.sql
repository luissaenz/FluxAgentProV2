-- ============================================================
-- Migration 013: Bartenders NOA — RPCs de Inventario
-- Funciones atómicas para reservar y liberar stock.
-- Ejecutar DESPUÉS de 011_bartenders_rls.sql
--
-- Por qué RPC y no UPDATE directo desde Python:
--   Si dos flows corren simultáneamente para el mismo item,
--   ambos podrían leer stock_disponible = 5 y reservar 5 cada uno,
--   resultando en stock_reservado = 10 con stock_actual = 5.
--   Una RPC con FOR UPDATE SKIP LOCKED resuelve esto atómicamente.
-- ============================================================

-- -----------------------------------------------------------
-- reserve_inventory_item
-- Reserva N unidades de un item. Falla si no hay stock.
-- -----------------------------------------------------------
CREATE OR REPLACE FUNCTION reserve_inventory_item(
    p_org_id   UUID,
    p_item_id  TEXT,
    p_cantidad INTEGER
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_disponible INTEGER;
    v_row        inventario%ROWTYPE;
BEGIN
    -- Lock de la fila para evitar race condition
    SELECT * INTO v_row
      FROM inventario
     WHERE org_id = p_org_id
       AND item_id = p_item_id
       FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'error', format('Item %s no encontrado para org %s', p_item_id, p_org_id)
        );
    END IF;

    v_disponible := v_row.stock_actual - v_row.stock_reservado;

    IF v_disponible < p_cantidad THEN
        RETURN jsonb_build_object(
            'error', format(
                'Stock insuficiente para %s: disponible=%s, solicitado=%s',
                p_item_id, v_disponible, p_cantidad
            ),
            'stock_disponible', v_disponible,
            'solicitado',       p_cantidad
        );
    END IF;

    -- Actualizar reserva
    UPDATE inventario
       SET stock_reservado      = stock_reservado + p_cantidad,
           ultima_actualizacion = CURRENT_DATE
     WHERE org_id  = p_org_id
       AND item_id = p_item_id;

    RETURN jsonb_build_object(
        'ok',              TRUE,
        'item_id',         p_item_id,
        'cantidad_reservada', p_cantidad,
        'stock_disponible_restante', v_disponible - p_cantidad
    );
END;
$$;

-- -----------------------------------------------------------
-- release_inventory_item
-- Libera N unidades previamente reservadas.
-- -----------------------------------------------------------
CREATE OR REPLACE FUNCTION release_inventory_item(
    p_org_id   UUID,
    p_item_id  TEXT,
    p_cantidad INTEGER
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_row inventario%ROWTYPE;
BEGIN
    SELECT * INTO v_row
      FROM inventario
     WHERE org_id = p_org_id
       AND item_id = p_item_id
       FOR UPDATE;

    IF NOT FOUND THEN
        RETURN jsonb_build_object(
            'error', format('Item %s no encontrado', p_item_id)
        );
    END IF;

    -- No puede liberar más de lo que está reservado
    IF v_row.stock_reservado < p_cantidad THEN
        RETURN jsonb_build_object(
            'error', format(
                'No se pueden liberar %s unidades: solo %s reservadas',
                p_cantidad, v_row.stock_reservado
            )
        );
    END IF;

    UPDATE inventario
       SET stock_reservado      = stock_reservado - p_cantidad,
           ultima_actualizacion = CURRENT_DATE
     WHERE org_id  = p_org_id
       AND item_id = p_item_id;

    RETURN jsonb_build_object(
        'ok',       TRUE,
        'item_id',  p_item_id,
        'cantidad_liberada', p_cantidad
    );
END;
$$;

-- -----------------------------------------------------------
-- Permisos: solo service_role puede llamar estas funciones
-- (los agentes las llaman a través del conector, no directamente)
-- -----------------------------------------------------------
REVOKE ALL ON FUNCTION reserve_inventory_item FROM PUBLIC;
REVOKE ALL ON FUNCTION release_inventory_item FROM PUBLIC;
GRANT EXECUTE ON FUNCTION reserve_inventory_item TO service_role;
GRANT EXECUTE ON FUNCTION release_inventory_item TO service_role;
