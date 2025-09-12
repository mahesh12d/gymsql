import { useParams } from 'wouter';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Users, Star, Lightbulb } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'wouter';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';

import { problemsApi, submissionsApi } from '@/lib/auth';
import { useAuth } from '@/hooks/use-auth';
import { useToast } from '@/hooks/use-toast';
import SQLEditor from '@/components/sql-editor';
import TableDisplay from '@/components/table-display';
import ResizableSplitter from '@/components/resizable-splitter';


export default function ProblemDetail() {
  const params = useParams();
  const problemId = params.id as string;
  const { user } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [showHint, setShowHint] = useState(false);
  const [hintIndex, setHintIndex] = useState(0);

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

  // Run Code - Non-persistent evaluation (no auth required)
  const handleRunQuery = async (query: string) => {
    // For now, return a mock evaluation result
    // In a real app, this would call a separate evaluation endpoint
    await new Promise(resolve => setTimeout(resolve, 800)); // Simulate processing
    return {
      isCorrect: false,
      message: 'Query executed successfully. Use "Check Solution" to submit your final answer.',
      executionTime: Math.floor(Math.random() * 50) + 10,
    };
  };
  
  // Check Solution - Persistent submission (auth required)
  const handleSubmitSolution = async (query: string) => {
    if (!user) {
      toast({
        title: 'Authentication required',
        description: 'Please log in to submit solutions.',
        variant: 'destructive',
      });
      throw new Error('Authentication required');
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

  const handleShowHint = () => {
    setShowHint(true);
  };

  const handleNextHint = () => {
    if (problem?.hints && hintIndex < problem.hints.length - 1) {
      setHintIndex(hintIndex + 1);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Back Button Only */}
        <div className="mb-4">
          <Link href="/problems">
            <Button variant="ghost" data-testid="button-back">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Problems
            </Button>
          </Link>
        </div>

        <ResizableSplitter
          defaultLeftWidth={45}
          className="h-[calc(100vh-120px)]" 
          leftPanel={
            <div className="h-full flex flex-col overflow-hidden">
              {/* Question Panel */}
              <div className="flex-1 space-y-6 p-6 overflow-auto">
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-4">
                        <h1 className="text-2xl font-bold text-foreground" data-testid="text-problem-title">
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
                    </div>
                    <div className="flex items-center space-x-6 text-sm text-muted-foreground mt-2">
                      <div className="flex items-center space-x-1">
                        <Users className="w-4 h-4" />
                        <span data-testid="text-solved-count">{problem.solvedCount} solved</span>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    {/* Problem Description */}
                    <div>
                      <div className="text-foreground leading-relaxed mb-6 prose prose-sm max-w-none" data-testid="text-problem-description">
                        <ReactMarkdown 
                          remarkPlugins={[remarkGfm]}
                          components={{
                            h1: ({children}) => <h1 className="text-2xl font-bold mb-4">{children}</h1>,
                            h2: ({children}) => <h2 className="text-xl font-semibold mb-3">{children}</h2>,
                            h3: ({children}) => <h3 className="text-lg font-medium mb-2">{children}</h3>,
                            p: ({children}) => <p className="mb-4 leading-relaxed">{children}</p>,
                            ul: ({children}) => <ul className="list-disc list-inside mb-4 space-y-1">{children}</ul>,
                            ol: ({children}) => <ol className="list-decimal list-inside mb-4 space-y-1">{children}</ol>,
                            li: ({children}) => <li className="text-foreground">{children}</li>,
                            code: ({children, className}) => {
                              const isInline = !className;
                              if (isInline) {
                                return <code className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono text-foreground">{children}</code>;
                              }
                              return <code className="bg-muted text-sm font-mono block">{children}</code>;
                            },
                            pre: ({children}) => <pre className="bg-muted p-4 rounded-lg overflow-x-auto mb-4 text-sm font-mono">{children}</pre>,
                            blockquote: ({children}) => <blockquote className="border-l-4 border-primary bg-muted/50 pl-4 pr-4 py-3 my-4 rounded-r-lg">{children}</blockquote>,
                            strong: ({children}) => <strong className="font-semibold text-foreground">{children}</strong>,
                            em: ({children}) => <em className="italic text-muted-foreground">{children}</em>,
                            table: ({children}) => <div className="overflow-x-auto my-4"><table className="min-w-full border-collapse border border-muted">{children}</table></div>,
                            thead: ({children}) => <thead className="bg-muted/50">{children}</thead>,
                            tbody: ({children}) => <tbody>{children}</tbody>,
                            tr: ({children}) => <tr className="border-b border-muted">{children}</tr>,
                            th: ({children}) => <th className="border border-muted px-3 py-2 text-left font-semibold">{children}</th>,
                            td: ({children}) => <td className="border border-muted px-3 py-2">{children}</td>,
                          }}
                        >
                          {problem.question?.description || ''}
                        </ReactMarkdown>
                      </div>
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
              
              {/* Hints Section - At Bottom of Left Panel */}
              <div className="flex-shrink-0 p-6 pt-0">
                {problem?.hints && problem.hints.length > 0 && (
                  <div className="space-y-3">
                    <Button 
                      onClick={handleShowHint}
                      variant="outline"
                      className="w-full text-primary hover:bg-primary/10"
                      data-testid="button-show-hint"
                    >
                      <Lightbulb className="mr-2 h-4 w-4" />
                      Show Hints
                    </Button>
                    
                    {showHint && (
                      <Alert className="border-primary/20 bg-primary/10">
                        <Lightbulb className="h-4 w-4 text-primary" />
                        <AlertDescription className="text-foreground">
                          <strong>💡 Hint {hintIndex + 1}:</strong> {problem.hints[hintIndex]}
                          {hintIndex < problem.hints.length - 1 && (
                            <Button 
                              onClick={handleNextHint}
                              variant="link" 
                              className="p-0 ml-2 text-primary"
                              data-testid="button-next-hint"
                            >
                              Next hint →
                            </Button>
                          )}
                        </AlertDescription>
                      </Alert>
                    )}
                  </div>
                )}
              </div>
            </div>
          }
          rightPanel={
            <div className="h-full">
              <SQLEditor
                initialQuery={problem?.question?.starterQuery || ''}
                onRunQuery={handleRunQuery}
                onSubmitSolution={handleSubmitSolution}
                className="h-full"
              />
            </div>
          }
        />
      </div>
    </div>
  );
}
