import { memo } from 'react';
import { Code2, MessageSquare, CheckCircle } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import ProblemDescriptionTab from '@/components/ProblemDescriptionTab';

interface Problem {
  question?: {
    description?: string;
    tables?: any[];
    expectedOutput?: any[];
  };
  hints?: string[];
  tags?: string[];
}

interface Submission {
  id: string;
  isCorrect: boolean;
  submittedAt: string;
  executionTime?: number;
}

interface ProblemTabsContentProps {
  problem?: Problem;
  userSubmissions?: Submission[];
  className?: string;
}

const ProblemTabsContent = memo(function ProblemTabsContent({
  problem,
  userSubmissions = [],
  className,
}: ProblemTabsContentProps) {
  const hasCorrectSubmission = userSubmissions.some((sub) => sub.isCorrect);

  return (
    <div className={`h-full flex flex-col ${className || ''}`}>
      <Tabs defaultValue="problem" className="flex flex-col h-full">
        <TabsList className="w-full justify-start border-b bg-transparent p-0 h-auto rounded-none">
          <TabsTrigger
            value="problem"
            className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none"
            data-testid="tab-problem"
          >
            Problem
          </TabsTrigger>
          <TabsTrigger
            value="solution"
            className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none"
            data-testid="tab-solution"
          >
            Solution
          </TabsTrigger>
          <TabsTrigger
            value="discussion"
            className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none"
            data-testid="tab-discussion"
          >
            Discussion
          </TabsTrigger>
          <TabsTrigger
            value="submission"
            className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none"
            data-testid="tab-submission"
          >
            Submissions
          </TabsTrigger>
        </TabsList>

        <TabsContent
          value="problem"
          className="flex-1 overflow-auto p-6 pt-0 mt-0"
          data-testid="content-problem"
        >
          <ProblemDescriptionTab problem={problem} />
        </TabsContent>

        <TabsContent
          value="solution"
          className="flex-1 overflow-auto p-6 pt-0 mt-0"
          data-testid="content-solution"
        >
          <div className="space-y-6">
            <div className="text-center py-8">
              <Code2 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-foreground mb-2">
                Solution
              </h3>
              <p className="text-muted-foreground mb-4">
                Complete this problem to view the official solution and
                explanations.
              </p>
              {!hasCorrectSubmission && (
                <Alert className="border-yellow-200 bg-yellow-50 dark:bg-yellow-950/30">
                  <AlertDescription className="text-yellow-800 dark:text-yellow-200">
                    💡 Solve the problem first to unlock the detailed
                    solution walkthrough!
                  </AlertDescription>
                </Alert>
              )}
              {hasCorrectSubmission && (
                <div className="mt-6 p-6 bg-muted/50 rounded-lg">
                  <h4 className="font-semibold mb-4">Official Solution:</h4>
                  <div className="text-left font-mono text-sm bg-background rounded border p-4">
                    <p className="text-muted-foreground">
                      [Solution code would be displayed here]
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </TabsContent>

        <TabsContent
          value="discussion"
          className="flex-1 overflow-auto p-6 pt-0 mt-0"
          data-testid="content-discussion"
        >
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-foreground">
                Discussion
              </h3>
              <Button
                variant="outline"
                size="sm"
                data-testid="button-new-discussion"
              >
                <MessageSquare className="h-4 w-4 mr-2" />
                New Discussion
              </Button>
            </div>

            <div className="space-y-4">
              <div className="text-center py-8">
                <MessageSquare className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h4 className="text-base font-semibold text-foreground mb-2">
                  No discussions yet
                </h4>
                <p className="text-muted-foreground mb-4">
                  Be the first to start a discussion about this problem!
                </p>
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent
          value="submission"
          className="flex-1 overflow-auto p-6 pt-0 mt-0"
          data-testid="content-submission"
        >
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-foreground">
                My Submissions
              </h3>
              <div className="text-sm text-muted-foreground">
                {userSubmissions.length} submissions
              </div>
            </div>

            {userSubmissions.length > 0 ? (
              <div className="space-y-3">
                {userSubmissions.map((submission, index) => (
                  <Card key={submission.id} className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3">
                        <div
                          className={`w-3 h-3 rounded-full ${
                            submission.isCorrect ? "bg-green-500" : "bg-red-500"
                          }`}
                        />
                        <span className="text-sm font-mono">
                          Submission {index + 1}
                        </span>
                        {submission.isCorrect && (
                          <Badge className="bg-green-100 text-green-800 text-xs">
                            ✓ Accepted
                          </Badge>
                        )}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {new Date(submission.submittedAt).toLocaleDateString()}
                      </div>
                    </div>
                    <div className="mt-3 text-sm text-muted-foreground">
                      Runtime: {submission.executionTime || "N/A"}ms
                    </div>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <CheckCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h4 className="text-base font-semibold text-foreground mb-2">
                  No submissions yet
                </h4>
                <p className="text-muted-foreground mb-4">
                  Submit your first solution to see it here!
                </p>
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
});

export default ProblemTabsContent;