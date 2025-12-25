'use client';

import { useState } from 'react';
import { ChevronLeft, ChevronRight, Upload, Loader2, Settings, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { TimezoneSelector } from '@/components/timezone-selector';
import { FileUploader } from '@/components/file-uploader';
import Link from 'next/link';

// Import all card templates
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

// API types matching backend response
interface WrappedData {
  intro: { username: string; year: number };
  stats_overview: {
    videos_watched: number;
    channels_explored: number;
    active_days: number;
    total_sessions: number;
  };
  time_spent: {
    total_hours: number;
    total_minutes: number;
    avg_daily_minutes: number;
  };
  peak_month: { month: string; watches: number };
  top_channel: { name: string; views: number; percentage: number };
  top_channels: { channels: { name: string; views: number }[] };
  watch_cycle: { peak_hour: number; hourly_data: number[] };
  peak_day: { day: string; daily_data: Record<string, number> };
  longest_streak: { days: number; dates: string };
  personality: { type: string; description: string };
  binge_sessions: { count: number; longest_duration: string; longest_date: string };
  late_night: { videos: number; latest_time: string; latest_date: string };
  habits: {
    total_channels: number;
    strongest: { channel: string; frequency: string };
    top_habits: any[];
  };
  patterns: {
    total_patterns: number;
    insights: string[];
    top_patterns: any[];
  };
  rewatched: { count: number; top_video: string; top_times: number };
  subscriptions: { total: number; watched: number; ghost: number; overlap_percentage: number };
  searches: { total: number; top_search: string; top_searches: any[] };
  first_last: {
    first_video: { title: string; date: string };
    last_video: { title: string; date: string };
  };
  metadata: { generated_at: string; version: string };
}

type AppState = 'upload' | 'processing' | 'cards' | 'error';

export default function Home() {
  const [state, setState] = useState<AppState>('upload');
  const [timezone, setTimezone] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [wrappedData, setWrappedData] = useState<WrappedData | null>(null);
  const [currentCard, setCurrentCard] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
  };

  const handleGenerate = async () => {
    if (!selectedFile || !timezone) return;

    setState('processing');
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('timezone', timezone);

      const response = await fetch('http://localhost:8000/api/wrapped/generate', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to generate wrapped');
      }

      const data: WrappedData = await response.json();
      setWrappedData(data);
      setState('cards');
      setCurrentCard(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setState('error');
    }
  };

  const handleReset = () => {
    setState('upload');
    setSelectedFile(null);
    setWrappedData(null);
    setCurrentCard(0);
    setError(null);
  };

  const goNext = () => {
    if (wrappedData) {
      setCurrentCard((c) => (c + 1) % 19);
    }
  };

  const goPrev = () => {
    if (wrappedData) {
      setCurrentCard((c) => (c - 1 + 19) % 19);
    }
  };

  // Render cards from data
  const renderCards = () => {
    if (!wrappedData) return [];

    return [
      <IntroCard
        key="intro"
        username={wrappedData.intro.username}
        year={wrappedData.intro.year}
      />,
      <StatsOverviewCard
        key="stats"
        videosWatched={wrappedData.stats_overview.videos_watched}
        channelsExplored={wrappedData.stats_overview.channels_explored}
        activeDays={wrappedData.stats_overview.active_days}
        totalSessions={wrappedData.stats_overview.total_sessions}
      />,
      <TimeSpentCard
        key="time"
        totalHours={wrappedData.time_spent.total_hours}
        totalMinutes={wrappedData.time_spent.total_minutes}
        avgDailyMinutes={wrappedData.time_spent.avg_daily_minutes}
      />,
      <MostActiveMonthCard
        key="peak-month"
        peakMonth={wrappedData.peak_month.month}
        peakMonthWatches={wrappedData.peak_month.watches}
      />,
      <ChannelSpotlightCard
        key="spotlight"
        channelName={wrappedData.top_channel.name}
        totalViews={wrappedData.top_channel.views}
        percentageOfTotal={wrappedData.top_channel.percentage}
      />,
      <TopChannelsCard
        key="top-channels"
        channels={wrappedData.top_channels.channels}
      />,
      <WatchCycleCard
        key="watch-cycle"
        peakHour={wrappedData.watch_cycle.peak_hour}
        hourlyData={wrappedData.watch_cycle.hourly_data}
      />,
      <DayOfWeekCard
        key="day-of-week"
        peakDay={wrappedData.peak_day.day}
      />,
      <LongestStreakCard
        key="streak"
        streakDays={wrappedData.longest_streak.days}
        streakDates={wrappedData.longest_streak.dates}
      />,
      <PersonalityCard
        key="personality"
        personalityType={wrappedData.personality.type}
        description={wrappedData.personality.description}
      />,
      <BingeSessionsCard
        key="binge"
        totalBinges={wrappedData.binge_sessions.count}
        longestDuration={wrappedData.binge_sessions.longest_duration}
        longestDate={wrappedData.binge_sessions.longest_date}
      />,
      <LateNightCard
        key="late-night"
        lateNightVideos={wrappedData.late_night.videos}
        latestWatch={wrappedData.late_night.latest_time}
        latestWatchDate={wrappedData.late_night.latest_date}
      />,
      <HabitsCard
        key="habits"
        totalHabitChannels={wrappedData.habits.total_channels}
        strongestHabit={wrappedData.habits.strongest}
      />,
      <PatternsCard
        key="patterns"
        totalPatterns={wrappedData.patterns.total_patterns}
        insights={wrappedData.patterns.insights}
      />,
      <RewatchedCard
        key="rewatched"
        rewatchedCount={wrappedData.rewatched.count}
        topRewatched={wrappedData.rewatched.top_video}
        rewatchTimes={wrappedData.rewatched.top_times}
      />,
      <SubscriptionCard
        key="subscriptions"
        totalSubscriptions={wrappedData.subscriptions.total}
        watchedSubscribed={wrappedData.subscriptions.watched}
        overlapPercentage={wrappedData.subscriptions.overlap_percentage}
        ghostSubscriptions={wrappedData.subscriptions.ghost}
      />,
      <SearchInsightsCard
        key="search"
        totalSearches={wrappedData.searches.total}
        topSearch={wrappedData.searches.top_search}
      />,
      <FirstLastVideoCard
        key="first-last"
        firstVideoTitle={wrappedData.first_last.first_video.title}
        firstVideoDate={wrappedData.first_last.first_video.date}
        lastVideoTitle={wrappedData.first_last.last_video.title}
        lastVideoDate={wrappedData.first_last.last_video.date}
      />,
      <OutroCard key="outro" year={wrappedData.intro.year} />,
    ];
  };

  const cards = renderCards();

  // Section labels
  const sections = [
    { name: 'INTRO', startIndex: 0 },
    { name: 'YOUR YEAR', startIndex: 1 },
    { name: 'FAVORITES', startIndex: 4 },
    { name: 'RHYTHM', startIndex: 6 },
    { name: 'PERSONALITY', startIndex: 9 },
    { name: 'DEEP DIVES', startIndex: 10 },
    { name: 'OUTRO', startIndex: 18 },
  ];

  const getCurrentSection = () => {
    for (let i = sections.length - 1; i >= 0; i--) {
      if (currentCard >= sections[i].startIndex) {
        return sections[i].name;
      }
    }
    return sections[0].name;
  };

  return (
    <main className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card/80 backdrop-blur-lg sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
              <span className="text-white font-bold text-lg">Y</span>
            </div>
            <div>
              <h1 className="text-xl font-bold">YouTube Wrapped</h1>
              <p className="text-xs text-muted-foreground">Discover your year in videos</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Link href="/wrapped-demo">
              <Button variant="outline" size="sm">
                <Sparkles className="w-4 h-4 mr-2" />
                Demo
              </Button>
            </Link>
            <Link href="/admin/debug">
              <Button variant="outline" size="sm">
                <Settings className="w-4 h-4 mr-2" />
                Admin
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Upload State */}
      {state === 'upload' && (
        <div className="max-w-lg mx-auto px-4 py-12">
          <div className="text-center mb-10">
            <Sparkles className="w-12 h-12 mx-auto mb-4 text-purple-500" />
            <h2 className="text-3xl font-bold mb-3">
              Your YouTube{' '}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-500 to-pink-500">
                Wrapped
              </span>
            </h2>
            <p className="text-muted-foreground">
              Upload your YouTube Takeout to discover your watch patterns,
              favorite channels, and viewing habits.
            </p>
          </div>

          <div className="space-y-6">
            <Card>
              <CardHeader className="pb-4">
                <CardTitle className="text-lg">1. Select Timezone</CardTitle>
              </CardHeader>
              <CardContent>
                <TimezoneSelector value={timezone} onChange={setTimezone} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-4">
                <CardTitle className="text-lg">2. Upload Takeout ZIP</CardTitle>
              </CardHeader>
              <CardContent>
                <FileUploader onFileSelect={handleFileSelect} />
              </CardContent>
            </Card>

            {selectedFile && timezone && (
              <Button
                onClick={handleGenerate}
                size="lg"
                className="w-full py-6 text-lg bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600"
              >
                <Sparkles className="w-5 h-5 mr-2" />
                Generate My Wrapped
              </Button>
            )}

            <p className="text-center text-sm text-muted-foreground">
              Your data is processed in memory and never stored on our servers.
            </p>
          </div>
        </div>
      )}

      {/* Processing State */}
      {state === 'processing' && (
        <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
          <Loader2 className="w-16 h-16 animate-spin text-purple-500 mb-6" />
          <h2 className="text-2xl font-bold mb-2">Generating Your Wrapped...</h2>
          <p className="text-muted-foreground">Analyzing your YouTube history</p>
        </div>
      )}

      {/* Error State */}
      {state === 'error' && (
        <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
          <div className="text-6xl mb-6">😕</div>
          <h2 className="text-2xl font-bold mb-2">Something went wrong</h2>
          <p className="text-muted-foreground mb-6">{error}</p>
          <Button onClick={handleReset} variant="outline">
            Try Again
          </Button>
        </div>
      )}

      {/* Cards State */}
      {state === 'cards' && wrappedData && (
        <div className="min-h-[calc(100vh-73px)] bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex flex-col items-center justify-center py-8">
          {/* Section indicator */}
          <div className="text-center mb-6">
            <span className="px-3 py-1 bg-purple-500/20 text-purple-300 rounded-full text-sm">
              {getCurrentSection()}
            </span>
            <span className="text-gray-400 text-sm ml-3">
              Card {currentCard + 1} of 18
            </span>
          </div>

          {/* Card carousel */}
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

          {/* Section bars */}
          <div className="flex gap-1 mt-6">
            {sections.map((section, i) => {
              const nextSectionStart = sections[i + 1]?.startIndex ?? 18;
              const isActive = currentCard >= section.startIndex && currentCard < nextSectionStart;

              return (
                <button
                  key={section.name}
                  onClick={() => setCurrentCard(section.startIndex)}
                  className={`h-2 rounded-full transition-all ${isActive ? 'bg-white w-8' : 'bg-white/30 hover:bg-white/50 w-4'
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
                className={`w-2 h-2 rounded-full transition-all ${i === currentCard ? 'bg-white scale-125' : 'bg-white/20 hover:bg-white/40'
                  }`}
              />
            ))}
          </div>

          {/* Reset button */}
          <Button
            onClick={handleReset}
            variant="ghost"
            className="mt-8 text-gray-400 hover:text-white"
          >
            Start Over
          </Button>
        </div>
      )}
    </main>
  );
}
