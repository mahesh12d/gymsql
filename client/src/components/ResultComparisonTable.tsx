import { useMemo } from 'react';

interface RowComparison {
  row_index: number;
  matches: boolean;
  actual_row: Record<string, any> | null;
  expected_row: Record<string, any>;
  differences?: string;
}

interface ValidationDetails {
  row_comparisons?: RowComparison[];
  matching_row_count?: number;
  total_row_count?: number;
  comparison_differences?: string[];
}

interface ResultComparisonTableProps {
  validationDetails: ValidationDetails;
  isCorrect: boolean;
}

export default function ResultComparisonTable({ validationDetails, isCorrect }: ResultComparisonTableProps) {
  const { headers, comparisons } = useMemo(() => {
    const rowComparisons = validationDetails.row_comparisons || [];
    
    if (rowComparisons.length === 0) {
      return { headers: [], comparisons: [] };
    }
    
    // Get headers from the first expected row
    const firstExpected = rowComparisons[0]?.expected_row;
    const headers = firstExpected ? Object.keys(firstExpected) : [];
    
    return { headers, comparisons: rowComparisons };
  }, [validationDetails]);

  if (!validationDetails.row_comparisons || validationDetails.row_comparisons.length === 0) {
    return null;
  }

  const matchingCount = validationDetails.matching_row_count || 0;
  const totalCount = validationDetails.total_row_count || 0;

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4" data-testid="comparison-table">
      <div className="mb-4">
        <h4 className="text-sm font-medium text-gray-900 mb-2">Detailed Result Comparison</h4>
        <div className="text-xs text-gray-600 mb-2">
          {matchingCount} of {totalCount} rows match
        </div>
        
        {/* Legend */}
        <div className="flex items-center space-x-4 text-xs mb-3">
          <div className="flex items-center space-x-1">
            <div className="w-3 h-3 bg-green-100 border border-green-200 rounded"></div>
            <span className="text-gray-600">Matching rows</span>
          </div>
          <div className="flex items-center space-x-1">
            <div className="w-3 h-3 bg-white border border-gray-200 rounded"></div>
            <span className="text-gray-600">Non-matching rows</span>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto max-h-96">
        <table className="w-full border-collapse">
          <thead className="sticky top-0 bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b border-gray-200">
                Row
              </th>
              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b border-gray-200">
                Status
              </th>
              {headers.map((header, i) => (
                <th 
                  key={i} 
                  className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b border-gray-200"
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {comparisons.map((comparison) => {
              const rowClass = comparison.matches 
                ? 'bg-green-50 hover:bg-green-100' 
                : 'bg-white hover:bg-gray-50';
                
              return (
                <tr 
                  key={comparison.row_index} 
                  className={rowClass}
                  data-testid={`row-comparison-${comparison.row_index}`}
                >
                  <td className="px-3 py-2 text-sm text-gray-900 font-medium">
                    {comparison.row_index + 1}
                  </td>
                  <td className="px-3 py-2 text-sm">
                    {comparison.matches ? (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        ✓ Match
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                        ✗ Different
                      </span>
                    )}
                  </td>
                  {headers.map((header, i) => {
                    const expectedValue = comparison.expected_row[header];
                    const actualValue = comparison.actual_row?.[header];
                    const cellMatches = comparison.matches || (expectedValue === actualValue);
                    
                    return (
                      <td 
                        key={i} 
                        className={`px-3 py-2 text-sm ${
                          cellMatches ? 'text-gray-900' : 'text-red-700 font-medium'
                        }`}
                      >
                        <div className="flex flex-col space-y-1">
                          {/* Show expected value */}
                          <div className="text-xs text-gray-500">
                            Expected: {String(expectedValue ?? '')}
                          </div>
                          {/* Show actual value if different or if row doesn't match */}
                          {(!comparison.matches || actualValue !== expectedValue) && (
                            <div className={`text-xs ${cellMatches ? 'text-gray-700' : 'text-red-600 font-medium'}`}>
                              Got: {actualValue !== undefined ? String(actualValue ?? '') : 'N/A'}
                            </div>
                          )}
                        </div>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Show comparison differences if any */}
      {validationDetails.comparison_differences && validationDetails.comparison_differences.length > 0 && (
        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
          <h5 className="text-sm font-medium text-yellow-800 mb-1">Additional Issues:</h5>
          <ul className="text-sm text-yellow-700 space-y-1">
            {validationDetails.comparison_differences.map((diff, index) => (
              <li key={index}>• {diff}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}