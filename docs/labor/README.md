# Feed laboral — contrato, cobertura y huecos

Tezca es el oráculo de la ley del trabajo del ecosistema. Este feed existe para
que **symbiosis-hcm no transcriba a mano ni un número ni un artículo**: ventanas
legales, topes, porcentajes de retención, catálogos del SAT y el texto vigente
de cada artículo se leen de aquí, por `official_id` y con vigencia.

Carril **T-1** del programa «Cobertura laboral del HCM»
(`claudedocs/hcm-hardening/plan-cobertura-laboral-hcm-2026-09-05.md`, §7).
Este documento cubre **T-1a: textos de artículos con vigencia**. Las reglas
estructuradas, los catálogos del SAT y los costos de regularización llegan en
T-1b y se documentan en [`reglas.md`](reglas.md).

## Por qué una tabla nueva y no Elasticsearch

El corpus ya sirve artículos en `GET /api/v1/laws/<id>/articles/`, desde el
índice de búsqueda. Ese índice guarda **una sola foto del texto, sin periodo de
vigencia**, y por eso no puede responder la única pregunta que le importa a un
cálculo de nómina o a una compuerta de cumplimiento:

> ¿Qué decía el artículo 59 de la LFT el 30 de abril de 2026?

La respuesta correcta es «cuarenta y ocho horas semanales», y la del índice
sería «cuarenta», porque el decreto del 1 de mayo de 2026 ya lo reformó. La
tabla `LawArticle` guarda el texto **con vigencia** para poder contestar bien;
Elasticsearch sigue siendo el índice de búsqueda y no se tocó.

## Contrato C1 — artículo vigente en una fecha

```
GET /api/v1/laws/{official_id}/articles/{article}/vigente/?on=YYYY-MM-DD
```

Requiere una API key (o JWT de Janua) con scope `read`, igual que el feed
fiscal. Sin `?on=` devuelve el texto vigente hoy.

> **Desviación declarada del contrato.** El brief pedía
> `GET /api/v1/laws/{official_id}/articles/{article}/?on=`. Esa ruta **ya
> existe** con otro significado en el corpus: `laws/<id>/articles/` sirve el
> listado desde Elasticsearch, y `laws/<id>/articles/<id>/references/` las
> referencias cruzadas. Montar el texto vigente en la ruta desnuda habría
> cambiado el significado de un endpoint público en uso. Se añadió el sufijo
> `/vigente/`, que además dice lo que hace. Todo lo demás del contrato —
> parámetro `?on=`, y las llaves `official_id`, `article`, `effective_from`,
> `dof_codigo`/`dof_date` y `source_url` de la respuesta — se respeta tal cual.

Respuesta (200):

| Campo | Qué es |
|---|---|
| `official_id`, `article` | La ley y el artículo, normalizados (`lft`, `39-A`) |
| `text` | Texto íntegro tal como lo publica la Cámara, con sus notas de reforma |
| `effective_from` / `effective_to` / `in_force` | El periodo en que rige (`effective_to` nulo = vigente) |
| `derogado` | El artículo dice «Se deroga». Se publica igual: un consumidor necesita saber que su base legal desapareció, no un 404 |
| `reformas_dof` | Todas las fechas DOF que la Cámara imprime bajo el artículo, de la más antigua a la más reciente |
| `dof_date` | La reforma que fija este texto (la última de `reformas_dof`) |
| `dof_codigo` | `codigo` de `nota_detalle` cuando la fila está atada a una publicación única |
| `edition` | La edición del texto vigente de la que se transcribió |
| `source`, `source_url` | De dónde se leyó |
| `provenance`, `is_verified` | `published` sólo con lectura primaria. **El consumidor sólo usa `published`.** |

Cuando no hay texto para esa fecha, **404 con explicación**, nunca el texto de
otra vigencia. HCM traduce ese 404 a `disclosed: pending` y muestra la
obligación con «ventana por publicar».

## De dónde se leyó cada texto

Del **`.doc`** del texto vigente que publica la Cámara de Diputados en
`https://www.diputados.gob.mx/LeyesBiblio/`, no del PDF de la misma página: el
PDF intercala espacios dentro de las palabras (`su bsiste`, `Artículo 39 -A`) y
repite el encabezado en cada página. Se cotejó que ambas ediciones declaran la
misma «última reforma».

`effective_from` es **la fecha de la reforma que tocó al artículo**, no la de la
última reforma de la ley entera. El artículo 20 de la LFT conserva su texto de
1970 aunque la ley se haya reformado el 14 de mayo de 2026; fecharlo en 2026
diría que su texto cambió ese día. Los 25 artículos sin nota de reforma se
fechan en la publicación original de su ley.

## Hallazgos que corrigen el plan

Tres lecturas primarias contradicen citas del plan del programa. Se registran
aquí porque los carriles HP-* dependen de ellas:

### 1. La jornada de 40 horas es gradual — hoy siguen siendo 48

El artículo 59 de la LFT, reformado por el decreto del **DOF 01-05-2026**
(`codigo` 5786537), dice «cuarenta horas semanales». Pero su **transitorio
segundo** escalona la reducción, y el **cuarto** hace lo propio con el tiempo
extraordinario:

| Año | Jornada semanal | Horas extra semanales |
|---|---|---|
| 2026 | 48 | 9 |
| 2027 | 46 | 9 |
| 2028 | 44 | 10 |
| 2029 | 42 | 11 |
| 2030 | 40 | 12 |

Un HCM que leyera sólo el texto del artículo calcularía hoy con 40 horas y se
equivocaría por ocho. Por eso la regla estructurada
`jornada_semanal_horas_max` se publica **con una vigencia por escalón** en
T-1b, y no como un número único.

El mismo decreto añadió la fracción **XXXIV al artículo 132**: registrar
electrónicamente la jornada de cada persona, con sus disposiciones generales en
vigor **desde el 1 de enero de 2027**, y una multa de 250 a 5000 UMA
(art. 994 fr. IV Bis) por incumplirla.

### 2. El REPSE no vive en la LFT 15-A a 15-D — esos artículos están derogados

La reforma del **DOF 23-04-2021** derogó los artículos 15-A, 15-B, 15-C y 15-D
de la LFT. La subcontratación quedó en los artículos **12** (prohibición de la
subcontratación de personal), **13** (permiso de servicios especializados),
**14** (contrato por escrito y responsabilidad solidaria) y **15** (registro
ante la STPS, vigencia de tres años). Los cuatro derogados se publican
igualmente, marcados `derogado: true`, para que un consumidor que todavía los
cite reciba la verdad en lugar de un 404.

Del lado fiscal, la no deducibilidad no está en la LFT sino en el **CFF 15-D**,
al que remite la fracción XXXIII del artículo 28 de la LISR.

### 3. La jornada/semana reducida no está en la LSS 62

El artículo 62 de la LSS trata de recaídas por riesgos de trabajo. La regla que
importa es la del **artículo 29 fracción III**: cuando la persona labora
jornadas reducidas, «en ningún caso se recibirán cuotas con base en un salario
inferior al mínimo». Es un **piso**, no un prorrateo libre.

Además, los artículos 422–425 (reglamento interior de trabajo) **no fijan
ningún umbral de personas**: el reglamento se forma por comisión mixta y se
deposita dentro de los ocho días siguientes a su firma, sin importar el tamaño
del centro. El «aviso si falta con > 20 personas» del plan no tiene base legal.

## Cobertura — artículo por artículo

87 artículos, todos `provenance='published'` con lectura primaria. Cero
`seed-unverified` en T-1a.

### `lft` — Ley Federal del Trabajo (Última reforma DOF 14-05-2026)

| Artículo | Vigente desde | Fechado por | Estado |
|---|---|---|---|
| 12 | 2021-04-23 | reforma DOF | vigente |
| 13 | 2021-04-23 | reforma DOF | vigente |
| 14 | 2021-04-23 | reforma DOF | vigente |
| 15 | 2021-04-23 | reforma DOF | vigente |
| 15-A | 2021-04-23 | reforma DOF | **derogado** |
| 15-B | 2021-04-23 | reforma DOF | **derogado** |
| 15-C | 2021-04-23 | reforma DOF | **derogado** |
| 15-D | 2021-04-23 | reforma DOF | **derogado** |
| 20 | 1970-04-01 | publicación original | vigente |
| 24 | 1970-04-01 | publicación original | vigente |
| 25 | 2019-05-01 | reforma DOF | vigente |
| 35 | 2012-11-30 | reforma DOF | vigente |
| 36 | 1970-04-01 | publicación original | vigente |
| 37 | 1970-04-01 | publicación original | vigente |
| 38 | 1970-04-01 | publicación original | vigente |
| 39 | 1970-04-01 | publicación original | vigente |
| 39-A | 2012-11-30 | reforma DOF | vigente |
| 39-B | 2012-11-30 | reforma DOF | vigente |
| 39-C | 2012-11-30 | reforma DOF | vigente |
| 39-D | 2012-11-30 | reforma DOF | vigente |
| 39-E | 2012-11-30 | reforma DOF | vigente |
| 39-F | 2012-11-30 | reforma DOF | vigente |
| 56 | 2026-01-15 | reforma DOF | vigente |
| 58 | 2026-05-01 | reforma DOF | vigente |
| 59 | 2026-05-01 | reforma DOF | vigente |
| 60 | 1970-04-01 | publicación original | vigente |
| 61 | 2026-05-01 | reforma DOF | vigente |
| 66 | 2026-05-01 | reforma DOF | vigente |
| 67 | 2026-05-01 | reforma DOF | vigente |
| 68 | 2026-05-01 | reforma DOF | vigente |
| 76 | 2022-12-27 | reforma DOF | vigente |
| 77 | 1970-04-01 | publicación original | vigente |
| 78 | 2022-12-27 | reforma DOF | vigente |
| 79 | 1970-04-01 | publicación original | vigente |
| 80 | 1970-04-01 | publicación original | vigente |
| 81 | 1970-04-01 | publicación original | vigente |
| 87 | 1975-12-31 | reforma DOF | vigente |
| 117 | 1970-04-01 | publicación original | vigente |
| 118 | 1970-04-01 | publicación original | vigente |
| 119 | 1970-04-01 | publicación original | vigente |
| 120 | 1970-04-01 | publicación original | vigente |
| 121 | 2019-05-01 | reforma DOF | vigente |
| 122 | 1976-07-02 | reforma DOF | vigente |
| 123 | 1970-04-01 | publicación original | vigente |
| 124 | 1970-04-01 | publicación original | vigente |
| 125 | 1970-04-01 | publicación original | vigente |
| 126 | 2012-04-09 | reforma DOF | vigente |
| 127 | 2024-12-24 | reforma DOF | vigente |
| 132 | 2026-05-01 | reforma DOF | vigente |
| 330-A | 2021-01-11 | reforma DOF | vigente |
| 330-B | 2021-01-11 | reforma DOF | vigente |
| 330-C | 2021-01-11 | reforma DOF | vigente |
| 330-D | 2021-01-11 | reforma DOF | vigente |
| 330-E | 2021-01-11 | reforma DOF | vigente |
| 330-F | 2021-01-11 | reforma DOF | vigente |
| 330-G | 2021-01-11 | reforma DOF | vigente |
| 330-H | 2021-01-11 | reforma DOF | vigente |
| 330-I | 2021-01-11 | reforma DOF | vigente |
| 330-J | 2021-01-11 | reforma DOF | vigente |
| 330-K | 2021-01-11 | reforma DOF | vigente |
| 422 | 2024-12-19 | reforma DOF | vigente |
| 423 | 2024-12-19 | reforma DOF | vigente |
| 424 | 2019-05-01 | reforma DOF | vigente |
| 425 | 1970-04-01 | publicación original | vigente |
| 804 | 2012-11-30 | reforma DOF | vigente |

### `lss` — Ley del Seguro Social (Última reforma DOF 15-01-2026)

| Artículo | Vigente desde | Fechado por | Estado |
|---|---|---|---|
| 5-A | 2024-06-07 | reforma DOF | vigente |
| 12 | 2019-07-02 | reforma DOF | vigente |
| 15 | 2024-01-24 | reforma DOF | vigente |
| 27 | 2009-01-16 | reforma DOF | vigente |
| 28 | 1995-12-21 | publicación original | vigente |
| 29 | 1995-12-21 | publicación original | vigente |
| 30 | 2001-12-20 | reforma DOF | vigente |
| 31 | 2001-12-20 | reforma DOF | vigente |
| 62 | 2001-12-20 | reforma DOF | vigente |

### `lifnvt` — Ley del INFONAVIT (Última reforma DOF 21-02-2025)

| Artículo | Vigente desde | Fechado por | Estado |
|---|---|---|---|
| 29 | 2025-02-21 | reforma DOF | vigente |

### `lisr` — Ley del ISR (Última reforma DOF 01-04-2024)

| Artículo | Vigente desde | Fechado por | Estado |
|---|---|---|---|
| 28 | 2021-11-12 | reforma DOF | vigente |
| 94 | 2021-11-12 | reforma DOF | vigente |
| 96 | 2013-12-11 | publicación original | vigente |
| 106 | 2021-11-12 | reforma DOF | vigente |
| 113-E | 2021-11-12 | reforma DOF | vigente |
| 113-J | 2021-11-12 | reforma DOF | vigente |

### `liva` — Ley del IVA (Última reforma DOF 12-11-2021)

| Artículo | Vigente desde | Fechado por | Estado |
|---|---|---|---|
| 1-A | 2021-04-23 | reforma DOF | vigente |

### `rliva` — Reglamento de la Ley del IVA (Última reforma DOF 25-09-2014)

| Artículo | Vigente desde | Fechado por | Estado |
|---|---|---|---|
| 3 | 2006-12-04 | publicación original | vigente |

### `cff` — Código Fiscal de la Federación (Última reforma DOF 09-04-2026)

| Artículo | Vigente desde | Fechado por | Estado |
|---|---|---|---|
| 15-D | 1981-12-31 | publicación original | vigente |
| 17-A | 1981-12-31 | publicación original | vigente |
| 21 | 2021-11-12 | reforma DOF | vigente |
| 32-D | 2021-11-12 | reforma DOF | vigente |
## Huecos declarados

Nada de esto se publicó, y nada debe rellenarse sin volver a leer el documento
primario:

| Hueco | Por qué | Dónde llega |
|---|---|---|
| **NOM-035-STPS-2018 y NOM-037-STPS-2023** como texto | Son normas, no leyes con articulado numerado: su unidad de cita es el numeral (`5.3`, `7.1 inciso b`), que `LawArticle` no modela hoy sin forzarlo. Sus **umbrales** sí se publican como reglas en T-1b, leídos del DOF | T-1b (reglas) / carril futuro (texto) |
| **Acuerdo REPSE (STPS, DOF 24-05-2021)** como texto | Mismo motivo: se numera con ordinales en letra («ARTÍCULO DÉCIMO TERCERO»). Su vigencia de tres años y la ventana de renovación se publican como reglas | T-1b (reglas) |
| **Lineamientos JCF vigentes** | No se localizó una publicación vigente en el DOF que los fije con fecha cierta; el programa cambió de reglas de operación varias veces. Publicar una versión sin poder citarla sería inventar | Pendiente, con ticket |
| **Reformas anteriores de cada artículo** | Se publica **una** vigencia por artículo: la actual. `reformas_dof` lista las fechas de las anteriores, pero sus textos no están: exigirían leer cada decreto histórico del DOF, uno por uno | Carril futuro, por demanda |
| **LISR con la edición 01-04-2024** | Es el texto vigente que publica la Cámara. Si hubo reformas fiscales posteriores no incorporadas todavía a esa edición, el feed las hereda | Se vuelve a leer cuando la Cámara publique una edición nueva |

## Comando de publicación (operador)

```bash
# 1. Ver qué escribiría, sin tocar la base
python manage.py publish_law_articles --dry-run

# 2. Escribir de verdad
LOCAL_DB=yes python manage.py publish_law_articles
```

Es **append-only e idempotente**: una fila ya `published` no se toca (la segunda
corrida reporta «Intactos: 87»). Una fila `seed-unverified` de la misma vigencia
se promueve en su lugar, igual que `publish_fiscal_values_2026`.

En el pod, `manage.py` vive en **`/app/manage.py`** — en la raíz de la imagen,
no bajo `apps/api/`. (Este documento decía `/app/apps/api/manage.py` hasta el
carril T-1d; esa ruta no existe.) Desde el 2026-09-06 el directorio de trabajo
ya no importa: ver la sección siguiente.

## Qué ocurre si el seed no está en la imagen

Los dos comandos leen su insumo de `data/labor/`, y los dos son **fail-closed**:
si el archivo no está, abortan **sin escribir nada**. Eso es lo correcto —
publicar medio catálogo del SAT haría que un timbrado rechazara claves buenas —
pero el mensaje de error es el mismo tanto si el archivo falta de verdad como si
sólo no se le encontró. Los dos modos se han visto:

**1. La semilla no viajó en la imagen.** El 2026-09-06, en el pod `tezca-api`
con la imagen de #234 y cwd `/app`:

```
python manage.py publish_law_articles --dry-run
  → No existe el seed: data/labor/articulos_vigentes.json
python manage.py publish_labor_rules  --dry-run
  → No se pudo leer el catálogo del SAT en data/labor/sat_catalogos.json:
    [Errno 2] ... No se escribió nada.
```

Los dos JSON estaban en git desde #233 y #234. Lo que faltaba era el archivo
**dentro de la imagen**: `.dockerignore` excluye `data/*` (el corpus vive en
Postgres + Elasticsearch, no en la imagen) y re-incluía a mano sólo tres
registros. `data/labor/*.json` no estaba en esa lista, así que `COPY . .` nunca
los subió. Corregido en T-1d re-incluyendo `data/labor/` con
`!data/labor/*.json`, y con un `COPY` explícito en `apps/indigo/Dockerfile` que
hace **fallar el build** si un builder vuelve a perder la re-inclusión — mejor
un build rojo que otra imagen que sólo se descubre rota cuando un operador entra
al pod a publicar.

**2. El comando se corrió desde otro directorio.** Hasta T-1d los valores por
omisión eran `Path("data")/labor/...`, relativos al **cwd**. Corrido desde
cualquier directorio que no fuera la raíz, el comando abortaba con el mismo «No
existe el seed» aunque el archivo estuviera perfectamente presente. Ahora
`DEFAULT_SEED` y `DEFAULT_CATALOGOS` se anclan a `settings.BASE_DIR`, así que
resuelven igual desde cualquier cwd. En el pod el valor no cambia (`BASE_DIR` es
`/app`); lo que cambia es que deja de depender de dónde estés parado.

Aguas abajo el costo no es un error visible: es un **feed laboral vacío**.
symbiosis-hcm es fail-closed contra Tezca, así que traduce la ausencia a
`disclosed: pending` y no publica ni una obligación — se ve como «todavía no
hay datos», no como una imagen mal armada.

### El chequeo que lo atrapa antes

`scripts/check-dockerignore-seeds.py` (job `dockerignore-seed-lint` en CI)
simula las reglas de `.dockerignore` —con la precedencia real de Docker: gana el
último patrón que casa— sobre la lista de semillas que los comandos de
publicación leen por omisión, y **falla nombrando el patrón culpable y su número
de línea** si alguna vuelve a quedar excluida. También exige que cada ruta exista
en el árbol: un `.dockerignore` correcto sobre un archivo borrado o renombrado
produce el mismo síntoma en el pod.

Sobre `main` el chequeo está en rojo con exactamente el diagnóstico del
incidente:

```
[FAIL] data/labor/articulos_vigentes.json: EXCLUIDA de la imagen por el
       patrón `data/*` (.dockerignore:32).
```

Al añadir una semilla nueva bajo `data/`, agrégala a `SEMILLAS_REQUERIDAS` en
ese script: es una línea, y es la diferencia entre que lo atrape CI y que lo
atrape un operador en producción.

> El chequeo **simula** `.dockerignore`, no construye la imagen: en el entorno
> del carril no había un demonio de Docker con el que ejercer un build real. La
> aserción de verdad —un `docker build` que falla si el archivo no está— vive en
> el `COPY` explícito del Dockerfile, que sí corre en cada build de
> `deploy-api`.

## Compuerta falsable

`tests/api/test_labor_articles.py::TestSeedCoherencia` corre **sobre el seed,
sin base de datos**, y entra con la lista de exenciones **vacía**: cero de las
87 filas incumplen. Cada aserción falla ante un error de transcripción concreto:

| Prueba | Qué atrapa |
|---|---|
| `test_todo_texto_empieza_por_su_propio_articulo` | El desalineamiento número ↔ texto. **Ya se puso en rojo durante el carril**: el extractor traía los 85 caracteres de la entrada del índice en vez del articulado del art. 15-A |
| `test_ningun_texto_esta_vacio_ni_truncado` | Textos de menos de 60 caracteres que son encabezados, no artículos |
| `test_las_vigencias_no_se_traslapan_por_articulo` | Dos textos vigentes el mismo día para el mismo artículo |
| `test_la_fecha_de_vigencia_es_la_de_su_ultima_reforma` | Fechar el artículo por la reforma de la ley entera |
| `test_ninguna_reforma_esta_en_el_futuro` | Un dedazo en una fecha DOF |
| `test_cubre_los_articulos_que_el_hcm_necesita` | Que la lista mínima del §7 del plan siga completa |
| `test_la_reforma_de_la_jornada_esta_en_el_texto` | Que el art. 59 traiga el texto del 01-05-2026 y no el anterior |
| `test_los_articulos_del_outsourcing_derogado_se_declaran` | Que LFT 15-A a 15-D salgan marcados `derogado` |

Las pruebas de API cubren el `?on=` **en la frontera de vigencia** (30 de abril
contra 1 de mayo de 2026), el 404 explicado, el 401/403 por scope y la
insensibilidad a mayúsculas del número de artículo.

### Empaquetado (T-1d)

`tests/api/test_labor_seed_packaging.py` cubre la otra mitad: que la semilla
esté **donde el comando la busca**. Sobre `main` está en rojo por dos razones
distintas, y conviene no confundirlas.

| Prueba | Qué atrapa |
|---|---|
| `test_las_rutas_resuelven_desde_otro_cwd` | Resuelve los valores por omisión en un subproceso cuyo cwd **no** es la raíz del repo. Con `Path("data")/...` no resuelven a nada: es el «No existe el seed» que no distingue un archivo ausente de un directorio equivocado |
| `test_default_seed_es_absoluto_y_existe` / `test_default_catalogos_es_absoluto_y_existe` | Que el valor por omisión siga anclado a `settings.BASE_DIR` y apunte a un archivo real |
| `test_la_semilla_no_esta_excluida` | Que `.dockerignore` no vuelva a dejar la semilla fuera de la imagen — nombra el patrón culpable y su línea |
| `test_el_dockerfile_copia_las_semillas` | Que siga en pie el `COPY` explícito que convierte una re-inclusión rota en un **build fallido** en vez de una imagen silenciosamente incompleta |
| `test_la_semilla_existe_en_el_arbol` | Que la semilla no se borre ni se renombre sin actualizar el comando |
