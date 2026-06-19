# DBI — Plantilla y Contrato de Parseo

Especificacion del **Documento Base de Iniciativa (DBI)**: el formato exacto que emite Clara y que el backend parsea de forma deterministica a campos estructurados (paso 7 del boot sequence). Esta es la **fuente de verdad** del formato; si el prompt o la knowledge base cambian el formato, se actualiza este archivo, los fixtures y el parser, y se siembra una nueva version en `agent_configs`.

## Fuente y version

- **Formato**: tomado de `skills/Clara_KnowledgeBase_v5_9.md` > "Plantilla DBI final v5.9".
- **Prompt asociado**: `skills/Clara_Prompt_v5_4_GPT.md` (v5.4).

> ⚠️ **Desfase de versiones**: el prompt es v5.4 y la knowledge base v5.9. El prompt referencia "la plantilla del archivo de conocimiento", asi que la v5.9 manda en cuanto al formato. Al actualizar Clara, alinear ambas versiones y registrar la version efectiva en `agent_configs.version`.

> ✅ **Reconciliacion con BD**: los conflictos entre la plantilla v5.9 y `migrations/001_initial.sql` (TRL/CRL/BRL a escala 1-9, `Tipo` con `mixta`, `return_horizon` en meses) se resuelven en `migrations/002_dbi_v59_alignment.sql`, que ademas agrega `dbi_extra JSONB` para los campos nuevos. Ver "Reconciliacion con el esquema actual" al final.

## Plantilla literal (v5.9)

```text
══════════════════════════════════════════
DOCUMENTO BASE DE INICIATIVA
Título: [corto] | Fecha: [fecha] | Área: [área] | Postulante: [nombre]
Tipo: [Interna / Externa / Mixta]
══════════════════════════════════════════

RESUMEN EJECUTIVO: [problema + solución + impacto, 2-3 líneas]

A. PROBLEMA
• Problema: [texto]
• Por qué importa: [texto]
• Quién lo tiene: [texto]
• Cómo se resuelve hoy: [texto]

B. SOLUCIÓN
• Descripción: [texto]
• Diferenciador y grado de novedad: [similar / mejora relevante / nuevo] — [texto]
• Competencia / sustitutos: [no analizado / identificados / analizados y diferenciados] — [texto]
• Impacto económico: [valor o rango] — Fuente: [...] — Beneficiario: [Elecmetal/cliente/ambos] — Clasificación: [Bajo/Medio/Alto]
• Tamaño de mercado (si Externa): mercado total [+fuente] / alcanzable [+razón] / clientes cerrables ~3a [+supuesto] / ticket anual [+base] / supuestos a validar
• TRL: [nivel único 1-9, un solo número] — Evidencia: [hecho que lo sostiene + fuente/fecha]
• Escalabilidad: [Local / Interna / Externa]
• Mercado / repetibilidad: [un cliente / varios actuales / mineros similares / otros mercados / no claro]

C. CLIENTE
• Interno: [área/rol o No aplica]
• Externo: [quién o No aplica]
• Tipo de cliente objetivo: [opción]
• CRL: [nivel único 1-9, un solo número / No declarado] — Evidencia: [hecho que lo sostiene + fuente/fecha]

D. ALINEAMIENTO (asignado por innovación)
• Foco: [foco o por asignar]
• Horizonte: [H1 / H2 / H3 / por asignar]

E. EQUIPO Y RECURSOS
• Área del postulante: [texto]
• Equipo interno: [nombres/roles + compromiso o solo postulante]
• Equipo externo: [nombres/roles o No aplica]
• Patrocinador: [nombre / cargo / área] [o Sin patrocinador identificado / por validar]
• Apoyo recibido: [espacio/financiamiento/mentoría/info o Ninguno]
• Otros recursos necesarios: [claros y disponibles / parciales / no claros]
• Duración estimada: [meses / No estimado]

F. RIESGO E INCERTIDUMBRE
• Duda principal: [texto]
• Condición clave: «Esto funciona si [texto]»
• Captura de valor: [mecanismo o Por definir]
• Incertidumbre: cliente [alta/media/baja] / solución [...] / modelo [...]
• BRL: [nivel único 1-9, un solo número / No declarado] — Evidencia: [hecho que lo sostiene + fuente/fecha]

G. HITOS
• Técnicos/operativos: [hito + fecha + KPI / No definido]
• Económicos/financieros: [hito + fecha + KPI / No definido]
• Horizonte de retorno: [meses exactos]

EVIDENCIA ADJUNTA: [lista o ninguna]
BLOQUES PENDIENTES: [lista o ninguno]
══════════════════════════════════════════
```

## Contrato de parseo

### Estructura general
- El documento esta enmarcado por lineas de **borde**: una secuencia de `═` (U+2550, "box drawings double horizontal"). Aparece 3 veces: apertura, cierre del encabezado y cierre del documento. El parser las usa como anclas; no las interpreta como contenido.
- Tras la 1ra linea de borde viene el **encabezado**: la constante `DOCUMENTO BASE DE INICIATIVA`, la linea de metadatos y la linea `Tipo:`.
- Tras la 2da linea de borde viene el **cuerpo**: `RESUMEN EJECUTIVO`, los bloques `A`–`G` y los pies (`EVIDENCIA ADJUNTA`, `BLOQUES PENDIENTES`).

### Anclas y sintaxis (recomendaciones de regex)
| Elemento | Patron | Notas |
|----------|--------|-------|
| Borde | `^═{3,}$` | delimitador, se ignora como dato |
| Linea de metadatos | `Título:\s*(.+?)\s*\|\s*Fecha:\s*(.+?)\s*\|\s*Área:\s*(.+?)\s*\|\s*Postulante:\s*(.+)$` | 4 pares separados por `\|` |
| Tipo | `^Tipo:\s*(.+)$` | valor: `Interna` / `Externa` / `Mixta` |
| Resumen | `^RESUMEN EJECUTIVO:\s*(.+)$` | puede abarcar 1-3 lineas |
| Cabecera de bloque | `^([A-G])\.\s+(.+)$` | letra mayuscula + punto |
| Linea de campo | `^•\s*([^:]+):\s*(.*)$` | vinñeta `•` (U+2022) + `Label: value` |
| Pie | `^(EVIDENCIA ADJUNTA\|BLOQUES PENDIENTES):\s*(.*)$` | |

### Campos compuestos (sub-parseo del `value`)
- **Impacto económico**: separar por `—` (em-dash, U+2014). Sub-claves: `Fuente`, `Beneficiario`, `Clasificación`. El primer fragmento es el valor/rango.
- **Tamaño de mercado**: separar por `/`. Factores TAM/SAM/SOM: `mercado total`, `alcanzable`, `clientes cerrables ~3a`, `ticket anual`, `supuestos a validar`. Solo presente si `Tipo` incluye Externa.
- **TRL / CRL / BRL**: `(\d|No declarado)\s*—\s*Evidencia:\s*(.+)` → nivel entero 1-9 (o `No declarado`) + linea de evidencia.
- **Diferenciador y grado de novedad** / **Competencia / sustitutos**: `[opción] — [texto]`; la opcion es el grado, el texto la justificacion.
- **Incertidumbre**: `cliente [x] / solución [y] / modelo [z]` → 3 valores `alta|media|baja`.
- **Condición clave**: viene entre comillas angulares `«…»`; extraer el interior.

### Centinelas (valores que indican ausencia, no contenido)
`No especificado`, `No aplica`, `No definido`, `No declarado`, `No estimado`, `por asignar`, `Por definir`, `Sin patrocinador identificado`, `Ninguno`, `ninguna`, `solo postulante`.
- Mapear a `NULL` en la columna correspondiente (salvo que la semantica de negocio pida conservar el literal, p.ej. `dbi_raw_text`).
- `PENDIENTE` (nucleo A/B/C/E) y los items de `BLOQUES PENDIENTES` NO son ausencia: marcan trabajo a completar offline. El parser debe poblar `BLOQUES PENDIENTES` y, si hay `PENDIENTE` en un nucleo, dejar `status` en un estado que refleje incompletitud (a definir; ver reconciliacion).

### Reglas de normalizacion
- **TRL/CRL/BRL**: SIEMPRE un entero `1..9` (la v5.9 prohibe rangos/bandas como "5-6"). Si llega algo fuera de rango o un rango, es error de formato → rechazar el parseo, no adivinar.
- **Tipo**: normalizar a minuscula del dominio: `Interna→interna`, `Externa→externa`, `Mixta→mixta`.
- **Escalabilidad**: `Local` / `Interna` / `Externa` (tal cual).
- **Fecha**: parsear a `DATE` (ISO `YYYY-MM-DD`). Aceptar formatos comunes es-CL y normalizar.
- **Horizonte de retorno**: la v5.9 pide **meses exactos** (entero), no banda.
- El parseo es **todo-o-nada**: si falta una ancla estructural (bordes, cabeceras de bloque obligatorias A/B/C) o un nivel TRL/CRL/BRL es invalido, abortar y registrar el fallo; nunca persistir un DBI parcialmente interpretado.

## Mapeo campo DBI → columna BD

Leyenda de **Estado**: ✅ existe y calza · ⚠️ existe pero con conflicto de tipo/lista · ➕ nuevo (sin columna hoy).

| Campo DBI | Bloque | Columna `initiatives` | Estado | Lista controlada / tipo |
|-----------|--------|------------------------|--------|--------------------------|
| Título | enc. | `title` | ✅ | texto |
| Fecha | enc. | `postulation_date` | ✅ | DATE |
| Área | enc. | `area` | ✅ | texto |
| Postulante | enc. | `applicant_name` | ✅ | texto |
| Tipo | enc. | `initiative_type` | ⚠️ | plantilla: Interna/Externa/**Mixta**; BD: solo interna/externa |
| Resumen ejecutivo | — | — | ➕ | texto |
| Problema | A | `problem` | ✅ | texto |
| Por qué importa | A | — | ➕ | texto |
| Quién lo tiene | A | — | ➕ | texto |
| Cómo se resuelve hoy | A | — | ➕ | texto |
| Descripción | B | `solution` | ✅ | texto |
| Diferenciador y grado de novedad | B | — | ➕ | similar/mejora relevante/nuevo + texto |
| Competencia / sustitutos | B | — | ➕ | no analizado/identificados/analizados + texto |
| Impacto económico (valor) | B | `economic_impact` | ✅ | texto |
| Impacto económico — Fuente | B | — | ➕ | texto |
| Impacto económico — Beneficiario | B | — | ➕ | Elecmetal/cliente/ambos |
| Impacto económico — Clasificación | B | — | ➕ | Bajo/Medio/Alto |
| Tamaño de mercado (TAM/SAM/SOM) | B | — | ➕ | 5 factores (texto + supuestos) |
| TRL (nivel) | B | `trl` | ⚠️ | plantilla: entero **1-9**; BD: banda 'TRL 1-2/3-4/5-6/7-9' |
| TRL — Evidencia | B | — | ➕ | texto |
| Escalabilidad | B | `scalability` | ✅ | Local/Interna/Externa |
| Mercado / repetibilidad | B | — | ➕ | un cliente/varios/mineros similares/otros/no claro |
| Interno | C | `internal_client` | ✅ | texto |
| Externo | C | `external_client` | ✅ | texto |
| Tipo de cliente objetivo | C | — | ➕ | texto/opción |
| CRL (nivel) | C | `crl` | ⚠️ | plantilla: entero **1-9**; BD: 'CRL 1-4' |
| CRL — Evidencia | C | — | ➕ | texto |
| Foco | D | `strategic_alignment` | ✅ | asignado por innovacion |
| Horizonte (H1/H2/H3) | D | — | ➕ | H1/H2/H3/por asignar |
| Área del postulante | E | — | ➕ | texto (≠ `area` del encabezado) |
| Equipo interno | E | `internal_team` | ✅ | texto |
| Equipo externo | E | `external_team` | ✅ | texto |
| Patrocinador | E | `sponsor` | ✅ | texto |
| Apoyo recibido | E | — | ➕ | texto |
| Otros recursos necesarios | E | — | ➕ | claros/parciales/no claros |
| Duración estimada | E | `estimated_duration` | ✅ | texto/meses |
| Duda principal | F | `main_doubt` | ✅ | texto |
| Condición clave | F | `key_condition` | ✅ | texto |
| Captura de valor | F | `value_capture` | ⚠️ | plantilla: mecanismo libre; BD: enum ahorro/venta/competitividad/nuevo negocio/no claro |
| Incertidumbre (cliente/solución/modelo) | F | — | ➕ | 3× alta/media/baja |
| BRL (nivel) | F | `brl` | ⚠️ | plantilla: entero **1-9**; BD: 'BRL 1-4' |
| BRL — Evidencia | F | — | ➕ | texto |
| Hitos técnicos/operativos | G | `technical_milestones` | ✅ | texto |
| Hitos económicos/financieros | G | `financial_milestones` | ✅ | texto |
| Horizonte de retorno | G | `return_horizon` | ⚠️ | plantilla: meses (entero); BD: bandas 0-6/.../+24/no se |
| Evidencia adjunta | pie | — | ➕ | lista |
| Bloques pendientes | pie | — | ➕ | lista |
| (texto completo) | — | `dbi_raw_text` | ✅ | TEXT |

## Reconciliacion con el esquema actual

La plantilla v5.9 evoluciono respecto al esquema `001_initial.sql` (disenado en la era v5.4). Hay **4 conflictos** y **~17 campos nuevos**. **Resuelto en `migrations/002_dbi_v59_alignment.sql`** (enfoque hibrido recomendado).

### Conflictos (requieren migracion)
1. **TRL/CRL/BRL: escala 1-9 entera** vs. los CHECK actuales (`TRL 1-2/3-4/5-6/7-9`, `CRL 1-4`, `BRL 1-4`). Es el conflicto mas grave: el scorecard del Evaluador (ver KB v5.9 > "Mapeo DBI → Scorecard") depende de la escala 1-9.
2. **`initiative_type` admite `mixta`**; el CHECK solo permite `interna`/`externa`.
3. **`return_horizon` en meses (entero)** vs. el CHECK de bandas.
4. **`value_capture`**: la plantilla lo registra como mecanismo en texto libre (bloque F), no como enum.

### Campos nuevos sin columna
Resumen ejecutivo; sub-campos de A (por que importa, quien lo tiene, como se resuelve hoy); diferenciador/novedad; competencia; desglose de impacto (fuente/beneficiario/clasificacion); tamano de mercado TAM/SAM/SOM; mercado/repetibilidad; tipo de cliente objetivo; lineas de evidencia TRL/CRL/BRL; horizonte H1/H2/H3; apoyo recibido; otros recursos; incertidumbre (×3); evidencia adjunta; bloques pendientes.

### Migracion aplicada: `002_dbi_v59_alignment.sql`
Enfoque hibrido (recomendado):
- **Corrige los 4 conflictos**: `TRL/CRL/BRL` → `SMALLINT 1..9`; `initiative_type` admite `mixta`; `return_horizon` → `SMALLINT` (meses); `value_capture` pasa a texto libre (se elimina el enum).
- **Agrega `dbi_extra JSONB`** para los ~17 campos nuevos hasta que el esquema se estabilice (consistente con `evaluations.results`).
- Las conversiones de tipo **preservan datos** existentes (bandas → punto representativo) y el `Down` revierte al esquema de `001` (lossy: `mixta`→`externa`, niveles >4 en CRL/BRL → NULL).

> Donde guardar cada campo nuevo dentro de `dbi_extra` queda definido por las claves del golden fixture (estructura por bloque). Si un campo se vuelve consultable con frecuencia, promoverlo a columna dedicada en una migracion futura.

## Golden fixture

Ejemplo completo y su parseo esperado para anclar el parser y sus tests:

- Entrada (DBI crudo): `backend/tests/fixtures/dbi/example_internal.txt`
- Salida esperada (parseo): `backend/tests/fixtures/dbi/example_internal.expected.json`

El test del parser debe: (1) parsear el `.txt`, (2) comparar contra el `.json`, (3) verificar normalizacion de TRL/CRL/BRL a entero, centinelas → null, y deteccion de `BLOQUES PENDIENTES`.
