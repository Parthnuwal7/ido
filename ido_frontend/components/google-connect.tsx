'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Loader2, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';

/**
 * "Connect Google" flow via the Data Portability API.
 *
 * Google forbids mixing data-portability scopes with any other scope, and the GIS SDK
 * always includes previously granted scopes -- so this uses TWO separate OAuth clients:
 * one for the data portability grant (the export), one for the account grant (openid +
 * youtube.readonly, used for identity and subscriptions). Each grant produces its own
 * token; both live in memory here and are passed to our backend per call.
 *
 * The browser owns the tokens: Google Identity Services hands us access tokens that
 * live in memory here and are passed to our backend per call. The backend never stores
 * the token or the downloaded archive. It does store the generated cards against the
 * Google account so the user can revisit them.
 *
 * Polling is driven from here rather than server-side, because the backend is stateless
 * and (on Hugging Face Spaces) sleeps when idle.
 */

const GIS_SRC = 'https://accounts.google.com/gsi/client';
const POLL_INTERVAL_MS = 20_000;
// Google documents exports as taking minutes to an hour. Past this we stop polling and
// tell the user plainly rather than spinning forever.
const POLL_TIMEOUT_MS = 60 * 60 * 1000;

type Phase = 'idle' | 'connecting' | 'confirm' | 'exporting' | 'processing' | 'error';

interface GoogleConnectProps {
    timezone: string;
    year: number;
    onComplete: (cards: any) => void;
    /** Fired once Google grants a token, so the page can list saved Wrappeds. */
    onToken?: (accessToken: string) => void;
    disabled?: boolean;
}

declare global {
    interface Window {
        google?: any;
    }
}

const apiUrl = () => process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function postJson(path: string, body: unknown) {
    const res = await fetch(`${apiUrl()}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Request failed');
    return data;
}

export function GoogleConnect({ timezone, year, onComplete, onToken, disabled }: GoogleConnectProps) {
    const [phase, setPhase] = useState<Phase>('idle');
    const [error, setError] = useState<string | null>(null);
    const [elapsed, setElapsed] = useState(0);
    const [pollCount, setPollCount] = useState(0);
    const [available, setAvailable] = useState(false);
    const [oauthScopes, setOauthScopes] = useState<string[]>([]);
    const [portabilityScopes, setPortabilityScopes] = useState<string[]>([]);
    // Grant 1's token (data portability), kept until grant 2 completes.
    const [portabilityToken, setPortabilityToken] = useState<string | null>(null);
    const portabilityClientId = useRef<string>('');
    const oauthClientId = useRef<string>('');
    const cancelled = useRef(false);

    useEffect(() => {
        // Reset on every run, not just at ref creation. React StrictMode (the Next.js
        // dev default) mounts, cleans up, then mounts again -- without this the cleanup
        // leaves cancelled.current permanently true, and run()'s poll loop returns on
        // its first iteration, leaving the button stuck on "preparing your export"
        // with no error and no completion.
        cancelled.current = false;

        fetch(`${apiUrl()}/api/portability/config`)
            .then((r) => r.json())
            .then((cfg) => {
                portabilityClientId.current = cfg.client_id || '';
                oauthClientId.current = cfg.oauth_client_id || '';
                setOauthScopes(cfg.oauth_scopes || []);
                setPortabilityScopes(cfg.portability_scopes || []);
                setAvailable(Boolean(cfg.configured));
            })
            .catch(() => setAvailable(false));

        if (!document.querySelector(`script[src="${GIS_SRC}"]`)) {
            const script = document.createElement('script');
            script.src = GIS_SRC;
            script.async = true;
            document.head.appendChild(script);
        }

        return () => {
            cancelled.current = true;
        };
    }, []);

    useEffect(() => {
        if (phase !== 'exporting') return;
        const started = Date.now();
        const tick = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000);
        return () => clearInterval(tick);
    }, [phase]);

    const run = useCallback(
        async (accessToken: string, oauthToken: string) => {
            try {
                setPhase('exporting');
                setPollCount(0);
                const { job_id } = await postJson('/api/portability/initiate', {
                    access_token: accessToken,
                });

                const deadline = Date.now() + POLL_TIMEOUT_MS;
                let urls: string[] = [];

                while (Date.now() < deadline) {
                    if (cancelled.current) return;

                    const state = await postJson('/api/portability/status', {
                        access_token: accessToken,
                        job_id,
                    });
                    setPollCount((c) => c + 1);
                    if (state.complete) {
                        urls = state.urls;
                        break;
                    }

                    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
                }

                if (!urls.length) {
                    throw new Error(
                        'Your export is taking longer than an hour. Google will still finish it — ' +
                        'try connecting again shortly, or download the ZIP from Takeout instead.'
                    );
                }

                setPhase('processing');
                const cards = await postJson('/api/portability/generate', {
                    access_token: accessToken,
                    oauth_token: oauthToken,
                    urls,
                    timezone,
                    year,
                });
                onComplete(cards);
            } catch (e) {
                setError(e instanceof Error ? e.message : 'Something went wrong');
                setPhase('error');
            }
        },
        [timezone, year, onComplete]
    );

    const connect = useCallback(() => {
        if (!window.google?.accounts?.oauth2) {
            setError('Google sign-in could not load. Check your connection and try again.');
            setPhase('error');
            return;
        }

        setError(null);
        setPhase('connecting');

        if (!portabilityToken) {
            // Step 1 (user click): the Data Portability scope via its OWN client. It must
            // come first and from a direct click: chaining a second popup from inside this
            // callback trips the popup blocker. A separate client avoids both the
            // "cannot mix scopes" rule and the restricted-scope incremental-auth rejection.
            window.google.accounts.oauth2
                .initTokenClient({
                    client_id: portabilityClientId.current,
                    scope: portabilityScopes.join(' '),
                    callback: (portabilityResponse: any) => {
                        if (portabilityResponse.error || !portabilityResponse.access_token) {
                            setError('Google access was declined.');
                            setPhase('error');
                            return;
                        }
                        setPortabilityToken(portabilityResponse.access_token);
                        setPhase('confirm');
                    },
                })
                .requestAccessToken();
            return;
        }

        // Step 2 (separate user click): openid + youtube.readonly via the account client.
        window.google.accounts.oauth2
            .initTokenClient({
                client_id: oauthClientId.current,
                scope: oauthScopes.join(' '),
                callback: (oauthResponse: any) => {
                    if (oauthResponse.error || !oauthResponse.access_token) {
                        setError('Google access was declined.');
                        setPhase('error');
                        return;
                    }
                    onToken?.(oauthResponse.access_token);
                    run(portabilityToken, oauthResponse.access_token);
                },
            })
            .requestAccessToken();
    }, [run, oauthScopes, portabilityScopes, onToken, portabilityToken]);

    if (!available) return null;

    const busy = phase === 'connecting' || phase === 'exporting' || phase === 'processing';

    return (
        <div className="space-y-3">
            <Button
                onClick={connect}
                disabled={disabled || busy}
                variant="outline"
                size="lg"
                className="w-full py-6"
            >
                {busy ? (
                    <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                ) : (
                    <ShieldCheck className="w-5 h-5 mr-2" />
                )}
                {phase === 'idle' && 'Connect Google instead'}
                {phase === 'connecting' && 'Waiting for Google…'}
                {phase === 'confirm' && 'Step 2 — Finish signing in'}
                {phase === 'exporting' && `Google is preparing your export… ${Math.floor(elapsed / 60)}m ${elapsed % 60}s`}
                {phase === 'processing' && 'Building your Wrapped…'}
                {phase === 'error' && 'Try connecting again'}
            </Button>

            {phase === 'connecting' && (
                <p className="text-xs text-muted-foreground text-center">
                    {portabilityToken
                        ? 'Approve the Google prompt for your account.'
                        : 'Approve the Google prompt for your YouTube data export.'}
                </p>
            )}

            {phase === 'confirm' && (
                <p className="text-xs text-muted-foreground text-center">
                    Your YouTube data export access is granted. Click again to finish signing
                    in — Google requires the export and your account consent separately.
                </p>
            )}

            {phase === 'exporting' && (
                <div className="text-xs text-muted-foreground text-center space-y-1">
                    <p>
                        Google builds the export on their side — this usually takes a few minutes,
                        occasionally up to an hour. Keep this tab open.
                    </p>
                    <p>
                        {Math.floor(elapsed / 60)}m {elapsed % 60}s elapsed · status check #{pollCount}
                    </p>
                </div>
            )}

            {phase === 'processing' && (
                <p className="text-xs text-muted-foreground text-center">
                    Downloading your archive and building your cards… can take a minute.
                </p>
            )}

            {phase === 'idle' && (
                <p className="text-xs text-muted-foreground text-center">
                    Skips the Takeout download entirely. Your export is processed and deleted —
                    only the insights are saved to your account, and you can delete them any time.
                </p>
            )}

            {error && <p className="text-xs text-destructive text-center">{error}</p>}
        </div>
    );
}
