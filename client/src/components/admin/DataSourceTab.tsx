import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Trash2, Plus, CheckCircle, XCircle, Info } from 'lucide-react';
import { useAdmin } from '@/contexts/AdminContext';

export function DataSourceTab() {
  const { state, actions } = useAdmin();
  const [solutionPath, setSolutionPath] = useState('');

  // Unified dataset management - supports both single and multiple datasets
  const datasets = state.datasets.length > 0 ? state.datasets : [{ bucket: '', key: '', table_name: '', description: '' }];

  const addDataset = () => {
    actions.setDatasets([
      ...state.datasets,
      { bucket: '', key: '', table_name: '', description: '' }
    ]);
  };

  const removeDataset = (index: number) => {
    if (state.datasets.length > 1) {
      actions.setDatasets(
        state.datasets.filter((_, i) => i !== index)
      );
    }
  };

  const updateDataset = (index: number, field: string, value: string) => {
    const updated = [...state.datasets];
    updated[index] = { ...updated[index], [field]: value };
    actions.setDatasets(updated);
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Data Source Management</CardTitle>
          <p className="text-sm text-muted-foreground">
            Validate S3 datasets and configure solution verification. 
            Supports single or multiple datasets. Apply validated data to Create Question tab.
          </p>
        </CardHeader>
      </Card>

      <div className="space-y-4">
        <Card>
          <CardHeader>
            <div className="flex justify-between items-center">
              <CardTitle>S3 Dataset Configuration</CardTitle>
              <Button
                onClick={addDataset}
                variant="outline"
                size="sm"
                data-testid="button-add-dataset"
              >
                <Plus className="w-4 h-4 mr-1" />
                Add Dataset
              </Button>
            </div>
            <p className="text-sm text-muted-foreground">
              Configure one or more S3 datasets. Each dataset will be loaded as a separate table.
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            {datasets.map((dataset, index) => (
              <div key={index} className="border rounded-lg p-4 space-y-3">
                <div className="flex justify-between items-center">
                  <h4 className="font-medium">
                    {datasets.length === 1 ? "Dataset" : `Dataset ${index + 1}`}
                  </h4>
                  {datasets.length > 1 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeDataset(index)}
                      data-testid={`button-remove-dataset-${index}`}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label>S3 Bucket Name</Label>
                    <Input
                      value={dataset.bucket}
                      onChange={(e) => updateDataset(index, 'bucket', e.target.value)}
                      placeholder="my-datasets-bucket"
                      data-testid={`input-dataset-${index}-bucket`}
                    />
                    <p className="text-xs text-muted-foreground">
                      The S3 bucket containing your dataset
                    </p>
                  </div>
                  <div>
                    <Label>S3 Object Key</Label>
                    <Input
                      value={dataset.key}
                      onChange={(e) => updateDataset(index, 'key', e.target.value)}
                      placeholder="datasets/table1.parquet"
                      data-testid={`input-dataset-${index}-key`}
                    />
                    <p className="text-xs text-muted-foreground">
                      The path to your parquet file within the bucket
                    </p>
                  </div>
                  <div>
                    <Label>Table Name in DuckDB</Label>
                    <Input
                      value={dataset.table_name}
                      onChange={(e) => updateDataset(index, 'table_name', e.target.value)}
                      placeholder={`table_${index + 1}`}
                      data-testid={`input-dataset-${index}-table-name`}
                    />
                    <p className="text-xs text-muted-foreground">
                      What to call this table in the SQL environment
                    </p>
                  </div>
                  <div>
                    <Label>Description (Optional)</Label>
                    <Input
                      value={dataset.description}
                      onChange={(e) => updateDataset(index, 'description', e.target.value)}
                      placeholder="Dataset description"
                      data-testid={`input-dataset-${index}-description`}
                    />
                    <p className="text-xs text-muted-foreground">
                      Brief description of this dataset
                    </p>
                  </div>
                </div>

                <div className="p-3 bg-gray-50 dark:bg-gray-800 rounded-md">
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    <strong>S3 Data Source:</strong> s3://{dataset.bucket}/{dataset.key} → {dataset.table_name}
                  </p>
                </div>
              </div>
            ))}

            <div className="space-y-4 pt-4 border-t">
              <div className="flex gap-2">
                <Button
                  onClick={() => actions.validateDatasets(solutionPath)}
                  disabled={state.isValidatingDatasets || datasets.some(d => !d.bucket?.trim() || !d.key?.trim())}
                  data-testid="button-validate-datasets"
                >
                  {state.isValidatingDatasets ? 'Validating...' : 'Validate Datasets'}
                </Button>
                
                {state.datasetValidation?.success && (
                  <Button
                    onClick={() => actions.applyValidationToDraft('unified')}
                    variant="outline"
                    data-testid="button-apply-datasets"
                  >
                    Apply to Draft
                  </Button>
                )}
              </div>

              {/* Validation Results */}
              {state.datasetValidation && (
                <Alert className={state.datasetValidation.success ? 'border-green-200' : 'border-red-200'}>
                  {state.datasetValidation.success ? (
                    <CheckCircle className="h-4 w-4 text-green-600" />
                  ) : (
                    <XCircle className="h-4 w-4 text-red-600" />
                  )}
                  <AlertDescription>
                    {state.datasetValidation.success ? (
                      <div>
                        <p className="font-medium text-green-800">✓ Dataset validation successful!</p>
                        <p className="text-sm">
                          Found {state.datasetValidation.total_tables} table(s) with {state.datasetValidation.total_rows?.toLocaleString()} total rows
                        </p>
                        {state.datasetValidation.validated_datasets && (
                          <div className="mt-2 space-y-2">
                            {state.datasetValidation.validated_datasets.map((dataset, i) => (
                              <div key={i} className="text-sm border rounded p-2">
                                <p className="font-medium">{dataset.table_name}: {dataset.row_count?.toLocaleString()} rows</p>
                                <div className="flex flex-wrap gap-1 mt-1">
                                  {dataset.table_schema?.slice(0, 4).map((col, j) => (
                                    <Badge key={j} variant="outline" className="text-xs">
                                      {col.column} ({col.type})
                                    </Badge>
                                  ))}
                                  {(dataset.table_schema?.length || 0) > 4 && (
                                    <Badge variant="outline" className="text-xs">
                                      +{(dataset.table_schema?.length || 0) - 4} more
                                    </Badge>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div>
                        <p className="font-medium text-red-800">✗ Dataset validation failed</p>
                        <p className="text-sm">{state.datasetValidation.error}</p>
                      </div>
                    )}
                  </AlertDescription>
                </Alert>
              )}
            </div>
          </CardContent>
        </Card>
        
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md p-4">
          <div className="flex">
            <Info className="w-4 h-4 text-yellow-600 dark:text-yellow-400 mt-0.5 mr-2 flex-shrink-0" />
            <div className="text-sm">
              <p className="font-medium text-yellow-800 dark:text-yellow-200 mb-1">Solution Verification Method</p>
              <div className="space-y-2">
                <label className="flex items-center space-x-2">
                  <input
                    type="radio"
                    name="solution-source"
                    value="neon"
                    checked={state.solutionVerification?.source === 'neon' || !state.solutionVerification}
                    onChange={() => actions.setSolutionVerification({ source: 'neon', verified: false })}
                  />
                  <span className="text-yellow-700 dark:text-yellow-300">Manual entry (recommended) - Enter expected results manually</span>
                </label>
              </div>
            </div>
          </div>
        </div>

        {/* Note for Neon verification */}
        {(!state.solutionVerification || state.solutionVerification?.source === 'neon') && (
          <div className="p-3 bg-blue-50 dark:bg-blue-950 rounded-md border border-blue-200 dark:border-blue-800">
            <p className="text-sm text-blue-700 dark:text-blue-200">
              💡 Using Neon database verification - solution will be validated against manually entered expected results in the Create Question tab.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}