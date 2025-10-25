import { useState, useEffect } from 'react';

interface JellyseerrMedia {
    id: number;
    title?: string;
    name?: string;
    posterPath: string | null;
    backdropPath: string | null;
    releaseDate?: string;
    firstAirDate?: string;
    voteAverage: number;
    mediaType: 'movie' | 'tv';
}

interface JellyseerrSearchResult {
    results: JellyseerrMedia[];
    page: number;
    totalPages: number;
    totalResults: number;
}

interface JellyseerrRequestResult {
    success: boolean;
    error?: string;
}

class JellyseerrApiClient {
    private baseUrl = '/jellyseerr';
    private imageBaseUrl = 'https://image.tmdb.org/t/p';

    private getHeaders(): HeadersInit {
        const headers: HeadersInit = {
            'Content-Type': 'application/json'
        };

        // Get auth token from ApiClient if available
        if ((window as any).ApiClient) {
            const token = (window as any).ApiClient.accessToken();
            if (token) {
                headers['X-Emby-Token'] = token;
            }
        }

        return headers;
    }

    async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
        const url = `${this.baseUrl}${endpoint}`;
        const headers = this.getHeaders();

        const response = await fetch(url, {
            ...options,
            headers: {
                ...headers,
                ...options.headers
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    }

    async checkStatus(): Promise<{ connected: boolean; error?: string }> {
        try {
            return await this.request('/status');
        } catch (error) {
            return { 
                connected: false, 
                error: error instanceof Error ? error.message : 'Unknown error' 
            };
        }
    }

    async search(query: string, page: number = 1): Promise<JellyseerrSearchResult | null> {
        try {
            const params = new URLSearchParams({ 
                query, 
                page: page.toString() 
            });
            return await this.request(`/search?${params}`);
        } catch (error) {
            console.error('Jellyseerr search failed:', error);
            return null;
        }
    }

    async requestMedia(mediaType: string, mediaId: number): Promise<JellyseerrRequestResult> {
        try {
            return await this.request('/request', {
                method: 'POST',
                body: JSON.stringify({ mediaType, mediaId })
            });
        } catch (error) {
            return { 
                success: false, 
                error: error instanceof Error ? error.message : 'Request failed' 
            };
        }
    }

    getPosterUrl(posterPath: string | null, size: string = 'w500'): string | null {
        if (!posterPath) return null;
        return `${this.imageBaseUrl}/${size}${posterPath}`;
    }

    getBackdropUrl(backdropPath: string | null, size: string = 'w1280'): string | null {
        if (!backdropPath) return null;
        return `${this.imageBaseUrl}/${size}${backdropPath}`;
    }
}

// Singleton instance
export const jellyseerrApi = new JellyseerrApiClient();

// Hook for searching Jellyseerr
export function useJellyseerrSearch(query: string, enabled: boolean = true) {
    const [results, setResults] = useState<JellyseerrMedia[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!query || !enabled) {
            setResults([]);
            return;
        }

        const searchJellyseerr = async () => {
            setLoading(true);
            setError(null);

            try {
                const data = await jellyseerrApi.search(query);
                
                if (data && data.results) {
                    setResults(data.results.slice(0, 12)); // Limit to 12 results
                } else {
                    setResults([]);
                }
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Failed to search Jellyseerr');
                setResults([]);
            } finally {
                setLoading(false);
            }
        };

        searchJellyseerr();
    }, [query, enabled]);

    return { results, loading, error };
}

// Hook for requesting media
export function useJellyseerrRequest() {
    const [requesting, setRequesting] = useState(false);

    const requestMedia = async (mediaType: string, mediaId: number): Promise<boolean> => {
        setRequesting(true);

        try {
            const result = await jellyseerrApi.requestMedia(mediaType, mediaId);
            return result.success;
        } catch (error) {
            console.error('Request failed:', error);
            return false;
        } finally {
            setRequesting(false);
        }
    };

    return { requestMedia, requesting };
}

export type { JellyseerrMedia, JellyseerrSearchResult };