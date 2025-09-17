import { useState, memo } from 'react';
import { 
  BookOpen, 
  Heart, 
  MessageSquare, 
  Trophy, 
  Users, 
  Code, 
  CheckCircle,
  Star,
  ThumbsUp,
  Send,
  Plus,
  Filter
} from 'lucide-react';
import { useQuery, useMutation } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuTrigger 
} from '@/components/ui/dropdown-menu';
import { useToast } from '@/hooks/use-toast';
import { apiRequest, queryClient } from '@/lib/queryClient';

interface User {
  id: string;
  username: string;
  profileImageUrl?: string;
}

interface OfficialSolution {
  id: string;
  problemId: string;
  createdBy: string;
  title: string;
  content: string;
  sqlCode: string;
  isOfficial: boolean;
  createdAt: string;
  updatedAt: string;
  creator: User;
}

interface CommunityAnswer {
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

interface AnswersScreenProps {
  problemId: string;
  hasCorrectSubmission?: boolean;
  className?: string;
}

const OfficialSolutionCard = memo(function OfficialSolutionCard({
  solution,
  hasAccess
}: {
  solution: OfficialSolution;
  hasAccess: boolean;
}) {
  return (
    <Card className="mb-6 border-l-4 border-l-green-500" data-testid={`official-solution-${solution.id}`}>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-green-100 dark:bg-green-900/20 rounded-lg">
              <Trophy className="w-5 h-5 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <CardTitle className="text-lg" data-testid={`text-solution-title-${solution.id}`}>
                {solution.title}
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                Official Solution by {solution.creator.username}
              </p>
            </div>
          </div>
          <Badge variant="secondary" className="bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-300">
            <CheckCircle className="w-3 h-3 mr-1" />
            Verified
          </Badge>
        </div>
      </CardHeader>
      
      <CardContent>
        {hasAccess ? (
          <div className="space-y-4">
            <div>
              <h4 className="font-medium text-foreground mb-2">Explanation:</h4>
              <div className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed" data-testid={`text-solution-explanation-${solution.id}`}>
                {solution.content}
              </div>
            </div>
            
            <div>
              <h4 className="font-medium text-foreground mb-2">SQL Solution:</h4>
              <div className="bg-muted/50 rounded-lg p-4">
                <pre className="text-sm font-mono whitespace-pre-wrap text-foreground" data-testid={`code-solution-${solution.id}`}>
                  {solution.sqlCode}
                </pre>
              </div>
            </div>
          </div>
        ) : (
          <Alert className="border-orange-200 bg-orange-50 dark:bg-orange-950/30">
            <AlertDescription className="text-orange-800 dark:text-orange-200">
              🔒 Solve this problem first to unlock the official solution!
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
});

const CommunityAnswerCard = memo(function CommunityAnswerCard({
  answer,
  onLike,
  onComment,
  hasAccess
}: {
  answer: CommunityAnswer;
  onLike: (id: string, isLiked: boolean) => void;
  onComment: (id: string) => void;
  hasAccess: boolean;
}) {
  const [showComments, setShowComments] = useState(false);
  const [replyContent, setReplyContent] = useState('');
  const { toast } = useToast();

  const { data: comments = [] } = useQuery({
    queryKey: [`/api/community/posts/${answer.id}/comments`, answer.id],
    enabled: showComments,
  });

  const replyMutation = useMutation({
    mutationFn: async (content: string) => {
      return apiRequest(`/api/community/posts/${answer.id}/comments`, {
        method: 'POST',
        body: JSON.stringify({ content }),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [`/api/community/posts/${answer.id}/comments`] });
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
    <Card className="mb-4 border-l-4 border-l-blue-500" data-testid={`community-answer-${answer.id}`}>
      <CardContent className="p-6">
        <div className="flex items-start space-x-4">
          <Avatar className="w-10 h-10">
            <AvatarImage src={answer.user.profileImageUrl} alt={answer.user.username} />
            <AvatarFallback>
              {answer.user.username?.charAt(0).toUpperCase() || 'U'}
            </AvatarFallback>
          </Avatar>
          
          <div className="flex-1">
            <div className="flex items-center space-x-2 mb-2">
              <span className="font-semibold text-foreground" data-testid={`text-username-${answer.id}`}>
                {answer.user.username}
              </span>
              <Badge variant="outline" className="text-xs">
                <Users className="w-3 h-3 mr-1" />
                Community
              </Badge>
              <span className="text-sm text-muted-foreground">
                {new Date(answer.createdAt).toLocaleDateString()}
              </span>
            </div>
            
            <div className="mb-3">
              <p className="text-foreground whitespace-pre-wrap" data-testid={`text-content-${answer.id}`}>
                {answer.content}
              </p>
            </div>
            
            {answer.codeSnippet && (
              <div className="mb-3">
                <h5 className="text-sm font-medium text-foreground mb-2">Code Solution:</h5>
                {hasAccess ? (
                  <div className="bg-muted/50 rounded-lg p-3">
                    <pre className="text-sm font-mono whitespace-pre-wrap" data-testid={`code-snippet-${answer.id}`}>
                      {answer.codeSnippet}
                    </pre>
                  </div>
                ) : (
                  <div className="bg-muted/50 rounded-lg p-3">
                    <div className="text-muted-foreground italic text-sm">
                      🔒 Solve the problem first to view community solutions
                    </div>
                  </div>
                )}
              </div>
            )}
            
            <div className="flex items-center space-x-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onLike(answer.id, !!answer.isLiked)}
                className="text-muted-foreground hover:text-red-500"
                data-testid={`button-like-${answer.id}`}
              >
                <Heart className={`w-4 h-4 mr-1 ${answer.isLiked ? 'fill-current text-red-500' : ''}`} />
                {answer.likes}
              </Button>
              
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowComments(!showComments)}
                className="text-muted-foreground hover:text-blue-500"
                data-testid={`button-comments-${answer.id}`}
              >
                <MessageSquare className="w-4 h-4 mr-1" />
                {answer.comments}
              </Button>
            </div>
            
            {showComments && (
              <div className="mt-4 space-y-4">
                <div className="flex items-start space-x-3">
                  <Textarea
                    placeholder="Share your thoughts on this solution..."
                    value={replyContent}
                    onChange={(e) => setReplyContent(e.target.value)}
                    rows={2}
                    className="resize-none"
                    data-testid={`textarea-reply-${answer.id}`}
                  />
                  <Button 
                    size="sm" 
                    onClick={handleReply}
                    disabled={!replyContent.trim() || replyMutation.isPending}
                    data-testid={`button-send-reply-${answer.id}`}
                  >
                    <Send className="w-4 h-4" />
                  </Button>
                </div>
                
                <div className="space-y-3 pl-4 border-l-2 border-muted">
                  {comments.map((comment: Comment) => (
                    <div key={comment.id} className="flex items-start space-x-3" data-testid={`comment-${comment.id}`}>
                      <Avatar className="w-8 h-8">
                        <AvatarImage src={comment.user.profileImageUrl} alt={comment.user.username} />
                        <AvatarFallback>
                          {comment.user.username?.charAt(0).toUpperCase() || 'U'}
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-1">
                          <span className="font-medium text-sm text-foreground">
                            {comment.user.username}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {new Date(comment.createdAt).toLocaleDateString()}
                          </span>
                        </div>
                        <p className="text-sm text-foreground whitespace-pre-wrap">
                          {comment.content}
                        </p>
                      </div>
                    </div>
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

const SubmitAnswerDialog = memo(function SubmitAnswerDialog({
  problemId,
  onClose
}: {
  problemId: string;
  onClose: () => void;
}) {
  const [content, setContent] = useState('');
  const [codeSnippet, setCodeSnippet] = useState('');
  const { toast } = useToast();

  const submitMutation = useMutation({
    mutationFn: async (data: { content: string; codeSnippet?: string }) => {
      return apiRequest(`/api/problems/${problemId}/discussions`, {
        method: 'POST',
        body: JSON.stringify({
          content: data.content,
          codeSnippet: data.codeSnippet || undefined,
        }),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [`/api/problems/${problemId}/discussions`] });
      setContent('');
      setCodeSnippet('');
      onClose();
      toast({ title: "Your solution has been shared successfully!" });
    },
    onError: () => {
      toast({ title: "Failed to submit solution", variant: "destructive" });
    },
  });

  const handleSubmit = () => {
    if (!content.trim()) return;
    submitMutation.mutate({ content, codeSnippet });
  };

  return (
    <DialogContent className="max-w-3xl" data-testid="dialog-submit-answer">
      <DialogHeader>
        <DialogTitle>Share Your Solution</DialogTitle>
      </DialogHeader>
      <div className="space-y-4">
        <div>
          <label className="text-sm font-medium text-foreground mb-2 block">
            Explain your approach and solution
          </label>
          <Textarea
            placeholder="Describe your solution approach, any insights, or alternative methods you used..."
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={4}
            className="resize-none"
            data-testid="textarea-answer-content"
          />
        </div>
        <div>
          <label className="text-sm font-medium text-foreground mb-2 block">
            SQL Code (Required)
          </label>
          <Textarea
            placeholder="-- Paste your working SQL solution here
SELECT column1, column2
FROM table_name
WHERE condition
ORDER BY column1;"
            value={codeSnippet}
            onChange={(e) => setCodeSnippet(e.target.value)}
            rows={6}
            className="font-mono text-sm resize-none"
            data-testid="textarea-answer-code"
          />
        </div>
        <Alert>
          <AlertDescription>
            💡 Share your working solution to help other learners understand different approaches to this problem.
          </AlertDescription>
        </Alert>
        <div className="flex justify-end space-x-2">
          <Button variant="outline" onClick={onClose} data-testid="button-cancel-answer">
            Cancel
          </Button>
          <Button 
            onClick={handleSubmit}
            disabled={!content.trim() || !codeSnippet.trim() || submitMutation.isPending}
            data-testid="button-submit-answer"
          >
            {submitMutation.isPending ? "Sharing..." : "Share Solution"}
          </Button>
        </div>
      </div>
    </DialogContent>
  );
});

const AnswersScreen = memo(function AnswersScreen({ 
  problemId, 
  hasCorrectSubmission = false, 
  className 
}: AnswersScreenProps) {
  const [showSubmitDialog, setShowSubmitDialog] = useState(false);
  const [sortBy, setSortBy] = useState('newest');
  const [filterType, setFilterType] = useState('all');
  const { toast } = useToast();

  // Fetch official solutions
  const { data: officialSolutions = [], isLoading: officialLoading } = useQuery({
    queryKey: [`/api/problems/${problemId}/solutions`, problemId],
    enabled: !!problemId,
  });

  // Fetch community answers (discussions with code snippets)
  const { data: communityAnswers = [], isLoading: communityLoading } = useQuery({
    queryKey: [`/api/problems/${problemId}/discussions`, problemId],
    enabled: !!problemId,
  });

  // Like/unlike mutation
  const likeMutation = useMutation({
    mutationFn: async ({ postId, isLiked }: { postId: string; isLiked: boolean }) => {
      const method = isLiked ? 'DELETE' : 'POST';
      return apiRequest(`/api/community/posts/${postId}/like`, { method });
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
    // Handled by the card component
  };

  // Filter and sort community answers
  const processedCommunityAnswers = communityAnswers
    .filter((answer: CommunityAnswer) => {
      if (filterType === 'all') return true;
      if (filterType === 'withCode') return answer.codeSnippet;
      if (filterType === 'popular') return answer.likes > 0;
      return true;
    })
    .sort((a: CommunityAnswer, b: CommunityAnswer) => {
      switch (sortBy) {
        case 'popular':
          return b.likes - a.likes;
        case 'oldest':
          return new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
        default: // newest
          return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
      }
    });

  return (
    <div className={`space-y-6 ${className || ''}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-foreground flex items-center space-x-2">
            <BookOpen className="w-6 h-6" />
            <span>Solutions & Answers</span>
          </h2>
          <p className="text-muted-foreground mt-1">
            Official solutions and community approaches to solve this problem
          </p>
        </div>
        <Dialog open={showSubmitDialog} onOpenChange={setShowSubmitDialog}>
          <DialogTrigger asChild>
            <Button className="bg-primary hover:bg-primary/90" data-testid="button-share-solution">
              <Plus className="w-4 h-4 mr-2" />
              Share My Solution
            </Button>
          </DialogTrigger>
          <SubmitAnswerDialog problemId={problemId} onClose={() => setShowSubmitDialog(false)} />
        </Dialog>
      </div>

      <Tabs defaultValue="all" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="all" data-testid="tab-all-answers">
            All Answers ({officialSolutions.length + processedCommunityAnswers.length})
          </TabsTrigger>
          <TabsTrigger value="official" data-testid="tab-official-solutions">
            Official ({officialSolutions.length})
          </TabsTrigger>
          <TabsTrigger value="community" data-testid="tab-community-answers">
            Community ({processedCommunityAnswers.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="all" className="mt-6">
          {(officialLoading || communityLoading) && (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
              <p className="text-muted-foreground">Loading solutions...</p>
            </div>
          )}

          {!officialLoading && !communityLoading && (
            <div className="space-y-6">
              {/* Official Solutions */}
              {officialSolutions.map((solution: OfficialSolution) => (
                <OfficialSolutionCard
                  key={solution.id}
                  solution={solution}
                  hasAccess={hasCorrectSubmission}
                />
              ))}

              {/* Community Answers */}
              {processedCommunityAnswers.map((answer: CommunityAnswer) => (
                <CommunityAnswerCard
                  key={answer.id}
                  answer={answer}
                  onLike={handleLike}
                  onComment={handleComment}
                  hasAccess={hasCorrectSubmission}
                />
              ))}

              {officialSolutions.length === 0 && processedCommunityAnswers.length === 0 && (
                <div className="text-center py-12">
                  <BookOpen className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-foreground mb-2">
                    No solutions yet
                  </h3>
                  <p className="text-muted-foreground mb-4">
                    Be the first to share your solution approach!
                  </p>
                </div>
              )}
            </div>
          )}
        </TabsContent>

        <TabsContent value="official" className="mt-6">
          <div className="space-y-6">
            {officialLoading && (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
                <p className="text-muted-foreground">Loading official solutions...</p>
              </div>
            )}

            {!officialLoading && officialSolutions.length > 0 && (
              officialSolutions.map((solution: OfficialSolution) => (
                <OfficialSolutionCard
                  key={solution.id}
                  solution={solution}
                  hasAccess={hasCorrectSubmission}
                />
              ))
            )}

            {!officialLoading && officialSolutions.length === 0 && (
              <div className="text-center py-12">
                <Trophy className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-foreground mb-2">
                  No official solutions yet
                </h3>
                <p className="text-muted-foreground">
                  Official solutions haven't been published for this problem yet.
                </p>
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="community" className="mt-6">
          <div className="space-y-6">
            {/* Filters and Sorting */}
            {processedCommunityAnswers.length > 0 && (
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  <Filter className="w-4 h-4 text-muted-foreground" />
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="outline" size="sm" className="w-32">
                        {sortBy === 'newest' && 'Newest'}
                        {sortBy === 'oldest' && 'Oldest'} 
                        {sortBy === 'popular' && 'Most Liked'}
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent>
                      <DropdownMenuItem onClick={() => setSortBy('newest')}>
                        Newest
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => setSortBy('oldest')}>
                        Oldest
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => setSortBy('popular')}>
                        Most Liked
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
                
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm" className="w-40">
                      {filterType === 'all' && 'All Answers'}
                      {filterType === 'withCode' && 'With Code'}
                      {filterType === 'popular' && 'Popular'}
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent>
                    <DropdownMenuItem onClick={() => setFilterType('all')}>
                      All Answers
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setFilterType('withCode')}>
                      With Code
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => setFilterType('popular')}>
                      Popular
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            )}

            {communityLoading && (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
                <p className="text-muted-foreground">Loading community answers...</p>
              </div>
            )}

            {!communityLoading && processedCommunityAnswers.length > 0 && (
              <div className="space-y-4" data-testid="community-answers-list">
                {processedCommunityAnswers.map((answer: CommunityAnswer) => (
                  <CommunityAnswerCard
                    key={answer.id}
                    answer={answer}
                    onLike={handleLike}
                    onComment={handleComment}
                    hasAccess={hasCorrectSubmission}
                  />
                ))}
              </div>
            )}

            {!communityLoading && processedCommunityAnswers.length === 0 && (
              <div className="text-center py-12">
                <Users className="h-16 w-16 text-muted-foreground mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-foreground mb-2">
                  No community solutions yet
                </h3>
                <p className="text-muted-foreground mb-4">
                  Be the first to share your solution with the community!
                </p>
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
});

export default AnswersScreen;