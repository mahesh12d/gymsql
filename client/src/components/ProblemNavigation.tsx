import { memo, useCallback } from 'react';
import { ArrowLeft, ChevronLeft, ChevronRight, Users, Star, Lock, Bookmark, ThumbsUp, ThumbsDown } from 'lucide-react';
import { Link } from 'wouter';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { problemsApi } from '@/lib/auth';
import { useAuth } from '@/hooks/use-auth';
import { useToast } from '@/hooks/use-toast';

interface Problem {
  id?: string;
  title?: string;
  likes?: number; // For backward compatibility
  upvotesCount?: number;
  company?: string;
  difficulty?: string;
  premium?: boolean | null;
  isBookmarked?: boolean;
  isLiked?: boolean; // For backward compatibility
  isUpvoted?: boolean;
  isDownvoted?: boolean;
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
  const { user } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Memoized calculation for solved status
  const isSolved = useCallback(() => {
    return userSubmissions?.some((sub) => sub.isCorrect) || false;
  }, [userSubmissions]);

  // Bookmark mutation
  const bookmarkMutation = useMutation({
    mutationFn: async () => {
      if (!problem?.id) throw new Error("No problem ID");
      return problemsApi.toggleBookmark(problem.id);
    },
    onSuccess: () => {
      // Invalidate and refetch problem data to get updated bookmark status
      queryClient.invalidateQueries({
        queryKey: ["/api/problems", problem?.id],
      });
      toast({
        title: problem?.isBookmarked ? "Bookmark removed" : "Problem bookmarked",
        description: problem?.isBookmarked 
          ? "Problem removed from your bookmarks" 
          : "Problem added to your bookmarks",
      });
    },
    onError: (error) => {
      toast({
        title: "Failed to update bookmark",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    },
  });

  // Upvote mutation
  const upvoteMutation = useMutation({
    mutationFn: async () => {
      if (!problem?.id) throw new Error("No problem ID");
      return problemsApi.toggleUpvote(problem.id);
    },
    onSuccess: () => {
      // Invalidate and refetch problem data to get updated vote status
      queryClient.invalidateQueries({
        queryKey: ["/api/problems", problem?.id],
      });
      toast({
        title: problem?.isUpvoted ? "Upvote removed" : "Problem upvoted",
        description: problem?.isUpvoted 
          ? "You removed your upvote from this problem" 
          : "You upvoted this problem",
      });
    },
    onError: (error) => {
      toast({
        title: "Failed to update upvote",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    },
  });

  // Downvote mutation
  const downvoteMutation = useMutation({
    mutationFn: async () => {
      if (!problem?.id) throw new Error("No problem ID");
      return problemsApi.toggleDownvote(problem.id);
    },
    onSuccess: () => {
      // Invalidate and refetch problem data to get updated vote status
      queryClient.invalidateQueries({
        queryKey: ["/api/problems", problem?.id],
      });
      toast({
        title: problem?.isDownvoted ? "Downvote removed" : "Problem downvoted",
        description: problem?.isDownvoted 
          ? "You removed your downvote from this problem" 
          : "You downvoted this problem",
      });
    },
    onError: (error) => {
      toast({
        title: "Failed to update downvote",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    },
  });

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
              <div className="flex items-center gap-2">
                {problem.premium && (
                  <Lock className="w-4 h-4 text-amber-500" />
                )}
                <h1 className="text-lg font-semibold" data-testid="text-problem-title">
                  {problem.title || 'Untitled Problem'}
                </h1>
              </div>
              {isSolved() && (
                <Badge variant="secondary" className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                  ✓ Solved
                </Badge>
              )}
            </div>
          </>
        )}
      </div>

      {/* Right: Problem Stats + Bookmark/Like Actions + Navigation */}
      <div className="flex items-center space-x-4">
        {problem && user && (
          <>
            {/* Bookmark, Upvote and Downvote Buttons */}
            <div className="flex items-center space-x-2">
              <Button
                onClick={() => bookmarkMutation.mutate()}
                disabled={bookmarkMutation.isPending}
                variant="ghost"
                size="sm"
                className={`h-8 w-8 p-0 ${problem.isBookmarked ? 'text-green-700 dark:text-green-400' : 'text-muted-foreground'}`}
                data-testid="button-bookmark"
              >
                <Bookmark className={`h-4 w-4 ${problem.isBookmarked ? 'fill-current' : ''}`} />
              </Button>
              
              <div className="flex items-center space-x-1">
                <Button
                  onClick={() => upvoteMutation.mutate()}
                  disabled={upvoteMutation.isPending}
                  variant="ghost"
                  size="sm"
                  className={`h-8 w-8 p-0 ${problem.isUpvoted ? 'text-green-600 dark:text-green-400' : 'text-muted-foreground'}`}
                  data-testid="button-upvote"
                >
                  <ThumbsUp className={`h-4 w-4 ${problem.isUpvoted ? 'fill-current' : ''}`} />
                </Button>
                
                {/* Show upvote count */}
                {(problem.upvotesCount && problem.upvotesCount > 0) && (
                  <span className="text-sm text-muted-foreground min-w-[1rem]">
                    {problem.upvotesCount}
                  </span>
                )}
                
                <Button
                  onClick={() => downvoteMutation.mutate()}
                  disabled={downvoteMutation.isPending}
                  variant="ghost"
                  size="sm"
                  className={`h-8 w-8 p-0 ${problem.isDownvoted ? 'text-red-600 dark:text-red-400' : 'text-muted-foreground'}`}
                  data-testid="button-downvote"
                >
                  <ThumbsDown className={`h-4 w-4 ${problem.isDownvoted ? 'fill-current' : ''}`} />
                </Button>
              </div>
            </div>
            
            {/* Problem Stats */}
            <div className="flex items-center space-x-3 text-sm text-muted-foreground">
              <div className="flex items-center space-x-1">
                <Users className="h-3 w-3" />
                <span>2.1k</span>
              </div>
              <div className="flex items-center space-x-1">
                <ThumbsUp className="h-3 w-3" />
                <span>{problem.upvotesCount || problem.likes || 0}</span>
              </div>
            </div>

            <div className="h-4 w-px bg-border"></div>
          </>
        )}
        
        {problem && !user && (
          <>
            {/* Problem Stats for non-logged in users */}
            <div className="flex items-center space-x-3 text-sm text-muted-foreground">
              <div className="flex items-center space-x-1">
                <Users className="h-3 w-3" />
                <span>2.1k</span>
              </div>
              <div className="flex items-center space-x-1">
                <ThumbsUp className="h-3 w-3" />
                <span>{problem.upvotesCount || problem.likes || 0}</span>
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