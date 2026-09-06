# Reglas laborales estructuradas, catálogos del SAT y costos de regularización

Carril **T-1b** del programa «Cobertura laboral del HCM»
(`claudedocs/hcm-hardening/plan-cobertura-laboral-hcm-2026-09-05.md`, §7 puntos
2, 3 y 4). El punto 1 —los textos de los artículos con vigencia— es T-1a y se
documenta en [`README.md`](README.md).

**La diferencia entre los dos carriles es la que separa leer de calcular.** T-1a
publica la prosa: «la duración máxima de la jornada ordinaria de trabajo será de
cuarenta horas semanales». T-1b publica el número con el que HCM calcula, y ese
número **hoy es 48**, porque el transitorio segundo del mismo decreto escalona la
reducción hasta 2030. Un consumidor que leyera sólo el artículo se equivocaría
por ocho horas cada semana de cada nómina.

## Contrato C1 — reglas estructuradas

```
GET /api/v1/labor/rules/?kind=&on=YYYY-MM-DD&payer_legal_form=&provider_regime=&service=
```

Requiere API key (o JWT de Janua) con scope `read`, igual que el feed fiscal.

| Campo | Qué es |
|---|---|
| `kind` | El nombre fijo de la regla (la lista completa, abajo) |
| `value` | Número, cadena, booleano, lista, tabla u objeto. La forma por `kind` se documenta en la tabla de cobertura |
| `unit` | Cómo leer el `value`: `dias_habiles`, `horas/semana`, `percent`, `MXN`, `tabla`, `formula`… |
| `effective_from` / `effective_to` | El periodo en que rige (`effective_to` nulo = vigente) |
| `official_id`, `article` | La ley y el artículo del que se leyó |
| `source`, `source_url`, `dof_codigo`, `dof_date` | La procedencia |
| `provenance` | `published` \| `seed-unverified`. **El consumidor sólo calcula con `published`.** |
| `payer_legal_form`, `provider_regime`, `service` | Las dimensiones, cuando la regla depende de ellas |

La respuesta trae además `count`, `all_published` (un vistazo: ¿puedo calcular
con todo esto?) y `disclaimer`.

### Filtrado por dimensiones: por qué `any` se incluye

`?payer_legal_form=persona_moral` devuelve las reglas de persona moral **y** las
marcadas `any`. Si el filtro fuera de igualdad estricta, un consumidor que
pregunta correctamente «soy persona moral» perdería la ventana del alta al IMSS,
que no distingue por pagador — un fallo silencioso. Lo mismo para
`provider_regime` y `service` con la cadena vacía.

### Sin fila para la fecha

La lista sale vacía (`count: 0`), no 404: preguntar por un `kind` que no existe
ese día es una respuesta legítima. HCM lo traduce a `disclosed: pending` y pinta
la obligación con «ventana por publicar». Un `kind` fuera del vocabulario sí es
400, porque es un error del llamador.

## Contrato C1 — catálogos del SAT

```
GET /api/v1/labor/catalogos/?catalog=&code=&on=YYYY-MM-DD
```

> **Desviación declarada del contrato.** El brief listaba `sat_catalogo` como un
> `kind` más de `/labor/rules/`. Un catálogo no es una regla: tiene clave,
> descripción, vigencia propia por clave y —en `c_RegimenFiscal`— banderas de a
> qué tipo de persona aplica. Meterlo en `LaborRule.value` habría obligado a
> serializar 55 filas dentro de un JSON y a que el consumidor las filtrara en
> memoria por fecha, justo lo que este feed existe para evitar. Viven en
> `SatCatalogEntry` con su propio endpoint. El `kind` `sat_catalogo` sigue
> declarado en el vocabulario por si el coordinador prefiere lo contrario; hoy
> no tiene filas. Si se pide, el cambio es una vista que reproyecte.

Campos: `catalog`, `code`, `label`, `effective_from`/`effective_to`,
`aplica_fisica`/`aplica_moral` (sólo `c_RegimenFiscal`), más la procedencia común.

## Cobertura: 39 reglas, 38 `published`, 1 hueco declarado

Los `kind` en **negrita** son los que el contrato C1 exige por nombre.

| `kind` | Dimensiones | Valor | Artículo | Vigencia | Procedencia |
|---|---|---|---|---|---|
| **`imss_alta_ventana_dias_habiles`** | — | `5` | LSS 15 fr. I | desde 2001-12-20 | published |
| **`contrato_escrito_desde_inicio`** | — | `true` | LFT 24 | desde 1970-04-01 | published |
| **`prueba_dias_max`** | — | `30` | LFT 39-A | desde 2012-11-30 | published |
| **`prueba_dias_max_direccion`** | — | `180` | LFT 39-A ¶2 | desde 2012-11-30 | published |
| **`capacitacion_inicial_meses_max`** | — | `3` | LFT 39-B ¶2 | desde 2012-11-30 | published |
| **`capacitacion_inicial_meses_max_direccion`** | — | `6` | LFT 39-B | desde 2012-11-30 | published |
| `jornada_semanal_horas_max` | — | `48` · `46` · `44` · `42` · `40` | LFT 59 + transitorio 2º | **cinco filas**, 2026 · 2027 · 2028 · 2029 · desde 2030 | published |
| `tiempo_extra_semanal_horas_max` | — | `9` · `9` · `10` · `11` · `12` | LFT 66 + transitorio 4º | **cinco filas**, mismos años | published |
| **`jornada_diurna_horas_max`** | — | `8` | LFT 61 | desde 2026-05-01 | published |
| **`jornada_nocturna_horas_max`** | — | `7` | LFT 61 | desde 2026-05-01 | published |
| **`jornada_mixta_horas_max`** | — | `7.5` | LFT 61 | desde 2026-05-01 | published |
| **`semana_reducida_prorrateo`** | — | objeto: piso del salario mínimo + divisores 7/15/30 | **LSS 29 fr. II y III** | desde 1997-07-01 | published |
| **`ptu_eventuales_dias_min`** | — | `60` | LFT 127 fr. VII | desde 1970-04-01 | published |
| **`ptu_fecha_limite_dias`** | — | `60` | LFT 122 | desde 1976-07-02 | published |
| **`aguinaldo_dias_min`** | — | `15` | LFT 87 | desde 1970-04-01 | published |
| **`aguinaldo_fecha_limite`** | — | `{mes:12, dia:20, criterio:"antes_de"}` | LFT 87 | desde 1970-04-01 | published |
| **`vacaciones_dias_por_anio`** | — | tabla 12·14·16·18·20 + «dos por cada cinco años» desde el sexto | LFT 76 (reforma 27-12-2022) | desde 2023-01-01 | published |
| **`prima_vacacional_pct_min`** | — | `25` | LFT 80 | desde 1970-04-01 | published |
| **`retencion_isr_honorarios_pct`** | `persona_moral` × `612` × `servicios_profesionales` | `10` | LISR 106 penúltimo ¶ | desde 2014-01-01 | published |
| **`retencion_isr_honorarios_pct`** | `persona_moral` × `626` | `1.25` | LISR 113-J | desde 2022-01-01 | published |
| **`retencion_isr_honorarios_pct`** | `persona_fisica` | `0` | LISR 106 | desde 2014-01-01 | published |
| **`retencion_iva_honorarios_fraccion`** | `persona_moral` × `servicios_profesionales` | `2/3` del trasladado | RLIVA 3 fr. I (obligación: LIVA 1-A fr. II a) | desde 2006-12-05 | published |
| **`retencion_iva_honorarios_fraccion`** | `persona_moral` × `autotransporte_terrestre_bienes` | `4 %` de la contraprestación | RLIVA 3 fr. II | desde 2006-12-05 | published |
| **`resico_tope_anual`** | — | `3500000` | LISR 113-E | desde 2022-01-01 | published |
| **`recargos_tasa_mensual`** | — | `2.07` mensual (+ parcialidades 1.42 · 1.63 · 1.97) | CFF 21 × LIF 2026 art. 11 | **2026-01-01 → 2026-12-31** | published |
| **`actualizacion_factor`** | — | la **fórmula** INPC/INPC con piso 1 | CFF 17-A | desde 1982-01-01 | published |
| **`repse_obligatorio_condiciones`** | — | texto estructurado: prohibición, permitido con registro, 4 condiciones | **LFT 12, 13, 14 y 15** | desde 2021-04-24 | published |
| `repse_vigencia_anios` | — | `3` años, renovación 3 meses antes | LFT 15 ¶2 + Acuerdo REPSE arts. 13º y 16º | desde 2021-05-25 | published |
| **`teletrabajo_umbral_pct`** | — | `40` | LFT 330-A ¶4 | desde 2021-01-12 | published |
| **`nom035_umbral_personas`** | — | tres tramos: ≤15 · 16–50 · >50, con numerales por tramo | NOM-035-STPS-2018 numeral 4 | desde 2019-10-23 | published |
| `recaracterizacion_indicios` | — | 3 elementos de ley + 7 indicios orientativos | LFT 20 ¶1 | desde 1970-04-01 | **seed-unverified** |

### Catálogos del SAT: 55 claves, las 55 `published`

| Catálogo | Claves | Archivo leído | Versión que el archivo declara | Vigencias |
|---|---|---|---|---|
| `c_RegimenFiscal` | 22 | `catCFDI.xls` | 2.0 (rev. 0, publicado 2020-05-25) | 2016-11-12 · 2020-06-01 (625) · 2024-01-01 (628, 629, 630); el 609 con baja el 2019-12-31 |
| `c_TipoRegimen` | 13 | `catNomina.xls` | 2.0 (rev. 1, publicado 2019-12-05) | 2017-01-01 · 2017-03-27 (12) · 2018-10-15 (13) |
| `c_TipoContrato` | 11 | `catNomina.xls` | 1.0 (rev. 0) | 2017-01-01 |
| `c_TipoJornada` | 9 | `catNomina.xls` | 1.0 (rev. A) | 2017-01-01 |

Las versiones se leyeron del encabezado de cada hoja con `xlrd` y están fijadas
por `test_cada_catalogo_declara_la_version_que_el_xls_imprime`: si alguien
reimporta de una edición nueva y olvida mover el campo, la prueba se pone roja.

## Cuatro lecturas primarias que corrigen el plan

Todas verificadas contra el documento oficial en este carril.

### 1. La jornada de 40 h es gradual: **hoy son 48**

El art. 59 reformado (DOF 01-05-2026, `codigo` 5786537) dice «cuarenta horas
semanales», pero su **transitorio segundo** escalona 48 (2026) · 46 (2027) ·
44 (2028) · 42 (2029) · 40 (2030), y el **cuarto** hace lo propio con el tiempo
extraordinario: 9 · 9 · 10 · 11 · 12. Por eso ambos `kind` se publican con **una
fila por escalón**, con `effective_to` cerrado en todas menos la de 2030.

El escalón de 2026 empieza el **1 de enero** y no el 1 de mayo (fecha de entrada
en vigor del decreto) porque el texto anterior del art. 59 también decía 48: la
serie no tiene hueco ni traslape, y `huecos_en_la_serie` lo comprueba.

El mismo decreto añadió la fracción **XXXIV al art. 132** (registro electrónico
de jornada; sus disposiciones generales entran en vigor el 01-01-2027, por el
transitorio quinto) y la multa del **art. 994 fr. IV Bis** (250 a 5 000 UMA).
Ninguna de las dos se publicó como regla en este carril: la primera depende de
disposiciones que la STPS aún no expide, y la segunda es materia sancionadora
que HCM no calcula.

### 2. El REPSE **no** vive en la LFT 15-A a 15-D

El plan cita «LFT 15-A a 15-D». El decreto del **DOF 23-04-2021 los derogó**; la
subcontratación quedó en los arts. **12, 13, 14 y 15** (prohibición, servicios
especializados, contrato por escrito, registro ante la STPS con vigencia de tres
años). La no deducibilidad está en el **CFF 15-D**, al que remite la LISR 28 fr.
XXXIII — no en la LFT. T-1a publica los cuatro artículos derogados con
`derogado: true` precisamente para que un consumidor que cite la base vieja
descubra que desapareció, en vez de recibir un 404 ambiguo.

### 3. La jornada reducida **no** está en la LSS 62

La LSS 62 trata **recaídas por riesgos de trabajo**. La regla de cotización con
jornada o semana reducida es el art. **29 fr. III**: si el salario se fija por
día trabajado por menos días de los de una semana, o la persona labora jornadas
reducidas, «en ningún caso se recibirán cuotas con base en un salario inferior
al mínimo». Es un **piso, no un prorrateo libre** — HP-2 debe leerlo así. La fr.
II del mismo artículo da los divisores 7 / 15 / 30 y el art. 28 el tope superior
de 25 veces el salario mínimo.

### 4. Los arts. 422–425 **no** fijan umbral de personas

El plan proponía «aviso si falta reglamento interior con > 20 personas
(confirmar)». Los arts. 422 a 425 de la LFT no condicionan el reglamento
interior de trabajo a ningún número de personas. **El umbral no tiene base legal
y no se publicó.** HP-6 debe pedir el reglamento a todo centro de trabajo, no
sólo a los que pasen de veinte.

## Huecos declarados: lo que no se publicó, y por qué

Ninguno se rellenó de memoria.

| Hueco | Por qué | Qué haría falta |
|---|---|---|
| **`recaracterizacion_indicios`** — la única fila `seed-unverified` | Los tres elementos (trabajo personal, subordinación, salario) **sí** son del art. 20 LFT. Los siete indicios son doctrina y jurisprudencia que este carril no pudo citar con registro verificable de la SCJN | Un dictamen o una tesis con registro. Mientras tanto, HCM puede **mostrarla al humano** que decide y ningún cálculo la usa (HP-9) |
| **`c_RegimenFiscal` 626 (RESICO)** | El `catCFDI.xls` que el SAT sirve en esa ruta es la **versión 2.0 de 2020** y no trae la clave: RESICO nació en 2022. La regla de retención del 1.25 % sí la cita por su clave, porque la sostiene la LISR 113-J sin necesidad del catálogo | Una lectura primaria del catálogo de CFDI 4.0 vigente. `test_el_hueco_del_626_esta_declarado_y_no_inventado` se pone roja el día que se publique, y obliga a actualizar este documento |
| **`actualizacion_factor`: la serie del INPC** | Se publica la **fórmula** del CFF 17-A, no un número. La serie mensual del INPC es de INEGI y no se leyó en este carril | Un consumidor que necesite el factor trae los dos INPC. Si HCM va a estimar costos de regularización sin traerlos, hace falta un carril que publique la serie |
| **`recargos_tasa_mensual` a partir de 2027** | La LIF es **anual**. La fila de 2026 se cierra el 31-12-2026 a propósito: sin LIF 2027 leída, el feed prefiere fallar en claro a arrastrar una tasa vencida | Leer el art. 11 de la LIF 2027 cuando se publique. Es trabajo recurrente cada noviembre, como el feed fiscal |
| **Lineamientos JCF** | No se localizó publicación vigente en el DOF que los fije con fecha cierta | Localizar el acuerdo o los lineamientos vigentes. HP-5 los necesita para el contador de dos oportunidades |
| **NOM-035 y NOM-037 como texto** | Se numeran por **numeral** (`5.3`, `7.1 inciso b`), no por artículo; `LawArticle` no lo modela sin forzarlo. Los **umbrales** de la NOM-035 sí se publican como regla, leídos del DOF (`codigo` 5541828) | Un modelo de «numeral» o aceptar `article` como cadena libre. Se decidió no forzarlo en este carril |
| **Acuerdo REPSE como texto** | Se numera con ordinales en letra («ARTÍCULO DÉCIMO TERCERO»). Su vigencia de tres años y la ventana de renovación **sí** se publican como regla | Lo mismo que arriba |
| **Umbral de personas para el reglamento interior** | **No existe en la ley.** Ver la lectura 4 | Nada: el plan se corrige, no el feed |
| **LFT 57** | El brief pide «56–61»; el 57 (modificación judicial de condiciones) no se publicó en T-1a | Una fila más en `articulos_vigentes.json`. No sostiene ninguna regla de T-1b |

## Compuertas

Todas con **lista de exenciones vacía**: ninguna fila del seed las incumple.

| Compuerta | Qué atrapa | Falsable |
|---|---|---|
| `vigencias_traslapadas` | Dos filas del mismo `kind` y dimensiones vigentes el mismo día — la consulta sería ambigua y el orden lo decidiría el ORM, no la ley | Sí: `test_un_escalon_sin_cerrar_levanta_traslape` abre el escalón de 2028 y la compuerta lo reporta |
| `huecos_en_la_serie` | Un día sin regla dentro de una serie cerrada. HCM diría «ventana por publicar» cuando la ley sí dice algo | Sí: `test_un_escalon_cerrado_antes_de_tiempo_levanta_hueco` cierra 2028 en junio y reporta el hueco 01-07 → 31-12 |
| `test_toda_fila_published_tiene_fuente_primaria` | Un `published` sin `source_url` ni `dof_codigo` — no se puede defender ante nadie | — |
| `test_toda_fila_explica_de_donde_sale_el_numero` | Una fila sin nota de lectura (< 40 caracteres): nadie podría revisarla sin rehacer el trabajo | — |
| `test_las_reglas_minimas_del_contrato_estan_publicadas` | Que falte cualquiera de los 24 `kind` que C1 exige por nombre | — |
| `test_recargos_son_la_tasa_de_la_lif_incrementada_en_cincuenta` | La identidad `2.07 == 1.38 × 1.5` **se verifica, no se transcribe**: copiar el 1.38 como tasa de mora la pone roja | — |
| `test_cada_catalogo_declara_la_version_que_el_xls_imprime` | Una reimportación que olvide mover la versión, dejando claves nuevas atribuidas a la edición vieja | Sí: verificado en el carril |
| `TestPublicacion` | Que el comando escriba sin `LOCAL_DB`, que no sea idempotente, que promueva solo un `seed-unverified`, o que escriba a medias con el catálogo ilegible | — |

## Pasos de operador

```bash
# 1. Ver qué escribiría, sin tocar la base (opción por omisión)
python manage.py publish_labor_rules --dry-run

# 2. Escribir
LOCAL_DB=yes python manage.py publish_labor_rules
```

Append-only e idempotente, con el mismo criterio que `publish_fiscal_values_2026`:
una fila ya `published` **no se toca nunca**; una `seed-unverified` de la misma
vigencia y dimensiones se promueve en su lugar. El comando **aborta sin escribir
nada** si el JSON de catálogos no se puede leer: medio catálogo del SAT haría
que un timbrado rechazara claves buenas.

En el pod, `manage.py` vive en `/app/apps/api/manage.py`.

T-1a debe publicarse antes (`publish_law_articles`), porque cada regla de aquí
apunta al artículo cuyo texto sirve aquel comando. No es una dependencia dura
—las tablas son independientes— pero un consumidor que siga `official_id` +
`article` desde una regla hasta su prosa encontraría un 404.

## Mantenimiento recurrente

| Cuándo | Qué |
|---|---|
| Cada noviembre/diciembre | Leer el art. 11 de la LIF del año entrante y añadir la fila de `recargos_tasa_mensual`, cerrando la anterior el 31 de diciembre |
| Cada 1 de enero, hasta 2030 | Nada: los cinco escalones de la jornada y del tiempo extra ya están publicados con su vigencia |
| Cuando el SAT publique una edición nueva de sus catálogos | Reimportar y **mover `catalogo_version`**; la prueba lo exige |
| Cuando se reforme un artículo citado | Añadir la fila nueva con `effective_from` de la reforma y cerrar la anterior el día anterior; nunca editar la existente |
