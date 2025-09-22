import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Trash2, Plus, Info, Eye, EyeOff } from 'lucide-react';
import { useAdmin } from '@/contexts/AdminContext';
import { useToast } from '@/hooks/use-toast';
import { apiRequest, queryClient } from '@/lib/queryClient';

export function CreateQuestionTab() {
  const { state, actions } = useAdmin();
  const { toast } = useToast();
  const [tagInput, setTagInput] = useState('');
  const [hintInput, setHintInput] = useState('');
  const [expectedOutputJson, setExpectedOutputJson] = useState('[]');
  const [showJsonPreview, setShowJsonPreview] = useState(false);
  const [jsonValidationError, setJsonValidationError] = useState('');

  const createProblemMutation = useMutation({
    mutationFn: async (problemData: any) => {
      const response = await fetch('/api/admin/problems', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${state.adminKey}`,
        },
        body: JSON.stringify({
          ...problemData,
          solution_source: state.solutionVerification?.source || 'neon',
          s3_solution_source: state.solutionVerification?.s3_solution_source
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create problem');
      }
      
      return response.json();
    },
    onSuccess: (result) => {
      toast({
        title: "Success",
        description: `Problem "${state.problemDraft.title}" created successfully!`,
      });
      actions.resetDraft();
      queryClient.invalidateQueries({ queryKey: ['/api/problems'] });
    },
    onError: (error: Error) => {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive",
      });
    }
  });

  const handleSubmit = () => {
    try {
      const expectedOutput = JSON.parse(expectedOutputJson);
      const problemData = {
        ...state.problemDraft,
        expectedOutput, // Use the new dedicated column
        question: {
          ...state.problemDraft.question,
          // Remove expectedOutput from question object (now in dedicated column)
          // Include s3_data_source if it exists in the question
          ...(state.problemDraft.question.s3_data_source && {
            s3_data_source: state.problemDraft.question.s3_data_source
          })
        }
      };
      
      createProblemMutation.mutate(problemData);
    } catch (error) {
      toast({
        title: "Error",
        description: "Invalid JSON in expected output",
        variant: "destructive",
      });
    }
  };

  // Validate JSON as user types
  const handleJsonChange = (value: string) => {
    setExpectedOutputJson(value);
    
    if (!value.trim()) {
      setJsonValidationError('');
      return;
    }
    
    try {
      JSON.parse(value);
      setJsonValidationError('');
    } catch (error) {
      setJsonValidationError(error instanceof Error ? error.message : 'Invalid JSON');
    }
  };

  // Parse JSON for preview
  const getParsedJson = () => {
    try {
      return JSON.parse(expectedOutputJson);
    } catch {
      return null;
    }
  };

  const addTag = () => {
    if (tagInput.trim() && !state.problemDraft.tags.includes(tagInput.trim())) {
      actions.updateDraft({
        tags: [...state.problemDraft.tags, tagInput.trim()]
      });
      setTagInput('');
    }
  };

  const removeTag = (tag: string) => {
    actions.updateDraft({
      tags: state.problemDraft.tags.filter(t => t !== tag)
    });
  };

  const addHint = () => {
    if (hintInput.trim()) {
      actions.updateDraft({
        hints: [...state.problemDraft.hints, hintInput.trim()]
      });
      setHintInput('');
    }
  };

  const removeHint = (index: number) => {
    actions.updateDraft({
      hints: state.problemDraft.hints.filter((_, i) => i !== index)
    });
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Create Question</CardTitle>
          {state.problemDraft.question.tables.length > 0 && (
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                📊 {state.problemDraft.question.tables.length} table(s) loaded from validation
              </AlertDescription>
            </Alert>
          )}
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="title">Problem Title *</Label>
            <Input
              id="title"
              value={state.problemDraft.title}
              onChange={(e) => actions.updateDraft({ title: e.target.value })}
              placeholder="e.g., Calculate Total Sales by Region"
              data-testid="input-title"
            />
          </div>

          <div>
            <Label htmlFor="difficulty">Difficulty *</Label>
            <select
              id="difficulty"
              value={state.problemDraft.difficulty}
              onChange={(e) => actions.updateDraft({ difficulty: e.target.value })}
              className="w-full p-2 border rounded-md"
              data-testid="select-difficulty"
            >
              {state.schemaInfo?.difficulty_options.map(diff => (
                <option key={diff} value={diff}>{diff}</option>
              ))}
            </select>
          </div>

          <div>
            <Label htmlFor="topic">Topic (Optional)</Label>
            <select
              id="topic"
              value={state.problemDraft.topic_id}
              onChange={(e) => actions.updateDraft({ topic_id: e.target.value })}
              className="w-full p-2 border rounded-md"
              data-testid="select-topic"
            >
              <option value="">Select a topic (optional)</option>
              {state.schemaInfo?.available_topics.map(topic => (
                <option key={topic.id} value={topic.id}>{topic.name}</option>
              ))}
            </select>
          </div>

          <div>
            <Label htmlFor="company">Company (Optional)</Label>
            <Input
              id="company"
              value={state.problemDraft.company}
              onChange={(e) => actions.updateDraft({ company: e.target.value })}
              placeholder="e.g., TechCorp"
              data-testid="input-company"
            />
          </div>

          <div>
            <Label>Premium Problem</Label>
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={state.problemDraft.premium}
                onChange={(e) => actions.updateDraft({ premium: e.target.checked })}
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
        </CardHeader>
        <CardContent>
          <Textarea
            value={state.problemDraft.question.description}
            onChange={(e) => actions.updateDraft({
              question: { ...state.problemDraft.question, description: e.target.value }
            })}
            placeholder="Describe the SQL problem here..."
            rows={8}
            data-testid="textarea-description"
          />
        </CardContent>
      </Card>

      {/* Table Preview */}
      {state.problemDraft.question.tables.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Tables Preview ({state.problemDraft.question.tables.length})</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {state.problemDraft.question.tables.map((table, index) => (
              <div key={index} className="border rounded p-4">
                <h4 className="font-medium mb-2">{table.name}</h4>
                <div className="text-sm text-gray-600 mb-2">
                  {table.columns.length} columns, {table.sample_data.length} sample rows
                </div>
                <div className="grid grid-cols-4 gap-2 text-xs">
                  {table.columns.slice(0, 4).map((col, colIndex) => (
                    <div key={colIndex} className="font-medium">{col.name}</div>
                  ))}
                  {table.columns.length > 4 && (
                    <div className="text-gray-500">...and {table.columns.length - 4} more</div>
                  )}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Tags */}
      <Card>
        <CardHeader>
          <CardTitle>Tags</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex space-x-2">
            <Input
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              placeholder="Add a tag"
              data-testid="input-tag"
            />
            <Button onClick={addTag} data-testid="button-add-tag">
              <Plus className="w-4 h-4 mr-2" />
              Add
            </Button>
          </div>
          <div className="flex flex-wrap gap-2">
            {state.problemDraft.tags.map((tag) => (
              <Badge key={tag} variant="secondary" className="flex items-center space-x-1">
                <span>{tag}</span>
                <button onClick={() => removeTag(tag)} data-testid={`button-remove-tag-${tag}`}>
                  <Trash2 className="w-3 h-3" />
                </button>
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Hints */}
      <Card>
        <CardHeader>
          <CardTitle>Hints</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex space-x-2">
            <Input
              value={hintInput}
              onChange={(e) => setHintInput(e.target.value)}
              placeholder="Add a hint"
              data-testid="input-hint"
            />
            <Button onClick={addHint} data-testid="button-add-hint">
              <Plus className="w-4 h-4 mr-2" />
              Add
            </Button>
          </div>
          <div className="space-y-2">
            {state.problemDraft.hints.map((hint, index) => (
              <div key={index} className="flex items-start space-x-2 p-2 bg-gray-50 dark:bg-gray-800 rounded">
                <span className="flex-1 text-sm">{hint}</span>
                <button onClick={() => removeHint(index)} data-testid={`button-remove-hint-${index}`}>
                  <Trash2 className="w-4 h-4 text-red-500" />
                </button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Expected Output - New JSONB Editor with Preview */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Expected Output (JSONB)</CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowJsonPreview(!showJsonPreview)}
              data-testid="button-toggle-preview"
            >
              {showJsonPreview ? <EyeOff className="w-4 h-4 mr-2" /> : <Eye className="w-4 h-4 mr-2" />}
              {showJsonPreview ? 'Hide Preview' : 'Show Preview'}
            </Button>
          </div>
          <p className="text-sm text-muted-foreground">
            Define the expected query results as JSON array. This will be stored in a dedicated JSONB column.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Textarea
              value={expectedOutputJson}
              onChange={(e) => handleJsonChange(e.target.value)}
              placeholder={`[\n  {"REGION": "North", "TOTAL_SALES": 15000},\n  {"REGION": "South", "TOTAL_SALES": 12000}\n]`}
              rows={8}
              className={`font-mono text-sm ${jsonValidationError ? 'border-red-500' : ''}`}
              data-testid="textarea-expected-output"
            />
            {jsonValidationError && (
              <Alert className="mt-2">
                <Info className="h-4 w-4" />
                <AlertDescription className="text-red-600">
                  <strong>JSON Error:</strong> {jsonValidationError}
                </AlertDescription>
              </Alert>
            )}
          </div>
          
          {/* JSON Preview */}
          {showJsonPreview && (
            <div className="border rounded-md">
              <div className="bg-gray-50 dark:bg-gray-800 px-3 py-2 border-b">
                <h4 className="text-sm font-medium">Preview</h4>
              </div>
              <div className="p-3">
                {getParsedJson() ? (
                  <div className="space-y-2">
                    {Array.isArray(getParsedJson()) ? (
                      <>
                        <div className="text-sm text-gray-600 dark:text-gray-400">
                          {getParsedJson().length} rows found
                        </div>
                        {getParsedJson().length > 0 && (
                          <div className="overflow-x-auto">
                            <table className="w-full text-sm border-collapse">
                              <thead>
                                <tr className="border-b">
                                  {Object.keys(getParsedJson()[0]).map((key) => (
                                    <th key={key} className="text-left p-2 font-medium bg-gray-50 dark:bg-gray-700">
                                      {key}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {getParsedJson().slice(0, 5).map((row: any, index: number) => (
                                  <tr key={index} className="border-b">
                                    {Object.values(row).map((value: any, colIndex: number) => (
                                      <td key={colIndex} className="p-2">
                                        {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                      </td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                            {getParsedJson().length > 5 && (
                              <div className="text-xs text-gray-500 mt-2">
                                ... and {getParsedJson().length - 5} more rows
                              </div>
                            )}
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="text-sm text-gray-600 dark:text-gray-400">
                        Expected output should be an array of objects
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-sm text-gray-500">
                    {expectedOutputJson.trim() ? 'Invalid JSON' : 'Enter valid JSON to see preview'}
                  </div>
                )}
              </div>
            </div>
          )}
          
          {/* Quick Examples */}
          <div className="text-xs text-gray-500 space-y-1">
            <div><strong>Example formats:</strong></div>
            <div>• Simple: <code>[{"{\"column\": \"value\"}"}]</code></div>
            <div>• Multiple rows: <code>[{"{\"id\": 1, \"name\": \"Alice\""}, {"{\"id\": 2, \"name\": \"Bob\"}"}]</code></div>
            <div>• Numbers: <code>[{"{\"total\": 15000, \"count\": 42}"}]</code></div>
          </div>
        </CardContent>
      </Card>

      {/* Solution Verification Status */}
      {state.solutionVerification && (
        <Card>
          <CardHeader>
            <CardTitle>Solution Verification</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`p-3 rounded-md ${
              state.solutionVerification.verified ? 'bg-green-50 dark:bg-green-900' : 'bg-red-50 dark:bg-red-900'
            }`}>
              <div className="flex items-center space-x-2">
                <span className={`w-2 h-2 rounded-full ${
                  state.solutionVerification.verified ? 'bg-green-500' : 'bg-red-500'
                }`}></span>
                <span className="text-sm">
                  {state.solutionVerification.verified ? 'Verified' : 'Not Verified'} - {state.solutionVerification.source.toUpperCase()}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Submit Button */}
      <div className="flex justify-end space-x-4">
        <Button variant="outline" onClick={actions.resetDraft} data-testid="button-reset">
          Reset Draft
        </Button>
        <Button 
          onClick={handleSubmit} 
          disabled={createProblemMutation.isPending || !state.problemDraft.title.trim()}
          data-testid="button-create-problem"
        >
          {createProblemMutation.isPending ? 'Creating...' : 'Create Problem'}
        </Button>
      </div>
    </div>
  );
}