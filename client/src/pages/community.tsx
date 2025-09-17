import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Heart, MessageCircle, Share, Code, Trophy, Image, Users, Activity, Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Separator } from '@/components/ui/separator';
import { useAuth } from '@/hooks/use-auth';
import { communityApi } from '@/lib/auth';
import { useToast } from '@/hooks/use-toast';

export default function Community() {
  const [newPostContent, setNewPostContent] = useState('');
  const [newPostCodeSnippet, setNewPostCodeSnippet] = useState('');
  const [selectedPostComments, setSelectedPostComments] = useState<string | null>(null);
  const [newComment, setNewComment] = useState('');
  const [pendingLikes, setPendingLikes] = useState<Set<string>>(new Set());
  const { user } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: posts, isLoading: postsLoading } = useQuery({
    queryKey: ['/api/community/posts'],
    queryFn: () => communityApi.getPosts(),
  });

  const createPostMutation = useMutation({
    mutationFn: (postData: { content: string; codeSnippet?: string }) => 
      communityApi.createPost(postData),
    onSuccess: () => {
      setNewPostContent('');
      setNewPostCodeSnippet('');
      queryClient.invalidateQueries({ queryKey: ['/api/community/posts'] });
      toast({
        title: 'Success!',
        description: 'Your post has been shared with the community.',
      });
    },
    onError: (error) => {
      toast({
        title: 'Failed to create post',
        description: error instanceof Error ? error.message : 'Please try again.',
        variant: 'destructive',
      });
    },
  });

  const likePostMutation = useMutation({
    mutationFn: ({ postId, isLiked }: { postId: string; isLiked: boolean }) =>
      isLiked ? communityApi.unlikePost(postId) : communityApi.likePost(postId),
    onMutate: async ({ postId, isLiked }) => {
      // Add to pending likes
      setPendingLikes(prev => new Set(prev).add(postId));
      
      // Cancel outgoing queries
      await queryClient.cancelQueries({ queryKey: ['/api/community/posts'] });
      
      // Snapshot previous value
      const previousPosts = queryClient.getQueryData(['/api/community/posts']);
      
      // Optimistically update the cache
      queryClient.setQueryData(['/api/community/posts'], (old: any) => {
        if (!old) return old;
        return old.map((post: any) => {
          if (post.id === postId) {
            return {
              ...post,
              likedByCurrentUser: !isLiked,
              likes: isLiked ? post.likes - 1 : post.likes + 1
            };
          }
          return post;
        });
      });
      
      return { previousPosts };
    },
    onError: (error, { postId }, context) => {
      // Revert optimistic update
      if (context?.previousPosts) {
        queryClient.setQueryData(['/api/community/posts'], context.previousPosts);
      }
      
      toast({
        title: 'Action failed',
        description: error instanceof Error ? error.message : 'Please try again.',
        variant: 'destructive',
      });
    },
    onSettled: (data, error, { postId }) => {
      // Remove from pending likes
      setPendingLikes(prev => {
        const newSet = new Set(prev);
        newSet.delete(postId);
        return newSet;
      });
      
      // Invalidate and refetch
      queryClient.invalidateQueries({ queryKey: ['/api/community/posts'] });
    },
  });

  // Fetch comments for a specific post
  const { data: comments = [] } = useQuery({
    queryKey: [`/api/community/posts/${selectedPostComments}/comments`],
    queryFn: () => communityApi.getComments(selectedPostComments!),
    enabled: !!selectedPostComments,
  });

  // Create comment mutation
  const createCommentMutation = useMutation({
    mutationFn: ({ postId, content }: { postId: string; content: string }) =>
      communityApi.createComment(postId, content),
    onSuccess: () => {
      setNewComment('');
      queryClient.invalidateQueries({ queryKey: [`/api/community/posts/${selectedPostComments}/comments`] });
      queryClient.invalidateQueries({ queryKey: ['/api/community/posts'] });
      toast({
        title: 'Comment posted!',
        description: 'Your comment has been added.',
      });
    },
    onError: (error) => {
      toast({
        title: 'Failed to post comment',
        description: error instanceof Error ? error.message : 'Please try again.',
        variant: 'destructive',
      });
    },
  });

  const handleCreatePost = () => {
    if (!newPostContent.trim()) return;
    
    createPostMutation.mutate({
      content: newPostContent,
      codeSnippet: newPostCodeSnippet || undefined,
    });
  };

  const handleLikePost = (postId: string, currentlyLiked: boolean) => {
    likePostMutation.mutate({ postId, isLiked: currentlyLiked });
  };

  const handleOpenComments = (postId: string) => {
    setSelectedPostComments(postId);
  };

  const handleCreateComment = () => {
    if (!newComment.trim() || !selectedPostComments) return;
    createCommentMutation.mutate({ 
      postId: selectedPostComments, 
      content: newComment 
    });
  };

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));
    
    if (diffInHours < 1) return 'Just now';
    if (diffInHours < 24) return `${diffInHours}h ago`;
    if (diffInHours < 168) return `${Math.floor(diffInHours / 24)}d ago`;
    return date.toLocaleDateString();
  };

  const getLevelBadgeColor = (level: string) => {
    switch (level) {
      case 'SQL Powerlifter': return 'bg-purple-100 text-purple-800';
      case 'SQL Athlete': return 'bg-blue-100 text-blue-800';
      case 'SQL Trainee': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  // Mock data for active members and study groups
  const activeMembers = [
    { id: '1', username: 'alex_chen', status: 'online', lastActive: 'Online now' },
    { id: '2', username: 'sarah_j', status: 'away', lastActive: '5 min ago' },
    { id: '3', username: 'mike_db', status: 'online', lastActive: 'Online now' },
  ];

  const studyGroups = [
    { name: 'Advanced Window Functions', members: 12 },
    { name: 'SQL Performance Tuning', members: 8 },
    { name: 'Database Design Patterns', members: 15 },
  ];

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-foreground mb-4">SQL Gym Community</h1>
          <p className="text-xl text-muted-foreground">Connect, share, and motivate each other</p>
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Main Feed */}
          <div className="lg:col-span-2 space-y-6">
            {/* Create Post */}
            {user && (
              <Card>
                <CardContent className="p-6">
                  <div className="flex items-start space-x-4">
                    <Avatar className="w-12 h-12">
                      <AvatarImage src={user.profileImageUrl} alt={user.username} />
                      <AvatarFallback>
                        {user.username?.charAt(0).toUpperCase() || 'U'}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1">
                      <Textarea
                        placeholder="Share your SQL journey, tips, or celebrate your achievements..."
                        value={newPostContent}
                        onChange={(e) => setNewPostContent(e.target.value)}
                        rows={3}
                        className="resize-none mb-3"
                        data-testid="textarea-new-post"
                      />
                      
                      {/* Code Snippet Input */}
                      <details className="mb-3">
                        <summary className="cursor-pointer text-sm text-muted-foreground hover:text-foreground">
                          Add code snippet (optional)
                        </summary>
                        <Textarea
                          placeholder="-- Add your SQL code here
SELECT column1, column2
FROM table_name
WHERE condition;"
                          value={newPostCodeSnippet}
                          onChange={(e) => setNewPostCodeSnippet(e.target.value)}
                          rows={4}
                          className="mt-2 font-mono text-sm resize-none"
                          data-testid="textarea-code-snippet"
                        />
                      </details>
                      
                      <div className="flex justify-between items-center">
                        <div className="flex items-center space-x-3">
                          <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-primary">
                            <Image className="w-4 h-4" />
                          </Button>
                          <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-primary">
                            <Code className="w-4 h-4" />
                          </Button>
                          <Button variant="ghost" size="sm" className="text-muted-foreground hover:text-primary">
                            <Trophy className="w-4 h-4" />
                          </Button>
                        </div>
                        <Button
                          onClick={handleCreatePost}
                          disabled={!newPostContent.trim() || createPostMutation.isPending}
                          className="dumbbell-btn bg-primary text-primary-foreground hover:bg-primary/90"
                          data-testid="button-share-post"
                        >
                          {createPostMutation.isPending ? 'Sharing...' : 'Share'}
                        </Button>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Community Posts */}
            {postsLoading ? (
              <div className="space-y-6">
                {[...Array(3)].map((_, i) => (
                  <Card key={i} className="animate-pulse">
                    <CardContent className="p-6">
                      <div className="flex items-start space-x-4">
                        <div className="w-12 h-12 bg-muted rounded-full" />
                        <div className="flex-1 space-y-3">
                          <div className="h-4 bg-muted rounded w-1/3" />
                          <div className="h-4 bg-muted rounded" />
                          <div className="h-4 bg-muted rounded w-4/5" />
                          <div className="h-20 bg-muted rounded" />
                          <div className="flex space-x-4">
                            <div className="h-8 bg-muted rounded w-16" />
                            <div className="h-8 bg-muted rounded w-16" />
                            <div className="h-8 bg-muted rounded w-16" />
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : posts?.length === 0 ? (
              <Card>
                <CardContent className="p-12 text-center">
                  <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
                    <MessageCircle className="w-8 h-8 text-muted-foreground" />
                  </div>
                  <h3 className="text-lg font-semibold text-foreground mb-2">No posts yet</h3>
                  <p className="text-muted-foreground">Be the first to share something with the community!</p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-6">
                {posts?.map((post) => (
                  <Card key={post.id} data-testid={`post-${post.id}`}>
                    <CardContent className="p-6">
                      <div className="flex items-start space-x-4">
                        <Avatar className="w-12 h-12">
                          <AvatarImage src={post.user.profileImageUrl} alt={post.user.username} />
                          <AvatarFallback>
                            {post.user.username?.charAt(0).toUpperCase() || 'U'}
                          </AvatarFallback>
                        </Avatar>
                        
                        <div className="flex-1">
                          <div className="flex items-center space-x-2 mb-2">
                            <h4 className="font-semibold text-foreground" data-testid={`text-post-author-${post.id}`}>
                              {post.user.firstName && post.user.lastName 
                                ? `${post.user.firstName} ${post.user.lastName}`
                                : post.user.username}
                            </h4>
                            <span className="text-sm text-muted-foreground">•</span>
                            <span className="text-sm text-muted-foreground" data-testid={`text-post-time-${post.id}`}>
                              {formatTimeAgo(post.createdAt)}
                            </span>
                            <Badge className={`text-xs ${getLevelBadgeColor(post.user.level)}`}>
                              {post.user.level}
                            </Badge>
                          </div>
                          
                          {/* Problem Information - Only show on community page */}
                          {post.problem && (
                            <div className="flex items-center space-x-2 mb-3">
                              <span className="text-sm text-muted-foreground">Discussing:</span>
                              <span className="text-sm font-medium text-primary" data-testid={`text-problem-title-${post.id}`}>
                                {post.problem.title}
                              </span>
                              {post.problem.company && (
                                <>
                                  <span className="text-sm text-muted-foreground">•</span>
                                  <Badge variant="secondary" className="text-xs" data-testid={`badge-company-${post.id}`}>
                                    {post.problem.company}
                                  </Badge>
                                </>
                              )}
                              <Badge 
                                variant="outline" 
                                className={`text-xs ${
                                  post.problem.difficulty === 'Easy' ? 'text-green-600 border-green-300' :
                                  post.problem.difficulty === 'Medium' ? 'text-yellow-600 border-yellow-300' :
                                  'text-red-600 border-red-300'
                                }`}
                                data-testid={`badge-difficulty-${post.id}`}
                              >
                                {post.problem.difficulty}
                              </Badge>
                            </div>
                          )}
                          
                          <p className="text-foreground mb-4 leading-relaxed" data-testid={`text-post-content-${post.id}`}>
                            {post.content}
                          </p>
                          
                          {/* Code Snippet */}
                          {post.codeSnippet && (
                            <div className="bg-muted rounded-lg p-3 mb-4 overflow-x-auto">
                              <pre className="text-sm text-muted-foreground font-mono">
                                <code data-testid={`code-snippet-${post.id}`}>{post.codeSnippet}</code>
                              </pre>
                            </div>
                          )}
                          
                          {/* Actions */}
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-6">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleLikePost(post.id, post.likedByCurrentUser)}
                                className={`flex items-center space-x-2 transition-colors ${
                                  post.likedByCurrentUser 
                                    ? 'text-red-500 hover:text-red-600' 
                                    : 'text-muted-foreground hover:text-red-500'
                                }`}
                                data-testid={`button-like-${post.id}`}
                                disabled={pendingLikes.has(post.id)}
                              >
                                <Heart className={`w-4 h-4 ${post.likedByCurrentUser ? 'fill-current' : ''}`} />
                                <span className="text-sm">{post.likes}</span>
                              </Button>
                              
                              <Dialog 
                                open={selectedPostComments === post.id}
                                onOpenChange={(open) => {
                                  if (open) {
                                    handleOpenComments(post.id);
                                  } else {
                                    setSelectedPostComments(null);
                                    setNewComment('');
                                  }
                                }}
                              >
                                <DialogTrigger asChild>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="flex items-center space-x-2 text-muted-foreground hover:text-blue-500 transition-colors"
                                    data-testid={`button-comment-${post.id}`}
                                  >
                                    <MessageCircle className="w-4 h-4" />
                                    <span className="text-sm">{post.comments}</span>
                                  </Button>
                                </DialogTrigger>
                                <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                                  <DialogHeader>
                                    <DialogTitle>Comments</DialogTitle>
                                  </DialogHeader>
                                  
                                  {/* Comments List */}
                                  <div className="space-y-4 mb-4">
                                    {selectedPostComments === post.id && comments.length > 0 ? (
                                      comments.map((comment: any) => (
                                        <div key={comment.id} className="border-b pb-3">
                                          <div className="flex items-start space-x-3">
                                            <Avatar className="w-8 h-8">
                                              <AvatarImage src={comment.user.profileImageUrl} alt={comment.user.username} />
                                              <AvatarFallback>
                                                {comment.user.username?.charAt(0).toUpperCase() || 'U'}
                                              </AvatarFallback>
                                            </Avatar>
                                            <div className="flex-1">
                                              <div className="flex items-center space-x-2 mb-1">
                                                <span className="font-semibold text-sm">{comment.user.username}</span>
                                                <span className="text-xs text-muted-foreground">
                                                  {formatTimeAgo(comment.createdAt)}
                                                </span>
                                              </div>
                                              <p className="text-sm text-foreground">{comment.content}</p>
                                            </div>
                                          </div>
                                        </div>
                                      ))
                                    ) : (
                                      <p className="text-muted-foreground text-sm text-center py-8">
                                        No comments yet. Be the first to comment!
                                      </p>
                                    )}
                                  </div>
                                  
                                  {/* Add Comment */}
                                  <div className="border-t pt-4">
                                    <div className="flex space-x-3">
                                      <Avatar className="w-8 h-8">
                                        <AvatarImage src={user?.profileImageUrl} alt={user?.username} />
                                        <AvatarFallback>
                                          {user?.username?.charAt(0).toUpperCase() || 'U'}
                                        </AvatarFallback>
                                      </Avatar>
                                      <div className="flex-1 space-y-2">
                                        <Textarea
                                          placeholder="Write a comment..."
                                          value={newComment}
                                          onChange={(e) => setNewComment(e.target.value)}
                                          className="min-h-[80px] resize-none"
                                        />
                                        <div className="flex justify-end">
                                          <Button
                                            onClick={handleCreateComment}
                                            disabled={!newComment.trim() || createCommentMutation.isPending}
                                            size="sm"
                                          >
                                            <Send className="w-4 h-4 mr-2" />
                                            {createCommentMutation.isPending ? 'Posting...' : 'Post Comment'}
                                          </Button>
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                </DialogContent>
                              </Dialog>
                              
                              <Button
                                variant="ghost"
                                size="sm"
                                className="flex items-center space-x-2 text-muted-foreground hover:text-green-500 transition-colors"
                                data-testid={`button-share-${post.id}`}
                              >
                                <Share className="w-4 h-4" />
                                <span className="text-sm">Share</span>
                              </Button>
                            </div>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Active Members */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Activity className="w-5 h-5 text-primary" />
                  <span>Active Members</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {activeMembers.map((member) => (
                  <div key={member.id} className="flex items-center space-x-3" data-testid={`active-member-${member.username}`}>
                    <Avatar className="w-10 h-10">
                      <AvatarFallback>
                        {member.username.charAt(0).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1">
                      <p className="font-medium text-foreground text-sm">{member.username}</p>
                      <p className="text-xs text-muted-foreground">{member.lastActive}</p>
                    </div>
                    <div className={`w-3 h-3 rounded-full ${
                      member.status === 'online' ? 'bg-green-400' : 'bg-yellow-400'
                    }`} />
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Weekly Challenge */}
            <Card className="bg-gradient-to-br from-primary to-orange-400 text-white">
              <CardHeader>
                <CardTitle className="text-white">Weekly Challenge</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm opacity-90 mb-4">
                  Share 3 helpful SQL tips this week to earn the "Community Helper" badge!
                </p>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Progress</span>
                    <span>1/3</span>
                  </div>
                  <div className="w-full bg-white/20 rounded-full h-2">
                    <div className="bg-white h-2 rounded-full" style={{ width: '33%' }} />
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Study Groups */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Users className="w-5 h-5 text-primary" />
                  <span>Study Groups</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {studyGroups.map((group, index) => (
                  <div key={index} className="flex items-center justify-between" data-testid={`study-group-${index}`}>
                    <div>
                      <p className="font-medium text-foreground text-sm">{group.name}</p>
                      <p className="text-xs text-muted-foreground">{group.members} members</p>
                    </div>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="text-primary hover:bg-primary/10"
                      data-testid={`button-join-group-${index}`}
                    >
                      Join
                    </Button>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Community Stats */}
            <Card>
              <CardHeader>
                <CardTitle>Community Stats</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Total Posts</span>
                  <span className="font-bold text-foreground">{posts?.length || 0}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Active Today</span>
                  <span className="font-bold text-foreground">{activeMembers.length}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Study Groups</span>
                  <span className="font-bold text-foreground">{studyGroups.length}</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
