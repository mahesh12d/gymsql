import { useParams, useLocation } from "wouter";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect, useCallback, useMemo } from "react";
import { Lock, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

import { problemsApi, submissionsApi } from "@/lib/auth";
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import ResizableSplitter from "@/components/resizable-splitter";
import ProblemNavigation from "@/components/ProblemNavigation";
import ProblemTabsContent from "@/components/ProblemTabsContent";
import OptimizedEditorOutputSplit from "@/components/OptimizedEditorOutputSplit";
import "../components/AnimatedFields.css";

export default function ProblemDetail() {
  const params = useParams();
  const problemId = params.id as string;
  const [, setLocation] = useLocation();
  const { user } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [latestSubmissionResult, setLatestSubmissionResult] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<string>("problem");

  // Memoized navigation handlers to prevent recreation
  const handleDifficultyClick = useCallback((difficulty: string) => {
    setLocation(`/problems?difficulty=${encodeURIComponent(difficulty)}`);
  }, [setLocation]);

  const handleCompanyClick = useCallback((company: string) => {
    setLocation(`/problems?company=${encodeURIComponent(company)}`);
  }, [setLocation]);

  // Optimized queries with proper memoization
  const { data: problem, isLoading: problemLoading } = useQuery({
    queryKey: ["/api/problems", problemId],
    queryFn: () => problemsApi.getById(problemId),
    enabled: !!problemId,
  });

  const { data: userSubmissions = [] } = useQuery({
    queryKey: ["/api/submissions", problemId],
    queryFn: () => submissionsApi.getByProblemId(problemId),
    enabled: !!problemId && !!user,
  });

  // Memoized run query mutation with DuckDB/PostgreSQL detection
  const runQueryMutation = useMutation({
    mutationFn: async (query: string) => {
      if (!problemId) throw new Error("No problem selected");
      
      // Check if problem has parquet data source OR S3 data source(s) to determine which endpoint to use
      const hasParquetData = problem?.parquetDataSource !== null && problem?.parquetDataSource !== undefined;
      const hasS3Data = problem?.s3DataSource !== null && problem?.s3DataSource !== undefined;
      const hasS3Datasets = problem?.s3Datasets && Array.isArray(problem.s3Datasets) && problem.s3Datasets.length > 0;
      
      if (hasParquetData || hasS3Data || hasS3Datasets) {
        // Use DuckDB endpoint for parquet/S3 data
        return submissionsApi.testDuckDBQuery(problemId, query);
      } else {
        // Use PostgreSQL endpoint for regular problems
        return submissionsApi.testQuery(problemId, query);
      }
    },
    onError: (error) => {
      toast({
        title: "Query failed",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    },
  });

  // Memoized submit solution mutation
  const submitSolutionMutation = useMutation({
    mutationFn: async (query: string) => {
      if (!problemId) throw new Error("No problem selected");
      return submissionsApi.submit(problemId, query);
    },
    onSuccess: (result) => {
      // Store the latest submission result for the left panel
      setLatestSubmissionResult(result);
      // Invalidate submissions to refetch
      queryClient.invalidateQueries({
        queryKey: ["/api/submissions", problemId],
      });
      // Also invalidate the problems list to update the isUserSolved status
      queryClient.invalidateQueries({
        queryKey: ["/api/problems"],
      });
      // Auto-open submissions tab after successful submission
      setActiveTab('submission');
    },
  });

  // Memoized handlers
  const handleRunQuery = useCallback(
    async (query: string) => {
      return runQueryMutation.mutateAsync(query);
    },
    [runQueryMutation]
  );

  const handleSubmitSolution = useCallback(
    async (query: string) => {
      return submitSolutionMutation.mutateAsync(query);
    },
    [submitSolutionMutation]
  );

  // Navigation handlers (placeholder - could be implemented with actual navigation logic)
  const handlePrevious = useCallback(() => {
    // Implement navigation to previous problem
    console.log("Navigate to previous problem");
  }, []);

  const handleNext = useCallback(() => {
    // Implement navigation to next problem  
    console.log("Navigate to next problem");
  }, []);

  // Loading state
  if (problemLoading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading problem...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (!problem) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-2">Problem not found</h1>
          <p className="text-muted-foreground mb-4">
            The problem you're looking for doesn't exist.
          </p>
          <button
            onClick={() => setLocation("/problems")}
            className="text-primary hover:underline"
          >
            Back to Problems
          </button>
        </div>
      </div>
    );
  }

  // Premium access check - block entire premium problems for non-premium users
  if (problem.premium && (!user || !user.premium)) {
    return (
      <div className="h-screen flex items-center justify-center bg-background">
        <div className="text-center max-w-md mx-auto p-8">
          <div className="flex items-center justify-center w-20 h-20 bg-amber-100 dark:bg-amber-900/20 rounded-full mx-auto mb-6">
            <Lock className="w-10 h-10 text-amber-600 dark:text-amber-500" />
          </div>
          <h1 className="text-3xl font-bold mb-4 text-foreground">Premium Problem</h1>
          <p className="text-muted-foreground mb-6 text-lg leading-relaxed">
            🔒 This is a premium problem. Upgrade to access the complete problem description, 
            hints, solutions, discussions, and coding environment.
          </p>
          <div className="space-y-3">
            <Button 
              className="w-full bg-amber-600 hover:bg-amber-700 text-white"
              onClick={() => {
                if (!user) {
                  // If not logged in, redirect to landing page (which shows auth forms)
                  setLocation("/");
                } else {
                  // If logged in but not premium, show upgrade message and redirect to landing
                  toast({
                    title: "Premium Upgrade Required",
                    description: "Contact support or visit our pricing page to upgrade to Premium.",
                    variant: "default",
                  });
                  // In a real app, this would redirect to billing/upgrade page
                  setLocation("/");
                }
              }}
              data-testid="button-upgrade-premium"
            >
              <Lock className="w-4 h-4 mr-2" />
              {!user ? "Sign in to Access" : "Upgrade to Premium"}
            </Button>
            <Button 
              variant="outline" 
              onClick={() => setLocation("/problems")}
              className="w-full"
              data-testid="button-back-problems"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Problems
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Navigation Header */}
      <ProblemNavigation
        problem={problem}
        userSubmissions={userSubmissions}
        onPrevious={handlePrevious}
        onNext={handleNext}
        hasPrevious={false} // TODO: Implement actual navigation logic
        hasNext={false} // TODO: Implement actual navigation logic
      />

      {/* Main Content with Resizable Split */}
      <div className="flex-1 min-h-0">
        <ResizableSplitter
          leftPanel={
            <ProblemTabsContent
              problem={problem}
              userSubmissions={userSubmissions}
              latestSubmissionResult={latestSubmissionResult}
              activeTab={activeTab}
              onTabChange={setActiveTab}
              problemId={problemId}
            />
          }
          rightPanel={
            <OptimizedEditorOutputSplit
              problem={problem}
              problemId={problemId}
              handleRunQuery={handleRunQuery}
              handleSubmitSolution={handleSubmitSolution}
              onDifficultyClick={handleDifficultyClick}
              onCompanyClick={handleCompanyClick}
            />
          }
        />
      </div>
    </div>
  );
}