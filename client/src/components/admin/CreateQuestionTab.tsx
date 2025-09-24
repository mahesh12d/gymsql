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
import { EnhancedTablePreview } from './EnhancedTablePreview';

export function CreateQuestionTab() {
  const { state, actions } = useAdmin();
  const { toast } = useToast();
  const [tagInput, setTagInput] = useState('');
  const [hintInput, setHintInput] = useState('');
  const [masterSolutionJson, setMasterSolutionJson] = useState('[]');
  const [showJsonPreview, setShowJsonPreview] = useState(false);
  const [jsonValidationError, setJsonValidationError] = useState('');
  const [solutionInputMode, setSolutionInputMode] = useState<'json' | 'table' | 'file'>('json');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [tableColumns, setTableColumns] = useState<Array<{name: string, type: string}>>([]);
  const [tableRows, setTableRows] = useState<Array<Record<string, any>>>([]);
  
  // Expected Display state variables
  const [expectedDisplayJson, setExpectedDisplayJson] = useState('[]');
  const [showDisplayPreview, setShowDisplayPreview] = useState(false);
  const [displayJsonValidationError, setDisplayJsonValidationError] = useState('');
  const [displayInputMode, setDisplayInputMode] = useState<'json' | 'table'>('json');
  const [displayTableColumns, setDisplayTableColumns] = useState<Array<{name: string, type: string}>>([]);
  const [displayTableRows, setDisplayTableRows] = useState<Array<Record<string, any>>>([]);

  const createProblemMutation = useMutation({
    mutationFn: async (problemData: any) => {
      // Use correct apiRequest signature: (method, url, data)
      return await apiRequest('POST', '/api/admin/problems', {
        ...problemData,
        solution_source: state.solutionVerification?.source || 'neon',
        // Remove s3_solution_source to avoid 422 errors
      });
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

  const convertParquetMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      
      // Use apiRequest and validate response in mutationFn for proper error handling
      const response = await apiRequest('POST', '/api/admin/convert-parquet', formData);
      const result = await response.json();
      
      // Validate response shape in mutationFn so errors go to onError
      if (!result || !result.data || !Array.isArray(result.data)) {
        throw new Error('Invalid response format from Parquet conversion');
      }
      
      const rows = result.data;
      
      // Validate data size
      if (rows.length === 0) {
        throw new Error('Parquet file is empty - no data was converted');
      }
      
      return result;
    },
    onSuccess: (result) => {
      const rows = result.data;
      const metadata = result.metadata || {};
      
      // Update the master solution with converted data
      setMasterSolutionJson(JSON.stringify(rows, null, 2));
      actions.updateDraft({ masterSolution: rows });
      
      // Switch back to JSON view to show the converted data
      setSolutionInputMode('json');
      
      toast({
        title: "Success",
        description: `Parquet file converted successfully! ${rows.length} rows loaded (${metadata.columns?.length || 'unknown'} columns).`,
      });
      
      // Clear the uploaded file
      setUploadedFile(null);
      setUploadError('');
    },
    onError: (error: Error) => {
      setUploadError(error.message);
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive",
      });
    }
  });

  const handleSubmit = () => {
    try {
      const masterSolution = solutionInputMode === 'json' 
        ? JSON.parse(masterSolutionJson) 
        : tableRows;
      
      const expectedDisplay = displayInputMode === 'json' 
        ? JSON.parse(expectedDisplayJson) 
        : displayTableRows;
      
      const problemData = {
        ...state.problemDraft,
        masterSolution, // Use the new master_solution field for validation
        expectedDisplay, // Display output for users (not validation)
        // Include s3_datasets if they exist at the top level
        ...(state.problemDraft.s3_datasets && {
          s3_datasets: state.problemDraft.s3_datasets
        }),
        question: {
          ...state.problemDraft.question,
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
        description: "Invalid JSON in master solution or expected display",
        variant: "destructive",
      });
    }
  };

  // Validate JSON as user types
  const handleJsonChange = (value: string) => {
    setMasterSolutionJson(value);
    
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
    if (solutionInputMode === 'table') {
      return tableRows;
    }
    try {
      return JSON.parse(masterSolutionJson);
    } catch {
      return null;
    }
  };

  // Helper functions for format conversion
  const convertJsonToTable = (jsonData: any[]) => {
    if (!Array.isArray(jsonData) || jsonData.length === 0) return;
    
    const columns = Object.keys(jsonData[0]).map(key => ({
      name: key,
      type: typeof jsonData[0][key] === 'number' ? 'number' : 
            typeof jsonData[0][key] === 'boolean' ? 'boolean' : 'text'
    }));
    
    setTableColumns(columns);
    setTableRows(jsonData);
  };

  const convertTableToJson = () => {
    return JSON.stringify(tableRows, null, 2);
  };

  // Expected Display helper functions
  const handleDisplayJsonChange = (value: string) => {
    setExpectedDisplayJson(value);
    
    if (!value.trim()) {
      setDisplayJsonValidationError('');
      return;
    }
    
    try {
      JSON.parse(value);
      setDisplayJsonValidationError('');
    } catch (error) {
      setDisplayJsonValidationError(error instanceof Error ? error.message : 'Invalid JSON');
    }
  };

  const getParsedDisplayJson = () => {
    if (displayInputMode === 'table') {
      return displayTableRows;
    }
    try {
      return JSON.parse(expectedDisplayJson);
    } catch {
      return null;
    }
  };

  const convertDisplayJsonToTable = (jsonData: any[]) => {
    if (!Array.isArray(jsonData) || jsonData.length === 0) return;
    
    const columns = Object.keys(jsonData[0]).map(key => ({
      name: key,
      type: typeof jsonData[0][key] === 'number' ? 'number' : 
            typeof jsonData[0][key] === 'boolean' ? 'boolean' : 'text'
    }));
    
    setDisplayTableColumns(columns);
    setDisplayTableRows(jsonData);
  };

  const convertDisplayTableToJson = () => {
    return JSON.stringify(displayTableRows, null, 2);
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

      {/* Enhanced Table Preview */}
      <EnhancedTablePreview 
        tables={state.problemDraft.question.tables}
        onTableUpdate={(updatedTables) => {
          actions.updateDraft({
            question: { 
              ...state.problemDraft.question, 
              tables: updatedTables 
            }
          });
        }}
      />

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

      {/* Master Solution - Enhanced JSONB Editor with Multiple Input Modes */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Master Solution</CardTitle>
            <div className="flex space-x-2">
              <select
                value={solutionInputMode}
                onChange={(e) => setSolutionInputMode(e.target.value as 'json' | 'table' | 'file')}
                className="text-sm border rounded px-2 py-1"
                data-testid="select-input-mode"
              >
                <option value="json">JSON Input</option>
                <option value="table">Table Builder</option>
                <option value="file">Parquet File Upload</option>
              </select>
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
          </div>
          <p className="text-sm text-muted-foreground">
            Define the definitive expected results for validation. This is used internally to check if user submissions are correct.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          {solutionInputMode === 'json' ? (
            <div>
              <Label>JSON Input</Label>
              <Textarea
                value={masterSolutionJson}
                onChange={(e) => handleJsonChange(e.target.value)}
                placeholder={`[\n  {"REGION": "North", "TOTAL_SALES": 15000},\n  {"REGION": "South", "TOTAL_SALES": 12000}\n]`}
                rows={8}
                className={`font-mono text-sm ${jsonValidationError ? 'border-red-500' : ''}`}
                data-testid="textarea-master-solution"
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
          ) : solutionInputMode === 'file' ? (
            <div>
              <Label>Parquet File Upload</Label>
              <p className="text-xs text-muted-foreground mb-2">
                Upload a Parquet file containing your expected results. Parquet files offer superior compression and performance for large datasets.
              </p>
              <div className="space-y-4">
                <div className="border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg p-6">
                  <input
                    type="file"
                    accept=".parquet"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) {
                        setUploadedFile(file);
                        setUploadError('');
                      }
                    }}
                    className="hidden"
                    id="parquet-upload"
                    data-testid="input-parquet-file"
                  />
                  <label
                    htmlFor="parquet-upload"
                    className="cursor-pointer flex flex-col items-center space-y-2"
                  >
                    <div className="text-4xl text-gray-400">📄</div>
                    <div className="text-sm text-center">
                      <span className="font-medium text-blue-600 hover:text-blue-500">
                        Click to upload
                      </span>{" "}
                      or drag and drop
                    </div>
                    <div className="text-xs text-gray-500">
                      Parquet files only (.parquet)
                    </div>
                  </label>
                </div>
                
                {uploadedFile && (
                  <div className="flex items-center justify-between p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded">
                    <div className="flex items-center space-x-2">
                      <div className="text-green-600">📄</div>
                      <div>
                        <div className="text-sm font-medium">{uploadedFile.name}</div>
                        <div className="text-xs text-gray-500">
                          {(uploadedFile.size / 1024 / 1024).toFixed(2)} MB
                        </div>
                      </div>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setUploadedFile(null)}
                      data-testid="button-remove-file"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                )}

                {uploadError && (
                  <Alert className="mt-2">
                    <Info className="h-4 w-4" />
                    <AlertDescription className="text-red-600">
                      <strong>Upload Error:</strong> {uploadError}
                    </AlertDescription>
                  </Alert>
                )}

                {uploadedFile && !isUploading && (
                  <Button
                    onClick={() => convertParquetMutation.mutate(uploadedFile)}
                    disabled={isUploading || convertParquetMutation.isPending}
                    className="w-full"
                    data-testid="button-convert-parquet"
                  >
                    {convertParquetMutation.isPending ? 'Converting...' : 'Convert to Master Solution'}
                  </Button>
                )}
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <Label>Table Builder</Label>
                <p className="text-xs text-muted-foreground mb-2">
                  Build your expected output table by defining columns and adding rows
                </p>
              </div>
              
              {/* Column Management */}
              <div className="border rounded-lg p-4">
                <h4 className="font-medium mb-2">Columns</h4>
                <div className="space-y-2">
                  {tableColumns.map((col, index) => (
                    <div key={index} className="flex items-center space-x-2">
                      <Input
                        placeholder="Column Name"
                        value={col.name}
                        onChange={(e) => {
                          const newColumns = [...tableColumns];
                          newColumns[index].name = e.target.value;
                          setTableColumns(newColumns);
                        }}
                        className="flex-1"
                        data-testid={`input-column-name-${index}`}
                      />
                      <select
                        value={col.type}
                        onChange={(e) => {
                          const newColumns = [...tableColumns];
                          newColumns[index].type = e.target.value;
                          setTableColumns(newColumns);
                        }}
                        className="border rounded px-2 py-1"
                        data-testid={`select-column-type-${index}`}
                      >
                        <option value="text">Text</option>
                        <option value="number">Number</option>
                        <option value="boolean">Boolean</option>
                        <option value="date">Date</option>
                      </select>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setTableColumns(tableColumns.filter((_, i) => i !== index));
                          // Remove this column from all rows
                          setTableRows(tableRows.map(row => {
                            const newRow = {...row};
                            delete newRow[col.name];
                            return newRow;
                          }));
                        }}
                        data-testid={`button-remove-column-${index}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  ))}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setTableColumns([...tableColumns, { name: '', type: 'text' }])}
                    data-testid="button-add-column"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Add Column
                  </Button>
                </div>
              </div>

              {/* Row Management */}
              {tableColumns.length > 0 && (
                <div className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium">Rows</h4>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        const newRow: Record<string, any> = {};
                        tableColumns.forEach(col => {
                          newRow[col.name] = col.type === 'number' ? 0 : col.type === 'boolean' ? false : '';
                        });
                        setTableRows([...tableRows, newRow]);
                      }}
                      data-testid="button-add-row"
                    >
                      <Plus className="w-4 h-4 mr-2" />
                      Add Row
                    </Button>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full border-collapse border">
                      <thead>
                        <tr>
                          {tableColumns.map((col, index) => (
                            <th key={index} className="border p-2 bg-gray-50 dark:bg-gray-800 text-left">
                              {col.name || 'Unnamed'}
                            </th>
                          ))}
                          <th className="border p-2 bg-gray-50 dark:bg-gray-800 w-10"></th>
                        </tr>
                      </thead>
                      <tbody>
                        {tableRows.map((row, rowIndex) => (
                          <tr key={rowIndex}>
                            {tableColumns.map((col, colIndex) => (
                              <td key={colIndex} className="border p-1">
                                {col.type === 'boolean' ? (
                                  <input
                                    type="checkbox"
                                    checked={row[col.name] || false}
                                    onChange={(e) => {
                                      const newRows = [...tableRows];
                                      newRows[rowIndex][col.name] = e.target.checked;
                                      setTableRows(newRows);
                                    }}
                                    data-testid={`checkbox-row-${rowIndex}-col-${colIndex}`}
                                  />
                                ) : (
                                  <Input
                                    type={col.type === 'number' ? 'number' : col.type === 'date' ? 'date' : 'text'}
                                    value={row[col.name] || ''}
                                    onChange={(e) => {
                                      const newRows = [...tableRows];
                                      newRows[rowIndex][col.name] = col.type === 'number' ? Number(e.target.value) : e.target.value;
                                      setTableRows(newRows);
                                    }}
                                    className="h-8"
                                    data-testid={`input-row-${rowIndex}-col-${colIndex}`}
                                  />
                                )}
                              </td>
                            ))}
                            <td className="border p-1">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => setTableRows(tableRows.filter((_, i) => i !== rowIndex))}
                                data-testid={`button-remove-row-${rowIndex}`}
                              >
                                <Trash2 className="w-3 h-3" />
                              </Button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
          
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
                    {masterSolutionJson.trim() ? 'Invalid JSON' : 'Enter valid JSON to see preview'}
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

      {/* Expected Display - What users see on the problem page */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Expected Display</CardTitle>
            <div className="flex space-x-2">
              <select
                value={displayInputMode}
                onChange={(e) => setDisplayInputMode(e.target.value as 'json' | 'table')}
                className="text-sm border rounded px-2 py-1"
                data-testid="select-display-input-mode"
              >
                <option value="json">JSON Input</option>
                <option value="table">Table Builder</option>
              </select>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowDisplayPreview(!showDisplayPreview)}
                data-testid="button-toggle-display-preview"
              >
                {showDisplayPreview ? <EyeOff className="w-4 h-4 mr-2" /> : <Eye className="w-4 h-4 mr-2" />}
                {showDisplayPreview ? 'Hide Preview' : 'Show Preview'}
              </Button>
            </div>
          </div>
          <p className="text-sm text-muted-foreground">
            Define what users see as the expected output on the problem page. This is for display purposes only and is not used for validation.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          {displayInputMode === 'json' ? (
            <div>
              <Label>JSON Input</Label>
              <Textarea
                value={expectedDisplayJson}
                onChange={(e) => handleDisplayJsonChange(e.target.value)}
                placeholder={`[\n  {"REGION": "North", "TOTAL_SALES": 15000},\n  {"REGION": "South", "TOTAL_SALES": 12000}\n]`}
                rows={8}
                className={`font-mono text-sm ${displayJsonValidationError ? 'border-red-500' : ''}`}
                data-testid="textarea-expected-display"
              />
              {displayJsonValidationError && (
                <Alert className="mt-2">
                  <Info className="h-4 w-4" />
                  <AlertDescription className="text-red-600">
                    <strong>JSON Error:</strong> {displayJsonValidationError}
                  </AlertDescription>
                </Alert>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <Label>Table Builder</Label>
                <p className="text-xs text-muted-foreground mb-2">
                  Build your expected display table by defining columns and adding rows
                </p>
              </div>
              
              {/* Column Management for Display */}
              <div className="border rounded-lg p-4">
                <h4 className="font-medium mb-2">Display Columns</h4>
                <div className="space-y-2">
                  {displayTableColumns.map((col, index) => (
                    <div key={index} className="flex items-center space-x-2">
                      <Input
                        value={col.name}
                        onChange={(e) => {
                          const newCols = [...displayTableColumns];
                          newCols[index].name = e.target.value;
                          setDisplayTableColumns(newCols);
                        }}
                        placeholder="Column name"
                        className="flex-1"
                      />
                      <select
                        value={col.type}
                        onChange={(e) => {
                          const newCols = [...displayTableColumns];
                          newCols[index].type = e.target.value;
                          setDisplayTableColumns(newCols);
                        }}
                        className="w-24 p-2 border rounded"
                      >
                        <option value="text">Text</option>
                        <option value="number">Number</option>
                        <option value="boolean">Boolean</option>
                      </select>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          const newCols = displayTableColumns.filter((_, i) => i !== index);
                          setDisplayTableColumns(newCols);
                          // Remove this column from all rows
                          const newRows = displayTableRows.map(row => {
                            const newRow = { ...row };
                            delete newRow[col.name];
                            return newRow;
                          });
                          setDisplayTableRows(newRows);
                        }}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  ))}
                  <Button
                    variant="outline"
                    onClick={() => {
                      setDisplayTableColumns([...displayTableColumns, { name: '', type: 'text' }]);
                    }}
                    className="w-full"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Add Column
                  </Button>
                </div>
              </div>

              {/* Row Management for Display */}
              {displayTableColumns.length > 0 && (
                <div className="border rounded-lg p-4">
                  <h4 className="font-medium mb-2">Display Rows</h4>
                  <div className="space-y-2">
                    {displayTableRows.map((row, rowIndex) => (
                      <div key={rowIndex} className="flex items-center space-x-2">
                        {displayTableColumns.map((col, colIndex) => (
                          <Input
                            key={colIndex}
                            value={row[col.name] || ''}
                            onChange={(e) => {
                              const newRows = [...displayTableRows];
                              newRows[rowIndex][col.name] = col.type === 'number' ? 
                                (e.target.value === '' ? '' : Number(e.target.value)) : 
                                e.target.value;
                              setDisplayTableRows(newRows);
                            }}
                            placeholder={col.name}
                            type={col.type === 'number' ? 'number' : 'text'}
                            className="flex-1"
                          />
                        ))}
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            const newRows = displayTableRows.filter((_, i) => i !== rowIndex);
                            setDisplayTableRows(newRows);
                          }}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    ))}
                    <Button
                      variant="outline"
                      onClick={() => {
                        const newRow: Record<string, any> = {};
                        displayTableColumns.forEach(col => {
                          newRow[col.name] = col.type === 'number' ? 0 : '';
                        });
                        setDisplayTableRows([...displayTableRows, newRow]);
                      }}
                      className="w-full"
                    >
                      <Plus className="w-4 h-4 mr-2" />
                      Add Row
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
          
          {/* Display JSON Preview */}
          {showDisplayPreview && (
            <div className="border rounded-md">
              <div className="bg-gray-50 dark:bg-gray-800 px-3 py-2 border-b">
                <h4 className="text-sm font-medium">Display Preview</h4>
              </div>
              <div className="p-3">
                {getParsedDisplayJson() ? (
                  <div className="space-y-2">
                    {Array.isArray(getParsedDisplayJson()) ? (
                      <>
                        <div className="text-sm text-gray-600 dark:text-gray-400">
                          {getParsedDisplayJson().length} rows found
                        </div>
                        {getParsedDisplayJson().length > 0 && (
                          <div className="overflow-x-auto">
                            <table className="w-full text-sm border-collapse">
                              <thead>
                                <tr className="border-b">
                                  {Object.keys(getParsedDisplayJson()[0]).map((key) => (
                                    <th key={key} className="text-left p-2 font-medium bg-gray-50 dark:bg-gray-700">
                                      {key}
                                    </th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {getParsedDisplayJson().slice(0, 5).map((row: any, index: number) => (
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
                            {getParsedDisplayJson().length > 5 && (
                              <div className="text-xs text-gray-500 mt-2">
                                ... and {getParsedDisplayJson().length - 5} more rows
                              </div>
                            )}
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="text-sm text-gray-600 dark:text-gray-400">
                        Expected display should be an array of objects
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-sm text-gray-500">
                    Enter valid JSON or use table builder to see preview
                  </div>
                )}
              </div>
            </div>
          )}
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