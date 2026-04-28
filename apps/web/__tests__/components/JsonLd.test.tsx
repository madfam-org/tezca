import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { JsonLd } from '@/components/JsonLd';

describe('JsonLd', () => {
    it('renders a script tag with type="application/ld+json"', () => {
        const { container } = render(<JsonLd data={{ '@context': 'https://schema.org' }} />);
        const script = container.querySelector('script[type="application/ld+json"]');
        expect(script).not.toBeNull();
    });

    it('serializes the data as JSON', () => {
        const data = { '@type': 'Organization', name: 'Tezca' };
        const { container } = render(<JsonLd data={data} />);
        const script = container.querySelector('script');
        expect(script?.innerHTML).toBe(JSON.stringify(data));
    });

    it('handles complex nested structures', () => {
        const data = {
            '@context': 'https://schema.org',
            '@type': 'BreadcrumbList',
            itemListElement: [
                { '@type': 'ListItem', position: 1, name: 'Home' },
                { '@type': 'ListItem', position: 2, name: 'Laws' },
            ],
        };
        const { container } = render(<JsonLd data={data} />);
        const parsed = JSON.parse(container.querySelector('script')!.innerHTML);
        expect(parsed.itemListElement).toHaveLength(2);
    });

    it('handles empty object', () => {
        const { container } = render(<JsonLd data={{}} />);
        const script = container.querySelector('script');
        expect(script?.innerHTML).toBe('{}');
    });
});
