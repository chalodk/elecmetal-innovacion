# Business Rules: Plataforma de Innovacion Elecmetal

## Flujo de Postulacion

**Regla:** El postulante solo puede tener una sesion activa con Clara a la vez.
**Justificacion:** Clara guia el proceso bloque por bloque en orden. Tener multiples sesiones simultaneas generaria DBIs inconsistentes.

**Regla:** Clara sigue un ciclo estricto: UNA pregunta por turno → respuesta del usuario → confirmacion → avance al siguiente bloque.
**Justificacion:** El prompt v5.4 esta disenado para evitar abrumar al postulante y asegurar que cada bloque quede completo antes de avanzar.

**Regla:** Si el postulante no puede responder tras 2 intentos de desbloqueo, Clara ofrece opciones basadas en lo recopilado. Si aun no puede, registra "PENDIENTE — el equipo de innovacion completara con el postulante."
**Justificacion:** No se puede forzar al postulante a inventar datos. Los pendientes se resuelven offline con el equipo de innovacion.

**Regla:** Los bloques A, B y C son obligatorios. Sin ellos la iniciativa no se considera completa.
**Justificacion:** Problema (A), solucion (B) y cliente (C) son el nucleo minimo que el comite necesita para evaluar.

**Regla:** Los bloques E (equipo), F (riesgo) y G (hitos) son opcionales pero fortalecen la postulacion. El postulante decide si completarlos.
**Justificacion:** No toda idea tiene equipo formado o madurez de modelo. Forzar esos campos generaria datos falsos.

**Regla:** El bloque D (alineamiento estrategico) NO se pregunta al postulante. Lo asigna internamente el equipo de innovacion.
**Justificacion:** El postulante no necesariamente conoce los focos estrategicos de la compania. La clasificacion es editorial, no declarativa.

## Estructuracion y Persistencia

**Regla:** Clara genera el DBI usando una plantilla exacta con delimitadores predecibles. El sistema parsea ese formato para extraer los 25 campos.
**Justificacion:** El parseo debe ser deterministico. Si la plantilla cambia, se actualiza el parser y se siembra una nueva version en `agent_configs`.

**Regla:** El `initiative_code` se autogenera con formato INI-AAAA-NNN (AAAA = ano, NNN = secuencial).
**Justificacion:** Codigo unico, legible y ordenable. La secuencia `seq_initiative_code` gestiona el contador.

**Regla:** El mail de confirmacion al postulante se dispara SOLO despues de confirmar que los 25 campos se guardaron correctamente en base de datos.
**Justificacion:** Si el parseo falla, no se debe notificar al postulante con datos incompletos.

**Regla:** La notificacion a la directora se envia simultaneamente con el mail al postulante.
**Justificacion:** Ambas dependen de la misma condicion (persistencia exitosa). No hay orden entre ellas.

## Evaluacion

**Regla:** Solo la directora puede activar al Evaluador. No se ejecuta automaticamente al llegar una postulacion.
**Justificacion:** La directora debe revisar preliminarmente la postulacion antes de decidir si merece evaluacion formal.

**Regla:** Una iniciativa tiene a lo sumo UNA evaluacion activa o completada. La relacion es 1:0..1.
**Justificacion:** El flujo actual no contempla reevaluaciones. Si en el futuro se requieren, se puede relajar el UNIQUE y versionar evaluaciones.

**Regla:** Las columnas 26-38 se almacenan como JSONB. La directora puede revisar, ajustar y completar estos campos antes del veredicto.
**Justificacion:** El esquema de salida del Evaluador no esta completamente definido. JSONB da flexibilidad sin bloquear el desarrollo.

**Regla:** El veredicto final lo emite el comité Sandbox fuera del sistema. La plataforma solo registra el resultado (aprobada/rechazada/pendiente).
**Justificacion:** La decision es humana y colegiada. La plataforma es herramienta de soporte, no de decision automatica.

## Agentes IA

**Regla:** Los tres agentes (Clara, Analista de Oportunidad, Evaluador) son Custom GPTs de OpenAI. Sus prompts, skills y tools existen y se consumen sin modificar.
**Justificacion:** Separar contenido de agente (prompts) de plataforma (codigo) permite que el equipo de innovacion itere los prompts sin tocar codigo.

**Regla:** Cada agente tiene versiones. Solo una version esta activa a la vez (`is_active = true`).
**Justificacion:** El versionado permite A/B testing, rollback seguro, y auditoria de que prompt se uso en cada momento historico.

**Regla:** El Analista de Oportunidad (Chat Dimensionador) es un agente independiente. No comparte sesion con Clara ni sus datos se heredan al DBI automaticamente.
**Justificacion:** Son herramientas distintas para momentos distintos. El postulante puede usar el analisis como insumo durante la conversacion con Clara, pero la transferencia es manual.

## Usuarios y Permisos

**Regla:** Hay tres roles: postulante, directora, admin. El rol se asigna en `profiles.role`.
**Justificacion:** RBAC simple para MVP. Si se necesitan permisos mas granulares, migrar a tabla `roles` + `permissions`.

**Regla:** Los perfiles se crean automaticamente al registrarse en Supabase Auth via trigger `handle_new_user()`. El rol default es 'postulante'.
**Justificacion:** Todo usuario que se registra es postulante por defecto. La promocion a directora/admin la hace un admin manualmente.

**Regla:** Solo usuarios autenticados acceden a la plataforma. La autenticacion se delega completamente a Supabase Auth (Google OAuth, Magic Link).
**Justificacion:** No reinventar autenticacion. Supabase Auth ya provee ambos metodos con RLS integrado.

## Integridad de Datos

**Regla:** Todas las listas controladas (TRL, CRL, BRL, escalabilidad, horizonte, estados) se validan con CHECK constraints a nivel de base de datos.
**Justificacion:** La DB es la ultima linea de defensa. Si el backend falla en validar, la constraint rechaza la escritura.

**Regla:** Toda FK declara ON DELETE explicito. Nunca se usa el default (NO ACTION).
**Justificacion:** Hace explicita la intencion: CASCADE para datos dependientes (mensajes sin sesion no sirven), RESTRICT para datos valiosos (no borrar un perfil con iniciativas), SET NULL para referencias opcionales.

**Regla:** Los timestamps usan TIMESTAMPTZ. Las fechas usan DATE.
**Justificacion:** La plataforma opera en Chile (UTC-4/UTC-3). TIMESTAMPTZ evita bugs de zona horaria.

## Analista de Oportunidad

**Regla:** El Analista recibe exactamente 6 campos de entrada: Titulo, Propuesta de valor, Segmento, Necesidad/friccion, Categoria de solucion, Beneficio.
**Justificacion:** La maquina de estados A-L del prompt v2 espera ese formato. Campos adicionales o faltantes requieren nueva version del prompt.

**Regla:** Un calculo TAM/SAM/SOM aplica a UNA sola geografia. Si el usuario quiere multiples geografias, se ejecutan calculos separados.
**Justificacion:** Evita promedios enganosos entre mercados con dinamicas distintas.

**Regla:** Todo output del Analista etiqueta cada numero como DATO, SUPUESTO o DERIVADO.
**Justificacion:** Transparencia y auditabilidad. El comite necesita saber que es evidencia y que es estimacion.
