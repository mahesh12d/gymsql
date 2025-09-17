import { memo } from 'react';
import { 
  Trophy,
  CheckCircle
} from 'lucide-react';
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface User {
  id: string;
  username: string;
  profileImageUrl?: string;
}

interface OfficialSolution {
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
  hasCorrectSubmission?: boolean;
  className?: string;
}

const OfficialSolutionCard = memo(function OfficialSolutionCard({
  solution,
  hasAccess
}: {
  solution: OfficialSolution;
  hasAccess: boolean;
}) {
  return (
    <Card className="mb-6 border-l-4 border-l-green-500" data-testid={`official-solution-${solution.id}`}>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-green-100 dark:bg-green-900/20 rounded-lg">
              <Trophy className="w-5 h-5 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <CardTitle className="text-lg" data-testid={`text-solution-title-${solution.id}`}>
                {solution.title}
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                Official Solution by {solution.creator.username}
              </p>
            </div>
          </div>
          <Badge variant="secondary" className="bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-300">
            <CheckCircle className="w-3 h-3 mr-1" />
            Verified
          </Badge>
        </div>
      </CardHeader>
      
      <CardContent>
        {hasAccess ? (
          <div className="space-y-4">
            <div>
              <h4 className="font-medium text-foreground mb-2">Explanation:</h4>
              <div className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed" data-testid={`text-solution-explanation-${solution.id}`}>
                {solution.content}
              </div>
            </div>
            
            <div>
              <h4 className="font-medium text-foreground mb-2">SQL Solution:</h4>
              <div className="bg-muted/50 rounded-lg p-4">
                <pre className="text-sm font-mono whitespace-pre-wrap text-foreground" data-testid={`code-solution-${solution.id}`}>
                  {solution.sqlCode}
                </pre>
              </div>
            </div>
          </div>
        ) : (
          <Alert className="border-orange-200 bg-orange-50 dark:bg-orange-950/30">
            <AlertDescription className="text-orange-800 dark:text-orange-200">
              🔒 Solve this problem first to unlock the official solution!
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
});

const AnswersScreen = memo(function AnswersScreen({ 
  problemId, 
  hasCorrectSubmission = false, 
  className 
}: AnswersScreenProps) {
  // Fetch admin solutions only
  const { data: adminSolutions = [], isLoading: solutionsLoading } = useQuery({
    queryKey: [`/api/problems/${problemId}/solutions`, problemId],
    enabled: !!problemId,
  });

  return (
    <div className={`space-y-6 ${className || ''}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-foreground flex items-center space-x-2">
            <Trophy className="w-6 h-6" />
            <span>Official Solutions</span>
          </h2>
          <p className="text-muted-foreground mt-1">
            Official solutions by the admin
          </p>
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

        {!solutionsLoading && adminSolutions.length > 0 && (
          adminSolutions.map((solution: OfficialSolution) => (
            <OfficialSolutionCard
              key={solution.id}
              solution={solution}
              hasAccess={hasCorrectSubmission}
            />
          ))
        )}

        {!solutionsLoading && adminSolutions.length === 0 && (
          <div className="text-center py-12">
            <Trophy className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-foreground mb-2">
              No solutions yet
            </h3>
            <p className="text-muted-foreground">
              Official solutions haven't been published for this problem yet.
            </p>
          </div>
        )}
      </div>
    </div>
  );
});

export default AnswersScreen;