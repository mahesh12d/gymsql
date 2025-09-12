import { useState, useMemo, useCallback, useEffect } from 'react';
import { Play, Save, RotateCcw, Lightbulb, Dumbbell, TrendingUp, ChevronDown, ChevronUp, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from '@/components/ui/resizable';
import CodeMirror from '@uiw/react-codemirror';
import { sql, PostgreSQL } from '@codemirror/lang-sql';
import { autocompletion } from '@codemirror/autocomplete';
import { EditorView, keymap, placeholder } from '@codemirror/view';
import { defaultKeymap, indentWithTab } from '@codemirror/commands';
import { oneDark } from '@codemirror/theme-one-dark';

interface SQLEditorProps {
  initialQuery?: string;
  onRunQuery: (query: string) => Promise<any>;
  hints?: string[];
  className?: string;
}

export default function SQLEditor({ 
  initialQuery = '', 
  onRunQuery, 
  hints = [],
  className = '' 
}: SQLEditorProps) {
  const [query, setQuery] = useState(initialQuery);
  const [result, setResult] = useState<any>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [showHint, setShowHint] = useState(false);
  const [hintIndex, setHintIndex] = useState(0);
  const [showOutput, setShowOutput] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

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

  const handleRunQuery = useCallback(async () => {
    if (!query.trim()) return;
    
    setIsRunning(true);
    setShowOutput(true);
    try {
      const result = await onRunQuery(query);
      setResult(result);
    } catch (error) {
      setResult({
        error: true,
        message: error instanceof Error ? error.message : 'Query execution failed',
      });
    } finally {
      setIsRunning(false);
    }
  }, [query, onRunQuery]);

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
          handleRunQuery();
          return true;
        }
      }
    ])
  ], [handleRunQuery]);

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
          minHeight: '16rem',
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

  const handleSubmit = async () => {
    if (!query.trim()) return;
    
    setIsSubmitting(true);
    setShowOutput(true);
    try {
      // Save the query
      localStorage.setItem('sqlgym_last_query', query);
      // Could also submit to user's solutions via API
      await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate API call
    } catch (error) {
      console.error('Submit failed:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReset = () => {
    setQuery(initialQuery);
    setResult(null);
  };

  const handleShowHint = () => {
    setShowHint(true);
  };

  const handleNextHint = () => {
    if (hintIndex < hints.length - 1) {
      setHintIndex(hintIndex + 1);
    }
  };

  return (
    <div className={`w-full h-full ${className}`}>
      <ResizablePanelGroup direction="horizontal" className="h-[calc(100vh-200px)] min-h-[600px]">
        {/* Left Panel - SQL Editor */}
        <ResizablePanel defaultSize={60} minSize={40}>
          <Card className="h-full overflow-hidden bg-card border-border">
            {/* Input Header */}
            <CardHeader className="bg-muted/50 px-6 py-4 border-b border-border">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <Dumbbell className="h-5 w-5 text-primary" />
                  <h3 className="text-lg font-semibold text-foreground">SQL Editor</h3>
                </div>
                <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                  <span>PostgreSQL 14</span>
                  <ChevronDown className="h-4 w-4" />
                </div>
              </div>
            </CardHeader>
            
            {/* Code Editor */}
            <CardContent className="p-0 h-full">
              <CodeMirror
                value={query}
                onChange={(value) => setQuery(value)}
                height="calc(100% - 1rem)"
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
        </ResizablePanel>
        
        <ResizableHandle withHandle />
        
        {/* Right Panel - Controls and Output */}
        <ResizablePanel defaultSize={40} minSize={25}>
          <div className="h-full flex flex-col">
            {/* Control Panel */}
            <Card className="mb-4">
              <CardHeader className="bg-muted/50 px-6 py-4 border-b border-border">
                <h3 className="text-lg font-semibold text-foreground">Actions</h3>
              </CardHeader>
              <CardContent className="p-6">
                <div className="space-y-3">
                  <Button
                    onClick={handleRunQuery}
                    disabled={isRunning || !query.trim()}
                    className="w-full bg-primary text-primary-foreground hover:bg-primary/90 font-semibold"
                    data-testid="button-run-query"
                  >
                    <Play className="mr-2 h-4 w-4" />
                    {isRunning ? 'Running...' : 'Run'}
                  </Button>
                  
                  <Button 
                    onClick={handleSubmit} 
                    disabled={isSubmitting || !query.trim()}
                    variant="outline"
                    className="w-full"
                    data-testid="button-submit"
                  >
                    <Save className="mr-2 h-4 w-4" />
                    {isSubmitting ? 'Submitting...' : 'Submit'}
                  </Button>
                  
                  <Button 
                    onClick={handleReset} 
                    variant="outline"
                    className="w-full"
                    data-testid="button-reset"
                  >
                    <RotateCcw className="mr-2 h-4 w-4" />
                    Reset
                  </Button>

                  {hints.length > 0 && (
                    <Button 
                      onClick={handleShowHint} 
                      variant="outline"
                      className="w-full text-primary hover:bg-primary/10"
                      data-testid="button-show-hint"
                    >
                      <Lightbulb className="mr-2 h-4 w-4" />
                      Show Hint
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
            
            {/* Output Panel - Only show when there's output or when triggered */}
            {showOutput && (
              <Card className="flex-1 overflow-hidden">
                <CardHeader className="bg-muted/50 px-6 py-4 border-b border-border">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <TrendingUp className="h-5 w-5 text-primary" />
                      <h3 className="text-lg font-semibold text-foreground">Output</h3>
                    </div>
                    <Button 
                      onClick={() => setShowOutput(false)}
                      variant="ghost"
                      size="sm"
                      data-testid="button-hide-output"
                    >
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                </CardHeader>
                
                {/* Output Content */}
                <CardContent className="p-6 flex-1 overflow-auto">
                  {!result ? (
                    <div className="flex flex-col items-center justify-center h-40 text-center">
                      <div className="text-6xl mb-4">💪</div>
                      <p className="text-muted-foreground text-lg">Ready to execute!</p>
                      <p className="text-sm text-muted-foreground mt-2">Run your query to see results</p>
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
                      <div className="flex items-center space-x-3 text-green-600">
                        <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                        <span className="font-medium">
                          {result.isCorrect ? 'Perfect! 🏆' : 'Query Complete'}
                        </span>
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
                        <div className="font-mono text-sm bg-background rounded border p-3">
                          <p>Status: {result.isCorrect ? '✅ Correct' : '⚠️ Review needed'}</p>
                          <p>Execution Time: {result.executionTime || 0}ms</p>
                          <p className="text-muted-foreground mt-2">
                            [Table data would be displayed here]
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>

      
      {/* Trainer Tips - Fixed Position Below Layout */}
      {showHint && hints.length > 0 && (
        <Alert className="border-primary/20 bg-primary/10 mt-4">
          <Lightbulb className="h-4 w-4 text-primary" />
          <AlertDescription className="text-foreground">
            <strong>💡 Hint {hintIndex + 1}:</strong> {hints[hintIndex]}
            {hintIndex < hints.length - 1 && (
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
  );
}
