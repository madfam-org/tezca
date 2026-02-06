import type { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Términos y Condiciones | Leyes Como Código México',
    description: 'Términos y condiciones de uso del portal Leyes Como Código México. Naturaleza del servicio, alcances y limitaciones.',
};

export default function TerminosLayout({ children }: { children: React.ReactNode }) {
    return children;
}
