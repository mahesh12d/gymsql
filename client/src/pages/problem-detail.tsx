import { useParams } from 'wouter';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Users, Star, Lightbulb, Play, Save, TrendingUp } from 'lucide-react';
import { useState, useMemo, useCallback, useEffect } from 'react';
import { Link } from 'wouter';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import CodeMirror from '@uiw/react-codemirror';
import { sql, PostgreSQL } from '@codemirror/lang-sql';
import { autocompletion } from '@codemirror/autocomplete';
import { EditorView, keymap, placeholder } from '@codemirror/view';
import { defaultKeymap, indentWithTab } from '@codemirror/commands';
import { oneDark } from '@codemirror/theme-one-dark';
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
import VerticalResizableSplitter from '@/components/vertical-resizable-splitter';

// Editor and Output Split Component
function EditorOutputSplit({ 
  problem, 
  handleRunQuery, 
  handleSubmitSolution 
}: {
  problem: any;
  handleRunQuery: (query: string) => Promise<any>;
  handleSubmitSolution: (query: string) => Promise<any>;
}) {
  const [query, setQuery] = useState(problem?.question?.starterQuery || '');
  const [result, setResult] = useState<any>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showOutput, setShowOutput] = useState(false);

  // Detect dark mode with reactivity
  const [isDarkMode, setIsDarkMode] = useState(() => {
    if (typeof window !== 'undefined') {
      return document.documentElement.classList.contains('dark');
    }
    return false;
  });

  useEffect(() => {
    const observer = new MutationObserver(() => {
      setIsDarkMode(document.documentElement.classList.contains('dark'));
    });
    
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class']
    });
    
    return () => observer.disconnect();
  }, []);

  const handleRun = useCallback(async () => {
    if (!query.trim()) return;
    
    setIsRunning(true);
    setShowOutput(true);
    try {
      const runResult = await handleRunQuery(query);
      setResult(runResult);
    } catch (error) {
      setResult({
        error: true,
        message: error instanceof Error ? error.message : 'Query execution failed',
      });
    } finally {
      setIsRunning(false);
    }
  }, [query, handleRunQuery]);

  const handleSubmit = useCallback(async () => {
    if (!query.trim()) return;
    
    setIsSubmitting(true);
    setShowOutput(true);
    try {
      const submitResult = await handleSubmitSolution(query);
      setResult(submitResult);
      localStorage.setItem('sqlgym_last_query', query);
    } catch (error) {
      setResult({
        error: true,
        message: error instanceof Error ? error.message : 'Submission failed',
      });
    } finally {
      setIsSubmitting(false);
    }
  }, [query, handleSubmitSolution]);

  // Configure CodeMirror extensions and theme
  const extensions = useMemo(() => [
    sql({
      dialect: PostgreSQL,
      upperCaseKeywords: true,
      schema: {
        customers: ['id', 'name', 'email'],
        employees: ['id', 'name', 'department'],
        orders: ['id', 'customer_id', 'total'],
        order_items: ['id', 'order_id', 'price', 'quantity'],
      }
    }),
    autocompletion(),
    EditorView.lineWrapping,
    placeholder('-- Write your SQL query here\nSELECT \n    column1,\n    column2\nFROM table_name\nWHERE condition;'),
    keymap.of([
      ...defaultKeymap,
      indentWithTab,
      {
        key: 'Mod-Enter',
        run: () => {
          handleRun();
          return true;
        }
      }
    ])
  ], [handleRun]);

  const theme = useMemo(() => {
    if (isDarkMode) {
      return [oneDark];
    }
    return [
      EditorView.theme({
        '&': {
          color: 'hsl(var(--foreground))',
          backgroundColor: 'hsl(var(--background))',
        },
        '.cm-content': {
          padding: '16px',
          fontSize: '14px',
          fontFamily: 'var(--font-mono)',
          minHeight: '200px',
        },
        '.cm-focused': {
          outline: 'none',
        },
        '.cm-editor': {
          borderRadius: '0',
        },
        '.cm-scroller': {
          fontFamily: 'var(--font-mono)',
        },
        '.cm-line': {
          lineHeight: '1.5',
        },
        '&.cm-focused .cm-cursor': {
          borderLeftColor: 'hsl(var(--primary))',
        },
        '&.cm-focused .cm-selectionBackground, .cm-selectionBackground': {
          backgroundColor: 'hsl(var(--primary) / 0.2)',
        }
      })
    ];
  }, [isDarkMode]);

  // Editor panel
  const editorPanel = (
    <div className="h-full flex flex-col">
      <div className="flex-1 flex flex-col min-h-0">
        <Card className="flex-1 flex flex-col overflow-hidden rounded-none border-0 border-b">
          <CardHeader className="bg-muted/50 px-6 py-4 border-b border-border flex-shrink-0">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <span className="text-lg font-semibold text-foreground">Code</span>
              </div>
              <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                <span>PostgreSQL 14</span>
              </div>
            </div>
          </CardHeader>
          
          <CardContent className="p-0 flex-1 min-h-0">
            <CodeMirror
              value={query}
              onChange={(value) => setQuery(value)}
              height="100%"
              theme={theme}
              extensions={extensions}
              basicSetup={{
                lineNumbers: true,
                foldGutter: true,
                dropCursor: false,
                allowMultipleSelections: false,
                indentOnInput: true,
                bracketMatching: true,
                closeBrackets: true,
                autocompletion: false,
                highlightSelectionMatches: false,
                searchKeymap: true,
                tabSize: 2,
              }}
              data-testid="editor-sql"
              className="sqlgym-editor h-full"
            />
          </CardContent>
        </Card>
      </div>
      
      {/* Action Buttons */}
      <div className="flex-shrink-0 p-4 bg-muted/30 border-b border-border">
        <div className="flex justify-end gap-3">
          <Button
            onClick={handleRun}
            disabled={isRunning || !query.trim()}
            className="bg-primary text-primary-foreground hover:bg-primary/90 font-semibold"
            data-testid="button-run-query"
          >
            <Play className="mr-2 h-4 w-4" />
            {isRunning ? 'Running...' : 'Run Code'}
          </Button>
          
          <Button 
            onClick={handleSubmit} 
            disabled={isSubmitting || !query.trim()}
            className="bg-green-600 hover:bg-green-700 text-white font-semibold"
            data-testid="button-submit"
          >
            <Save className="mr-2 h-4 w-4" />
            {isSubmitting ? 'Submitting...' : 'Check Solution'}
          </Button>
        </div>
      </div>
    </div>
  );

  // Output panel
  const outputPanel = (
    <Card className="h-full rounded-none border-0">
      <CardHeader className="bg-muted/50 px-6 py-3 border-b border-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <TrendingUp className="h-4 w-4 text-primary" />
            <span className="font-semibold text-foreground">Output</span>
          </div>
          <div className="text-sm text-muted-foreground">
            {result?.executionTime && `Execution time: ${result.executionTime || 0.01604} seconds`}
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="p-6 h-full overflow-auto">
        {!result ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="text-4xl mb-4">⚡</div>
            <p className="text-muted-foreground">Ready to execute!</p>
            <p className="text-sm text-muted-foreground mt-2">Use Alt + Enter to run query</p>
          </div>
        ) : result.error ? (
          <div className="space-y-4">
            <div className="flex items-center space-x-3 text-red-600">
              <div className="w-3 h-3 bg-red-500 rounded-full"></div>
              <span className="font-medium">Query Failed</span>
            </div>
            <div className="bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg p-4">
              <p className="text-red-800 dark:text-red-200 text-sm font-mono">{result.message}</p>
            </div>
            <p className="text-sm text-muted-foreground">Check your query and try again.</p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3 text-green-600">
                <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                <span className="font-medium">
                  {result.isCorrect ? 'Perfect! 🏆' : 'Query Complete'}
                </span>
              </div>
            </div>
            
            {result.isCorrect && (
              <div className="bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 rounded-lg p-4">
                <div className="flex items-center space-x-2">
                  <span className="text-2xl">🎉</span>
                  <div>
                    <p className="text-green-800 dark:text-green-200 font-medium">Excellent work!</p>
                    <p className="text-green-700 dark:text-green-300 text-sm">Your solution is correct!</p>
                  </div>
                </div>
              </div>
            )}
            
            <div className="bg-muted/50 rounded-lg p-4">
              <p className="text-sm text-muted-foreground mb-2">📊 Query Results:</p>
              <div className="font-mono text-sm bg-background rounded border p-3 overflow-x-auto">
                <p>Status: {result.isCorrect ? '✅ Correct' : '⚠️ Review needed'}</p>
                <p className="text-muted-foreground mt-2">
                  [Table data would be displayed here]
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );

  // Show resizable layout when output is visible, otherwise show just the editor
  if (showOutput) {
    return (
      <VerticalResizableSplitter
        topPanel={editorPanel}
        bottomPanel={outputPanel}
        defaultTopHeight={60}
        minTopHeight={35}
        minBottomHeight={25}
        className="h-full"
      />
    );
  }

  // Show just the editor when no output
  return (
    <div className="h-full">
      {editorPanel}
    </div>
  );
}

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
    <div className="h-screen bg-background flex flex-col">
      {/* Top Navigation Bar */}
      <div className="flex-shrink-0 bg-background border-b border-border px-6 py-3">
        <Link href="/problems">
          <Button variant="ghost" data-testid="button-back">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Problems
          </Button>
        </Link>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 min-h-0">
        <ResizableSplitter
          defaultLeftWidth={45}
          minLeftWidth={30}
          minRightWidth={30}
          className="h-full"
          leftPanel={
            /* Problem Panel - Full Height */
            <div className="h-full flex flex-col overflow-hidden bg-background">
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

                    {/* Hints Section */}
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
            </div>
          }
          rightPanel={
            /* Editor + Output Panels with Vertical Split */
            <EditorOutputSplit 
              problem={problem}
              handleRunQuery={handleRunQuery}
              handleSubmitSolution={handleSubmitSolution}
            />
          }
        />
      </div>
    </div>
  );
}
