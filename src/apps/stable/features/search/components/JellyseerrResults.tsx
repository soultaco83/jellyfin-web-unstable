import React, { useState } from 'react';
import type { FC } from 'react';
import { Card, CardContent, CardMedia, Typography, Button, Grid, Box, CircularProgress, Alert } from '@mui/material';
import { useJellyseerrSearch, useJellyseerrRequest, jellyseerrApi } from './useJellyseerr';
import type { JellyseerrMedia } from './useJellyseerr';

interface JellyseerrResultsProps {
    query: string;
}

const JellyseerrMediaCard: FC<{ media: JellyseerrMedia }> = ({ media }) => {
    const { requestMedia, requesting } = useJellyseerrRequest();
    const [requested, setRequested] = useState(false);

    const handleRequest = async () => {
        const success = await requestMedia(media.mediaType, media.id);
        if (success) {
            setRequested(true);
        }
    };

    const posterUrl = jellyseerrApi.getPosterUrl(media.posterPath) || '/web/assets/img/icon-transparent.png';
    const title = media.title || media.name || 'Unknown Title';
    const year = (media.releaseDate || media.firstAirDate || '').split('-')[0];
    const rating = media.voteAverage ? media.voteAverage.toFixed(1) : 'N/A';
    const mediaTypeLabel = media.mediaType === 'tv' ? 'TV' : 'Movie';

    return (
        <Card 
            sx={{ 
                height: '100%', 
                display: 'flex', 
                flexDirection: 'column',
                transition: 'transform 0.2s',
                '&:hover': {
                    transform: 'scale(1.02)'
                }
            }}
        >
            <CardMedia
                component="img"
                sx={{
                    aspectRatio: '2/3',
                    objectFit: 'cover'
                }}
                image={posterUrl}
                alt={title}
            />
            <CardContent sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                <Typography 
                    gutterBottom 
                    variant="h6" 
                    component="div"
                    sx={{
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                        minHeight: '3em'
                    }}
                >
                    {title}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {year && `${year} • `}{mediaTypeLabel} • ⭐ {rating}
                </Typography>
                <Box sx={{ mt: 'auto' }}>
                    <Button
                        variant={requested ? 'outlined' : 'contained'}
                        fullWidth
                        disabled={requesting || requested}
                        onClick={handleRequest}
                        color={requested ? 'success' : 'primary'}
                    >
                        {requesting ? (
                            <CircularProgress size={20} />
                        ) : requested ? (
                            '✓ Requested'
                        ) : (
                            'Request'
                        )}
                    </Button>
                </Box>
            </CardContent>
        </Card>
    );
};

const JellyseerrResults: FC<JellyseerrResultsProps> = ({ query }) => {
    const { results, loading, error } = useJellyseerrSearch(query, !!query);

    if (!query) {
        return null;
    }

    if (loading) {
        return (
            <Box sx={{ mt: 4, textAlign: 'center' }}>
                <CircularProgress />
                <Typography variant="body1" sx={{ mt: 2 }}>
                    Searching Jellyseerr...
                </Typography>
            </Box>
        );
    }

    if (error) {
        return (
            <Box sx={{ mt: 4 }}>
                <Alert severity="error">
                    Failed to search Jellyseerr: {error}
                </Alert>
            </Box>
        );
    }

    if (results.length === 0) {
        return null; // Don't show anything if no results
    }

    return (
        <Box sx={{ mt: 4 }}>
            <Typography 
                variant="h5" 
                component="h2" 
                gutterBottom
                sx={{ mb: 3 }}
            >
                Available on Jellyseerr
            </Typography>
            <Grid container spacing={2}>
                {results.map((media) => (
                    <Grid item xs={6} sm={4} md={3} lg={2} key={`${media.mediaType}-${media.id}`}>
                        <JellyseerrMediaCard media={media} />
                    </Grid>
                ))}
            </Grid>
        </Box>
    );
};

export default JellyseerrResults;