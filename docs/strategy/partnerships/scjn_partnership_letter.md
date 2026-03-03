# Solicitud de Colaboración: Corpus Judicial SCJN

**A:** Coordinación de Compilación y Sistematización de Tesis, SCJN
**De:** Tezca (tezca.mx) — Plataforma de Derecho Mexicano Abierto
**Fecha:** Marzo 2026

---

## Resumen

Tezca es una plataforma de código abierto (AGPL-3.0) que ofrece acceso gratuito y en formato legible por máquina a más de 35,000 instrumentos legales mexicanos: leyes federales, estatales, municipales, NOMs, tratados internacionales y reglamentos.

Solicitamos acceso a los corpus de **jurisprudencia** y **tesis aisladas** de la SCJN para integrarlos a nuestra plataforma, ampliando el acceso público al marco jurídico mexicano.

## Datos Solicitados

| Corpus | Estimado | Épocas |
|--------|----------|--------|
| Jurisprudencia | ~60,000 registros | 10ª y 11ª época (prioritarias), históricas |
| Tesis aisladas | ~440,000 registros | 10ª y 11ª época (prioritarias), históricas |

### Campos necesarios por registro

- Registro (clave única)
- Época
- Instancia (Pleno, Salas, TCC)
- Materia (civil, penal, administrativa, laboral, constitucional)
- Tipo (jurisprudencia / tesis aislada)
- Rubro
- Texto completo
- Precedentes
- Votos particulares / concurrentes
- Ponente
- Fuente (Semanario Judicial, Gaceta)

### Formatos preferidos

1. **JSON bulk** (ideal) — un archivo por época o un dump completo
2. **CSV/TSV** — tabular con texto en columnas
3. **API bulk access** — endpoint de descarga masiva
4. **XML** — formato Akoma Ntoso o propio de SCJN

## Beneficio Mutuo

### Para la SCJN
- **Mayor difusión**: Tezca recibe 50,000+ visitantes mensuales interesados en legislación mexicana
- **Interoperabilidad**: Vinculación automática entre tesis y las leyes que interpretan (cross-references)
- **Accesibilidad**: Búsqueda de texto completo en español con normalización de acentos
- **Preservación**: Copia de respaldo abierta del corpus en infraestructura distribuida (Cloudflare R2)

### Para el público
- **Acceso unificado**: Un solo portal para legislación Y jurisprudencia
- **Búsqueda cruzada**: "¿Qué tesis interpretan el artículo 123 de la CPEUM?"
- **Formato abierto**: Datos descargables, citables, y reutilizables bajo licencia abierta
- **Trilingüe**: Interfaz en español, inglés y náhuatl clásico

## Compromiso de Tezca

1. **Atribución completa**: Cada registro mostrará "Fuente: SCJN — Semanario Judicial de la Federación"
2. **Sin modificación**: Los textos se presentan íntegros, sin edición ni interpretación
3. **Código abierto**: Todo el código es público bajo AGPL-3.0 en GitHub
4. **Actualización**: Mecanismo de sincronización periódica para nuevas tesis
5. **Sin monetización directa**: Los datos judiciales serán de acceso libre y gratuito

## Contacto

**Proyecto:** Tezca — tezca.mx
**Email:** contacto@tezca.mx
**GitHub:** github.com/tezca-mx/tezca
**Licencia:** AGPL-3.0

---

*Tezca cree que el acceso abierto al derecho mexicano fortalece el Estado de Derecho y la participación ciudadana informada.*
