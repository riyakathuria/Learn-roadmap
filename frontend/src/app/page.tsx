"use client";

import React, { useState } from 'react';
import { useAuth } from '@/lib/auth';
import { ConceptInputForm } from '@/components/forms/concept-input-form';
import { RoadmapDisplay } from '@/components/roadmap/roadmap-display';
import { ResourceCard } from '@/components/recommendations/resource-card';
import { AuthModal } from '@/components/auth/auth-modal';
import { Header } from '@/components/layout/header';
import { apiClient, Roadmap, Resource } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, BookOpen, Target, TrendingUp, LogIn, UserPlus } from 'lucide-react';

export default function HomePage() {
  const { user, loading: authLoading, isAuthenticated } = useAuth();
  const [roadmap, setRoadmap] = useState<Roadmap | null>(null);
  const [recommendations, setRecommendations] = useState<Resource[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAuthModal, setShowAuthModal] = useState(false);

  // Listen for auth modal events from header
  React.useEffect(() => {
    const handleOpenAuthModal = () => setShowAuthModal(true);
    window.addEventListener('openAuthModal', handleOpenAuthModal);
    return () => window.removeEventListener('openAuthModal', handleOpenAuthModal);
  }, []);

  const handleGenerateRoadmap = async (data: {
    concept: string;
    duration_weeks: number;
    preferences?: any;
  }) => {
    if (!isAuthenticated) {
      setShowAuthModal(true);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.generateRoadmap(
        data.concept,
        data.duration_weeks,
        data.preferences
      );

      setRoadmap(response.roadmap);
      setRecommendations(response.recommendations || []);
    } catch (err: any) {
      setError(err.message || 'Failed to generate roadmap');
    } finally {
      setLoading(false);
    }
  };

  const handleStepComplete = async (stepId: number, completed: boolean) => {
    if (!roadmap) return;

    try {
      await apiClient.updateRoadmapProgress(roadmap.id, stepId, completed);
      // Update local state
      setRoadmap(prev => {
        if (!prev || !prev.steps) return prev;
        return {
          ...prev,
          steps: prev.steps.map(step =>
            step.id === stepId
              ? { ...step, status: completed ? 'completed' : 'pending' }
              : step
          )
        };
      });
    } catch (err: any) {
      setError('Failed to update step progress');
    }
  };

  const handleResourceClick = (resource: Resource) => {
    // Open resource in new tab
    window.open(resource.url, '_blank');
  };

  const handleResourceRate = async (resourceId: number, rating: number) => {
    try {
      await apiClient.rateResource(resourceId, rating);
      // Update local state
      setRecommendations(prev =>
        prev.map(res =>
          res.id === resourceId
            ? { ...res, user_rating: rating }
            : res
        )
      );
    } catch (err: any) {
      setError('Failed to rate resource');
    }
  };

  const handleResourceComplete = async (resourceId: number) => {
    try {
      await apiClient.markResourceComplete(resourceId);
      // Update local state
      setRecommendations(prev =>
        prev.map(res =>
          res.id === resourceId
            ? { ...res, user_completed: true }
            : res
        )
      );
    } catch (err: any) {
      setError('Failed to mark resource as completed');
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin mx-auto" />
          <p className="text-lg">Loading...</p>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin mx-auto" />
          <p className="text-lg">Generating your personalized roadmap...</p>
          <p className="text-sm text-gray-600">This may take a few moments</p>
        </div>
      </div>
    );
  }

  if (roadmap) {
    return (
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="mb-6 flex justify-between items-center">
            <h1 className="text-3xl font-bold text-gray-900">Your Learning Roadmap</h1>
            <Button
              variant="outline"
              onClick={() => {
                setRoadmap(null);
                setRecommendations([]);
                setError(null);
              }}
            >
              Create New Roadmap
            </Button>
          </div>

          {error && (
            <Alert className="mb-6">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <RoadmapDisplay
            roadmap={roadmap}
            recommendations={recommendations}
            onStepComplete={handleStepComplete}
            onResourceClick={handleResourceClick}
          />

          {/* Step-specific recommendations removed - only shown within steps */}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <Header />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Hero Section */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Personalized Learning Roadmaps
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-3xl mx-auto">
            Transform your learning goals into structured roadmaps with AI-powered recommendations,
            tailored to your pace and preferences.
          </p>

          {/* Authentication Prompt */}
          {!isAuthenticated && (
            <div className="mb-8">
              <p className="text-lg text-gray-700 mb-4">
                Sign up or sign in to create your personalized learning roadmap
              </p>
              <div className="flex justify-center space-x-4">
                <Button
                  variant="outline"
                  onClick={() => setShowAuthModal(true)}
                  className="px-6 py-2"
                >
                  <LogIn className="h-4 w-4 mr-2" />
                  Sign In
                </Button>
                <Button
                  onClick={() => setShowAuthModal(true)}
                  className="px-6 py-2"
                >
                  <UserPlus className="h-4 w-4 mr-2" />
                  Get Started
                </Button>
              </div>
            </div>
          )}

          <div className="grid md:grid-cols-3 gap-6 mb-12">
            <Card>
              <CardContent className="pt-6 text-center">
                <Target className="h-8 w-8 mx-auto mb-4 text-blue-600" />
                <h3 className="font-semibold mb-2">Personalized Plans</h3>
                <p className="text-sm text-gray-600">
                  AI-generated roadmaps based on your skill level and learning style
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6 text-center">
                <BookOpen className="h-8 w-8 mx-auto mb-4 text-green-600" />
                <h3 className="font-semibold mb-2">Curated Resources</h3>
                <p className="text-sm text-gray-600">
                  Handpicked videos, articles, courses, and books from trusted sources
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6 text-center">
                <TrendingUp className="h-8 w-8 mx-auto mb-4 text-purple-600" />
                <h3 className="font-semibold mb-2">Track Progress</h3>
                <p className="text-sm text-gray-600">
                  Monitor your learning journey with interactive progress tracking
                </p>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <Alert className="mb-6 max-w-2xl mx-auto">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Main Form */}
        <ConceptInputForm onSubmit={handleGenerateRoadmap} loading={loading} />

        {/* Auth Modal */}
        <AuthModal
          isOpen={showAuthModal}
          onClose={() => setShowAuthModal(false)}
        />

        {/* Features Section */}
        <div className="mt-16 text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-8">Why Choose Our Platform?</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="text-center">
              <div className="text-3xl mb-2">🎯</div>
              <h4 className="font-semibold">Goal-Oriented</h4>
              <p className="text-sm text-gray-600">Clear milestones and achievable targets</p>
            </div>
            <div className="text-center">
              <div className="text-3xl mb-2">⚡</div>
              <h4 className="font-semibold">Time-Efficient</h4>
              <p className="text-sm text-gray-600">Optimized learning paths save your time</p>
            </div>
            <div className="text-center">
              <div className="text-3xl mb-2">🧠</div>
              <h4 className="font-semibold">Adaptive Learning</h4>
              <p className="text-sm text-gray-600">Recommendations improve based on your preferences</p>
            </div>
            <div className="text-center">
              <div className="text-3xl mb-2">🌟</div>
              <h4 className="font-semibold">Quality Content</h4>
              <p className="text-sm text-gray-600">Verified resources from reputable platforms</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
