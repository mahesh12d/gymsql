import { memo, useState } from 'react';
import { Code2, MessageSquare, CheckCircle, BookOpen, Heart, Reply, Send, ChevronUp, ChevronDown, Lock } from 'lucide-react';
import { useQuery, useMutation } from "@tanstack/react-query";
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Textarea } from '@/components/ui/textarea';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { useToast } from '@/hooks/use-toast';
import { useAuth } from '@/hooks/use-auth';
import { apiRequest, queryClient } from '@/lib/queryClient';
import ProblemDescriptionTab from '@/components/ProblemDescriptionTab';
import AnswersScreen from '@/components/AnswersScreen';
import ResultComparisonTable from './ResultComparisonTable';
import { RichTextEditor } from '@/components/RichTextEditor';
import { MarkdownRenderer } from '@/components/MarkdownRenderer';

interface Problem {
  id?: string;
  question?: {
    description?: string;
    tables?: any[];
    expectedOutput?: any[];
  };
  hints?: string[];
  tags?: string[];
  premium?: boolean | null;
}

interface Solution {
  id: string;
  problem_id: string;
  title: string;
  explanation: string;
  code: string;
  approach: string;
  time_complexity: string;
  space_complexity: string;
  tags: string[];
  created_at: string;
}

interface Submission {
  id: string;
  isCorrect: boolean;
  submittedAt: string;
  executionTime?: number;
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

interface ProblemTabsContentProps {
  problem?: Problem;
  userSubmissions?: Submission[];
  latestSubmissionResult?: SubmissionResult | null;
  className?: string;
  activeTab?: string;
  onTabChange?: (value: string) => void;
  problemId?: string;
}

interface User {
  id: string;
  username: string;
  profileImageUrl?: string;
}

interface Discussion {
  id: string;
  userId: string;
  problemId: string;
  content: string;
  codeSnippet?: string;
  likes: number;
  comments: number;
  createdAt: string;
  user: User;
  isLiked?: boolean;
}

interface Comment {
  id: string;
  postId: string;
  userId: string;
  parentId?: string;
  content: string;
  createdAt: string;
  user: User;
  replies?: Comment[];
}

const NestedComment = memo(function NestedComment({
  comment,
  discussionId,
  onReply,
  depth = 0
}: {
  comment: Comment;
  discussionId: string;
  onReply: (content: string, parentId?: string) => void;
  depth: number;
}) {
  const [showReplyBox, setShowReplyBox] = useState(false);
  const [replyContent, setReplyContent] = useState('');
  const { toast } = useToast();

  const replyMutation = useMutation({
    mutationFn: async (data: { content: string; parentId?: string }) => {
      return apiRequest('POST', `/api/community/posts/${discussionId}/comments`, { 
          content: data.content,
          parent_id: data.parentId 
        });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [`/api/community/posts/${discussionId}/comments`] });
      setReplyContent('');
      setShowReplyBox(false);
      toast({ title: "Reply posted successfully!" });
    },
    onError: () => {
      toast({ title: "Failed to post reply", variant: "destructive" });
    },
  });

  const handleSubmitReply = () => {
    if (!replyContent.trim()) return;
    replyMutation.mutate({ content: replyContent, parentId: comment.id });
  };

  const maxDepth = 3; // Limit nesting depth to avoid infinite nesting
  const isMaxDepth = depth >= maxDepth;

  return (
    <div className={`${depth > 0 ? 'ml-6 mt-3' : ''}`} data-testid={`comment-${comment.id}`}>
      <div className="flex items-start space-x-3">
        <Avatar className={`${depth > 0 ? 'w-6 h-6' : 'w-8 h-8'}`}>
          <AvatarImage src={comment.user.profileImageUrl} alt={comment.user.username} />
          <AvatarFallback>
            {comment.user.username?.charAt(0).toUpperCase() || 'U'}
          </AvatarFallback>
        </Avatar>
        
        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-1">
            <span className={`font-medium text-foreground ${depth > 0 ? 'text-sm' : 'text-sm'}`}>
              {comment.user.username}
            </span>
            <span className="text-xs text-muted-foreground">
              {new Date(comment.createdAt).toLocaleDateString()}
            </span>
          </div>
          
          <p className={`text-foreground whitespace-pre-wrap ${depth > 0 ? 'text-sm' : 'text-sm'}`}>
            {comment.content}
          </p>
          
          {/* Reply button */}
          {!isMaxDepth && (
            <div className="mt-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowReplyBox(!showReplyBox)}
                className="text-xs text-muted-foreground hover:text-blue-500 h-6 px-2"
                data-testid={`button-reply-${comment.id}`}
              >
                <Reply className="w-3 h-3 mr-1" />
                Reply
              </Button>
            </div>
          )}
          
          {/* Reply input box */}
          {showReplyBox && (
            <div className="mt-3 space-y-2">
              <Textarea
                placeholder={`Reply to ${comment.user.username}...`}
                value={replyContent}
                onChange={(e) => setReplyContent(e.target.value)}
                rows={2}
                className="resize-none text-sm"
                data-testid={`textarea-nested-reply-${comment.id}`}
              />
              <div className="flex justify-end space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setShowReplyBox(false);
                    setReplyContent('');
                  }}
                  className="h-8 text-xs"
                  data-testid={`button-cancel-reply-${comment.id}`}
                >
                  Cancel
                </Button>
                <Button
                  size="sm"
                  onClick={handleSubmitReply}
                  disabled={!replyContent.trim() || replyMutation.isPending}
                  className="h-8 text-xs"
                  data-testid={`button-submit-reply-${comment.id}`}
                >
                  {replyMutation.isPending ? "Posting..." : "Reply"}
                </Button>
              </div>
            </div>
          )}
          
          {/* Nested replies */}
          {comment.replies && comment.replies.length > 0 && (
            <div className="mt-3 space-y-3">
              {comment.replies.map((reply) => (
                <NestedComment
                  key={reply.id}
                  comment={reply}
                  discussionId={discussionId}
                  onReply={onReply}
                  depth={depth + 1}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
});

const OutputTable = ({ data, title }: { data: any[]; title: string }) => {
  if (!data || data.length === 0) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-700 mb-2">{title}</h3>
        <div className="text-gray-500 italic text-sm">No data to display</div>
      </div>
    );
  }

  const headers = Object.keys(data[0]);

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <div className="bg-gray-50 px-4 py-2 border-b border-gray-200">
        <h3 className="text-sm font-medium text-gray-700">{title}</h3>
      </div>
      <div className="overflow-auto max-h-80 min-h-32">
        <table className="w-full">
          <thead className="sticky top-0 bg-gray-50 z-10">
            <tr className="border-b border-gray-200">
              {headers.map((header, i) => (
                <th 
                  key={i} 
                  className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {data.map((row, i) => (
              <tr key={i} className="hover:bg-gray-50">
                {headers.map((header, j) => (
                  <td key={j} className="px-4 py-2 text-sm text-gray-900">
                    {String(row[header] ?? '')}
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

const DiscussionCard = memo(function DiscussionCard({ 
  discussion, 
  onLike, 
  onComment 
}: { 
  discussion: Discussion;
  onLike: (id: string, isLiked: boolean) => void;
  onComment: (id: string) => void;
}) {
  const [showComments, setShowComments] = useState(discussion.comments > 0);
  const [replyContent, setReplyContent] = useState('');
  const { toast } = useToast();

  const { data: comments = [] } = useQuery({
    queryKey: [`/api/community/posts/${discussion.id}/comments`, discussion.id],
    enabled: showComments,
  });

  const replyMutation = useMutation({
    mutationFn: async (content: string) => {
      return apiRequest('POST', `/api/community/posts/${discussion.id}/comments`, { content });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [`/api/community/posts/${discussion.id}/comments`] });
      queryClient.invalidateQueries({ queryKey: [`/api/problems/${discussion.problemId}/discussions`] });
      setReplyContent('');
      toast({ title: "Reply posted successfully!" });
    },
    onError: () => {
      toast({ title: "Failed to post reply", variant: "destructive" });
    },
  });

  const handleReply = () => {
    if (!replyContent.trim()) return;
    replyMutation.mutate(replyContent);
  };

  return (
    <Card className="mb-4" data-testid={`discussion-${discussion.id}`}>
      <CardContent className="p-6">
        <div className="flex items-start space-x-4">
          <Avatar className="w-10 h-10">
            <AvatarImage src={discussion.user.profileImageUrl} alt={discussion.user.username} />
            <AvatarFallback>
              {discussion.user.username?.charAt(0).toUpperCase() || 'U'}
            </AvatarFallback>
          </Avatar>
          
          <div className="flex-1">
            <div className="flex items-center space-x-2 mb-2">
              <span className="font-semibold text-foreground" data-testid={`text-username-${discussion.id}`}>
                {discussion.user.username}
              </span>
              <span className="text-sm text-muted-foreground">
                {new Date(discussion.createdAt).toLocaleDateString()}
              </span>
            </div>
            
            <div className="mb-3" data-testid={`text-content-${discussion.id}`}>
              <MarkdownRenderer content={discussion.content} />
            </div>
            
            {discussion.codeSnippet && (
              <div className="bg-muted/50 rounded-lg p-3 mb-3">
                <pre className="text-sm font-mono whitespace-pre-wrap" data-testid={`code-snippet-${discussion.id}`}>
                  {discussion.codeSnippet}
                </pre>
              </div>
            )}
            
            <div className="flex items-center space-x-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onLike(discussion.id, !!discussion.isLiked)}
                className="text-muted-foreground hover:text-red-500"
                data-testid={`button-like-${discussion.id}`}
              >
                <Heart className={`w-4 h-4 mr-1 ${discussion.isLiked ? 'fill-current text-red-500' : ''}`} />
                {discussion.likes}
              </Button>
              
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowComments(!showComments)}
                className="text-muted-foreground hover:text-blue-500"
                data-testid={`button-comments-${discussion.id}`}
              >
                <MessageSquare className="w-4 h-4 mr-1" />
                {showComments ? 'Hide' : 'View'} {discussion.comments} {discussion.comments === 1 ? 'comment' : 'comments'}
                {showComments ? <ChevronUp className="w-3 h-3 ml-1" /> : <ChevronDown className="w-3 h-3 ml-1" />}
              </Button>
            </div>
            
            {showComments && (
              <div className="mt-4 space-y-4">
                {/* Reply Input */}
                <div className="flex items-start space-x-3">
                  <Textarea
                    placeholder="Write a reply..."
                    value={replyContent}
                    onChange={(e) => setReplyContent(e.target.value)}
                    rows={2}
                    className="resize-none"
                    data-testid={`textarea-reply-${discussion.id}`}
                  />
                  <Button 
                    size="sm" 
                    onClick={handleReply}
                    disabled={!replyContent.trim() || replyMutation.isPending}
                    data-testid={`button-send-reply-${discussion.id}`}
                  >
                    <Send className="w-4 h-4" />
                  </Button>
                </div>
                
                {/* Comments */}
                <div className="space-y-3 pl-4 border-l-2 border-muted">
                  {comments.map((comment: Comment) => (
                    <NestedComment 
                      key={comment.id} 
                      comment={comment} 
                      discussionId={discussion.id}
                      onReply={() => {}} // Handled internally by NestedComment
                      depth={0}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
});


const ProblemTabsContent = memo(function ProblemTabsContent({
  problem,
  userSubmissions = [],
  latestSubmissionResult = null,
  className,
  activeTab = "problem",
  onTabChange,
  problemId,
}: ProblemTabsContentProps) {
  const [newDiscussionContent, setNewDiscussionContent] = useState('');
  const { toast } = useToast();
  const { user } = useAuth();

  // Removed premium access restrictions for discussions


  // Fetch discussions for this problem
  const { data: discussions = [], isLoading: discussionsLoading } = useQuery({
    queryKey: [`/api/problems/${problemId}/discussions`],
    enabled: !!problemId,
  });

  // Create discussion mutation
  const createDiscussionMutation = useMutation({
    mutationFn: async (content: string) => {
      return apiRequest('POST', `/api/problems/${problemId}/discussions`, { content });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [`/api/problems/${problemId}/discussions`] });
      setNewDiscussionContent('');
      toast({ title: "Discussion posted successfully!" });
    },
    onError: () => {
      toast({ title: "Failed to create discussion", variant: "destructive" });
    },
  });

  const handleCreateDiscussion = () => {
    if (!newDiscussionContent.trim()) return;
    createDiscussionMutation.mutate(newDiscussionContent);
  };

  // Like/unlike discussion mutation
  const likeMutation = useMutation({
    mutationFn: async ({ postId, isLiked }: { postId: string; isLiked: boolean }) => {
      const method = isLiked ? 'DELETE' : 'POST';
      return apiRequest(method, `/api/community/posts/${postId}/like`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [`/api/problems/${problemId}/discussions`] });
    },
    onError: () => {
      toast({ title: "Failed to update like", variant: "destructive" });
    },
  });

  const handleLike = (postId: string, isLiked: boolean) => {
    likeMutation.mutate({ postId, isLiked });
  };

  const handleComment = (postId: string) => {
    // This is handled by the DiscussionCard component
  };

  return (
    <div className={`h-full flex flex-col ${className || ''}`}>
      <Tabs value={activeTab} onValueChange={onTabChange} className="flex flex-col h-full">
        <TabsList className="w-full justify-start border-b bg-transparent p-0 h-auto rounded-none">
          <TabsTrigger
            value="problem"
            className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none"
            data-testid="tab-problem"
          >
            Problem
          </TabsTrigger>
          <TabsTrigger
            value="solution"
            className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none"
            data-testid="tab-solution"
          >
            Answers
          </TabsTrigger>
          <TabsTrigger
            value="discussion"
            className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none"
            data-testid="tab-discussion"
          >
            Discussion
          </TabsTrigger>
          <TabsTrigger
            value="submission"
            className="data-[state=active]:bg-transparent data-[state=active]:border-b-2 data-[state=active]:border-primary rounded-none"
            data-testid="tab-submission"
          >
            Submissions
          </TabsTrigger>
        </TabsList>

        <TabsContent
          value="problem"
          className="flex-1 overflow-auto p-6 pt-0 mt-0"
          data-testid="content-problem"
        >
          <ProblemDescriptionTab problem={problem} problemId={problemId} />
        </TabsContent>

        <TabsContent
          value="solution"
          className="flex-1 overflow-auto p-6 pt-0 mt-0"
          data-testid="content-solution"
        >
          {problemId && (
            <AnswersScreen 
              problemId={problemId}
            />
          )}
        </TabsContent>

        <TabsContent
          value="discussion"
          className="flex-1 overflow-auto p-6 pt-0 mt-0"
          data-testid="content-discussion"
        >
          <div className="space-y-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-foreground">
                Discussion
              </h3>
            </div>

            {/* Create Discussion - Inline Editor */}
            {user && (
              <Card className="border-2 border-primary/20 hover:border-primary/40 transition-all duration-300 shadow-lg hover:shadow-xl bg-gradient-to-br from-background via-background to-primary/5">
                <CardContent className="p-6">
                  <div className="w-full">
                    <RichTextEditor
                      value={newDiscussionContent}
                      onChange={setNewDiscussionContent}
                      placeholder="Share your thoughts, ask questions, or discuss solutions for this problem..."
                      minHeight="120px"
                      testId="textarea-new-discussion"
                    />

                    <div className="flex justify-end mt-3">
                      <Button
                        onClick={handleCreateDiscussion}
                        disabled={!newDiscussionContent.trim() || createDiscussionMutation.isPending}
                        className="bg-gradient-to-r from-primary to-primary/80 text-primary-foreground hover:from-primary/90 hover:to-primary/70 shadow-md hover:shadow-lg transform hover:scale-105 transition-all duration-200"
                        data-testid="button-post-discussion"
                      >
                        {createDiscussionMutation.isPending ? "Posting..." : "Post Discussion"}
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Premium lock removed - discussions now always available */}
            {false ? (
              <div className="flex flex-col items-center justify-center py-12 space-y-4">
                <div className="flex items-center justify-center w-16 h-16 bg-amber-100 dark:bg-amber-900/20 rounded-full">
                  <Lock className="w-8 h-8 text-amber-600 dark:text-amber-500" />
                </div>
                <div className="text-center space-y-2">
                  <h4 className="text-lg font-semibold text-foreground">
                    Premium Content Locked
                  </h4>
                  <p className="text-muted-foreground max-w-md">
                    🔒 Premium subscription required to view and participate in discussions for this problem!
                  </p>
                  <div className="pt-4">
                    <Button variant="default" className="bg-amber-600 hover:bg-amber-700">
                      <Lock className="w-4 h-4 mr-2" />
                      Upgrade to Premium
                    </Button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {discussionsLoading && (
                  <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
                    <p className="text-muted-foreground">Loading discussions...</p>
                  </div>
                )}

                {!discussionsLoading && discussions.length === 0 && (
                  <div className="text-center py-8">
                    <MessageSquare className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                    <h4 className="text-base font-semibold text-foreground mb-2">
                      No discussions yet
                    </h4>
                    <p className="text-muted-foreground mb-4">
                      Be the first to start a discussion about this problem!
                    </p>
                  </div>
                )}

                {!discussionsLoading && discussions.length > 0 && (
                  <div className="space-y-4" data-testid="discussions-list">
                    {discussions.map((discussion: Discussion) => (
                      <DiscussionCard
                        key={discussion.id}
                        discussion={discussion}
                        onLike={handleLike}
                        onComment={handleComment}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent
          value="submission"
          className="flex-1 overflow-auto p-6 pt-0 mt-0"
          data-testid="content-submission"
        >
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-foreground">
                My Submissions
              </h3>
              <div className="text-sm text-muted-foreground">
                {userSubmissions.length} submissions
              </div>
            </div>

            {/* Latest Submission Result */}
            {latestSubmissionResult && (
              <div className="space-y-4">
                {/* Result Status Banner */}
                {latestSubmissionResult.is_correct ? (
                  <div className="bg-green-50 border border-green-200 rounded-lg p-3" data-testid="banner-success">
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                      <span className="text-green-800 font-medium text-sm">Success!</span>
                    </div>
                    <p className="text-green-700 text-sm mt-1">
                      Your solution is correct! Well done!
                    </p>
                  </div>
                ) : (
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

                {/* Output and Expected Tables */}
                {latestSubmissionResult.test_results && latestSubmissionResult.test_results.length > 0 && (
                  <div className="space-y-4">
                    {(() => {
                      const mainTestResult = latestSubmissionResult.test_results.find(test => !test.is_hidden) || latestSubmissionResult.test_results[0];
                      return mainTestResult ? (
                        <>
                          <OutputTable 
                            data={mainTestResult.user_output} 
                            title="Your Output" 
                          />
                          <OutputTable 
                            data={mainTestResult.expected_output} 
                            title="Expected Output" 
                          />
                          
                          {/* Detailed Result Comparison */}
                          {mainTestResult.validation_details && (
                            <ResultComparisonTable 
                              validationDetails={mainTestResult.validation_details}
                              isCorrect={latestSubmissionResult.is_correct}
                            />
                          )}
                        </>
                      ) : null;
                    })()}
                  </div>
                )}
              </div>
            )}

            {/* Show message when no submissions */}
            {!latestSubmissionResult && userSubmissions.length === 0 && (
              <div className="text-center py-8">
                <CheckCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <h4 className="text-base font-semibold text-foreground mb-2">
                  No submissions yet
                </h4>
                <p className="text-muted-foreground mb-4">
                  Submit your first solution to see it here!
                </p>
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
});

export default ProblemTabsContent;