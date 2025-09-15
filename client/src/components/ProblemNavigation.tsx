import { memo, useCallback } from 'react';
import { ArrowLeft, ChevronLeft, ChevronRight, Users, Star } from 'lucide-react';
import { Link } from 'wouter';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface Problem {
  id?: string;
  title?: string;
  likes?: number;
  company?: string;
  difficulty?: string;
}

interface ProblemNavigationProps {
  problem?: Problem;
  userSubmissions?: any[];
  onPrevious?: () => void;
  onNext?: () => void;
  hasPrevious?: boolean;
  hasNext?: boolean;
  className?: string;
}

const ProblemNavigation = memo(function ProblemNavigation({
  problem,
  userSubmissions = [],
  onPrevious,
  onNext,
  hasPrevious = false,
  hasNext = false,
  className,
}: ProblemNavigationProps) {
  // Memoized calculation for solved status
  const isSolved = useCallback(() => {
    return userSubmissions?.some((sub) => sub.isCorrect) || false;
  }, [userSubmissions]);

  const handlePrevious = useCallback(() => {
    if (hasPrevious && onPrevious) {
      onPrevious();
    }
  }, [hasPrevious, onPrevious]);

  const handleNext = useCallback(() => {
    if (hasNext && onNext) {
      onNext();
    }
  }, [hasNext, onNext]);

  return (
    <div className={`flex items-center justify-between py-4 px-6 border-b ${className || ''}`}>
      {/* Left: Back to Problems + Title */}
      <div className="flex items-center space-x-4">
        <Link to="/problems">
          <Button
            variant="ghost"
            size="sm"
            className="text-muted-foreground hover:text-foreground"
            data-testid="button-back-to-problems"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Problems
          </Button>
        </Link>

        {problem && (
          <>
            <div className="h-4 w-px bg-border"></div>
            <div className="flex items-center space-x-3">
              <h1 className="text-lg font-semibold" data-testid="text-problem-title">
                {problem.title || 'Untitled Problem'}
              </h1>
              {isSolved() && (
                <Badge variant="secondary" className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                  ✓ Solved
                </Badge>
              )}
            </div>
          </>
        )}
      </div>

      {/* Right: Problem Stats + Navigation */}
      <div className="flex items-center space-x-4">
        {problem && (
          <>
            {/* Problem Stats */}
            <div className="flex items-center space-x-3 text-sm text-muted-foreground">
              <div className="flex items-center space-x-1">
                <Users className="h-3 w-3" />
                <span>2.1k</span>
              </div>
              <div className="flex items-center space-x-1">
                <Star className="h-3 w-3" />
                <span>{problem.likes || 0}</span>
              </div>
            </div>

            <div className="h-4 w-px bg-border"></div>
          </>
        )}

        {/* Navigation Controls */}
        <div className="flex items-center space-x-2">
          <Button
            onClick={handlePrevious}
            disabled={!hasPrevious}
            variant="outline"
            size="sm"
            className="h-8 w-8 p-0"
            data-testid="button-previous-problem"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button
            onClick={handleNext}
            disabled={!hasNext}
            variant="outline"
            size="sm"
            className="h-8 w-8 p-0"
            data-testid="button-next-problem"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
});

export default ProblemNavigation;