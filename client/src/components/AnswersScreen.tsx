import { memo } from 'react';
import { Trophy } from 'lucide-react';
import { useQuery } from "@tanstack/react-query";

interface User {
  id: string;
  username: string;
  profileImageUrl?: string;
}

interface Solution {
  id: string;
  problemId: string;
  createdBy: string;
  title: string;
  content: string;
  sqlCode: string;
  isOfficial: boolean;
  createdAt: string;
  updatedAt: string;
  creator: User;
}

interface AnswersScreenProps {
  problemId: string;
  className?: string;
}

const SolutionDisplay = memo(function SolutionDisplay({
  solution
}: {
  solution: Solution;
}) {

  return (
    <div className="space-y-6" data-testid={`solution-${solution.id}`}>
      {/* Solution Title */}
      <div>
        <h3 className="text-xl font-bold text-foreground mb-2" data-testid={`text-solution-title-${solution.id}`}>
          {solution.title}
        </h3>
      </div>

      {/* Explanation */}
      <div>
        <h4 className="text-lg font-semibold mb-3 text-foreground">Explanation:</h4>
        <div className="text-foreground prose prose-sm max-w-none dark:prose-invert">
          <div className="mb-3 text-foreground leading-relaxed whitespace-pre-wrap" data-testid={`text-solution-explanation-${solution.id}`}>
            {solution.content}
          </div>
        </div>
      </div>

      {/* SQL Solution */}
      <div>
        <h4 className="text-lg font-semibold mb-3 text-foreground">SQL Solution:</h4>
        <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-sm font-mono text-foreground mb-4" data-testid={`code-solution-${solution.id}`}>
          {solution.sqlCode}
        </pre>
      </div>
    </div>
  );
});

const AnswersScreen = memo(function AnswersScreen({ 
  problemId, 
  className 
}: AnswersScreenProps) {

  // Fetch the solution (single solution)
  const { data: solution, isLoading: solutionsLoading, error: solutionError } = useQuery({
    queryKey: [`/api/problems/${problemId}/official-solution`],
    enabled: !!problemId,
  });

  return (
    <div className={`space-y-6 ${className || ''}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-foreground flex items-center space-x-2">
            <Trophy className="w-6 h-6" />
            <span>Solutions</span>
          </h2>
        </div>
      </div>

      {/* Solutions Content */}
      <div className="space-y-6">
        {solutionsLoading && (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-muted-foreground">Loading solutions...</p>
          </div>
        )}

        {!solutionsLoading && !solutionError && solution && (
          <SolutionDisplay
            key={solution.id}
            solution={solution}
          />
        )}

        {!solutionsLoading && (solutionError || !solution) && (
          <div className="text-center py-12">
            <Trophy className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-foreground mb-2">
              No solution yet
            </h3>
            <p className="text-muted-foreground">
              {solutionError?.response?.status === 404 
                ? "The solution hasn't been published for this problem yet."
                : "Solutions haven't been published for this problem yet."
              }
            </p>
          </div>
        )}
      </div>
    </div>
  );
});

export default AnswersScreen;