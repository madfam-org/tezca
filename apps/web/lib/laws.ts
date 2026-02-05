
export interface Law {
    id: string;
    name: string;
    fullName: string;
    articles: number;
    transitorios: number;
    grade: 'A' | 'B' | 'C';
    score: number;
    priority: 1 | 2;
    tier: string;
    file: string;
    versions?: LawVersion[];
}

export interface LawVersion {
    publication_date: string;
    valid_from: string;
    dof_url: string;
    xml_file: string;
}

const API_URL = process.env.API_URL || 'http://localhost:8000/api/v1';

// Fallback static data for when API is unavailable or for static generation if needed
const staticLaws: Law[] = [
    {
        id: 'amparo',
        name: 'Ley de Amparo',
        fullName: 'Ley de Amparo',
        articles: 285,
        transitorios: 8,
        grade: 'A',
        score: 99.0,
        priority: 1,
        tier: 'constitutional',
        file: 'mx-fed-amparo-v2.xml'
    }
];

export async function getLawById(id: string): Promise<Law | undefined> {
    try {
        const res = await fetch(`${API_URL}/laws/${id}/`, { next: { revalidate: 60 } });
        if (!res.ok) {
            if (res.status === 404) return undefined;
            // Fallback to static if API fails
            return staticLaws.find(l => l.id === id);
        }

        const data = await res.json();

        // Map API response to UI Law interface
        return {
            id: data.id,
            name: data.short_name || data.name,
            fullName: data.name,
            articles: data.articles || 0,
            transitorios: 0,
            grade: data.grade || 'A',
            score: data.score || 100,
            priority: 2, // Default
            tier: data.tier || 'general',
            file: data.versions?.[0]?.xml_file || '',
            versions: data.versions || []
        };
    } catch (e) {
        console.error("Failed to fetch law:", e);
        return staticLaws.find(l => l.id === id);
    }
}

export async function getAllLaws(): Promise<Law[]> {
    try {
        const res = await fetch(`${API_URL}/laws/`, { next: { revalidate: 60 } });
        if (!res.ok) return staticLaws;
        const data = await res.json();
        return data.map((d: Record<string, string>) => ({
            id: d.id,
            name: d.name,
            fullName: d.name,
            articles: 0,
            transitorios: 0,
            grade: 'A',
            score: 100,
            priority: 2,
            tier: 'general',
            file: ''
        }));
    } catch {
        return staticLaws;
    }
}

// Deprecated synchronous exports for compatibility
export const laws = staticLaws;
export function getTotalArticles(): number { return 0; }
export function getAverageQuality(): number { return 100; }
