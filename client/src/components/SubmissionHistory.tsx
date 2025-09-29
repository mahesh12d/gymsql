import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';
import { CheckCircle, XCircle } from 'lucide-react';

interface Submission {
  id: string;
  query: string;
  isCorrect: boolean;
  executionTime: number;
  submittedAt: string;
  score?: number;
}

interface SubmissionHistoryProps {
  problemId: string;
}

export default function SubmissionHistory({ problemId }: SubmissionHistoryProps) {
  const { data: submissions = [], isLoading, error } = useQuery({
    queryKey: [`/api/problems/${problemId}/submissions`],
    enabled: !!problemId,
  });

  if (isLoading) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="text-gray-600 text-sm">Loading submission history...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="text-red-600 text-sm">Failed to load submission history</div>
      </div>
    );
  }

  if (submissions.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="text-gray-500 text-sm italic">No submissions yet</div>
      </div>
    );
  }

  const formatTime = (dateString: string) => {
    try {
      return format(new Date(dateString), 'MM/dd/yyyy HH:mm');
    } catch {
      return dateString;
    }
  };

  const getStatusBadge = (isCorrect: boolean, score?: number) => {
    if (isCorrect) {
      return (
        <div className="flex items-center space-x-1">
          <CheckCircle className="w-4 h-4 text-green-600" />
          <span className="text-green-600 font-medium text-sm">Success</span>
        </div>
      );
    } else {
      return (
        <div className="flex items-center space-x-1">
          <XCircle className="w-4 h-4 text-red-600" />
          <span className="text-red-600 font-medium text-sm">Error</span>
        </div>
      );
    }
  };

  const truncateQuery = (query: string, maxLength: number = 50) => {
    if (query.length <= maxLength) return query;
    return query.substring(0, maxLength) + '...';
  };

  const copyToClipboard = async (query: string) => {
    try {
      await navigator.clipboard.writeText(query);
      // Could add a toast notification here
    } catch (err) {
      console.error('Failed to copy query:', err);
    }
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <div className="bg-gray-50 px-4 py-2 border-b border-gray-200">
        <h3 className="text-sm font-medium text-gray-700">Submission History</h3>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                TIME
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                STATUS
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                YOUR SUBMISSION
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                RUNTIME
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {submissions.map((submission) => (
              <tr key={submission.id} className="hover:bg-gray-50" data-testid={`submission-row-${submission.id}`}>
                <td className="px-4 py-2 text-sm text-gray-900">
                  {formatTime(submission.submittedAt)}
                </td>
                <td className="px-4 py-2 text-sm">
                  {getStatusBadge(submission.isCorrect, submission.score)}
                </td>
                <td className="px-4 py-2 text-sm">
                  <div className="flex items-center space-x-2">
                    <span 
                      className="text-gray-900 font-mono text-xs bg-gray-100 px-2 py-1 rounded cursor-pointer hover:bg-gray-200"
                      onClick={() => copyToClipboard(submission.query)}
                      title="Click to copy full query"
                      data-testid={`query-copy-${submission.id}`}
                    >
                      {truncateQuery(submission.query)}
                    </span>
                    <button
                      onClick={() => copyToClipboard(submission.query)}
                      className="text-blue-600 hover:text-blue-800 text-xs"
                      title="Copy to clipboard"
                      data-testid={`button-copy-${submission.id}`}
                    >
                      Copy To Clipboard
                    </button>
                  </div>
                </td>
                <td className="px-4 py-2 text-sm text-gray-900">
                  {submission.executionTime ? `${submission.executionTime}ms` : 'PostgreSQL 14'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}