import { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Trash2, Edit, Save, X } from 'lucide-react';
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

interface SolutionCreate {
  title: string;
  content: string;
  sql_code: string;
  is_official: boolean;
}

export function SolutionsTab() {
  const { state } = useAdmin();
  const { toast } = useToast();
  const [selectedProblemId, setSelectedProblemId] = useState('');
  const [editingSolution, setEditingSolution] = useState<Solution | null>(null);
  const [solutionForm, setSolutionForm] = useState<SolutionCreate>({
    title: '',
    content: '',
    sql_code: '',
    is_official: true
  });

  // React Query for problems
  const { data: problems = [], isLoading: problemsLoading } = useQuery({
    queryKey: ['/api/problems'],
    enabled: state.isAuthenticated
  });

  // React Query for solutions
  const { data: solutions = [], isLoading: solutionsLoading, refetch: refetchSolutions } = useQuery({
    queryKey: ['/api/admin/problems', selectedProblemId, 'solutions'],
    enabled: !!selectedProblemId && state.isAuthenticated,
    queryFn: async () => {
      const response = await fetch(`/api/admin/problems/${selectedProblemId}/solutions`, {
        headers: {
          'Authorization': `Bearer ${state.adminKey}`
        }
      });
      if (!response.ok) {
        throw new Error('Failed to fetch solutions');
      }
      return response.json();
    }
  });

  // Create solution mutation
  const createSolutionMutation = useMutation({
    mutationFn: async (solutionData: SolutionCreate) => {
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
        throw new Error(error.detail || 'Failed to create solution');
      }
      
      return response.json();
    },
    onSuccess: () => {
      toast({
        title: "Success",
        description: "Solution created successfully"
      });
      setSolutionForm({ title: '', content: '', sql_code: '', is_official: true });
      queryClient.invalidateQueries({ queryKey: ['/api/admin/problems', selectedProblemId, 'solutions'] });
    },
    onError: (error: Error) => {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive"
      });
    }
  });

  // Update solution mutation
  const updateSolutionMutation = useMutation({
    mutationFn: async ({ solutionId, data }: { solutionId: string, data: SolutionCreate }) => {
      const response = await fetch(`/api/admin/solutions/${solutionId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${state.adminKey}`
        },
        body: JSON.stringify(data)
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to update solution');
      }
      
      return response.json();
    },
    onSuccess: () => {
      toast({
        title: "Success",
        description: "Solution updated successfully"
      });
      setEditingSolution(null);
      setSolutionForm({ title: '', content: '', sql_code: '', is_official: true });
      queryClient.invalidateQueries({ queryKey: ['/api/admin/problems', selectedProblemId, 'solutions'] });
    },
    onError: (error: Error) => {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive"
      });
    }
  });

  // Delete solution mutation
  const deleteSolutionMutation = useMutation({
    mutationFn: async (solutionId: string) => {
      const response = await fetch(`/api/admin/solutions/${solutionId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${state.adminKey}`
        }
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to delete solution');
      }
      return response.json();
    },
    onSuccess: () => {
      toast({
        title: "Success",
        description: "Solution deleted successfully"
      });
      queryClient.invalidateQueries({ queryKey: ['/api/admin/problems', selectedProblemId, 'solutions'] });
    },
    onError: (error: Error) => {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive"
      });
    }
  });

  const deleteSolution = (solutionId: string) => {
    if (!confirm('Are you sure you want to delete this solution?')) return;
    deleteSolutionMutation.mutate(solutionId);
  };

  const editSolution = (solution: Solution) => {
    setEditingSolution(solution);
    setSolutionForm({
      title: solution.title,
      content: solution.content,
      sql_code: solution.sql_code,
      is_official: solution.is_official
    });
  };

  const handleSubmit = () => {
    if (!selectedProblemId) {
      toast({
        title: "Error",
        description: "Please select a problem first",
        variant: "destructive"
      });
      return;
    }

    if (editingSolution) {
      updateSolutionMutation.mutate({
        solutionId: editingSolution.id,
        data: solutionForm
      });
    } else {
      createSolutionMutation.mutate(solutionForm);
    }
  };

  const cancelEdit = () => {
    setEditingSolution(null);
    setSolutionForm({ title: '', content: '', sql_code: '', is_official: true });
  };

  // Clear editing state when problem changes
  useEffect(() => {
    if (editingSolution) {
      setEditingSolution(null);
      setSolutionForm({ title: '', content: '', sql_code: '', is_official: true });
    }
  }, [selectedProblemId, editingSolution]);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Solutions Management</CardTitle>
          <p className="text-sm text-muted-foreground">
            Manage solutions for existing problems. Select a problem to view and edit its solutions.
          </p>
        </CardHeader>
      </Card>

      <Tabs defaultValue="manage" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="manage" data-testid="tab-manage-solutions">Manage Solutions</TabsTrigger>
          <TabsTrigger value="create" data-testid="tab-create-solution">Create Solution</TabsTrigger>
        </TabsList>

        <TabsContent value="manage" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Problem Selection</CardTitle>
            </CardHeader>
            <CardContent>
              <div>
                <Label htmlFor="problem-select">Select a Problem</Label>
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

          {selectedProblemId && (
            <Card>
              <CardHeader>
                <CardTitle>Solutions for Selected Problem</CardTitle>
              </CardHeader>
              <CardContent>
                {solutionsLoading ? (
                  <div>Loading solutions...</div>
                ) : solutions.length === 0 ? (
                  <Alert>
                    <AlertDescription>
                      No solutions found for this problem. Create one using the "Create Solution" tab.
                    </AlertDescription>
                  </Alert>
                ) : (
                  <div className="space-y-4">
                    {solutions.map((solution: Solution) => (
                      <div key={solution.id} className="border rounded p-4">
                        <div className="flex justify-between items-start mb-2">
                          <div className="flex items-center space-x-2">
                            <h4 className="font-medium">{solution.title}</h4>
                            {solution.is_official && (
                              <Badge variant="default">Official</Badge>
                            )}
                          </div>
                          <div className="flex space-x-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => editSolution(solution)}
                              data-testid={`button-edit-solution-${solution.id}`}
                            >
                              <Edit className="w-4 h-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => deleteSolution(solution.id)}
                              data-testid={`button-delete-solution-${solution.id}`}
                            >
                              <Trash2 className="w-4 h-4 text-red-500" />
                            </Button>
                          </div>
                        </div>

                        <p className="text-sm text-gray-600 mb-2">{solution.content}</p>
                        
                        <div className="bg-gray-50 dark:bg-gray-800 rounded p-3 mb-2">
                          <code className="text-sm">{solution.sql_code}</code>
                        </div>

                        <div className="text-xs text-gray-500">
                          By {solution.creator.username} • {new Date(solution.created_at).toLocaleDateString()}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="create" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>
                {editingSolution ? 'Edit Solution' : 'Create New Solution'}
              </CardTitle>
              {editingSolution && (
                <Alert>
                  <AlertDescription>
                    Editing solution: {editingSolution.title}
                  </AlertDescription>
                </Alert>
              )}
            </CardHeader>
            <CardContent className="space-y-4">
              {!selectedProblemId && (
                <Alert>
                  <AlertDescription>
                    Please select a problem from the "Manage Solutions" tab first.
                  </AlertDescription>
                </Alert>
              )}

              <div>
                <Label htmlFor="solution-title">Solution Title</Label>
                <Input
                  id="solution-title"
                  value={solutionForm.title}
                  onChange={(e) => setSolutionForm(prev => ({ ...prev, title: e.target.value }))}
                  placeholder="e.g., Optimized JOIN solution"
                  disabled={!selectedProblemId}
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
                  disabled={!selectedProblemId}
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
                  disabled={!selectedProblemId}
                  data-testid="textarea-solution-sql"
                />
              </div>

              <div>
                <Label>Solution Type</Label>
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={solutionForm.is_official}
                    onChange={(e) => setSolutionForm(prev => ({ ...prev, is_official: e.target.checked }))}
                    disabled={!selectedProblemId}
                    data-testid="checkbox-official-solution"
                  />
                  <span>Mark as official solution</span>
                </div>
              </div>

              <div className="flex justify-end space-x-2">
                {editingSolution && (
                  <Button variant="outline" onClick={cancelEdit} data-testid="button-cancel-edit">
                    <X className="w-4 h-4 mr-2" />
                    Cancel
                  </Button>
                )}
                <Button 
                  onClick={handleSubmit}
                  disabled={!selectedProblemId || !solutionForm.title.trim() || !solutionForm.sql_code.trim() || createSolutionMutation.isPending || updateSolutionMutation.isPending}
                  data-testid="button-submit-solution"
                >
                  <Save className="w-4 h-4 mr-2" />
                  {editingSolution ? 'Update Solution' : 'Create Solution'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}