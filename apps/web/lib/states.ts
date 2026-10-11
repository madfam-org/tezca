/**
 * The 32 Mexican states: URL slugs (keys match the API's state slugs) and
 * display names with proper accents.
 *
 * Single source for the state pages (`app/estados/[state]`), their metadata
 * (`app/estados/[state]/layout.tsx`) and the sitemap (`app/sitemap.ts`), so a
 * state can't appear in one and be missing from another.
 */
export const STATE_DISPLAY_NAMES: Record<string, string> = {
    aguascalientes: 'Aguascalientes',
    baja_california: 'Baja California',
    baja_california_sur: 'Baja California Sur',
    campeche: 'Campeche',
    chiapas: 'Chiapas',
    chihuahua: 'Chihuahua',
    ciudad_de_mexico: 'Ciudad de México',
    coahuila: 'Coahuila',
    colima: 'Colima',
    durango: 'Durango',
    estado_de_mexico: 'Estado de México',
    guanajuato: 'Guanajuato',
    guerrero: 'Guerrero',
    hidalgo: 'Hidalgo',
    jalisco: 'Jalisco',
    michoacan: 'Michoacán',
    morelos: 'Morelos',
    nayarit: 'Nayarit',
    nuevo_leon: 'Nuevo León',
    oaxaca: 'Oaxaca',
    puebla: 'Puebla',
    queretaro: 'Querétaro',
    quintana_roo: 'Quintana Roo',
    san_luis_potosi: 'San Luis Potosí',
    sinaloa: 'Sinaloa',
    sonora: 'Sonora',
    tabasco: 'Tabasco',
    tamaulipas: 'Tamaulipas',
    tlaxcala: 'Tlaxcala',
    veracruz: 'Veracruz',
    yucatan: 'Yucatán',
    zacatecas: 'Zacatecas',
};

export const STATE_SLUGS: readonly string[] = Object.keys(STATE_DISPLAY_NAMES);

export function getStateDisplayName(slug: string): string {
    return STATE_DISPLAY_NAMES[slug]
        ?? slug.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

/** Unique, state-specific `<title>` and meta description for `/estados/<slug>`. */
export function getStateSeo(slug: string): { title: string; description: string } {
    const name = getStateDisplayName(slug);
    return {
        title: `Leyes de ${name} — Legislación estatal — Tezca`,
        description:
            `Consulta la legislación estatal de ${name} en Tezca: leyes, códigos y reglamentos ` +
            `del estado tomados de fuentes oficiales, con búsqueda de texto completo y referencias cruzadas.`,
    };
}
