import { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Save, FileText, Plus } from 'lucide-react';
import { useAdmin } from '@/contexts/AdminContext';
import { useToast } from '@/hooks/use-toast';
import { queryClient } from '@/lib/queryClient';

interface Solution {
  id: string;
  problem_id: string;
  title: string;
  content: string;
  sql_code: string;
  is_official: boolean;
  created_at: string;
  creator: {
    id: string;
    username: string;
  };
}

interface SolutionForm {
  title: string;
  content: string;
  sql_code: string;
}

export function SolutionsTab() {
  const { state } = useAdmin();
  const { toast } = useToast();
  const [selectedProblemId, setSelectedProblemId] = useState('');
  const [solutionForm, setSolutionForm] = useState<SolutionForm>({
    title: '',
    content: '',
    sql_code: ''
  });

  // React Query for problems
  const { data: problems = [], isLoading: problemsLoading } = useQuery({
    queryKey: ['/api/problems'],
    enabled: state.isAuthenticated
  });

  // React Query for existing solution (new endpoint)
  const { data: existingSolution, isLoading: solutionLoading, error: solutionError } = useQuery({
    queryKey: ['/api/admin/problems', selectedProblemId, 'solution'],
    enabled: !!selectedProblemId && state.isAuthenticated,
    queryFn: async () => {
      const response = await fetch(`/api/admin/problems/${selectedProblemId}/solution`, {
        headers: {
          'Authorization': `Bearer ${state.adminKey}`
        }
      });
      if (!response.ok) {
        if (response.status === 404) {
          return null; // No solution exists yet
        }
        throw new Error('Failed to fetch solution');
      }
      return response.json();
    }
  });

  // Create or update solution mutation
  const saveSolutionMutation = useMutation({
    mutationFn: async (solutionData: SolutionForm) => {
      const response = await fetch(`/api/admin/problems/${selectedProblemId}/solutions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${state.adminKey}`
        },
        body: JSON.stringify(solutionData)
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to save solution');
      }
      
      return response.json();
    },
    onSuccess: () => {
      toast({
        title: "Success",
        description: existingSolution ? "Solution updated successfully" : "Solution created successfully"
      });
      queryClient.invalidateQueries({ queryKey: ['/api/admin/problems', selectedProblemId, 'solution'] });
    },
    onError: (error: Error) => {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive"
      });
    }
  });

  const handleSubmit = () => {
    if (!selectedProblemId) {
      toast({
        title: "Error",
        description: "Please select a problem first",
        variant: "destructive"
      });
      return;
    }

    if (!solutionForm.title.trim() || !solutionForm.sql_code.trim()) {
      toast({
        title: "Error",
        description: "Please fill in the title and SQL code",
        variant: "destructive"
      });
      return;
    }

    saveSolutionMutation.mutate(solutionForm);
  };

  // Load existing solution data when problem changes
  useEffect(() => {
    if (existingSolution) {
      setSolutionForm({
        title: existingSolution.title || '',
        content: existingSolution.content || '',
        sql_code: existingSolution.sql_code || ''
      });
    } else {
      setSolutionForm({
        title: '',
        content: '',
        sql_code: ''
      });
    }
  }, [existingSolution, selectedProblemId]);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Solution Management</CardTitle>
          <p className="text-sm text-muted-foreground">
            Create or edit solutions for problems. Each problem has one solution.
          </p>
        </CardHeader>
      </Card>

      {/* Problem Selection */}
      <Card>
        <CardHeader>
          <CardTitle>Select Problem</CardTitle>
        </CardHeader>
        <CardContent>
          <div>
            <Label htmlFor="problem-select">Choose a Problem</Label>
            <select
              id="problem-select"
              value={selectedProblemId}
              onChange={(e) => setSelectedProblemId(e.target.value)}
              className="w-full p-2 border rounded-md"
              data-testid="select-problem"
            >
              <option value="">Choose a problem...</option>
              {problems.map((problem: any) => (
                <option key={problem.id} value={problem.id}>
                  {problem.title} ({problem.difficulty})
                </option>
              ))}
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Solution Form */}
      {selectedProblemId && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {existingSolution ? (
                <>
                  <FileText className="w-5 h-5" />
                  Edit Solution
                </>
              ) : (
                <>
                  <Plus className="w-5 h-5" />
                  Create Solution
                </>
              )}
            </CardTitle>
            {solutionLoading && (
              <p className="text-sm text-muted-foreground">Loading solution...</p>
            )}
            {existingSolution && (
              <Alert>
                <AlertDescription>
                  Editing existing solution for this problem.
                </AlertDescription>
              </Alert>
            )}
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="solution-title">Solution Title</Label>
              <Input
                id="solution-title"
                value={solutionForm.title}
                onChange={(e) => setSolutionForm(prev => ({ ...prev, title: e.target.value }))}
                placeholder="e.g., Optimized JOIN solution"
                data-testid="input-solution-title"
              />
            </div>

            <div>
              <Label htmlFor="solution-content">Solution Explanation</Label>
              <Textarea
                id="solution-content"
                value={solutionForm.content}
                onChange={(e) => setSolutionForm(prev => ({ ...prev, content: e.target.value }))}
                placeholder="Explain the approach and key insights..."
                rows={4}
                data-testid="textarea-solution-content"
              />
            </div>

            <div>
              <Label htmlFor="solution-sql">SQL Code</Label>
              <Textarea
                id="solution-sql"
                value={solutionForm.sql_code}
                onChange={(e) => setSolutionForm(prev => ({ ...prev, sql_code: e.target.value }))}
                placeholder="SELECT ..."
                rows={8}
                className="font-mono text-sm"
                data-testid="textarea-solution-sql"
              />
            </div>

            <div className="flex justify-end">
              <Button 
                onClick={handleSubmit}
                disabled={!solutionForm.title?.trim() || !solutionForm.sql_code?.trim() || saveSolutionMutation.isPending}
                data-testid="button-submit-solution"
              >
                <Save className="w-4 h-4 mr-2" />
                {saveSolutionMutation.isPending 
                  ? 'Saving...' 
                  : existingSolution 
                    ? 'Update Solution' 
                    : 'Create Solution'
                }
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {!selectedProblemId && (
        <Alert>
          <AlertDescription>
            Please select a problem above to create or edit its solution.
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}