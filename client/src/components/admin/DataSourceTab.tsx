import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Trash2, Plus, CheckCircle, XCircle, Info } from 'lucide-react';
import { useAdmin } from '@/contexts/AdminContext';

export function DataSourceTab() {
  const { state, actions } = useAdmin();
  const [solutionPath, setSolutionPath] = useState('');

  const addMultiTableDataset = () => {
    actions.setMultiTableDatasets([
      ...state.multiTableDatasets,
      { bucket: '', key: '', table_name: '', description: '' }
    ]);
  };

  const removeMultiTableDataset = (index: number) => {
    actions.setMultiTableDatasets(
      state.multiTableDatasets.filter((_, i) => i !== index)
    );
  };

  const updateMultiTableDataset = (index: number, field: string, value: string) => {
    const updated = [...state.multiTableDatasets];
    updated[index] = { ...updated[index], [field]: value };
    actions.setMultiTableDatasets(updated);
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Data Source Management</CardTitle>
          <p className="text-sm text-muted-foreground">
            Validate S3 datasets and configure solution verification. 
            Apply validated data to Create Question tab.
          </p>
        </CardHeader>
      </Card>

      <Tabs defaultValue="single" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="single" data-testid="tab-single-dataset">Single Dataset</TabsTrigger>
          <TabsTrigger value="multi" data-testid="tab-multi-dataset">Multi-table Dataset</TabsTrigger>
        </TabsList>

        <TabsContent value="single" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Single S3 Dataset Validation</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="s3-bucket">S3 Bucket Name</Label>
                <Input
                  id="s3-bucket"
                  value={state.s3Source.bucket}
                  onChange={(e) => actions.setS3Source({ ...state.s3Source, bucket: e.target.value })}
                  placeholder="my-datasets-bucket"
                  data-testid="input-s3-bucket"
                />
                <p className="text-xs text-muted-foreground">
                  The S3 bucket containing your dataset
                </p>
              </div>

              <div>
                <Label htmlFor="s3-key">S3 Object Key</Label>
                <Input
                  id="s3-key"
                  value={state.s3Source.key}
                  onChange={(e) => actions.setS3Source({ ...state.s3Source, key: e.target.value })}
                  placeholder="datasets/sales.parquet"
                  data-testid="input-s3-key"
                />
                <p className="text-xs text-muted-foreground">
                  The path to your parquet file within the bucket
                </p>
              </div>

              <div>
                <Label htmlFor="s3-table-name">Table Name in DuckDB</Label>
                <Input
                  id="s3-table-name"
                  value={state.s3Source.table_name}
                  onChange={(e) => actions.setS3Source({ ...state.s3Source, table_name: e.target.value })}
                  placeholder="problem_data"
                  data-testid="input-s3-table-name"
                />
                <p className="text-xs text-muted-foreground">
                  What to call this table in the SQL environment
                </p>
              </div>

              <div>
                <Label htmlFor="s3-description">Description (Optional)</Label>
                <Input
                  id="s3-description"
                  value={state.s3Source.description}
                  onChange={(e) => actions.setS3Source({ ...state.s3Source, description: e.target.value })}
                  placeholder="Dataset description"
                  data-testid="input-s3-description"
                />
                <p className="text-xs text-muted-foreground">
                  Brief description of this dataset
                </p>
              </div>

              <div className="space-y-4">
                <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-md">
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    <strong>S3 Data Source:</strong> s3://{state.s3Source.bucket}/{state.s3Source.key}
                  </p>
                </div>

                <div className="flex gap-2">
                  <Button
                    onClick={actions.validateS3Dataset}
                    disabled={state.isValidatingS3 || !state.s3Source.bucket.trim() || !state.s3Source.key.trim()}
                    data-testid="button-validate-s3"
                  >
                    {state.isValidatingS3 ? 'Validating...' : 'Validate S3 Dataset'}
                  </Button>
                  
                  {state.s3Validation?.success && (
                    <Button
                      onClick={() => actions.applyValidationToDraft('single')}
                      variant="outline"
                      data-testid="button-apply-single"
                    >
                      Apply to Draft
                    </Button>
                  )}
                </div>

                {/* Validation Results */}
                {state.s3Validation && (
                  <Alert className={state.s3Validation.success ? 'border-green-200' : 'border-red-200'}>
                    {state.s3Validation.success ? (
                      <CheckCircle className="h-4 w-4 text-green-600" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-600" />
                    )}
                    <AlertDescription>
                      {state.s3Validation.success ? (
                        <div>
                          <p className="font-medium text-green-800">✓ S3 validation successful!</p>
                          <p className="text-sm">
                            Found {state.s3Validation.row_count?.toLocaleString()} rows with {state.s3Validation.table_schema?.length} columns
                          </p>
                          {state.s3Validation.table_schema && (
                            <div className="mt-2">
                              <p className="text-xs font-medium">Columns:</p>
                              <div className="flex flex-wrap gap-1 mt-1">
                                {state.s3Validation.table_schema.slice(0, 6).map((col, i) => (
                                  <Badge key={i} variant="outline" className="text-xs">
                                    {col.column} ({col.type})
                                  </Badge>
                                ))}
                                {state.s3Validation.table_schema.length > 6 && (
                                  <Badge variant="outline" className="text-xs">
                                    +{state.s3Validation.table_schema.length - 6} more
                                  </Badge>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div>
                          <p className="font-medium text-red-800">✗ S3 validation failed</p>
                          <p className="text-sm">{state.s3Validation.error}</p>
                        </div>
                      )}
                    </AlertDescription>
                  </Alert>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="multi" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Multi-table Dataset Validation</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {state.multiTableDatasets.map((dataset, index) => (
                <div key={index} className="border rounded p-4 space-y-3">
                  <div className="flex justify-between items-center">
                    <h4 className="font-medium">Dataset {index + 1}</h4>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeMultiTableDataset(index)}
                      data-testid={`button-remove-dataset-${index}`}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <Label>S3 Bucket</Label>
                      <Input
                        value={dataset.bucket}
                        onChange={(e) => updateMultiTableDataset(index, 'bucket', e.target.value)}
                        placeholder="my-datasets-bucket"
                        data-testid={`input-dataset-${index}-bucket`}
                      />
                    </div>
                    <div>
                      <Label>S3 Key</Label>
                      <Input
                        value={dataset.key}
                        onChange={(e) => updateMultiTableDataset(index, 'key', e.target.value)}
                        placeholder="datasets/table1.parquet"
                        data-testid={`input-dataset-${index}-key`}
                      />
                    </div>
                    <div>
                      <Label>Table Name</Label>
                      <Input
                        value={dataset.table_name}
                        onChange={(e) => updateMultiTableDataset(index, 'table_name', e.target.value)}
                        placeholder="orders"
                        data-testid={`input-dataset-${index}-table-name`}
                      />
                    </div>
                    <div>
                      <Label>Description</Label>
                      <Input
                        value={dataset.description}
                        onChange={(e) => updateMultiTableDataset(index, 'description', e.target.value)}
                        placeholder="Orders table"
                        data-testid={`input-dataset-${index}-description`}
                      />
                    </div>
                  </div>
                </div>
              ))}

              <Button onClick={addMultiTableDataset} variant="outline" data-testid="button-add-dataset">
                <Plus className="w-4 h-4 mr-2" />
                Add Dataset
              </Button>

              {/* Solution File Path - Only required for S3 verification */}
              {state.solutionVerification?.source === 's3' && (
                <div>
                  <Label htmlFor="solution-path">Solution File Path *</Label>
                  <Input
                    id="solution-path"
                    value={solutionPath}
                    onChange={(e) => setSolutionPath(e.target.value)}
                    placeholder="problems/multi001/solution.parquet"
                    data-testid="input-solution-path"
                  />
                  <p className="text-xs text-muted-foreground">
                    Path to the expected solution file in S3 (required when using S3 verification)
                  </p>
                </div>
              )}

              {/* Note for Neon verification */}
              {state.solutionVerification?.source === 'neon' && (
                <div className="p-3 bg-blue-50 dark:bg-blue-950 rounded-md border border-blue-200 dark:border-blue-800">
                  <p className="text-sm text-blue-700 dark:text-blue-200">
                    💡 Using Neon database verification - solution will be validated against manually entered expected results in the Create Question tab.
                  </p>
                </div>
              )}

              <div className="flex gap-2">
                <Button
                  onClick={() => actions.validateMultiTableDatasets(solutionPath)}
                  disabled={state.isValidatingMultiTable || state.multiTableDatasets.length === 0 || (state.solutionVerification?.source === 's3' && !solutionPath.trim())}
                  data-testid="button-validate-multi"
                >
                  {state.isValidatingMultiTable ? 'Validating...' : 'Validate Multi-table Datasets'}
                </Button>

                {state.multiTableValidation?.success && (
                  <Button
                    onClick={() => actions.applyValidationToDraft('multi')}
                    variant="outline"
                    data-testid="button-apply-multi"
                  >
                    Apply to Draft
                  </Button>
                )}
              </div>

              {/* Multi-table Validation Results */}
              {state.multiTableValidation && (
                <Alert className={state.multiTableValidation.success ? 'border-green-200' : 'border-red-200'}>
                  {state.multiTableValidation.success ? (
                    <CheckCircle className="h-4 w-4 text-green-600" />
                  ) : (
                    <XCircle className="h-4 w-4 text-red-600" />
                  )}
                  <AlertDescription>
                    {state.multiTableValidation.success ? (
                      <div>
                        <p className="font-medium text-green-800">✓ Multi-table validation successful!</p>
                        <p className="text-sm">
                          Validated {state.multiTableValidation.validated_datasets?.length} datasets with {state.multiTableValidation.total_rows?.toLocaleString()} total rows
                        </p>
                        {state.multiTableValidation.validated_datasets && (
                          <div className="mt-2 space-y-1">
                            {state.multiTableValidation.validated_datasets.map((dataset, i) => (
                              <div key={i} className="text-xs">
                                <Badge variant="outline" className="mr-2">{dataset.table_name}</Badge>
                                {dataset.row_count.toLocaleString()} rows, {dataset.table_schema?.length || 0} columns
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div>
                        <p className="font-medium text-red-800">✗ Multi-table validation failed</p>
                        <p className="text-sm">{state.multiTableValidation.error}</p>
                      </div>
                    )}
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Solution Verification - The SINGLE instance */}
      <Card>
        <CardHeader>
          <CardTitle>Solution Verification Method</CardTitle>
          <p className="text-sm text-muted-foreground">
            Configure how the solution will be verified for created questions.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3">
            <div 
              className={`p-4 border-2 rounded-lg cursor-pointer transition-colors ${
                state.solutionVerification?.source === 'neon' 
                  ? 'border-primary bg-primary/5' 
                  : 'border-border hover:border-primary/50'
              }`}
              onClick={() => actions.setSolutionType('neon')}
              data-testid="option-solution-source-neon"
            >
              <div className="flex items-center space-x-2">
                <div className={`w-4 h-4 rounded-full border-2 ${
                  state.solutionVerification?.source === 'neon' ? 'border-primary bg-primary' : 'border-border'
                }`}></div>
                <div>
                  <div className="font-medium">Neon Database</div>
                  <div className="text-sm text-muted-foreground">Solution stored in PostgreSQL</div>
                </div>
              </div>
            </div>

            <div 
              className={`p-4 border-2 rounded-lg cursor-pointer transition-colors ${
                state.solutionVerification?.source === 's3' 
                  ? 'border-primary bg-primary/5' 
                  : 'border-border hover:border-primary/50'
              }`}
              onClick={() => actions.setSolutionType('s3')}
              data-testid="option-solution-source-s3"
            >
              <div className="flex items-center space-x-2">
                <div className={`w-4 h-4 rounded-full border-2 ${
                  state.solutionVerification?.source === 's3' ? 'border-primary bg-primary' : 'border-border'
                }`}></div>
                <div>
                  <div className="font-medium">S3 Dataset</div>
                  <div className="text-sm text-muted-foreground">Solution as parquet file in S3</div>
                </div>
              </div>
            </div>
          </div>

          {/* Neon Database Configuration and Guidance */}
          {state.solutionVerification?.source === 'neon' && (
            <div className="space-y-3 p-4 bg-blue-50 dark:bg-blue-950 rounded-md border border-blue-200 dark:border-blue-800">
              <div className="flex items-start space-x-2">
                <Info className="h-5 w-5 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                <div className="space-y-3">
                  <div>
                    <h4 className="font-medium text-blue-900 dark:text-blue-100">How Neon Database Solution Works</h4>
                    <p className="text-sm text-blue-700 dark:text-blue-200 mt-1">
                      When using Neon database for solution verification, the system will automatically generate and store the expected results.
                    </p>
                  </div>
                  
                  <div className="space-y-2">
                    <div className="text-sm">
                      <p className="font-medium text-blue-900 dark:text-blue-100">Expected Result Structure:</p>
                      <ul className="mt-1 space-y-1 text-blue-700 dark:text-blue-200 list-disc list-inside">
                        <li>Results will be stored as JSON in the <code className="bg-blue-100 dark:bg-blue-900 px-1 rounded text-xs">expected_output</code> field</li>
                        <li>Each row represents one record of the expected solution</li>
                        <li>Column names must match your SQL query's SELECT clause</li>
                        <li>Data types will be automatically inferred and validated</li>
                      </ul>
                    </div>
                    
                    <div className="text-sm">
                      <p className="font-medium text-blue-900 dark:text-blue-100">How to Set Expected Results:</p>
                      <ol className="mt-1 space-y-1 text-blue-700 dark:text-blue-200 list-decimal list-inside">
                        <li>Create your problem with the dataset(s) above</li>
                        <li>In the "Create Question" tab, manually enter the expected results in the Expected Output section</li>
                        <li>Or run your solution SQL query and copy the results</li>
                        <li>The system will automatically validate submissions against these stored results</li>
                      </ol>
                    </div>

                    <div className="text-sm p-2 bg-blue-100 dark:bg-blue-900 rounded">
                      <p className="font-medium text-blue-900 dark:text-blue-100">💡 Tip:</p>
                      <p className="text-blue-700 dark:text-blue-200">
                        Test your SQL query first with the validated dataset above, then copy the exact results as your expected output.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* S3 Solution Configuration */}
          {state.solutionVerification?.source === 's3' && (
            <div className="space-y-3 p-4 bg-gray-50 dark:bg-gray-800 rounded-md">
              <div>
                <Label>S3 Solution Bucket</Label>
                <Input
                  value={state.solutionVerification.s3_solution_source?.bucket || ''}
                  onChange={(e) => {
                    const newConfig = {
                      bucket: e.target.value,
                      key: state.solutionVerification?.s3_solution_source?.key || '',
                      description: state.solutionVerification?.s3_solution_source?.description || ''
                    };
                    actions.updateS3SolutionConfig(newConfig);
                  }}
                  placeholder="my-solutions-bucket"
                  data-testid="input-s3-solution-bucket"
                />
              </div>

              <div>
                <Label>S3 Solution Key</Label>
                <Input
                  value={state.solutionVerification.s3_solution_source?.key || ''}
                  onChange={(e) => {
                    const newConfig = {
                      bucket: state.solutionVerification?.s3_solution_source?.bucket || '',
                      key: e.target.value,
                      description: state.solutionVerification?.s3_solution_source?.description || ''
                    };
                    actions.updateS3SolutionConfig(newConfig);
                  }}
                  placeholder="solutions/problem001.parquet"
                  data-testid="input-s3-solution-key"
                />
              </div>

              <div>
                <Label>Description (Optional)</Label>
                <Input
                  value={state.solutionVerification.s3_solution_source?.description || ''}
                  onChange={(e) => {
                    const newConfig = {
                      bucket: state.solutionVerification?.s3_solution_source?.bucket || '',
                      key: state.solutionVerification?.s3_solution_source?.key || '',
                      description: e.target.value
                    };
                    actions.updateS3SolutionConfig(newConfig);
                  }}
                  placeholder="Solution description"
                  data-testid="input-s3-solution-description"
                />
              </div>

              <Button
                onClick={() => {
                  if (state.solutionVerification?.s3_solution_source) {
                    actions.verifySolution('s3', state.solutionVerification.s3_solution_source);
                  }
                }}
                size="sm"
                data-testid="button-verify-s3-solution"
              >
                Verify S3 Solution
              </Button>
            </div>
          )}

          {/* Verification Status */}
          {state.solutionVerification && (
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                <div className="flex items-center space-x-2">
                  {state.solutionVerification.verified ? (
                    <CheckCircle className="h-4 w-4 text-green-500" />
                  ) : (
                    <XCircle className="h-4 w-4 text-red-500" />
                  )}
                  <span>
                    Solution verification: {state.solutionVerification.verified ? 'Verified' : 'Not Verified'} 
                    ({state.solutionVerification.source.toUpperCase()})
                  </span>
                </div>
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>
    </div>
  );
}