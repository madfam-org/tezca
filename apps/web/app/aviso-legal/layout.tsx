import type { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Aviso Legal | Leyes Como Código México',
    description: 'Aviso legal del portal Leyes Como Código México. Este sitio no es una publicación oficial del gobierno mexicano.',
};

export default function AvisoLegalLayout({ children }: { children: React.ReactNode }) {
    return children;
}
