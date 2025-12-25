'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
    Search,
    Eye,
    Users,
    Youtube,
    Clock,
    TrendingUp,
    BarChart3,
    Loader2,
    ArrowLeft,
    AlertTriangle,
    Moon,
    Calendar,
    Sun,
    Zap,
    Repeat,
    Flame,
    Activity,
    Timer,
    Layers
} from 'lucide-react';
import Link from 'next/link';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ChannelData {
    channel: string;
    channel_clean: string;
    count: number;
    percentage: number;
}

interface SearchData {
    term: string;
    term_clean: string;
    count: number;
}

interface AnalyticsData {
    summary: {
        total_events: number;
        total_watch: number;
        total_search: number;
        total_subscribe: number;
        unique_channels: number;
        date_range: { first: string | null; last: string | null };
        language_breakdown: { hindi?: number; hinglish?: number; english?: number; unknown?: number };
    };
    channels: {
        total_unique_channels: number;
        total_count: number;
        engagement_filter: string;
        top_channels: ChannelData[];
        other_count: number;
        view_distribution: { bucket: string; count: number }[];
        engagement_summary: { total_watch: number; total_view: number; total_all: number };
    };
    watch_patterns: {
        hourly_distribution: { hour: number; count: number }[];
        daily_distribution: { day: number; count: number }[];
        peak_hour: number | null;
        peak_hour_count: number;
        peak_day: string | null;
        peak_day_count: number;
        // New fields
        weekly_peak_days: { year: number; week: number; peak_day: string; peak_day_num: number; count: number }[];
        overall_peak_day: string | null;
        overall_peak_wins: number;
        total_weeks: number;
        time_intervals: { interval: string; count: number; hours: string }[];
        peak_interval: string | null;
        circular_activity: { hour: number; label: string; count: number; percentage: number }[];
    };
    searches: {
        total_searches: number;
        unique_searches: number;
        top_searches: SearchData[];
        language_breakdown: { hindi?: number; hinglish?: number; english?: number; unknown?: number };
    };
    subscription_overlap: {
        total_subscriptions: number;
        total_watched_channels: number;
        subscribed_and_watched: { count: number; percentage: number; channels: string[] };
        watched_not_subscribed: { count: number; channels: string[] };
        subscribed_not_watched: { count: number; channels: string[] };
    };
    behavior_anomalies?: {
        baseline: {
            avg_daily_watches: number;
            std_dev: number;
            late_night_baseline_pct: number;
            total_days: number;
        };
        anomalies: { type: string; date: string; description: string; severity: string }[];
        late_night_sessions: { date: string; late_night_count: number; total_count: number; peak_hour: number | null }[];
        binge_days: { date: string; count: number; above_average_by: number; multiplier: number }[];
        unusual_weeks: { year: number; week: number; late_night_count: number; late_night_percentage: number; baseline_percentage: number; total_watches: number }[];
        // New fields
        binge_watching_periods: { start_date: string; end_date: string; duration_days: number; total_videos: number; avg_per_day: number }[];
        late_night_moods: { start_date: string; end_date: string; duration_days: number; total_late_videos: number }[];
        patterns: {
            weekend_warrior: boolean;
            weekend_pct: number;
            chronotype: string;
            night_watches: number;
            morning_watches: number;
            inactive_periods: { start: string; end: string; gap_days: number }[];
        };
    };
    habit_formation?: {
        channel_habits: {
            channel: string;
            total_days_watched: number;
            habit_streaks: { start: string; end: string; days: number }[];
            longest_streak: number;
            total_habit_days: number;
            habit_score: number;
        }[];
        content_habits: {
            topic: string;
            total_days: number;
            habit_streaks: { start: string; end: string; days: number }[];
            longest_streak: number;
            total_habit_days: number;
        }[];
        video_habits: {
            title: string;
            channel: string;
            days_watched: number;
            total_watches: number;
            first_seen: string;
            has_streak: boolean;
            longest_streak: number;
        }[];
        habit_strength: number;
        total_channels_with_habits: number;
        total_videos_rewatched: number;
        total_topics_with_habits: number;
        max_streak_days: number;
        summary: string;
    };
    temporal_trends?: {
        monthly_stats: {
            month: string;
            month_label: string;
            total_watches: number;
            peak_hour: number | null;
            peak_hour_label: string;
            peak_hour_count: number;
            peak_day: number | null;
            peak_day_name: string | null;
            peak_day_count: number;
        }[];
        pattern_shifts: {
            type: string;
            from_month: string;
            to_month: string;
            from_value: string;
            to_value: string;
            description: string;
        }[];
        activity_trend: {
            month: string;
            month_label: string;
            watches: number;
        }[];
        total_months: number;
        summary: string;
    };
    time_spent?: {
        total_minutes: number;
        total_hours: number;
        average_daily_minutes: number;
        total_days: number;
        sessions: {
            total_count: number;
            average_duration_minutes: number;
            longest_session_minutes: number;
        };
        summary: string;
    };
    channel_distribution?: {
        bin_distribution: {
            bin: string;
            channel_count: number;
            video_count: number;
        }[];
        temporal_by_bin: {
            month: string;
            bins: Record<string, number>;
        }[];
        stats: {
            total_channels: number;
            total_videos: number;
            single_view_channels: number;
            single_view_percentage: number;
        };
    };
}

export default function AnalyticsPage() {
    const [token, setToken] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [data, setData] = useState<AnalyticsData | null>(null);
    const [engagementFilter, setEngagementFilter] = useState<'all' | 'watch' | 'view'>('all');
    const [channelLoading, setChannelLoading] = useState(false);

    // Store original engagement summary so it persists when switching filters
    const [originalEngagementSummary, setOriginalEngagementSummary] = useState<{
        total_watch: number;
        total_view: number;
        total_all: number;
    } | null>(null);

    const loadAnalytics = async () => {
        if (!token.trim()) return;

        setLoading(true);
        setError(null);
        setEngagementFilter('all'); // Reset filter when loading new data

        try {
            const response = await fetch(`${API_BASE_URL}/api/analytics/${token}/full`);
            if (!response.ok) {
                throw new Error('Session not found');
            }
            const result = await response.json();
            setData(result);
            // Store original engagement summary
            setOriginalEngagementSummary(result.channels?.engagement_summary || null);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load analytics');
        } finally {
            setLoading(false);
        }
    };

    const loadChannelData = async (filter: 'all' | 'watch' | 'view') => {
        if (!token.trim() || !data) return;

        setChannelLoading(true);
        setEngagementFilter(filter);

        try {
            const response = await fetch(`${API_BASE_URL}/api/analytics/${token}/channels?engagement=${filter}`);
            if (response.ok) {
                const channelData = await response.json();
                // Use the stored original engagement summary
                setData(prev => prev ? {
                    ...prev,
                    channels: {
                        ...channelData,
                        engagement_summary: originalEngagementSummary || channelData.engagement_summary
                    }
                } : null);
            }
        } finally {
            setChannelLoading(false);
        }
    };

    const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

    return (
        <div className="min-h-screen bg-background p-6">
            <div className="max-w-7xl mx-auto space-y-6">
                {/* Header */}
                <div className="flex items-center gap-4">
                    <Link href="/admin/debug">
                        <Button variant="ghost" size="icon">
                            <ArrowLeft className="w-5 h-5" />
                        </Button>
                    </Link>
                    <div>
                        <h1 className="text-3xl font-bold">Session Analytics</h1>
                        <p className="text-muted-foreground">Analyze your YouTube data</p>
                    </div>
                </div>

                {/* Token Input */}
                <Card>
                    <CardContent className="p-4">
                        <div className="flex gap-3">
                            <Input
                                placeholder="Enter session token..."
                                value={token}
                                onChange={(e) => setToken(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && loadAnalytics()}
                                className="flex-1"
                            />
                            <Button onClick={loadAnalytics} disabled={loading || !token.trim()}>
                                {loading ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                    <Search className="w-4 h-4" />
                                )}
                                <span className="ml-2">Analyze</span>
                            </Button>
                        </div>
                        {error && (
                            <p className="text-destructive text-sm mt-2">{error}</p>
                        )}
                    </CardContent>
                </Card>

                {data && (
                    <>
                        {/* Summary Cards */}
                        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                            <Card>
                                <CardContent className="p-4 text-center">
                                    <Eye className="w-8 h-8 mx-auto mb-2 text-blue-500" />
                                    <p className="text-2xl font-bold">{data.summary.total_watch.toLocaleString()}</p>
                                    <p className="text-xs text-muted-foreground">Videos Watched</p>
                                </CardContent>
                            </Card>
                            <Card>
                                <CardContent className="p-4 text-center">
                                    <Youtube className="w-8 h-8 mx-auto mb-2 text-red-500" />
                                    <p className="text-2xl font-bold">{data.summary.unique_channels.toLocaleString()}</p>
                                    <p className="text-xs text-muted-foreground">Unique Channels</p>
                                </CardContent>
                            </Card>
                            <Card>
                                <CardContent className="p-4 text-center">
                                    <Search className="w-8 h-8 mx-auto mb-2 text-green-500" />
                                    <p className="text-2xl font-bold">{data.summary.total_search.toLocaleString()}</p>
                                    <p className="text-xs text-muted-foreground">Searches</p>
                                </CardContent>
                            </Card>
                            <Card>
                                <CardContent className="p-4 text-center">
                                    <Users className="w-8 h-8 mx-auto mb-2 text-purple-500" />
                                    <p className="text-2xl font-bold">{data.summary.total_subscribe.toLocaleString()}</p>
                                    <p className="text-xs text-muted-foreground">Subscriptions</p>
                                </CardContent>
                            </Card>
                            <Card>
                                <CardContent className="p-4 text-center">
                                    <Clock className="w-8 h-8 mx-auto mb-2 text-orange-500" />
                                    <p className="text-2xl font-bold">{data.watch_patterns.peak_hour ?? '-'}:00</p>
                                    <p className="text-xs text-muted-foreground">Peak Hour</p>
                                </CardContent>
                            </Card>
                        </div>

                        {/* Time Spent Card */}
                        {data.time_spent && (
                            <Card className="bg-gradient-to-br from-indigo-500/10 to-purple-500/10 border-indigo-500/20">
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-lg flex items-center gap-2">
                                        <Timer className="w-5 h-5 text-indigo-500" />
                                        Time Spent on YouTube
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                                        <div className="text-center p-3 bg-background/50 rounded-lg">
                                            <p className="text-3xl font-bold text-indigo-500">
                                                {data.time_spent.total_hours >= 24
                                                    ? `${Math.floor(data.time_spent.total_hours / 24)}d ${Math.round(data.time_spent.total_hours % 24)}h`
                                                    : `${data.time_spent.total_hours}h`
                                                }
                                            </p>
                                            <p className="text-xs text-muted-foreground">Total Time</p>
                                            <p className="text-xs text-indigo-400 mt-0.5">
                                                ({Math.round(data.time_spent.total_minutes).toLocaleString()} min)
                                            </p>
                                        </div>
                                        <div className="text-center p-3 bg-background/50 rounded-lg">
                                            <p className="text-3xl font-bold text-purple-500">
                                                {Math.round(data.time_spent.average_daily_minutes)}
                                            </p>
                                            <p className="text-xs text-muted-foreground">Min/Day Avg</p>
                                        </div>
                                        <div className="text-center p-3 bg-background/50 rounded-lg">
                                            <p className="text-3xl font-bold text-blue-500">
                                                {data.time_spent.total_days}
                                            </p>
                                            <p className="text-xs text-muted-foreground">Active Days</p>
                                        </div>
                                        <div className="text-center p-3 bg-background/50 rounded-lg">
                                            <p className="text-3xl font-bold text-cyan-500">
                                                {data.time_spent.sessions.total_count}
                                            </p>
                                            <p className="text-xs text-muted-foreground">Sessions</p>
                                        </div>
                                        <div className="text-center p-3 bg-background/50 rounded-lg">
                                            <p className="text-3xl font-bold text-teal-500">
                                                {Math.round(data.time_spent.sessions.longest_session_minutes)}m
                                            </p>
                                            <p className="text-xs text-muted-foreground">Longest Session</p>
                                        </div>
                                    </div>
                                    <p className="text-sm text-muted-foreground text-center mt-4">
                                        {data.time_spent.summary}
                                    </p>
                                </CardContent>
                            </Card>
                        )}

                        {/* Language Breakdown */}
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-lg flex items-center gap-2">
                                    <BarChart3 className="w-5 h-5" />
                                    Language Breakdown
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="grid grid-cols-4 gap-4 text-center">
                                    <div>
                                        <p className="text-2xl font-bold text-orange-500">
                                            {data.summary.language_breakdown.hindi || 0}
                                        </p>
                                        <p className="text-sm text-muted-foreground">Hindi</p>
                                    </div>
                                    <div>
                                        <p className="text-2xl font-bold text-yellow-500">
                                            {data.summary.language_breakdown.hinglish || 0}
                                        </p>
                                        <p className="text-sm text-muted-foreground">Hinglish</p>
                                    </div>
                                    <div>
                                        <p className="text-2xl font-bold text-blue-500">
                                            {data.summary.language_breakdown.english || 0}
                                        </p>
                                        <p className="text-sm text-muted-foreground">English</p>
                                    </div>
                                    <div>
                                        <p className="text-2xl font-bold text-gray-500">
                                            {data.summary.language_breakdown.unknown || 0}
                                        </p>
                                        <p className="text-sm text-muted-foreground">Unknown</p>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Channel View Distribution Histogram */}
                        <Card>
                            <CardHeader>
                                <div className="flex items-center justify-between">
                                    <CardTitle className="text-lg flex items-center gap-2">
                                        <BarChart3 className="w-5 h-5" />
                                        Channel Distribution by Count
                                    </CardTitle>
                                    {/* Toggle for Watch/View/All */}
                                    <div className="flex gap-1 bg-muted rounded-lg p-1">
                                        <Button
                                            size="sm"
                                            variant={engagementFilter === 'all' ? 'default' : 'ghost'}
                                            onClick={() => loadChannelData('all')}
                                            disabled={channelLoading}
                                            className="text-xs h-7"
                                        >
                                            All ({data.channels.engagement_summary?.total_all || 0})
                                        </Button>
                                        <Button
                                            size="sm"
                                            variant={engagementFilter === 'watch' ? 'default' : 'ghost'}
                                            onClick={() => loadChannelData('watch')}
                                            disabled={channelLoading}
                                            className="text-xs h-7"
                                        >
                                            Watch ({data.channels.engagement_summary?.total_watch || 0})
                                        </Button>
                                        <Button
                                            size="sm"
                                            variant={engagementFilter === 'view' ? 'default' : 'ghost'}
                                            onClick={() => loadChannelData('view')}
                                            disabled={channelLoading}
                                            className="text-xs h-7"
                                        >
                                            View ({data.channels.engagement_summary?.total_view || 0})
                                        </Button>
                                    </div>
                                </div>
                                <p className="text-xs text-muted-foreground mt-1">
                                    Watch = actively watched | View = passively viewed
                                </p>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-3">
                                    {data.channels.view_distribution?.map((bucket) => {
                                        const max = Math.max(...(data.channels.view_distribution?.map(b => b.count) || [1]));
                                        const width = max > 0 ? (bucket.count / max) * 100 : 0;
                                        return (
                                            <div key={bucket.bucket} className="flex items-center gap-3">
                                                <span className="w-16 text-sm text-muted-foreground text-right">
                                                    {bucket.bucket}
                                                </span>
                                                <div className="flex-1 h-8 bg-muted/30 rounded-lg overflow-hidden">
                                                    <div
                                                        className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg flex items-center justify-end pr-2"
                                                        style={{ width: `${Math.max(width, 2)}%` }}
                                                    >
                                                        {width > 15 && (
                                                            <span className="text-xs font-medium text-white">
                                                                {bucket.count}
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                                {width <= 15 && (
                                                    <span className="text-sm font-medium w-12">
                                                        {bucket.count}
                                                    </span>
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                                <p className="text-xs text-muted-foreground mt-4">
                                    Shows how many channels fall into each view count range
                                </p>
                            </CardContent>
                        </Card>

                        <div className="grid md:grid-cols-2 gap-6">
                            {/* Top Channels */}
                            <Card>
                                <CardHeader>
                                    <CardTitle className="text-lg flex items-center gap-2">
                                        <TrendingUp className="w-5 h-5" />
                                        Top Channels
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <ScrollArea className="h-80">
                                        <div className="space-y-2">
                                            {data.channels.top_channels.map((channel, idx) => (
                                                <div
                                                    key={channel.channel_clean}
                                                    className="flex items-center justify-between p-2 rounded-lg bg-muted/30"
                                                >
                                                    <div className="flex items-center gap-3">
                                                        <span className="text-muted-foreground w-6 text-right">
                                                            {idx + 1}.
                                                        </span>
                                                        <span className="truncate max-w-[200px]">{channel.channel}</span>
                                                    </div>
                                                    <div className="flex items-center gap-2">
                                                        <Badge variant="secondary">{channel.count}</Badge>
                                                        <span className="text-xs text-muted-foreground w-12 text-right">
                                                            {channel.percentage}%
                                                        </span>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </ScrollArea>
                                </CardContent>
                            </Card>

                            {/* Watch Patterns */}
                            <Card>
                                <CardHeader>
                                    <CardTitle className="text-lg flex items-center gap-2">
                                        <Clock className="w-5 h-5" />
                                        Watch Patterns
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    {/* Hourly */}
                                    <div>
                                        <p className="text-sm font-medium mb-2">By Hour</p>
                                        <div className="flex gap-0.5 h-16">
                                            {data.watch_patterns.hourly_distribution.map((h) => {
                                                const max = Math.max(...data.watch_patterns.hourly_distribution.map(x => x.count));
                                                const height = max > 0 ? (h.count / max) * 100 : 0;
                                                return (
                                                    <div
                                                        key={h.hour}
                                                        className="flex-1 flex flex-col justify-end"
                                                        title={`${h.hour}:00 - ${h.count} watches`}
                                                    >
                                                        <div
                                                            className="bg-blue-500 rounded-t"
                                                            style={{ height: `${height}%` }}
                                                        />
                                                    </div>
                                                );
                                            })}
                                        </div>
                                        <div className="flex justify-between text-xs text-muted-foreground mt-1">
                                            <span>0:00</span>
                                            <span>12:00</span>
                                            <span>23:00</span>
                                        </div>
                                    </div>

                                    {/* Daily */}
                                    <div>
                                        <p className="text-sm font-medium mb-2">By Day</p>
                                        <div className="grid grid-cols-7 gap-2">
                                            {data.watch_patterns.daily_distribution.map((d, idx) => {
                                                const max = Math.max(...data.watch_patterns.daily_distribution.map(x => x.count));
                                                const intensity = max > 0 ? (d.count / max) : 0;
                                                return (
                                                    <div key={d.day} className="text-center">
                                                        <div
                                                            className="h-12 rounded flex items-center justify-center text-xs font-medium"
                                                            style={{
                                                                backgroundColor: `rgba(59, 130, 246, ${0.2 + intensity * 0.8})`
                                                            }}
                                                        >
                                                            {d.count}
                                                        </div>
                                                        <p className="text-xs text-muted-foreground mt-1">{dayNames[idx]}</p>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>

                                    <div className="flex gap-4 text-sm">
                                        <div>
                                            <span className="text-muted-foreground">Peak Day: </span>
                                            <span className="font-medium">{data.watch_patterns.peak_day || '-'}</span>
                                        </div>
                                        <div>
                                            <span className="text-muted-foreground">Peak Hour: </span>
                                            <span className="font-medium">{data.watch_patterns.peak_hour ?? '-'}:00</span>
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        </div>

                        {/* Time Intervals Card */}
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-lg flex items-center gap-2">
                                    <Clock className="w-5 h-5" />
                                    Watch Time Intervals
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    {data.watch_patterns.time_intervals?.map((interval) => {
                                        const isPeak = interval.interval === data.watch_patterns.peak_interval;
                                        return (
                                            <div
                                                key={interval.interval}
                                                className={`p-4 rounded-lg text-center ${isPeak ? 'bg-blue-500/20 ring-2 ring-blue-500' : 'bg-muted/30'}`}
                                            >
                                                <p className="text-2xl font-bold">{interval.count.toLocaleString()}</p>
                                                <p className="text-xs text-muted-foreground">{interval.interval}</p>
                                                {isPeak && <Badge className="mt-2" variant="default">Peak</Badge>}
                                            </div>
                                        );
                                    })}
                                </div>
                            </CardContent>
                        </Card>

                        {/* Circular Activity Chart */}
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-lg flex items-center gap-2">
                                    <BarChart3 className="w-5 h-5" />
                                    24-Hour Activity Clock
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="flex justify-center">
                                    <div className="relative w-80 h-80">
                                        {/* Clock circle */}
                                        <svg viewBox="0 0 200 200" className="w-full h-full">
                                            {/* Background circle */}
                                            <circle cx="100" cy="100" r="90" fill="none" stroke="currentColor" strokeWidth="1" className="text-muted/30" />
                                            <circle cx="100" cy="100" r="60" fill="none" stroke="currentColor" strokeWidth="1" className="text-muted/20" />
                                            <circle cx="100" cy="100" r="30" fill="none" stroke="currentColor" strokeWidth="1" className="text-muted/10" />

                                            {/* Activity segments */}
                                            {data.watch_patterns.circular_activity?.map((hour) => {
                                                const maxPercentage = Math.max(...(data.watch_patterns.circular_activity?.map(h => h.percentage) || [1]));
                                                const radius = 20 + (hour.percentage / maxPercentage) * 70;
                                                const angle = (hour.hour * 15 - 90) * (Math.PI / 180); // 15 degrees per hour, start at top
                                                const x1 = 100 + Math.cos(angle) * 15;
                                                const y1 = 100 + Math.sin(angle) * 15;
                                                const x2 = 100 + Math.cos(angle) * radius;
                                                const y2 = 100 + Math.sin(angle) * radius;

                                                // Color based on intensity
                                                const intensity = hour.percentage / maxPercentage;
                                                const hue = 200 + intensity * 60; // Blue to purple

                                                return (
                                                    <line
                                                        key={hour.hour}
                                                        x1={x1}
                                                        y1={y1}
                                                        x2={x2}
                                                        y2={y2}
                                                        stroke={`hsl(${hue}, 70%, ${50 + intensity * 20}%)`}
                                                        strokeWidth="6"
                                                        strokeLinecap="round"
                                                    >
                                                        <title>{hour.label}: {hour.count} watches ({hour.percentage}%)</title>
                                                    </line>
                                                );
                                            })}

                                            {/* Hour labels */}
                                            {[0, 3, 6, 9, 12, 15, 18, 21].map((hour) => {
                                                const angle = (hour * 15 - 90) * (Math.PI / 180);
                                                const x = 100 + Math.cos(angle) * 95;
                                                const y = 100 + Math.sin(angle) * 95;
                                                const label = hour === 0 ? '12AM' : hour === 12 ? '12PM' : hour < 12 ? `${hour}AM` : `${hour - 12}PM`;
                                                return (
                                                    <text
                                                        key={hour}
                                                        x={x}
                                                        y={y}
                                                        textAnchor="middle"
                                                        dominantBaseline="middle"
                                                        className="text-[8px] fill-muted-foreground"
                                                    >
                                                        {label}
                                                    </text>
                                                );
                                            })}
                                        </svg>
                                    </div>
                                </div>
                                <p className="text-xs text-muted-foreground text-center mt-2">
                                    Bar length shows relative watch activity. Hover for details.
                                </p>
                            </CardContent>
                        </Card>

                        {/* Weekly Peak Day Analysis */}
                        {data.watch_patterns.weekly_peak_days && data.watch_patterns.weekly_peak_days.length > 0 && (
                            <Card>
                                <CardHeader>
                                    <CardTitle className="text-lg flex items-center gap-2">
                                        <TrendingUp className="w-5 h-5" />
                                        Weekly Peak Day Analysis
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div className="flex gap-4 items-center">
                                        <div className="p-4 bg-green-500/20 rounded-lg text-center flex-1">
                                            <p className="text-3xl font-bold text-green-500">
                                                {data.watch_patterns.overall_peak_day || '-'}
                                            </p>
                                            <p className="text-xs text-muted-foreground">Most Active Day Overall</p>
                                            <p className="text-xs text-green-500">
                                                Won {data.watch_patterns.overall_peak_wins} of {data.watch_patterns.total_weeks} weeks
                                            </p>
                                        </div>
                                    </div>

                                    <div>
                                        <p className="text-sm font-medium mb-2">Recent Weeks (Peak Day)</p>
                                        <div className="flex flex-wrap gap-2">
                                            {data.watch_patterns.weekly_peak_days.map((week) => (
                                                <div
                                                    key={`${week.year}-${week.week}`}
                                                    className="px-3 py-1 rounded-full bg-muted/30 text-xs"
                                                    title={`Week ${week.week}, ${week.year}: ${week.count} watches`}
                                                >
                                                    <span className="font-medium">{week.peak_day.slice(0, 3)}</span>
                                                    <span className="text-muted-foreground ml-1">({week.count})</span>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        )}

                        <div className="grid md:grid-cols-2 gap-6">
                        </div>

                        <div className="grid md:grid-cols-2 gap-6">
                            {/* Top Searches */}
                            <Card>
                                <CardHeader>
                                    <CardTitle className="text-lg flex items-center gap-2">
                                        <Search className="w-5 h-5" />
                                        Top Searches ({data.searches.total_searches})
                                    </CardTitle>
                                </CardHeader>
                                <CardContent>
                                    <ScrollArea className="h-64">
                                        <div className="space-y-2">
                                            {data.searches.top_searches.map((search, idx) => (
                                                <div
                                                    key={search.term_clean}
                                                    className="flex items-center justify-between p-2 rounded-lg bg-muted/30"
                                                >
                                                    <span className="truncate max-w-[250px]">{search.term}</span>
                                                    <Badge variant="outline">{search.count}</Badge>
                                                </div>
                                            ))}
                                        </div>
                                    </ScrollArea>
                                </CardContent>
                            </Card>

                            {/* Subscription Overlap */}
                            <Card>
                                <CardHeader>
                                    <CardTitle className="text-lg flex items-center gap-2">
                                        <Users className="w-5 h-5" />
                                        Subscription Analysis
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-4">
                                    <div className="grid grid-cols-2 gap-4 text-center">
                                        <div className="p-3 bg-green-500/20 rounded-lg">
                                            <p className="text-2xl font-bold text-green-500">
                                                {data.subscription_overlap.subscribed_and_watched.count}
                                            </p>
                                            <p className="text-xs text-muted-foreground">Subscribed & Watched</p>
                                            <p className="text-xs text-green-500">
                                                {data.subscription_overlap.subscribed_and_watched.percentage}% of subs
                                            </p>
                                        </div>
                                        <div className="p-3 bg-yellow-500/20 rounded-lg">
                                            <p className="text-2xl font-bold text-yellow-500">
                                                {data.subscription_overlap.watched_not_subscribed.count}
                                            </p>
                                            <p className="text-xs text-muted-foreground">Watched, Not Subscribed</p>
                                        </div>
                                    </div>
                                    <div className="p-3 bg-muted/30 rounded-lg">
                                        <p className="text-sm font-medium mb-2">Not Watching ({data.subscription_overlap.subscribed_not_watched.count})</p>
                                        <p className="text-xs text-muted-foreground">
                                            {data.subscription_overlap.subscribed_not_watched.channels.slice(0, 5).join(', ')}
                                            {data.subscription_overlap.subscribed_not_watched.count > 5 && '...'}
                                        </p>
                                    </div>
                                </CardContent>
                            </Card>
                        </div>

                        {/* Behavior Anomalies */}
                        {data.behavior_anomalies && (
                            <Card>
                                <CardHeader>
                                    <CardTitle className="text-lg flex items-center gap-2">
                                        <AlertTriangle className="w-5 h-5 text-yellow-500" />
                                        Behavior Anomalies
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-6">
                                    {/* Baseline Stats */}
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                                        <div className="p-3 bg-muted/30 rounded-lg">
                                            <p className="text-xl font-bold">{data.behavior_anomalies.baseline.avg_daily_watches}</p>
                                            <p className="text-xs text-muted-foreground">Avg Daily Watches</p>
                                        </div>
                                        <div className="p-3 bg-muted/30 rounded-lg">
                                            <p className="text-xl font-bold">±{data.behavior_anomalies.baseline.std_dev}</p>
                                            <p className="text-xs text-muted-foreground">Std Deviation</p>
                                        </div>
                                        <div className="p-3 bg-muted/30 rounded-lg">
                                            <p className="text-xl font-bold">{data.behavior_anomalies.baseline.late_night_baseline_pct}%</p>
                                            <p className="text-xs text-muted-foreground">Late Night Baseline</p>
                                        </div>
                                        <div className="p-3 bg-muted/30 rounded-lg">
                                            <p className="text-xl font-bold">{data.behavior_anomalies.baseline.total_days}</p>
                                            <p className="text-xs text-muted-foreground">Days Tracked</p>
                                        </div>
                                    </div>

                                    {/* Anomalies List */}
                                    {data.behavior_anomalies.anomalies.length > 0 && (
                                        <div>
                                            <p className="text-sm font-medium mb-3">Detected Anomalies</p>
                                            <div className="space-y-2">
                                                {data.behavior_anomalies.anomalies.map((anomaly, idx) => (
                                                    <div
                                                        key={`${anomaly.date}-${idx}`}
                                                        className={`p-3 rounded-lg flex items-center gap-3 ${anomaly.severity === 'high' ? 'bg-red-500/20' : 'bg-yellow-500/20'
                                                            }`}
                                                    >
                                                        {anomaly.type === 'late_night' ? (
                                                            <Moon className="w-5 h-5 text-purple-500" />
                                                        ) : (
                                                            <Eye className="w-5 h-5 text-orange-500" />
                                                        )}
                                                        <div className="flex-1">
                                                            <p className="text-sm font-medium">{anomaly.description}</p>
                                                            <p className="text-xs text-muted-foreground">{anomaly.date}</p>
                                                        </div>
                                                        <Badge variant={anomaly.severity === 'high' ? 'destructive' : 'secondary'}>
                                                            {anomaly.type === 'late_night' ? 'Late Night' : 'Binge'}
                                                        </Badge>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Late Night Sessions */}
                                    {data.behavior_anomalies.late_night_sessions.length > 0 && (
                                        <div>
                                            <p className="text-sm font-medium mb-3 flex items-center gap-2">
                                                <Moon className="w-4 h-4" />
                                                Late Night Sessions (12AM-5AM)
                                            </p>
                                            <div className="flex flex-wrap gap-2">
                                                {data.behavior_anomalies.late_night_sessions.slice(-15).map((session) => (
                                                    <div
                                                        key={session.date}
                                                        className="px-3 py-2 rounded-lg bg-purple-500/20 text-xs"
                                                        title={`Total: ${session.total_count} videos`}
                                                    >
                                                        <span className="font-medium">{session.date.slice(5)}</span>
                                                        <span className="text-purple-400 ml-2">{session.late_night_count} videos</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Binge Days */}
                                    {data.behavior_anomalies.binge_days.length > 0 && (
                                        <div>
                                            <p className="text-sm font-medium mb-3 flex items-center gap-2">
                                                <TrendingUp className="w-4 h-4" />
                                                Binge Days (2x+ average)
                                            </p>
                                            <div className="flex flex-wrap gap-2">
                                                {data.behavior_anomalies.binge_days.slice(-10).map((day) => (
                                                    <div
                                                        key={day.date}
                                                        className="px-3 py-2 rounded-lg bg-orange-500/20 text-xs"
                                                    >
                                                        <span className="font-medium">{day.date.slice(5)}</span>
                                                        <span className="text-orange-400 ml-2">{day.count} ({day.multiplier}x)</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Binge Watching Periods (Streaks) */}
                                    {data.behavior_anomalies.binge_watching_periods?.length > 0 && (
                                        <div className="p-4 bg-orange-500/10 rounded-lg border border-orange-500/30">
                                            <p className="text-sm font-medium mb-3 flex items-center gap-2">
                                                <Zap className="w-4 h-4 text-orange-500" />
                                                Binge Watching Periods
                                            </p>
                                            <div className="space-y-2">
                                                {data.behavior_anomalies.binge_watching_periods.map((period) => (
                                                    <div
                                                        key={period.start_date}
                                                        className="flex items-center justify-between text-sm"
                                                    >
                                                        <span className="text-muted-foreground">
                                                            {period.start_date.slice(5)} → {period.end_date.slice(5)}
                                                        </span>
                                                        <div className="flex gap-2">
                                                            <Badge variant="secondary">{period.duration_days} days</Badge>
                                                            <Badge variant="outline">{period.total_videos} videos</Badge>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Late Night Moods (Streaks) */}
                                    {data.behavior_anomalies.late_night_moods?.length > 0 && (
                                        <div className="p-4 bg-purple-500/10 rounded-lg border border-purple-500/30">
                                            <p className="text-sm font-medium mb-3 flex items-center gap-2">
                                                <Moon className="w-4 h-4 text-purple-500" />
                                                Late Night Moods
                                            </p>
                                            <div className="space-y-2">
                                                {data.behavior_anomalies.late_night_moods.map((mood) => (
                                                    <div
                                                        key={mood.start_date}
                                                        className="flex items-center justify-between text-sm"
                                                    >
                                                        <span className="text-muted-foreground">
                                                            {mood.start_date.slice(5)} → {mood.end_date.slice(5)}
                                                        </span>
                                                        <div className="flex gap-2">
                                                            <Badge variant="secondary">{mood.duration_days} nights</Badge>
                                                            <Badge variant="outline">{mood.total_late_videos} late videos</Badge>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* Behavior Patterns */}
                                    {data.behavior_anomalies.patterns && (
                                        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                                            <div className={`p-4 rounded-lg text-center ${data.behavior_anomalies.patterns.chronotype === 'Night Owl'
                                                ? 'bg-purple-500/20'
                                                : data.behavior_anomalies.patterns.chronotype === 'Early Bird'
                                                    ? 'bg-yellow-500/20'
                                                    : 'bg-muted/30'
                                                }`}>
                                                {data.behavior_anomalies.patterns.chronotype === 'Night Owl' ? (
                                                    <Moon className="w-6 h-6 mx-auto mb-2 text-purple-500" />
                                                ) : data.behavior_anomalies.patterns.chronotype === 'Early Bird' ? (
                                                    <Sun className="w-6 h-6 mx-auto mb-2 text-yellow-500" />
                                                ) : (
                                                    <Clock className="w-6 h-6 mx-auto mb-2" />
                                                )}
                                                <p className="font-bold">{data.behavior_anomalies.patterns.chronotype}</p>
                                                <p className="text-xs text-muted-foreground">Your Watch Type</p>
                                            </div>

                                            <div className={`p-4 rounded-lg text-center ${data.behavior_anomalies.patterns.weekend_warrior ? 'bg-green-500/20' : 'bg-muted/30'
                                                }`}>
                                                <Calendar className="w-6 h-6 mx-auto mb-2" />
                                                <p className="font-bold">
                                                    {data.behavior_anomalies.patterns.weekend_warrior ? 'Weekend Warrior' : 'Weekday Watcher'}
                                                </p>
                                                <p className="text-xs text-muted-foreground">
                                                    {data.behavior_anomalies.patterns.weekend_pct}% on weekends
                                                </p>
                                            </div>

                                            <div className="p-4 rounded-lg text-center bg-gray-500/20">
                                                <AlertTriangle className="w-6 h-6 mx-auto mb-2 text-gray-400" />
                                                <p className="font-bold">
                                                    {data.behavior_anomalies.patterns.inactive_periods?.length || 0} Breaks
                                                </p>
                                                <p className="text-xs text-muted-foreground">
                                                    {data.behavior_anomalies.patterns.inactive_periods?.length > 0
                                                        ? `Longest: ${Math.max(...data.behavior_anomalies.patterns.inactive_periods.map(p => p.gap_days))} days`
                                                        : 'No gaps > 3 days'
                                                    }
                                                </p>
                                            </div>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        )}

                        {/* Habit Formation Card */}
                        {data.habit_formation && (
                            <Card>
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2">
                                        <Repeat className="w-5 h-5 text-green-500" />
                                        Habit Formation
                                        {data.habit_formation.habit_strength > 0 && (
                                            <Badge variant="outline" className="ml-2">
                                                Strength: {data.habit_formation.habit_strength}/100
                                            </Badge>
                                        )}
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-6">
                                    {/* Summary */}
                                    <div className="p-4 bg-muted/30 rounded-lg">
                                        <p className="text-center text-muted-foreground">
                                            {data.habit_formation.summary}
                                        </p>
                                    </div>

                                    {/* Stats Grid */}
                                    <div className="grid grid-cols-4 gap-4 text-center">
                                        <div className="p-3 bg-green-500/10 rounded-lg">
                                            <Repeat className="w-5 h-5 mx-auto mb-1 text-green-500" />
                                            <p className="text-2xl font-bold">{data.habit_formation.total_channels_with_habits}</p>
                                            <p className="text-xs text-muted-foreground">Habitual Channels</p>
                                        </div>
                                        <div className="p-3 bg-orange-500/10 rounded-lg">
                                            <Flame className="w-5 h-5 mx-auto mb-1 text-orange-500" />
                                            <p className="text-2xl font-bold">{data.habit_formation.max_streak_days}</p>
                                            <p className="text-xs text-muted-foreground">Longest Streak</p>
                                        </div>
                                        <div className="p-3 bg-purple-500/10 rounded-lg">
                                            <Eye className="w-5 h-5 mx-auto mb-1 text-purple-500" />
                                            <p className="text-2xl font-bold">{data.habit_formation.total_videos_rewatched || 0}</p>
                                            <p className="text-xs text-muted-foreground">Rewatched Videos</p>
                                        </div>
                                        <div className="p-3 bg-blue-500/10 rounded-lg">
                                            <TrendingUp className="w-5 h-5 mx-auto mb-1 text-blue-500" />
                                            <p className="text-2xl font-bold">{data.habit_formation.total_topics_with_habits}</p>
                                            <p className="text-xs text-muted-foreground">Recurring Topics</p>
                                        </div>
                                    </div>

                                    {/* Channel Habits - Scrollable */}
                                    {data.habit_formation.channel_habits.length > 0 && (
                                        <div>
                                            <h4 className="font-semibold mb-3 flex items-center gap-2">
                                                <Youtube className="w-4 h-4" />
                                                Daily Channel Habits
                                                <span className="text-xs text-muted-foreground font-normal">
                                                    ({data.habit_formation.channel_habits.length} channels)
                                                </span>
                                            </h4>
                                            <ScrollArea className="h-[300px]">
                                                <div className="space-y-2 pr-4">
                                                    {data.habit_formation.channel_habits.map((habit, i) => (
                                                        <div key={i} className="flex items-center justify-between p-3 bg-muted/20 rounded-lg">
                                                            <div className="flex-1 min-w-0">
                                                                <p className="font-medium truncate">{habit.channel}</p>
                                                                <p className="text-xs text-muted-foreground">
                                                                    {habit.total_days_watched} days total • {habit.habit_streaks.length} streak(s)
                                                                </p>
                                                            </div>
                                                            <div className="text-right ml-2">
                                                                <Badge variant={habit.longest_streak >= 7 ? 'default' : habit.longest_streak >= 5 ? 'secondary' : 'outline'}>
                                                                    {habit.longest_streak} days
                                                                </Badge>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </ScrollArea>
                                        </div>
                                    )}

                                    {/* Video Habits */}
                                    {data.habit_formation.video_habits && data.habit_formation.video_habits.length > 0 && (
                                        <div>
                                            <h4 className="font-semibold mb-3 flex items-center gap-2">
                                                <Eye className="w-4 h-4" />
                                                Rewatched Videos
                                                <span className="text-xs text-muted-foreground font-normal">
                                                    (watched on multiple days)
                                                </span>
                                            </h4>
                                            <ScrollArea className="h-[250px]">
                                                <div className="space-y-2 pr-4">
                                                    {data.habit_formation.video_habits.map((video, i) => (
                                                        <div key={i} className="p-3 bg-muted/20 rounded-lg">
                                                            <p className="font-medium text-sm truncate">{video.title}</p>
                                                            <div className="flex items-center justify-between mt-1">
                                                                <p className="text-xs text-muted-foreground truncate">
                                                                    {video.channel}
                                                                </p>
                                                                <div className="flex items-center gap-2">
                                                                    <Badge variant="outline" className="text-xs">
                                                                        {video.days_watched} days
                                                                    </Badge>
                                                                    <span className="text-xs text-muted-foreground">
                                                                        {video.total_watches}x watched
                                                                    </span>
                                                                    {video.has_streak && (
                                                                        <Badge variant="secondary" className="text-xs">
                                                                            <Flame className="w-3 h-3 mr-1" />
                                                                            {video.longest_streak}d streak
                                                                        </Badge>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        </div>
                                                    ))}
                                                </div>
                                            </ScrollArea>
                                        </div>
                                    )}

                                    {/* Content/Topic Habits */}
                                    {data.habit_formation.content_habits.length > 0 && (
                                        <div>
                                            <h4 className="font-semibold mb-3 flex items-center gap-2">
                                                <TrendingUp className="w-4 h-4" />
                                                Recurring Content Interests
                                            </h4>
                                            <div className="flex flex-wrap gap-2">
                                                {data.habit_formation.content_habits.slice(0, 20).map((habit, i) => (
                                                    <Badge key={i} variant="outline" className="py-1">
                                                        {habit.topic}
                                                        <span className="ml-1 text-xs text-muted-foreground">
                                                            ({habit.longest_streak}d streak)
                                                        </span>
                                                    </Badge>
                                                ))}
                                            </div>
                                        </div>
                                    )}

                                    {/* No Habits Message */}
                                    {data.habit_formation.channel_habits.length === 0 &&
                                        (!data.habit_formation.video_habits || data.habit_formation.video_habits.length === 0) &&
                                        data.habit_formation.content_habits.length === 0 && (
                                            <div className="text-center text-muted-foreground py-4">
                                                <p>No strong daily habits detected (min 3 consecutive days)</p>
                                                <p className="text-xs mt-1">Watch the same channel daily to form habits!</p>
                                            </div>
                                        )}
                                </CardContent>
                            </Card>
                        )}

                        {/* Temporal Trends Card */}
                        {data.temporal_trends && data.temporal_trends.monthly_stats.length > 0 && (
                            <Card>
                                <CardHeader>
                                    <CardTitle className="flex items-center gap-2">
                                        <Activity className="w-5 h-5 text-cyan-500" />
                                        Temporal Trends
                                        <span className="text-sm font-normal text-muted-foreground ml-2">
                                            {data.temporal_trends.total_months} months tracked
                                        </span>
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-6">
                                    {/* Summary */}
                                    <div className="p-4 bg-muted/30 rounded-lg">
                                        <p className="text-center text-muted-foreground">
                                            {data.temporal_trends.summary}
                                        </p>
                                    </div>

                                    {/* Activity Trend Chart (Simple Bar) */}
                                    <div>
                                        <h4 className="font-semibold mb-3 flex items-center gap-2">
                                            <BarChart3 className="w-4 h-4" />
                                            Monthly Watch Activity
                                        </h4>
                                        <div className="space-y-1">
                                            {data.temporal_trends.activity_trend.slice(-12).map((month, i) => {
                                                const maxWatches = Math.max(...data.temporal_trends!.activity_trend.slice(-12).map(m => m.watches));
                                                const percentage = maxWatches > 0 ? (month.watches / maxWatches) * 100 : 0;
                                                return (
                                                    <div key={i} className="flex items-center gap-2">
                                                        <span className="text-xs w-16 text-muted-foreground">{month.month_label}</span>
                                                        <div className="flex-1 bg-muted/30 rounded-full h-4">
                                                            <div
                                                                className="bg-cyan-500 h-4 rounded-full transition-all"
                                                                style={{ width: `${percentage}%` }}
                                                            />
                                                        </div>
                                                        <span className="text-xs w-12 text-right">{month.watches}</span>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>

                                    {/* Monthly Peak Patterns Table */}
                                    <div>
                                        <h4 className="font-semibold mb-3 flex items-center gap-2">
                                            <Clock className="w-4 h-4" />
                                            Peak Patterns by Month
                                        </h4>
                                        <ScrollArea className="h-[250px]">
                                            <div className="space-y-2 pr-4">
                                                {data.temporal_trends.monthly_stats.slice().reverse().map((month, i) => (
                                                    <div key={i} className="flex items-center justify-between p-3 bg-muted/20 rounded-lg">
                                                        <div>
                                                            <p className="font-medium">{month.month_label}</p>
                                                            <p className="text-xs text-muted-foreground">
                                                                {month.total_watches} videos watched
                                                            </p>
                                                        </div>
                                                        <div className="flex gap-2">
                                                            <Badge variant="outline" className="text-xs">
                                                                <Clock className="w-3 h-3 mr-1" />
                                                                Peak: {month.peak_hour_label}
                                                            </Badge>
                                                            {month.peak_day_name && (
                                                                <Badge variant="secondary" className="text-xs">
                                                                    <Calendar className="w-3 h-3 mr-1" />
                                                                    {month.peak_day_name}
                                                                </Badge>
                                                            )}
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </ScrollArea>
                                    </div>

                                    {/* Pattern Shifts */}
                                    {data.temporal_trends.pattern_shifts.length > 0 && (
                                        <div>
                                            <h4 className="font-semibold mb-3 flex items-center gap-2">
                                                <AlertTriangle className="w-4 h-4 text-yellow-500" />
                                                Significant Pattern Shifts
                                            </h4>
                                            <div className="space-y-2">
                                                {data.temporal_trends.pattern_shifts.map((shift, i) => (
                                                    <div key={i} className="p-3 bg-yellow-500/10 rounded-lg border border-yellow-500/20">
                                                        <div className="flex items-center justify-between">
                                                            <span className="text-sm">{shift.description}</span>
                                                            <Badge variant="outline" className="text-xs">
                                                                {shift.from_month} → {shift.to_month}
                                                            </Badge>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        )}

                        {/* Channel Distribution by Bin */}
                        {data.channel_distribution && (
                            <Card>
                                <CardHeader>
                                    <CardTitle className="text-lg flex items-center gap-2">
                                        <Layers className="w-5 h-5 text-purple-500" />
                                        Channel Distribution by Watch Count
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="space-y-6">
                                    {/* Stats Summary */}
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                                        <div className="text-center p-3 bg-muted/50 rounded-lg">
                                            <p className="text-2xl font-bold">{data.channel_distribution.stats.total_channels.toLocaleString()}</p>
                                            <p className="text-xs text-muted-foreground">Total Channels</p>
                                        </div>
                                        <div className="text-center p-3 bg-muted/50 rounded-lg">
                                            <p className="text-2xl font-bold">{data.channel_distribution.stats.total_videos.toLocaleString()}</p>
                                            <p className="text-xs text-muted-foreground">Total Videos</p>
                                        </div>
                                        <div className="text-center p-3 bg-muted/50 rounded-lg">
                                            <p className="text-2xl font-bold text-orange-500">{data.channel_distribution.stats.single_view_channels.toLocaleString()}</p>
                                            <p className="text-xs text-muted-foreground">Single-View Channels</p>
                                        </div>
                                        <div className="text-center p-3 bg-muted/50 rounded-lg">
                                            <p className="text-2xl font-bold text-orange-500">{data.channel_distribution.stats.single_view_percentage}%</p>
                                            <p className="text-xs text-muted-foreground">One-Off Rate</p>
                                        </div>
                                    </div>

                                    {/* Bin Distribution Bar Chart */}
                                    <div>
                                        <h4 className="font-semibold mb-3">Channels by View Count</h4>
                                        <div className="space-y-2">
                                            {data.channel_distribution.bin_distribution.map((bin) => {
                                                const maxChannels = Math.max(...data.channel_distribution!.bin_distribution.map(b => b.channel_count));
                                                const percentage = maxChannels > 0 ? (bin.channel_count / maxChannels) * 100 : 0;
                                                return (
                                                    <div key={bin.bin} className="flex items-center gap-3">
                                                        <span className="w-16 text-sm text-right font-mono">{bin.bin}</span>
                                                        <div className="flex-1 h-8 bg-muted/30 rounded-lg overflow-hidden relative">
                                                            <div
                                                                className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg transition-all duration-500"
                                                                style={{ width: `${percentage}%` }}
                                                            />
                                                            <div className="absolute inset-0 flex items-center justify-between px-3">
                                                                <span className="text-sm font-medium text-white drop-shadow">
                                                                    {bin.channel_count.toLocaleString()} channels
                                                                </span>
                                                                <span className="text-xs text-white/80 drop-shadow">
                                                                    {bin.video_count.toLocaleString()} videos
                                                                </span>
                                                            </div>
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>

                                    {/* Temporal Distribution */}
                                    {data.channel_distribution.temporal_by_bin.length > 0 && (
                                        <div>
                                            <h4 className="font-semibold mb-3">Video Watches by Month & Channel Type</h4>
                                            <ScrollArea className="h-64">
                                                <div className="space-y-1">
                                                    {data.channel_distribution.temporal_by_bin.slice(-12).map((month) => {
                                                        const total = Object.values(month.bins).reduce((a, b) => a + b, 0);
                                                        return (
                                                            <div key={month.month} className="flex items-center gap-2">
                                                                <span className="w-16 text-xs font-mono">{month.month}</span>
                                                                <div className="flex-1 h-6 bg-muted/20 rounded overflow-hidden flex">
                                                                    {["1", "2-5", "6-10", "11-20", "21-50", "51-100", "100+"].map((binKey, i) => {
                                                                        const count = month.bins[binKey] || 0;
                                                                        const pct = total > 0 ? (count / total) * 100 : 0;
                                                                        const colors = [
                                                                            "bg-gray-400",
                                                                            "bg-blue-400",
                                                                            "bg-cyan-400",
                                                                            "bg-green-400",
                                                                            "bg-yellow-400",
                                                                            "bg-orange-400",
                                                                            "bg-red-400"
                                                                        ];
                                                                        return pct > 0 ? (
                                                                            <div
                                                                                key={binKey}
                                                                                className={`${colors[i]} h-full`}
                                                                                style={{ width: `${pct}%` }}
                                                                                title={`${binKey}: ${count} videos`}
                                                                            />
                                                                        ) : null;
                                                                    })}
                                                                </div>
                                                                <span className="w-12 text-xs text-right">{total}</span>
                                                            </div>
                                                        );
                                                    })}
                                                </div>
                                            </ScrollArea>
                                            <div className="flex flex-wrap gap-2 mt-3 justify-center">
                                                {["1", "2-5", "6-10", "11-20", "21-50", "51-100", "100+"].map((binKey, i) => {
                                                    const colors = ["bg-gray-400", "bg-blue-400", "bg-cyan-400", "bg-green-400", "bg-yellow-400", "bg-orange-400", "bg-red-400"];
                                                    return (
                                                        <div key={binKey} className="flex items-center gap-1">
                                                            <div className={`w-3 h-3 ${colors[i]} rounded`} />
                                                            <span className="text-xs">{binKey}</span>
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}
