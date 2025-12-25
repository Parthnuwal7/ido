'use client';

import { useState, useEffect, ReactNode } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Lock, Eye, EyeOff } from 'lucide-react';

// Password from environment variable (set in .env.local)
// Fallback to 'ido2025' if not set
const ADMIN_PASSWORD = process.env.NEXT_PUBLIC_ADMIN_PASSWORD || 'ido2025';

interface AdminLayoutProps {
    children: ReactNode;
}

export default function AdminLayout({ children }: AdminLayoutProps) {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(true);

    // Check if already authenticated (session storage)
    useEffect(() => {
        const auth = sessionStorage.getItem('admin_auth');
        if (auth === 'true') {
            setIsAuthenticated(true);
        }
        setIsLoading(false);
    }, []);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        if (password === ADMIN_PASSWORD) {
            setIsAuthenticated(true);
            sessionStorage.setItem('admin_auth', 'true');
        } else {
            setError('Incorrect password');
            setPassword('');
        }
    };

    const handleLogout = () => {
        setIsAuthenticated(false);
        sessionStorage.removeItem('admin_auth');
    };

    if (isLoading) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center">
                <div className="animate-pulse text-muted-foreground">Loading...</div>
            </div>
        );
    }

    if (!isAuthenticated) {
        return (
            <div className="min-h-screen bg-background flex items-center justify-center p-4">
                <Card className="w-full max-w-sm">
                    <CardHeader className="text-center">
                        <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-purple-500/10 flex items-center justify-center">
                            <Lock className="w-6 h-6 text-purple-500" />
                        </div>
                        <CardTitle>Admin Access</CardTitle>
                        <p className="text-sm text-muted-foreground mt-1">
                            Enter password to access admin features
                        </p>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div className="relative">
                                <Input
                                    type={showPassword ? 'text' : 'password'}
                                    placeholder="Enter password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="pr-10"
                                    autoFocus
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                >
                                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                </button>
                            </div>

                            {error && (
                                <p className="text-sm text-red-500 text-center">{error}</p>
                            )}

                            <Button type="submit" className="w-full">
                                Unlock
                            </Button>
                        </form>
                    </CardContent>
                </Card>
            </div>
        );
    }

    // Authenticated - show children with logout option
    return (
        <div className="min-h-screen bg-background">
            {/* Admin Header with Logout */}
            <div className="fixed top-4 right-4 z-50">
                <Button variant="ghost" size="sm" onClick={handleLogout}>
                    <Lock className="w-4 h-4 mr-2" />
                    Logout
                </Button>
            </div>
            {children}
        </div>
    );
}
