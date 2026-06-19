-- +goose Up
-- +goose StatementBegin

-- =============================================================================
-- 002. Alinear `initiatives` con la plantilla DBI v5.9
-- Ver docs/context/references/dbi-template.md > Reconciliacion con el esquema actual.
-- Corrige 4 conflictos (initiative_type, TRL/CRL/BRL, return_horizon, value_capture)
-- y agrega `dbi_extra JSONB` para los campos nuevos de la plantilla (enfoque hibrido).
-- Las conversiones preservan datos existentes donde es posible.
-- =============================================================================

-- 1. initiative_type: admitir 'mixta'
ALTER TABLE initiatives DROP CONSTRAINT ck_initiatives_type;
ALTER TABLE initiatives ADD CONSTRAINT ck_initiatives_type
  CHECK (initiative_type IN ('interna', 'externa', 'mixta'));

-- 2. TRL/CRL/BRL: de bandas/etiquetas TEXT a nivel entero unico 1-9 (escala v5.9)
ALTER TABLE initiatives DROP CONSTRAINT ck_initiatives_trl;
ALTER TABLE initiatives DROP CONSTRAINT ck_initiatives_crl;
ALTER TABLE initiatives DROP CONSTRAINT ck_initiatives_brl;

ALTER TABLE initiatives
  ALTER COLUMN trl TYPE SMALLINT USING (
    CASE trl
      WHEN 'TRL 1-2' THEN 2
      WHEN 'TRL 3-4' THEN 4
      WHEN 'TRL 5-6' THEN 6
      WHEN 'TRL 7-9' THEN 8
      ELSE NULLIF(regexp_replace(COALESCE(trl, ''), '\D', '', 'g'), '')::smallint
    END
  );
ALTER TABLE initiatives
  ALTER COLUMN crl TYPE SMALLINT USING (
    NULLIF(regexp_replace(COALESCE(crl, ''), '\D', '', 'g'), '')::smallint
  );
ALTER TABLE initiatives
  ALTER COLUMN brl TYPE SMALLINT USING (
    NULLIF(regexp_replace(COALESCE(brl, ''), '\D', '', 'g'), '')::smallint
  );

ALTER TABLE initiatives ADD CONSTRAINT ck_initiatives_trl
  CHECK (trl IS NULL OR trl BETWEEN 1 AND 9);
ALTER TABLE initiatives ADD CONSTRAINT ck_initiatives_crl
  CHECK (crl IS NULL OR crl BETWEEN 1 AND 9);
ALTER TABLE initiatives ADD CONSTRAINT ck_initiatives_brl
  CHECK (brl IS NULL OR brl BETWEEN 1 AND 9);

-- 3. return_horizon: de bandas TEXT a meses (entero)
ALTER TABLE initiatives DROP CONSTRAINT ck_initiatives_return_horizon;
ALTER TABLE initiatives
  ALTER COLUMN return_horizon TYPE SMALLINT USING (
    CASE return_horizon
      WHEN '0-6'   THEN 6
      WHEN '6-12'  THEN 12
      WHEN '12-18' THEN 18
      WHEN '18-24' THEN 24
      WHEN '+24'   THEN 25
      WHEN 'no se' THEN NULL
      ELSE NULLIF(regexp_replace(COALESCE(return_horizon, ''), '\D', '', 'g'), '')::smallint
    END
  );
ALTER TABLE initiatives ADD CONSTRAINT ck_initiatives_return_horizon
  CHECK (return_horizon IS NULL OR return_horizon >= 0);

-- 4. value_capture: la plantilla v5.9 lo registra como mecanismo en texto libre (bloque F)
ALTER TABLE initiatives DROP CONSTRAINT ck_initiatives_value_capture;

-- 5. dbi_extra: campos nuevos de la plantilla v5.9 sin columna dedicada (hibrido JSONB)
ALTER TABLE initiatives ADD COLUMN dbi_extra JSONB;

-- Comentarios actualizados
COMMENT ON COLUMN initiatives.initiative_type IS 'Tipo: interna, externa o mixta.';
COMMENT ON COLUMN initiatives.trl IS 'Bloque B: nivel TRL entero 1-9 (escala v5.9).';
COMMENT ON COLUMN initiatives.crl IS 'Bloque C: nivel CRL entero 1-9 (escala v5.9).';
COMMENT ON COLUMN initiatives.brl IS 'Bloque F: nivel BRL entero 1-9 (escala v5.9).';
COMMENT ON COLUMN initiatives.return_horizon IS 'Bloque G: horizonte de retorno en meses (entero).';
COMMENT ON COLUMN initiatives.value_capture IS 'Bloque F: mecanismo de captura de valor (texto libre).';
COMMENT ON COLUMN initiatives.dbi_extra IS 'Campos de la plantilla DBI v5.9 sin columna dedicada: resumen ejecutivo, sub-campos de A, diferenciador/novedad, competencia, desglose de impacto, TAM/SAM/SOM, mercado/repetibilidad, tipo de cliente objetivo, evidencia TRL/CRL/BRL, horizonte H1/H2/H3, apoyo recibido, otros recursos, incertidumbre, evidencia adjunta, bloques pendientes. Ver docs/context/references/dbi-template.md.';

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

-- =============================================================================
-- Revertir 002: volver al esquema de 001 (bandas/etiquetas TEXT, enums).
-- NOTA: la reversion es lossy. Filas 'mixta' -> 'externa'; niveles CRL/BRL > 4
-- y value_capture fuera del enum -> NULL.
-- =============================================================================

ALTER TABLE initiatives DROP COLUMN IF EXISTS dbi_extra;

-- value_capture: re-imponer enum (coercionar valores fuera de dominio)
UPDATE initiatives SET value_capture = NULL
  WHERE value_capture IS NOT NULL
    AND value_capture NOT IN ('ahorro', 'venta', 'competitividad', 'nuevo negocio', 'no claro');
ALTER TABLE initiatives ADD CONSTRAINT ck_initiatives_value_capture
  CHECK (value_capture IS NULL OR value_capture IN (
    'ahorro', 'venta', 'competitividad', 'nuevo negocio', 'no claro'
  ));

-- return_horizon: meses -> bandas TEXT
ALTER TABLE initiatives DROP CONSTRAINT ck_initiatives_return_horizon;
ALTER TABLE initiatives
  ALTER COLUMN return_horizon TYPE TEXT USING (
    CASE
      WHEN return_horizon IS NULL    THEN NULL
      WHEN return_horizon <= 6       THEN '0-6'
      WHEN return_horizon <= 12      THEN '6-12'
      WHEN return_horizon <= 18      THEN '12-18'
      WHEN return_horizon <= 24      THEN '18-24'
      ELSE '+24'
    END
  );
ALTER TABLE initiatives ADD CONSTRAINT ck_initiatives_return_horizon
  CHECK (return_horizon IS NULL OR return_horizon IN ('0-6', '6-12', '12-18', '18-24', '+24', 'no se'));

-- TRL/CRL/BRL: enteros -> bandas/etiquetas TEXT
ALTER TABLE initiatives DROP CONSTRAINT ck_initiatives_trl;
ALTER TABLE initiatives DROP CONSTRAINT ck_initiatives_crl;
ALTER TABLE initiatives DROP CONSTRAINT ck_initiatives_brl;

ALTER TABLE initiatives
  ALTER COLUMN trl TYPE TEXT USING (
    CASE
      WHEN trl IS NULL          THEN NULL
      WHEN trl BETWEEN 1 AND 2  THEN 'TRL 1-2'
      WHEN trl BETWEEN 3 AND 4  THEN 'TRL 3-4'
      WHEN trl BETWEEN 5 AND 6  THEN 'TRL 5-6'
      ELSE 'TRL 7-9'
    END
  );
ALTER TABLE initiatives
  ALTER COLUMN crl TYPE TEXT USING (
    CASE WHEN crl BETWEEN 1 AND 4 THEN 'CRL ' || crl::text ELSE NULL END
  );
ALTER TABLE initiatives
  ALTER COLUMN brl TYPE TEXT USING (
    CASE WHEN brl BETWEEN 1 AND 4 THEN 'BRL ' || brl::text ELSE NULL END
  );

ALTER TABLE initiatives ADD CONSTRAINT ck_initiatives_trl
  CHECK (trl IS NULL OR trl IN ('TRL 1-2', 'TRL 3-4', 'TRL 5-6', 'TRL 7-9'));
ALTER TABLE initiatives ADD CONSTRAINT ck_initiatives_crl
  CHECK (crl IS NULL OR crl IN ('CRL 1', 'CRL 2', 'CRL 3', 'CRL 4'));
ALTER TABLE initiatives ADD CONSTRAINT ck_initiatives_brl
  CHECK (brl IS NULL OR brl IN ('BRL 1', 'BRL 2', 'BRL 3', 'BRL 4'));

-- initiative_type: quitar 'mixta'
UPDATE initiatives SET initiative_type = 'externa' WHERE initiative_type = 'mixta';
ALTER TABLE initiatives DROP CONSTRAINT ck_initiatives_type;
ALTER TABLE initiatives ADD CONSTRAINT ck_initiatives_type
  CHECK (initiative_type IN ('interna', 'externa'));

-- Restaurar comentarios originales
COMMENT ON COLUMN initiatives.initiative_type IS 'Tipo: interna o externa.';
COMMENT ON COLUMN initiatives.trl IS 'Bloque B.3: TRL 1-2 / 3-4 / 5-6 / 7-9.';
COMMENT ON COLUMN initiatives.crl IS 'Bloque C: CRL 1-4.';
COMMENT ON COLUMN initiatives.brl IS 'Bloque F: BRL 1-4.';
COMMENT ON COLUMN initiatives.return_horizon IS 'Bloque G: 0-6/6-12/12-18/18-24/+24/no se.';
COMMENT ON COLUMN initiatives.value_capture IS 'Bloque F: ahorro/venta/competitividad/nuevo negocio/no claro.';

-- +goose StatementEnd
