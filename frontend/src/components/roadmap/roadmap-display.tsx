"use client";

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Roadmap, RoadmapStep, Resource } from '@/lib/api';

interface RoadmapDisplayProps {
  roadmap: Roadmap;
  recommendations: Resource[];
  onStepComplete?: (stepId: number, completed: boolean) => void;
  onResourceClick?: (resource: Resource) => void;
}

export function RoadmapDisplay({
  roadmap,
  recommendations,
  onStepComplete,
  onResourceClick
}: RoadmapDisplayProps) {
  const [activeStep, setActiveStep] = useState<number | null>(null);

  const calculateProgress = () => {
    if (!roadmap.steps) return 0;
    const completedSteps = roadmap.steps.filter(step => step.status === 'completed').length;
    return (completedSteps / roadmap.steps.length) * 100;
  };

  const getDifficultyColor = (difficulty?: string) => {
    switch (difficulty?.toLowerCase()) {
      case 'beginner': return 'bg-green-100 text-green-800';
      case 'intermediate': return 'bg-yellow-100 text-yellow-800';
      case 'advanced': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800';
      case 'in_progress': return 'bg-blue-100 text-blue-800';
      case 'pending': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      {/* Roadmap Header */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-start">
            <div>
              <CardTitle className="text-2xl">{roadmap.title}</CardTitle>
              <CardDescription>{roadmap.description}</CardDescription>
            </div>
            <div className="text-right">
              <Badge variant="outline">{roadmap.duration_weeks} weeks</Badge>
              <p className="text-sm text-gray-500 mt-1">
                Status: <Badge className={getStatusColor(roadmap.status)}>{roadmap.status}</Badge>
              </p>
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Progress</span>
              <span>{calculateProgress().toFixed(0)}%</span>
            </div>
            <Progress value={calculateProgress()} className="w-full" />
          </div>
        </CardHeader>
      </Card>

      {/* Roadmap Content */}
      <Tabs defaultValue="steps" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="steps">Learning Steps</TabsTrigger>
          <TabsTrigger value="recommendations">Recommended Resources</TabsTrigger>
        </TabsList>

        <TabsContent value="steps" className="space-y-4">
          {roadmap.steps?.map((step: RoadmapStep, index: number) => (
            <Card key={step.id} className="cursor-pointer hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm font-mono">
                        {index + 1}
                      </span>
                      {step.title}
                    </CardTitle>
                    <CardDescription className="mt-2">{step.description}</CardDescription>
                  </div>
                  <div className="flex gap-2 ml-4">
                    <Badge className={getDifficultyColor(step.difficulty)}>
                      {step.difficulty}
                    </Badge>
                    <Badge className={getStatusColor(step.status)}>
                      {step.status?.replace('_', ' ')}
                    </Badge>
                  </div>
                </div>
                {step.estimated_hours && (
                  <p className="text-sm text-gray-600">
                    Estimated time: {step.estimated_hours} hours
                  </p>
                )}
              </CardHeader>
              <CardContent>
                {step.prerequisites && step.prerequisites.length > 0 && (
                  <div className="mb-4">
                    <h4 className="text-sm font-medium mb-2">Prerequisites:</h4>
                    <div className="flex flex-wrap gap-1">
                      {step.prerequisites.map((prereq, idx) => (
                        <Badge key={idx} variant="secondary" className="text-xs">
                          {prereq}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant={step.status === 'completed' ? 'secondary' : 'default'}
                    onClick={() => onStepComplete?.(step.id, step.status !== 'completed')}
                  >
                    {step.status === 'completed' ? 'Mark Incomplete' : 'Mark Complete'}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setActiveStep(activeStep === step.id ? null : step.id)}
                  >
                    {activeStep === step.id ? 'Hide Resources' : 'Show Resources'}
                  </Button>
                </div>

                {activeStep === step.id && (
                  <div className="mt-4 pt-4 border-t">
                    <h4 className="text-sm font-medium mb-3">Recommended Resources for "{step.title}":</h4>
                    <div className="space-y-3">
                      {recommendations
                        .filter(resource =>
                          // Match resources based on step content and tags
                          resource.tags?.some(tag =>
                            step.prerequisites?.includes(tag) ||
                            step.title.toLowerCase().includes(tag.toLowerCase()) ||
                            step.description?.toLowerCase().includes(tag.toLowerCase())
                          ) ||
                          // Also match by step-specific resource recommendations from backend
                          (resource as any).step_id === step.id
                        )
                        .slice(0, 3) // Show exactly 3 resources per step as requested
                        .map((resource, index) => {
                          // Ensure we have full resource data
                          const fullResource = {
                            id: resource.id || (resource as any).resource_id,
                            title: resource.title || (resource as any).resource_title,
                            description: resource.description || '',
                            url: resource.url || (resource as any).resource_url,
                            media_type: resource.media_type || (resource as any).resource_type,
                            difficulty: resource.difficulty,
                            duration_minutes: resource.duration_minutes,
                            rating: resource.rating,
                            rating_count: resource.rating_count,
                            tags: resource.tags || [],
                            source: resource.source,
                            recommendation_score: (resource as any).recommendation_score,
                            recommendation_reason: (resource as any).recommendation_reason
                          };
                          return (
                            <div key={fullResource.id} className="border-l-4 border-blue-500 pl-4 py-2 bg-blue-50 rounded-r-lg">
                              <div className="flex justify-between items-start">
                                <div className="flex-1">
                                  <div className="flex items-center gap-2 mb-1">
                                    <span className="bg-blue-100 text-blue-800 px-2 py-0.5 rounded text-xs font-mono">
                                      {index + 1}
                                    </span>
                                    <h5 className="font-medium text-sm">{fullResource.title}</h5>
                                  </div>
                                  <p className="text-xs text-gray-600 mb-2">{fullResource.description}</p>
                                  <div className="flex items-center gap-4 text-xs text-gray-500">
                                    <span className="font-medium">{fullResource.media_type}</span>
                                    <span>{fullResource.source}</span>
                                  </div>
                                </div>
                                <div className="flex flex-col items-end gap-1 ml-4">
                                  <Badge variant="outline" className="text-xs">
                                    {fullResource.difficulty}
                                  </Badge>
                                  <Badge variant="secondary" className="text-xs">
                                    ⭐ {fullResource.rating?.toFixed(1)}
                                  </Badge>
                                  {fullResource.media_type?.toLowerCase() === 'video' && (
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      className="h-6 px-2 text-xs"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        onResourceClick?.(resource);
                                      }}
                                    >
                                      View →
                                    </Button>
                                  )}
                                </div>
                              </div>
                              {fullResource.tags && fullResource.tags.length > 0 && (
                                <div className="flex flex-wrap gap-1 mt-2">
                                  {fullResource.tags.slice(0, 3).map((tag, tagIdx) => (
                                    <Badge key={tagIdx} variant="secondary" className="text-xs">
                                      {tag}
                                    </Badge>
                                  ))}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      {recommendations.filter(resource =>
                        resource.tags?.some(tag =>
                          step.prerequisites?.includes(tag) ||
                          step.title.toLowerCase().includes(tag.toLowerCase()) ||
                          step.description?.toLowerCase().includes(tag.toLowerCase())
                        ) || (resource as any).step_id === step.id
                      ).length === 0 && (
                        <div className="text-center py-4 text-gray-500 text-sm">
                          No specific resources found for this step. Check the general recommendations tab for alternatives.
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="recommendations" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {recommendations.map((resource) => (
              <Card
                key={resource.id}
                className="cursor-pointer hover:shadow-md transition-shadow"
                onClick={() => onResourceClick?.(resource)}
              >
                <CardHeader>
                  <CardTitle className="text-lg">{resource.title}</CardTitle>
                  <CardDescription className="line-clamp-2">
                    {resource.description}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex justify-between items-center mb-2">
                    <Badge variant="outline">{resource.media_type}</Badge>
                    <Badge className={getDifficultyColor(resource.difficulty)}>
                      {resource.difficulty}
                    </Badge>
                  </div>
                  <div className="flex justify-between items-center text-sm">
                    <span>⭐ {resource.rating?.toFixed(1)} ({resource.rating_count})</span>
                    <span>{resource.duration_minutes}min</span>
                  </div>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {resource.tags?.slice(0, 3).map((tag, idx) => (
                      <Badge key={idx} variant="secondary" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}