import { memo, useState, useCallback, useEffect } from "react";
import { Lightbulb } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import TableDisplay from "@/components/table-display";
import { queryClient } from "@/lib/queryClient";

interface Problem {
  question?: {
    description?: string;
    tables?: any[];
    expectedOutput?: any[];
  };
  hints?: string[];
  tags?: string[];
}

interface ProblemDescriptionTabProps {
  problem?: Problem;
  className?: string;
  problemId?: string;
}

const ProblemDescriptionTab = memo(function ProblemDescriptionTab({
  problem,
  className,
  problemId,
}: ProblemDescriptionTabProps) {
  const [showHint, setShowHint] = useState(false);
  const [hintIndex, setHintIndex] = useState(0);

  // Force cache invalidation on mount to ensure fresh data
  useEffect(() => {
    if (problemId) {
      queryClient.invalidateQueries({ queryKey: ["/api/problems", problemId] });
    }
  }, [problemId]);

  const handleHintClick = useCallback(() => {
    if (!showHint) {
      setShowHint(true);
    } else if (hintIndex < (problem?.hints?.length || 0) - 1) {
      setHintIndex((prev) => prev + 1);
    }
  }, [showHint, hintIndex, problem?.hints?.length]);

  // Parse hint content and extract code blocks
  const parseHintContent = useCallback((content: string) => {
    const parts = content.split(/(\*\/\*[\s\S]*?\*\/\*)/);
    return parts.map((part, partIndex) => {
      if (part.startsWith("*/*") && part.endsWith("*/*")) {
        const codeContent = part.slice(3, -3);
        return (
          <code
            key={partIndex}
            className="block bg-gray-100 dark:bg-gray-800 p-3 rounded-md text-sm font-mono my-2 whitespace-pre-wrap"
          >
            {codeContent}
          </code>
        );
      } else {
        return part;
      }
    });
  }, []);

  return (
    <div className={`space-y-6 ${className || ""}`}>
      {/* Problem Description */}
      <div className="space-y-4">
        <div className="text-foreground prose prose-sm max-w-none dark:prose-invert">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              p: ({ children }) => (
                <p className="mb-3 text-foreground leading-relaxed">
                  {children}
                </p>
              ),
              h1: ({ children }) => (
                <h1 className="text-xl font-bold mb-4 text-foreground">
                  {children}
                </h1>
              ),
              h2: ({ children }) => (
                <h2 className="text-lg font-semibold mb-3 text-foreground">
                  {children}
                </h2>
              ),
              h3: ({ children }) => (
                <h3 className="text-base font-semibold mb-2 text-foreground">
                  {children}
                </h3>
              ),
              ul: ({ children }) => (
                <ul className="list-disc list-inside mb-3 space-y-1 text-foreground">
                  {children}
                </ul>
              ),
              ol: ({ children }) => (
                <ol className="list-decimal list-inside mb-3 space-y-1 text-foreground">
                  {children}
                </ol>
              ),
              li: ({ children }) => (
                <li className="text-foreground">{children}</li>
              ),
              strong: ({ children }) => (
                <strong className="font-semibold text-foreground">
                  {children}
                </strong>
              ),
              em: ({ children }) => (
                <em className="italic text-foreground">{children}</em>
              ),
              code: ({ children }) => (
                <code className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono text-foreground">
                  {children}
                </code>
              ),
              pre: ({ children }) => (
                <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-sm font-mono text-foreground mb-4">
                  {children}
                </pre>
              ),
              blockquote: ({ children }) => (
                <blockquote className="border-l-4 border-primary pl-4 italic text-muted-foreground mb-4">
                  {children}
                </blockquote>
              ),
              table: ({ children }) => (
                <div className="overflow-x-auto mb-4">
                  <table className="min-w-full border border-muted rounded-lg">
                    {children}
                  </table>
                </div>
              ),
              thead: ({ children }) => (
                <thead className="bg-muted/50">{children}</thead>
              ),
              tbody: ({ children }) => <tbody>{children}</tbody>,
              tr: ({ children }) => (
                <tr className="border-b border-muted">{children}</tr>
              ),
              th: ({ children }) => (
                <th className="border border-muted px-3 py-2 text-left font-semibold">
                  {children}
                </th>
              ),
              td: ({ children }) => (
                <td className="border border-muted px-3 py-2">{children}</td>
              ),
            }}
          >
            {problem?.question?.description || ""}
          </ReactMarkdown>
        </div>
      </div>

      {/* Structured Table Display */}
      <TableDisplay
        tables={problem?.question?.tables || []}
        expectedOutput={problem?.expectedDisplay || problem?.question?.expectedOutput || []}
      />

      {/* Hints Section */}
      {problem?.hints && problem.hints.length > 0 && (
        <div className="space-y-3">
          {!showHint ? (
            <Button
              onClick={handleHintClick}
              variant="outline"
              className="w-full text-primary hover:bg-primary/10"
              data-testid="button-hint"
            >
              <Lightbulb className="mr-2 h-4 w-4" />
              HINT
            </Button>
          ) : (
            <>
              <div className="space-y-4">
                {problem.hints
                  .slice(0, hintIndex + 1)
                  .map((hint: string, index: number) => (
                    <div key={index} className="text-foreground">
                      <h3 className="text-center font-bold text-lg mb-2 text-foreground">
                        HINT {index + 1}
                      </h3>
                      <p className="text-foreground leading-relaxed">
                        {parseHintContent(hint)}
                      </p>
                    </div>
                  ))}
              </div>

              {hintIndex < (problem?.hints?.length || 0) - 1 && (
                <Button
                  onClick={handleHintClick}
                  variant="outline"
                  className="w-full text-primary hover:bg-primary/10 mt-3"
                  data-testid="button-hint"
                >
                  <Lightbulb className="mr-2 h-4 w-4" />
                  HINT
                </Button>
              )}
            </>
          )}
        </div>
      )}

      {/* Tags */}
      {problem?.tags && problem.tags.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-foreground mb-2">Tags</h4>
          <div className="flex flex-wrap gap-2">
            {problem.tags.map((tag: string, index: number) => (
              <Badge key={index} variant="outline" data-testid={`tag-${tag}`}>
                {tag}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
});


export default ProblemDescriptionTab;
