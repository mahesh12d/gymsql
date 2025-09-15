import { memo } from 'react';
import { TrendingUp } from 'lucide-react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';

interface QueryResult {
  error?: boolean;
  message?: string;
  isCorrect?: boolean;
  executionTime?: number;
}

interface OutputPanelProps {
  result: QueryResult | null;
  className?: string;
}

const OutputPanel = memo(function OutputPanel({ result, className }: OutputPanelProps) {
  return (
    <Card className={`h-full rounded-none border-0 ${className || ''}`}>
      <CardHeader className="bg-muted/50 px-5 py-2.5 border-b border-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <TrendingUp className="h-3.5 w-3.5 text-primary" />
            <span className="font-semibold text-sm text-foreground">
              Output
            </span>
          </div>
          <div className="text-xs text-muted-foreground">
            {result?.executionTime &&
              `Execution time: ${result.executionTime || 0.01604} seconds`}
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-5 h-full overflow-auto">
        {!result ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="text-3xl mb-3">⚡</div>
            <p className="text-sm text-muted-foreground">Ready to execute!</p>
            <p className="text-xs text-muted-foreground mt-1.5">
              Use Alt + Enter to run query
            </p>
          </div>
        ) : result.error ? (
          <div className="space-y-3">
            <div className="flex items-center space-x-2.5 text-red-600">
              <div className="w-2.5 h-2.5 bg-red-500 rounded-full"></div>
              <span className="font-medium text-sm">Query Failed</span>
            </div>
            <div className="bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg p-3">
              <p className="text-red-800 dark:text-red-200 text-xs font-mono">
                {result.message}
              </p>
            </div>
            <p className="text-xs text-muted-foreground">
              Check your query and try again.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2.5 text-green-600">
                <div className="w-2.5 h-2.5 bg-green-500 rounded-full"></div>
                <span className="font-medium text-sm">
                  {result.isCorrect ? "Perfect! 🏆" : "Query Complete"}
                </span>
              </div>
            </div>

            {result.isCorrect && (
              <div className="bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 rounded-lg p-3">
                <div className="flex items-center space-x-1.5">
                  <span className="text-lg">🎉</span>
                  <div>
                    <p className="text-green-800 dark:text-green-200 font-medium text-sm">
                      Excellent work!
                    </p>
                    <p className="text-green-700 dark:text-green-300 text-xs">
                      Your solution is correct!
                    </p>
                  </div>
                </div>
              </div>
            )}

            <div className="bg-muted/50 rounded-lg p-3">
              <p className="text-xs text-muted-foreground mb-1.5">
                📊 Query Results:
              </p>
              <div className="font-mono text-xs bg-background rounded border p-2 overflow-x-auto">
                <p>
                  Status: {result.isCorrect ? "✅ Correct" : "⚠️ Review needed"}
                </p>
                <p className="text-muted-foreground mt-1.5">
                  [Table data would be displayed here]
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
});

export default OutputPanel;