'use client';

import { useState } from 'react';
import { ExtractResult, PreprocessedSessionData } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
    Check,
    Loader2,
    FileJson,
    FileSpreadsheet,
    AlertCircle,
    Sparkles,
    Eye,
    Search,
    Youtube,
    Users,
    Hash,
    Tags
} from 'lucide-react';

interface TopicExtractionResult {
    token: string;
    total_events: number;
    active_watch_events: number;
    events_with_topics: number;
    extraction_stats: {
        total_hashtags: number;
        total_ner: number;
        total_nouns: number;
        total_micro_topics: number;
    };
    status: string;
}

interface ResultsDisplayProps {
    extractResult: ExtractResult | null;
    preprocessedSession: PreprocessedSessionData | null;
    onPreprocessAndStore: () => void;
    isProcessing: boolean;
}

export function ResultsDisplay({
    extractResult,
    preprocessedSession,
    onPreprocessAndStore,
    isProcessing
}: ResultsDisplayProps) {
    const [isExtractingTopics, setIsExtractingTopics] = useState(false);
    const [topicResult, setTopicResult] = useState<TopicExtractionResult | null>(null);
    const [topicError, setTopicError] = useState<string | null>(null);

    if (!extractResult) return null;

    const formatBytes = (bytes: number) => {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    const handleExtractTopics = async () => {
        if (!preprocessedSession) return;

        setIsExtractingTopics(true);
        setTopicError(null);

        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const response = await fetch(`${apiUrl}/api/topics/${preprocessedSession.token}/enrich`, {
                method: 'POST',
            });

            if (!response.ok) {
                throw new Error(`Failed to extract topics: ${response.statusText}`);
            }

            const result = await response.json();
            setTopicResult(result);
        } catch (error) {
            setTopicError(error instanceof Error ? error.message : 'Unknown error');
        } finally {
            setIsExtractingTopics(false);
        }
    };

    // If we have preprocessed data, show that instead
    if (preprocessedSession) {
        const langBreakdown = preprocessedSession.stats.language_breakdown;

        return (
            <Card className="animate-in fade-in-50 slide-in-from-bottom-4">
                <CardHeader className="flex flex-row items-center justify-between">
                    <CardTitle className="text-lg flex items-center gap-2">
                        <Sparkles className="w-5 h-5 text-primary" />
                        Preprocessed Data
                    </CardTitle>
                    <Badge variant="secondary">{preprocessedSession.timezone}</Badge>
                </CardHeader>
                <CardContent className="space-y-4">
                    {/* Stats */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="p-4 bg-muted/50 rounded-lg text-center">
                            <Eye className="w-6 h-6 mx-auto mb-2 text-blue-500" />
                            <p className="text-2xl font-bold">{preprocessedSession.stats.total_watch}</p>
                            <p className="text-xs text-muted-foreground">Watch Events</p>
                        </div>
                        <div className="p-4 bg-muted/50 rounded-lg text-center">
                            <Search className="w-6 h-6 mx-auto mb-2 text-green-500" />
                            <p className="text-2xl font-bold">{preprocessedSession.stats.total_search}</p>
                            <p className="text-xs text-muted-foreground">Search Events</p>
                        </div>
                        <div className="p-4 bg-muted/50 rounded-lg text-center">
                            <Users className="w-6 h-6 mx-auto mb-2 text-purple-500" />
                            <p className="text-2xl font-bold">{preprocessedSession.stats.total_subscribe}</p>
                            <p className="text-xs text-muted-foreground">Subscriptions</p>
                        </div>
                        <div className="p-4 bg-muted/50 rounded-lg text-center">
                            <Youtube className="w-6 h-6 mx-auto mb-2 text-red-500" />
                            <p className="text-2xl font-bold">{preprocessedSession.stats.total_events}</p>
                            <p className="text-xs text-muted-foreground">Total Events</p>
                        </div>
                    </div>

                    {/* Language Breakdown */}
                    {langBreakdown && (
                        <div className="p-4 bg-muted/30 rounded-lg">
                            <h4 className="text-sm font-medium mb-3">Language Breakdown</h4>
                            <div className="grid grid-cols-4 gap-2 text-center">
                                <div>
                                    <p className="text-lg font-bold text-orange-500">{langBreakdown.hindi}</p>
                                    <p className="text-xs text-muted-foreground">Hindi</p>
                                </div>
                                <div>
                                    <p className="text-lg font-bold text-yellow-500">{langBreakdown.hinglish}</p>
                                    <p className="text-xs text-muted-foreground">Hinglish</p>
                                </div>
                                <div>
                                    <p className="text-lg font-bold text-blue-500">{langBreakdown.english}</p>
                                    <p className="text-xs text-muted-foreground">English</p>
                                </div>
                                <div>
                                    <p className="text-lg font-bold text-gray-500">{langBreakdown.unknown}</p>
                                    <p className="text-xs text-muted-foreground">Unknown</p>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Session info */}
                    <Alert className="bg-primary/10 border-primary/30">
                        <Check className="h-4 w-4 text-primary" />
                        <AlertTitle className="text-primary">Data Processed & Stored!</AlertTitle>
                        <AlertDescription className="space-y-1">
                            <p>
                                Token: <code className="bg-muted px-2 py-0.5 rounded text-xs">{preprocessedSession.token}</code>
                            </p>
                            <p className="text-xs text-muted-foreground">
                                Created: {new Date(preprocessedSession.created_at).toLocaleString()}
                            </p>
                        </AlertDescription>
                    </Alert>

                    {/* Topic Extraction Button */}
                    {!topicResult && (
                        <Button
                            onClick={handleExtractTopics}
                            disabled={isExtractingTopics}
                            className="w-full"
                            size="lg"
                            variant="outline"
                        >
                            {isExtractingTopics ? (
                                <>
                                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                    Extracting Topics...
                                </>
                            ) : (
                                <>
                                    <Tags className="w-4 h-4 mr-2" />
                                    Extract Micro Topics
                                </>
                            )}
                        </Button>
                    )}

                    {/* Topic Extraction Error */}
                    {topicError && (
                        <Alert variant="destructive">
                            <AlertCircle className="h-4 w-4" />
                            <AlertTitle>Topic Extraction Failed</AlertTitle>
                            <AlertDescription>{topicError}</AlertDescription>
                        </Alert>
                    )}

                    {/* Topic Extraction Result */}
                    {topicResult && (
                        <Alert className="bg-green-500/10 border-green-500/30">
                            <Tags className="h-4 w-4 text-green-500" />
                            <AlertTitle className="text-green-500">Topics Extracted!</AlertTitle>
                            <AlertDescription>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-2">
                                    <div className="text-center p-2 bg-background/50 rounded">
                                        <p className="text-lg font-bold">{topicResult.extraction_stats.total_hashtags}</p>
                                        <p className="text-xs text-muted-foreground">Hashtags</p>
                                    </div>
                                    <div className="text-center p-2 bg-background/50 rounded">
                                        <p className="text-lg font-bold">{topicResult.extraction_stats.total_ner}</p>
                                        <p className="text-xs text-muted-foreground">Entities</p>
                                    </div>
                                    <div className="text-center p-2 bg-background/50 rounded">
                                        <p className="text-lg font-bold">{topicResult.extraction_stats.total_nouns}</p>
                                        <p className="text-xs text-muted-foreground">Nouns</p>
                                    </div>
                                    <div className="text-center p-2 bg-background/50 rounded">
                                        <p className="text-lg font-bold">{topicResult.extraction_stats.total_micro_topics}</p>
                                        <p className="text-xs text-muted-foreground">Topics</p>
                                    </div>
                                </div>
                                <p className="text-xs text-muted-foreground mt-2">
                                    Processed {topicResult.events_with_topics} of {topicResult.active_watch_events} active watch events
                                </p>
                            </AlertDescription>
                        </Alert>
                    )}

                    {/* Sample events */}
                    <div>
                        <h4 className="text-sm font-medium mb-3">Sample Events</h4>
                        <ScrollArea className="h-64 w-full rounded-md border bg-muted/30 p-3">
                            <div className="space-y-2">
                                {preprocessedSession.events.slice(0, 20).map((event, idx) => (
                                    <div
                                        key={idx}
                                        className="p-3 bg-background rounded-lg border text-sm"
                                    >
                                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                                            <Badge
                                                variant="outline"
                                                className={
                                                    event.type === 'watch' ? 'border-blue-500 text-blue-500' :
                                                        event.type === 'search' ? 'border-green-500 text-green-500' :
                                                            'border-purple-500 text-purple-500'
                                                }
                                            >
                                                {event.type}
                                            </Badge>
                                            {event.engagement && (
                                                <Badge variant="secondary" className="text-xs">
                                                    {event.engagement}
                                                </Badge>
                                            )}
                                            {event.language_type && event.language_type !== 'unknown' && (
                                                <Badge
                                                    variant="outline"
                                                    className={
                                                        event.language_type === 'hindi' ? 'border-orange-500 text-orange-500' :
                                                            event.language_type === 'hinglish' ? 'border-yellow-500 text-yellow-500' :
                                                                'border-blue-400 text-blue-400'
                                                    }
                                                >
                                                    {event.language_type}
                                                </Badge>
                                            )}
                                        </div>
                                        {event.text_raw && (
                                            <p className="text-foreground truncate">{event.text_raw}</p>
                                        )}
                                        {event.channel && (
                                            <p className="text-xs text-muted-foreground">Channel: {event.channel}</p>
                                        )}
                                        {event.timestamp_local && (
                                            <p className="text-xs text-muted-foreground mt-1">
                                                {new Date(event.timestamp_local).toLocaleString()}
                                            </p>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </ScrollArea>
                    </div>
                </CardContent>
            </Card>
        );
    }

    // Show extracted files and preprocess button
    return (
        <Card className="animate-in fade-in-50 slide-in-from-bottom-4">
            <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-lg">Extracted Files</CardTitle>
                <Badge variant="secondary">{extractResult.timezone}</Badge>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* File list */}
                <div className="space-y-3">
                    {extractResult.files.map((file) => (
                        <Card key={file.filename} className="bg-muted/30">
                            <CardContent className="p-4">
                                <div className="flex items-start justify-between">
                                    <div className="flex items-center gap-3">
                                        <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                                            {file.content_type === 'json' ? (
                                                <FileJson className="w-5 h-5 text-primary" />
                                            ) : (
                                                <FileSpreadsheet className="w-5 h-5 text-primary" />
                                            )}
                                        </div>
                                        <div>
                                            <p className="font-medium">{file.filename}</p>
                                            <p className="text-xs text-muted-foreground">{formatBytes(file.size_bytes)}</p>
                                        </div>
                                    </div>
                                    <Badge variant="outline" className="text-xs">
                                        {file.content_type.toUpperCase()}
                                    </Badge>
                                </div>
                            </CardContent>
                        </Card>
                    ))}
                </div>

                {/* Missing files warning */}
                {extractResult.missing_files.length > 0 && (
                    <Alert variant="destructive" className="bg-yellow-500/10 border-yellow-500/30 text-yellow-600">
                        <AlertCircle className="h-4 w-4" />
                        <AlertTitle>Some files could not be extracted</AlertTitle>
                        <AlertDescription>
                            <ul className="list-disc list-inside mt-1">
                                {extractResult.missing_files.map((f) => (
                                    <li key={f}>{f}</li>
                                ))}
                            </ul>
                        </AlertDescription>
                    </Alert>
                )}

                {/* Preprocess button */}
                <Button
                    onClick={onPreprocessAndStore}
                    disabled={isProcessing}
                    className="w-full"
                    size="lg"
                >
                    {isProcessing ? (
                        <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Processing...
                        </>
                    ) : (
                        <>
                            <Sparkles className="w-4 h-4 mr-2" />
                            Preprocess & Store Data
                        </>
                    )}
                </Button>
            </CardContent>
        </Card>
    );
}

