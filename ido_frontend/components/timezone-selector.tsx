'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import {
    Command,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
} from '@/components/ui/command';
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from '@/components/ui/popover';
import { Check, ChevronsUpDown, Globe } from 'lucide-react';
import { cn } from '@/lib/utils';

// Common timezones for quick selection
const COMMON_TIMEZONES = [
    'UTC',
    'America/New_York',
    'America/Chicago',
    'America/Denver',
    'America/Los_Angeles',
    'Europe/London',
    'Europe/Paris',
    'Europe/Berlin',
    'Asia/Tokyo',
    'Asia/Shanghai',
    'Asia/Kolkata',
    'Asia/Dubai',
    'Australia/Sydney',
    'Pacific/Auckland',
];

interface TimezoneSelectorProps {
    value: string;
    onChange: (timezone: string) => void;
    disabled?: boolean;
}

export function TimezoneSelector({ value, onChange, disabled }: TimezoneSelectorProps) {
    const [open, setOpen] = useState(false);
    const [allTimezones, setAllTimezones] = useState<string[]>(COMMON_TIMEZONES);

    // Auto-detect timezone on mount
    useEffect(() => {
        const detected = Intl.DateTimeFormat().resolvedOptions().timeZone;
        if (detected && !value) {
            onChange(detected);
        }
    }, [onChange, value]);

    // Try to load all timezones from backend
    useEffect(() => {
        fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/content/timezones`)
            .then(res => res.json())
            .then(data => {
                if (data.timezones) {
                    setAllTimezones(data.timezones);
                }
            })
            .catch(() => {
                setAllTimezones(COMMON_TIMEZONES);
            });
    }, []);

    const formatTimezone = (tz: string) => {
        try {
            const offset = new Date().toLocaleString('en-US', { timeZone: tz, timeZoneName: 'short' }).split(' ').pop();
            return `${tz} (${offset})`;
        } catch {
            return tz;
        }
    };

    return (
        <div className="space-y-2">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Globe className="h-4 w-4" />
                <span>Your Timezone</span>
            </div>

            <Popover open={open} onOpenChange={setOpen}>
                <PopoverTrigger asChild>
                    <Button
                        variant="outline"
                        role="combobox"
                        aria-expanded={open}
                        className="w-full justify-between"
                        disabled={disabled}
                    >
                        {value ? formatTimezone(value) : 'Select timezone...'}
                        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                    </Button>
                </PopoverTrigger>
                <PopoverContent className="w-full p-0" align="start">
                    <Command>
                        <CommandInput placeholder="Search timezone..." />
                        <CommandList>
                            <CommandEmpty>No timezone found.</CommandEmpty>
                            <CommandGroup>
                                {allTimezones.slice(0, 50).map((tz) => (
                                    <CommandItem
                                        key={tz}
                                        value={tz}
                                        onSelect={() => {
                                            onChange(tz);
                                            setOpen(false);
                                        }}
                                    >
                                        <Check
                                            className={cn(
                                                'mr-2 h-4 w-4',
                                                value === tz ? 'opacity-100' : 'opacity-0'
                                            )}
                                        />
                                        {formatTimezone(tz)}
                                    </CommandItem>
                                ))}
                            </CommandGroup>
                        </CommandList>
                    </Command>
                </PopoverContent>
            </Popover>

            {value && (
                <p className="text-xs text-muted-foreground">
                    Current time: {new Date().toLocaleString('en-US', { timeZone: value })}
                </p>
            )}
        </div>
    );
}
