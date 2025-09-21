import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Info, Database, Eye } from 'lucide-react';
import { useAdmin } from '@/contexts/AdminContext';
import { useState } from 'react';

export function SchemaInfoTab() {
  const { state, actions } = useAdmin();
  const [showExample, setShowExample] = useState(false);

  const loadExample = () => {
    if (state.schemaInfo?.example_problem) {
      actions.updateDraft(state.schemaInfo.example_problem);
      actions.setActiveTab('create');
    }
  };

  if (!state.schemaInfo) {
    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Schema Information</CardTitle>
          </CardHeader>
          <CardContent>
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                Please authenticate with admin key to view schema information.
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Schema Information</CardTitle>
          <p className="text-sm text-muted-foreground">
            Database schema structure and available options for problem creation.
          </p>
        </CardHeader>
      </Card>

      {/* Difficulty Options */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Database className="w-5 h-5" />
            <span>Difficulty Options</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {state.schemaInfo.difficulty_options.map((difficulty) => (
              <Badge key={difficulty} variant="outline">
                {difficulty}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Available Topics */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Database className="w-5 h-5" />
            <span>Available Topics</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {state.schemaInfo.available_topics.map((topic) => (
              <div key={topic.id} className="flex items-center space-x-2 p-2 bg-gray-50 dark:bg-gray-800 rounded">
                <Badge variant="secondary">{topic.name}</Badge>
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  ID: {topic.id}
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Problem Structure */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Database className="w-5 h-5" />
            <span>Problem Structure</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="bg-gray-50 dark:bg-gray-800 rounded p-4">
            <pre className="text-sm overflow-auto">
              {JSON.stringify(state.schemaInfo.problem_structure, null, 2)}
            </pre>
          </div>
        </CardContent>
      </Card>

      {/* Example Problem */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Eye className="w-5 h-5" />
            <span>Example Problem</span>
          </CardTitle>
          <div className="flex space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowExample(!showExample)}
              data-testid="button-toggle-example"
            >
              {showExample ? 'Hide' : 'Show'} Example
            </Button>
            <Button
              size="sm"
              onClick={loadExample}
              data-testid="button-load-example"
            >
              Load Example to Draft
            </Button>
          </div>
        </CardHeader>
        {showExample && (
          <CardContent>
            <div className="space-y-4">
              {/* Basic Info */}
              <div>
                <h4 className="font-medium mb-2">Basic Information</h4>
                <div className="space-y-1 text-sm">
                  <div><strong>Title:</strong> {state.schemaInfo.example_problem.title}</div>
                  <div><strong>Difficulty:</strong> {state.schemaInfo.example_problem.difficulty}</div>
                  <div><strong>Company:</strong> {state.schemaInfo.example_problem.company || 'None'}</div>
                  <div><strong>Premium:</strong> {state.schemaInfo.example_problem.premium ? 'Yes' : 'No'}</div>
                </div>
              </div>

              {/* Tags */}
              {state.schemaInfo.example_problem.tags.length > 0 && (
                <div>
                  <h4 className="font-medium mb-2">Tags</h4>
                  <div className="flex flex-wrap gap-1">
                    {state.schemaInfo.example_problem.tags.map((tag, index) => (
                      <Badge key={index} variant="outline" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Description */}
              <div>
                <h4 className="font-medium mb-2">Description</h4>
                <div className="bg-gray-50 dark:bg-gray-800 rounded p-3 text-sm whitespace-pre-wrap">
                  {state.schemaInfo.example_problem.question.description}
                </div>
              </div>

              {/* Tables */}
              {state.schemaInfo.example_problem.question.tables.length > 0 && (
                <div>
                  <h4 className="font-medium mb-2">Tables ({state.schemaInfo.example_problem.question.tables.length})</h4>
                  <div className="space-y-3">
                    {state.schemaInfo.example_problem.question.tables.map((table, index) => (
                      <div key={index} className="border rounded p-3">
                        <div className="font-medium mb-2">{table.name}</div>
                        <div className="text-sm text-gray-600 mb-2">
                          {table.columns.length} columns, {table.sample_data.length} sample rows
                        </div>
                        <div className="grid grid-cols-3 gap-2 text-xs">
                          {table.columns.slice(0, 6).map((col, colIndex) => (
                            <div key={colIndex} className="font-medium">
                              {col.name} ({col.type})
                            </div>
                          ))}
                          {table.columns.length > 6 && (
                            <div className="text-gray-500">...and {table.columns.length - 6} more</div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Hints */}
              {state.schemaInfo.example_problem.hints.length > 0 && (
                <div>
                  <h4 className="font-medium mb-2">Hints</h4>
                  <div className="space-y-2">
                    {state.schemaInfo.example_problem.hints.map((hint, index) => (
                      <div key={index} className="text-sm p-2 bg-blue-50 dark:bg-blue-900 rounded">
                        {hint}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Expected Output */}
              {state.schemaInfo.example_problem.question.expectedOutput.length > 0 && (
                <div>
                  <h4 className="font-medium mb-2">Expected Output</h4>
                  <div className="bg-gray-50 dark:bg-gray-800 rounded p-3">
                    <pre className="text-xs overflow-auto">
                      {JSON.stringify(state.schemaInfo.example_problem.question.expectedOutput, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        )}
      </Card>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <Alert>
              <Info className="h-4 w-4" />
              <AlertDescription>
                Use the example problem as a starting point for creating new questions. 
                It demonstrates the proper structure and format.
              </AlertDescription>
            </Alert>
            
            <div className="flex space-x-2">
              <Button
                onClick={() => actions.setActiveTab('create')}
                data-testid="button-go-to-create"
              >
                Go to Create Question
              </Button>
              <Button
                variant="outline"
                onClick={() => actions.setActiveTab('datasource')}
                data-testid="button-go-to-datasource"
              >
                Go to Data Source
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}