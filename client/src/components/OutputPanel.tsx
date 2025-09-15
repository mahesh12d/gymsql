import { memo } from "react";
import { TrendingUp } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import React from "react";

interface QueryResult {
  error?: boolean;
  message?: string;
  isCorrect?: boolean;
  executionTime?: number;
  query_result?: {
    status: string;
    execution_time_ms: number;
    result: Array<Record<string, any>>;
    rows_affected: number;
    columns: string[];
  };
}

interface OutputPanelProps {
  result: QueryResult | null;
  className?: string;
}

interface OutputPanelProps {
  result: {
    success: boolean;
    console_output?: string;
    results?: any[];
    execution_time_ms?: number;
    error?: string;
    feedback?: string[];
    test_results?: any[];
  };
  isLoading: boolean;
}

export default function OutputPanel({ result, isLoading }: OutputPanelProps) {
  if (isLoading) {
    return (
      <div className="p-4 bg-gray-900 text-gray-400 font-mono text-sm">
        Executing query...
      </div>
    );
  }

  if (!result) {
    return (
      <div className="p-4 bg-gray-900 text-gray-400 font-mono text-sm">
        Ready to execute queries...
      </div>
    );
  }

  return (
    <div className="bg-gray-900 text-gray-100 font-mono text-sm overflow-auto">
      <pre
        className={`p-4 whitespace-pre-wrap ${
          result.success ? "text-green-400" : "text-red-400"
        }`}
      >
        {result.console_output ||
          (result.error ? `ERROR: ${result.error}` : "No output")}
      </pre>

      {/* Optional: Show test results separately if they exist */}
      {result.test_results && result.test_results.length > 0 && (
        <div className="border-t border-gray-700 p-4">
          <h3 className="text-blue-400 mb-2">Test Results:</h3>
          {result.test_results.map((test, index) => (
            <div
              key={index}
              className={`mb-1 ${test.passed ? "text-green-400" : "text-red-400"}`}
            >
              {test.passed ? "✓" : "✗"} {test.name}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
