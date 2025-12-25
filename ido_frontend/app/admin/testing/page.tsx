'use client';

import { useState } from 'react';
import { TimezoneSelector } from '@/components/timezone-selector';
import { FileUploader } from '@/components/file-uploader';
import { ProcessingStatus } from '@/components/processing-status';
import { ResultsDisplay } from '@/components/results-display';
import { useZipProcessor } from '@/hooks/use-zip-processor';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Zap, RotateCcw, ArrowLeft, Database, Beaker } from 'lucide-react';
import Link from 'next/link';

/**
 * Admin Testing Page
 * 
 * This page provides the full preprocessing pipeline with storage.
 * Use this for development, debugging, and testing with lossy analysis (topics).
 */
export default function AdminTestingPage() {
    const [timezone, setTimezone] = useState('');
    const [selectedFile, setSelectedFile] = useState<File | null>(null);

    const {
        step,
        scanResult,
        extractResult,
        preprocessedSession,
        error,
        processZip,
        preprocessAndStore,
        reset,
    } = useZipProcessor();

    const handleFileSelect = (file: File) => {
        setSelectedFile(file);
    };

    const handleProcess = async () => {
        if (!selectedFile || !timezone) return;
        await processZip(selectedFile, timezone);
    };

    const handleReset = () => {
        reset();
        setSelectedFile(null);
    };

    const isProcessing = step === 'scanning' || step === 'extracting' || step === 'preprocessing';

    return (
        <main className="min-h-screen bg-background">
            {/* Header */}
            <header className="border-b bg-card/80 backdrop-blur-lg sticky top-0 z-50">
                <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Link href="/admin/debug">
                            <Button variant="ghost" size="icon">
                                <ArrowLeft className="w-4 h-4" />
                            </Button>
                        </Link>
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500 to-red-500 flex items-center justify-center">
                            <Beaker className="w-5 h-5 text-white" />
                        </div>
                        <div>
                            <h1 className="text-xl font-bold">Testing Mode</h1>
                            <p className="text-xs text-muted-foreground">Full pipeline with storage</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        <Database className="w-4 h-4 text-orange-500" />
                        <span className="text-xs text-muted-foreground">Data stored locally</span>
                    </div>
                </div>
            </header>

            {/* Warning banner */}
            <div className="bg-orange-500/10 border-b border-orange-500/20">
                <div className="max-w-4xl mx-auto px-4 py-3 text-sm text-orange-600 dark:text-orange-400">
                    <strong>Testing Mode:</strong> This page stores data in /storage for debugging.
                    Includes full preprocessing and lossy analysis (topics).
                    For production use, use the main page.
                </div>
            </div>

            {/* Main content */}
            <div className="max-w-4xl mx-auto px-4 py-8">
                {/* Steps */}
                <div className="space-y-6">
                    {/* Step 1: Timezone */}
                    <Card>
                        <CardHeader className="pb-4">
                            <CardTitle className="flex items-center gap-3 text-lg">
                                <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-sm">
                                    1
                                </div>
                                Select Your Timezone
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <TimezoneSelector
                                value={timezone}
                                onChange={setTimezone}
                                disabled={isProcessing}
                            />
                        </CardContent>
                    </Card>

                    {/* Step 2: Upload */}
                    <Card>
                        <CardHeader className="pb-4">
                            <CardTitle className="flex items-center gap-3 text-lg">
                                <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold text-sm">
                                    2
                                </div>
                                Upload Your Data
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <FileUploader
                                onFileSelect={handleFileSelect}
                                disabled={isProcessing}
                            />
                        </CardContent>
                    </Card>

                    {/* Process button */}
                    {selectedFile && timezone && step === 'idle' && (
                        <Button
                            onClick={handleProcess}
                            size="lg"
                            className="w-full py-6 text-lg bg-orange-500 hover:bg-orange-600"
                        >
                            <Zap className="w-5 h-5 mr-2" />
                            Process & Store Data
                        </Button>
                    )}

                    {/* Processing status */}
                    {step !== 'idle' && (
                        <ProcessingStatus
                            step={step}
                            scanResult={scanResult}
                            error={error}
                        />
                    )}

                    {/* Results */}
                    {extractResult && (
                        <ResultsDisplay
                            extractResult={extractResult}
                            preprocessedSession={preprocessedSession}
                            onPreprocessAndStore={preprocessAndStore}
                            isProcessing={step === 'preprocessing'}
                        />
                    )}

                    {/* Reset button */}
                    {(step === 'complete' || step === 'error') && (
                        <Button
                            onClick={handleReset}
                            variant="outline"
                            className="w-full"
                        >
                            <RotateCcw className="w-4 h-4 mr-2" />
                            Start Over
                        </Button>
                    )}
                </div>
            </div>
        </main>
    );
}
