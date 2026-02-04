'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';

interface ComparisonContextType {
    selectedLaws: string[];
    toggleLaw: (lawId: string) => void;
    clearSelection: () => void;
    isLawSelected: (lawId: string) => boolean;
}

const ComparisonContext = createContext<ComparisonContextType | undefined>(undefined);

export function ComparisonProvider({ children }: { children: React.ReactNode }) {
    const [selectedLaws, setSelectedLaws] = useState<string[]>([]);

    // Load from localStorage on mount
    useEffect(() => {
        const stored = localStorage.getItem('comparison_selected_laws');
        if (stored) {
            try {
                setSelectedLaws(JSON.parse(stored));
            } catch (e) {
                console.error("Failed to parse selected laws", e);
            }
        }
    }, []);

    // Save to localStorage on change
    useEffect(() => {
        localStorage.setItem('comparison_selected_laws', JSON.stringify(selectedLaws));
    }, [selectedLaws]);

    const toggleLaw = (lawId: string) => {
        setSelectedLaws(prev => {
            if (prev.includes(lawId)) {
                return prev.filter(id => id !== lawId);
            }
            if (prev.length >= 2) {
                // Remove the first one and add new one to keep max 2
                return [...prev.slice(1), lawId];
            }
            return [...prev, lawId];
        });
    };

    const clearSelection = () => {
        setSelectedLaws([]);
    };

    const isLawSelected = (lawId: string) => {
        return selectedLaws.includes(lawId);
    };

    return (
        <ComparisonContext.Provider value={{ selectedLaws, toggleLaw, clearSelection, isLawSelected }}>
            {children}
        </ComparisonContext.Provider>
    );
}

export function useComparison() {
    const context = useContext(ComparisonContext);
    if (context === undefined) {
        throw new Error('useComparison must be used within a ComparisonProvider');
    }
    return context;
}
