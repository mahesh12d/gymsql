import { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiRequest, queryClient } from '@/lib/queryClient';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Trash2, Plus, Eye, Info, Code, Save, Edit } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface TableColumn {
  name: string;
  type: string;
  description: string;
}

interface TableData {
  name: string;
  columns: TableColumn[];
  sample_data: Record<string, any>[];
}

interface QuestionData {
  description: string;
  tables: TableData[];
  expectedOutput: Record<string, any>[];
}

interface ProblemData {
  title: string;
  difficulty: string;
  question: QuestionData;
  tags: string[];
  company: string;
  hints: string[];
  premium: boolean;
  topic_id: string;
}

interface SchemaInfo {
  problem_structure: Record<string, any>;
  example_problem: ProblemData;
  difficulty_options: string[];
  available_topics: { id: string; name: string }[];
}

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

export default function AdminPanel() {
  const { toast } = useToast();
  const [adminKey, setAdminKey] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [schemaInfo, setSchemaInfo] = useState<SchemaInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('create');

  // Form state
  const [problemData, setProblemData] = useState<ProblemData>({
    title: '',
    difficulty: 'Easy',
    question: {
      description: '',
      tables: [],
      expectedOutput: []
    },
    tags: [],
    company: '',
    hints: [],
    premium: false,
    topic_id: ''
  });

  const [tagInput, setTagInput] = useState('');
  const [hintInput, setHintInput] = useState('');
  
  // Solutions management state
  const [selectedProblemId, setSelectedProblemId] = useState('');
  const [editingSolution, setEditingSolution] = useState<Solution | null>(null);
  const [solutionForm, setSolutionForm] = useState<SolutionCreate>({
    title: '',
    content: '',
    sql_code: '',
    is_official: true
  });
  const [expectedOutputJson, setExpectedOutputJson] = useState('[]');
  const [sampleDataJson, setSampleDataJson] = useState<string[]>([]);
  const [expectedOutputRows, setExpectedOutputRows] = useState<Record<string, any>[]>([]);

  // Authentication
  const handleAuthenticate = async () => {
    if (!adminKey.trim()) {
      toast({
        title: "Error",
        description: "Please enter the admin key",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('/api/admin/schema-info', {
        headers: {
          'Authorization': `Bearer ${adminKey}`,
        },
      });

      if (response.ok) {
        const schema = await response.json();
        setSchemaInfo(schema);
        setIsAuthenticated(true);
        setProblemData(schema.example_problem);
        setExpectedOutputJson(JSON.stringify(schema.example_problem.question.expectedOutput, null, 2));
        setExpectedOutputRows(schema.example_problem.question.expectedOutput);
        setSampleDataJson(schema.example_problem.question.tables.map(table => 
          JSON.stringify(table.sample_data, null, 2)
        ));
        toast({
          title: "Success",
          description: "Admin access granted!",
        });
      } else {
        toast({
          title: "Authentication Failed",
          description: "Invalid admin key",
          variant: "destructive",
        });
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to authenticate",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  // React Query for problems
  const { data: problems = [], isLoading: problemsLoading } = useQuery({
    queryKey: ['/api/problems'],
    enabled: isAuthenticated
  });

  // React Query for solutions
  const { data: solutions = [], isLoading: solutionsLoading, refetch: refetchSolutions } = useQuery({
    queryKey: ['/api/admin/problems', selectedProblemId, 'solutions'],
    enabled: !!selectedProblemId && isAuthenticated,
    queryFn: async () => {
      const response = await fetch(`/api/admin/problems/${selectedProblemId}/solutions`, {
        headers: {
          'Authorization': `Bearer ${adminKey}`
        }
      });
      if (!response.ok) {
        throw new Error('Failed to fetch solutions');
      }
      return response.json();
    }
  });

  // React Query mutation for creating solutions
  const createSolutionMutation = useMutation({
    mutationFn: async (solutionData: SolutionCreate) => {
      const response = await fetch(`/api/admin/problems/${selectedProblemId}/solutions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${adminKey}`
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

  const createSolution = () => {
    if (!selectedProblemId) return;
    createSolutionMutation.mutate(solutionForm);
  };

  // React Query mutation for updating solutions
  const updateSolutionMutation = useMutation({
    mutationFn: async ({ solutionId, solutionData }: { solutionId: string; solutionData: SolutionCreate }) => {
      const response = await fetch(`/api/admin/solutions/${solutionId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${adminKey}`
        },
        body: JSON.stringify(solutionData)
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

  const updateSolution = () => {
    if (!editingSolution) return;
    updateSolutionMutation.mutate({ solutionId: editingSolution.id, solutionData: solutionForm });
  };

  // React Query mutation for deleting solutions
  const deleteSolutionMutation = useMutation({
    mutationFn: async (solutionId: string) => {
      const response = await fetch(`/api/admin/solutions/${solutionId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${adminKey}`
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

  // Clear editing state when problem changes
  useEffect(() => {
    if (editingSolution) {
      setEditingSolution(null);
      setSolutionForm({ title: '', content: '', sql_code: '', is_official: true });
    }
  }, [selectedProblemId, editingSolution]);

  // Form handlers
  const addTable = () => {
    setProblemData(prev => ({
      ...prev,
      question: {
        ...prev.question,
        tables: [...prev.question.tables, {
          name: '',
          columns: [],
          sample_data: []
        }]
      }
    }));
    setSampleDataJson(prev => [...prev, '[]']);
  };

  const removeTable = (index: number) => {
    setProblemData(prev => ({
      ...prev,
      question: {
        ...prev.question,
        tables: prev.question.tables.filter((_, i) => i !== index)
      }
    }));
    setSampleDataJson(prev => prev.filter((_, i) => i !== index));
  };

  const updateTable = (index: number, field: keyof TableData, value: any) => {
    setProblemData(prev => ({
      ...prev,
      question: {
        ...prev.question,
        tables: prev.question.tables.map((table, i) => 
          i === index ? { ...table, [field]: value } : table
        )
      }
    }));
  };

  const addColumn = (tableIndex: number) => {
    const newColumns = [...problemData.question.tables[tableIndex].columns, {
      name: '',
      type: 'VARCHAR(255)',
      description: ''
    }];
    updateTable(tableIndex, 'columns', newColumns);
  };

  const removeColumn = (tableIndex: number, columnIndex: number) => {
    const newColumns = problemData.question.tables[tableIndex].columns.filter((_, i) => i !== columnIndex);
    updateTable(tableIndex, 'columns', newColumns);
  };

  const updateColumn = (tableIndex: number, columnIndex: number, field: keyof TableColumn, value: string) => {
    const newColumns = problemData.question.tables[tableIndex].columns.map((col, i) => 
      i === columnIndex ? { ...col, [field]: value } : col
    );
    updateTable(tableIndex, 'columns', newColumns);
  };

  const addTag = () => {
    if (tagInput.trim() && !problemData.tags.includes(tagInput.trim())) {
      setProblemData(prev => ({
        ...prev,
        tags: [...prev.tags, tagInput.trim()]
      }));
      setTagInput('');
    }
  };

  const removeTag = (tag: string) => {
    setProblemData(prev => ({
      ...prev,
      tags: prev.tags.filter(t => t !== tag)
    }));
  };

  const addHint = () => {
    if (hintInput.trim()) {
      setProblemData(prev => ({
        ...prev,
        hints: [...prev.hints, hintInput.trim()]
      }));
      setHintInput('');
    }
  };

  const removeHint = (index: number) => {
    setProblemData(prev => ({
      ...prev,
      hints: prev.hints.filter((_, i) => i !== index)
    }));
  };

  const updateSampleData = (tableIndex: number, jsonString: string) => {
    const newSampleDataJson = [...sampleDataJson];
    newSampleDataJson[tableIndex] = jsonString;
    setSampleDataJson(newSampleDataJson);

    try {
      const parsed = JSON.parse(jsonString);
      updateTable(tableIndex, 'sample_data', Array.isArray(parsed) ? parsed : []);
    } catch (error) {
      // Invalid JSON, keep the string for user to fix
    }
  };

  const addSampleRow = (tableIndex: number) => {
    const table = problemData.question.tables[tableIndex];
    const newRow = table.columns.reduce((acc, col) => ({ ...acc, [col.name]: '' }), {});
    const newSampleData = [...table.sample_data, newRow];
    updateTable(tableIndex, 'sample_data', newSampleData);
  };

  const removeSampleRow = (tableIndex: number, rowIndex: number) => {
    const table = problemData.question.tables[tableIndex];
    const newSampleData = table.sample_data.filter((_, i) => i !== rowIndex);
    updateTable(tableIndex, 'sample_data', newSampleData);
  };

  const updateSampleRowField = (tableIndex: number, rowIndex: number, fieldName: string, value: any) => {
    const table = problemData.question.tables[tableIndex];
    const newSampleData = table.sample_data.map((row, i) => 
      i === rowIndex ? { ...row, [fieldName]: value } : row
    );
    updateTable(tableIndex, 'sample_data', newSampleData);
  };

  const addExpectedOutputRow = () => {
    setExpectedOutputRows(prev => [...prev, {}]);
  };

  const removeExpectedOutputRow = (index: number) => {
    setExpectedOutputRows(prev => prev.filter((_, i) => i !== index));
  };

  const updateExpectedOutputField = (rowIndex: number, fieldName: string, value: any) => {
    setExpectedOutputRows(prev => prev.map((row, i) => 
      i === rowIndex ? { ...row, [fieldName]: value } : row
    ));
  };

  const addFieldToExpectedOutput = (fieldName: string) => {
    if (fieldName.trim()) {
      setExpectedOutputRows(prev => prev.map(row => ({ ...row, [fieldName]: '' })));
    }
  };

  const getExpectedOutputFieldNames = () => {
    if (expectedOutputRows.length === 0) return [];
    return Object.keys(expectedOutputRows[0] || {});
  };

  const submitProblem = async () => {
    try {
      // Validation
      if (!problemData.title.trim()) {
        toast({
          title: "Validation Error",
          description: "Problem title is required",
          variant: "destructive",
        });
        return;
      }

      if (!problemData.question.description.trim()) {
        toast({
          title: "Validation Error",
          description: "Problem description is required",
          variant: "destructive",
        });
        return;
      }

      if (problemData.question.tables.length === 0) {
        toast({
          title: "Validation Error",
          description: "At least one table is required",
          variant: "destructive",
        });
        return;
      }

      // Validate tables have columns
      for (let i = 0; i < problemData.question.tables.length; i++) {
        const table = problemData.question.tables[i];
        if (!table.name.trim()) {
          toast({
            title: "Validation Error",
            description: `Table ${i + 1} name is required`,
            variant: "destructive",
          });
          return;
        }
        if (table.columns.length === 0) {
          toast({
            title: "Validation Error",
            description: `Table "${table.name}" must have at least one column`,
            variant: "destructive",
          });
          return;
        }
      }

      if (expectedOutputRows.length === 0) {
        toast({
          title: "Validation Error",
          description: "Expected output must have at least one row",
          variant: "destructive",
        });
        return;
      }

      const finalProblemData = {
        ...problemData,
        question: {
          ...problemData.question,
          tables: problemData.question.tables,
          expectedOutput: expectedOutputRows
        }
      };

      setLoading(true);
      const response = await fetch('/api/admin/problems', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${adminKey}`,
        },
        body: JSON.stringify(finalProblemData),
      });

      if (response.ok) {
        const result = await response.json();
        toast({
          title: "Success",
          description: `Problem "${result.title}" created successfully!`,
        });
        
        // Reset form with example
        if (schemaInfo) {
          setProblemData(schemaInfo.example_problem);
          setExpectedOutputJson(JSON.stringify(schemaInfo.example_problem.question.expectedOutput, null, 2));
          setSampleDataJson(schemaInfo.example_problem.question.tables.map(table => 
            JSON.stringify(table.sample_data, null, 2)
          ));
        }
      } else {
        const error = await response.json();
        toast({
          title: "Error",
          description: error.detail || "Failed to create problem",
          variant: "destructive",
        });
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to submit problem",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="container mx-auto py-8 max-w-md" data-testid="admin-login">
        <Card>
          <CardHeader>
            <CardTitle data-testid="text-admin-title">Admin Panel</CardTitle>
            <CardDescription>Enter your admin key to access the question creation interface</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="admin-key">Admin Key</Label>
              <Input
                id="admin-key"
                type="password"
                value={adminKey}
                onChange={(e) => setAdminKey(e.target.value)}
                placeholder="Enter admin key"
                data-testid="input-admin-key"
                onKeyPress={(e) => e.key === 'Enter' && handleAuthenticate()}
              />
            </div>
            <Button 
              onClick={handleAuthenticate} 
              disabled={loading}
              className="w-full"
              data-testid="button-authenticate"
            >
              {loading ? 'Authenticating...' : 'Access Admin Panel'}
            </Button>
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                For development, use the key: <code className="bg-muted px-1 rounded">admin-dev-key-123</code>
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8" data-testid="admin-panel">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2" data-testid="text-admin-header">Question Creator</h1>
        <p className="text-muted-foreground">Create SQL problems with proper schema validation</p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="create" data-testid="tab-create">Create Question</TabsTrigger>
          <TabsTrigger value="solutions" data-testid="tab-solutions">Solutions</TabsTrigger>
          <TabsTrigger value="schema" data-testid="tab-schema">Schema Info</TabsTrigger>
          <TabsTrigger value="example" data-testid="tab-example">Example</TabsTrigger>
        </TabsList>

        <TabsContent value="create" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Basic Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="title">Problem Title *</Label>
                <Input
                  id="title"
                  value={problemData.title}
                  onChange={(e) => setProblemData(prev => ({ ...prev, title: e.target.value }))}
                  placeholder="e.g., Calculate Total Sales by Region"
                  data-testid="input-title"
                />
              </div>

              <div>
                <Label htmlFor="difficulty">Difficulty *</Label>
                <select
                  id="difficulty"
                  value={problemData.difficulty}
                  onChange={(e) => setProblemData(prev => ({ ...prev, difficulty: e.target.value }))}
                  className="w-full p-2 border rounded-md"
                  data-testid="select-difficulty"
                >
                  {schemaInfo?.difficulty_options.map(diff => (
                    <option key={diff} value={diff}>{diff}</option>
                  ))}
                </select>
              </div>

              <div>
                <Label htmlFor="company">Company (Optional)</Label>
                <Input
                  id="company"
                  value={problemData.company}
                  onChange={(e) => setProblemData(prev => ({ ...prev, company: e.target.value }))}
                  placeholder="e.g., TechCorp"
                  data-testid="input-company"
                />
              </div>

              <div>
                <Label>Premium Problem</Label>
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={problemData.premium}
                    onChange={(e) => setProblemData(prev => ({ ...prev, premium: e.target.checked }))}
                    data-testid="checkbox-premium"
                  />
                  <span>Requires premium subscription</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Problem Description</CardTitle>
              <CardDescription>Write the problem description in Markdown format</CardDescription>
            </CardHeader>
            <CardContent>
              <Textarea
                value={problemData.question.description}
                onChange={(e) => setProblemData(prev => ({
                  ...prev,
                  question: { ...prev.question, description: e.target.value }
                }))}
                rows={10}
                placeholder="Write your problem description here..."
                data-testid="textarea-description"
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Database Tables</CardTitle>
              <CardDescription>Define the tables that students will work with</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {problemData.question.tables.map((table, tableIndex) => (
                <Card key={tableIndex} className="border border-dashed">
                  <CardHeader>
                    <div className="flex justify-between items-center">
                      <CardTitle className="text-lg">Table {tableIndex + 1}</CardTitle>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeTable(tableIndex)}
                        data-testid={`button-remove-table-${tableIndex}`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <Label>Table Name</Label>
                      <Input
                        value={table.name}
                        onChange={(e) => updateTable(tableIndex, 'name', e.target.value)}
                        placeholder="e.g., orders"
                        data-testid={`input-table-name-${tableIndex}`}
                      />
                    </div>

                    <div>
                      <div className="flex justify-between items-center mb-2">
                        <Label>Columns</Label>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => addColumn(tableIndex)}
                          data-testid={`button-add-column-${tableIndex}`}
                        >
                          <Plus className="h-4 w-4 mr-2" />
                          Add Column
                        </Button>
                      </div>
                      <div className="space-y-2">
                        {table.columns.map((column, columnIndex) => (
                          <div key={columnIndex} className="flex gap-2 items-center">
                            <Input
                              value={column.name}
                              onChange={(e) => updateColumn(tableIndex, columnIndex, 'name', e.target.value)}
                              placeholder="Column name"
                              className="flex-1"
                              data-testid={`input-column-name-${tableIndex}-${columnIndex}`}
                            />
                            <Input
                              value={column.type}
                              onChange={(e) => updateColumn(tableIndex, columnIndex, 'type', e.target.value)}
                              placeholder="Data type"
                              className="flex-1"
                              data-testid={`input-column-type-${tableIndex}-${columnIndex}`}
                            />
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => removeColumn(tableIndex, columnIndex)}
                              data-testid={`button-remove-column-${tableIndex}-${columnIndex}`}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between items-center mb-2">
                        <Label>Sample Data</Label>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => addSampleRow(tableIndex)}
                          disabled={table.columns.length === 0}
                          data-testid={`button-add-sample-row-${tableIndex}`}
                        >
                          <Plus className="h-4 w-4 mr-2" />
                          Add Row
                        </Button>
                      </div>
                      
                      {table.columns.length === 0 ? (
                        <div className="text-sm text-muted-foreground p-4 border rounded-md">
                          Add columns first to create sample data
                        </div>
                      ) : (
                        <div className="border rounded-md">
                          {table.columns.length > 0 && (
                            <div className="bg-muted p-2 grid gap-2" style={{ gridTemplateColumns: `repeat(${table.columns.length + 1}, 1fr)` }}>
                              {table.columns.map((col, colIndex) => (
                                <div key={colIndex} className="font-medium text-sm">
                                  {col.name} ({col.type})
                                </div>
                              ))}
                              <div className="font-medium text-sm">Actions</div>
                            </div>
                          )}
                          
                          {table.sample_data.map((row, rowIndex) => (
                            <div key={rowIndex} className="p-2 border-t grid gap-2" style={{ gridTemplateColumns: `repeat(${table.columns.length + 1}, 1fr)` }}>
                              {table.columns.map((col, colIndex) => (
                                <Input
                                  key={colIndex}
                                  value={row[col.name] || ''}
                                  onChange={(e) => updateSampleRowField(tableIndex, rowIndex, col.name, e.target.value)}
                                  placeholder={`Enter ${col.name}`}
                                  className="text-sm"
                                  data-testid={`input-sample-${tableIndex}-${rowIndex}-${col.name}`}
                                />
                              ))}
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => removeSampleRow(tableIndex, rowIndex)}
                                data-testid={`button-remove-sample-row-${tableIndex}-${rowIndex}`}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          ))}
                          
                          {table.sample_data.length === 0 && table.columns.length > 0 && (
                            <div className="p-4 text-center text-muted-foreground text-sm">
                              No sample data yet. Click "Add Row" to create sample data.
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
              
              <Button
                variant="outline"
                onClick={addTable}
                className="w-full"
                data-testid="button-add-table"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Table
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Expected Output</CardTitle>
              <CardDescription>Define the expected query result structure</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="flex gap-2 mb-4">
                  <Input
                    placeholder="Add field name (e.g., total_sales, region)"
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        const input = e.target as HTMLInputElement;
                        if (input.value.trim()) {
                          addFieldToExpectedOutput(input.value.trim());
                          input.value = '';
                        }
                      }
                    }}
                    data-testid="input-add-output-field"
                  />
                  <Button
                    variant="outline"
                    onClick={() => {
                      const input = document.querySelector('[data-testid="input-add-output-field"]') as HTMLInputElement;
                      if (input?.value.trim()) {
                        addFieldToExpectedOutput(input.value.trim());
                        input.value = '';
                      }
                    }}
                    data-testid="button-add-output-field"
                  >
                    Add Field
                  </Button>
                </div>
                
                <div className="flex justify-between items-center mb-2">
                  <Label>Expected Output Rows</Label>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={addExpectedOutputRow}
                    data-testid="button-add-output-row"
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Add Row
                  </Button>
                </div>
                
                {getExpectedOutputFieldNames().length === 0 ? (
                  <div className="text-sm text-muted-foreground p-4 border rounded-md">
                    Add field names first, then create expected output rows
                  </div>
                ) : (
                  <div className="border rounded-md">
                    {getExpectedOutputFieldNames().length > 0 && (
                      <div className="bg-muted p-2 grid gap-2" style={{ gridTemplateColumns: `repeat(${getExpectedOutputFieldNames().length + 1}, 1fr)` }}>
                        {getExpectedOutputFieldNames().map((fieldName, index) => (
                          <div key={index} className="font-medium text-sm">
                            {fieldName}
                          </div>
                        ))}
                        <div className="font-medium text-sm">Actions</div>
                      </div>
                    )}
                    
                    {expectedOutputRows.map((row, rowIndex) => (
                      <div key={rowIndex} className="p-2 border-t grid gap-2" style={{ gridTemplateColumns: `repeat(${getExpectedOutputFieldNames().length + 1}, 1fr)` }}>
                        {getExpectedOutputFieldNames().map((fieldName, fieldIndex) => (
                          <Input
                            key={fieldIndex}
                            value={row[fieldName] || ''}
                            onChange={(e) => updateExpectedOutputField(rowIndex, fieldName, e.target.value)}
                            placeholder={`Enter ${fieldName}`}
                            className="text-sm"
                            data-testid={`input-output-${rowIndex}-${fieldName}`}
                          />
                        ))}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeExpectedOutputRow(rowIndex)}
                          data-testid={`button-remove-output-row-${rowIndex}`}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                    
                    {expectedOutputRows.length === 0 && (
                      <div className="p-4 text-center text-muted-foreground text-sm">
                        No output rows yet. Click "Add Row" to create expected output data.
                      </div>
                    )}
                  </div>
                )}
              </div>
              
              <Separator />
              
              <details className="mt-4">
                <summary className="cursor-pointer text-sm font-medium mb-2">JSON Preview (Advanced)</summary>
                <Textarea
                  value={JSON.stringify(expectedOutputRows, null, 2)}
                  readOnly
                  rows={6}
                  className="font-mono text-xs bg-muted"
                  data-testid="textarea-expected-output-preview"
                />
              </details>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Tags & Hints</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Tags</Label>
                <div className="flex gap-2 mb-2">
                  <Input
                    value={tagInput}
                    onChange={(e) => setTagInput(e.target.value)}
                    placeholder="Add tag"
                    onKeyPress={(e) => e.key === 'Enter' && addTag()}
                    data-testid="input-tag"
                  />
                  <Button variant="outline" onClick={addTag} data-testid="button-add-tag">
                    Add
                  </Button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {problemData.tags.map((tag, index) => (
                    <Badge key={index} variant="secondary" className="cursor-pointer" onClick={() => removeTag(tag)}>
                      {tag} ×
                    </Badge>
                  ))}
                </div>
              </div>

              <div>
                <Label>Hints</Label>
                <div className="flex gap-2 mb-2">
                  <Input
                    value={hintInput}
                    onChange={(e) => setHintInput(e.target.value)}
                    placeholder="Add hint"
                    onKeyPress={(e) => e.key === 'Enter' && addHint()}
                    data-testid="input-hint"
                  />
                  <Button variant="outline" onClick={addHint} data-testid="button-add-hint">
                    Add
                  </Button>
                </div>
                <div className="space-y-2">
                  {problemData.hints.map((hint, index) => (
                    <div key={index} className="flex justify-between items-center p-2 bg-muted rounded">
                      <span className="text-sm">{hint}</span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeHint(index)}
                        data-testid={`button-remove-hint-${index}`}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="flex gap-4">
            <Button
              onClick={submitProblem}
              disabled={loading || !problemData.title.trim()}
              className="flex-1"
              size="lg"
              data-testid="button-submit-problem"
            >
              {loading ? 'Creating Problem...' : 'Create Problem'}
            </Button>
            
            <Button
              variant="outline"
              onClick={() => {
                if (schemaInfo) {
                  const exampleProblem = { ...schemaInfo.example_problem };
                  setProblemData(exampleProblem);
                  setExpectedOutputRows([...exampleProblem.question.expectedOutput]);
                  setTagInput('');
                  setHintInput('');
                  toast({
                    title: "Form Reset",
                    description: "Form has been reset with example data",
                  });
                }
              }}
              disabled={loading}
              size="lg"
              data-testid="button-reset-form"
            >
              Reset to Example
            </Button>
          </div>
        </TabsContent>

        <TabsContent value="solutions" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Code className="h-5 w-5" />
                Solutions Management
              </CardTitle>
              <CardDescription>
                Create and manage official solutions for problems
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Problem Selection */}
              <div className="space-y-2">
                <Label htmlFor="problem-select">Select Problem</Label>
                <select
                  id="problem-select"
                  className="w-full p-2 border rounded-md"
                  value={selectedProblemId}
                  onChange={(e) => setSelectedProblemId(e.target.value)}
                  data-testid="select-problem"
                >
                  <option value="">Select a problem...</option>
                  {(problems || []).map((problem: any) => (
                    <option key={problem.id} value={problem.id}>
                      {problem.title} ({problem.difficulty})
                    </option>
                  ))}
                </select>
              </div>

              {/* Solution Form */}
              {selectedProblemId && (
                <div className="space-y-4 p-4 border rounded-lg bg-gray-50 dark:bg-gray-800">
                  <h3 className="text-lg font-semibold">
                    {editingSolution ? 'Edit Solution' : 'Create New Solution'}
                  </h3>
                  
                  <div className="space-y-2">
                    <Label htmlFor="solution-title">Solution Title</Label>
                    <Input
                      id="solution-title"
                      placeholder="Enter solution title..."
                      value={solutionForm.title}
                      onChange={(e) => setSolutionForm(prev => ({ ...prev, title: e.target.value }))}
                      data-testid="input-solution-title"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="solution-content">Solution Explanation</Label>
                    <Textarea
                      id="solution-content"
                      placeholder="Explain the solution approach..."
                      value={solutionForm.content}
                      onChange={(e) => setSolutionForm(prev => ({ ...prev, content: e.target.value }))}
                      rows={4}
                      data-testid="textarea-solution-content"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="solution-sql">SQL Code</Label>
                    <Textarea
                      id="solution-sql"
                      placeholder="Enter the SQL solution..."
                      value={solutionForm.sql_code}
                      onChange={(e) => setSolutionForm(prev => ({ ...prev, sql_code: e.target.value }))}
                      rows={6}
                      className="font-mono"
                      data-testid="textarea-solution-sql"
                    />
                  </div>


                  <div className="flex gap-2">
                    <Button
                      onClick={() => editingSolution ? updateSolution() : createSolution()}
                      disabled={createSolutionMutation.isPending || updateSolutionMutation.isPending || !solutionForm.title || !solutionForm.content || !solutionForm.sql_code}
                      data-testid="button-save-solution"
                    >
                      <Save className="h-4 w-4 mr-2" />
                      {editingSolution ? 'Update Solution' : 'Create Solution'}
                    </Button>
                    
                    {editingSolution && (
                      <Button
                        variant="outline"
                        onClick={() => {
                          setEditingSolution(null);
                          setSolutionForm({ title: '', content: '', sql_code: '', is_official: true });
                        }}
                        data-testid="button-cancel-edit"
                      >
                        Cancel
                      </Button>
                    )}
                  </div>
                </div>
              )}

              {/* Existing Solutions */}
              {selectedProblemId && (solutions || []).length > 0 && (
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold">Existing Solutions</h3>
                  {(solutions || []).map((solution: Solution) => (
                    <Card key={solution.id} className="p-4">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <h4 className="font-semibold" data-testid={`text-solution-title-${solution.id}`}>
                              {solution.title}
                            </h4>
                            {solution.is_official && (
                              <Badge variant="default">Official</Badge>
                            )}
                          </div>
                          <p className="text-sm text-gray-600 dark:text-gray-400 mb-2" data-testid={`text-solution-content-${solution.id}`}>
                            {solution.content}
                          </p>
                          <pre className="bg-gray-100 dark:bg-gray-700 p-2 rounded text-sm overflow-x-auto" data-testid={`text-solution-sql-${solution.id}`}>
                            {solution.sql_code}
                          </pre>
                          <p className="text-xs text-gray-500 mt-2">
                            By {solution.creator.username} • {new Date(solution.created_at).toLocaleDateString()}
                          </p>
                        </div>
                        <div className="flex gap-2 ml-4">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => editSolution(solution)}
                            data-testid={`button-edit-solution-${solution.id}`}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() => deleteSolution(solution.id)}
                            data-testid={`button-delete-solution-${solution.id}`}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="schema" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Schema Structure</CardTitle>
              <CardDescription>Complete structure for creating problems</CardDescription>
            </CardHeader>
            <CardContent>
              <pre className="bg-muted p-4 rounded-lg overflow-auto text-sm">
                {JSON.stringify(schemaInfo?.problem_structure, null, 2)}
              </pre>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="example" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Example Problem</CardTitle>
              <CardDescription>Complete example with all fields</CardDescription>
            </CardHeader>
            <CardContent>
              <pre className="bg-muted p-4 rounded-lg overflow-auto text-sm">
                {JSON.stringify(schemaInfo?.example_problem, null, 2)}
              </pre>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}