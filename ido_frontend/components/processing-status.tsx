'use client';

import { ProcessingStep } from '@/hooks/use-zip-processor';
import { ScanResult } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Check, X, Loader2, Search, Package, AlertCircle, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ProcessingStatusProps {
    step: ProcessingStep;
    scanResult: ScanResult | null;
    error: string | null;
}

const STEPS = [
    { key: 'scanning', label: 'Scanning', icon: Search },
    { key: 'extracting', label: 'Extracting', icon: Package },
    { key: 'preprocessing', label: 'Processing', icon: Sparkles },
    { key: 'complete', label: 'Complete', icon: Check },
];

export function ProcessingStatus({ step, scanResult, error }: ProcessingStatusProps) {
    if (step === 'idle') return null;

    const currentIndex = STEPS.findIndex(s => s.key === step);

    return (
        <Card className="animate-in fade-in-50 slide-in-from-bottom-4">
            <CardHeader>
                <CardTitle className="text-lg">Processing Status</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
                {/* Progress steps */}
                <div className="flex items-center justify-between">
                    {STEPS.map((s, i) => {
                        const isActive = s.key === step;
                        const isComplete = currentIndex > i || step === 'complete';
                        const isError = step === 'error' && i === currentIndex;
                        const Icon = s.icon;

                        return (
                            <div key={s.key} className="flex flex-col items-center flex-1">
                                <div
                                    className={cn(
                                        'w-10 h-10 rounded-full flex items-center justify-center mb-2 transition-all',
                                        isError && 'bg-destructive/20 text-destructive',
                                        isComplete && 'bg-primary/20 text-primary',
                                        isActive && !isError && 'bg-primary/20 text-primary',
                                        !isActive && !isComplete && !isError && 'bg-muted text-muted-foreground'
                                    )}
                                >
                                    {isError ? (
                                        <X className="w-5 h-5" />
                                    ) : isComplete ? (
                                        <Check className="w-5 h-5" />
                                    ) : isActive ? (
                                        <Loader2 className="w-5 h-5 animate-spin" />
                                    ) : (
                                        <Icon className="w-5 h-5" />
                                    )}
                                </div>
                                <span className={cn(
                                    'text-xs text-center',
                                    isActive ? 'text-foreground font-medium' : 'text-muted-foreground'
                                )}>
                                    {s.label}
                                </span>
                            </div>
                        );
                    })}
                </div>

                {/* Error message */}
                {error && (
                    <Alert variant="destructive">
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription>{error}</AlertDescription>
                    </Alert>
                )}

                {/* Scan results */}
                {scanResult && (
                    <div className="space-y-3">
                        <h4 className="text-sm font-medium text-muted-foreground">Files Found in ZIP</h4>
                        <div className="space-y-2">
                            {Object.entries(scanResult.found_files).map(([filename, path]) => (
                                <div
                                    key={filename}
                                    className="flex items-center justify-between p-3 bg-muted/50 rounded-lg"
                                >
                                    <span className="text-sm font-medium">{filename}</span>
                                    {path ? (
                                        <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20">
                                            <Check className="w-3 h-3 mr-1" />
                                            Found
                                        </Badge>
                                    ) : (
                                        <Badge variant="outline" className="bg-yellow-500/10 text-yellow-600 border-yellow-500/20">
                                            <AlertCircle className="w-3 h-3 mr-1" />
                                            Missing
                                        </Badge>
                                    )}
                                </div>
                            ))}
                        </div>
                        <p className="text-xs text-muted-foreground">
                            Total files in ZIP: {scanResult.total_files_in_zip}
                        </p>
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
