'use client';

import { useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cardThemes } from '@/components/wrapped';

// All card templates
import {
    IntroCard,
    StatsOverviewCard,
    TimeSpentCard,
    MostActiveMonthCard,
    ChannelSpotlightCard,
    TopChannelsCard,
    WatchCycleCard,
    DayOfWeekCard,
    LongestStreakCard,
    PersonalityCard,
    BingeSessionsCard,
    LateNightCard,
    HabitsCard,
    PatternsCard,
    RewatchedCard,
    SubscriptionCard,
    SearchInsightsCard,
    FirstLastVideoCard,
    OutroCard,
} from '@/components/wrapped/card-templates';

/**
 * YouTube Wrapped Demo v2
 * Full 19-card flow based on cards_doc.md specification
 */

export default function WrappedDemoPage() {
    const [currentCard, setCurrentCard] = useState(0);

    // Sample demo data
    const demoData = {
        // Intro
        username: 'Explorer',
        year: 2025,

        // Stats
        videosWatched: 1247,
        channelsExplored: 342,
        activeDays: 298,
        totalSessions: 456,

        // Time
        totalHours: 127,
        totalMinutes: 7620,
        avgDailyMinutes: 26,

        // Peak month
        peakMonth: 'July',
        peakMonthWatches: 312,

        // Channels
        topChannel: { name: 'Kurzgesagt', views: 156, percentage: 12 },
        topChannels: [
            { name: 'Kurzgesagt', views: 156 },
            { name: 'Veritasium', views: 89 },
            { name: 'Mark Rober', views: 67 },
            { name: 'MKBHD', views: 54 },
            { name: 'Linus Tech Tips', views: 48 },
        ],

        // Rhythm
        peakHour: 22,
        peakDay: 'Saturday',
        longestStreak: 47,
        streakDates: 'June 12 - July 28',

        // Deep dives
        totalBinges: 12,
        longestBingeDuration: '5h 42m',
        longestBingeDate: 'November 23',

        lateNightVideos: 89,
        latestWatch: '3:47 AM',
        latestWatchDate: 'December 3',

        habitChannels: 8,
        strongestHabit: { channel: 'Daily Dose of Internet', frequency: '2.3 days' },

        // Patterns (Association Rule Mining)
        patterns: {
            totalPatterns: 7,
            insights: [
                'You watch **Kurzgesagt** on **Sundays** (68% of the time)',
                '**MKBHD** is your **morning** go-to (54%)',
                '**Veritasium** is your **weekend** channel (72% weekend views)',
                'You watch **Mark Rober** on **Saturdays** (45% of the time)',
            ],
        },

        rewatchedCount: 23,
        topRewatched: 'lofi hip hop radio - beats to relax/study to',
        rewatchTimes: 7,

        totalSubscriptions: 148,
        watchedSubscribed: 67,
        overlapPercentage: 45,
        ghostSubscriptions: 81,

        totalSearches: 156,
        topSearch: 'coding tutorials',

        firstVideo: { title: 'Why You Should Learn TypeScript in 2025', date: 'January 3, 2025' },
        lastVideo: { title: 'Best Moments of 2025 Compilation', date: 'December 23, 2025' },
    };

    // Section labels for navigation
    const sections = [
        { name: 'INTRO', startIndex: 0 },
        { name: 'YOUR YEAR', startIndex: 1 },
        { name: 'FAVORITES', startIndex: 4 },
        { name: 'RHYTHM', startIndex: 6 },
        { name: 'PERSONALITY', startIndex: 10 },
        { name: 'DEEP DIVES', startIndex: 11 },
        { name: 'OUTRO', startIndex: 18 },
    ];

    // All cards in order
    const cards = [
        // SECTION 1: INTRO (index 0)
        <IntroCard key="intro" username={demoData.username} year={demoData.year} />,

        // SECTION 2: YOUR YEAR WITH US (indices 1-3)
        <StatsOverviewCard
            key="stats"
            videosWatched={demoData.videosWatched}
            channelsExplored={demoData.channelsExplored}
            activeDays={demoData.activeDays}
            totalSessions={demoData.totalSessions}
        />,
        <TimeSpentCard
            key="time"
            totalHours={demoData.totalHours}
            totalMinutes={demoData.totalMinutes}
            avgDailyMinutes={demoData.avgDailyMinutes}
        />,
        <MostActiveMonthCard
            key="peak-month"
            peakMonth={demoData.peakMonth}
            peakMonthWatches={demoData.peakMonthWatches}
        />,

        // SECTION 3: YOUR FAVORITES (indices 4-5)
        <ChannelSpotlightCard
            key="spotlight"
            channelName={demoData.topChannel.name}
            totalViews={demoData.topChannel.views}
            percentageOfTotal={demoData.topChannel.percentage}
        />,
        <TopChannelsCard key="top-channels" channels={demoData.topChannels} />,

        // SECTION 4: YOUR RHYTHM (indices 6-9)
        <WatchCycleCard
            key="watch-cycle"
            peakHour={demoData.peakHour}
            hourlyData={[2, 1, 0, 0, 0, 1, 3, 5, 8, 12, 15, 18, 22, 25, 28, 32, 38, 45, 52, 58, 65, 48, 35, 12]}
        />,
        <DayOfWeekCard key="day-of-week" peakDay={demoData.peakDay} />,
        <LongestStreakCard
            key="streak"
            streakDays={demoData.longestStreak}
            streakDates={demoData.streakDates}
        />,

        // SECTION 5: PERSONALIZATION (index 10)
        <PersonalityCard
            key="personality"
            personalityType="Curious Mind"
            description="You dive deep into diverse topics"
        />,

        // SECTION 6: DEEP DIVES (indices 11-17)
        <BingeSessionsCard
            key="binge"
            totalBinges={demoData.totalBinges}
            longestDuration={demoData.longestBingeDuration}
            longestDate={demoData.longestBingeDate}
        />,
        <LateNightCard
            key="late-night"
            lateNightVideos={demoData.lateNightVideos}
            latestWatch={demoData.latestWatch}
            latestWatchDate={demoData.latestWatchDate}
        />,
        <HabitsCard
            key="habits"
            totalHabitChannels={demoData.habitChannels}
            strongestHabit={demoData.strongestHabit}
        />,
        <PatternsCard
            key="patterns"
            totalPatterns={demoData.patterns.totalPatterns}
            insights={demoData.patterns.insights}
        />,
        <RewatchedCard
            key="rewatched"
            rewatchedCount={demoData.rewatchedCount}
            topRewatched={demoData.topRewatched}
            rewatchTimes={demoData.rewatchTimes}
        />,
        <SubscriptionCard
            key="subscriptions"
            totalSubscriptions={demoData.totalSubscriptions}
            watchedSubscribed={demoData.watchedSubscribed}
            overlapPercentage={demoData.overlapPercentage}
            ghostSubscriptions={demoData.ghostSubscriptions}
        />,
        <SearchInsightsCard
            key="search"
            totalSearches={demoData.totalSearches}
            topSearch={demoData.topSearch}
        />,
        <FirstLastVideoCard
            key="first-last"
            firstVideoTitle={demoData.firstVideo.title}
            firstVideoDate={demoData.firstVideo.date}
            lastVideoTitle={demoData.lastVideo.title}
            lastVideoDate={demoData.lastVideo.date}
        />,

        // SECTION 7: OUTRO (index 17)
        <OutroCard key="outro" year={demoData.year} />,
    ];

    const goNext = () => setCurrentCard((c) => (c + 1) % cards.length);
    const goPrev = () => setCurrentCard((c) => (c - 1 + cards.length) % cards.length);

    // Get current section
    const getCurrentSection = () => {
        for (let i = sections.length - 1; i >= 0; i--) {
            if (currentCard >= sections[i].startIndex) {
                return sections[i].name;
            }
        }
        return sections[0].name;
    };

    return (
        <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4">
            {/* Header */}
            <div className="text-center mb-6">
                <h1 className="text-2xl font-bold text-foreground mb-1">
                    YouTube Wrapped Demo
                </h1>
                <div className="flex items-center justify-center gap-3">
                    <span className="px-3 py-1 bg-purple-500/20 text-purple-400 rounded-full text-sm">
                        {getCurrentSection()}
                    </span>
                    <span className="text-muted-foreground text-sm">
                        Card {currentCard + 1} of {cards.length}
                    </span>
                </div>
            </div>

            {/* Card Display */}
            <div className="relative flex items-center gap-4">
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={goPrev}
                    className="text-white hover:bg-white/10"
                >
                    <ChevronLeft className="w-8 h-8" />
                </Button>

                <div className="transition-all duration-300 transform hover:scale-[1.02]">
                    {cards[currentCard]}
                </div>

                <Button
                    variant="ghost"
                    size="icon"
                    onClick={goNext}
                    className="text-white hover:bg-white/10"
                >
                    <ChevronRight className="w-8 h-8" />
                </Button>
            </div>

            {/* Section indicators */}
            <div className="flex gap-1 mt-6">
                {sections.map((section, i) => {
                    const nextSectionStart = sections[i + 1]?.startIndex ?? cards.length;
                    const cardsInSection = nextSectionStart - section.startIndex;
                    const isActive = currentCard >= section.startIndex && currentCard < nextSectionStart;

                    return (
                        <button
                            key={section.name}
                            onClick={() => setCurrentCard(section.startIndex)}
                            className={`h-2 rounded-full transition-all ${isActive
                                ? 'bg-white w-8'
                                : 'bg-white/30 hover:bg-white/50 w-4'
                                }`}
                            title={section.name}
                        />
                    );
                })}
            </div>

            {/* Dot indicators */}
            <div className="flex gap-1.5 mt-4">
                {cards.map((_, i) => (
                    <button
                        key={i}
                        onClick={() => setCurrentCard(i)}
                        className={`w-2 h-2 rounded-full transition-all ${i === currentCard
                            ? 'bg-white scale-125'
                            : 'bg-white/20 hover:bg-white/40'
                            }`}
                    />
                ))}
            </div>

            {/* Theme showcase */}
            <div className="mt-8 text-center">
                <h2 className="text-sm font-semibold text-white/50 mb-2">Available Themes</h2>
                <div className="flex gap-2 flex-wrap justify-center max-w-md">
                    {Object.keys(cardThemes).map((theme) => (
                        <div
                            key={theme}
                            className={`px-3 py-1 rounded-full text-xs font-medium ${cardThemes[theme as keyof typeof cardThemes].bg
                                } ${cardThemes[theme as keyof typeof cardThemes].text}`}
                        >
                            {theme}
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
