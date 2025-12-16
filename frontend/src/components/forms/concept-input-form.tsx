"use client";

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { X, Plus, Lightbulb, Clock, Target } from 'lucide-react';

interface ConceptInputFormProps {
  onSubmit: (data: {
    concept: string;
    duration_weeks: number;
    preferences?: {
      difficulty?: string;
      learning_style?: string;
      preferred_media_types?: string[];
      avoid_tags?: string[];
      max_daily_hours?: number;
    };
  }) => void;
  loading?: boolean;
}

export function ConceptInputForm({ onSubmit, loading = false }: ConceptInputFormProps) {
  const [concept, setConcept] = useState('');
  const [durationWeeks, setDurationWeeks] = useState<number>(6);
  const [difficulty, setDifficulty] = useState<string>('');
  const [learningStyle, setLearningStyle] = useState<string>('');
  const [preferredMediaTypes, setPreferredMediaTypes] = useState<string[]>([]);
  const [avoidTags, setAvoidTags] = useState<string[]>([]);
  const [maxDailyHours, setMaxDailyHours] = useState<number>(2);
  const [newTag, setNewTag] = useState('');

  const mediaTypeOptions = [
    { value: 'video', label: 'Videos' },
    { value: 'article', label: 'Articles' },
    { value: 'course', label: 'Courses' },
    { value: 'book', label: 'Books' },
    { value: 'podcast', label: 'Podcasts' },
    { value: 'interactive', label: 'Interactive Content' }
  ];

  const difficultyOptions = [
    { value: 'beginner', label: 'Beginner' },
    { value: 'intermediate', label: 'Intermediate' },
    { value: 'advanced', label: 'Advanced' }
  ];

  const learningStyleOptions = [
    { value: 'visual', label: 'Visual' },
    { value: 'auditory', label: 'Auditory' },
    { value: 'kinesthetic', label: 'Kinesthetic (Hands-on)' },
    { value: 'reading', label: 'Reading/Writing' },
    { value: 'mixed', label: 'Mixed' }
  ];

  const addPreferredMediaType = (mediaType: string) => {
    if (!preferredMediaTypes.includes(mediaType)) {
      setPreferredMediaTypes([...preferredMediaTypes, mediaType]);
    }
  };

  const removePreferredMediaType = (mediaType: string) => {
    setPreferredMediaTypes(preferredMediaTypes.filter(type => type !== mediaType));
  };

  const addAvoidTag = () => {
    if (newTag.trim() && !avoidTags.includes(newTag.trim())) {
      setAvoidTags([...avoidTags, newTag.trim()]);
      setNewTag('');
    }
  };

  const removeAvoidTag = (tag: string) => {
    setAvoidTags(avoidTags.filter(t => t !== tag));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!concept.trim()) return;

    onSubmit({
      concept: concept.trim(),
      duration_weeks: durationWeeks,
      preferences: {
        difficulty: difficulty || undefined,
        learning_style: learningStyle || undefined,
        preferred_media_types: preferredMediaTypes.length > 0 ? preferredMediaTypes : undefined,
        avoid_tags: avoidTags.length > 0 ? avoidTags : undefined,
        max_daily_hours: maxDailyHours
      }
    });
  };

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Lightbulb className="h-5 w-5" />
          Create Your Learning Roadmap
        </CardTitle>
        <CardDescription>
          Tell us what you want to learn, and we'll create a personalized roadmap with recommended resources.
        </CardDescription>
      </CardHeader>

      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Concept Input */}
          <div className="space-y-2">
            <Label htmlFor="concept">What do you want to learn?</Label>
            <Textarea
              id="concept"
              placeholder="e.g., Python programming, machine learning, web development, data science..."
              value={concept}
              onChange={(e) => setConcept(e.target.value)}
              rows={3}
              required
            />
          </div>

          {/* Duration */}
          <div className="space-y-2">
            <Label htmlFor="duration" className="flex items-center gap-2">
              <Clock className="h-4 w-4" />
              How many weeks do you have to learn this?
            </Label>
            <Select value={durationWeeks.toString()} onValueChange={(value) => setDurationWeeks(parseInt(value))}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="2">2 weeks (Quick overview)</SelectItem>
                <SelectItem value="4">4 weeks (Basic understanding)</SelectItem>
                <SelectItem value="6">6 weeks (Solid foundation)</SelectItem>
                <SelectItem value="8">8 weeks (Comprehensive)</SelectItem>
                <SelectItem value="12">12 weeks (Expert level)</SelectItem>
                <SelectItem value="16">16 weeks (Master level)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Difficulty Level */}
          <div className="space-y-2">
            <Label htmlFor="difficulty" className="flex items-center gap-2">
              <Target className="h-4 w-4" />
              What's your current skill level? (Optional)
            </Label>
            <Select value={difficulty} onValueChange={setDifficulty}>
              <SelectTrigger>
                <SelectValue placeholder="Select your skill level" />
              </SelectTrigger>
              <SelectContent>
                {difficultyOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Learning Style */}
          <div className="space-y-2">
            <Label htmlFor="learning-style">How do you prefer to learn? (Optional)</Label>
            <Select value={learningStyle} onValueChange={setLearningStyle}>
              <SelectTrigger>
                <SelectValue placeholder="Select your learning style" />
              </SelectTrigger>
              <SelectContent>
                {learningStyleOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Preferred Media Types */}
          <div className="space-y-2">
            <Label>Preferred content types (Optional)</Label>
            <p className="text-sm text-gray-600">Select the types of content you enjoy learning from:</p>
            <div className="flex flex-wrap gap-2">
              {mediaTypeOptions.map((option) => (
                <Button
                  key={option.value}
                  type="button"
                  variant={preferredMediaTypes.includes(option.value) ? "default" : "outline"}
                  size="sm"
                  onClick={() => preferredMediaTypes.includes(option.value)
                    ? removePreferredMediaType(option.value)
                    : addPreferredMediaType(option.value)
                  }
                >
                  {option.label}
                </Button>
              ))}
            </div>
          </div>

          {/* Avoid Tags */}
          <div className="space-y-2">
            <Label>Topics to avoid (Optional)</Label>
            <p className="text-sm text-gray-600">Add any topics or technologies you want to skip:</p>
            <div className="flex gap-2">
              <Input
                placeholder="e.g., mathematics, statistics, theory..."
                value={newTag}
                onChange={(e) => setNewTag(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addAvoidTag())}
              />
              <Button type="button" onClick={addAvoidTag} size="sm">
                <Plus className="h-4 w-4" />
              </Button>
            </div>
            {avoidTags.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {avoidTags.map((tag) => (
                  <Badge key={tag} variant="secondary" className="flex items-center gap-1">
                    {tag}
                    <X
                      className="h-3 w-3 cursor-pointer hover:text-red-600"
                      onClick={() => removeAvoidTag(tag)}
                    />
                  </Badge>
                ))}
              </div>
            )}
          </div>

          {/* Daily Time Commitment */}
          <div className="space-y-2">
            <Label htmlFor="daily-hours">Daily time commitment (hours)</Label>
            <Select value={maxDailyHours.toString()} onValueChange={(value) => setMaxDailyHours(parseInt(value))}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1">1 hour (Casual learning)</SelectItem>
                <SelectItem value="2">2 hours (Regular practice)</SelectItem>
                <SelectItem value="3">3 hours (Intensive)</SelectItem>
                <SelectItem value="4">4 hours (Full commitment)</SelectItem>
                <SelectItem value="6">6+ hours (Professional)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Submit Button */}
          <Button
            type="submit"
            className="w-full"
            disabled={loading || !concept.trim()}
          >
            {loading ? 'Generating Roadmap...' : 'Generate My Roadmap'}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}