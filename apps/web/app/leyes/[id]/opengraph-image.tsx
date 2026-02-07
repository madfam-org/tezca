import { ImageResponse } from 'next/og';
import { API_BASE_URL } from '@/lib/config';

export const runtime = 'nodejs';
export const alt = 'Tezca — Ley';
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

const TIER_COLORS: Record<string, { bg: string; text: string; label: string }> = {
    federal: { bg: '#1e40af', text: '#ffffff', label: 'Federal' },
    state: { bg: '#047857', text: '#ffffff', label: 'Estatal' },
    municipal: { bg: '#7c3aed', text: '#ffffff', label: 'Municipal' },
};

export default async function Image({
    params,
}: {
    params: Promise<{ id: string }>;
}) {
    const { id } = await params;
    const lawId = decodeURIComponent(id);

    let lawName = lawId;
    let tier = 'federal';
    let category = '';
    let articleCount = 0;

    try {
        const res = await fetch(`${API_BASE_URL}/laws/${lawId}/`, {
            next: { revalidate: 3600 },
        });
        if (res.ok) {
            const data = await res.json();
            const law = data.law || data;
            lawName = law.name || lawId;
            tier = law.tier || 'federal';
            category = law.category || '';
            articleCount = data.total || law.article_count || 0;
        }
    } catch {
        // Fallback to defaults
    }

    const tierInfo = TIER_COLORS[tier] || TIER_COLORS.federal;

    return new ImageResponse(
        (
            <div
                style={{
                    width: '100%',
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    padding: '60px',
                    background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)',
                    color: '#ffffff',
                    fontFamily: 'system-ui, sans-serif',
                }}
            >
                {/* Top: Tezca branding */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div
                        style={{
                            width: '40px',
                            height: '40px',
                            borderRadius: '8px',
                            background: 'rgba(255,255,255,0.15)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '20px',
                        }}
                    >
                        {/* Book icon */}
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
                        </svg>
                    </div>
                    <span style={{ fontSize: '24px', fontWeight: 700, opacity: 0.9 }}>Tezca</span>
                    <span style={{ fontSize: '18px', opacity: 0.5, marginLeft: '4px' }}>El Espejo de la Ley</span>
                </div>

                {/* Center: Law name */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                    <h1
                        style={{
                            fontSize: lawName.length > 80 ? '32px' : lawName.length > 50 ? '38px' : '46px',
                            fontWeight: 700,
                            lineHeight: 1.2,
                            margin: 0,
                            letterSpacing: '-0.02em',
                            maxWidth: '1000px',
                        }}
                    >
                        {lawName.length > 120 ? lawName.slice(0, 117) + '...' : lawName}
                    </h1>

                    {/* Badges row */}
                    <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                        <div
                            style={{
                                display: 'flex',
                                padding: '6px 16px',
                                borderRadius: '999px',
                                background: tierInfo.bg,
                                color: tierInfo.text,
                                fontSize: '16px',
                                fontWeight: 600,
                            }}
                        >
                            {tierInfo.label}
                        </div>
                        {category && (
                            <div
                                style={{
                                    display: 'flex',
                                    padding: '6px 16px',
                                    borderRadius: '999px',
                                    background: 'rgba(255,255,255,0.15)',
                                    color: '#e2e8f0',
                                    fontSize: '16px',
                                    fontWeight: 500,
                                }}
                            >
                                {category}
                            </div>
                        )}
                        {articleCount > 0 && (
                            <div
                                style={{
                                    display: 'flex',
                                    padding: '6px 16px',
                                    borderRadius: '999px',
                                    background: 'rgba(255,255,255,0.1)',
                                    color: '#94a3b8',
                                    fontSize: '16px',
                                }}
                            >
                                {articleCount.toLocaleString('es-MX')} artículos
                            </div>
                        )}
                    </div>
                </div>

                {/* Bottom: URL */}
                <div
                    style={{
                        fontSize: '18px',
                        opacity: 0.4,
                        letterSpacing: '0.02em',
                    }}
                >
                    tezca.mx/leyes/{lawId.length > 60 ? lawId.slice(0, 57) + '...' : lawId}
                </div>
            </div>
        ),
        { ...size },
    );
}
