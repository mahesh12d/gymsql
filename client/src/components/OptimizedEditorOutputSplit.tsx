import { memo, useState, useCallback } from "react";
import EditorHeader from "@/components/EditorHeader";
import CodeEditor from "@/components/CodeEditor";
import OutputPanel from "@/components/OutputPanel";
import VerticalResizableSplitter from "@/components/vertical-resizable-splitter";

interface Problem {
  company?: string;
  difficulty?: string;
  question?: {
    starterQuery?: string;
    tables?: Array<{ name: string }>;
  };
}

interface QueryResult {
  error?: boolean;
  message?: string;
  isCorrect?: boolean;
  executionTime?: number;
}

interface OptimizedEditorOutputSplitProps {
  problem?: Problem;
  handleRunQuery: (query: string) => Promise<any>;
  handleSubmitSolution: (query: string) => Promise<any>;
  onDifficultyClick: (difficulty: string) => void;
  onCompanyClick: (company: string) => void;
  className?: string;
}

const OptimizedEditorOutputSplit = memo(function OptimizedEditorOutputSplit({
  problem,
  handleRunQuery,
  handleSubmitSolution,
  onDifficultyClick,
  onCompanyClick,
  className,
}: OptimizedEditorOutputSplitProps) {
  const [result, setResult] = useState<QueryResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showOutput, setShowOutput] = useState(false);

  const selectedCompany = problem?.company || "NY Times";
  const selectedDifficulty = problem?.difficulty || "Medium";

  // Optimized run query handler
  const optimizedRunQuery = useCallback(
    async (query: string) => {
      setIsRunning(true);
      setShowOutput(true);
      try {
        const runResult = await handleRunQuery(query);
        setResult(runResult);
        return runResult;
      } catch (error) {
        const errorResult = {
          error: true,
          message:
            error instanceof Error ? error.message : "Query execution failed",
        };
        setResult(errorResult);
        return errorResult;
      } finally {
        setIsRunning(false);
      }
    },
    [handleRunQuery],
  );

  // Optimized submit solution handler
  const optimizedSubmitSolution = useCallback(
    async (query: string) => {
      setIsSubmitting(true);
      setShowOutput(true);
      try {
        const submitResult = await handleSubmitSolution(query);
        setResult(submitResult);
        return submitResult;
      } catch (error) {
        const errorResult = {
          error: true,
          message: error instanceof Error ? error.message : "Submission failed",
        };
        setResult(errorResult);
        return errorResult;
      } finally {
        setIsSubmitting(false);
      }
    },
    [handleSubmitSolution],
  );

  // Editor panel with header
  const editorPanel = (
    <div className="h-full flex flex-col">
      <EditorHeader
        company={selectedCompany}
        difficulty={selectedDifficulty}
        onCompanyClick={onCompanyClick}
        onDifficultyClick={onDifficultyClick}
      />
      <div className="flex-1 min-h-0">
        <CodeEditor
          problem={problem}
          onRunQuery={optimizedRunQuery}
          onSubmitSolution={optimizedSubmitSolution}
          isRunning={isRunning}
          isSubmitting={isSubmitting}
        />
      </div>
    </div>
  );

  // Output panel
  const outputPanel = (
    <OutputPanel result={result} isLoading={isRunning || isSubmitting} />
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
        className={`h-full ${className || ""}`}
      />
    );
  }

  // Show just the editor when no output
  return <div className={`h-full ${className || ""}`}>{editorPanel}</div>;
});

export default OptimizedEditorOutputSplit;
