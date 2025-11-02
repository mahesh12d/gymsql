import { memo, useState, useCallback } from "react";
import { useLocation } from "wouter";
import { LogIn, Lock, Play, CheckCircle } from "lucide-react";
import EditorHeader from "@/components/EditorHeader";
import CodeEditor from "@/components/CodeEditor";
import OutputPanel from "@/components/OutputPanel";
import SubmissionResultPanel from "@/components/SubmissionResultPanel";
import VerticalResizableSplitter from "@/components/vertical-resizable-splitter";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";

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
  success: boolean;
  results?: any[];
  execution_time_ms?: number;
  rows_affected?: number;
  console_info?: string;
  error?: string;
  feedback?: string[];
  test_results?: any[];
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
  const { user } = useAuth();
  const [, setLocation] = useLocation();
  const [result, setResult] = useState<QueryResult | null>(null);
  const [submissionResult, setSubmissionResult] = useState<any | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showOutput, setShowOutput] = useState(false);
  const [isSubmissionMode, setIsSubmissionMode] = useState(false);
  const [submittedQuery, setSubmittedQuery] = useState<string>("");

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
          success: false,
          error:
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
      setSubmittedQuery(query); // Store the query for AI hints
      try {
        const submitResult = await handleSubmitSolution(query);
        setSubmissionResult(submitResult);
        return submitResult;
      } catch (error) {
        const errorResult = {
          success: false,
          error: error instanceof Error ? error.message : "Submission failed",
        };
        setSubmissionResult(errorResult);
        return errorResult;
      } finally {
        setIsSubmitting(false);
      }
    },
    [handleSubmitSolution],
  );

  // Login prompt panel for unauthenticated users
  const loginPromptPanel = (
    <div className="h-full flex flex-col">
      <EditorHeader
        company={selectedCompany}
        difficulty={selectedDifficulty}
        onCompanyClick={onCompanyClick}
        onDifficultyClick={onDifficultyClick}
        problem={problem}
      />
      <div className="flex-1 min-h-0 flex items-center justify-center bg-muted/30">
        <Card className="max-w-md mx-4 shadow-lg border-2">
          <CardContent className="pt-8 pb-8 px-8">
            <div className="text-center space-y-6">
              <div className="flex justify-center">
                <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center">
                  <Lock className="w-8 h-8 text-primary" />
                </div>
              </div>
              <div className="space-y-2">
                <h3 className="text-2xl font-bold text-foreground">Sign in to Code</h3>
                <p className="text-muted-foreground text-sm">
                  Create a free account to write and test SQL queries, submit solutions, and track your progress.
                </p>
              </div>
              <div className="space-y-3 pt-2">
                <div className="flex items-start gap-3 text-left">
                  <Play className="w-5 h-5 text-green-600 dark:text-green-500 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-foreground">Run & Test Your Code</p>
                    <p className="text-xs text-muted-foreground">Execute SQL queries and see results instantly</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 text-left">
                  <CheckCircle className="w-5 h-5 text-blue-600 dark:text-blue-500 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-foreground">Submit Solutions</p>
                    <p className="text-xs text-muted-foreground">Get instant feedback and track your submissions</p>
                  </div>
                </div>
                <div className="flex items-start gap-3 text-left">
                  <LogIn className="w-5 h-5 text-purple-600 dark:text-purple-500 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-foreground">Track Your Progress</p>
                    <p className="text-xs text-muted-foreground">Monitor your learning journey and achievements</p>
                  </div>
                </div>
              </div>
              <Button 
                onClick={() => setLocation("/")}
                className="w-full mt-4"
                size="lg"
                data-testid="button-login-to-code"
              >
                <LogIn className="w-4 h-4 mr-2" />
                Sign In to Start Coding
              </Button>
              <p className="text-xs text-muted-foreground">
                Free forever • No credit card required
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );

  // Editor panel with header
  const editorPanel = (
    <div className="h-full flex flex-col">
      <EditorHeader
        company={selectedCompany}
        difficulty={selectedDifficulty}
        onCompanyClick={onCompanyClick}
        onDifficultyClick={onDifficultyClick}
        problem={problem}
      />
      <div className="flex-1 min-h-0">
        <CodeEditor
          problem={problem}
          problemId={problemId}
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
      userQuery={submittedQuery}
    />
  ) : (
    <OutputPanel result={result} isLoading={isRunning} />
  );

  // Show login prompt for unauthenticated users
  if (!user) {
    return <div className={`h-full ${className || ""}`}>{loginPromptPanel}</div>;
  }

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
