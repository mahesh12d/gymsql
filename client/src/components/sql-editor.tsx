import { useState, useMemo, useCallback, useEffect } from 'react';
import { Play, Save, TrendingUp, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
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
  className?: string;
}

export default function SQLEditor({ 
  initialQuery = '', 
  onRunQuery,
  onSubmitSolution,
  className = '' 
}: SQLEditorProps) {
  const [query, setQuery] = useState(initialQuery);
  const [result, setResult] = useState<any>(null);
  const [isRunning, setIsRunning] = useState(false);
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
  }, [query, onRunQuery, onSubmitSolution]);

  const handleSubmit = async () => {
    if (!query.trim()) return;
    
    setIsSubmitting(true);
    setShowOutput(true);
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
          minHeight: '300px',
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
    <div className={`h-full flex flex-col ${className}`}>
      {/* SQL Editor */}
      <div className="flex-1 flex flex-col min-h-0">
        <Card className="flex-1 flex flex-col overflow-hidden">
          <CardHeader className="bg-muted/50 px-6 py-4 border-b border-border flex-shrink-0">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <span className="text-lg font-semibold text-foreground">Code</span>
              </div>
              <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                <span>PostgreSQL 14</span>
                <ChevronDown className="h-4 w-4" />
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
      <div className="flex-shrink-0 p-4 bg-muted/30 border-t border-border">
        <div className="flex justify-end gap-3">
          <Button
            onClick={handleRunQuery}
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
      
      {/* Output Panel - Collapsible */}
      {showOutput && (
        <div className="flex-shrink-0 border-t border-border">
          <Card className="rounded-none border-0">
            <CardHeader className="bg-muted/50 px-6 py-3 border-b border-border">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <TrendingUp className="h-4 w-4 text-primary" />
                  <span className="font-semibold text-foreground">Output</span>
                </div>
                <Button 
                  onClick={() => setShowOutput(false)}
                  variant="ghost"
                  size="sm"
                  data-testid="button-hide-output"
                >
                  <ChevronUp className="h-4 w-4" />
                </Button>
              </div>
            </CardHeader>
            
            <CardContent className="p-6 max-h-80 overflow-auto">
              {!result ? (
                <div className="flex flex-col items-center justify-center py-8 text-center">
                  <div className="text-4xl mb-4">⚡</div>
                  <p className="text-muted-foreground">Ready to execute!</p>
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
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3 text-green-600">
                      <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                      <span className="font-medium">
                        {result.isCorrect ? 'Perfect! 🏆' : 'Query Complete'}
                      </span>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Execution time: {result.executionTime || 0}.01604 seconds
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
        </div>
      )}
    </div>
  );
}