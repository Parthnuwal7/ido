'use client';

import { Sparkles } from 'lucide-react';

/**
 * Consent for naming taste worlds with an LLM.
 *
 * Unchecked by default. Ticking it sends up to five channel names per taste world,
 * plus the topic categories YouTube assigns them, to OpenRouter. Nothing else leaves:
 * no watch history, no timestamps, no video titles, no identity.
 *
 * Unticked, the taste worlds are labelled with the user's own channel names instead,
 * which always works and is never wrong.
 */

interface InterestNamingConsentProps {
    checked: boolean;
    onChange: (checked: boolean) => void;
    disabled?: boolean;
}

export function InterestNamingConsent({
    checked,
    onChange,
    disabled,
}: InterestNamingConsentProps) {
    return (
        <label className="flex items-start gap-3 cursor-pointer group">
            <input
                type="checkbox"
                checked={checked}
                disabled={disabled}
                onChange={(e) => onChange(e.target.checked)}
                className="mt-1 h-4 w-4 rounded border-input accent-purple-500 cursor-pointer"
            />
            <span className="text-sm">
                <span className="font-medium flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-purple-500" />
                    Name my taste worlds
                </span>
                <span className="block text-xs text-muted-foreground mt-1">
                    Sends a few channel names to an AI service to turn
                    &ldquo;rajasthanroyals &middot; cricinfo&rdquo; into
                    &ldquo;IPL Cricket&rdquo;. Your watch history never leaves.
                    Leave this off and we&rsquo;ll use your channel names instead.
                </span>
            </span>
        </label>
    );
}
