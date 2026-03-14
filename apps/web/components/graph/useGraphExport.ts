import { useCallback } from 'react';
import type Sigma from 'sigma';

export function useGraphExport(getSigma: () => Sigma | null) {
    const exportPNG = useCallback(() => {
        const sigma = getSigma();
        if (!sigma) return;

        const canvases = sigma.getCanvases();
        // Sigma renders across multiple layered canvases; composite them
        const layers = Object.values(canvases) as HTMLCanvasElement[];
        if (layers.length === 0) return;

        const first = layers[0];
        const w = first.width;
        const h = first.height;

        const composite = document.createElement('canvas');
        composite.width = w;
        composite.height = h;
        const ctx = composite.getContext('2d');
        if (!ctx) return;

        // White background
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, w, h);

        // Draw each Sigma layer
        for (const layer of layers) {
            ctx.drawImage(layer, 0, 0);
        }

        const url = composite.toDataURL('image/png');
        const link = document.createElement('a');
        link.download = 'tezca-grafo.png';
        link.href = url;
        link.click();
    }, [getSigma]);

    return { exportPNG };
}
