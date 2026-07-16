'use client';

import React, { createContext, useContext, useState, useEffect, useRef } from 'react';

interface ComparisonContextType {
    selectedLaws: string[];
    toggleLaw: (lawId: string) => void;
    clearSelection: () => void;
    isLawSelected: (lawId: string) => boolean;
}

const ComparisonContext = createContext<ComparisonContextType | undefined>(undefined);

function getInitialLaws(): string[] {
    if (typeof window === 'undefined') return [];
    if (typeof localStorage === 'undefined' || typeof localStorage.getItem !== 'function') return [];
    try {
        const stored = localStorage.getItem('comparison_selected_laws');
        return stored ? JSON.parse(stored) : [];
    } catch {
        return [];
    }
}

export function ComparisonProvider({ children }: { children: React.ReactNode }) {
    const [selectedLaws, setSelectedLaws] = useState<string[]>(getInitialLaws);
    const isInitialMount = useRef(true);

    // Save to localStorage on change (skip initial mount)
    useEffect(() => {
        if (isInitialMount.current) {
            isInitialMount.current = false;
            return;
        }
        try {
            if (typeof localStorage !== 'undefined' && typeof localStorage.setItem === 'function') {
                localStorage.setItem('comparison_selected_laws', JSON.stringify(selectedLaws));
            }
        } catch {
            // localStorage unavailable
        }
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
