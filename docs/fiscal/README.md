# Carriles fiscales — índice y método

Los documentos de esta carpeta registran **qué se leyó del DOF, cuándo y con qué
cita**. El contrato del feed (endpoints, formas de respuesta, procedencia) vive
en [`../FISCAL_VALUES_FEED.md`](../FISCAL_VALUES_FEED.md); aquí está el rastro de
verificación que lo respalda.

| Documento | Qué cubre | Estado |
|---|---|---|
| [`2025-errata-isr-dof.md`](2025-errata-isr-dof.md) | Corrección de la tarifa ISR 2025: 6 cuotas fijas equivocadas, tabla de subsidio derogada, tarifa anual del Art. 152 ausente | Publicado en producción 2026-09-05 ~17:45 CDMX (4 filas nuevas) |
| [`2026-publicacion-dof.md`](2026-publicacion-dof.md) | Primera publicación verificada de 2026: UMA, salarios mínimos generales, tarifa mensual del Art. 96, subsidio al empleo | Publicado en producción 2026-09-05 ~17:45 CDMX (6 filas nuevas) |

Ambas corridas reportaron **«Intactas: 0»**: ninguna encontró una fila ya
`published` que debiera respetar.

## Lo que sigue pendiente

Ninguno de estos huecos se cerró con la publicación, y ninguno debe rellenarse
sin volver a leer el documento primario:

- **Tarifa anual del ISR (Art. 152) de 2026.** No publicada: la verificación
  sólo registró los renglones extremos, no los intermedios. La de 2025 sí está
  publicada, y **no puede copiarse** al otro año: los extremos difieren.
- **Los 61 salarios mínimos profesionales 2026.** El modelo `MinimumWage` los
  aloja sin migración, pero sus valores no están verificados.
- **Tarifas del Art. 106** (pagos provisionales), y las de periodos de 7, 10 y
  15 días.
- **`imss_rates` e `isn_rates`**, de cualquier año. Nunca han estado en el feed.
  Por eso `all_published` sigue en `false` para 2025 y 2026.
- **Escalares 2025** — UMA y salarios mínimos — siguen `seed-unverified`.
- **Cotejo contra el PDF facsimilar** de la edición matutina del DOF. Todo lo
  publicado se leyó del *texto* servido por los endpoints, no del facsímil; ese
  cotejo es lo que falta para un sello formal.

## Consumidores

`symbiosis-hcm` lee `isr_brackets`, `subsidio_rule` y la UMA por `?on=`, y ya
está en producción. El comando `sync_fiscal_basis`, del lado de HCM, está
disponible para que el operador refresque su base fiscal contra este feed; vive
en HCM, no en Tezca. Ningún cambio de este carril alteró el contrato que ese
cliente consume.

---

## Método: cómo leer el DOF

Esta sección es la lección transferible de los dos carriles. Vive aquí, y no en
la nota de un carril, porque el siguiente año la va a necesitar.

### Los endpoints que sirven, y el que no

`nota_detalle.php` **no sirve para fechas viejas**: para publicaciones de
diciembre de 2024 devuelve un cascarón vacío (3,325 bytes idénticos, sin el
texto). Sólo responde para meses recientes. Una cita que enlaza a ese cascarón
no es verificable por quien la lea después.

Los dos que sí funcionan:

```bash
# 1. Índice del día — se identifica la nota por su título y se extrae el codigo
curl "https://dof.gob.mx/index_111.php?year=2024&month=12&day=30"

# 2. Texto íntegro de la nota (.doc; las tablas vienen con tabuladores)
curl "https://dof.gob.mx/nota_to_doc.php?codnota=5746354" -o nota.doc
textutil -convert txt -encoding UTF-8 nota.doc
```

Los índices `index_111`/`113` son además poco fiables: a menudo devuelven la
misma edición para días distintos. **Conviene leer el DOF en la ventana de
publicación, no meses después.**

### La trampa del apartado C

En el Anexo 8 de la RMF, la tarifa anual del Art. 152 aparece **dos veces**: la
fracción I es la del ejercicio **anterior** y la fracción II la del ejercicio en
curso, en ese orden. En la RMF 2025 ambas resultaron numéricamente idénticas, así
que quien extraiga «la primera tabla anual que aparece» **acierta por accidente**
ese año y fallará el año en que difieran. Hay que citar la fracción, no la
posición.

### Nunca reutilizar la tarifa de un año para otro

El carril 2026 asumió que 2025 ≡ 2026; leer la RMF 2025 lo desmintió (los
importes de 2026 tienen cero ocurrencias en ese texto). Las tasas sí coinciden
entre años; los límites se actualizaron ≈13.2 %. Cada año se lee de su propio
instrumento.

### La compuerta de coherencia abarata la lectura, no la reemplaza

`apps/api/fiscal_coherence.py` verifica la identidad de toda tarifa progresiva
del repo, de cualquier año. Habría cazado 4 de los 6 errores de 2025 sin
consultar el DOF — pero no los dos cuyo desfase era constante (−1,000.00
exactos), porque la identidad es relativa y un error constante se propaga sin
romperla. Es un filtro barato antes de publicar, no un sustituto de leer el
documento.
