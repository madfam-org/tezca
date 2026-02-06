import type { Metadata } from 'next';

export const metadata: Metadata = {
    title: 'Política de Privacidad | Leyes Como Código México',
    description: 'Política de privacidad del portal Leyes Como Código México. Información sobre recopilación de datos y derechos del usuario.',
};

export default function PrivacidadLayout({ children }: { children: React.ReactNode }) {
    return children;
}
