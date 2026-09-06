# Reglas laborales estructuradas, catálogos del SAT y costos de regularización

Carriles **T-1b** y **T-1c** del programa «Cobertura laboral del HCM»
(`claudedocs/hcm-hardening/plan-cobertura-laboral-hcm-2026-09-05.md`, §7 puntos
2, 3 y 4). El punto 1 —los textos de los artículos con vigencia— es T-1a y se
documenta en [`README.md`](README.md).

**T-1c** cierra los cuatro `kind` que el catálogo de obligaciones del HCM
consulta y que T-1a/T-1b no publicaban: la vigencia de la opinión 32-D, el CFDI
de nómina, el umbral de las comisiones mixtas y la validación del programa JCF.
Sus filas viven en `apps/api/labor_seed_hcm.py` y su compuerta —la que fija que
**ningún** `kind` del catálogo del HCM quede sin respuesta ni sin motivo— en
`tests/api/test_labor_seed_hcm.py`.

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

## Cobertura: 46 reglas, 45 `published`, 1 hueco declarado

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
| **`nom035_umbral_personas`** | — | tres tramos: ≤15 · 16–50 · >50, con numerales por tramo | NOM-035-STPS-2018 numeral 4 | 2019-10-23 → **2026-09-05** | published (**superada**, ver T-1f) |
| **`nom035_umbral_personas`** | — | los mismos tres tramos **corregidos** + equivalencia NMX-R-025 | **NOM-035-STPS-2018 numeral 2** | desde 2026-09-06 | published |
| `nom037_aplicabilidad` | — | sin umbral de personas: basta una en teletrabajo | **NOM-037-STPS-2023 numeral 2** | desde 2023-12-05 | published |
| **`opinion_32d_vigencia_dias`** | — | `30` días naturales | **RMF 2026 regla 2.1.36** (no el CFF) | **2026-01-01 → 2026-12-31** | published |
| **`cfdi_nomina_por_periodo`** | — | objeto: `disparo = erogacion` | **LISR 99 fr. III** | desde 2014-01-01 | published |
| **`comisiones_mixtas_umbral_personas`** | — | `> 50` personas (obligatoria desde 51) | **LFT 153-E** (no el 132) | desde 2012-12-01 | published |
| **`jcf_validacion_periodicidad_dias`** | — | ciclo mensual, última semana del mes | Reglas de Operación JCF (DOF 31-12-2024, `codigo` 5746424) | desde 2024-12-31 | published |

> **T-1e.** El `article` de esta fila es la única cita en prosa del seed —«Reglas de Operación JCF, apartado V y obligaciones del Centro de Trabajo», 72 caracteres— porque las Reglas de Operación no se numeran por artículos. No cabía en el `varchar(32)` de la columna y por eso `publish_labor_rules --dry-run` abortaba en producción. Se ensanchó la columna a 200; la cita **no** se truncó. Ver «Validación previa y límites de campo» en `docs/labor/README.md`.
| `relacion_trabajo_elementos` | — | los **3 elementos** del art. 20 + la regla de los «mismos efectos» | **LFT 20 ¶1 y ¶3** | desde 1970-04-01 | published (**T-1f**) |
| `recaracterizacion_indicios` | — | los 7 indicios orientativos, **sin** los elementos de ley | LFT 20 (doctrina, no texto) | desde 1970-04-01 | **seed-unverified** |

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

## Siete lecturas primarias que corrigen el plan

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


### 5. La vigencia de la opinión 32-D **no** está en el CFF (T-1c)

El catálogo del HCM funda `opinion_32d_vigencia_dias` en **CFF 32-D**. Ese
artículo **no fija plazo alguno**: delega el procedimiento en «reglas de
carácter general», y sólo impone periodicidad propia (mensual) a las sociedades
anónimas que cotizan en bolsa. Los **treinta días naturales** están en la
**RMF 2026 regla 2.1.36**:

> «La opinión del cumplimiento de obligaciones fiscales […] que se emita en
> sentido positivo, tendrá una vigencia de treinta días naturales a partir de
> la fecha de emisión.»

La regla **2.1.37** que cita el brief es otra cosa: la aplicación en línea para
que quien ejerce recursos públicos consulte la opinión en contrataciones
mayores a $300,000.00. **Sólo la opinión positiva vence**; una negativa no
caduca, se corrige. Como la RMF es anual, la fila se cierra el **31-12-2026**:
preguntar por 2027 debe devolver «no hay regla», no la de 2026 extrapolada.

### 6. El CFDI de nómina **no** es «por periodo» (T-1c)

El `kind` se llama `cfdi_nomina_por_periodo`, pero **LISR 99 fr. III** ata el
comprobante a la **erogación**, no a un periodo de calendario:

> «Expedir y entregar comprobantes fiscales a las personas que reciban pagos
> por los conceptos a que se refiere este Capítulo, **en la fecha en que se
> realice la erogación correspondiente**».

El `kind` conserva el nombre porque el contrato C1 ya lo fijó y renombrarlo
rompería al consumidor sin mover una coma de la ley; el **valor** dice la
verdad (`disparo: "erogacion"`). La periodicidad de pago (`c_PeriodicidadPago`)
describe la nómina en el complemento, no es el plazo para timbrar.

### 7. Las comisiones mixtas son **más de 50**, y no las funda el art. 132 (T-1c)

El catálogo del HCM funda `comisiones_mixtas_umbral_personas` en **LFT 132**,
cuya fracción XXVIII obliga a «participar en la integración y funcionamiento de
las Comisiones que deban formarse» **sin fijar número alguno**. El umbral está
en **LFT 153-E**: «En las empresas que tengan más de 50 trabajadores se
constituirán Comisiones Mixtas de Capacitación, Adiestramiento y Productividad».
El segundo párrafo confirma el corte por el otro lado: «las micro y pequeñas
empresas, que son aquellas que cuentan con **hasta 50** trabajadores».

El umbral es **estricto**: con 50 personas no hay obligación; con 51 sí. Es el
mismo error de fundamento que la lectura 4 corrigió para el reglamento interior,
y se resuelve igual — se publica el artículo que sí dice el número, en vez de
inventar uno para que cuadre el renglón.

## T-1f · Los fundamentos que HP-1 y HP-0c piden, y qué resolvió cada uno

Este carril no publicó reglas nuevas de la nada: **verificó contra fuente
primaria lo que ya estaba, partió en dos una fila que mezclaba ley con
doctrina, y cerró tres de los cinco huecos de corpus que HP-0c declaró.** Los
otros dos no se cerraron porque no se pueden cerrar, y eso también se afirma
aquí con la lectura que lo demuestra.

### Lo que HP-1 (symbiosis-hcm #93) consulta

| `kind` | Artículo | Procedencia | Cómo se verificó |
|---|---|---|---|
| `capacitacion_inicial_meses_max` = `3` | **LFT 39-B ¶2** | `published` | El texto vigente dice «duración máxima de **tres meses**». Ya estaba publicado por T-1b; T-1f añade el cruce contra el texto del artículo, de modo que un dedazo en la cifra pone roja la prueba |
| `capacitacion_inicial_meses_max_direccion` = `6` | **LFT 39-B ¶2** | `published` | «hasta de **seis meses** sólo cuando se trate de trabajadores para puestos de dirección, gerenciales… o que requieran conocimientos profesionales especializados» |
| `relacion_trabajo_elementos` | **LFT 20 ¶1 y ¶3** | `published` (**nuevo**) | Los tres elementos que el art. 20 sí enuncia: trabajo personal, subordinación, salario. Más la regla del ¶3: la prestación y el contrato «producen los mismos efectos» |
| `recaracterizacion_indicios` | LFT 20 (doctrina) | `seed-unverified` | Los siete indicios **no están en la LFT**. Siguen sin verificar |

**Por qué se partió la fila en dos.** T-1b publicó una sola fila
`recaracterizacion_indicios` que era honesta —declaraba en su propio `value`
que los indicios no eran de ley— pero tenía un efecto que la honestidad no
arreglaba: al ser toda la fila `seed-unverified`, el consumidor fail-closed la
descartaba **entera**, y con ella los tres elementos que el art. 20 enuncia
palabra por palabra. HCM se quedaba sin poder afirmar la definición legal de
relación de trabajo, que es justo lo que necesita para levantar el aviso del
principio 4 del programa. Partida en dos, HCM lee la ley como `published` y ve
los indicios como lo que son. La prueba
`test_los_indicios_ya_no_arrastran_a_la_ley` impide que vuelvan a mezclarse.

### Los cinco huecos de corpus de HP-0c (`catalogo_huecos.py`, motivo `corpus`)

| Hueco | Estado tras T-1f | Ruta exacta que el HCM debe citar |
|---|---|---|
| `registro_stps_jcf` | **RESUELTO** — ya estaba, con otro nombre | `official_id` = **`jcf-reglas-2026`** (DOF **5777674**, 31-12-2025), ingresado por `manage.py ingest_jcf` desde `data/jcf/catalog.json`. HP-0c citó el DOF 5746424, que son las Reglas de **2025**, expresamente abrogadas por las de 2026 |
| `nom035` | **RESUELTO** | `GET /api/v1/laws/nom_NOM-035-STPS-2018/articles/2/vigente/?on=` — numeral 2 (campo de aplicación), leído íntegro del DOF 5541828 |
| `nom037_si_aplica` | **RESUELTO** | `GET /api/v1/laws/nom_NOM-037-STPS-2023/articles/2/vigente/?on=` — numeral 2, DOF 5691672. Más el `kind` `nom037_aplicabilidad` |
| `convenio_institucion` | **SIGUE HUECO** — y no por falta de ingesta | Ver abajo |
| `carta_aceptacion` | **SIGUE HUECO** — mismo motivo | Ver abajo |

### Por qué el motivo de HP-0c para las NOM dejó de aplicar

HP-0c escribió: «`LawArticle` no modela numerales (“5.3”, “7.1 inciso b”) sin
forzarlo, y T-1b decidió no forzarlo». Era exacto **cuando `article` medía 32
caracteres**. T-1e ensanchó esa columna a 200 por una razón distinta —la cita
en prosa de las Reglas de Operación JCF no cabía y reventaba `--dry-run` en
producción— y de paso dejó el camino abierto: un numeral cabe en 200
caracteres igual que «39-B». No hubo que forzar nada ni inventar un modelo de
«numeral»; hubo que darse cuenta de que la restricción ya no existía.

### Los dos huecos que no se cierran, con la lectura que lo demuestra

`convenio_institucion` y `carta_aceptacion` son los dos que un carril apurado
habría «resuelto» publicando una regla con un artículo plausible del
Reglamento de la Ley Reglamentaria del art. 5o. constitucional. **No hay tal
artículo.** Lectura primaria del texto vigente (LeyesBiblio,
`regley/Reg_LRArt5C_050418.pdf`, última reforma DOF 05-04-2018), contada sobre
el documento completo:

* **«carta de aceptación» aparece CERO veces.** Ni esa forma ni «aceptación» a
  secas.
* **«convenio» aparece 4 veces, y ninguna es la del hueco**: los convenios del
  Ejecutivo Federal sobre ejercicio profesional (art. 22 fr. IV), su registro
  (art. 33 fr. V), el convenio de honorarios entre profesionista y cliente
  (art. 45) y los convenios de coordinación con los estados (transitorio
  SEXTO). Ninguno es un convenio entre institución educativa y centro receptor.
* El brief de este carril apuntaba a los **arts. 52–60** para prácticas y
  servicio social. Es una atribución equivocada que conviene dejar por
  escrito: los arts. 52–57 son la **autorización de la práctica profesional
  del pasante** ante la Dirección General de Profesiones, y los arts. 58–60
  son las **Comisiones Técnicas Consultivas**. El servicio social vive en el
  **Capítulo VIII, arts. 85–93**, y el art. 85 lo deja «al cuidado y
  responsabilidad de las escuelas de enseñanza profesional, conforme a sus
  planes de estudios» — sin exigir instrumento federal alguno.

**Conclusión, que es la que el HCM necesita:** el motivo del hueco no es «a
Tezca le falta ingerir un documento». Es que **el documento no existe**: el
convenio y la carta los rige el convenio mismo y la normativa interna de cada
institución. HP-0c ya lo había intuido («lo rige el convenio mismo»); esta
lectura lo confirma con cifras. No hay carril río arriba que abrir, y la
etiqueta `corpus` es engañosa para estos dos: el estado correcto es el que
HP-0c usa para el reglamento interior, `sin_ventana` —o mejor, un motivo
`sin_ordenamiento_federal`—. **Contrato propuesto al carril HP-0c**, no
cambiado aquí en silencio.

Lo que sí se publica, y el HCM puede citar para el vínculo formativo, es el
**art. 52**: los seis requisitos para que la Dirección General de Profesiones
autorice la práctica profesional del pasante. Está en el corpus como
`GET /api/v1/laws/reg_lrart5c/articles/52/vigente/`.

### La corrección de la NOM-035 que este carril encontró de paso

Verificar el numeral destapó dos errores de transcripción en la fila que T-1b
publicó, ninguno detectable por una prueba de «existe la fila»:

1. **El campo de aplicación es el numeral 2, no el 4.** En la NOM-035 el
   numeral 4 son las *Definiciones*. Un consumidor que fuera a citar el
   fundamento habría citado el numeral equivocado.
2. **El tramo de hasta 15 personas exigía de más.** El inciso a) del numeral 2
   dice, palabra por palabra: «deberán cumplir con lo dispuesto por los
   numerales **5.1, 5.4, 5.5, 5.7, 8.1 y 8.2**». La fila publicada listaba
   «5.1, 5.2, 5.4-5.8, 7.1 inciso a), 8» — le pedía además el 5.2 y el 7.1, que
   la norma no le impone. HCM habría exigido evidencia que la norma no requiere
   **al centro de trabajo más pequeño, que es el que menos margen tiene**.

Se corrigió **append-only**: la fila de 2019 se conserva y se cierra el
2026-09-05; la corregida rige desde el 2026-09-06. La fecha es la de la
corrección y no la de la norma a propósito — adelantarla a 2019 reescribiría
lo que Tezca respondió entre 2019 y hoy. La fila nueva añade además el último
párrafo del numeral 2, que T-1b no había transcrito: la equivalencia por
certificado **NMX-R-025-SCFI-2015**, que da por cumplidos cuatro incisos.

## Huecos declarados: lo que no se publicó, y por qué

Ninguno se rellenó de memoria.

| Hueco | Por qué | Qué haría falta |
|---|---|---|
| **`recaracterizacion_indicios`** — la única fila `seed-unverified` | Los siete indicios son doctrina y jurisprudencia que este carril no pudo citar con registro verificable de la SCJN. **T-1f sacó de esta fila los tres elementos de ley**, que ahora viven en `relacion_trabajo_elementos` como `published` | Una tesis o jurisprudencia con **número de registro** del Semanario Judicial de la Federación. Mientras tanto, HCM puede **mostrarla al humano** que decide y ningún cálculo la usa (HP-9) |
| **`c_RegimenFiscal` 626 (RESICO)** | El `catCFDI.xls` que el SAT sirve en esa ruta es la **versión 2.0 de 2020** y no trae la clave: RESICO nació en 2022. La regla de retención del 1.25 % sí la cita por su clave, porque la sostiene la LISR 113-J sin necesidad del catálogo | Una lectura primaria del catálogo de CFDI 4.0 vigente. `test_el_hueco_del_626_esta_declarado_y_no_inventado` se pone roja el día que se publique, y obliga a actualizar este documento |
| **`actualizacion_factor`: la serie del INPC** | Se publica la **fórmula** del CFF 17-A, no un número. La serie mensual del INPC es de INEGI y no se leyó en este carril | Un consumidor que necesite el factor trae los dos INPC. Si HCM va a estimar costos de regularización sin traerlos, hace falta un carril que publique la serie |
| **`recargos_tasa_mensual` a partir de 2027** | La LIF es **anual**. La fila de 2026 se cierra el 31-12-2026 a propósito: sin LIF 2027 leída, el feed prefiere fallar en claro a arrastrar una tasa vencida | Leer el art. 11 de la LIF 2027 cuando se publique. Es trabajo recurrente cada noviembre, como el feed fiscal |
| ~~**NOM-035 y NOM-037 como texto**~~ — **CERRADO por T-1f** | Se cerró solo cuando T-1e ensanchó `article` de 32 a 200 caracteres para poder citar las Reglas de Operación JCF: con esa columna, un numeral (`2`, `7.1 inciso b`) cabe como cualquier artículo. El **numeral 2** (campo de aplicación) de la NOM-035 y de la NOM-037 se publica ya como `LawArticle`, leído íntegro del DOF | Nada para el campo de aplicación. Los numerales 5 y 7 (obligaciones del patrón, identificación de factores) siguen sin transcribirse: mismo camino, más volumen |
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
| `test_todo_kind_del_hcm_existe` (T-1c) | Que el catálogo de obligaciones del HCM consulte un `kind` que Tezca no publica **ni** declara como hueco con motivo. Fija los **14** `regla_ventana_kind` del catálogo; entra con `HUECOS_DECLARADOS` **vacío** | Sí: vaciar `REGLAS_HCM` la pone roja nombrando los cuatro `kind` que faltarían |
| `test_la_opinion_32d_no_se_atribuye_al_cff` · `test_las_comisiones_mixtas_no_se_atribuyen_al_132` (T-1c) | Que alguien «corrija» el fundamento de vuelta al artículo que el HCM cita y que no dice el número | — |
| `TestElHcmPuedeLeerlas` (T-1c) | Que la fila exista en el seed pero no llegue a la base ni se pueda consultar por vigencia (el camino comando → modelo → consulta) | — |
| `TestPublicacion` | Que el comando escriba sin `LOCAL_DB`, que no sea idempotente, que promueva solo un `seed-unverified`, o que escriba a medias con el catálogo ilegible | — |
| `desbordes_de_longitud` (T-1e) | Un valor del seed más largo que el `max_length` de su columna. Es la clase que reventó `--dry-run` en producción con `value too long for type character varying(32)` **con el CI en verde**: la suite corre sobre SQLite, que ignora el ancho de un `VARCHAR(n)`. La compuerta mide contra el modelo, así que no depende del backend | Sí: **estaba roja sobre `main`**, nombrando `fila 42 (kind=jcf_validacion_periodicidad_dias), campo article: 72 caracteres > max_length 32` |
| `TestDryRunNoEscribe` (T-1e) | Que `--dry-run` vuelva a implementarse como «escribe y deshaz». Hoy hace 98 consultas y **cero** `INSERT`/`UPDATE`/`DELETE`, y una fila inválida sale con `CommandError` —fila, campo y cifras— sin traceback | Sí: muta el seed en memoria con la fila que reventó en el pod |
| `TestCorreccionNom035` (T-1f) | Que alguien revierta el campo de aplicación al numeral 4 o vuelva a exigirle al tramo de ≤15 personas numerales que la NOM no le impone | Sí: **verificado en el carril** — devolver la lista vieja pone roja `test_el_tramo_de_hasta_15_pide_lo_que_la_norma_pide` con `At index 1 diff: '5.2' != '5.4'` |
| `test_los_indicios_ya_no_arrastran_a_la_ley` (T-1f) | Que los tres elementos del art. 20 vuelvan a meterse en la fila `seed-unverified`, dejando otra vez al consumidor fail-closed sin la definición legal | Sí: la clave `elementos_de_ley` dentro del `value` de los indicios la pone roja |
| `test_es_el_unico_sin_verificar_del_feed` (T-1f) | Promover los indicios doctrinales a `published` «para que HCM los use» | Sí: **verificado en el carril** — cambiar la procedencia pone rojas dos pruebas |
| `test_los_dos_formativos_no_se_inventaron` (T-1f) | Publicar una regla `convenio_institucion` o `carta_aceptacion` con un artículo plausible del Reglamento del art. 5o, que **no dice eso** | Sí: añadir cualquiera de los dos `kind` al seed la pone roja |
| `test_el_valor_esta_en_el_texto_del_articulo` (T-1f) | Un dedazo en los topes del art. 39-B. Cruza la cifra contra el **texto** que Tezca sirve, no contra sí misma | — |

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

### T-1f: el orden importa más que antes

Con este carril, tres reglas apuntan a artículos que **sólo existen si
`publish_law_articles` corrió**: el numeral 2 de la NOM-035, el de la NOM-037 y
los seis artículos del Reglamento del art. 5o. Ejecutar en seco primero, y
siempre en este orden:

```bash
# 1. En seco, los dos, y leer las cifras antes de escribir nada
python manage.py publish_law_articles --dry-run     # 95 artículos (87 + 8 de T-1f)
python manage.py publish_labor_rules  --dry-run     # 101 filas: 46 reglas + 55 claves SAT

# 2. Escribir, artículos primero
LOCAL_DB=yes python manage.py publish_law_articles
LOCAL_DB=yes python manage.py publish_labor_rules
```

Los 8 artículos nuevos de T-1f son `reg_lrart5c` 51, 52, 85, 86, 87 y 88, más
el numeral 2 de `nom_NOM-035-STPS-2018` y de `nom_NOM-037-STPS-2023`.

**Lo que el operador debe esperar de la corrección de la NOM-035.** La fila de
2019 ya está `published` en producción y el comando **no la toca** —es la
regla append-only, y es la correcta—. Eso significa que su `effective_to`
nuevo (2026-09-05) **no se aplica solo**: en producción quedarán las dos filas
vigentes a la vez y `vigencias_traslapadas` lo vería si corriera contra la
base. La fila corregida gana igual en la consulta (el endpoint ordena por
`-effective_from`), así que **el consumidor recibe la respuesta correcta desde
el primer día**; lo que queda pendiente es cerrar la vieja. Es una escritura
de un solo campo sobre una fila publicada, que este carril deliberadamente no
automatiza: promover un `UPDATE` sobre filas `published` dentro del comando
abriría exactamente la puerta que el diseño append-only cierra. Corresponde al
operador, con la consulta explícita:

```sql
-- Cerrar la fila superada de nom035_umbral_personas (article='4').
-- Idempotente: si ya está cerrada, no cambia nada.
UPDATE api_laborrule
   SET effective_to = DATE '2026-09-05'
 WHERE kind = 'nom035_umbral_personas'
   AND article = '4'
   AND effective_from = DATE '2019-10-23'
   AND effective_to IS NULL;
-- Debe reportar UPDATE 1. Verificar después que quedan dos filas y sólo una
-- vigente hoy:
--   SELECT article, effective_from, effective_to FROM api_laborrule
--    WHERE kind = 'nom035_umbral_personas' ORDER BY effective_from;
```

## Mantenimiento recurrente

| Cuándo | Qué |
|---|---|
| Cada noviembre/diciembre | Leer el art. 11 de la LIF del año entrante y añadir la fila de `recargos_tasa_mensual`, cerrando la anterior el 31 de diciembre |
| Cada 1 de enero, hasta 2030 | Nada: los cinco escalones de la jornada y del tiempo extra ya están publicados con su vigencia |
| Cuando el SAT publique una edición nueva de sus catálogos | Reimportar y **mover `catalogo_version`**; la prueba lo exige |
| Cada diciembre, con la RMF del año entrante | Leer la regla 2.1.36 de la RMF nueva y añadir la fila de `opinion_32d_vigencia_dias`, cerrando la anterior el 31 de diciembre. La RMF es **anual**: sin ella, el feed calla en vez de arrastrar un plazo vencido |
| Cuando la STPS publique Reglas de Operación nuevas del JCF | Añadir la fila de `jcf_validacion_periodicidad_dias` con su `dof_codigo`. Las de 2024 siguen vigentes por su Transitorio TERCERO hasta que otras las sustituyan |
| Cuando el catálogo del HCM añada un `regla_ventana_kind` | Añadirlo a `KINDS_DEL_CATALOGO_HCM` en `tests/api/test_labor_seed_hcm.py`. La compuerta obliga entonces a publicarlo con lectura primaria o a declararlo hueco con motivo |
| Cuando se reforme un artículo citado | Añadir la fila nueva con `effective_from` de la reforma y cerrar la anterior el día anterior; nunca editar la existente |
