'use client';

import { useCallback, useEffect, useState } from 'react';
import { History, Loader2, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

/**
 * Wrappeds this Google account has saved.
 *
 * Only generated cards are stored server-side, never the uploaded archive and never the
 * access token. The token below lives in memory for this page session and is sent as a
 * bearer credential; the backend resolves it to an account id with Google rather than
 * trusting anything the browser claims.
 */

interface SavedWrapped {
    year: number;
    source: string;
    created_at: string;
}

interface SavedWrappedsProps {
    accessToken: string | null;
    onOpen: (cards: any) => void;
}

const apiUrl = () => process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function SavedWrappeds({ accessToken, onOpen }: SavedWrappedsProps) {
    const [items, setItems] = useState<SavedWrapped[]>([]);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const authHeaders = useCallback(
        () => ({ Authorization: `Bearer ${accessToken}` }),
        [accessToken]
    );

    const refresh = useCallback(async () => {
        if (!accessToken) return;
        try {
            const res = await fetch(`${apiUrl()}/api/me/wrapped`, { headers: authHeaders() });
            if (!res.ok) return; // not signed in, or nothing saved yet
            const data = await res.json();
            setItems(data.wrappeds || []);
        } catch {
            /* a missing history list is not worth interrupting the page for */
        }
    }, [accessToken, authHeaders]);

    useEffect(() => {
        refresh();
    }, [refresh]);

    const open = async (year: number) => {
        setBusy(true);
        setError(null);
        try {
            const res = await fetch(`${apiUrl()}/api/me/wrapped/${year}`, {
                headers: authHeaders(),
            });
            if (!res.ok) throw new Error('That Wrapped could not be loaded');
            const data = await res.json();
            onOpen(data.cards);
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Something went wrong');
        } finally {
            setBusy(false);
        }
    };

    const forget = async () => {
        setBusy(true);
        setError(null);
        try {
            await fetch(`${apiUrl()}/api/me/data`, { method: 'DELETE', headers: authHeaders() });
            setItems([]);
        } catch {
            setError('Could not delete your saved data');
        } finally {
            setBusy(false);
        }
    };

    if (!accessToken || items.length === 0) return null;

    return (
        <Card>
            <CardHeader className="pb-4">
                <CardTitle className="text-lg flex items-center gap-2">
                    <History className="w-5 h-5" />
                    Your saved Wrappeds
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
                <div className="flex flex-wrap gap-2">
                    {items.map((item) => (
                        <Button
                            key={item.year}
                            variant="secondary"
                            disabled={busy}
                            onClick={() => open(item.year)}
                        >
                            {busy ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
                            {item.year}
                        </Button>
                    ))}
                </div>

                <div className="flex items-center justify-between pt-1">
                    <p className="text-xs text-muted-foreground">
                        Only your generated insights are saved — never your uploaded data.
                    </p>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={forget}
                        disabled={busy}
                        className="text-destructive hover:text-destructive"
                    >
                        <Trash2 className="w-4 h-4 mr-1" />
                        Delete
                    </Button>
                </div>

                {error && <p className="text-xs text-destructive">{error}</p>}
            </CardContent>
        </Card>
    );
}
