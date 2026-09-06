# Errata ISR 2025 — corregida contra el DOF

**Fecha de verificación:** 2026-09-05
**Estado:** publicado en producción el 2026-09-05 ~17:45 CDMX — 4 filas nuevas,
0 promovidas, 0 retiradas por derogación, 0 intactas. Ver [«Handoff»](#handoff).
**Fuente:** lectura directa del texto del DOF, sin fuentes secundarias.
Insumo: `claudedocs/hcm-hardening/dof-2025-isr-verificacion.md` (labspace).

Este documento es el gemelo de `2026-publicacion-dof.md`, y existe por una
razón distinta: aquel **completaba** un año sin cifras verificadas; éste
**corrige** cifras que ya estaban sembradas y eran incorrectas.

---

## Origen

El carril 2026 agregó una prueba de coherencia aritmética de cuotas fijas y
dejó anotado, sin tocarlo, que la tarifa ISR 2025 **no cuadra consigo misma**.
Este carril fue a leer el Anexo 8 de la RMF 2025 en el DOF y confirmó el
diagnóstico, con más alcance del previsto:

| Qué | Veredicto |
|---|---|
| Tarifa mensual Art. 96 (11 tramos) | **6 cuotas fijas equivocadas** (tramos 6 a 11) |
| Subsidio al empleo | **tabla completa derogada** desde el decreto DOF 01-05-2024 |
| Tarifa anual Art. 152 | **ausente** — nunca se sembró |

Los once límites y las once tasas de la tarifa mensual **siempre fueron
correctos**. El error estaba sólo en las cuotas fijas, con un patrón de dígito
de millar perdido (−1,000.00 exactos en tres tramos) que apunta a transcripción
manual, no a un ejercicio fiscal distinto. El efecto es que la tarifa sembrada
**subestimaba el ISR retenido** en los tramos altos, hasta ≈$1,022 mensuales
por trabajador.

**El diseño fail-closed funcionó.** El seed nunca afirmó estar verificado
(`provenance='seed-unverified'`, `is_verified=False`) y su propia nota decía de
dónde venían los números. Por eso esto es un hallazgo y no un incidente. Lo que
falló es la fuente aguas arriba:
`symbiosis-hcm/packages/mx-payroll/mx_payroll/isr.py`.

---

## Qué quedó

Cuatro filas, todas `published`, todas con su `dof_codigo`.

| Valor | Vigencia | DOF | `codigo` |
|---|---|---|---|
| ISR tarifa mensual Art. 96 (11 tramos) | 2025-01-01 a 2025-12-31 | 30/12/2024, SHCP/SAT | 5746354 |
| ISR tarifa anual Art. 152 (11 tramos) | 2025-01-01 a 2025-12-31 | 30/12/2024, SHCP/SAT | 5746354 |
| Subsidio al empleo (enero) | 2025-01-01 a 2025-01-31 | 31/12/2024 | 5746529 |
| Subsidio al empleo (feb–dic) | 2025-02-01 a 2025-12-31 | 31/12/2024 | 5746529 |

Más una fila **retirada**: la tabla de subsidio por tramos, derogada.

### Las seis cuotas fijas corregidas

Anexo 8 de la RMF 2025, **apartado A fracción V** — «Tarifa aplicable durante
2025 para el cálculo de los pagos provisionales mensuales a que se refieren los
artículos 96 de la Ley del ISR y 175 de su Reglamento, así como la regla
3.12.2.»

| # | Límite inferior | Cuota fija DOF | Cuota fija que había | Δ |
|---:|---:|---:|---:|---:|
| 6 | 15,487.72 | **1,640.18** | 1,639.32 | −0.86 |
| 7 | 31,236.50 | **5,004.12** | 4,005.47 | −998.65 |
| 8 | 49,233.01 | **9,236.89** | 8,236.89 | −1,000.00 |
| 9 | 93,993.91 | **22,665.17** | 21,665.17 | −1,000.00 |
| 10 | 125,325.21 | **32,691.18** | 31,691.18 | −1,000.00 |
| 11 | 375,975.62 | **117,912.32** | 116,890.10 | −1,022.22 |

Los tramos 1 a 5 ya eran correctos (0.00, 14.32, 371.83, 893.63, 1,182.88).

### La tarifa anual del Art. 152

Anexo 8, **apartado C fracción II** — «Tarifa para el cálculo del impuesto
correspondiente al ejercicio de **2025** …». El seed nunca la tuvo, pese a que
el modelo define el `kind` `isr_annual` desde el principio.

| Límite inferior | Límite superior | Cuota fija | % s/ excedente |
|---:|---:|---:|---:|
| 0.01 | 8,952.49 | 0.00 | 1.92 |
| 8,952.50 | 75,984.55 | 171.88 | 6.40 |
| 75,984.56 | 133,536.07 | 4,461.94 | 10.88 |
| 133,536.08 | 155,229.80 | 10,723.55 | 16.00 |
| 155,229.81 | 185,852.57 | 14,194.54 | 17.92 |
| 185,852.58 | 374,837.88 | 19,682.13 | 21.36 |
| 374,837.89 | 590,795.99 | 60,049.40 | 23.52 |
| 590,796.00 | 1,127,926.84 | 110,842.74 | 30.00 |
| 1,127,926.85 | 1,503,902.46 | 271,981.99 | 32.00 |
| 1,503,902.47 | 4,511,707.37 | 392,294.17 | 34.00 |
| 4,511,707.38 | en adelante | 1,414,947.85 | 35.00 |

### El subsidio al empleo — regla derivada, no tabla

La tabla de once renglones que el seed traía (de $407.02 a $0.00, con límite
superior **$7,382.33**) está **derogada**. El «Decreto que otorga el subsidio
para el empleo» (DOF 01/05/2024), modificado el 31/12/2024, la sustituyó por
una cuota fija, y el considerando de esa modificación cita precisamente ese
límite de $7,382.33 como el defecto que vino a corregir. Es decir: el seed
sembraba literalmente la tabla que el legislador declaró obsoleta.

Texto verificado del decreto (`codigo` 5746529):

- **Artículo Segundo** — subsidio mensual = UMA mensual × **13.8 %**, para
  trabajadores cuyo ingreso base no exceda de **$10,171.00**.
- **Periodos menores a un mes** — (UMA mensual × 13.8 %) ÷ **30.4** × días.
- **TRANSITORIO PRIMERO** — en vigor el 1 de enero de 2025.
- **TRANSITORIO SEGUNDO** — para **enero de 2025** el porcentaje es **14.39 %**
  «en sustitución del porcentaje de 13.8 %», y el considerando precisa que se
  aplica sobre «la Unidad de Medida y Actualización **vigente en 2024**».

Ese transitorio da a 2025 **dos vigencias**, igual que a 2026 pero por otro
motivo: en 2026 sólo cambia la UMA, en 2025 cambian **la UMA y el porcentaje a
la vez**.

| Periodo | UMA mensual | % | Subsidio mensual |
|---|---:|---:|---:|
| 2025-01-01 a 2025-01-31 | 3,300.53 (UMA 2024) | 14.39 | **474.95** |
| 2025-02-01 a 2025-12-31 | 3,439.46 (UMA 2025) | 13.8 | **474.65** |

Que el subsidio quede casi plano entre enero y febrero **no es casualidad**: es
lo que el transitorio busca, y corrobora la lectura del empalme. Si alguien
asignara la UMA 2025 a enero, el importe saltaría a $494.94 y se rompería la
continuidad. Hay una prueba que fija ese invariante.

Se publican bajo el `kind` **`subsidio_rule` que ya introdujo el carril 2026**
— no se inventó un tipo nuevo. La única extensión fue volver `rate_of_uma` un
parámetro de `subsidio_rule_rows()` (por omisión 13.8 %, así que ningún llamador
de 2026 cambió), porque enero de 2025 necesita el 14.39 %. La forma de la fila
es idéntica entre años: un consumidor no distingue de cuál viene.

**La tabla derogada no se conserva «por compatibilidad».** Se retiró del seed y
el comando la borra de una base ya sembrada. Un consumidor que aplique tramos
derogados calcula mal y no se entera; uno que reciba `null` en `subsidio` falla
en claro, que es el comportamiento que este feed existe para producir. Se borra
en lugar de cerrarle la vigencia porque **nunca fue derecho vigente en 2025**:
no es historia que preservar sino una transcripción equivocada, y el
append-only protege la historia de los valores que *estuvieron en vigor*. Si un
operador la promovió a `published` a mano, el comando **no la toca** y lo dice
en pantalla: deshacer un acto deliberado de operador no le toca a un comando.

### Cómo resuelve `/fiscal/tables/2025/?on=`

El endpoint ya sabía manejar varias vigencias por `kind` — el carril 2026 cerró
ese hueco al publicar el subsidio con dos filas. 2025 reutiliza ese mecanismo
tal cual, sin cambios en `fiscal_views.py`:

```bash
curl -H "X-API-Key: $KEY" "$TEZCA/api/v1/fiscal/tables/2025/?on=2025-01-20"
#   subsidio_rule → monthly_amount 474.95 · uma_monthly 3300.53 · rate_of_uma 0.1439

curl -H "X-API-Key: $KEY" "$TEZCA/api/v1/fiscal/tables/2025/?on=2025-01-31"
#   474.95 — la frontera es inclusiva, el último día de vigencia es suyo

curl -H "X-API-Key: $KEY" "$TEZCA/api/v1/fiscal/tables/2025/?on=2025-02-01"
#   subsidio_rule → monthly_amount 474.65 · uma_monthly 3439.46 · rate_of_uma 0.138

curl -H "X-API-Key: $KEY" "$TEZCA/api/v1/fiscal/tables/2025/"
#   sin ?on= devuelve la vigencia MÁS RECIENTE (474.65) y lista la otra
#   en superseded_within_year.subsidio_rule (474.95)
```

`subsidio` (tramos) devuelve `null` en todos los casos, e `isr_annual` ya no.

---

## Cómo se probó

### La compuerta de coherencia, extendida a todo el repo

El carril 2026 dejó una prueba de coherencia aritmética que sólo miraba la
tarifa 2026. Ahora vive en `apps/api/fiscal_coherence.py` y cubre **toda tarifa
ISR sembrada o publicada** — mensual o anual, de cualquier año:

```
cuota_fija[n] == cuota_fija[n-1] + tasa[n-1] × (inferior[n] − inferior[n-1])
```

Escrita sobre los **límites inferiores** y no sobre el tope del tramo anterior,
para no depender de que disten exactamente un centavo. Tolerancia: 2 centavos
(el DOF redondea y la cadena acumula; la desviación real máxima observada es
0.012).

Las tarifas se descubren **por reflexión** sobre los módulos `apps.api.fiscal_*`,
así que un `fiscal_dof_2027` futuro queda cubierto el día que se cree, sin que
nadie recuerde volver al archivo de pruebas. Una prueba aparte verifica que la
reflexión sigue encontrando las tarifas conocidas, para que un renombre no
convierta la cobertura en un bucle vacío.

**En rojo sobre la base:** aplicada a la tarifa 2025 tal como estaba sembrada,
la compuerta señala los tramos **6, 7, 8 y 11**:

| Tramo | Desde | Declaraba | La identidad exige | Desvía |
|---:|---:|---:|---:|---:|
| 6 | 15,487.72 | 1,639.32 | 1,640.18 | 0.86 |
| 7 | 31,236.50 | 4,005.47 | 5,003.26 | 997.79 |
| 8 | 49,233.01 | 8,236.89 | 8,238.25 | 1.36 |
| 11 | 375,975.62 | 116,890.10 | 116,912.32 | 22.22 |

**En verde con la corrección:** las cuatro tarifas del repo (2025 mensual, 2025
anual, 2026 mensual y el piso del seed) pasan sin excepciones.

**El límite honesto, escrito como prueba.** La compuerta habría cazado **4 de
los 6** errores, no 6 de 6: los tramos 9 y 10 traían −1,000.00 exactos, el mismo
desfase que su predecesor, y la identidad es *relativa*, así que un error
constante se propaga sin romperla. Hay una prueba —
`test_dos_tramos_erroneos_SI_pasan_la_compuerta` — que fija ese límite para que
nadie confunda la compuerta con un sustituto de leer el DOF. La abarata; no la
reemplaza.

Nótese que el valor que la identidad exigía para el tramo 6 (**1,640.18**) es
exactamente el del DOF: ahí la compuerta sola bastaba para reconstruir la cifra
correcta.

### Pruebas «golden» corregidas

Dos pruebas fijaban los datos malos y se cambiaron, no se borraron:

1. **`test_subsidio_top_row_is_zero`** afirmaba que el último renglón de
   `SUBSIDIO_MONTHLY_2025` valía `0.00`. Era cierto — sobre una tabla
   **derogada**. Pasó verde durante un año mientras el seed servía tramos que
   ningún patrón puede aplicar. Se reemplazó por
   `test_the_repealed_subsidio_bracket_table_is_gone`, que afirma que la tabla
   ya no se siembra.
2. **`test_isr_brackets_are_contiguous`** y compañía seguían pasando con las
   cuotas equivocadas, porque ninguna miraba las cuotas fijas. Se les sumó
   `test_isr_fixed_fees_match_the_dof`, que impide que el piso del seed vuelva
   a divergir de la lectura citada.

### Compuertas locales

- `pytest tests/api/` → **1397 passed, 9 skipped** (185 de ellas fiscales)
- `black --check apps/ tests/ scripts/` → 453 unchanged
- `isort --check-only` → limpio
- `audit_file_sizes.py` → exit 0
- `audit_silent_excepts.py` → OK
- `manage.py makemigrations --check --dry-run` → No changes detected

**Sin migración**: se reutilizan `isr_annual` y `subsidio_rule`, que ya existen
en el modelo, y ninguna columna cambia.

---

## Receta: leer el DOF para fechas viejas

`nota_detalle.php` **no sirve** para publicaciones de diciembre de 2024:
devuelve un cascarón vacío (3,325 bytes idénticos, sin el texto). Sólo responde
para meses recientes. Los dos endpoints que sí funcionan:

```bash
# 1. Índice del día — se identifica la nota por su título y se extrae el codigo
curl "https://dof.gob.mx/index_111.php?year=2024&month=12&day=30"

# 2. Texto íntegro de la nota (.doc; las tablas vienen con tabuladores)
curl "https://dof.gob.mx/nota_to_doc.php?codnota=5746354" -o nota.doc
textutil -convert txt -encoding UTF-8 nota.doc
```

Por eso las URL de `fiscal_dof_2025.py` apuntan a `nota_to_doc.php`: una cita
que enlaza a un cascarón vacío no es verificable por quien la lea después. Hay
una prueba que lo fija.

**Trampa del apartado C.** La tarifa anual viene **dos veces**: la fracción I es
la del ejercicio **anterior** (2024) y la fracción II la del ejercicio en curso
(2025), en ese orden. En la RMF 2025 ambas son numéricamente idénticas, así que
quien extraiga «la primera tabla anual que aparece» acierta por accidente este
año y fallará el año en que difieran. Las cifras publicadas son de la **fracción
II**, y la cita lo dice.

---

## Límites

- La lectura es del **texto** servido por `nota_to_doc.php`, no del PDF
  facsimilar de la edición matutina (`abrirPDF.php?archivo=30122024-MAT.pdf`,
  26.8 MB). Para un sellado formal conviene que el operador coteje contra ese
  PDF.
- **No se verificaron** las tarifas de periodos de 7, 10 y 15 días, ni las del
  Art. 106, ni las mensuales individuales de 2025. Tezca no las siembra y este
  carril no las agregó: inventar alcance es la falla que este feed evita.
- **`imss_rates` e `isn_rates` 2025** siguen ausentes, como para todos los años.
  `all_published` para 2025 no es `true`.
- Este carril **no tocó escalares**: la UMA y los salarios mínimos 2025 quedan
  como estaban, es decir `seed-unverified`, y la publicación en producción no
  los cambió. Su verificación es otro trabajo.
- **No se corrigió `symbiosis-hcm`.** Ver abajo.

---

## Handoff

1. **`symbiosis-hcm/packages/mx-payroll/mx_payroll/isr.py` es el origen del
   error y, a diferencia de Tezca, probablemente calcula nómina en producción
   con estos números.** Prioridad más alta que este propio seed. Fuera del
   alcance de este repo.
2. **Operador — hecho en producción el 2026-09-05, ~17:45 CDMX.** Se corrió en
   el pod `tezca-api` con la imagen de #231, después del ensayo:

   ```
   LOCAL_DB=yes python manage.py publish_fiscal_values_2025
   Published: 4 filas nuevas, 0 promovidas, 0 retiradas por derogación… Intactas: 0
   ```

   Las cuatro filas de [«Qué quedó»](#qué-quedó) son, desde esa fecha, lo que
   sirve el feed en producción. «0 retiradas por derogación» dice que la base de
   producción **nunca tuvo sembrada** la tabla de subsidio por tramos derogada:
   no había nada que borrar, no que el borrado fallara. «Intactas: 0» dice que
   no había ninguna fila ya `published` que el comando debiera respetar.

   La receta sigue válida para otros entornos, en este orden:

   ```bash
   python manage.py publish_fiscal_values_2025 --dry-run
   LOCAL_DB=yes python manage.py publish_fiscal_values_2025
   ```

   No hay migración que correr. El comando es idempotente, **nunca toca una
   fila ya `published`**, y reporta cuántas filas creó, promovió y retiró.
3. **Cotejar contra el PDF facsimilar** — **sigue pendiente**. La publicación de
   arriba no lo incluye: la lectura fue del texto de `nota_to_doc.php`, no del
   facsímil de la edición matutina. Es el paso que falta para el sello formal.
4. **La afirmación «2025 ≡ 2026» quedó invalidada.** Los importes 2026
   (844.59, 7,168.51, 133,488.54, 425,641.99) tienen **cero ocurrencias** en el
   texto de la RMF 2025. Las tasas sí coinciden entre años; los límites se
   actualizaron ≈13.2 %. Los valores 2026 del carril anterior **no quedan
   invalidados** — se leyeron de su propio instrumento (`codigo` 5777219) — pero
   ninguna tabla debe reutilizarse para el otro año. Hay una prueba que lo fija.
5. **Pendiente de 2026 que este carril no resolvió**: la tarifa anual del Art.
   152 de 2026 sigue sin publicarse (el documento de verificación de aquel
   carril sólo registró sus extremos). Ahora que existe la de 2025, el contraste
   confirma que **no** puede copiarse: los extremos difieren.
