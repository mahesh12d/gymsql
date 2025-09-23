import { memo, useState, useCallback, useEffect } from 'react';
import { Play, Save } from 'lucide-react';
import CodeMirror from '@uiw/react-codemirror';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useTheme } from '@/hooks/use-theme';
import { useCodeMirrorConfig } from '@/hooks/use-codemirror-config';

interface Problem {
  question?: {
    starterQuery?: string;
    tables?: Array<{ name: string }>;
  };
}

interface CodeEditorProps {
  problem?: Problem;
  onRunQuery: (query: string) => Promise<any>;
  onSubmitSolution: (query: string) => Promise<any>;
  isRunning?: boolean;
  isSubmitting?: boolean;
  className?: string;
}

const CodeEditor = memo(function CodeEditor({
  problem,
  onRunQuery,
  onSubmitSolution,
  isRunning = false,
  isSubmitting = false,
  className,
}: CodeEditorProps) {
  const [query, setQuery] = useState('');
  const [hasUserEdited, setHasUserEdited] = useState(false);
  const [lastProblemId, setLastProblemId] = useState<string | null>(null);
  const isDarkMode = useTheme();

  // Get problem ID for tracking problem changes
  const currentProblemId = problem?.question?.tables?.[0]?.name || 
                          (problem?.question?.starterQuery ? 'starter' : null);

  // Initialize query when problem loads or changes
  useEffect(() => {
    // Only reset query if:
    // 1. We have no query yet (first load)
    // 2. OR we switched to a different problem (problem ID changed)
    // 3. AND user hasn't made custom edits to current problem
    const shouldInitializeQuery = !query || 
                                 (currentProblemId !== lastProblemId && !hasUserEdited);

    if (shouldInitializeQuery && problem) {
      if (problem?.question?.starterQuery) {
        setQuery(problem.question.starterQuery);
      } else if (problem?.question?.tables && problem.question.tables.length > 0) {
        const firstTable = problem.question.tables[0];
        const tableName = firstTable.name;
        setQuery(`SELECT * FROM "${tableName}";`);
      }
      // Reset user edited flag when initializing with new problem
      if (currentProblemId !== lastProblemId) {
        setHasUserEdited(false);
      }
    }

    // Update tracked problem ID
    if (currentProblemId && currentProblemId !== lastProblemId) {
      setLastProblemId(currentProblemId);
    }
  }, [problem, currentProblemId, lastProblemId, query, hasUserEdited]);

  // Handle query changes and track user edits
  const handleQueryChange = useCallback((value: string) => {
    setQuery(value);
    // Mark as user edited if they've made changes beyond initial setup
    if (value !== problem?.question?.starterQuery && 
        value !== `SELECT * FROM "${problem?.question?.tables?.[0]?.name}";`) {
      setHasUserEdited(true);
    }
  }, [problem?.question?.starterQuery, problem?.question?.tables]);

  // Memoized handlers to prevent recreation
  const handleRun = useCallback(async () => {
    if (!query.trim()) return;
    await onRunQuery(query);
  }, [query, onRunQuery]);

  const handleSubmit = useCallback(async () => {
    if (!query.trim()) return;
    await onSubmitSolution(query);
    localStorage.setItem("sqlgym_last_query", query);
  }, [query, onSubmitSolution]);

  // Get optimized CodeMirror configuration
  const { extensions, theme } = useCodeMirrorConfig({
    problem,
    isDarkMode,
    onRunQuery: handleRun,
  });

  return (
    <div className={`h-full flex flex-col ${className || ''}`}>
      <div className="flex-1 flex flex-col min-h-0">
        <Card className="flex-1 flex flex-col overflow-hidden rounded-none border-0">
          <CardContent className="p-0 flex-1 min-h-0 overflow-hidden">
            <CodeMirror
              value={query}
              onChange={handleQueryChange}
              height="calc(100vh - 200px)"
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
          </CardContent>
        </Card>
      </div>

      {/* Action Buttons */}
      <div className="flex-shrink-0 p-2 bg-muted/30">
        <div className="flex justify-end gap-3">
          <Button
            onClick={handleRun}
            disabled={isRunning || !query.trim()}
            className="bg-primary text-primary-foreground hover:bg-primary/90 font-semibold h-8"
            data-testid="button-run-query"
          >
            <Play className="mr-2 h-4 w-4" />
            {isRunning ? "Running..." : "Run Code"}
          </Button>

          <Button
            onClick={handleSubmit}
            disabled={isSubmitting || !query.trim()}
            className="bg-green-600 hover:bg-green-700 text-white font-semibold h-8"
            data-testid="button-submit"
          >
            <Save className="mr-2 h-4 w-4" />
            {isSubmitting ? "Submitting..." : "Check Solution"}
          </Button>
        </div>
      </div>
    </div>
  );
});

export default CodeEditor;