import { useParams, useLocation } from "wouter";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect, useCallback, useMemo } from "react";

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

  // Memoized run query mutation
  const runQueryMutation = useMutation({
    mutationFn: async (query: string) => {
      if (!problemId) throw new Error("No problem selected");
      return submissionsApi.testQuery(problemId, query);
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
      if (result.isCorrect) {
        toast({
          title: "🎉 Congratulations!",
          description: "Your solution is correct!",
        });
      } else {
        toast({
          title: "Solution submitted",
          description: "Keep trying! Check the feedback for hints.",
          variant: "default",
        });
      }
      // Invalidate submissions to refetch
      queryClient.invalidateQueries({
        queryKey: ["/api/submissions", problemId],
      });
    },
    onError: (error) => {
      toast({
        title: "Submission failed",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
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
            />
          }
          rightPanel={
            <OptimizedEditorOutputSplit
              problem={problem}
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