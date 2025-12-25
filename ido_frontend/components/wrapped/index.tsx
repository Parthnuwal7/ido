'use client';

import { ReactNode } from 'react';
import { cn } from '@/lib/utils';

/**
 * Wrapped Card Component Library
 * 
 * A collection of reusable components for building "Spotify Wrapped" style
 * insight cards with vibrant colors, bold typography, and playful design.
 */

// ============================================
// COLOR THEMES
// ============================================

export const cardThemes = {
    yellow: {
        bg: 'bg-[#FFDD00]',
        text: 'text-gray-900',
        accent: 'bg-[#6B5ACD]',
    },
    purple: {
        bg: 'bg-[#6B5ACD]',
        text: 'text-white',
        accent: 'bg-[#FFDD00]',
    },
    coral: {
        bg: 'bg-[#FF6B6B]',
        text: 'text-white',
        accent: 'bg-[#2D1B4E]',
    },
    teal: {
        bg: 'bg-[#00C9B7]',
        text: 'text-gray-900',
        accent: 'bg-[#FF6B6B]',
    },
    navy: {
        bg: 'bg-[#1A1A2E]',
        text: 'text-white',
        accent: 'bg-[#FF6B6B]',
    },
    gradient1: {
        bg: 'bg-gradient-to-br from-[#FF6B6B] via-[#FF8E53] to-[#FFDD00]',
        text: 'text-white',
        accent: 'bg-[#2D1B4E]',
    },
    gradient2: {
        bg: 'bg-gradient-to-br from-[#6B5ACD] via-[#9B59B6] to-[#E74C3C]',
        text: 'text-white',
        accent: 'bg-[#FFDD00]',
    },
} as const;

export type CardTheme = keyof typeof cardThemes;

// ============================================
// BASE CARD CONTAINER
// ============================================

interface WrappedCardProps {
    children: ReactNode;
    theme?: CardTheme;
    className?: string;
}

export function WrappedCard({
    children,
    theme = 'yellow',
    className
}: WrappedCardProps) {
    const colors = cardThemes[theme];

    return (
        <div
            className={cn(
                'relative w-[360px] h-[640px] rounded-3xl overflow-hidden',
                'flex flex-col p-8',
                colors.bg,
                colors.text,
                className
            )}
        >
            {children}
            {/* Watermark */}
            <div className="absolute bottom-3 right-4 text-xs opacity-80 font-medium">
                Ido by Parthnuwal7
            </div>
        </div>
    );
}

// ============================================
// TYPOGRAPHY COMPONENTS
// ============================================

interface HeadingProps {
    children: ReactNode;
    size?: 'xl' | '2xl' | '3xl' | '4xl' | '5xl';
    className?: string;
}

export function WrappedHeading({
    children,
    size = '4xl',
    className
}: HeadingProps) {
    const sizeClasses = {
        'xl': 'text-xl',
        '2xl': 'text-2xl',
        '3xl': 'text-3xl',
        '4xl': 'text-4xl md:text-5xl',
        '5xl': 'text-5xl md:text-6xl',
    };

    return (
        <h2
            className={cn(
                'font-black leading-tight tracking-tight',
                sizeClasses[size],
                className
            )}
        >
            {children}
        </h2>
    );
}

interface SubtitleProps {
    children: ReactNode;
    className?: string;
}

export function WrappedSubtitle({ children, className }: SubtitleProps) {
    return (
        <p className={cn('text-lg opacity-90', className)}>
            {children}
        </p>
    );
}

interface BigNumberProps {
    value: string | number;
    label?: string;
    suffix?: string;
    className?: string;
}

export function WrappedBigNumber({ value, label, suffix, className }: BigNumberProps) {
    return (
        <div className={cn('text-center', className)}>
            <div className="flex items-baseline justify-center gap-2">
                <span className="text-7xl md:text-8xl font-black">{value}</span>
                {suffix && <span className="text-3xl font-bold opacity-80">{suffix}</span>}
            </div>
            {label && <p className="text-xl mt-2 opacity-80">{label}</p>}
        </div>
    );
}

// ============================================
// DECORATIVE SHAPES
// ============================================

interface ShapeProps {
    className?: string;
    color?: string;
}

export function CircleShape({ className, color = 'bg-[#6B5ACD]' }: ShapeProps) {
    return (
        <div
            className={cn(
                'absolute rounded-full',
                color,
                className
            )}
        />
    );
}

export function SemiCircleShape({ className, color = 'bg-[#6B5ACD]' }: ShapeProps) {
    return (
        <div
            className={cn(
                'absolute rounded-full',
                color,
                className
            )}
            style={{ clipPath: 'inset(0 50% 0 0)' }}
        />
    );
}

export function SquareShape({ className, color = 'bg-[#FF6B6B]' }: ShapeProps) {
    return (
        <div
            className={cn(
                'absolute',
                color,
                className
            )}
        />
    );
}

export function DotsPattern({ className }: { className?: string }) {
    return (
        <div
            className={cn('absolute', className)}
            style={{
                backgroundImage: 'radial-gradient(circle, currentColor 2px, transparent 2px)',
                backgroundSize: '16px 16px',
            }}
        />
    );
}

export function GridPattern({ className }: { className?: string }) {
    return (
        <div
            className={cn('absolute opacity-20', className)}
            style={{
                backgroundImage: `
          linear-gradient(currentColor 1px, transparent 1px),
          linear-gradient(90deg, currentColor 1px, transparent 1px)
        `,
                backgroundSize: '20px 20px',
            }}
        />
    );
}

// ============================================
// CARD SECTIONS
// ============================================

interface CardHeaderProps {
    logo?: ReactNode;
    label?: string;
    className?: string;
}

export function WrappedCardHeader({ logo, label, className }: CardHeaderProps) {
    return (
        <div className={cn('flex items-center gap-3 mb-auto', className)}>
            {logo && (
                <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center">
                    {logo}
                </div>
            )}
            {label && (
                <span className="text-sm font-semibold uppercase tracking-wider opacity-70">
                    {label}
                </span>
            )}
        </div>
    );
}

interface CardFooterProps {
    children?: ReactNode;
    className?: string;
}

export function WrappedCardFooter({ children, className }: CardFooterProps) {
    return (
        <div className={cn('mt-auto pt-6', className)}>
            {children}
        </div>
    );
}

interface CardContentProps {
    children: ReactNode;
    position?: 'start' | 'center' | 'end';
    className?: string;
}

export function WrappedCardContent({
    children,
    position = 'center',
    className
}: CardContentProps) {
    const positionClasses = {
        start: 'justify-start',
        center: 'justify-center',
        end: 'justify-end',
    };

    return (
        <div
            className={cn(
                'flex-1 flex flex-col',
                positionClasses[position],
                className
            )}
        >
            {children}
        </div>
    );
}

// ============================================
// BADGE COMPONENT
// ============================================

interface BadgeProps {
    children: ReactNode;
    variant?: 'default' | 'outline' | 'filled';
    className?: string;
}

export function WrappedBadge({
    children,
    variant = 'default',
    className
}: BadgeProps) {
    const variantClasses = {
        default: 'bg-white/20 text-current',
        outline: 'border-2 border-current bg-transparent',
        filled: 'bg-white text-gray-900',
    };

    return (
        <span
            className={cn(
                'inline-flex items-center px-4 py-2 rounded-full text-sm font-bold',
                variantClasses[variant],
                className
            )}
        >
            {children}
        </span>
    );
}

// ============================================
// RANKING LIST
// ============================================

interface RankingItem {
    rank: number;
    label: string;
    value?: string;
}

interface RankingListProps {
    items: RankingItem[];
    className?: string;
}

export function WrappedRankingList({ items, className }: RankingListProps) {
    return (
        <div className={cn('space-y-3', className)}>
            {items.map((item, i) => (
                <div
                    key={i}
                    className="flex items-center gap-4 p-3 rounded-xl bg-white/10"
                >
                    <span className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center font-bold">
                        {item.rank}
                    </span>
                    <span className="flex-1 font-semibold truncate">{item.label}</span>
                    {item.value && (
                        <span className="text-sm opacity-70">{item.value}</span>
                    )}
                </div>
            ))}
        </div>
    );
}

// ============================================
// PROGRESS BAR
// ============================================

interface ProgressBarProps {
    value: number;
    max?: number;
    label?: string;
    showValue?: boolean;
    className?: string;
}

export function WrappedProgressBar({
    value,
    max = 100,
    label,
    showValue = true,
    className
}: ProgressBarProps) {
    const percentage = Math.min((value / max) * 100, 100);

    return (
        <div className={cn('space-y-2', className)}>
            {(label || showValue) && (
                <div className="flex justify-between text-sm">
                    {label && <span>{label}</span>}
                    {showValue && <span className="font-bold">{value}</span>}
                </div>
            )}
            <div className="h-3 rounded-full bg-white/20 overflow-hidden">
                <div
                    className="h-full rounded-full bg-white transition-all duration-500"
                    style={{ width: `${percentage}%` }}
                />
            </div>
        </div>
    );
}

// ============================================
// YEAR BADGE (like the "2025 Wrapped" badge)
// ============================================

interface YearBadgeProps {
    year?: number;
    label?: string;
    className?: string;
}

export function WrappedYearBadge({
    year = new Date().getFullYear(),
    label = 'Wrapped',
    className
}: YearBadgeProps) {
    return (
        <div className={cn('flex items-center gap-2', className)}>
            <div className="px-4 py-2 bg-white text-gray-900 rounded-l-full font-black">
                {year}
            </div>
            <div className="px-4 py-2 bg-gray-900 text-white rounded-r-full font-bold italic">
                {label}
            </div>
        </div>
    );
}
