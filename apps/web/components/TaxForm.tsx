"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { CheckCircle2, AlertCircle, Info } from "lucide-react";

export default function TaxForm() {
    const [incomeCash, setIncomeCash] = useState<number>(0);
    const [incomeGoods, setIncomeGoods] = useState<number>(0);
    const [result, setResult] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError("");
        setResult(null);

        try {
            const res = await fetch("http://localhost:8000/api/v1/calculate/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    period: "2024-01",
                    income_cash: incomeCash,
                    income_goods: incomeGoods,
                    is_resident: true,
                }),
            });

            if (!res.ok) {
                throw new Error("Calculation failed");
            }

            const data = await res.json();
            setResult(data);
        } catch (err) {
            setError("Error connecting to the tax engine.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <Card className="max-w-xl mx-auto shadow-lg">
            <CardHeader>
                <CardTitle>Calculadora de Impuestos 2024</CardTitle>
                <CardDescription>Régimen General (LISR Art. 96) - Mensual</CardDescription>
            </CardHeader>
            <CardContent>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="incomeCash">Ingreso Efectivo</Label>
                            <Input
                                id="incomeCash"
                                type="number"
                                placeholder="0.00"
                                value={incomeCash}
                                onChange={(e) => setIncomeCash(parseFloat(e.target.value) || 0)}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="incomeGoods">Ingreso en Bienes</Label>
                            <Input
                                id="incomeGoods"
                                type="number"
                                placeholder="0.00"
                                value={incomeGoods}
                                onChange={(e) => setIncomeGoods(parseFloat(e.target.value) || 0)}
                            />
                        </div>
                    </div>

                    <Button type="submit" className="w-full bg-indigo-600 hover:bg-indigo-700" disabled={loading}>
                        {loading ? "Calculando..." : "Calcular Impuestos"}
                    </Button>
                </form>

                {error && (
                    <Alert variant="destructive" className="mt-4">
                        <AlertCircle className="h-4 w-4" />
                        <AlertTitle>Error</AlertTitle>
                        <AlertDescription>{error}</AlertDescription>
                    </Alert>
                )}

                {result && (
                    <div className="mt-6 space-y-4 animate-in fade-in slide-in-from-bottom-2">

                        <div className="p-4 bg-gray-50 rounded-lg border border-gray-100 space-y-3">
                            <div className="flex items-center gap-2 mb-2 border-b pb-2">
                                <Info className="h-4 w-4 text-blue-600" />
                                <h3 className="font-semibold text-gray-800">Desglose del Cálculo</h3>
                            </div>

                            <div className="grid grid-cols-2 text-sm gap-y-1">
                                <span className="text-gray-500">Ingreso Gravable:</span>
                                <span className="text-right font-medium">${result.gross_income.toLocaleString('es-MX', { minimumFractionDigits: 2 })}</span>

                                <span className="text-gray-500">(-) Límite Inferior:</span>
                                <span className="text-right">${result.breakdown.lower_limit.toLocaleString('es-MX', { minimumFractionDigits: 2 })}</span>

                                <span className="text-gray-500">(=) Excedente:</span>
                                <span className="text-right">${(result.gross_income - result.breakdown.lower_limit).toLocaleString('es-MX', { minimumFractionDigits: 2 })}</span>

                                <span className="text-gray-500">(x) Tasa:</span>
                                <span className="text-right">{result.breakdown.rate}%</span>

                                <span className="text-gray-500">(+) Cuota Fija:</span>
                                <span className="text-right">${result.breakdown.fixed_fee.toLocaleString('es-MX', { minimumFractionDigits: 2 })}</span>
                            </div>
                        </div>

                        <div className="p-4 bg-green-50 rounded-lg border border-green-200 shadow-sm flex justify-between items-center">
                            <div>
                                <h3 className="font-bold text-green-900 text-lg">Total a Pagar</h3>
                                <p className="text-xs text-green-700">ISR Personas Físicas</p>
                            </div>
                            <div className="text-2xl font-extrabold text-green-800">
                                ${result.isr_obligation.toLocaleString('es-MX', { minimumFractionDigits: 2 })}
                            </div>
                        </div>

                    </div>
                )}
            </CardContent>
        </Card>
    );
}
