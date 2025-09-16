import { memo, useState, useCallback } from "react";
import EditorHeader from "@/components/EditorHeader";
import CodeEditor from "@/components/CodeEditor";
import OutputPanel from "@/components/OutputPanel";
import SubmissionResultPanel from "@/components/SubmissionResultPanel";
import VerticalResizableSplitter from "@/components/vertical-resizable-splitter";

interface Problem {
  company?: string;
  difficulty?: string;
  premium?: boolean | null;
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
  problemId?: string;
  handleRunQuery: (query: string) => Promise<any>;
  handleSubmitSolution: (query: string) => Promise<any>;
  onDifficultyClick: (difficulty: string) => void;
  onCompanyClick: (company: string) => void;
  className?: string;
}

const OptimizedEditorOutputSplit = memo(function OptimizedEditorOutputSplit({
  problem,
  problemId,
  handleRunQuery,
  handleSubmitSolution,
  onDifficultyClick,
  onCompanyClick,
  className,
}: OptimizedEditorOutputSplitProps) {
  const [result, setResult] = useState<QueryResult | null>(null);
  const [submissionResult, setSubmissionResult] = useState<any | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showOutput, setShowOutput] = useState(false);
  const [isSubmissionMode, setIsSubmissionMode] = useState(false);

  const selectedCompany = problem?.company || "NY Times";
  const selectedDifficulty = problem?.difficulty || "Medium";

  // Optimized run query handler
  const optimizedRunQuery = useCallback(
    async (query: string) => {
      setIsRunning(true);
      setShowOutput(true);
      setIsSubmissionMode(false); // Switch to query mode
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
      setIsSubmissionMode(true); // Switch to submission mode
      try {
        const submitResult = await handleSubmitSolution(query);
        setSubmissionResult(submitResult);
        return submitResult;
      } catch (error) {
        const errorResult = {
          error: true,
          message: error instanceof Error ? error.message : "Submission failed",
        };
        setSubmissionResult(errorResult);
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

  // Output panel - show different component based on mode
  const outputPanel = isSubmissionMode ? (
    <SubmissionResultPanel 
      result={submissionResult} 
      isLoading={isSubmitting}
      problemId={problemId || ""} 
    />
  ) : (
    <OutputPanel result={result} isLoading={isRunning} />
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
