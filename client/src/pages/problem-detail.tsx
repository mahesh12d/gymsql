import { useParams } from 'wouter';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Users, Star, Lightbulb } from 'lucide-react';
import { Link } from 'wouter';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { problemsApi, submissionsApi } from '@/lib/auth';
import { useAuth } from '@/hooks/use-auth';
import { useToast } from '@/hooks/use-toast';
import SQLEditor from '@/components/sql-editor';
import TableDisplay from '@/components/table-display';

export default function ProblemDetail() {
  const params = useParams();
  const problemId = params.id as string;
  const { user } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: problem, isLoading: problemLoading } = useQuery({
    queryKey: ['/api/problems', problemId],
    queryFn: () => problemsApi.getById(problemId),
    enabled: !!problemId,
  });

  const { data: userSubmissions } = useQuery({
    queryKey: ['/api/submissions/user', user?.id, problemId],
    queryFn: () => submissionsApi.getUserSubmissions(user!.id),
    enabled: !!user?.id,
    select: (submissions) => submissions.filter(s => s.problemId === problemId),
  });

  const submitMutation = useMutation({
    mutationFn: (query: string) => submissionsApi.create({ problemId, query }),
    onSuccess: (result) => {
      toast({
        title: result.isCorrect ? 'Success!' : 'Query Executed',
        description: result.message,
        variant: result.isCorrect ? 'default' : 'destructive',
      });
      
      // Invalidate relevant queries
      queryClient.invalidateQueries({ queryKey: ['/api/submissions/user'] });
      if (result.isCorrect) {
        queryClient.invalidateQueries({ queryKey: ['/api/auth/user'] });
        queryClient.invalidateQueries({ queryKey: ['/api/problems', problemId] });
      }
    },
    onError: (error) => {
      toast({
        title: 'Submission failed',
        description: error instanceof Error ? error.message : 'Please try again.',
        variant: 'destructive',
      });
    },
  });

  const handleRunQuery = async (query: string) => {
    if (!user) {
      toast({
        title: 'Authentication required',
        description: 'Please log in to submit solutions.',
        variant: 'destructive',
      });
      return;
    }
    
    return submitMutation.mutateAsync(query);
  };

  if (problemLoading) {
    return (
      <div className="min-h-screen bg-background">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="animate-pulse space-y-8">
            <div className="h-8 bg-muted rounded w-1/4" />
            <div className="grid lg:grid-cols-2 gap-8">
              <div className="space-y-6">
                <div className="h-6 bg-muted rounded w-3/4" />
                <div className="h-4 bg-muted rounded" />
                <div className="h-4 bg-muted rounded w-5/6" />
                <div className="h-32 bg-muted rounded" />
              </div>
              <div className="space-y-6">
                <div className="h-6 bg-muted rounded w-1/2" />
                <div className="h-64 bg-muted rounded" />
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!problem) {
    return (
      <div className="min-h-screen bg-background">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center py-12">
            <h1 className="text-2xl font-bold text-foreground mb-4">Problem not found</h1>
            <p className="text-muted-foreground mb-6">The problem you're looking for doesn't exist.</p>
            <Link href="/problems">
              <Button data-testid="button-back-to-problems">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Problems
              </Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'Easy': return 'bg-green-100 text-green-800';
      case 'Medium': return 'bg-yellow-100 text-yellow-800';
      case 'Hard': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const hasCorrectSubmission = userSubmissions?.some(s => s.isCorrect) || false;

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <Link href="/problems">
            <Button variant="ghost" className="mb-4" data-testid="button-back">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Problems
            </Button>
          </Link>
          
          <div className="flex items-center space-x-4 mb-4">
            <h1 className="text-3xl font-bold text-foreground" data-testid="text-problem-title">
              {problem.title}
            </h1>
            <Badge className={getDifficultyColor(problem.difficulty)}>
              {problem.difficulty}
            </Badge>
            {hasCorrectSubmission && (
              <Badge className="bg-green-100 text-green-800">
                ✓ Solved
              </Badge>
            )}
          </div>
          
          <div className="flex items-center space-x-6 text-sm text-muted-foreground">
            <div className="flex items-center space-x-1">
              <Users className="w-4 h-4" />
              <span data-testid="text-solved-count">{problem.solvedCount} solved</span>
            </div>
          </div>
        </div>

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Single Question Block - Now displays structured table format */}
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Question</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Problem Description */}
                <div>
                  <p className="text-foreground leading-relaxed mb-6" data-testid="text-problem-description">
                    {problem.question?.description}
                  </p>
                </div>

                {/* Structured Table Display */}
                <TableDisplay 
                  tables={problem.question?.tables || []} 
                  expectedOutput={problem.question?.expectedOutput || []}
                />
              </CardContent>
            </Card>

            {/* Tags */}
            {problem.tags && problem.tags.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Tags</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {problem.tags.map((tag: string, index: number) => (
                      <Badge key={index} variant="outline" data-testid={`tag-${tag}`}>
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Previous Submissions */}
            {userSubmissions && userSubmissions.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Your Submissions</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {userSubmissions.slice(0, 5).map((submission, index) => (
                      <div 
                        key={submission.id} 
                        className="flex items-center justify-between p-3 bg-muted rounded-lg"
                        data-testid={`submission-${index}`}
                      >
                        <div className="flex items-center space-x-3">
                          <div className={`w-3 h-3 rounded-full ${
                            submission.isCorrect ? 'bg-green-500' : 'bg-red-500'
                          }`} />
                          <span className="text-sm font-medium">
                            {submission.isCorrect ? 'Correct' : 'Incorrect'}
                          </span>
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {new Date(submission.submittedAt).toLocaleDateString()}
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* SQL Editor */}
          <div>
            <SQLEditor
              onRunQuery={handleRunQuery}
              hints={problem.hints || []}
              className="sticky top-8"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
