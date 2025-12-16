"use client";

import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Star, Clock, ExternalLink, CheckCircle, BookmarkPlus } from 'lucide-react';
import { Resource } from '@/lib/api';

interface ResourceCardProps {
  resource: Resource;
  onClick?: (resource: Resource) => void;
  onRate?: (resourceId: number, rating: number) => void;
  onComplete?: (resourceId: number) => void;
  onSave?: (resourceId: number) => void;
  showActions?: boolean;
}

export function ResourceCard({
  resource,
  onClick,
  onRate,
  onComplete,
  onSave,
  showActions = true
}: ResourceCardProps) {
  const getDifficultyColor = (difficulty?: string) => {
    switch (difficulty?.toLowerCase()) {
      case 'beginner': return 'bg-green-100 text-green-800 hover:bg-green-200';
      case 'intermediate': return 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200';
      case 'advanced': return 'bg-red-100 text-red-800 hover:bg-red-200';
      default: return 'bg-gray-100 text-gray-800 hover:bg-gray-200';
    }
  };

  const getMediaTypeIcon = (mediaType: string) => {
    switch (mediaType?.toLowerCase()) {
      case 'video': return '🎥';
      case 'article': return '📄';
      case 'course': return '🎓';
      case 'book': return '📚';
      case 'podcast': return '🎧';
      default: return '📖';
    }
  };

  const formatDuration = (minutes?: number) => {
    if (!minutes) return 'N/A';
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  };

  return (
    <Card
      className="cursor-pointer hover:shadow-lg transition-all duration-200 hover:scale-[1.02]"
      onClick={() => onClick?.(resource)}
    >
      <CardHeader className="pb-3">
        <div className="flex justify-between items-start gap-2">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-lg leading-tight line-clamp-2 flex items-center gap-2">
              <span className="text-xl">{getMediaTypeIcon(resource.media_type)}</span>
              {resource.title}
            </CardTitle>
            <CardDescription className="mt-1 line-clamp-2">
              {resource.description}
            </CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent className="pt-0">
        {/* Resource metadata */}
        <div className="flex flex-wrap gap-2 mb-3">
          <Badge className={getDifficultyColor(resource.difficulty)}>
            {resource.difficulty || 'Unknown'}
          </Badge>
          <Badge variant="outline">
            {resource.media_type}
          </Badge>
          {resource.source && (
            <Badge variant="secondary">
              {resource.source}
            </Badge>
          )}
          {resource.learning_style && (
            <Badge variant="outline">
              {resource.learning_style}
            </Badge>
          )}
        </div>

        {/* Rating and duration */}
        <div className="flex justify-between items-center mb-3 text-sm">
          <div className="flex items-center gap-1">
            <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
            <span className="font-medium">{resource.rating?.toFixed(1) || 'N/A'}</span>
            {resource.rating_count && resource.rating_count > 0 && (
              <span className="text-gray-500">({resource.rating_count})</span>
            )}
          </div>
          <div className="flex items-center gap-1 text-gray-600">
            <Clock className="h-4 w-4" />
            <span>{formatDuration(resource.duration_minutes)}</span>
          </div>
          {resource.media_type?.toLowerCase() === 'video' && (
            <Button
              size="sm"
              variant="ghost"
              onClick={(e) => {
                e.stopPropagation();
                window.open(resource.url, '_blank');
              }}
              className="shrink-0"
            >
              <ExternalLink className="h-4 w-4" />
            </Button>
          )}
        </div>

        {/* Tags */}
        {resource.tags && resource.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {resource.tags.slice(0, 4).map((tag, idx) => (
              <Badge key={idx} variant="secondary" className="text-xs">
                {tag}
              </Badge>
            ))}
            {resource.tags.length > 4 && (
              <Badge variant="secondary" className="text-xs">
                +{resource.tags.length - 4}
              </Badge>
            )}
          </div>
        )}

        {/* User interactions */}
        {showActions && (
          <div className="flex gap-2 pt-2 border-t">
            <Button
              size="sm"
              variant="outline"
              className="flex-1"
              onClick={(e) => {
                e.stopPropagation();
                onSave?.(resource.id);
              }}
              disabled={resource.user_saved}
            >
              <BookmarkPlus className="h-4 w-4 mr-1" />
              {resource.user_saved ? 'Saved' : 'Save'}
            </Button>

            <Button
              size="sm"
              variant={resource.user_completed ? 'secondary' : 'default'}
              className="flex-1"
              onClick={(e) => {
                e.stopPropagation();
                onComplete?.(resource.id);
              }}
            >
              <CheckCircle className="h-4 w-4 mr-1" />
              {resource.user_completed ? 'Completed' : 'Complete'}
            </Button>
          </div>
        )}

        {/* User rating display */}
        {resource.user_rating && (
          <div className="flex items-center gap-1 mt-2 text-sm text-blue-600">
            <Star className="h-4 w-4 fill-blue-600" />
            <span>Your rating: {resource.user_rating}/5</span>
          </div>
        )}

        {/* Completion status */}
        {resource.user_completed && (
          <div className="flex items-center gap-1 mt-1 text-sm text-green-600">
            <CheckCircle className="h-4 w-4" />
            <span>Completed</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}