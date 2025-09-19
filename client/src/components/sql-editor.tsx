import { useState, useMemo, useCallback, useEffect } from 'react';
import { Play, Save, Lightbulb, Dumbbell, TrendingUp, ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import CodeMirror from '@uiw/react-codemirror';
import { sql, PostgreSQL } from '@codemirror/lang-sql';
import { autocompletion } from '@codemirror/autocomplete';
import { EditorView, keymap, placeholder } from '@codemirror/view';
import { defaultKeymap, indentWithTab } from '@codemirror/commands';
import { oneDark } from '@codemirror/theme-one-dark';

interface SQLEditorProps {
  initialQuery?: string;
  onRunQuery: (query: string) => Promise<any>;
  onSubmitSolution: (query: string) => Promise<any>;
  hints?: string[];
  className?: string;
  problem?: any; // Add problem prop to determine database type
}

export default function SQLEditor({ 
  initialQuery = '', 
  onRunQuery,
  onSubmitSolution,
  hints = [],
  className = '',
  problem
}: SQLEditorProps) {
  const [query, setQuery] = useState(initialQuery);
  const [result, setResult] = useState<any>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showHint, setShowHint] = useState(false);
  const [hintIndex, setHintIndex] = useState(0);

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

  const handleSubmitSolution = useCallback(async () => {
    if (!query.trim()) return;
    
    setIsSubmitting(true);
    try {
      const result = await onSubmitSolution(query);
      setResult(result);
      // Also save to localStorage as backup
      localStorage.setItem('sqlgym_last_query', query);
    } catch (error) {
      setResult({
        error: true,
        message: error instanceof Error ? error.message : 'Submission failed',
      });
    } finally {
      setIsSubmitting(false);
    }
  }, [query, onSubmitSolution]);

  const handleSave = () => {
    localStorage.setItem('sqlgym_last_query', query);
    console.log('Saving query:', query);
  };


  const handleShowHint = () => {
    setShowHint(true);
  };

  const handleNextHint = () => {
    if (hintIndex < hints.length - 1) {
      setHintIndex(hintIndex + 1);
    }
  };

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
          minHeight: '200px', // Reduced height
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

  return (
    <div className={`w-full max-w-6xl mx-auto ${className}`}>
      {/* Training Zone (Input Section) - Reduced spacing */}
      <div className="mb-3">
        <Card className="overflow-hidden">
          {/* Input Header - Reduced padding */}
          <CardHeader className="bg-muted/50 px-4 py-2 border-b border-border">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Dumbbell className="h-4 w-4 text-primary" />
                <h3 className="text-base font-semibold text-foreground">Training Zone</h3>
              </div>
              <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                <span>{problem?.parquet_data_source ? 'DuckDB' : 'PostgreSQL 14'}</span>
                <ChevronDown className="h-4 w-4" />
              </div>
            </div>
          </CardHeader>
          
          {/* Code Editor - Reduced height */}
          <CardContent className="p-0">
            <div className="relative">
              <CodeMirror
                value={query}
                onChange={(value) => setQuery(value)}
                height="200px" // Fixed compact height
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
                className="sqlgym-editor"
              />
              <div className="absolute top-2 right-2 text-xs text-muted-foreground">
                Ctrl/Cmd + Enter to run
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Gym Controls - Moved up and made more compact */}
      <div className="flex flex-wrap gap-2 mb-3">
        <Button
          onClick={handleRunQuery}
          disabled={isRunning || !query.trim()}
          className="bg-primary text-primary-foreground hover:bg-primary/90 font-semibold flex items-center"
          data-testid="button-run-query"
        >
          <Dumbbell className="mr-2 h-4 w-4" />
          {isRunning ? 'Running...' : 'Run Code'}
        </Button>
        
        <Button 
          onClick={handleSave} 
          variant="outline"
          className="flex items-center"
        >
          <Save className="mr-2 h-4 w-4" />
          Save Query
        </Button>
        

        {hints.length > 0 && (
          <Button 
            onClick={handleShowHint} 
            variant="outline"
            className="text-primary hover:bg-primary/10 flex items-center"
          >
            <Lightbulb className="mr-2 h-4 w-4" />
            Get Hint
          </Button>
        )}

        {/* Check Solution button like in your screenshot */}
        <Button
          onClick={handleSubmitSolution}
          disabled={isSubmitting || !query.trim()}
          className="bg-green-600 text-white hover:bg-green-700 font-semibold flex items-center ml-auto"
          data-testid="button-submit"
        >
          ✓ {isSubmitting ? 'Submitting...' : 'Check Solution'}
        </Button>
      </div>

      {/* Trainer Tips - More compact */}
      {showHint && hints.length > 0 && (
        <Alert className="border-primary/20 bg-primary/5 mb-3 py-3">
          <div className="flex">
            <Lightbulb className="h-4 w-4 text-primary mt-0.5 mr-2 flex-shrink-0" />
            <AlertDescription className="text-foreground">
              <strong>💡 Hint {hintIndex + 1}:</strong> {hints[hintIndex]}
              {hintIndex < hints.length - 1 && (
                <Button 
                  onClick={handleNextHint}
                  variant="link" 
                  className="p-0 ml-2 text-primary underline text-sm"
                >
                  Next hint →
                </Button>
              )}
            </AlertDescription>
          </div>
        </Alert>
      )}

      {/* Performance Report (Output Section) - Only appears when there are results */}
      {result && (
        <div className="mb-4">
          <Card className="overflow-hidden">
            <CardHeader className="bg-muted/50 px-4 py-2 border-b border-border">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <TrendingUp className="h-4 w-4 text-primary" />
                  <h3 className="text-base font-semibold text-foreground">Query Results</h3>
                </div>
                {result && !result.error && (
                  <div className="text-sm text-muted-foreground">
                    Execution: {result.executionTime || 0}ms
                  </div>
                )}
              </div>
            </CardHeader>
            
            <CardContent className="p-4">
              {result.error ? (
                <div className="space-y-3">
                  <div className="flex items-center space-x-2 text-red-600 dark:text-red-400">
                    <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                    <span className="font-medium text-sm">Query Failed</span>
                  </div>
                  <div className="bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded p-3">
                    <p className="text-red-800 dark:text-red-200 text-sm font-mono">{result.message}</p>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-center space-x-2 text-green-600 dark:text-green-400">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="font-medium text-sm">
                      {result.isCorrect ? 'Perfect! 🏆' : 'Query Executed'}
                    </span>
                  </div>
                  
                  {result.isCorrect && (
                    <div className="bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 rounded p-3">
                      <div className="flex items-center space-x-2">
                        <span className="text-lg">🎉</span>
                        <div>
                          <p className="text-green-800 dark:text-green-200 font-medium text-sm">Excellent work!</p>
                          <p className="text-green-700 dark:text-green-300 text-sm">Solution is correct!</p>
                        </div>
                      </div>
                    </div>
                  )}
                  
                  <div className="bg-muted/50 rounded p-3">
                    <p className="text-sm text-muted-foreground mb-2">📊 Results:</p>
                    <div className="font-mono text-sm bg-background rounded border p-2">
                      <p className="mb-2">Status: {result.isCorrect ? 'Correct' : 'Check again'}</p>
                      <p className="mb-2">Performance: {result.query_result?.execution_time_ms || result.executionTime || 0}ms</p>
                      {result.query_result?.result && result.query_result.result.length > 0 ? (
                        <div className="overflow-x-auto mt-2">
                          <table className="w-full text-xs border-collapse">
                            <thead>
                              <tr>
                                {Object.keys(result.query_result.result[0]).map((column) => (
                                  <th key={column} className="border border-border px-2 py-1 bg-muted font-semibold text-left">
                                    {column}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {result.query_result.result.slice(0, 10).map((row, index) => (
                                <tr key={index}>
                                  {Object.values(row).map((value, colIndex) => (
                                    <td key={colIndex} className="border border-border px-2 py-1">
                                      {String(value)}
                                    </td>
                                  ))}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                          {result.query_result.result.length > 10 && (
                            <p className="text-muted-foreground mt-2 text-xs">
                              Showing first 10 of {result.query_result.rows_affected} rows
                            </p>
                          )}
                          <p className="text-muted-foreground mt-1 text-xs">
                            {result.query_result.rows_affected} rows returned
                          </p>
                        </div>
                      ) : (
                        <p className="text-muted-foreground mt-1 text-xs">
                          No data returned
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Empty state hint when no result - Only shows when no results */}
      {!result && (
        <div className="text-center py-4 text-muted-foreground text-sm">
          💡 Write your SQL query above and click "Run Code" to see results
        </div>
      )}
    </div>
  );
}