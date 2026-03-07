import { Metadata } from 'next';
import { LawGraphContainer } from '@/components/graph/LawGraphContainer';

export const metadata: Metadata = {
    title: 'Grafo de Leyes | Tezca',
    description: 'Red interactiva de referencias cruzadas entre leyes mexicanas.',
};

export default function GrafoPage() {
    return (
        <div className="container mx-auto px-4 sm:px-6 py-8">
            <LawGraphContainer />
        </div>
    );
}
