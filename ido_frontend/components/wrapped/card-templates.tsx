'use client';

import {
    Youtube, Clock, Flame, TrendingUp, Moon, Sun,
    Users, Calendar, Search, Play, Bell, Repeat,
    Heart, Zap, Timer, Award, Sparkles, Share2
} from 'lucide-react';
import {
    WrappedCard,
    WrappedCardHeader,
    WrappedCardContent,
    WrappedCardFooter,
    WrappedHeading,
    WrappedSubtitle,
    WrappedBigNumber,
    WrappedBadge,
    WrappedRankingList,
    WrappedYearBadge,
    WrappedProgressBar,
    CircleShape,
    SemiCircleShape,
    GridPattern,
    CardTheme,
} from './index';

/**
 * YouTube Wrapped Card Templates v2
 * Based on cards_doc.md specification
 */

// ============================================
// SECTION 1: INTRO
// ============================================

interface IntroCardProps {
    username?: string;
    year?: number;
}

export function IntroCard({ username = 'there', year = 2025 }: IntroCardProps) {
    return (
        <WrappedCard theme="yellow">
            <CircleShape className="w-32 h-32 -top-8 -right-8" color="bg-[#6B5ACD]" />
            <SemiCircleShape className="w-48 h-48 -bottom-24 -left-24" color="bg-[#6B5ACD]/50" />
            <CircleShape className="w-20 h-20 bottom-32 right-8" color="bg-[#6B5ACD]/30" />

            <WrappedCardHeader logo={<Youtube className="w-6 h-6" />} label="YouTube Wrapped" />

            <WrappedCardContent>
                <WrappedHeading size="5xl">
                    Oh, hey{username && `,`}
                    {username && <br />}
                    {username && `${username}!`}
                </WrappedHeading>
                <WrappedSubtitle className="mt-4">
                    It&apos;s time to take a look at your year with YouTube
                </WrappedSubtitle>
            </WrappedCardContent>

            <WrappedCardFooter>
                <WrappedYearBadge year={year} />
            </WrappedCardFooter>
        </WrappedCard>
    );
}

// ============================================
// SECTION 2: YOUR YEAR WITH US
// ============================================

interface StatsOverviewCardProps {
    videosWatched: number;
    channelsExplored: number;
    activeDays: number;
    totalSessions: number;
}

export function StatsOverviewCard({
    videosWatched,
    channelsExplored,
    activeDays,
    totalSessions
}: StatsOverviewCardProps) {
    return (
        <WrappedCard theme="gradient2">
            <GridPattern className="inset-0 w-full h-full opacity-10" />

            <WrappedCardHeader logo={<TrendingUp className="w-6 h-6" />} label="Your Year With Us" />

            <WrappedCardContent>
                <WrappedHeading size="3xl" className="mb-8 text-center">
                    Your year in numbers
                </WrappedHeading>

                <div className="space-y-4">
                    <div className="text-center p-4 bg-white/10 rounded-2xl">
                        <div className="text-4xl font-black">{videosWatched.toLocaleString()}</div>
                        <div className="text-sm opacity-70">videos watched</div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        <div className="text-center p-3 bg-white/10 rounded-xl">
                            <div className="text-2xl font-black">{channelsExplored}</div>
                            <div className="text-xs opacity-70">channels explored</div>
                        </div>
                        <div className="text-center p-3 bg-white/10 rounded-xl">
                            <div className="text-2xl font-black">{activeDays}</div>
                            <div className="text-xs opacity-70">days active</div>
                        </div>
                    </div>

                    <div className="text-center p-3 bg-white/10 rounded-xl">
                        <div className="text-2xl font-black">{totalSessions}</div>
                        <div className="text-xs opacity-70">watch sessions</div>
                    </div>
                </div>
            </WrappedCardContent>
        </WrappedCard>
    );
}

interface TimeSpentCardProps {
    totalHours: number;
    totalMinutes: number;
    avgDailyMinutes: number;
}

export function TimeSpentCard({ totalHours, totalMinutes, avgDailyMinutes }: TimeSpentCardProps) {
    return (
        <WrappedCard theme="gradient1">
            <CircleShape className="w-64 h-64 -top-32 -right-32 opacity-30" color="bg-white" />
            <GridPattern className="inset-0 w-full h-full" />

            <WrappedCardHeader logo={<Clock className="w-6 h-6" />} label="Time Spent" />

            <WrappedCardContent>
                <WrappedHeading size="2xl" className="mb-4">
                    You spent a total of
                </WrappedHeading>

                <WrappedBigNumber value={totalHours} suffix="hours" />

                <p className="text-center text-lg opacity-70 mt-2">
                    ({totalMinutes.toLocaleString()} minutes)
                </p>
            </WrappedCardContent>

            <WrappedCardFooter className="text-center">
                <WrappedBadge variant="filled">
                    {avgDailyMinutes} min/day average
                </WrappedBadge>
            </WrappedCardFooter>
        </WrappedCard>
    );
}

interface MostActiveMonthCardProps {
    peakMonth: string;
    peakMonthWatches: number;
    monthlyTrend?: number[]; // 12 values for area chart
}

export function MostActiveMonthCard({ peakMonth, peakMonthWatches }: MostActiveMonthCardProps) {
    return (
        <WrappedCard theme="teal">
            <CircleShape className="w-40 h-40 -bottom-20 -right-20" color="bg-[#FF6B6B]" />

            <WrappedCardHeader logo={<Calendar className="w-6 h-6" />} label="Peak Activity" />

            <WrappedCardContent>
                <WrappedHeading size="2xl" className="mb-4">
                    Your YouTube usage peaked in
                </WrappedHeading>

                <WrappedHeading size="5xl" className="mb-4">
                    {peakMonth}
                </WrappedHeading>

                <WrappedBadge variant="outline">
                    {peakMonthWatches} videos watched
                </WrappedBadge>
            </WrappedCardContent>
        </WrappedCard>
    );
}

// ============================================
// SECTION 3: YOUR FAVORITES
// ============================================

interface ChannelSpotlightCardProps {
    channelName: string;
    totalViews: number;
    percentageOfTotal?: number;
}

export function ChannelSpotlightCard({
    channelName,
    totalViews,
    percentageOfTotal
}: ChannelSpotlightCardProps) {
    return (
        <WrappedCard theme="coral">
            <SemiCircleShape className="w-72 h-72 -top-36 -left-36" color="bg-white/20" />
            <CircleShape className="w-24 h-24 bottom-24 right-4" color="bg-[#2D1B4E]" />

            <WrappedCardHeader logo={<Award className="w-6 h-6" />} label="Your #1" />

            <WrappedCardContent>
                <WrappedHeading size="2xl" className="mb-4">
                    Your most watched channel was
                </WrappedHeading>

                <WrappedHeading size="4xl" className="mb-6">
                    {channelName}
                </WrappedHeading>

                <div className="flex flex-col gap-2 items-center">
                    <WrappedBadge variant="filled">
                        {totalViews} videos watched
                    </WrappedBadge>
                    {percentageOfTotal && (
                        <WrappedSubtitle className="text-center">
                            That&apos;s {percentageOfTotal}% of all your views!
                        </WrappedSubtitle>
                    )}
                </div>
            </WrappedCardContent>
        </WrappedCard>
    );
}

interface TopChannelsCardProps {
    channels: { name: string; views: number }[];
}

export function TopChannelsCard({ channels }: TopChannelsCardProps) {
    const items = channels.slice(0, 5).map((ch, i) => ({
        rank: i + 1,
        label: ch.name,
        value: `${ch.views} views`,
    }));

    return (
        <WrappedCard theme="purple">
            <CircleShape className="w-40 h-40 -bottom-20 -right-20" color="bg-[#FFDD00]" />

            <WrappedCardHeader logo={<Flame className="w-6 h-6" />} label="Your Favorites" />

            <WrappedCardContent position="start" className="pt-6">
                <WrappedHeading size="3xl" className="mb-6">
                    Top 5 channels
                </WrappedHeading>

                <WrappedRankingList items={items} />
            </WrappedCardContent>
        </WrappedCard>
    );
}

// ============================================
// SECTION 4: YOUR RHYTHM
// ============================================

interface WatchCycleCardProps {
    peakHour: number;
    hourlyData?: number[]; // 24 values
}

export function WatchCycleCard({ peakHour, hourlyData = [] }: WatchCycleCardProps) {
    const formatHour = (h: number) => {
        if (h === 0) return '12 AM';
        if (h === 12) return '12 PM';
        return h > 12 ? `${h - 12} PM` : `${h} AM`;
    };

    // Generate 24 hour segments
    const hours = Array.from({ length: 24 }, (_, i) => i);

    // Normalize hourly data for visualization
    const maxVal = hourlyData.length > 0 ? Math.max(...hourlyData, 1) : 1;
    const normalizedData = hourlyData.length === 24
        ? hourlyData.map(v => v / maxVal)
        : hours.map(() => 0.3); // placeholder if no data

    return (
        <WrappedCard theme="navy">
            <WrappedCardHeader logo={<Clock className="w-6 h-6" />} label="Your Rhythm" />

            <WrappedCardContent>
                <WrappedHeading size="2xl" className="mb-4 text-center">
                    Your 24-hour watch cycle
                </WrappedHeading>

                {/* Polar Activity Chart */}
                <div className="relative w-52 h-52 mx-auto mb-4">
                    {/* Background rings */}
                    <div className="absolute inset-0 rounded-full border border-white/10" />
                    <div className="absolute inset-[20%] rounded-full border border-white/10" />
                    <div className="absolute inset-[40%] rounded-full border border-white/10" />

                    {/* Hour segments */}
                    <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100">
                        {hours.map((hour) => {
                            const intensity = normalizedData[hour];
                            const angle = (hour * 15) - 90; // 15 degrees per hour, starting at top
                            const angleRad = (angle * Math.PI) / 180;
                            const nextAngleRad = ((angle + 14) * Math.PI) / 180;

                            // Inner and outer radius based on intensity
                            const innerRadius = 20;
                            const outerRadius = 20 + (intensity * 28);

                            // Calculate path points
                            const x1 = 50 + innerRadius * Math.cos(angleRad);
                            const y1 = 50 + innerRadius * Math.sin(angleRad);
                            const x2 = 50 + outerRadius * Math.cos(angleRad);
                            const y2 = 50 + outerRadius * Math.sin(angleRad);
                            const x3 = 50 + outerRadius * Math.cos(nextAngleRad);
                            const y3 = 50 + outerRadius * Math.sin(nextAngleRad);
                            const x4 = 50 + innerRadius * Math.cos(nextAngleRad);
                            const y4 = 50 + innerRadius * Math.sin(nextAngleRad);

                            const isPeak = hour === peakHour;
                            const isActive = normalizedData[hour] > 0.5;

                            return (
                                <path
                                    key={hour}
                                    d={`M ${x1} ${y1} L ${x2} ${y2} L ${x3} ${y3} L ${x4} ${y4} Z`}
                                    fill={isPeak ? '#FF6B6B' : isActive ? '#6B5ACD' : '#ffffff'}
                                    opacity={isPeak ? 1 : 0.2 + (intensity * 0.6)}
                                    stroke="rgba(255,255,255,0.1)"
                                    strokeWidth="0.3"
                                />
                            );
                        })}
                    </svg>

                    {/* Center circle with peak hour */}
                    <div className="absolute inset-[35%] rounded-full bg-[#1A1A2E] flex items-center justify-center">
                        <div className="text-center">
                            <div className="text-lg font-black">{formatHour(peakHour)}</div>
                            <div className="text-[8px] opacity-70">PEAK</div>
                        </div>
                    </div>

                    {/* Hour labels */}
                    <div className="absolute top-1 left-1/2 -translate-x-1/2 text-[8px] opacity-50">12A</div>
                    <div className="absolute right-1 top-1/2 -translate-y-1/2 text-[8px] opacity-50">6A</div>
                    <div className="absolute bottom-1 left-1/2 -translate-x-1/2 text-[8px] opacity-50">12P</div>
                    <div className="absolute left-1 top-1/2 -translate-y-1/2 text-[8px] opacity-50">6P</div>
                </div>
            </WrappedCardContent>

            <WrappedCardFooter className="text-center">
                <WrappedSubtitle>
                    You&apos;re most active around {formatHour(peakHour)}
                </WrappedSubtitle>
            </WrappedCardFooter>
        </WrappedCard>
    );
}

interface DayOfWeekCardProps {
    peakDay: string;
    dailyData?: Record<string, number>;
}

export function DayOfWeekCard({ peakDay }: DayOfWeekCardProps) {
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

    return (
        <WrappedCard theme="purple">
            <CircleShape className="w-32 h-32 -top-16 -right-16" color="bg-[#FFDD00]/50" />

            <WrappedCardHeader logo={<Calendar className="w-6 h-6" />} label="Weekly Pattern" />

            <WrappedCardContent>
                <WrappedHeading size="4xl" className="mb-2">
                    {peakDay}s
                </WrappedHeading>

                <WrappedSubtitle className="mb-8">
                    are your YouTube day
                </WrappedSubtitle>

                {/* Simple day indicators */}
                <div className="flex justify-between px-4">
                    {days.map((day) => (
                        <div
                            key={day}
                            className={`text-center px-2 py-1 rounded ${day.startsWith(peakDay.slice(0, 3))
                                ? 'bg-[#FFDD00] text-gray-900 font-bold'
                                : 'opacity-50'
                                }`}
                        >
                            {day}
                        </div>
                    ))}
                </div>
            </WrappedCardContent>
        </WrappedCard>
    );
}

interface LongestStreakCardProps {
    streakDays: number;
    streakDates?: string;
}

export function LongestStreakCard({ streakDays, streakDates }: LongestStreakCardProps) {
    return (
        <WrappedCard theme="gradient1">
            <CircleShape className="w-40 h-40 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 opacity-20" color="bg-white" />

            <WrappedCardHeader logo={<Flame className="w-6 h-6" />} label="Consistency" />

            <WrappedCardContent>
                <WrappedHeading size="2xl" className="mb-4">
                    Your longest streak
                </WrappedHeading>

                <WrappedBigNumber value={streakDays} suffix="days" />

                <WrappedSubtitle className="text-center mt-4">
                    in a row!
                </WrappedSubtitle>

                {streakDates && (
                    <div className="mt-6 text-center">
                        <WrappedBadge variant="outline">{streakDates}</WrappedBadge>
                    </div>
                )}
            </WrappedCardContent>
        </WrappedCard>
    );
}

// ============================================
// SECTION 5: PERSONALIZATION
// ============================================

interface PersonalityCardProps {
    personalityType: string;
    description: string;
}

export function PersonalityCard({
    personalityType = "Curious Mind",
    description = "You dive deep into diverse topics"
}: PersonalityCardProps) {
    return (
        <WrappedCard theme="gradient2">
            <CircleShape className="w-48 h-48 -top-24 -left-24" color="bg-white/10" />
            <CircleShape className="w-32 h-32 -bottom-16 -right-16" color="bg-white/10" />

            <WrappedCardHeader logo={<Sparkles className="w-6 h-6" />} label="Your Personality" />

            <WrappedCardContent>
                <WrappedHeading size="2xl" className="mb-4">
                    You&apos;re a
                </WrappedHeading>

                <WrappedHeading size="4xl" className="mb-6">
                    {personalityType}
                </WrappedHeading>

                <WrappedSubtitle className="text-center">
                    {description}
                </WrappedSubtitle>
            </WrappedCardContent>
        </WrappedCard>
    );
}

// ============================================
// SECTION 6: DEEP DIVES
// ============================================

interface BingeSessionsCardProps {
    totalBinges: number;
    longestDuration: string;
    longestDate: string;
}

export function BingeSessionsCard({ totalBinges, longestDuration, longestDate }: BingeSessionsCardProps) {
    return (
        <WrappedCard theme="navy">
            <GridPattern className="inset-0 w-full h-full opacity-10" />

            <WrappedCardHeader logo={<Play className="w-6 h-6" />} label="Binge Sessions" />

            <WrappedCardContent>
                <WrappedHeading size="3xl" className="mb-6">
                    {totalBinges} binge sessions
                </WrappedHeading>

                <div className="space-y-4">
                    <div className="p-4 bg-white/10 rounded-xl">
                        <div className="text-sm opacity-70 mb-1">Your longest</div>
                        <div className="text-2xl font-bold">{longestDuration}</div>
                    </div>

                    <WrappedSubtitle className="text-center">
                        on {longestDate}
                    </WrappedSubtitle>
                </div>
            </WrappedCardContent>
        </WrappedCard>
    );
}

interface LateNightCardProps {
    lateNightVideos: number;
    latestWatch: string;
    latestWatchDate: string;
}

export function LateNightCard({ lateNightVideos, latestWatch, latestWatchDate }: LateNightCardProps) {
    return (
        <WrappedCard theme="navy">
            <CircleShape className="w-24 h-24 top-20 right-8 opacity-30" color="bg-[#6B5ACD]" />

            <WrappedCardHeader logo={<Moon className="w-6 h-6" />} label="Night Owl" />

            <WrappedCardContent>
                <WrappedHeading size="3xl" className="mb-4">
                    {lateNightVideos} videos
                </WrappedHeading>

                <WrappedSubtitle className="mb-8">
                    watched after midnight
                </WrappedSubtitle>

                <div className="p-4 bg-white/10 rounded-xl text-center">
                    <div className="text-sm opacity-70 mb-1">Latest watch</div>
                    <div className="text-xl font-bold">{latestWatch}</div>
                    <div className="text-sm opacity-70">on {latestWatchDate}</div>
                </div>
            </WrappedCardContent>
        </WrappedCard>
    );
}

interface HabitsCardProps {
    totalHabitChannels: number;
    strongestHabit: { channel: string; frequency: string };
    topHabits?: { channel: string; frequency: string }[];
}

export function HabitsCard({ totalHabitChannels, strongestHabit }: HabitsCardProps) {
    return (
        <WrappedCard theme="coral">
            <CircleShape className="w-32 h-32 -bottom-16 -left-16" color="bg-[#2D1B4E]" />

            <WrappedCardHeader logo={<Repeat className="w-6 h-6" />} label="Your Habits" />

            <WrappedCardContent>
                <WrappedHeading size="3xl" className="mb-6">
                    {totalHabitChannels} channels
                </WrappedHeading>

                <WrappedSubtitle className="mb-8">
                    you watch regularly
                </WrappedSubtitle>

                <div className="p-4 bg-white/20 rounded-xl">
                    <div className="text-sm opacity-80 mb-2">Strongest habit</div>
                    <div className="text-lg font-bold">{strongestHabit.channel}</div>
                    <div className="text-sm opacity-80">every {strongestHabit.frequency}</div>
                </div>
            </WrappedCardContent>
        </WrappedCard>
    );
}

interface RewatchedCardProps {
    rewatchedCount: number;
    topRewatched: string;
    rewatchTimes: number;
}

export function RewatchedCard({ rewatchedCount, topRewatched, rewatchTimes }: RewatchedCardProps) {
    return (
        <WrappedCard theme="purple">
            <WrappedCardHeader logo={<Repeat className="w-6 h-6" />} label="Comfort Content" />

            <WrappedCardContent>
                <WrappedHeading size="3xl" className="mb-4">
                    {rewatchedCount} videos
                </WrappedHeading>

                <WrappedSubtitle className="mb-8">
                    you rewatched this year
                </WrappedSubtitle>

                <div className="p-4 bg-white/10 rounded-xl">
                    <div className="text-sm opacity-70 mb-2">Most rewatched</div>
                    <div className="text-sm font-bold line-clamp-2">{topRewatched}</div>
                    <WrappedBadge variant="outline" className="mt-2">
                        Watched {rewatchTimes} times
                    </WrappedBadge>
                </div>
            </WrappedCardContent>
        </WrappedCard>
    );
}

interface SubscriptionCardProps {
    totalSubscriptions: number;
    watchedSubscribed: number;
    overlapPercentage: number;
    ghostSubscriptions: number;
}

export function SubscriptionCard({
    totalSubscriptions,
    watchedSubscribed,
    overlapPercentage,
    ghostSubscriptions
}: SubscriptionCardProps) {
    return (
        <WrappedCard theme="teal">
            <WrappedCardHeader logo={<Bell className="w-6 h-6" />} label="Subscriptions" />

            <WrappedCardContent>
                <WrappedHeading size="4xl" className="mb-2">
                    {totalSubscriptions}
                </WrappedHeading>

                <WrappedSubtitle className="mb-6">
                    channels subscribed
                </WrappedSubtitle>

                <div className="space-y-3">
                    <div className="flex justify-between p-3 bg-white/10 rounded-lg">
                        <span>Actually watched</span>
                        <span className="font-bold">{watchedSubscribed}</span>
                    </div>
                    <div className="flex justify-between p-3 bg-white/10 rounded-lg">
                        <span>Engagement rate</span>
                        <span className="font-bold">{overlapPercentage}%</span>
                    </div>
                    <div className="flex justify-between p-3 bg-[#FF6B6B]/20 rounded-lg text-[#FF6B6B]">
                        <span>Ghost subscriptions</span>
                        <span className="font-bold">{ghostSubscriptions}</span>
                    </div>
                </div>
            </WrappedCardContent>
        </WrappedCard>
    );
}

interface SearchInsightsCardProps {
    totalSearches: number;
    topSearch: string;
    topSearches?: string[];
}

export function SearchInsightsCard({ totalSearches, topSearch }: SearchInsightsCardProps) {
    return (
        <WrappedCard theme="yellow">
            <CircleShape className="w-32 h-32 -bottom-16 -right-16" color="bg-[#6B5ACD]" />

            <WrappedCardHeader logo={<Search className="w-6 h-6" />} label="Search Insights" />

            <WrappedCardContent>
                <WrappedHeading size="3xl" className="mb-4">
                    {totalSearches} searches
                </WrappedHeading>

                <WrappedSubtitle className="mb-8">
                    this year
                </WrappedSubtitle>

                <div className="p-4 bg-gray-900/10 rounded-xl">
                    <div className="text-sm opacity-70 mb-2">Most searched</div>
                    <div className="text-lg font-bold">&quot;{topSearch}&quot;</div>
                </div>
            </WrappedCardContent>
        </WrappedCard>
    );
}

interface FirstLastVideoCardProps {
    firstVideoTitle: string;
    firstVideoDate: string;
    lastVideoTitle: string;
    lastVideoDate: string;
}

export function FirstLastVideoCard({
    firstVideoTitle,
    firstVideoDate,
    lastVideoTitle,
    lastVideoDate
}: FirstLastVideoCardProps) {
    return (
        <WrappedCard theme="gradient2">
            <WrappedCardHeader logo={<Play className="w-6 h-6" />} label="Bookends" />

            <WrappedCardContent>
                <WrappedHeading size="2xl" className="mb-6 text-center">
                    Your year in videos
                </WrappedHeading>

                <div className="space-y-4">
                    <div className="p-4 bg-white/10 rounded-xl">
                        <div className="text-xs opacity-70 mb-1">Started with</div>
                        <div className="text-sm font-bold line-clamp-2">{firstVideoTitle}</div>
                        <div className="text-xs opacity-70 mt-1">{firstVideoDate}</div>
                    </div>

                    <div className="text-center opacity-50">↓</div>

                    <div className="p-4 bg-white/10 rounded-xl">
                        <div className="text-xs opacity-70 mb-1">Ended with</div>
                        <div className="text-sm font-bold line-clamp-2">{lastVideoTitle}</div>
                        <div className="text-xs opacity-70 mt-1">{lastVideoDate}</div>
                    </div>
                </div>
            </WrappedCardContent>
        </WrappedCard>
    );
}

// ============================================
// PATTERNS CARD (Association Rule Mining)
// ============================================

interface PatternsCardProps {
    totalPatterns: number;
    insights: string[];
}

export function PatternsCard({ totalPatterns, insights }: PatternsCardProps) {
    // Parse markdown-style bold text
    const parseInsight = (text: string) => {
        const parts = text.split(/\*\*(.*?)\*\*/g);
        return parts.map((part, i) =>
            i % 2 === 1 ? <strong key={i} className="text-[#FFDD00]">{part}</strong> : part
        );
    };

    return (
        <WrappedCard theme="gradient2">
            <CircleShape className="w-32 h-32 -top-16 -right-16" color="bg-[#FFDD00]/30" />
            <GridPattern className="inset-0 w-full h-full opacity-10" />

            <WrappedCardHeader logo={<Zap className="w-6 h-6" />} label="Your Patterns" />

            <WrappedCardContent position="start" className="pt-4">
                <WrappedHeading size="2xl" className="mb-2 text-center">
                    We found {totalPatterns} patterns
                </WrappedHeading>

                <WrappedSubtitle className="mb-6 text-center">
                    in your viewing behavior
                </WrappedSubtitle>

                <div className="space-y-3">
                    {insights.slice(0, 4).map((insight, i) => (
                        <div
                            key={i}
                            className="p-3 bg-white/10 rounded-xl text-sm flex items-start gap-3"
                        >
                            <span className="text-[#FFDD00] text-lg">💡</span>
                            <span>{parseInsight(insight)}</span>
                        </div>
                    ))}

                    {insights.length === 0 && (
                        <div className="text-center text-sm opacity-70 py-4">
                            Not enough data to detect patterns yet
                        </div>
                    )}
                </div>
            </WrappedCardContent>
        </WrappedCard>
    );
}

// ============================================
// SECTION 7: OUTRO
// ============================================

interface OutroCardProps {
    year?: number;
}

export function OutroCard({ year = 2025 }: OutroCardProps) {
    return (
        <WrappedCard theme="gradient1">
            <CircleShape className="w-48 h-48 -top-24 -right-24" color="bg-white/20" />
            <CircleShape className="w-32 h-32 -bottom-16 -left-16" color="bg-white/20" />

            <WrappedCardHeader logo={<Heart className="w-6 h-6" />} label="That's a wrap!" />

            <WrappedCardContent>
                <WrappedHeading size="4xl" className="mb-6 text-center">
                    That&apos;s your {year}!
                </WrappedHeading>

                <WrappedSubtitle className="text-center mb-8">
                    Thanks for spending your year with YouTube
                </WrappedSubtitle>
            </WrappedCardContent>

            <WrappedCardFooter className="text-center">
                <button className="flex items-center gap-2 mx-auto px-6 py-3 bg-white text-gray-900 rounded-full font-bold hover:scale-105 transition-transform">
                    <Share2 className="w-5 h-5" />
                    Share your Wrapped
                </button>
            </WrappedCardFooter>
        </WrappedCard>
    );
}
