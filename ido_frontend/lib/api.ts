/**
 * API client for IDO Backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface ScanResult {
  found_files: Record<string, string | null>;
  missing_files: string[];
  total_files_in_zip: number;
}

export interface ExtractedFile {
  filename: string;
  content_type: 'json' | 'csv';
  content: string;
  size_bytes: number;
}

export interface ExtractResult {
  files: ExtractedFile[];
  timezone: string;
  missing_files: string[];
}

export interface PreviewResult {
  watch_history: {
    total_items: number;
    sample_items: unknown[];
    has_more: boolean;
  } | null;
  search_history: {
    total_items: number;
    sample_items: unknown[];
    has_more: boolean;
  } | null;
  subscriptions: {
    total_items: number;
    headers: string[];
    sample_items: unknown[];
    has_more: boolean;
  } | null;
  timezone: string;
}

export interface SessionResponse {
  token: string;
  files_stored: string[];
  timezone: string;
  created_at: string;
}

export interface SessionData {
  token: string;
  files: ExtractedFile[];
  timezone: string;
  created_at: string;
}

// Event types for preprocessed data
export interface Event {
  type: 'watch' | 'search' | 'subscribe';
  engagement: 'active' | 'passive' | null;
  timestamp_utc: string | null;
  timestamp_local: string | null;
  hour_local: number | null;
  day_of_week: number | null;
  month_local: number | null;
  text_raw: string | null;
  text_clean: string | null;
  language_type: 'hindi' | 'hinglish' | 'english' | 'unknown' | null;
  language_confidence: 'high' | 'medium' | 'low' | null;
  // Micro topic extraction fields
  hashtags: string[] | null;
  ner: string[] | null;
  nouns: string[] | null;
  text_v1: string | null;  // Hinglish only: text with Hindi removed
  micro_topics: string[] | null;
  channel: string | null;
  channel_clean: string | null;
  channel_url: string | null;
  video_url: string | null;
}

export interface LanguageBreakdown {
  hindi: number;
  hinglish: number;
  english: number;
  unknown: number;
}

export interface PreprocessStats {
  total_watch: number;
  total_search: number;
  total_subscribe: number;
  total_events: number;
  language_breakdown: LanguageBreakdown;
}

export interface PreprocessResult {
  watch_history: Event[];
  search_history: Event[];
  subscriptions: Event[];
  combined_events: Event[];
  stats: PreprocessStats;
  timezone: string;
}

export interface PreprocessedSessionData {
  token: string;
  events: Event[];
  stats: PreprocessStats;
  timezone: string;
  created_at: string;
}

class APIClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  async readZip(file: File): Promise<ScanResult> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${this.baseUrl}/api/zip/read`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to scan ZIP file');
    }

    return response.json();
  }

  async extractZip(file: File, paths: Record<string, string>, timezone: string): Promise<ExtractResult> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('paths', JSON.stringify(paths));
    formData.append('timezone', timezone);

    const response = await fetch(`${this.baseUrl}/api/zip/extract`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to extract files');
    }

    return response.json();
  }

  async previewContent(files: ExtractedFile[], timezone: string): Promise<PreviewResult> {
    const response = await fetch(`${this.baseUrl}/api/content/preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ files, timezone }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to preview content');
    }

    return response.json();
  }

  async getTimezones(): Promise<{ timezones: string[] }> {
    const response = await fetch(`${this.baseUrl}/api/content/timezones`);
    if (!response.ok) throw new Error('Failed to fetch timezones');
    return response.json();
  }

  async storeSession(files: ExtractedFile[], timezone: string): Promise<SessionResponse> {
    const response = await fetch(`${this.baseUrl}/api/session/store`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ files, timezone }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to store session');
    }

    return response.json();
  }

  async getSession(token: string): Promise<SessionData> {
    const response = await fetch(`${this.baseUrl}/api/session/${token}`);
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Session not found');
    }
    return response.json();
  }

  async deleteSession(token: string): Promise<{ message: string }> {
    const response = await fetch(`${this.baseUrl}/api/session/${token}`, { method: 'DELETE' });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to delete session');
    }
    return response.json();
  }

  async listSessions(): Promise<{ sessions: SessionResponse[]; count: number }> {
    const response = await fetch(`${this.baseUrl}/api/session/`);
    if (!response.ok) throw new Error('Failed to list sessions');
    return response.json();
  }

  async healthCheck(): Promise<{ status: string; version: string }> {
    const response = await fetch(`${this.baseUrl}/api/health`);
    if (!response.ok) throw new Error('Backend is not healthy');
    return response.json();
  }

  // Preprocessing endpoints
  async preprocessAll(files: ExtractedFile[], timezone: string): Promise<PreprocessResult> {
    const response = await fetch(`${this.baseUrl}/api/preprocess/all`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ files, timezone }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to preprocess files');
    }

    return response.json();
  }

  async preprocessAndStore(files: ExtractedFile[], timezone: string): Promise<PreprocessedSessionData> {
    const response = await fetch(`${this.baseUrl}/api/preprocess/all-and-store`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ files, timezone }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to preprocess and store');
    }

    return response.json();
  }

  async getPreprocessedSession(token: string): Promise<PreprocessedSessionData> {
    const response = await fetch(`${this.baseUrl}/api/preprocess/session/${token}`);
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Preprocessed session not found');
    }
    return response.json();
  }
}

export const api = new APIClient();
export default api;
