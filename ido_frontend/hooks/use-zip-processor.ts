'use client';

import { useState, useCallback } from 'react';
import api, { ScanResult, ExtractResult, PreprocessedSessionData } from '@/lib/api';

export type ProcessingStep = 'idle' | 'scanning' | 'extracting' | 'preprocessing' | 'complete' | 'error';

interface UseZipProcessorReturn {
    step: ProcessingStep;
    scanResult: ScanResult | null;
    extractResult: ExtractResult | null;
    preprocessedSession: PreprocessedSessionData | null;
    error: string | null;
    processZip: (file: File, timezone: string) => Promise<void>;
    preprocessAndStore: () => Promise<void>;
    reset: () => void;
}

export function useZipProcessor(): UseZipProcessorReturn {
    const [step, setStep] = useState<ProcessingStep>('idle');
    const [scanResult, setScanResult] = useState<ScanResult | null>(null);
    const [extractResult, setExtractResult] = useState<ExtractResult | null>(null);
    const [preprocessedSession, setPreprocessedSession] = useState<PreprocessedSessionData | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [currentTimezone, setCurrentTimezone] = useState<string>('UTC');

    const processZip = useCallback(async (file: File, timezone: string) => {
        setError(null);
        setCurrentTimezone(timezone);

        try {
            // Step 1: Scan the ZIP
            setStep('scanning');
            const scan = await api.readZip(file);
            setScanResult(scan);

            // Get paths of found files (filter out nulls)
            const foundPaths: Record<string, string> = {};
            Object.entries(scan.found_files).forEach(([filename, path]) => {
                if (path) foundPaths[filename] = path;
            });

            if (Object.keys(foundPaths).length === 0) {
                throw new Error('No target files found in the ZIP archive');
            }

            // Step 2: Extract the files
            setStep('extracting');
            const extract = await api.extractZip(file, foundPaths, timezone);
            setExtractResult(extract);
            setStep('complete');

        } catch (err) {
            setStep('error');
            setError(err instanceof Error ? err.message : 'An unknown error occurred');
        }
    }, []);

    const preprocessAndStore = useCallback(async () => {
        if (!extractResult) {
            setError('No extracted files to process');
            return;
        }

        try {
            setStep('preprocessing');
            const session = await api.preprocessAndStore(extractResult.files, currentTimezone);
            setPreprocessedSession(session);
            setStep('complete');
        } catch (err) {
            setStep('error');
            setError(err instanceof Error ? err.message : 'Failed to preprocess and store');
        }
    }, [extractResult, currentTimezone]);

    const reset = useCallback(() => {
        setStep('idle');
        setScanResult(null);
        setExtractResult(null);
        setPreprocessedSession(null);
        setError(null);
    }, []);

    return {
        step,
        scanResult,
        extractResult,
        preprocessedSession,
        error,
        processZip,
        preprocessAndStore,
        reset,
    };
}
