# Publicación fiscal 2026 — verificada contra el DOF

**Fecha de verificación:** 2026-09-05
**Estado:** filas escritas con `provenance='published'`
**Fuente:** lectura directa del texto del DOF (`nota_detalle`), sin fuentes
secundarias. Insumo: `claudedocs/hcm-hardening/dof-2026-verificacion.md`.

Hasta ahora todos los valores 2026 del feed eran `seed-unverified`: cifras
conocidas, útiles como apoyo, pero sin una cita que las defendiera. Esta
publicación cierra ese hueco para la UMA, los salarios mínimos generales, la
tarifa mensual del ISR y el subsidio al empleo.

Regla de la casa (Aldo, 2026-09-05): **todo lo que en HCM dependa de
cumplimiento legal se lee de Tezca.** Este documento es el registro de qué
quedó publicado y con qué procedencia.

---

## Qué se publicó

Cada fila lleva `dof_codigo`, el identificador de `nota_detalle` del DOF, que
junto con la fecha resuelve a un documento único:

```
https://dof.gob.mx/nota_detalle.php?codigo=<codigo>&fecha=<dd/mm/aaaa>
```

| Valor | Cifra | Vigencia | DOF | `codigo` |
|---|---|---|---|---|
| UMA diaria 2026 | $117.31 | desde 2026-02-01 | 09/01/2026, INEGI | 5778072 |
| UMA mensual 2026 | $3,566.22 | desde 2026-02-01 | 09/01/2026, INEGI | 5778072 |
| UMA anual 2026 | $42,794.64 | desde 2026-02-01 | 09/01/2026, INEGI | 5778072 |
| Salario mínimo general (ZSMG) | $315.04/día | desde 2026-01-01 | 09/12/2025, CONASAMI | 5775534 |
| Salario mínimo ZLFN | $440.87/día | desde 2026-01-01 | 09/12/2025, CONASAMI | 5775534 |
| ISR tarifa mensual Art. 96 (11 tramos) | ver abajo | 2026-01-01 a 2026-12-31 | 28/12/2025, SHCP/SAT | 5777219 |
| Subsidio al empleo (enero) | $474.65/mes | 2026-01-01 a 2026-01-31 | 01/05/2024 mod. 31/12/2024 | 5746529 |
| Subsidio al empleo (desde febrero) | $492.14/mes | desde 2026-02-01 | 01/05/2024 mod. 31/12/2024 | 5746529 |

Ocho filas: 1 UMA, 2 salarios mínimos, 1 tabla ISR, 2 reglas de subsidio, más
el cierre de vigencia de la UMA 2025 y de los salarios mínimos 2025.

### UMA 2026

Publicada por el INEGI el 9 de enero de 2026 (firmada el día 8), **vigente a
partir del 1 de febrero** conforme a la LFVUMA. Enero de 2026 se rige todavía
por la UMA 2025 ($113.14 diarios), y el feed lo resuelve así:

```bash
curl -H "X-API-Key: tzk_..." "$TEZCA/api/v1/fiscal/uma/?on=2026-01-15"   # 113.14
curl -H "X-API-Key: tzk_..." "$TEZCA/api/v1/fiscal/uma/?on=2026-03-01"   # 117.31
```

El mensual y el anual son **los que publicó el INEGI**, no derivados de
multiplicar el diario. El seed anterior traía $3,566.28 y $42,795.36 —
derivados a mano— y esta publicación los corrige a $3,566.22 y $42,794.64.
Como esa fila nunca fue una aserción de cumplimiento (`seed-unverified` lo
dice explícitamente), corregirla al promoverla es el flujo de operador que ya
documenta `FISCAL_VALUES_FEED.md`, no una violación del append-only.

**El fin de vigencia queda en `NULL`.** El 31 de enero de 2027 se sigue de que
la UMA del año siguiente entre en vigor el 1 de febrero, pero **no está en el
texto del DOF**, y el feed no afirma lo que no leyó. `NULL` ya significa
«sigue vigente», que es exactamente lo que sabemos.

### Salarios mínimos 2026

Resolución del H. Consejo de Representantes de la CONASAMI, DOF 09/12/2025,
vigente desde el 1 de enero de 2026. El incremento publicado fue de **13.0 %**
para la ZSMG (MIR de $17.01 más 6.5 %) y de **5.0 %** para la ZLFN, sin MIR.

**Los 61 salarios mínimos profesionales NO se publicaron.** La resolución los
trae, pero el documento de verificación sólo registra que la tabla existe, no
sus valores. Inventarlos sería exactamente el fallo que este feed existe para
evitar. Queda pendiente (ver abajo).

### ISR 2026 — tarifa mensual del Art. 96

Anexo 8 de la RMF 2026, apartado B fracción V («durante 2026»), publicado en
el DOF del 28 de diciembre de 2025. La RMF 2026 misma es el `codigo` 5777217,
vigente del 01-01-2026 al 31-12-2026.

Los importes **coinciden con los de 2025**: el Art. 152 de la LISR sólo obliga
a actualizar la tarifa cuando la inflación acumulada rebasa 10 %. Pero el
**instrumento y la cita son nuevos**, y ésa es la razón de publicar una fila
2026 propia en lugar de dejar que un consumidor reutilice la de 2025: quien
defienda una retención de 2026 ante el SAT cita el Anexo 8 de la RMF 2026.

| Límite inferior | Límite superior | Cuota fija | % s/ excedente |
|---:|---:|---:|---:|
| 0.01 | 844.59 | 0.00 | 1.92 |
| 844.60 | 7,168.51 | 16.22 | 6.40 |
| 7,168.52 | 12,598.02 | 420.95 | 10.88 |
| 12,598.03 | 14,644.64 | 1,011.68 | 16.00 |
| 14,644.65 | 17,533.64 | 1,339.14 | 17.92 |
| 17,533.65 | 35,362.83 | 1,856.84 | 21.36 |
| 35,362.84 | 55,736.68 | 5,665.16 | 23.52 |
| 55,736.69 | 106,410.50 | 10,457.09 | 30.00 |
| 106,410.51 | 141,880.66 | 25,659.23 | 32.00 |
| 141,880.67 | 425,641.99 | 37,009.69 | 34.00 |
| 425,642.00 | en adelante | 133,488.54 | 35.00 |

### Subsidio al empleo 2026 — regla derivada, no tabla

**No hubo decreto nuevo para 2026**: se recorrieron los índices del DOF entre
el 15/12/2025 y el 28/02/2026 sin encontrarlo, así que sigue vigente el
«Decreto que otorga el subsidio para el empleo» del 01/05/2024, modificado el
31/12/2024.

Desde ese decreto el subsidio **dejó de ser una tabla de rangos**: es un monto
mensual fijo igual al **13.8 % de la UMA mensual**, para quien percibe un
ingreso base que no exceda **$10,171.00**. Para periodos menores a un mes:

```
(UMA mensual × 13.8 %) ÷ 30.4 × días
```

Como el monto se deriva de la UMA y la UMA cambia el 1 de febrero, 2026 tiene
**dos vigencias**, que el modelo append-only guarda como dos filas:

| Periodo | UMA mensual | Subsidio mensual |
|---|---:|---:|
| 2026-01-01 a 2026-01-31 | 3,439.46 (UMA 2025) | **474.65** |
| desde 2026-02-01 | 3,566.22 (UMA 2026) | **492.14** |

La sustitución del 14.39 % aplicó **sólo a enero de 2025** y no se arrastra.

Se publican bajo un `kind` nuevo, `subsidio_rule`, en vez de forzarlo a los
tramos de `subsidio_monthly`. Un consumidor que sólo sepa leer `subsidio`
(tramos) recibe `null` y falla en claro, en lugar de aplicar tramos derogados.
Las filas guardan la fórmula junto con el importe para que se pueda recalcular
en vez de confiar en un número opaco.

---

## Cambios de esquema

Aditivos, sin romper a ningún consumidor:

- **`dof_codigo`** (`CharField`, opcional, indexado) en `FiscalValueBase` y en
  `FiscalTable`. Es el `codigo` de `nota_detalle` — la misma disciplina de
  identidad que `apps.scraper` aplica a los documentos anclados del corpus.
  Se expone en cada respuesta del feed.
- **`FiscalTable.Kind.SUBSIDIO_RULE`** para el subsidio post-decreto.
- `GET /fiscal/tables/<year>/` acepta ahora **`?on=YYYY-MM-DD`** y devuelve dos
  campos nuevos: `subsidio_rule` e `isr_annual`, más `superseded_within_year`
  cuando un mismo `kind` tiene varias vigencias en el año. Sin `?on=` devuelve
  la vigencia más reciente del año, que antes era «la que quedara al final del
  diccionario» — un empate silencioso que ahora es explícito.

`symbiosis-hcm` (`apps/api/payroll/tezca_client.py`) lee `value`, `year`,
`effective_date`, `isr_brackets`, `imss_rates` e `isn_rates`. Ninguno cambió de
nombre, tipo ni forma: **el cliente no requiere cambios**.

---

## Lo que quedó pendiente por falta de fuente primaria

Ninguno de estos se completó a mano. Cada uno necesita otra lectura del
documento primario.

1. **Tarifa anual del ISR (Art. 152), 2026.** El Anexo 8 la trae, pero el
   documento de verificación sólo registró los extremos —0.01 a 10,135.11 al
   1.92 %, y 5,107,703.93 en adelante al 35 %—, no los once renglones. No se
   publicó ninguna fila `isr_annual` 2026: `?kind=isr_annual&year=2026` no
   devuelve nada, y el consumidor falla en claro.
2. **Los 61 salarios mínimos profesionales 2026.** El modelo `MinimumWage`
   tiene el campo `zone` deliberadamente abierto para alojarlos sin migración,
   pero sus valores no están en la verificación.
3. **Tarifas del Art. 106 (pagos provisionales).** El Anexo 8 las incluye; no
   se transcribieron.
4. **Cuotas IMSS (`imss_rates`) e ISN por entidad (`isn_rates`) 2026.** Nunca
   han estado en el feed, para ningún año. `/fiscal/tables/2026/` los devuelve
   como `null`, que es lo correcto: ausente, nunca sustituido.

Por eso `all_published` en `/fiscal/tables/2026/` **no** es `true`: lo que hay
está verificado, pero el año no está completo.

### Hallazgo colateral: la tabla ISR 2025 no cuadra consigo misma

Al transcribir la tarifa 2026 se corrió una comprobación aritmética sobre las
cuotas fijas: en una tarifa progresiva, la cuota fija de cada tramo debe ser el
impuesto acumulado hasta el tope del tramo anterior. **La tarifa 2026 cuadra en
los once tramos con un centavo de tolerancia.** La de 2025 —`seed-unverified`,
en `fiscal_seed_data.py`— **no**:

| Tramo hasta | Cuota fija esperada | En el archivo | Δ |
|---:|---:|---:|---:|
| 15,487.71 | 1,640.18 | 1,639.32 | 0.86 |
| 31,236.49 | 5,003.26 | **4,005.47** | **997.79** |
| 49,233.00 | 8,238.25 | 8,236.89 | 1.36 |
| 375,975.61 | 116,912.32 | 116,890.10 | 22.22 |

Los desvíos de centavos son redondeo; el de ~998 pesos parece un dedazo. La
fila está marcada `seed-unverified`, así que **nadie debería estar citándola**,
pero sí alimenta apoyo a la decisión hoy, y el mismo origen
(`symbiosis-hcm/packages/mx-payroll/mx_payroll/isr.py`) probablemente arrastra
el error.

**No se tocó en esta rama**: corregirla exige leer el Anexo 8 de la RMF 2025 en
el DOF, y este carril sólo verificó 2026. Queda levantado como trabajo aparte.
Lo que sí se agregó es la prueba de coherencia aritmética para 2026, que es la
que caza esta clase de error antes de que se publique.

---

## Despliegue (operador)

Nada de esto corre solo contra producción. La publicación es un despliegue del
operador, en este orden:

1. **Migración.** `python manage.py migrate api` — agrega `dof_codigo` y el
   `kind` nuevo. Es aditiva: columna opcional con `default=""`, sin backfill y
   sin bloqueo de tabla.
2. **Ensayo.** `python manage.py publish_fiscal_values_2026 --dry-run`.
   Reporta lo que escribiría sin tocar la base. En una base ya sembrada debe
   decir «promovidas» para la UMA 2026 y los salarios mínimos 2026, y «filas
   nuevas» para el ISR y las dos del subsidio.
3. **Escritura.** `LOCAL_DB=yes python manage.py publish_fiscal_values_2026`.
   El guard `LOCAL_DB=yes` es el que exige AGENTS.md para cualquier comando
   que mute la base. Es idempotente y **nunca toca una fila que ya esté
   `published`**: si un operador corrigió algo a mano, se respeta.
4. **Verificación en vivo** (con una API key con scope `read`):

   ```bash
   curl -H "X-API-Key: $KEY" "$TEZCA/api/v1/fiscal/uma/?on=2026-03-01"
   #   value 117.3100 · year 2026 · provenance published

   curl -H "X-API-Key: $KEY" "$TEZCA/api/v1/fiscal/uma/?on=2026-01-15"
   #   value 113.1400 · year 2025  (enero se rige por la UMA anterior)

   curl -H "X-API-Key: $KEY" "$TEZCA/api/v1/fiscal/uma/current/"
   #   117.3100 mientras estemos después del 2026-02-01

   curl -H "X-API-Key: $KEY" "$TEZCA/api/v1/fiscal/minimos/?on=2026-06-15"
   #   general 315.0400 · zlfn 440.8700 · ambos published

   curl -H "X-API-Key: $KEY" "$TEZCA/api/v1/fiscal/tables/2026/"
   #   isr_brackets con 11 tramos · dof_codigo 5777219 · provenance published
   #   subsidio null · subsidio_rule con monthly_amount 492.14
   ```

5. **Aviso a los consumidores.** `symbiosis-hcm` no requiere cambio de
   contrato, pero sí conviene avisar que la UMA 2026 y la tarifa ISR 2026 ya
   son citables (`is_verified: true`), porque hasta hoy cualquier gate sobre
   `provenance == "published"` las rechazaba.

### Reversión

Append-only: no hay «deshacer». Si una cifra resultara equivocada, el
procedimiento es cerrar la vigencia de la fila mala y escribir la buena con su
cita — nunca borrar. El admin en `/admin/` se niega a borrar una fila
`published` precisamente por eso.

---

## Cuándo vuelve a tocar

- **~9 de enero de 2027** — el INEGI publica la UMA 2027 (vigente desde el 1
  de febrero). Al escribirla hay que cerrar la vigencia de la de 2026, que hoy
  está abierta, y recalcular las dos filas del subsidio.
- **~diciembre de 2026** — CONASAMI publica los salarios mínimos 2027.
- **~28 de diciembre de 2026** — el SAT publica los anexos de la RMF 2027; el
  Anexo 8 trae la tarifa del ISR aunque los importes no cambien.
- **En cualquier momento** — un decreto nuevo de subsidio al empleo cambiaría
  el 13.8 % o el tope de $10,171.00.

Los índices `index_111`/`113` del DOF son poco fiables (a menudo devuelven la
misma edición); la verificación de 2026 se logró leyendo `nota_detalle`
secuenciales, y los endpoints sólo sirven meses recientes. Conviene leer el DOF
en la ventana de publicación, no meses después.
