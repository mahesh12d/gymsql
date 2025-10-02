import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Heart,
  MessageCircle,
  Code,
  Activity,
  Send,
  Dumbbell,
  ChevronDown,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/hooks/use-auth";
import { communityApi } from "@/lib/auth";
import { useToast } from "@/hooks/use-toast";
import { UserProfilePopover } from "@/components/UserProfilePopover";
import { RichTextEditor } from "@/components/RichTextEditor";
import { MarkdownRenderer } from "@/components/MarkdownRenderer";

type PostFilter = "all" | "general" | "problems";

export default function Community() {
  const [newPostContent, setNewPostContent] = useState("");
  const [selectedPostComments, setSelectedPostComments] = useState<
    string | null
  >(null);
  const [newComment, setNewComment] = useState("");
  const [pendingLikes, setPendingLikes] = useState<Set<string>>(new Set());
  const [postFilter, setPostFilter] = useState<PostFilter>("all");
  const { user } = useAuth();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: posts, isLoading: postsLoading } = useQuery({
    queryKey: ["/api/community/posts"],
    queryFn: () => communityApi.getPosts(),
  });

  // Filter out premium problem posts for non-premium users
  const accessiblePosts = useMemo(() => {
    if (!posts) return [];

    return posts.filter((post) => {
      // If post is about a premium problem and user is not premium, hide it
      if (post.problem?.premium === true && (!user || !user.premium)) {
        return false;
      }
      return true;
    });
  }, [posts, user]);

  // Filter posts based on selected filter
  const filteredPosts = useMemo(() => {
    if (!accessiblePosts) return [];

    switch (postFilter) {
      case "general":
        return accessiblePosts.filter((post) => !post.problem);
      case "problems":
        return accessiblePosts.filter((post) => post.problem);
      case "all":
      default:
        return accessiblePosts;
    }
  }, [accessiblePosts, postFilter]);

  const createPostMutation = useMutation({
    mutationFn: (postData: { content: string; codeSnippet?: string }) =>
      communityApi.createPost(postData),
    onSuccess: () => {
      setNewPostContent("");
      queryClient.invalidateQueries({ queryKey: ["/api/community/posts"] });
      toast({
        title: "Success!",
        description: "Your post has been shared with the community.",
      });
    },
    onError: (error) => {
      toast({
        title: "Failed to create post",
        description:
          error instanceof Error ? error.message : "Please try again.",
        variant: "destructive",
      });
    },
  });

  const likePostMutation = useMutation({
    mutationFn: ({ postId, isLiked }: { postId: string; isLiked: boolean }) =>
      isLiked ? communityApi.unlikePost(postId) : communityApi.likePost(postId),
    onMutate: async ({ postId, isLiked }) => {
      // Add to pending likes
      setPendingLikes((prev) => new Set(prev).add(postId));

      // Cancel outgoing queries
      await queryClient.cancelQueries({ queryKey: ["/api/community/posts"] });

      // Snapshot previous value
      const previousPosts = queryClient.getQueryData(["/api/community/posts"]);

      // Optimistically update the cache
      queryClient.setQueryData(["/api/community/posts"], (old: any) => {
        if (!old) return old;
        return old.map((post: any) => {
          if (post.id === postId) {
            return {
              ...post,
              likedByCurrentUser: !isLiked,
              likes: isLiked ? post.likes - 1 : post.likes + 1,
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
        queryClient.setQueryData(
          ["/api/community/posts"],
          context.previousPosts,
        );
      }

      toast({
        title: "Action failed",
        description:
          error instanceof Error ? error.message : "Please try again.",
        variant: "destructive",
      });
    },
    onSettled: (data, error, { postId }) => {
      // Remove from pending likes
      setPendingLikes((prev) => {
        const newSet = new Set(prev);
        newSet.delete(postId);
        return newSet;
      });

      // Invalidate and refetch
      queryClient.invalidateQueries({ queryKey: ["/api/community/posts"] });
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
      setNewComment("");
      queryClient.invalidateQueries({
        queryKey: [`/api/community/posts/${selectedPostComments}/comments`],
      });
      queryClient.invalidateQueries({ queryKey: ["/api/community/posts"] });
      toast({
        title: "Comment posted!",
        description: "Your comment has been added.",
      });
    },
    onError: (error) => {
      toast({
        title: "Failed to post comment",
        description:
          error instanceof Error ? error.message : "Please try again.",
        variant: "destructive",
      });
    },
  });

  const handleCreatePost = () => {
    if (!newPostContent.trim()) return;

    createPostMutation.mutate({
      content: newPostContent,
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
      content: newComment,
    });
  };

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = Math.floor(
      (now.getTime() - date.getTime()) / (1000 * 60 * 60),
    );

    if (diffInHours < 1) return "Just now";
    if (diffInHours < 24) return `${diffInHours}h ago`;
    if (diffInHours < 168) return `${Math.floor(diffInHours / 24)}d ago`;
    return date.toLocaleDateString();
  };

  const getLevelBadgeColor = (level: string) => {
    switch (level) {
      case "SQL Powerlifter":
        return "bg-purple-100 text-purple-800";
      case "SQL Athlete":
        return "bg-blue-100 text-blue-800";
      case "SQL Trainee":
        return "bg-green-100 text-green-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-foreground mb-4">
            SQL Gym Community
          </h1>
          <p className="text-xl text-muted-foreground">
            Connect, share, and motivate each other
          </p>
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Main Feed */}
          <div className="lg:col-span-2 space-y-6">
            {/* Filter Dropdown with Gym Animation */}
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-foreground">
                Community Feed
              </h2>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="outline"
                    className="relative group hover:border-primary/50 transition-all duration-300"
                    data-testid="dropdown-filter-trigger"
                  >
                    <Dumbbell className="w-4 h-4 mr-2 text-primary animate-bounce group-hover:animate-pulse" />
                    <span className="font-semibold">
                      {postFilter === "all" && "All Posts"}
                      {postFilter === "general" && "General"}
                      {postFilter === "problems" && "Problem Discussions"}
                    </span>
                    <ChevronDown className="w-4 h-4 ml-2 opacity-50 group-hover:opacity-100 transition-opacity" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuRadioGroup
                    value={postFilter}
                    onValueChange={(value) =>
                      setPostFilter(value as PostFilter)
                    }
                  >
                    <DropdownMenuRadioItem
                      value="all"
                      data-testid="dropdown-all-posts"
                    >
                      All Posts
                    </DropdownMenuRadioItem>
                    <DropdownMenuRadioItem
                      value="general"
                      data-testid="dropdown-general-posts"
                    >
                      General
                    </DropdownMenuRadioItem>
                    <DropdownMenuRadioItem
                      value="problems"
                      data-testid="dropdown-problem-posts"
                    >
                      Problem Discussions
                    </DropdownMenuRadioItem>
                  </DropdownMenuRadioGroup>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            {/* Create Post */}
            {user && (
              <Card className="border-2 border-primary/20 hover:border-primary/40 transition-all duration-300 shadow-lg hover:shadow-xl bg-gradient-to-br from-background via-background to-primary/5">
                <CardContent className="p-6">
                  <div className="w-full">
                    <RichTextEditor
                      value={newPostContent}
                      onChange={setNewPostContent}
                      placeholder="Ask your SQL questions, share solutions or just chat with the community!"
                      minHeight="150px"
                      testId="textarea-new-post"
                    />

                    <div className="flex justify-end mt-3">
                      <Button
                        onClick={handleCreatePost}
                        disabled={
                          !newPostContent.trim() || createPostMutation.isPending
                        }
                        className="dumbbell-btn bg-gradient-to-r from-primary to-primary/80 text-primary-foreground hover:from-primary/90 hover:to-primary/70 shadow-md hover:shadow-lg transform hover:scale-105 transition-all duration-200"
                        data-testid="button-share-post"
                      >
                        {createPostMutation.isPending ? "Sharing..." : "Share"}
                      </Button>
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
                      <div className="w-full space-y-3">
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
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : filteredPosts.length === 0 ? (
              <Card>
                <CardContent className="p-12 text-center">
                  <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
                    <MessageCircle className="w-8 h-8 text-muted-foreground" />
                  </div>
                  <h3 className="text-lg font-semibold text-foreground mb-2">
                    {postFilter === "general"
                      ? "No general posts yet"
                      : postFilter === "problems"
                        ? "No problem discussions yet"
                        : "No posts yet"}
                  </h3>
                  <p className="text-muted-foreground">
                    {postFilter === "all"
                      ? "Be the first to share something with the community!"
                      : postFilter === "general"
                        ? "Be the first to share a general post!"
                        : "Be the first to discuss a problem!"}
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-6">
                {filteredPosts.map((post) => (
                  <Card
                    key={post.id}
                    data-testid={`post-${post.id}`}
                    className="border border-border/50 hover:border-primary/30 hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 bg-gradient-to-br from-card via-card to-primary/5 backdrop-blur-sm"
                  >
                    <CardContent className="p-6">
                      <div className="w-full">
                        <div className="flex-1">
                          <div className="flex items-center space-x-2 mb-2">
                            {/* Clickable Username for Chat */}
                            <UserProfilePopover
                              user={{
                                id: post.user.id,
                                username: post.user.username,
                                first_name: post.user.firstName,
                                last_name: post.user.lastName,
                                profileImageUrl: post.user.profileImageUrl,
                                premium: post.user.premium,
                              }}
                            >
                              <h4
                                className="font-bold text-foreground hover:text-primary cursor-pointer transition-all duration-200 hover:scale-105 inline-block"
                                data-testid={`text-post-author-${post.id}`}
                              >
                                {post.user.firstName && post.user.lastName
                                  ? `${post.user.firstName} ${post.user.lastName}`
                                  : post.user.username}
                              </h4>
                            </UserProfilePopover>
                            <span className="text-sm text-muted-foreground">
                              •
                            </span>
                            <span
                              className="text-sm text-muted-foreground"
                              data-testid={`text-post-time-${post.id}`}
                            >
                              {formatTimeAgo(post.createdAt)}
                            </span>
                            <Badge
                              className={`text-xs ${getLevelBadgeColor(post.user.level)} shadow-sm hover:shadow-md transition-shadow duration-200`}
                            >
                              {post.user.level}
                            </Badge>
                          </div>

                          {/* Problem Information - Only show on community page */}
                          {post.problem && (
                            <div className="flex items-center space-x-2 mb-3">
                              <span className="text-sm text-muted-foreground">
                                Discussing:
                              </span>
                              <span
                                className="text-sm font-medium text-primary"
                                data-testid={`text-problem-title-${post.id}`}
                              >
                                {post.problem.title}
                              </span>
                              {post.problem.company && (
                                <>
                                  <span className="text-sm text-muted-foreground">
                                    •
                                  </span>
                                  <Badge
                                    variant="secondary"
                                    className="text-xs"
                                    data-testid={`badge-company-${post.id}`}
                                  >
                                    {post.problem.company}
                                  </Badge>
                                </>
                              )}
                              <Badge
                                variant="outline"
                                className={`text-xs ${
                                  post.problem.difficulty === "Easy"
                                    ? "text-green-600 border-green-300"
                                    : post.problem.difficulty === "Medium"
                                      ? "text-yellow-600 border-yellow-300"
                                      : "text-red-600 border-red-300"
                                }`}
                                data-testid={`badge-difficulty-${post.id}`}
                              >
                                {post.problem.difficulty}
                              </Badge>
                            </div>
                          )}

                          <div
                            className="mb-4"
                            data-testid={`text-post-content-${post.id}`}
                          >
                            <MarkdownRenderer content={post.content} />
                          </div>

                          {/* Actions */}
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-6">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() =>
                                  handleLikePost(
                                    post.id,
                                    post.likedByCurrentUser,
                                  )
                                }
                                className={`flex items-center space-x-2 transition-all duration-200 hover:scale-110 ${
                                  post.likedByCurrentUser
                                    ? "text-red-600 bg-red-50 dark:text-red-400 dark:bg-red-950/50 hover:bg-red-100 dark:hover:bg-red-950"
                                    : "text-muted-foreground hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950"
                                }`}
                                data-testid={`button-like-${post.id}`}
                                disabled={pendingLikes.has(post.id)}
                              >
                                <Heart
                                  className={`w-4 h-4 transition-all duration-200 ${post.likedByCurrentUser ? "fill-current" : ""}`}
                                />
                                <span className="text-sm font-semibold">
                                  {post.likes}
                                </span>
                              </Button>

                              <Dialog
                                open={selectedPostComments === post.id}
                                onOpenChange={(open) => {
                                  if (open) {
                                    handleOpenComments(post.id);
                                  } else {
                                    setSelectedPostComments(null);
                                    setNewComment("");
                                  }
                                }}
                              >
                                <DialogTrigger asChild>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="flex items-center space-x-2 text-muted-foreground hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-950 transition-all duration-200 hover:scale-110"
                                    data-testid={`button-comment-${post.id}`}
                                  >
                                    <MessageCircle className="w-4 h-4" />
                                    <span className="text-sm font-semibold">
                                      {post.comments}
                                    </span>
                                  </Button>
                                </DialogTrigger>
                                <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                                  <DialogHeader>
                                    <DialogTitle>Comments</DialogTitle>
                                  </DialogHeader>

                                  {/* Comments List */}
                                  <div className="space-y-4 mb-4">
                                    {selectedPostComments === post.id &&
                                    comments.length > 0 ? (
                                      comments.map((comment: any) => (
                                        <div
                                          key={comment.id}
                                          className="border-b pb-3"
                                        >
                                          <div className="flex items-start space-x-3">
                                            <Avatar className="w-8 h-8">
                                              <AvatarImage
                                                src={
                                                  comment.user.profileImageUrl
                                                }
                                                alt={comment.user.username}
                                              />
                                              <AvatarFallback>
                                                {comment.user.username
                                                  ?.charAt(0)
                                                  .toUpperCase() || "U"}
                                              </AvatarFallback>
                                            </Avatar>
                                            <div className="flex-1">
                                              <div className="flex items-center space-x-2 mb-1">
                                                <span className="font-semibold text-sm">
                                                  {comment.user.username}
                                                </span>
                                                <span className="text-xs text-muted-foreground">
                                                  {formatTimeAgo(
                                                    comment.createdAt,
                                                  )}
                                                </span>
                                              </div>
                                              <div className="text-sm">
                                                <MarkdownRenderer
                                                  content={comment.content}
                                                />
                                              </div>
                                            </div>
                                          </div>
                                        </div>
                                      ))
                                    ) : (
                                      <p className="text-muted-foreground text-sm text-center py-8">
                                        No comments yet. Be the first to
                                        comment!
                                      </p>
                                    )}
                                  </div>

                                  {/* Add Comment */}
                                  <div className="border-t pt-4">
                                    <div className="flex space-x-3">
                                      <Avatar className="w-8 h-8">
                                        <AvatarImage
                                          src={user?.profileImageUrl}
                                          alt={user?.username}
                                        />
                                        <AvatarFallback>
                                          {user?.username
                                            ?.charAt(0)
                                            .toUpperCase() || "U"}
                                        </AvatarFallback>
                                      </Avatar>
                                      <div className="flex-1 space-y-2">
                                        <RichTextEditor
                                          value={newComment}
                                          onChange={setNewComment}
                                          placeholder="Write a comment..."
                                          minHeight="100px"
                                          testId="textarea-new-comment"
                                        />
                                        <div className="flex justify-end">
                                          <Button
                                            onClick={handleCreateComment}
                                            disabled={
                                              !newComment.trim() ||
                                              createCommentMutation.isPending
                                            }
                                            size="sm"
                                          >
                                            <Send className="w-4 h-4 mr-2" />
                                            {createCommentMutation.isPending
                                              ? "Posting..."
                                              : "Post Comment"}
                                          </Button>
                                        </div>
                                      </div>
                                    </div>
                                  </div>
                                </DialogContent>
                              </Dialog>
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
          <div className="space-y-6"></div>
        </div>
      </div>
    </div>
  );
}
