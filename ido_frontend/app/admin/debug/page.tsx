'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Zap, ArrowLeft, Loader2, CheckCircle, XCircle, Circle } from 'lucide-react';
import Link from 'next/link';

type ApiEndpoint = {
    name: string;
    method: 'GET' | 'POST' | 'DELETE';
    path: string;
    needsFile?: boolean;
    bodyTemplate?: string;
};

const ENDPOINTS: ApiEndpoint[] = [
    { name: 'Health Check', method: 'GET', path: '/api/health' },
    { name: 'Get Timezones', method: 'GET', path: '/api/content/timezones' },
    { name: 'List Sessions', method: 'GET', path: '/api/session/' },
    { name: 'Read ZIP', method: 'POST', path: '/api/zip/read', needsFile: true },
    {
        name: 'Extract ZIP',
        method: 'POST',
        path: '/api/zip/extract',
        needsFile: true,
        bodyTemplate: '{"paths": {"watch-history.json": "path/to/file"}, "timezone": "UTC"}'
    },
    {
        name: 'Preview Content',
        method: 'POST',
        path: '/api/content/preview',
        bodyTemplate: '{"files": [], "timezone": "UTC"}'
    },
    {
        name: 'Store Session',
        method: 'POST',
        path: '/api/session/store',
        bodyTemplate: '{"files": [], "timezone": "UTC"}'
    },
    { name: 'Get Session', method: 'GET', path: '/api/session/{token}' },
    { name: 'Delete Session', method: 'DELETE', path: '/api/session/{token}' },
];

export default function DebugPage() {
    const [selectedEndpoint, setSelectedEndpoint] = useState<ApiEndpoint>(ENDPOINTS[0]);
    const [baseUrl, setBaseUrl] = useState('http://localhost:8000');
    const [pathParams, setPathParams] = useState('');
    const [requestBody, setRequestBody] = useState('');
    const [file, setFile] = useState<File | null>(null);
    const [response, setResponse] = useState<string>('');
    const [status, setStatus] = useState<number | null>(null);
    const [loading, setLoading] = useState(false);
    const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking');

    useEffect(() => {
        checkBackendStatus();
    }, [baseUrl]);

    const checkBackendStatus = async () => {
        setBackendStatus('checking');
        try {
            const res = await fetch(`${baseUrl}/api/health`);
            setBackendStatus(res.ok ? 'online' : 'offline');
        } catch {
            setBackendStatus('offline');
        }
    };

    const handleEndpointChange = (name: string) => {
        const endpoint = ENDPOINTS.find(e => e.name === name);
        if (endpoint) {
            setSelectedEndpoint(endpoint);
            setRequestBody(endpoint.bodyTemplate || '');
            setPathParams('');
            setResponse('');
            setStatus(null);
        }
    };

    const getFullPath = () => {
        let path = selectedEndpoint.path;
        if (path.includes('{token}') && pathParams) {
            path = path.replace('{token}', pathParams);
        }
        return `${baseUrl}${path}`;
    };

    const executeRequest = async () => {
        setLoading(true);
        setResponse('');
        setStatus(null);

        try {
            const url = getFullPath();
            const options: RequestInit = {
                method: selectedEndpoint.method,
            };

            if (selectedEndpoint.method === 'POST') {
                if (selectedEndpoint.needsFile && file) {
                    const formData = new FormData();
                    formData.append('file', file);
                    if (requestBody) {
                        try {
                            const body = JSON.parse(requestBody);
                            Object.entries(body).forEach(([key, value]) => {
                                formData.append(key, typeof value === 'string' ? value : JSON.stringify(value));
                            });
                        } catch {
                            // Ignore JSON parse errors for form data
                        }
                    }
                    options.body = formData;
                } else if (requestBody) {
                    options.headers = { 'Content-Type': 'application/json' };
                    options.body = requestBody;
                }
            }

            const res = await fetch(url, options);
            setStatus(res.status);

            const data = await res.json();
            setResponse(JSON.stringify(data, null, 2));
        } catch (err) {
            setResponse(err instanceof Error ? err.message : 'Request failed');
            setStatus(0);
        } finally {
            setLoading(false);
        }
    };

    return (
        <main className="min-h-screen bg-background">
            {/* Header */}
            <header className="border-b bg-card/80 backdrop-blur-lg sticky top-0 z-50">
                <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Link href="/">
                            <Button variant="ghost" size="sm">
                                <ArrowLeft className="w-4 h-4 mr-2" />
                                Back
                            </Button>
                        </Link>
                        <div>
                            <h1 className="text-xl font-bold">API Debug Panel</h1>
                            <p className="text-xs text-muted-foreground">Test backend endpoints</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2">
                        {backendStatus === 'online' ? (
                            <CheckCircle className="w-4 h-4 text-green-500" />
                        ) : backendStatus === 'offline' ? (
                            <XCircle className="w-4 h-4 text-destructive" />
                        ) : (
                            <Circle className="w-4 h-4 text-yellow-500 animate-pulse" />
                        )}
                        <span className="text-sm text-muted-foreground">
                            {backendStatus === 'online' ? 'Backend Online' : backendStatus === 'offline' ? 'Backend Offline' : 'Checking...'}
                        </span>
                    </div>
                </div>
            </header>

            <div className="max-w-6xl mx-auto px-4 py-8">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Request Panel */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Request</CardTitle>
                            <CardDescription>Configure and send API requests</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {/* Base URL */}
                            <div className="space-y-2">
                                <Label>Base URL</Label>
                                <Input
                                    value={baseUrl}
                                    onChange={(e) => setBaseUrl(e.target.value)}
                                />
                            </div>

                            {/* Endpoint selector */}
                            <div className="space-y-2">
                                <Label>Endpoint</Label>
                                <Select
                                    value={selectedEndpoint.name}
                                    onValueChange={handleEndpointChange}
                                >
                                    <SelectTrigger>
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {ENDPOINTS.map((ep) => (
                                            <SelectItem key={ep.name} value={ep.name}>
                                                <span className="flex items-center gap-2">
                                                    <Badge variant={
                                                        ep.method === 'GET' ? 'default' :
                                                            ep.method === 'POST' ? 'secondary' : 'destructive'
                                                    } className="text-xs">
                                                        {ep.method}
                                                    </Badge>
                                                    {ep.name}
                                                </span>
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>

                            {/* Full path display */}
                            <div className="p-3 bg-muted rounded-lg">
                                <div className="flex items-center gap-2">
                                    <Badge variant={
                                        selectedEndpoint.method === 'GET' ? 'default' :
                                            selectedEndpoint.method === 'POST' ? 'secondary' : 'destructive'
                                    }>
                                        {selectedEndpoint.method}
                                    </Badge>
                                    <code className="text-sm break-all">{getFullPath()}</code>
                                </div>
                            </div>

                            {/* Path params */}
                            {selectedEndpoint.path.includes('{token}') && (
                                <div className="space-y-2">
                                    <Label>Token Parameter</Label>
                                    <Input
                                        value={pathParams}
                                        onChange={(e) => setPathParams(e.target.value)}
                                        placeholder="Enter session token"
                                    />
                                </div>
                            )}

                            {/* File upload */}
                            {selectedEndpoint.needsFile && (
                                <div className="space-y-2">
                                    <Label>ZIP File</Label>
                                    <Input
                                        type="file"
                                        accept=".zip"
                                        onChange={(e) => setFile(e.target.files?.[0] || null)}
                                    />
                                    {file && (
                                        <p className="text-xs text-muted-foreground">Selected: {file.name}</p>
                                    )}
                                </div>
                            )}

                            {/* Request body */}
                            {selectedEndpoint.method === 'POST' && (
                                <div className="space-y-2">
                                    <Label>Request Body (JSON)</Label>
                                    <Textarea
                                        value={requestBody}
                                        onChange={(e) => setRequestBody(e.target.value)}
                                        rows={6}
                                        className="font-mono text-sm"
                                        placeholder="{}"
                                    />
                                </div>
                            )}

                            {/* Execute button */}
                            <Button
                                onClick={executeRequest}
                                disabled={loading || backendStatus === 'offline'}
                                className="w-full"
                            >
                                {loading ? (
                                    <>
                                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                        Sending...
                                    </>
                                ) : (
                                    <>
                                        <Zap className="w-4 h-4 mr-2" />
                                        Send Request
                                    </>
                                )}
                            </Button>
                        </CardContent>
                    </Card>

                    {/* Response Panel */}
                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between">
                            <div>
                                <CardTitle>Response</CardTitle>
                                <CardDescription>API response data</CardDescription>
                            </div>
                            {status !== null && (
                                <Badge variant={
                                    status >= 200 && status < 300 ? 'default' :
                                        status >= 400 ? 'destructive' : 'secondary'
                                }>
                                    Status: {status}
                                </Badge>
                            )}
                        </CardHeader>
                        <CardContent>
                            <ScrollArea className="h-[500px] w-full rounded-md border bg-muted/50 p-4">
                                {response ? (
                                    <pre className="text-sm font-mono whitespace-pre-wrap break-words">
                                        {response}
                                    </pre>
                                ) : (
                                    <p className="text-muted-foreground text-center py-16">
                                        Response will appear here
                                    </p>
                                )}
                            </ScrollArea>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </main>
    );
}
