'use client';

import { CalendarDays } from 'lucide-react';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';

// How many past years to offer before we know what the export actually contains.
const YEARS_BACK = 4;

interface YearSelectorProps {
    value: number;
    onChange: (year: number) => void;
    /**
     * Years the last successful response reported as having watch history. Until a
     * ZIP has been processed we cannot know these, so the list falls back to a recent
     * range. Once known, we offer only years that will actually produce a Wrapped.
     */
    availableYears?: number[];
    disabled?: boolean;
}

export function YearSelector({
    value,
    onChange,
    availableYears,
    disabled,
}: YearSelectorProps) {
    const currentYear = new Date().getFullYear();

    const years =
        availableYears && availableYears.length > 0
            ? [...availableYears].sort((a, b) => b - a)
            : Array.from({ length: YEARS_BACK + 1 }, (_, i) => currentYear - i);

    return (
        <div className="space-y-2">
            <Select
                value={String(value)}
                onValueChange={(v) => onChange(Number(v))}
                disabled={disabled}
            >
                <SelectTrigger className="w-full">
                    <div className="flex items-center gap-2">
                        <CalendarDays className="w-4 h-4 text-muted-foreground" />
                        <SelectValue placeholder="Select a year" />
                    </div>
                </SelectTrigger>
                <SelectContent>
                    {years.map((year) => (
                        <SelectItem key={year} value={String(year)}>
                            {year}
                            {year === currentYear ? ' (this year)' : ''}
                        </SelectItem>
                    ))}
                </SelectContent>
            </Select>

            <p className="text-xs text-muted-foreground">
                {availableYears && availableYears.length > 0
                    ? 'Showing years found in your last upload.'
                    : 'Your Wrapped covers one calendar year.'}
            </p>
        </div>
    );
}
