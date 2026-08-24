'use client';

import { Calendar, Sparkles, TrendingUp, Users, Zap } from 'lucide-react';
import {
    WrappedCard,
    WrappedCardHeader,
    WrappedCardContent,
    WrappedCardFooter,
    WrappedHeading,
    WrappedSubtitle,
    WrappedBigNumber,
    WrappedBadge,
    CircleShape,
    SemiCircleShape,
    GridPattern,
} from './index';

/**
 * Cards for the viewing-style and taste-world insights.
 *
 * Kept apart from card-templates.tsx, which is already long. Two conventions hold
 * across every card here:
 *
 *  - Nothing is readable by colour or area alone. The radar carries its own
 *    percentages; the heatmap identifies rows by label, not hue.
 *  - Nothing claims a comparison we cannot make. We only ever see one user's data,
 *    so no card says "more than average". niche_meter is the single exception and
 *    only because a subscriber count is an absolute quantity.
 */

// ============================================
// VIEWING MODE
// ============================================

interface ViewingModeCardProps {
    rapidShare: number;
    rapidWatches: number;
    consideredWatches: number;
    longestChain: number;
    longestChainMinutes: number;
    style: string;
}

/**
 * A single ratio against a whole, so this is a meter rather than a chart -- a
 * one-bar bar chart would be noise. The footnote is not decoration: Takeout never
 * labels Shorts, so this is a deduction from timing and the card has to say so.
 */
export function ViewingModeCard({
    rapidShare,
    rapidWatches,
    consideredWatches,
    longestChain,
    longestChainMinutes,
    style,
}: ViewingModeCardProps) {
    const pct = Math.round(rapidShare * 100);

    return (
        <WrappedCard theme="coral">
            <CircleShape className="w-40 h-40 -bottom-20 -left-20" color="bg-white/10" />

            <WrappedCardHeader logo={<Zap className="w-6 h-6" />} label="How You Watch" />

            <WrappedCardContent>
                <WrappedBigNumber value={`${pct}%`} />
                <WrappedSubtitle className="mb-6 text-center">
                    of your watching was rapid-fire
                </WrappedSubtitle>

                <div className="w-full max-w-xs mb-6">
                    <div className="flex h-4 rounded-full overflow-hidden bg-white/20">
                        <div className="bg-white" style={{ width: `${pct}%` }} />
                    </div>
                    <div className="flex justify-between text-xs mt-2 opacity-80">
                        <span>{rapidWatches.toLocaleString()} rapid</span>
                        <span>{consideredWatches.toLocaleString()} settled in</span>
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-3 w-full max-w-xs text-center">
                    <div className="p-3 bg-white/10 rounded-xl">
                        <div className="text-2xl font-bold">{longestChain}</div>
                        <div className="text-xs opacity-80">in a row</div>
                    </div>
                    <div className="p-3 bg-white/10 rounded-xl">
                        <div className="text-2xl font-bold">
                            {Math.round(longestChainMinutes)}m
                        </div>
                        <div className="text-xs opacity-80">without pausing</div>
                    </div>
                </div>

                <WrappedBadge className="mt-4">
                    {style === 'bingeing' ? 'You settle in' : 'You graze'}
                </WrappedBadge>
            </WrappedCardContent>

            <WrappedCardFooter>
                <span className="text-[10px] opacity-60">
                    Inferred from gaps between videos — YouTube doesn&rsquo;t mark which were Shorts
                </span>
            </WrappedCardFooter>
        </WrappedCard>
    );
}

// ============================================
// DISCOVERY ARC
// ============================================

interface DiscoveryArcCardProps {
    months: { month: string; novelty_rate: number; top10_share: number }[];
    noveltyStart: number | null;
    noveltyEnd: number | null;
    summary: string;
}

/**
 * Two series on ONE axis. Both are shares of a month, so they are directly
 * comparable and a second y-scale would misrepresent them. A legend is present
 * because there are two series.
 */
export function DiscoveryArcCard({
    months,
    noveltyStart,
    noveltyEnd,
    summary,
}: DiscoveryArcCardProps) {
    const w = 280;
    const h = 110;
    const pad = 6;

    const line = (key: 'novelty_rate' | 'top10_share') =>
        months
            .map((m, i) => {
                const x = pad + (i / Math.max(months.length - 1, 1)) * (w - pad * 2);
                const y = h - pad - m[key] * (h - pad * 2);
                return `${x},${y}`;
            })
            .join(' ');

    const headline =
        summary === 'narrowing_but_spreading'
            ? 'You stopped hunting, and spread out'
            : summary === 'narrowing'
                ? 'Your circle got tighter'
                : summary === 'widening'
                    ? 'You kept finding new things'
                    : 'You held steady';

    return (
        <WrappedCard theme="navy">
            <GridPattern className="inset-0 w-full h-full opacity-10" />

            <WrappedCardHeader
                logo={<TrendingUp className="w-6 h-6" />}
                label="Your Year Shifted"
            />

            <WrappedCardContent position="start" className="pt-4">
                <WrappedHeading size="xl" className="mb-6 text-center">
                    {headline}
                </WrappedHeading>

                {months.length > 1 && (
                    <svg
                        viewBox={`0 0 ${w} ${h}`}
                        className="w-full mb-3"
                        role="img"
                        aria-label="New channels found and top-ten share, month by month"
                    >
                        {[0.25, 0.5, 0.75].map((g) => (
                            <line
                                key={g}
                                x1={pad}
                                x2={w - pad}
                                y1={h - pad - g * (h - pad * 2)}
                                y2={h - pad - g * (h - pad * 2)}
                                stroke="rgba(255,255,255,0.12)"
                                strokeWidth="1"
                            />
                        ))}
                        <polyline
                            points={line('novelty_rate')}
                            fill="none"
                            stroke="#FFDD00"
                            strokeWidth="2"
                            strokeLinecap="round"
                        />
                        <polyline
                            points={line('top10_share')}
                            fill="none"
                            stroke="#5EEAD4"
                            strokeWidth="2"
                            strokeLinecap="round"
                        />

                        {/* Direct labels at each line start and end, so a value can be
                            read off the chart without tracing back to the legend. */}
                        {(['novelty_rate', 'top10_share'] as const).map((key) =>
                            [0, months.length - 1].map((i) => {
                                const colour =
                                    key === 'novelty_rate' ? '#FFDD00' : '#5EEAD4';
                                const x =
                                    pad +
                                    (i / Math.max(months.length - 1, 1)) * (w - pad * 2);
                                const y = h - pad - months[i][key] * (h - pad * 2);
                                return (
                                    <g key={`${key}-${i}`}>
                                        <circle cx={x} cy={y} r="3" fill={colour} />
                                        <text
                                            x={i === 0 ? x + 6 : x - 6}
                                            y={y - 7}
                                            fill={colour}
                                            fontSize="11"
                                            fontWeight="700"
                                            textAnchor={i === 0 ? 'start' : 'end'}
                                        >
                                            {Math.round(months[i][key] * 100)}%
                                        </text>
                                    </g>
                                );
                            })
                        )}
                    </svg>
                )}

                <div className="flex gap-5 justify-center text-xs mb-5">
                    <span className="flex items-center gap-1.5">
                        <span className="w-4 h-[3px] rounded bg-[#FFDD00]" />
                        new channels
                    </span>
                    <span className="flex items-center gap-1.5">
                        <span className="w-4 h-[3px] rounded bg-[#5EEAD4]" />
                        top-10 share
                    </span>
                </div>

                {noveltyStart !== null && noveltyEnd !== null && (
                    <p className="text-sm text-center opacity-90">
                        New-channel discovery went from{' '}
                        <strong>{Math.round(noveltyStart * 100)}%</strong> to{' '}
                        <strong>{Math.round(noveltyEnd * 100)}%</strong> of your watching
                    </p>
                )}
            </WrappedCardContent>
        </WrappedCard>
    );
}

// ============================================
// TASTE WORLDS
// ============================================

interface TasteWorld {
    label: string;
    name: string | null;
    channels: string[];
    share: number;
    watches: number;
}

interface TasteWorldsCardProps {
    worlds: TasteWorld[];
    coverage: number;
}

/**
 * A radar reads as a shape rather than as precise magnitudes, which is the point
 * on a Wrapped card. Shape alone would not be honest, so every world also carries
 * its percentage in text -- nothing here is readable by area only.
 *
 * `coverage` is shown because clusters never describe all viewing: the long tail
 * of once-watched channels cannot be placed in any world.
 */
export function TasteWorldsCard({ worlds, coverage }: TasteWorldsCardProps) {
    const shown = worlds.slice(0, 8);
    const axes = Math.max(shown.length, 3);
    const peak = Math.max(...shown.map((w) => w.share), 0.01);

    const point = (i: number, r: number): [number, number] => {
        const angle = (i / axes) * 2 * Math.PI - Math.PI / 2;
        return [50 + r * Math.cos(angle), 50 + r * Math.sin(angle)];
    };

    const shape = shown
        .map((w, i) => point(i, 8 + (w.share / peak) * 34).join(','))
        .join(' ');

    return (
        <WrappedCard theme="purple">
            <WrappedCardHeader
                logo={<Sparkles className="w-6 h-6" />}
                label="Your Taste Worlds"
            />

            <WrappedCardContent position="start" className="pt-2">
                <WrappedHeading size="xl" className="mb-3 text-center">
                    You lived in {shown.length} worlds
                </WrappedHeading>

                <div className="relative w-40 h-40 mx-auto mb-4">
                    <svg
                        viewBox="0 0 100 100"
                        className="w-full h-full"
                        role="img"
                        aria-label="Share of viewing per taste world"
                    >
                        {[0.33, 0.66, 1].map((ring) => (
                            <polygon
                                key={ring}
                                points={Array.from({ length: axes }, (_, i) =>
                                    point(i, 8 + ring * 34).join(',')
                                ).join(' ')}
                                fill="none"
                                stroke="rgba(255,255,255,0.15)"
                                strokeWidth="0.6"
                            />
                        ))}
                        {Array.from({ length: axes }, (_, i) => {
                            const [x, y] = point(i, 42);
                            return (
                                <line
                                    key={i}
                                    x1="50"
                                    y1="50"
                                    x2={x}
                                    y2={y}
                                    stroke="rgba(255,255,255,0.15)"
                                    strokeWidth="0.6"
                                />
                            );
                        })}
                        <polygon
                            points={shape}
                            fill="#FFDD00"
                            fillOpacity="0.35"
                            stroke="#FFDD00"
                            strokeWidth="2"
                            strokeLinejoin="round"
                        />
                    </svg>
                </div>

                <div className="w-full space-y-1.5">
                    {shown.map((world, i) => (
                        <div
                            key={i}
                            className="flex items-baseline justify-between gap-3 text-sm"
                        >
                            <span className="truncate opacity-90">
                                {world.name || world.label}
                            </span>
                            <span className="font-bold shrink-0">
                                {Math.round(world.share * 100)}%
                            </span>
                        </div>
                    ))}
                </div>
            </WrappedCardContent>

            <WrappedCardFooter>
                <span className="text-[10px] opacity-60">
                    Covers {Math.round(coverage * 100)}% of your watching — the rest is one-off channels
                </span>
            </WrappedCardFooter>
        </WrappedCard>
    );
}

// ============================================
// TASTE CALENDAR
// ============================================

interface TasteCalendarCardProps {
    months: string[];
    worlds: { label: string; name: string | null; shares: number[] }[];
    seasonal: boolean;
}

const FULL_MONTHS = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
];

/**
 * The two most interesting things the grid shows, in words.
 *
 * A heatmap rewards study; a Wrapped card gets a few seconds. These pull out the
 * peak ("April was your cricket month") and the clearest rise ("you grew into pop
 * music") so the card says something even to someone who never reads the grid.
 */
function calendarTakeaways(
    months: string[],
    worlds: { label: string; name: string | null; shares: number[] }[]
): string[] {
    const nameOf = (world: { label: string; name: string | null }) =>
        world.name || world.label.split(' \u00b7 ')[0];
    const monthName = (i: number) =>
        FULL_MONTHS[Math.max(0, parseInt(months[i]?.slice(5, 7) ?? '1', 10) - 1)];

    const out: string[] = [];

    let peak = { world: '', month: 0, share: 0 };
    worlds.forEach((world) => {
        world.shares.forEach((share, i) => {
            if (share > peak.share) peak = { world: nameOf(world), month: i, share };
        });
    });
    if (peak.share > 0.3) {
        out.push(
            `${monthName(peak.month)} was your ${peak.world.toLowerCase()} month \u2014 ` +
            `${Math.round(peak.share * 100)}% of it went there`
        );
    }

    if (months.length >= 4) {
        const third = Math.max(1, Math.floor(months.length / 3));
        const mean = (xs: number[]) => xs.reduce((a, b) => a + b, 0) / (xs.length || 1);
        let rise = { world: '', delta: 0 };
        worlds.forEach((world) => {
            const delta =
                mean(world.shares.slice(-third)) - mean(world.shares.slice(0, third));
            if (delta > rise.delta) rise = { world: nameOf(world), delta };
        });
        if (rise.delta > 0.05) {
            out.push(`You grew into ${rise.world.toLowerCase()} as the year went on`);
        }
    }

    return out.slice(0, 2);
}

const MONTH_LETTERS = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'];

/**
 * Sequential encoding: ONE hue, more-is-darker. Row identity comes from the row
 * label rather than from colour, so no categorical palette is involved and there
 * is nothing for a colourblind reader to disambiguate by hue.
 */
export function TasteCalendarCard({ months, worlds, seasonal }: TasteCalendarCardProps) {
    const shown = worlds.slice(0, 8);
    const peak = Math.max(...shown.flatMap((w) => w.shares), 0.01);
    const takeaways = calendarTakeaways(months, shown);

    const letterFor = (month: string) =>
        MONTH_LETTERS[Math.max(0, parseInt(month.slice(5, 7), 10) - 1)] ?? '';

    return (
        <WrappedCard theme="navy">
            <WrappedCardHeader
                logo={<Calendar className="w-6 h-6" />}
                label="Your Year In Worlds"
            />

            <WrappedCardContent position="start" className="pt-2">
                <WrappedHeading size="xl" className="mb-4 text-center">
                    {seasonal ? 'Your taste had seasons' : 'Your taste held steady'}
                </WrappedHeading>

                <div className="w-full overflow-x-auto">
                    <div className="min-w-fit">
                        <div className="flex gap-[2px] mb-1 pl-[92px]">
                            {months.map((month, i) => (
                                <div
                                    key={i}
                                    className="w-5 text-center text-[9px] opacity-60"
                                >
                                    {letterFor(month)}
                                </div>
                            ))}
                        </div>

                        {shown.map((world, row) => (
                            <div key={row} className="flex items-center gap-[2px] mb-[2px]">
                                <div className="w-[88px] pr-1 truncate text-[10px] opacity-80 text-right">
                                    {world.name || world.label.split(' · ')[0]}
                                </div>
                                {world.shares.map((share, col) => (
                                    <div
                                        key={col}
                                        className="w-5 h-5 rounded-[3px]"
                                        style={{
                                            backgroundColor: '#FFDD00',
                                            opacity: 0.08 + (share / peak) * 0.92,
                                        }}
                                        title={`${world.name || world.label}: ${Math.round(
                                            share * 100
                                        )}% of ${months[col]}`}
                                    />
                                ))}
                            </div>
                        ))}
                    </div>
                </div>

                <div className="mt-5 space-y-2 w-full">
                    {takeaways.map((line, i) => (
                        <div
                            key={i}
                            className="p-3 bg-white/10 rounded-xl text-sm leading-snug"
                        >
                            {line}
                        </div>
                    ))}
                </div>

                <p className="text-[11px] text-center opacity-60 mt-4">
                    Brighter means more of that month went to that world
                </p>
            </WrappedCardContent>
        </WrappedCard>
    );
}

// ============================================
// NICHE METER
// ============================================

interface NicheMeterCardProps {
    medianSubscribers: number;
    obscureFind: { channel: string; subscribers: number };
    bucketCounts: { under_10k: number; '10k_1m': number; over_1m: number };
    channelsMeasured: number;
}

/**
 * The only card here on an absolute scale. Everything else in this set is relative
 * with no baseline, which is why none of them says "more than average" -- a
 * subscriber count is a real quantity that means something on its own.
 */
export function NicheMeterCard({
    medianSubscribers,
    obscureFind,
    bucketCounts,
    channelsMeasured,
}: NicheMeterCardProps) {
    const compact = (n: number) =>
        n >= 1_000_000
            ? `${(n / 1_000_000).toFixed(1)}M`
            : n >= 1_000
                ? `${Math.round(n / 1_000)}K`
                : `${n}`;

    const buckets = [
        { label: 'under 10K', count: bucketCounts.under_10k },
        { label: '10K–1M', count: bucketCounts['10k_1m'] },
        { label: 'over 1M', count: bucketCounts.over_1m },
    ];
    const total = Math.max(
        buckets.reduce((sum, bucket) => sum + bucket.count, 0),
        1
    );

    return (
        <WrappedCard theme="teal">
            <SemiCircleShape className="w-40 h-20 top-0 right-0" color="bg-white/10" />

            <WrappedCardHeader
                logo={<Users className="w-6 h-6" />}
                label="Mainstream Or Not"
            />

            <WrappedCardContent>
                <WrappedBigNumber value={compact(medianSubscribers)} />
                <WrappedSubtitle className="mb-6 text-center">
                    subscribers on your median channel
                </WrappedSubtitle>

                <div className="w-full max-w-xs mb-2">
                    <div className="flex h-4 rounded-full overflow-hidden gap-[2px]">
                        {buckets.map((bucket, i) => (
                            <div
                                key={i}
                                className="bg-white"
                                style={{
                                    width: `${(bucket.count / total) * 100}%`,
                                    opacity: 0.35 + i * 0.32,
                                }}
                            />
                        ))}
                    </div>
                    <div className="flex justify-between text-[10px] mt-2 opacity-80">
                        {buckets.map((bucket, i) => (
                            <span key={i}>
                                {bucket.label}: {bucket.count}
                            </span>
                        ))}
                    </div>
                </div>

                <div className="mt-5 p-3 bg-white/10 rounded-xl w-full max-w-xs text-center">
                    <div className="text-[10px] uppercase tracking-wide opacity-70 mb-1">
                        Your deepest cut
                    </div>
                    <div className="font-bold truncate">{obscureFind.channel}</div>
                    <div className="text-xs opacity-80">
                        {compact(obscureFind.subscribers)} subscribers
                    </div>
                </div>
            </WrappedCardContent>

            <WrappedCardFooter>
                <span className="text-[10px] opacity-60">
                    Across {channelsMeasured} of your regular channels
                </span>
            </WrappedCardFooter>
        </WrappedCard>
    );
}
