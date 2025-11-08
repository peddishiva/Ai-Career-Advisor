'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, AlertCircle, TrendingUp, Award, BookOpen } from 'lucide-react';

export default function AnalysisResults({ analysis, detailed = false }) {
  if (!analysis) {
    return (
      <div className="text-center py-6 text-muted-foreground">
        No analysis data available. Upload a resume to get started.
      </div>
    );
  }

  const { skills = [], experience, education, strengths = [], areasForImprovement = [] } = analysis;

  const renderSkills = () => (
    <div className="space-y-2">
      <h3 className="font-medium flex items-center gap-2">
        <Award className="h-4 w-4 text-primary" />
        Key Skills
      </h3>
      <div className="flex flex-wrap gap-2">
        {skills.map((skill, index) => (
          <Badge key={index} variant="secondary" className="text-sm">
            {skill}
          </Badge>
        ))}
      </div>
    </div>
  );

  const renderExperience = () => (
    <div className="space-y-2">
      <h3 className="font-medium flex items-center gap-2">
        <TrendingUp className="h-4 w-4 text-primary" />
        Professional Experience
      </h3>
      <p className="text-sm">{experience || 'No experience information available'}</p>
    </div>
  );

  const renderEducation = () => (
    <div className="space-y-2">
      <h3 className="font-medium flex items-center gap-2">
        <BookOpen className="h-4 w-4 text-primary" />
        Education
      </h3>
      <p className="text-sm">{education || 'No education information available'}</p>
    </div>
  );

  const renderStrengths = () => {
    if (!detailed) return null;
    
    return (
      <div className="space-y-2">
        <h3 className="font-medium flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-green-500" />
          Key Strengths
        </h3>
        <ul className="space-y-1 text-sm">
          {strengths.map((strength, index) => (
            <li key={index} className="flex items-start gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
              <span>{strength}</span>
            </li>
          ))}
        </ul>
      </div>
    );
  };

  const renderAreasForImprovement = () => {
    if (!detailed) return null;
    
    return (
      <div className="space-y-2">
        <h3 className="font-medium flex items-center gap-2">
          <AlertCircle className="h-4 w-4 text-amber-500" />
          Areas for Improvement
        </h3>
        <ul className="space-y-1 text-sm">
          {areasForImprovement.map((area, index) => (
            <li key={index} className="flex items-start gap-2">
              <AlertCircle className="h-4 w-4 text-amber-500 mt-0.5 flex-shrink-0" />
              <span>{area}</span>
            </li>
          ))}
        </ul>
      </div>
    );
  };

  if (detailed) {
    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Skills & Qualifications</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {renderSkills()}
            <div className="grid gap-4 md:grid-cols-2">
              {renderExperience()}
              {renderEducation()}
            </div>
          </CardContent>
        </Card>
        
        <div className="grid gap-6 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Strengths</CardTitle>
            </CardHeader>
            <CardContent>
              {strengths.length > 0 ? (
                <ul className="space-y-2">
                  {strengths.map((strength, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
                      <span>{strength}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-muted-foreground">No strengths identified yet.</p>
              )}
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle>Areas for Improvement</CardTitle>
            </CardHeader>
            <CardContent>
              {areasForImprovement.length > 0 ? (
                <ul className="space-y-2">
                  {areasForImprovement.map((area, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <AlertCircle className="h-4 w-4 text-amber-500 mt-0.5 flex-shrink-0" />
                      <span>{area}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-muted-foreground">No specific areas for improvement identified.</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  // Default (overview) view
  return (
    <div className="space-y-4">
      {renderSkills()}
      <div className="grid gap-4 md:grid-cols-2">
        {renderExperience()}
        {renderEducation()}
      </div>
      {renderStrengths()}
      {renderAreasForImprovement()}
    </div>
  );
}
