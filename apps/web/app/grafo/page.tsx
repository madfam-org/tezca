import { Metadata } from 'next';
import { LawGraphContainer } from '@/components/graph/LawGraphContainer';

export const metadata: Metadata = {
    title: 'Grafo de Leyes | Tezca',
    description: 'Red interactiva de referencias cruzadas entre leyes mexicanas.',
};

export default function GrafoPage() {
    return <LawGraphContainer mode="fullscreen" />;
}
