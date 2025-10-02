import { useQuery } from '@tanstack/react-query';
import { Clock, CheckCircle, XCircle, Code, ArrowRight, Filter } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'wouter';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { submissionsApi, problemsApi } from '@/lib/auth';
import { useAuth } from '@/hooks/use-auth';

export default function Submissions() {
  const [filter, setFilter] = useState<'all' | 'correct' | 'incorrect'>('all');
  const { user } = useAuth();

  const { data: submissions, isLoading: submissionsLoading } = useQuery({
    queryKey: ['/api/submissions/user', user?.id],
    queryFn: () => submissionsApi.getUserSubmissions(user!.id),
    enabled: !!user?.id,
  });

  const { data: problems } = useQuery({
    queryKey: ['/api/problems'],
    queryFn: () => problemsApi.getAll(),
  });

  const filteredSubmissions = submissions?.filter(submission => {
    if (filter === 'correct') return submission.isCorrect;
    if (filter === 'incorrect') return !submission.isCorrect;
    return true;
  }) || [];

  const getProblemTitle = (problemId: string) => {
    return problems?.find(p => p.id === problemId)?.title || 'Unknown Problem';
  };

  const getProblemDifficulty = (problemId: string) => {
    return problems?.find(p => p.id === problemId)?.difficulty || 'Unknown';
  };

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'Easy': return 'bg-green-100 text-green-800';
      case 'Medium': return 'bg-yellow-100 text-yellow-800';
      case 'Hard': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const truncateQuery = (query: string, maxLength: number = 100) => {
    if (query.length <= maxLength) return query;
    return query.substring(0, maxLength).trim() + '...';
  };

  // Calculate stats
  const totalSubmissions = submissions?.length || 0;
  const correctSubmissions = submissions?.filter(s => s.isCorrect).length || 0;
  const successRate = totalSubmissions > 0 ? Math.round((correctSubmissions / totalSubmissions) * 100) : 0;
  const avgExecutionTime = submissions?.length ? 
    Math.round(submissions.reduce((sum, s) => sum + (s.executionTime || 0), 0) / submissions.length) : 0;

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-foreground mb-4">Your Submissions</h1>
          <p className="text-xl text-muted-foreground">Track your SQL training progress and achievements</p>
        </div>

        {/* Stats Overview */}
        <div className="grid md:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardContent className="p-6 text-center">
              <div className="text-3xl font-bold text-primary mb-2" data-testid="stat-total-submissions">
                {totalSubmissions}
              </div>
              <div className="text-sm text-muted-foreground">Total Submissions</div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-6 text-center">
              <div className="text-3xl font-bold text-green-600 mb-2" data-testid="stat-correct-submissions">
                {correctSubmissions}
              </div>
              <div className="text-sm text-muted-foreground">Correct Solutions</div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-6 text-center">
              <div className="text-3xl font-bold text-blue-600 mb-2" data-testid="stat-success-rate">
                {successRate}%
              </div>
              <div className="text-sm text-muted-foreground">Success Rate</div>
            </CardContent>
          </Card>
          
          <Card>
            <CardContent className="p-6 text-center">
              <div className="text-3xl font-bold text-orange-600 mb-2" data-testid="stat-avg-time">
                {avgExecutionTime}ms
              </div>
              <div className="text-sm text-muted-foreground">Avg Execution Time</div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <div className="flex items-center space-x-4 mb-6">
          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm font-medium text-foreground">Filter:</span>
          </div>
          <div className="bg-white border border-border rounded-lg p-1 inline-flex">
            <Button
              variant={filter === 'all' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setFilter('all')}
              className={filter === 'all' ? 'bg-primary text-primary-foreground' : ''}
              data-testid="button-filter-all"
            >
              All ({totalSubmissions})
            </Button>
            <Button
              variant={filter === 'correct' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setFilter('correct')}
              className={filter === 'correct' ? 'bg-primary text-primary-foreground' : ''}
              data-testid="button-filter-correct"
            >
              Correct ({correctSubmissions})
            </Button>
            <Button
              variant={filter === 'incorrect' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setFilter('incorrect')}
              className={filter === 'incorrect' ? 'bg-primary text-primary-foreground' : ''}
              data-testid="button-filter-incorrect"
            >
              Incorrect ({totalSubmissions - correctSubmissions})
            </Button>
          </div>
        </div>

        {/* Submissions List */}
        {submissionsLoading ? (
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <Card key={i} className="animate-pulse">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="space-y-3 flex-1">
                      <div className="h-4 bg-muted rounded w-1/3" />
                      <div className="h-3 bg-muted rounded w-1/2" />
                      <div className="h-16 bg-muted rounded" />
                    </div>
                    <div className="ml-4 space-y-2">
                      <div className="h-6 bg-muted rounded w-20" />
                      <div className="h-4 bg-muted rounded w-16" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : filteredSubmissions.length === 0 ? (
          <Card>
            <CardContent className="p-12 text-center">
              <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
                <Code className="w-8 h-8 text-muted-foreground" />
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-2">
                {filter === 'all' ? 'No submissions yet' : `No ${filter} submissions`}
              </h3>
              <p className="text-muted-foreground mb-6">
                {filter === 'all' 
                  ? 'Start solving problems to see your submission history here!'
                  : `You haven't made any ${filter} submissions yet.`}
              </p>
              {filter === 'all' && (
                <Link href="/problems">
                  <Button className="dumbbell-btn bg-primary text-primary-foreground hover:bg-primary/90" data-testid="button-start-solving">
                    Start Solving Problems
                  </Button>
                </Link>
              )}
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {filteredSubmissions.map((submission, index) => (
              <Card key={submission.id} className="hover:shadow-md transition-shadow" data-testid={`submission-${index}`}>
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      {/* Header */}
                      <div className="flex items-center space-x-3 mb-3">
                        <div className={`flex items-center justify-center w-8 h-8 rounded-full ${
                          submission.isCorrect ? 'bg-green-100' : 'bg-red-100'
                        }`}>
                          {submission.isCorrect ? (
                            <CheckCircle className="w-5 h-5 text-green-600" />
                          ) : (
                            <XCircle className="w-5 h-5 text-red-600" />
                          )}
                        </div>
                        
                        <div className="flex-1">
                          <Link href={`/problems/${submission.problemId}`}>
                            <h3 className="font-semibold text-foreground hover:text-primary transition-colors cursor-pointer" data-testid={`text-problem-title-${index}`}>
                              {getProblemTitle(submission.problemId)}
                            </h3>
                          </Link>
                          <div className="flex items-center space-x-3 mt-1">
                            <Badge className={getDifficultyColor(getProblemDifficulty(submission.problemId))}>
                              {getProblemDifficulty(submission.problemId)}
                            </Badge>
                            <div className="flex items-center space-x-1 text-sm text-muted-foreground">
                              <Clock className="w-3 h-3" />
                              <span data-testid={`text-submission-date-${index}`}>
                                {formatDate(submission.submittedAt)}
                              </span>
                            </div>
                            {submission.executionTime && (
                              <span className="text-sm text-muted-foreground" data-testid={`text-execution-time-${index}`}>
                                {submission.executionTime}ms
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Query Preview */}
                      <div className="bg-muted rounded-lg p-3 mb-3">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-foreground">SQL Query</span>
                          <Badge variant="outline" className={
                            submission.isCorrect ? 'text-green-700 border-green-300' : 'text-red-700 border-red-300'
                          }>
                            {submission.isCorrect ? 'Correct' : 'Incorrect'}
                          </Badge>
                        </div>
                        <pre className="text-sm text-muted-foreground font-mono overflow-x-auto">
                          <code data-testid={`code-query-${index}`}>
                            {truncateQuery(submission.query)}
                          </code>
                        </pre>
                        {submission.query.length > 100 && (
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="mt-2 text-primary hover:bg-primary/10"
                            data-testid={`button-view-full-${index}`}
                          >
                            View Full Query
                          </Button>
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="ml-4 flex flex-col space-y-2">
                      <Link href={`/problems/${submission.problemId}`}>
                        <Button 
                          variant="outline" 
                          size="sm"
                          className="w-full"
                          data-testid={`button-view-problem-${index}`}
                        >
                          View Problem
                          <ArrowRight className="ml-2 w-3 h-3" />
                        </Button>
                      </Link>
                      
                      {!submission.isCorrect && (
                        <Link href={`/problems/${submission.problemId}`}>
                          <Button 
                            variant="outline" 
                            size="sm"
                            className="w-full text-primary border-primary hover:bg-primary/10"
                            data-testid={`button-retry-${index}`}
                          >
                            Try Again
                          </Button>
                        </Link>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
