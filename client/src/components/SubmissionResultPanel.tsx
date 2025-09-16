import SubmissionHistory from './SubmissionHistory';

interface SubmissionResult {
  success: boolean;
  is_correct: boolean;
  score: number;
  feedback: string[];
  test_results: TestResult[];
  submission_id: string;
  execution_stats: {
    avg_time_ms: number;
    max_time_ms: number;
    memory_used_mb: number;
  };
}

interface TestResult {
  test_case_id: string;
  test_case_name: string;
  is_hidden: boolean;
  is_correct: boolean;
  score: number;
  feedback: string[];
  execution_time_ms: number;
  execution_status: string;
  validation_details: any;
  user_output: any[];
  expected_output: any[];
  output_matches: boolean;
}

interface SubmissionResultPanelProps {
  result: SubmissionResult | null;
  isLoading: boolean;
  problemId: string;
}


export default function SubmissionResultPanel({ result, isLoading, problemId }: SubmissionResultPanelProps) {
  if (isLoading) {
    return (
      <div className="h-full bg-gray-50 flex items-center justify-center">
        <div className="text-gray-600">Submitting solution...</div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="h-full bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Submit your solution to see results...</div>
      </div>
    );
  }

  // Get the first non-hidden test result for main comparison display
  const mainTestResult = result.test_results?.find(test => !test.is_hidden) || result.test_results?.[0];
  const hasOutputMismatch = !result.is_correct && mainTestResult;

  return (
    <div className="h-full bg-gray-50 flex flex-col overflow-auto">
      <div className="p-4 space-y-4 flex-1 min-h-0">
        {/* Mismatch Banner */}
        {hasOutputMismatch && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3" data-testid="banner-mismatch">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-red-500 rounded-full"></div>
              <span className="text-red-800 font-medium text-sm">Mismatched</span>
            </div>
            <p className="text-red-700 text-sm mt-1">
              Your query's output doesn't match with the solution's output!
            </p>
          </div>
        )}

        {/* Success Banner */}
        {result.is_correct && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-3" data-testid="banner-success">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="text-green-800 font-medium text-sm">Success!</span>
            </div>
            <p className="text-green-700 text-sm mt-1">
              Your solution is correct! Well done!
            </p>
          </div>
        )}

        {/* Submission Stats */}
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-lg font-semibold text-gray-900">
                {(result.score ?? 0).toFixed(1)}%
              </div>
              <div className="text-xs text-gray-500">Score</div>
            </div>
            <div>
              <div className="text-lg font-semibold text-gray-900">
                {result.execution_stats?.avg_time_ms ?? 0}ms
              </div>
              <div className="text-xs text-gray-500">Runtime</div>
            </div>
            <div>
              <div className="text-lg font-semibold text-gray-900">
                {(result.execution_stats?.memory_used_mb ?? 0).toFixed(1)}MB
              </div>
              <div className="text-xs text-gray-500">Memory</div>
            </div>
          </div>
        </div>

        {/* Feedback Messages */}
        {result.feedback && result.feedback.length > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <h4 className="text-sm font-medium text-blue-800 mb-2">Feedback</h4>
            <ul className="text-sm text-blue-700 space-y-1">
              {result.feedback.map((message, index) => (
                <li key={index}>• {message}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Submission History */}
        <SubmissionHistory problemId={problemId} />
      </div>
    </div>
  );
}