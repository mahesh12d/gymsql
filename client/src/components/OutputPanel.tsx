import React, { useMemo } from 'react';

interface OutputPanelProps {
  result: {
    success: boolean;
    results?: any[];
    execution_time_ms?: number;
    rows_affected?: number;
    console_info?: string;
    error?: string;
    feedback?: string[];
    test_results?: any[];
  } | null;
  isLoading: boolean;
}

const OptimizedTable = ({ data }: { data: any[] }) => {
  const { headers, rows } = useMemo(() => {
    if (!data || data.length === 0) return { headers: [], rows: [] };
    
    const headers = Object.keys(data[0]);
    const rows = data.map(row => headers.map(header => row[header]));
    
    return { headers, rows };
  }, [data]);

  if (headers.length === 0) {
    return <div className="text-gray-500 italic p-4">No data to display</div>;
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden max-h-full">
      <div className="overflow-auto max-h-96">
        <table className="w-full">
          <thead className="sticky top-0 bg-gray-50">
            <tr className="border-b border-gray-200">
              {headers.map((header, i) => (
                <th 
                  key={i} 
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {rows.map((row, i) => (
              <tr key={i} className="hover:bg-gray-50">
                {row.map((cell, j) => (
                  <td key={j} className="px-4 py-3 text-sm text-gray-900">
                    {String(cell ?? '')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default function OutputPanel({ result, isLoading }: OutputPanelProps) {
  if (isLoading) {
    return (
      <div className="h-full bg-gray-50 flex items-center justify-center">
        <div className="text-gray-600">Executing query...</div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="h-full bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Ready to execute queries...</div>
      </div>
    );
  }

  const executionTimeSeconds = result.execution_time_ms ? (result.execution_time_ms / 1000).toFixed(5) : '0.00000';

  // Add this handler for the "View in new tab" functionality
  const handleViewInNewTab = () => {
    if (!result?.results || result.results.length === 0) return;
    
    const htmlContent = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>Query Results</title>
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 20px; }
          table { width: 100%; border-collapse: collapse; border: 1px solid #e5e5e5; }
          th { background: #f9f9f9; padding: 12px; text-align: left; border-bottom: 1px solid #e5e5e5; font-weight: 600; }
          td { padding: 12px; border-bottom: 1px solid #f0f0f0; }
          tr:hover { background: #f9f9f9; }
        </style>
      </head>
      <body>
        <h2>Query Results</h2>
        <p>Execution time: ${executionTimeSeconds} seconds | ${result.results.length} rows</p>
        <table>
          <thead>
            <tr>
              ${Object.keys(result.results[0]).map(header => `<th>${header}</th>`).join('')}
            </tr>
          </thead>
          <tbody>
            ${result.results.map(row => 
              `<tr>${Object.values(row).map(cell => `<td>${String(cell ?? '')}</td>`).join('')}</tr>`
            ).join('')}
          </tbody>
        </table>
      </body>
      </html>
    `;
    
    const blob = new Blob([htmlContent], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
    
    // Clean up the URL object after a delay
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  return (
    <div className="h-full bg-gray-50 flex flex-col">
      {/* Header with execution info */}
      <div className="flex-shrink-0 px-4 py-3 bg-white border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <span className="text-sm text-gray-700">
            Execution time: {executionTimeSeconds} seconds
          </span>
          {result.rows_affected !== undefined && (
            <span className="text-sm text-gray-500">
              {result.rows_affected} rows
            </span>
          )}
        </div>
        <button 
          onClick={handleViewInNewTab}
          className="px-3 py-1 text-sm text-blue-600 border border-blue-300 rounded hover:bg-blue-50"
          disabled={!result?.results || result.results.length === 0}
          data-testid="button-view-new-tab"
        >
          View the output in a new tab
        </button>
      </div>

      {/* Results area */}
      <div className="flex-1 p-4 overflow-auto">
        {result.success && result.results && result.results.length > 0 ? (
          <OptimizedTable data={result.results} />
        ) : !result.success ? (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="text-red-800 font-medium">Query Error</div>
            <div className="text-red-700 mt-1 whitespace-pre-wrap">
              {result.error || 'Query failed'}
            </div>
          </div>
        ) : (
          <div className="text-center text-gray-500 py-8">
            Query executed successfully - no rows returned
          </div>
        )}
      </div>

      {/* Test results section */}
      {result.test_results && result.test_results.length > 0 && (
        <div className="flex-shrink-0 border-t border-gray-200 p-4 bg-white">
          <h3 className="text-gray-900 font-medium mb-2">Test Results:</h3>
          <div className="space-y-1">
            {result.test_results.map((test, index) => (
              <div key={index} className={`text-sm flex items-center space-x-2`}>
                <span className={test.passed ? 'text-green-600' : 'text-red-600'}>
                  {test.passed ? '✓' : '✗'}
                </span>
                <span className="text-gray-700">{test.name}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}