-- +goose Up
-- +goose StatementBegin

-- =============================================================================
-- 003. Funcion atomica para persistir iniciativa + transicionar sesion.
--
-- El bridge Management API de Supabase ejecuta cada query como HTTP request
-- individual (no hay BEGIN/COMMIT desde el cliente). Esta funcion encapsula
-- INSERT en initiatives + UPDATE de sessions en una sola operacion PL/pgSQL,
-- que es inherentemente transaccional (cualquier error → ROLLBACK automatico).
--
-- Se llama via: SELECT * FROM persist_initiative_atomic(...)
-- =============================================================================

CREATE OR REPLACE FUNCTION persist_initiative_atomic(
    _session_id         bigint,
    _user_id            uuid,
    _title              text,
    _initiative_type    text,
    _postulation_date   date,
    _area               text,
    _applicant_name     text,
    _problem            text,
    _solution           text,
    _economic_impact    text,
    _trl                smallint,
    _scalability        text,
    _internal_client    text,
    _external_client    text,
    _crl                smallint,
    _sponsor            text,
    _internal_team      text,
    _external_team      text,
    _estimated_duration text,
    _main_doubt         text,
    _key_condition      text,
    _value_capture      text,
    _brl                smallint,
    _technical_milestones  text,
    _financial_milestones  text,
    _return_horizon     smallint,
    _strategic_alignment text,
    _dbi_raw_text       text,
    _dbi_extra          jsonb
) RETURNS SETOF initiatives
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    _seq_num bigint;
    _code    text;
    _init_id bigint;
BEGIN
    -- Generar initiative_code: INI-YYYY-NNN
    _seq_num := nextval('seq_initiative_code');
    _code := 'INI-' || to_char(date_part('year', now()), 'FM0000')
                  || '-' || to_char(_seq_num, 'FM000');

    -- Insertar iniciativa
    INSERT INTO initiatives (
        session_id, user_id, status, initiative_code,
        title, initiative_type, postulation_date, area,
        applicant_name, problem, solution,
        economic_impact, trl, scalability,
        internal_client, external_client, crl,
        sponsor, internal_team, external_team,
        estimated_duration,
        main_doubt, key_condition, value_capture, brl,
        technical_milestones, financial_milestones,
        return_horizon, strategic_alignment,
        dbi_raw_text, dbi_extra
    ) VALUES (
        _session_id, _user_id, 'persistido', _code,
        _title, _initiative_type, _postulation_date, _area,
        _applicant_name, _problem, _solution,
        _economic_impact, _trl, _scalability,
        _internal_client, _external_client, _crl,
        _sponsor, _internal_team, _external_team,
        _estimated_duration,
        _main_doubt, _key_condition, _value_capture, _brl,
        _technical_milestones, _financial_milestones,
        _return_horizon, _strategic_alignment,
        _dbi_raw_text, _dbi_extra
    ) RETURNING id INTO _init_id;

    -- Transicionar sesion a completed (atomico con el INSERT)
    UPDATE sessions
    SET status     = 'completed',
        ended_at   = now(),
        updated_at = now()
    WHERE id = _session_id;

    -- Devolver la fila insertada
    RETURN QUERY SELECT * FROM initiatives WHERE id = _init_id;
END;
$$;

COMMENT ON FUNCTION persist_initiative_atomic(
    bigint, uuid, text, text, date, text, text, text, text, text,
    smallint, text, text, text, smallint, text, text, text, text,
    text, text, text, smallint, text, text, smallint, text, text, jsonb
) IS 'Inserta una iniciativa y transiciona la sesion a completed en una sola operacion atomica (PL/pgSQL). Genera initiative_code via seq_initiative_code.';

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

DROP FUNCTION IF EXISTS persist_initiative_atomic(
    bigint, uuid, text, text, date, text, text, text, text, text,
    smallint, text, text, text, smallint, text, text, text, text,
    text, text, text, smallint, text, text, smallint, text, text, jsonb
);

-- +goose StatementEnd
