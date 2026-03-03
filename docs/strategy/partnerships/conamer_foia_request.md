# Solicitud de Acceso a la Información: Catálogo Nacional de Regulaciones (CONAMER)

**Organismo:** Comisión Nacional de Mejora Regulatoria (CONAMER) / sucesor
**Vía:** Plataforma Nacional de Transparencia (PNT) — INAI
**Base legal:** Ley General de Transparencia y Acceso a la Información Pública, Art. 4, 6, 113

---

## Texto de la Solicitud

> Solicito, en ejercicio de mi derecho de acceso a la información pública conforme a la Ley General de Transparencia y Acceso a la Información Pública:
>
> **Los datos del Catálogo Nacional de Regulaciones, Trámites y Servicios (CNARTyS)**, ahora migrado al portal catalogonacional.gob.mx, en formato electrónico descargable.
>
> Específicamente solicito:
>
> 1. **Listado completo de instrumentos regulatorios** registrados en el catálogo nacional, incluyendo para cada uno:
>    - Nombre del instrumento
>    - Tipo (reglamento, lineamiento, acuerdo, manual, NOM, etc.)
>    - Dependencia u organismo emisor
>    - Fecha de publicación en DOF
>    - Estatus (vigente, abrogado, derogado)
>    - Número de identificación o clave de registro
>
> 2. **Formato preferido:** CSV, JSON, o XML. Alternativamente, cualquier formato electrónico estructurado que permita su procesamiento.
>
> 3. **Universo estimado:** El catálogo reportaba 113,373+ instrumentos regulatorios al cierre de 2025.
>
> **Justificación:** Esta información es de carácter público conforme al principio de máxima publicidad (Art. 6 constitucional). Los datos solicitados no contienen información confidencial ni datos personales. El acceso público a la regulación vigente es fundamental para la certeza jurídica y la participación ciudadana en la mejora regulatoria.
>
> **Uso previsto:** Integración al portal tezca.mx, plataforma de código abierto (AGPL-3.0) que ofrece acceso gratuito al marco jurídico mexicano. Los datos serán atribuidos a CONAMER/catalogonacional.gob.mx como fuente.

---

## Datos del Solicitante

- **Nombre:** [Nombre del representante de Tezca]
- **Correo:** contacto@tezca.mx
- **Organización:** Tezca — Plataforma de Derecho Mexicano Abierto

## Notas de Seguimiento

- **Portal web bloqueado:** catalogonacional.gob.mx devuelve 403 a solicitudes HTTP automatizadas (WAF Cloudflare/similar)
- **Portal anterior:** cnartys.conamer.gob.mx — DNS muerto desde ~2025
- **Alternativa datos.gob.mx:** Verificar si CONAMER publica datasets en la plataforma de datos abiertos
- **Plazo legal:** 20 días hábiles para respuesta (Art. 132, LGTAIP)
- **Recurso de revisión:** Ante INAI si la respuesta es insatisfactoria (Art. 142, LGTAIP)

## Estrategia Complementaria

1. **PNT submission** → esperar respuesta 20 días hábiles
2. **datos.gob.mx** → buscar datasets publicados por CONAMER
3. **Contacto directo** → email a CONAMER solicitando API o bulk download
4. **Playwright scraper** → fallback técnico (apps/scraper/federal/conamer_playwright.py)
