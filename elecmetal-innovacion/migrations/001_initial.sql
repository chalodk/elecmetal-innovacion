-- +goose Up
-- +goose StatementBegin

-- =============================================================================
-- 01. profiles
-- =============================================================================
CREATE TABLE profiles (
  id          UUID        NOT NULL,
  full_name   TEXT        NOT NULL,
  role        TEXT        NOT NULL DEFAULT 'postulante',
  avatar_url  TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT pk_profiles PRIMARY KEY (id),
  CONSTRAINT ck_profiles_role CHECK (role IN ('postulante', 'directora', 'admin'))
);

COMMENT ON TABLE profiles IS 'Perfil de usuario vinculado a auth.users de Supabase.';
COMMENT ON COLUMN profiles.id IS 'Mismo ID de Supabase Auth.';
COMMENT ON COLUMN profiles.full_name IS 'Nombre completo del usuario.';
COMMENT ON COLUMN profiles.role IS 'Rol: postulante, directora, admin.';
COMMENT ON COLUMN profiles.avatar_url IS 'URL del avatar.';
COMMENT ON COLUMN profiles.created_at IS 'Fecha de creacion del perfil.';
COMMENT ON COLUMN profiles.updated_at IS 'Ultima actualizacion del perfil.';

-- Trigger: auto-create profile on Supabase Auth signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, full_name, role)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.email),
    'postulante'
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- NOTE: This trigger requires Supabase Auth. Run only with Supabase.
-- For standalone PostgreSQL, comment out the trigger and create profiles manually.

-- =============================================================================
-- 02. agent_configs
-- =============================================================================
CREATE TABLE agent_configs (
  id              BIGINT       GENERATED ALWAYS AS IDENTITY,
  agent_name      TEXT         NOT NULL,
  version         TEXT         NOT NULL,
  prompt_text     TEXT         NOT NULL,
  base_knowledge  TEXT,
  skill_file      TEXT,
  is_active       BOOLEAN      NOT NULL DEFAULT true,
  created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),

  CONSTRAINT pk_agent_configs PRIMARY KEY (id),
  CONSTRAINT uq_agent_configs_name_version UNIQUE (agent_name, version)
);

COMMENT ON TABLE agent_configs IS 'Configuracion versionada de agentes IA. Permite reemplazar prompts y skills sin rediseno.';
COMMENT ON COLUMN agent_configs.id IS 'PK auto-incremental.';
COMMENT ON COLUMN agent_configs.agent_name IS 'Identificador del agente: clara, analista_oportunidad, evaluador.';
COMMENT ON COLUMN agent_configs.version IS 'Version del prompt: v5.4, v2, etc.';
COMMENT ON COLUMN agent_configs.prompt_text IS 'Prompt completo del agente.';
COMMENT ON COLUMN agent_configs.base_knowledge IS 'Path al archivo de conocimiento base (PDF o MD).';
COMMENT ON COLUMN agent_configs.skill_file IS 'Path al archivo de skill (.skill).';
COMMENT ON COLUMN agent_configs.is_active IS 'Solo una version activa por agente a la vez.';
COMMENT ON COLUMN agent_configs.created_at IS 'Fecha de creacion de esta version.';
COMMENT ON COLUMN agent_configs.updated_at IS 'Ultima modificacion de esta version.';

CREATE INDEX idx_agent_configs_agent_name ON agent_configs(agent_name);
CREATE INDEX idx_agent_configs_is_active ON agent_configs(is_active) WHERE is_active = true;

-- =============================================================================
-- 03. sessions
-- =============================================================================
CREATE TABLE sessions (
  id          BIGINT       GENERATED ALWAYS AS IDENTITY,
  user_id     UUID         NOT NULL,
  agent_type  TEXT         NOT NULL,
  status      TEXT         NOT NULL DEFAULT 'active',
  title       TEXT,
  started_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
  ended_at    TIMESTAMPTZ,
  created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),

  CONSTRAINT pk_sessions PRIMARY KEY (id),
  CONSTRAINT fk_sessions_profiles FOREIGN KEY (user_id) REFERENCES profiles(id) ON DELETE CASCADE,
  CONSTRAINT ck_sessions_agent_type CHECK (agent_type IN ('clara', 'analista_oportunidad')),
  CONSTRAINT ck_sessions_status CHECK (status IN ('active', 'completed', 'abandoned'))
);

COMMENT ON TABLE sessions IS 'Sesion de chat entre un usuario y un agente IA.';
COMMENT ON COLUMN sessions.id IS 'PK auto-incremental.';
COMMENT ON COLUMN sessions.user_id IS 'Usuario que inicio la sesion.';
COMMENT ON COLUMN sessions.agent_type IS 'Agente IA: clara o analista_oportunidad.';
COMMENT ON COLUMN sessions.status IS 'Estado: active, completed, abandoned.';
COMMENT ON COLUMN sessions.title IS 'Titulo para sidebar (primeras palabras del chat).';
COMMENT ON COLUMN sessions.started_at IS 'Momento de inicio de la sesion.';
COMMENT ON COLUMN sessions.ended_at IS 'Momento de cierre de la sesion.';
COMMENT ON COLUMN sessions.created_at IS 'Fecha de creacion del registro.';
COMMENT ON COLUMN sessions.updated_at IS 'Ultima actualizacion del registro.';

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_status ON sessions(status);

-- =============================================================================
-- 04. messages
-- =============================================================================
CREATE TABLE messages (
  id          BIGINT       GENERATED ALWAYS AS IDENTITY,
  session_id  BIGINT       NOT NULL,
  role        TEXT         NOT NULL,
  content     TEXT         NOT NULL,
  metadata    JSONB,
  created_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),

  CONSTRAINT pk_messages PRIMARY KEY (id),
  CONSTRAINT fk_messages_sessions FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
  CONSTRAINT ck_messages_role CHECK (role IN ('user', 'assistant', 'system'))
);

COMMENT ON TABLE messages IS 'Mensaje individual dentro de una sesion de chat.';
COMMENT ON COLUMN messages.id IS 'PK auto-incremental.';
COMMENT ON COLUMN messages.session_id IS 'Sesion a la que pertenece el mensaje.';
COMMENT ON COLUMN messages.role IS 'Rol del emisor: user, assistant, system.';
COMMENT ON COLUMN messages.content IS 'Contenido del mensaje.';
COMMENT ON COLUMN messages.metadata IS 'Metadatos: tokens usados, bloque DBI referenciado, etc.';
COMMENT ON COLUMN messages.created_at IS 'Momento de envio del mensaje.';

CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);

-- =============================================================================
-- 05. initiatives
-- =============================================================================
CREATE SEQUENCE seq_initiative_code;

CREATE TABLE initiatives (
  id                    BIGINT       GENERATED ALWAYS AS IDENTITY,
  session_id            BIGINT,
  user_id               UUID         NOT NULL,
  status                TEXT         NOT NULL DEFAULT 'dbi_generado',
  initiative_code       TEXT         NOT NULL,
  title                 TEXT         NOT NULL,
  initiative_type       TEXT         NOT NULL,
  postulation_date      DATE         NOT NULL DEFAULT CURRENT_DATE,
  area                  TEXT         NOT NULL,
  applicant_name        TEXT         NOT NULL,
  problem               TEXT         NOT NULL,
  solution              TEXT         NOT NULL,
  economic_impact       TEXT,
  trl                   TEXT,
  scalability           TEXT,
  internal_client       TEXT,
  external_client       TEXT,
  crl                   TEXT,
  sponsor               TEXT,
  internal_team         TEXT,
  external_team         TEXT,
  estimated_duration    TEXT,
  main_doubt            TEXT,
  key_condition         TEXT,
  value_capture         TEXT,
  brl                   TEXT,
  technical_milestones  TEXT,
  financial_milestones  TEXT,
  return_horizon        TEXT,
  strategic_alignment   TEXT,
  dbi_raw_text          TEXT,
  created_at            TIMESTAMPTZ  NOT NULL DEFAULT now(),
  updated_at            TIMESTAMPTZ  NOT NULL DEFAULT now(),

  CONSTRAINT pk_initiatives PRIMARY KEY (id),
  CONSTRAINT fk_initiatives_sessions FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE SET NULL,
  CONSTRAINT fk_initiatives_profiles FOREIGN KEY (user_id) REFERENCES profiles(id) ON DELETE RESTRICT,
  CONSTRAINT uq_initiatives_code UNIQUE (initiative_code),
  CONSTRAINT ck_initiatives_status CHECK (status IN (
    'dbi_generado', 'persistido', 'notificado', 'en_evaluacion', 'evaluado', 'validado', 'veredicto'
  )),
  CONSTRAINT ck_initiatives_type CHECK (initiative_type IN ('interna', 'externa')),
  CONSTRAINT ck_initiatives_trl CHECK (trl IS NULL OR trl IN ('TRL 1-2', 'TRL 3-4', 'TRL 5-6', 'TRL 7-9')),
  CONSTRAINT ck_initiatives_scalability CHECK (scalability IS NULL OR scalability IN ('Local', 'Interna', 'Externa')),
  CONSTRAINT ck_initiatives_crl CHECK (crl IS NULL OR crl IN ('CRL 1', 'CRL 2', 'CRL 3', 'CRL 4')),
  CONSTRAINT ck_initiatives_brl CHECK (brl IS NULL OR brl IN ('BRL 1', 'BRL 2', 'BRL 3', 'BRL 4')),
  CONSTRAINT ck_initiatives_return_horizon CHECK (return_horizon IS NULL OR return_horizon IN (
    '0-6', '6-12', '12-18', '18-24', '+24', 'no se'
  )),
  CONSTRAINT ck_initiatives_value_capture CHECK (value_capture IS NULL OR value_capture IN (
    'ahorro', 'venta', 'competitividad', 'nuevo negocio', 'no claro'
  ))
);

COMMENT ON TABLE initiatives IS 'Postulacion de innovacion (DBI parseado a campos estructurados).';
COMMENT ON COLUMN initiatives.id IS 'PK auto-incremental.';
COMMENT ON COLUMN initiatives.session_id IS 'Sesion con Clara que produjo esta iniciativa (nullable si se crea sin sesion).';
COMMENT ON COLUMN initiatives.user_id IS 'Postulante que creo la iniciativa.';
COMMENT ON COLUMN initiatives.status IS 'Ciclo de vida: dbi_generado -> persistido -> notificado -> en_evaluacion -> evaluado -> validado -> veredicto.';
COMMENT ON COLUMN initiatives.initiative_code IS 'Codigo unico autogenerado: INI-AAAA-NNN.';
COMMENT ON COLUMN initiatives.title IS 'Titulo del DBI.';
COMMENT ON COLUMN initiatives.initiative_type IS 'Tipo: interna o externa.';
COMMENT ON COLUMN initiatives.postulation_date IS 'Fecha de postulacion.';
COMMENT ON COLUMN initiatives.area IS 'Area del postulante (Bloque E).';
COMMENT ON COLUMN initiatives.applicant_name IS 'Nombre del postulante.';
COMMENT ON COLUMN initiatives.problem IS 'Bloque A: descripcion consolidada del problema.';
COMMENT ON COLUMN initiatives.solution IS 'Bloque B.1: descripcion y diferenciador de la solucion.';
COMMENT ON COLUMN initiatives.economic_impact IS 'Bloque B.2: impacto economico (valor + fuente + tipo).';
COMMENT ON COLUMN initiatives.trl IS 'Bloque B.3: TRL 1-2 / 3-4 / 5-6 / 7-9.';
COMMENT ON COLUMN initiatives.scalability IS 'Bloque B.4: Local / Interna / Externa.';
COMMENT ON COLUMN initiatives.internal_client IS 'Bloque C: cliente interno.';
COMMENT ON COLUMN initiatives.external_client IS 'Bloque C: cliente externo o "no aplica".';
COMMENT ON COLUMN initiatives.crl IS 'Bloque C: CRL 1-4.';
COMMENT ON COLUMN initiatives.sponsor IS 'Bloque E: patrocinador.';
COMMENT ON COLUMN initiatives.internal_team IS 'Bloque E: equipo interno.';
COMMENT ON COLUMN initiatives.external_team IS 'Bloque E: equipo externo.';
COMMENT ON COLUMN initiatives.estimated_duration IS 'Bloque E: duracion estimada.';
COMMENT ON COLUMN initiatives.main_doubt IS 'Bloque F: duda principal.';
COMMENT ON COLUMN initiatives.key_condition IS 'Bloque F: condicion clave.';
COMMENT ON COLUMN initiatives.value_capture IS 'Bloque F: ahorro/venta/competitividad/nuevo negocio/no claro.';
COMMENT ON COLUMN initiatives.brl IS 'Bloque F: BRL 1-4.';
COMMENT ON COLUMN initiatives.technical_milestones IS 'Bloque G: hitos tecnicos.';
COMMENT ON COLUMN initiatives.financial_milestones IS 'Bloque G: hitos financieros.';
COMMENT ON COLUMN initiatives.return_horizon IS 'Bloque G: 0-6/6-12/12-18/18-24/+24/no se.';
COMMENT ON COLUMN initiatives.strategic_alignment IS 'Bloque D: alineamiento estrategico (asignado por equipo de innovacion).';
COMMENT ON COLUMN initiatives.dbi_raw_text IS 'Texto completo del DBI original generado por Clara.';
COMMENT ON COLUMN initiatives.created_at IS 'Fecha de creacion de la iniciativa.';
COMMENT ON COLUMN initiatives.updated_at IS 'Ultima actualizacion de la iniciativa.';

CREATE INDEX idx_initiatives_user_id ON initiatives(user_id);
CREATE INDEX idx_initiatives_session_id ON initiatives(session_id);
CREATE INDEX idx_initiatives_status ON initiatives(status);

-- =============================================================================
-- 06. evaluations
-- =============================================================================
CREATE TABLE evaluations (
  id              BIGINT       GENERATED ALWAYS AS IDENTITY,
  initiative_id   BIGINT       NOT NULL,
  activated_by    UUID         NOT NULL,
  status          TEXT         NOT NULL DEFAULT 'pending',
  results         JSONB,
  reviewed_by     UUID,
  reviewed_at     TIMESTAMPTZ,
  veredicto       TEXT,
  created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),

  CONSTRAINT pk_evaluations PRIMARY KEY (id),
  CONSTRAINT fk_evaluations_initiatives FOREIGN KEY (initiative_id) REFERENCES initiatives(id) ON DELETE CASCADE,
  CONSTRAINT fk_evaluations_activated_by FOREIGN KEY (activated_by) REFERENCES profiles(id) ON DELETE RESTRICT,
  CONSTRAINT fk_evaluations_reviewed_by FOREIGN KEY (reviewed_by) REFERENCES profiles(id) ON DELETE SET NULL,
  CONSTRAINT uq_evaluations_initiative UNIQUE (initiative_id),
  CONSTRAINT ck_evaluations_status CHECK (status IN ('pending', 'in_progress', 'completed')),
  CONSTRAINT ck_evaluations_veredicto CHECK (veredicto IS NULL OR veredicto IN ('aprobada', 'rechazada', 'pendiente'))
);

COMMENT ON TABLE evaluations IS 'Evaluacion IA de una iniciativa. Una iniciativa tiene a lo sumo una evaluacion.';
COMMENT ON COLUMN evaluations.id IS 'PK auto-incremental.';
COMMENT ON COLUMN evaluations.initiative_id IS 'Iniciativa evaluada (relacion 1:1).';
COMMENT ON COLUMN evaluations.activated_by IS 'Directora que activo la evaluacion.';
COMMENT ON COLUMN evaluations.status IS 'Estado: pending, in_progress, completed.';
COMMENT ON COLUMN evaluations.results IS 'Resultados del Evaluador: columnas 26-38 en JSONB flexible.';
COMMENT ON COLUMN evaluations.reviewed_by IS 'Directora que reviso y valido los resultados (nullable).';
COMMENT ON COLUMN evaluations.reviewed_at IS 'Momento de la validacion.';
COMMENT ON COLUMN evaluations.veredicto IS 'Decision del comité: aprobada, rechazada, pendiente.';
COMMENT ON COLUMN evaluations.created_at IS 'Fecha de creacion de la evaluacion.';
COMMENT ON COLUMN evaluations.updated_at IS 'Ultima actualizacion de la evaluacion.';

CREATE INDEX idx_evaluations_activated_by ON evaluations(activated_by);

-- =============================================================================
-- 07. notifications
-- =============================================================================
CREATE TABLE notifications (
  id                  BIGINT       GENERATED ALWAYS AS IDENTITY,
  initiative_id       BIGINT       NOT NULL,
  recipient_user_id   UUID         NOT NULL,
  notification_type   TEXT         NOT NULL,
  status              TEXT         NOT NULL DEFAULT 'pending',
  sent_at             TIMESTAMPTZ,
  metadata            JSONB,
  created_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),

  CONSTRAINT pk_notifications PRIMARY KEY (id),
  CONSTRAINT fk_notifications_initiatives FOREIGN KEY (initiative_id) REFERENCES initiatives(id) ON DELETE CASCADE,
  CONSTRAINT fk_notifications_profiles FOREIGN KEY (recipient_user_id) REFERENCES profiles(id) ON DELETE CASCADE,
  CONSTRAINT ck_notifications_type CHECK (notification_type IN ('receipt_to_applicant', 'notice_to_director')),
  CONSTRAINT ck_notifications_status CHECK (status IN ('pending', 'sent', 'failed'))
);

COMMENT ON TABLE notifications IS 'Registro de notificaciones enviadas por el sistema.';
COMMENT ON COLUMN notifications.id IS 'PK auto-incremental.';
COMMENT ON COLUMN notifications.initiative_id IS 'Iniciativa relacionada.';
COMMENT ON COLUMN notifications.recipient_user_id IS 'Usuario destinatario.';
COMMENT ON COLUMN notifications.notification_type IS 'Tipo: receipt_to_applicant, notice_to_director.';
COMMENT ON COLUMN notifications.status IS 'Estado: pending, sent, failed.';
COMMENT ON COLUMN notifications.sent_at IS 'Momento del envio exitoso.';
COMMENT ON COLUMN notifications.metadata IS 'Metadatos del email: destinatario, error info, etc.';
COMMENT ON COLUMN notifications.created_at IS 'Fecha de creacion del registro.';

CREATE INDEX idx_notifications_initiative_id ON notifications(initiative_id);
CREATE INDEX idx_notifications_recipient_user_id ON notifications(recipient_user_id);

-- =============================================================================
-- Seeds: agent configurations
-- Nota: los prompts completos estan en los archivos fuente de /input.
-- Aqui se siembran versiones resumidas como referencia. El backend carga
-- los prompts completos desde los archivos al inicializar los agentes.
-- =============================================================================

-- Clara v5.4
INSERT INTO agent_configs (agent_name, version, prompt_text, base_knowledge, is_active)
VALUES (
  'clara',
  'v5.4',
  'CLARA v5.4 — Asistente de postulacion de iniciativas ME Elecmetal.
Guia al postulante bloque por bloque (A->clasificacion->B->C->resumen->E->F->G->entrega).
Reglas: una pregunta por turno, sin jerga, sin inventar datos, TRL/CRL/BRL solo en DBI final.
DBI: 7 bloques (A-G). A, B, C obligatorios. D clasificacion interna. E-G opcionales.
Fuente: Clara_Prompt_v5_4_GPT.md + Base_de_Conocimiento_Clara.pdf.',
  'Base_de_Conocimiento_Clara.pdf',
  true
);

-- Analista de Oportunidad v2
INSERT INTO agent_configs (agent_name, version, prompt_text, skill_file, is_active)
VALUES (
  'analista_oportunidad',
  'v2',
  'Analista de Oportunidad Economica v2 — Modela TAM/SAM/SOM de ideas de innovacion.
Maquina de estados A-L. Calcula revenue anual a Ano 5, USD nominal, una geografia a la vez.
Entrada: 6 campos (Titulo, Propuesta de valor, Segmento, Necesidad, Categoria, Beneficio).
Catalogo de 8 plantillas de modelamiento (P1-P8). Outputs: data row, narrativa, slide-ready.
Fuente: prompt_analista_oportunidad_v2.md + tam-sam-som-modeler.skill.',
  'tam-sam-som-modeler.skill',
  true
);

-- Evaluador v1 (placeholder)
INSERT INTO agent_configs (agent_name, version, prompt_text, is_active)
VALUES (
  'evaluador',
  'v1',
  'Evaluador de Iniciativas v1 — Evalua postulaciones aprobadas por la directora.
Genera columnas 26-38: dimensiones, admisibilidad y ruta de la iniciativa.
Prompt completo pendiente de carga por el equipo de innovacion.',
  true
);

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin

DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS evaluations CASCADE;
DROP TABLE IF EXISTS initiatives CASCADE;
DROP SEQUENCE IF EXISTS seq_initiative_code;
DROP TABLE IF EXISTS messages CASCADE;
DROP TABLE IF EXISTS sessions CASCADE;
DROP TABLE IF EXISTS agent_configs CASCADE;
DROP TABLE IF EXISTS profiles CASCADE;
DROP FUNCTION IF EXISTS public.handle_new_user();

-- +goose StatementEnd
