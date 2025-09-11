import { useState, useMemo, useCallback, useEffect } from 'react';
import { Play, Save, RotateCcw, Lightbulb } from 'lucide-react';
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

  const handleSave = () => {
    localStorage.setItem('sqlgym_last_query', query);
    // Could also save to user's drafts via API
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
    <div className={`space-y-6 ${className}`}>
      {/* SQL Editor */}
      <div>
        <h3 className="text-xl font-semibold text-foreground mb-3">SQL Editor</h3>
        <Card className="overflow-hidden">
          <CardHeader className="bg-muted px-4 py-2 border-b border-border">
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-red-400 rounded-full"></div>
              <div className="w-3 h-3 bg-yellow-400 rounded-full"></div>
              <div className="w-3 h-3 bg-green-400 rounded-full"></div>
              <span className="text-sm text-muted-foreground ml-4">query.sql</span>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <CodeMirror
              value={query}
              onChange={(value) => setQuery(value)}
              height="16rem"
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
              className="code-editor"
            />
          </CardContent>
        </Card>
      </div>

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-3">
        <Button
          onClick={handleRunQuery}
          disabled={isRunning || !query.trim()}
          className="dumbbell-btn bg-primary text-primary-foreground hover:bg-primary/90"
          data-testid="button-run-query"
        >
          <Play className="mr-2 h-4 w-4" />
          {isRunning ? 'Running...' : 'Run Query'}
        </Button>
        
        <Button 
          onClick={handleSave} 
          variant="outline"
          data-testid="button-save"
        >
          <Save className="mr-2 h-4 w-4" />
          Save
        </Button>
        
        <Button 
          onClick={handleReset} 
          variant="outline"
          data-testid="button-reset"
        >
          <RotateCcw className="mr-2 h-4 w-4" />
          Reset
        </Button>

        {hints.length > 0 && (
          <Button 
            onClick={handleShowHint} 
            variant="outline"
            className="text-primary hover:bg-primary/10"
            data-testid="button-show-hint"
          >
            <Lightbulb className="mr-2 h-4 w-4" />
            Show Hint
          </Button>
        )}
      </div>

      {/* Hints */}
      {showHint && hints.length > 0 && (
        <Alert className="border-primary/20 bg-primary/10">
          <Lightbulb className="h-4 w-4 text-primary" />
          <AlertDescription className="text-foreground">
            <strong>Hint {hintIndex + 1}:</strong> {hints[hintIndex]}
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

      {/* Results Panel */}
      {result && (
        <div>
          <h3 className="text-xl font-semibold text-foreground mb-3">Results</h3>
          <Card className="overflow-hidden">
            <CardHeader className={`px-4 py-2 border-b ${
              result.error ? 'bg-red-50 border-red-200' : 'bg-green-50 border-green-200'
            }`}>
              <div className="flex items-center space-x-2">
                {result.error ? (
                  <>
                    <div className="w-4 h-4 bg-red-500 rounded-full"></div>
                    <span className="text-red-800 font-medium">Query failed</span>
                  </>
                ) : (
                  <>
                    <div className="w-4 h-4 bg-green-500 rounded-full"></div>
                    <span className="text-green-800 font-medium">
                      {result.isCorrect ? 'Query executed successfully!' : 'Query executed, but result may be incorrect'}
                    </span>
                  </>
                )}
              </div>
            </CardHeader>
            <CardContent className="p-4">
              {result.error ? (
                <p className="text-red-600 text-sm">{result.message}</p>
              ) : (
                <div>
                  <p className="text-sm text-muted-foreground mb-2">
                    Execution time: {result.executionTime || 0}ms
                  </p>
                  {result.isCorrect && (
                    <Alert className="border-green-200 bg-green-50">
                      <AlertDescription className="text-green-800">
                        🎉 Congratulations! Your query is correct. You've earned XP points!
                      </AlertDescription>
                    </Alert>
                  )}
                  <div className="mt-4 text-sm text-muted-foreground">
                    <p>Query result would be displayed here in a real implementation.</p>
                    <p>Status: {result.isCorrect ? '✅ Correct' : '❌ Incorrect'}</p>
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
