import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/hooks/use-toast";
import { apiRequest, queryClient } from "@/lib/queryClient";
import ReactECharts from "echarts-for-react";
import { User, Trophy, Target, TrendingUp, Clock, Star, Award, BookOpen, Lightbulb, Users, Flag, Zap, Crown, Flame, Medal, Gauge, RocketIcon, Search, UserPlus, UserMinus, Pencil, Linkedin, Building, ExternalLink, Trash2 } from "lucide-react";
import { format, subDays } from "date-fns";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { UserProfilePopover } from "@/components/UserProfilePopover";
import CalendarHeatmap from 'react-calendar-heatmap';
import 'react-calendar-heatmap/dist/styles.css';
import { Tooltip as ReactTooltip } from 'react-tooltip';

interface BasicInfo {
  user_id: string;
  username: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  company_name: string | null;
  linkedin_url: string | null;
  profile_image_url: string | null;
  problems_solved: number;
  premium: boolean;
  created_at: string;
}

interface PerformanceStats {
  total_submissions: number;
  correct_submissions: number;
  accuracy_rate: number;
  current_streak: number;
  longest_streak: number;
  rank: number;
  total_users: number;
}

interface DifficultyBreakdown {
  Easy: number;
  Medium: number;
  Hard: number;
}

interface UserBadge {
  id: string;
  name: string;
  description: string;
  icon_url: string | null;
  rarity: string;
  earned_at: string;
}

interface RecentActivity {
  problem_title: string;
  difficulty: string;
  submitted_at: string;
  execution_time: number | null;
}

interface ProgressOverTime {
  date: string;
  solved_count: number;
}

interface UserProfile {
  success: boolean;
  basic_info: BasicInfo;
  performance_stats: PerformanceStats;
  difficulty_breakdown: DifficultyBreakdown;
  topic_breakdown: Record<string, number>;
  recent_activity: RecentActivity[];
  progress_over_time: ProgressOverTime[];
  badges: UserBadge[];
}


interface FollowerUser {
  id: string;
  username: string;
  firstName: string | null;
  lastName: string | null;
  companyName: string | null;
  linkedinUrl: string | null;
  profileImageUrl: string | null;
  problemsSolved: number;
}

interface FollowStatus {
  isFollowing: boolean;
  followersCount: number;
  followingCount: number;
}

const DIFFICULTY_COLORS = {
  Easy: "#22c55e",
  Medium: "#f59e0b", 
  Hard: "#ef4444"
};

const RARITY_COLORS = {
  common: "#64748b",
  rare: "#3b82f6",
  epic: "#8b5cf6",
  legendary: "#f59e0b"
};

// ✏️ Edit Profile Dialog
function EditProfileDialog({ basicInfo }: { basicInfo: BasicInfo }) {
  const [open, setOpen] = useState(false);
  const [firstName, setFirstName] = useState(basicInfo.first_name || "");
  const [lastName, setLastName] = useState(basicInfo.last_name || "");
  const [companyName, setCompanyName] = useState(basicInfo.company_name || "");
  const [linkedinUrl, setLinkedinUrl] = useState(basicInfo.linkedin_url || "");
  const { toast } = useToast();

  const updateProfileMutation = useMutation({
    mutationFn: async (data: { firstName: string; lastName: string; companyName: string; linkedinUrl: string }) => {
      const response = await apiRequest("PUT", "/api/users/profile", data);
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/user/profile"] });
      queryClient.invalidateQueries({ queryKey: ["/api/auth/user"] });
      toast({
        title: "Success",
        description: "Profile updated successfully",
      });
      setOpen(false);
    },
    onError: (error: any) => {
      toast({
        title: "Error",
        description: error.message || "Failed to update profile",
        variant: "destructive",
      });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateProfileMutation.mutate({
      firstName,
      lastName,
      companyName,
      linkedinUrl,
    });
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" data-testid="button-edit-profile">
          <Pencil className="h-4 w-4 mr-2" />
          Edit Profile
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]" data-testid="dialog-edit-profile">
        <DialogHeader>
          <DialogTitle>Edit Profile</DialogTitle>
          <DialogDescription>
            Update your personal information
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 mt-4">
          <div className="space-y-2">
            <Label htmlFor="firstName">First Name</Label>
            <Input
              id="firstName"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              placeholder="Enter first name"
              data-testid="input-first-name"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="lastName">Last Name</Label>
            <Input
              id="lastName"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              placeholder="Enter last name"
              data-testid="input-last-name"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="companyName">
              <Building className="h-4 w-4 inline mr-1" />
              Company Name
            </Label>
            <Input
              id="companyName"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="Enter company name"
              data-testid="input-company-name"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="linkedinUrl">
              <Linkedin className="h-4 w-4 inline mr-1" />
              LinkedIn URL
            </Label>
            <Input
              id="linkedinUrl"
              type="url"
              value={linkedinUrl}
              onChange={(e) => setLinkedinUrl(e.target.value)}
              placeholder="https://linkedin.com/in/username"
              data-testid="input-linkedin-url"
            />
          </div>
          <div className="flex justify-end space-x-2 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
              data-testid="button-cancel"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={updateProfileMutation.isPending}
              data-testid="button-save-profile"
            >
              {updateProfileMutation.isPending ? "Saving..." : "Save Changes"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// 👤 Competitive User Information Header
function CompetitiveUserHeader({ basicInfo, performanceStats }: { basicInfo: BasicInfo; performanceStats: PerformanceStats }) {
  const displayName = basicInfo.first_name && basicInfo.last_name 
    ? `${basicInfo.first_name} ${basicInfo.last_name}`
    : basicInfo.username;

  // Determine title based on performance
  const getUserTitle = () => {
    if (performanceStats.rank <= 10) return "SQL Legend 👑";
    if (performanceStats.rank <= 100) return "Query Master 🏆";
    if (performanceStats.accuracy_rate > 90) return "Joins Specialist 🔗";
    if (performanceStats.correct_submissions > 50) return "Window Function Expert 📊";
    return "Rising Star ⭐";
  };

  return (
    <Card data-testid="profile-header" className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-950 dark:to-purple-950 border-2">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-6">
            <Avatar className="h-24 w-24 border-4 border-yellow-400" data-testid="avatar-profile">
              <AvatarImage src={basicInfo.profile_image_url || undefined} />
              <AvatarFallback className="text-xl bg-gradient-to-br from-yellow-400 to-orange-500 text-white">
                {displayName.charAt(0).toUpperCase()}
              </AvatarFallback>
            </Avatar>
            
            <div className="flex-1">
              <div className="flex items-center space-x-3 mb-1">
                <CardTitle className="text-3xl" data-testid="text-username">{displayName}</CardTitle>
                <Badge className="bg-gradient-to-r from-yellow-500 to-orange-500 text-white" data-testid="badge-title">
                  {getUserTitle()}
                </Badge>
              </div>
              
              <div className="flex items-center space-x-2 mb-3">
                <Crown className="h-5 w-5 text-yellow-500" />
                <span className="text-xl font-bold text-yellow-600" data-testid="text-global-rank">
                  #{performanceStats.rank} / {(performanceStats.total_users || 0).toLocaleString()}
                </span>
                <span className="text-sm text-muted-foreground">Global Rank</span>
              </div>
              
              <div className="flex items-center space-x-6 text-sm flex-wrap">
                <div className="flex items-center space-x-1" data-testid="text-joined">
                  <User className="h-4 w-4" />
                  <span className="text-muted-foreground">
                    Joined {format(new Date(basicInfo.created_at), "MMM yyyy")}
                  </span>
                </div>
                <div className="flex items-center space-x-1" data-testid="text-last-active">
                  <Clock className="h-4 w-4" />
                  <span className="text-muted-foreground">Last active today</span>
                </div>
                {basicInfo.company_name && (
                  <div className="flex items-center space-x-1" data-testid="text-company">
                    <Building className="h-4 w-4" />
                    <span className="text-muted-foreground">{basicInfo.company_name}</span>
                  </div>
                )}
                {basicInfo.linkedin_url && (
                  <a 
                    href={basicInfo.linkedin_url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="flex items-center space-x-1 text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                    data-testid="link-linkedin"
                  >
                    <Linkedin className="h-4 w-4" />
                    <span>LinkedIn</span>
                  </a>
                )}
              </div>
            </div>
          </div>
          
          {/* Quick Stats Badge */}
          <div className="text-right space-y-2">
            <EditProfileDialog basicInfo={basicInfo} />
            <Badge variant={basicInfo.premium ? "default" : "secondary"} data-testid="badge-premium" className="block">
              {basicInfo.premium ? "Premium Racer 🏎️" : "Free Rider 🚗"}
            </Badge>
            <div className="text-sm text-muted-foreground" data-testid="text-email">{basicInfo.email}</div>
          </div>
        </div>
      </CardHeader>
    </Card>
  );
}

// 🏆 Competitive Overview Section
function CompetitiveOverview({ stats, recentActivity, allUsersStats }: { 
  stats: PerformanceStats;
  recentActivity: RecentActivity[];
  allUsersStats?: { avgAccuracy: number; avgSolved: number };
}) {
  const userSolved = stats.correct_submissions;
  
  // Calculate averages from backend data or use defaults
  const globalAvgAccuracy = allUsersStats?.avgAccuracy || 73;
  const top10PercentAverage = allUsersStats?.avgSolved || Math.ceil(userSolved * 1.5);
  
  // Calculate fastest solve time from recent activity
  const executionTimes = (recentActivity || [])
    .filter(a => a.execution_time !== null && a.execution_time > 0)
    .map(a => a.execution_time as number);
  
  const fastestTime = executionTimes.length > 0 
    ? Math.min(...executionTimes)
    : null;
  
  // Format time in seconds or ms
  const formatTime = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    if (minutes > 0) {
      return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }
    return `${seconds}s`;
  };

  return (
    <Card data-testid="card-competitive-overview" className="border-2 border-yellow-200 dark:border-yellow-800">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Trophy className="h-6 w-6 text-yellow-500" />
          <span>🏆 Competitive Overview</span>
        </CardTitle>
        <CardDescription>How you stack up against other SQL racers</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Total Questions Solved vs Top 10% */}
          <div className="text-center p-4 bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900 dark:to-blue-800 rounded-lg" data-testid="stat-solved-comparison">
            <div className="flex items-center justify-center space-x-2 mb-2">
              <Target className="h-5 w-5 text-blue-600" />
              <span className="text-sm font-medium">Questions Solved</span>
            </div>
            <div className="text-3xl font-bold text-blue-600">{userSolved}</div>
            <div className="text-sm text-muted-foreground mb-2">
              Top 10% avg: {top10PercentAverage}
            </div>
            <Badge variant={userSolved > top10PercentAverage ? "default" : "secondary"}>
              {userSolved > top10PercentAverage ? "Above Average 📈" : "Room to Grow 🚀"}
            </Badge>
          </div>

          {/* Accuracy Rate vs Peers */}
          <div className="text-center p-4 bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900 dark:to-green-800 rounded-lg" data-testid="stat-accuracy-comparison">
            <div className="flex items-center justify-center space-x-2 mb-2">
              <Gauge className="h-5 w-5 text-green-600" />
              <span className="text-sm font-medium">Accuracy Rate</span>
            </div>
            <div className="text-3xl font-bold text-green-600">{stats.accuracy_rate}%</div>
            <div className="text-sm text-muted-foreground mb-2">
              vs Global avg: {globalAvgAccuracy}%
            </div>
            <Badge variant={stats.accuracy_rate > globalAvgAccuracy ? "default" : "secondary"}>
              {stats.accuracy_rate > 90 ? "Elite Precision 🎯" : stats.accuracy_rate > globalAvgAccuracy ? "Above Average ⬆️" : "Keep Practicing 💪"}
            </Badge>
          </div>

          {/* Fastest Solve Time Record */}
          <div className="text-center p-4 bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900 dark:to-purple-800 rounded-lg" data-testid="stat-fastest-time">
            <div className="flex items-center justify-center space-x-2 mb-2">
              <Zap className="h-5 w-5 text-purple-600" />
              <span className="text-sm font-medium">Fastest Solve</span>
            </div>
            {fastestTime !== null ? (
              <>
                <div className="text-3xl font-bold text-purple-600">{formatTime(fastestTime)}</div>
                <div className="text-sm text-muted-foreground mb-2">
                  Personal best 🏁
                </div>
                <Badge variant="outline" className="border-purple-600 text-purple-600">
                  {fastestTime < 1000 ? "Lightning Fast ⚡" : fastestTime < 5000 ? "Quick Solver 🚀" : "Steady Pace 💪"}
                </Badge>
              </>
            ) : (
              <>
                <div className="text-2xl font-bold text-purple-600">N/A</div>
                <div className="text-sm text-muted-foreground mb-2">
                  No timed solves yet
                </div>
                <Badge variant="outline" className="border-purple-600 text-purple-600">
                  Start Racing! 🏁
                </Badge>
              </>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}


// 📚 Helpful Link Interface
interface HelpfulLink {
  id: string;
  userId: string;
  title: string;
  url: string;
  createdAt: string;
  user: {
    id: string;
    username: string;
    firstName?: string;
    lastName?: string;
  };
}

// 👥 Combined Friends & Resources Component
function FriendsAndResourcesSection({ userId, isPremium }: { userId: string; isPremium: boolean }) {
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<FollowerUser[]>([]);
  const [newTitle, setNewTitle] = useState('');
  const [newUrl, setNewUrl] = useState('');
  const { toast } = useToast();

  // Get follow status for current user
  const { data: followStatus } = useQuery<FollowStatus>({
    queryKey: ["/api/users/follow-status", userId],
    enabled: !!userId,
  });

  // Get followers list
  const { data: followers = [] } = useQuery<FollowerUser[]>({
    queryKey: ["/api/users/followers", userId],
    enabled: !!userId,
  });

  // Get following list
  const { data: following = [] } = useQuery<FollowerUser[]>({
    queryKey: ["/api/users/following", userId],
    enabled: !!userId,
  });

  // Get helpful links
  const { data: links, isLoading: linksLoading } = useQuery<HelpfulLink[]>({
    queryKey: ['/api/helpful-links'],
  });

  // Follow user mutation
  const followMutation = useMutation({
    mutationFn: async (targetUserId: string) => {
      const response = await apiRequest("POST", `/api/users/follow/${targetUserId}`);
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/users/follow-status", userId] });
      queryClient.invalidateQueries({ queryKey: ["/api/users/followers", userId] });
      queryClient.invalidateQueries({ queryKey: ["/api/users/following", userId] });
      toast({
        title: "Success",
        description: "Successfully followed user",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Error",
        description: error.message || "Failed to follow user",
        variant: "destructive",
      });
    },
  });

  // Unfollow user mutation
  const unfollowMutation = useMutation({
    mutationFn: async (targetUserId: string) => {
      const response = await apiRequest("DELETE", `/api/users/unfollow/${targetUserId}`);
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/users/follow-status", userId] });
      queryClient.invalidateQueries({ queryKey: ["/api/users/followers", userId] });
      queryClient.invalidateQueries({ queryKey: ["/api/users/following", userId] });
      toast({
        title: "Success",
        description: "Successfully unfollowed user",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Error",
        description: error.message || "Failed to unfollow user",
        variant: "destructive",
      });
    },
  });

  // Create link mutation
  const createLinkMutation = useMutation({
    mutationFn: async (data: { title: string; url: string }) => {
      const response = await apiRequest('POST', '/api/helpful-links', data);
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/helpful-links'] });
      setNewTitle('');
      setNewUrl('');
      toast({
        title: 'Success',
        description: 'Link shared successfully!',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.message || 'Failed to share link',
        variant: 'destructive',
      });
    },
  });

  // Delete link mutation
  const deleteLinkMutation = useMutation({
    mutationFn: async (linkId: string) => {
      const response = await apiRequest('DELETE', `/api/helpful-links/${linkId}`);
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/helpful-links'] });
      toast({
        title: 'Success',
        description: 'Link removed successfully!',
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.message || 'Failed to remove link',
        variant: 'destructive',
      });
    },
  });

  // Search users
  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }

    try {
      const response = await apiRequest("GET", `/api/users/search?q=${encodeURIComponent(searchQuery)}&limit=10`);
      const data = await response.json();
      setSearchResults(data);
    } catch (error: any) {
      toast({
        title: "Error",
        description: "Failed to search users",
        variant: "destructive",
      });
    }
  };

  const handleFollow = (targetUserId: string) => {
    followMutation.mutate(targetUserId);
  };

  const handleUnfollow = (targetUserId: string) => {
    unfollowMutation.mutate(targetUserId);
  };

  const isFollowingUser = (targetUserId: string) => {
    return following.some(user => user.id === targetUserId);
  };

  const handleSubmitLink = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || !newUrl.trim()) {
      toast({
        title: 'Error',
        description: 'Please fill in all fields',
        variant: 'destructive',
      });
      return;
    }
    createLinkMutation.mutate({ title: newTitle, url: newUrl });
  };

  return (
    <Card data-testid="card-friends-resources" className="border-2 border-purple-200 dark:border-purple-800">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Users className="h-6 w-6 text-purple-500" />
          <span>👥 Friends & Resources</span>
        </CardTitle>
        <CardDescription>
          Connect with users and share helpful resources
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="friends" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="friends" data-testid="tab-friends">
              <Users className="h-4 w-4 mr-2" />
              Friends
            </TabsTrigger>
            <TabsTrigger value="resources" data-testid="tab-resources">
              <BookOpen className="h-4 w-4 mr-2" />
              Resources
            </TabsTrigger>
          </TabsList>

          {/* Friends Tab */}
          <TabsContent value="friends" className="space-y-4">
            <div className="text-sm text-muted-foreground mb-2">
              {followStatus?.followersCount || 0} Followers • {followStatus?.followingCount || 0} Following
            </div>
            
            <Tabs defaultValue="search" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="search" data-testid="tab-search">Search</TabsTrigger>
                <TabsTrigger value="followers" data-testid="tab-followers">
                  Followers ({followStatus?.followersCount || 0})
                </TabsTrigger>
                <TabsTrigger value="following" data-testid="tab-following">
                  Following ({followStatus?.followingCount || 0})
                </TabsTrigger>
              </TabsList>

              {/* Search Tab */}
              <TabsContent value="search" className="space-y-4">
                <div className="flex space-x-2">
                  <Input
                    placeholder="Search users..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyPress={(e) => e.key === "Enter" && handleSearch()}
                    data-testid="input-search-users"
                  />
                  <Button onClick={handleSearch} data-testid="button-search">
                    <Search className="h-4 w-4 mr-2" />
                    Search
                  </Button>
                </div>

                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {searchResults.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground" data-testid="text-no-search-results">
                      {searchQuery ? "No users found" : "Search for users to follow"}
                    </div>
                  ) : (
                    searchResults.map((user) => (
                      <div
                        key={user.id}
                        className="flex items-center justify-between p-3 rounded-lg border hover:bg-accent"
                        data-testid={`user-search-result-${user.id}`}
                      >
                        <div className="flex items-center space-x-3">
                          <Avatar className="h-10 w-10">
                            <AvatarImage src={user.profileImageUrl || undefined} />
                            <AvatarFallback>{user.username.charAt(0).toUpperCase()}</AvatarFallback>
                          </Avatar>
                          <div>
                            <div className="font-medium">{user.username}</div>
                            {(user.firstName || user.lastName) && (
                              <div className="text-sm text-muted-foreground">
                                {user.firstName} {user.lastName}
                              </div>
                            )}
                            <div className="text-xs text-muted-foreground">
                              {user.problemsSolved} problems solved
                            </div>
                          </div>
                        </div>
                        <Button
                          size="sm"
                          variant={isFollowingUser(user.id) ? "outline" : "default"}
                          onClick={() =>
                            isFollowingUser(user.id) ? handleUnfollow(user.id) : handleFollow(user.id)
                          }
                          disabled={followMutation.isPending || unfollowMutation.isPending}
                          data-testid={`button-follow-${user.id}`}
                        >
                          {isFollowingUser(user.id) ? (
                            <>
                              <UserMinus className="h-4 w-4 mr-1" />
                              Unfollow
                            </>
                          ) : (
                            <>
                              <UserPlus className="h-4 w-4 mr-1" />
                              Follow
                            </>
                          )}
                        </Button>
                      </div>
                    ))
                  )}
                </div>
              </TabsContent>

              {/* Followers Tab */}
              <TabsContent value="followers" className="space-y-2 max-h-96 overflow-y-auto">
                {followers.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground" data-testid="text-no-followers">
                    No followers yet
                  </div>
                ) : (
                  followers.map((user) => (
                    <div
                      key={user.id}
                      className="flex items-center justify-between p-3 rounded-lg border"
                      data-testid={`follower-${user.id}`}
                    >
                      <UserProfilePopover
                        user={{
                          id: user.id,
                          username: user.username,
                          first_name: user.firstName || undefined,
                          last_name: user.lastName || undefined,
                          companyName: user.companyName || undefined,
                          linkedinUrl: user.linkedinUrl || undefined,
                          profileImageUrl: user.profileImageUrl || undefined,
                          problemsSolved: user.problemsSolved,
                        }}
                        trigger="hover"
                      >
                        <div className="flex items-center space-x-3">
                          <Avatar className="h-10 w-10">
                            <AvatarImage src={user.profileImageUrl || undefined} />
                            <AvatarFallback>{user.username.charAt(0).toUpperCase()}</AvatarFallback>
                          </Avatar>
                          <div>
                            <div className="font-medium">{user.username}</div>
                            {(user.firstName || user.lastName) && (
                              <div className="text-sm text-muted-foreground">
                                {user.firstName} {user.lastName}
                              </div>
                            )}
                            <div className="text-xs text-muted-foreground">
                              {user.problemsSolved} problems solved
                            </div>
                          </div>
                        </div>
                      </UserProfilePopover>
                      <Button
                        size="sm"
                        variant={isFollowingUser(user.id) ? "outline" : "default"}
                        onClick={() =>
                          isFollowingUser(user.id) ? handleUnfollow(user.id) : handleFollow(user.id)
                        }
                        disabled={followMutation.isPending || unfollowMutation.isPending}
                        data-testid={`button-follow-back-${user.id}`}
                      >
                        {isFollowingUser(user.id) ? (
                          <>
                            <UserMinus className="h-4 w-4 mr-1" />
                            Unfollow
                          </>
                        ) : (
                          <>
                            <UserPlus className="h-4 w-4 mr-1" />
                            Follow Back
                          </>
                        )}
                      </Button>
                    </div>
                  ))
                )}
              </TabsContent>

              {/* Following Tab */}
              <TabsContent value="following" className="space-y-2 max-h-96 overflow-y-auto">
                {following.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground" data-testid="text-not-following-anyone">
                    Not following anyone yet
                  </div>
                ) : (
                  following.map((user) => (
                    <div
                      key={user.id}
                      className="flex items-center justify-between p-3 rounded-lg border"
                      data-testid={`following-${user.id}`}
                    >
                      <UserProfilePopover
                        user={{
                          id: user.id,
                          username: user.username,
                          first_name: user.firstName || undefined,
                          last_name: user.lastName || undefined,
                          companyName: user.companyName || undefined,
                          linkedinUrl: user.linkedinUrl || undefined,
                          profileImageUrl: user.profileImageUrl || undefined,
                          problemsSolved: user.problemsSolved,
                        }}
                        trigger="hover"
                      >
                        <div className="flex items-center space-x-3">
                          <Avatar className="h-10 w-10">
                            <AvatarImage src={user.profileImageUrl || undefined} />
                            <AvatarFallback>{user.username.charAt(0).toUpperCase()}</AvatarFallback>
                          </Avatar>
                          <div>
                            <div className="font-medium">{user.username}</div>
                            {(user.firstName || user.lastName) && (
                              <div className="text-sm text-muted-foreground">
                                {user.firstName} {user.lastName}
                              </div>
                            )}
                            <div className="text-xs text-muted-foreground">
                              {user.problemsSolved} problems solved
                            </div>
                          </div>
                        </div>
                      </UserProfilePopover>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleUnfollow(user.id)}
                        disabled={unfollowMutation.isPending}
                        data-testid={`button-unfollow-${user.id}`}
                      >
                        <UserMinus className="h-4 w-4 mr-1" />
                        Unfollow
                      </Button>
                    </div>
                  ))
                )}
              </TabsContent>
            </Tabs>
          </TabsContent>

          {/* Resources Tab */}
          <TabsContent value="resources" className="space-y-6">
            {!isPremium ? (
              <div className="text-center py-8">
                <Crown className="h-12 w-12 mx-auto mb-4 text-yellow-500" />
                <Badge variant="outline" className="mb-4">Premium</Badge>
                <p className="text-muted-foreground">
                  Premium users can share helpful SQL resources, tutorials, and articles with the community.
                </p>
              </div>
            ) : (
              <>
                <form onSubmit={handleSubmitLink} className="space-y-4 p-4 border rounded-lg bg-muted/30">
                  <div className="space-y-2">
                    <Label htmlFor="link-title">Resource Title</Label>
                    <Input
                      id="link-title"
                      placeholder="e.g., SQL Join Tutorial"
                      value={newTitle}
                      onChange={(e) => setNewTitle(e.target.value)}
                      data-testid="input-link-title"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="link-url">URL</Label>
                    <Input
                      id="link-url"
                      placeholder="https://..."
                      value={newUrl}
                      onChange={(e) => setNewUrl(e.target.value)}
                      type="url"
                      data-testid="input-link-url"
                    />
                  </div>
                  <Button
                    type="submit"
                    className="w-full"
                    disabled={createLinkMutation.isPending}
                    data-testid="button-submit-link"
                  >
                    {createLinkMutation.isPending ? 'Sharing...' : 'Share Resource'}
                  </Button>
                </form>

                <Separator />

                <div className="space-y-3">
                  <h3 className="font-medium text-sm text-muted-foreground">Your Shared Links</h3>
                  {linksLoading ? (
                    <div className="space-y-3">
                      {[...Array(2)].map((_, i) => (
                        <div key={i} className="h-16 bg-muted rounded-lg animate-pulse" />
                      ))}
                    </div>
                  ) : links && links.length > 0 ? (
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {links.map((link) => (
                        <div
                          key={link.id}
                          className="p-3 bg-muted/50 rounded-lg hover:bg-muted transition-colors"
                          data-testid={`link-item-${link.id}`}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1 min-w-0">
                              <a
                                href={link.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="font-medium text-sm text-foreground hover:text-primary flex items-center space-x-1"
                                data-testid={`link-url-${link.id}`}
                              >
                                <span className="truncate">{link.title}</span>
                                <ExternalLink className="w-3 h-3 flex-shrink-0" />
                              </a>
                              <p className="text-xs text-muted-foreground mt-1">
                                Shared on {format(new Date(link.createdAt), "MMM dd, yyyy")}
                              </p>
                            </div>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => deleteLinkMutation.mutate(link.id)}
                              disabled={deleteLinkMutation.isPending}
                              className="ml-2 h-8 w-8 p-0"
                              data-testid={`button-delete-link-${link.id}`}
                            >
                              <Trash2 className="w-3 h-3 text-destructive" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8 text-muted-foreground">
                      <BookOpen className="w-12 h-12 mx-auto mb-3 opacity-20" />
                      <p className="text-sm">You haven't shared any links yet</p>
                    </div>
                  )}
                </div>
              </>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

// 📈 Progress Charts with ECharts
function ProgressChartsSection({ progressOverTime, topicBreakdown, difficultyBreakdown }: { 
  progressOverTime: ProgressOverTime[]; 
  topicBreakdown: Record<string, number>;
  difficultyBreakdown: DifficultyBreakdown;
}) {
  // Prepare data for GitHub-style heatmap (last 365 days)
  const today = new Date();
  const startDate = subDays(today, 365);
  
  // Transform progress data for react-calendar-heatmap
  const heatmapValues = progressOverTime.map(p => ({
    date: p.date,
    count: p.solved_count
  }));

  // Prepare topic data for animated bar chart
  const topicData = Object.entries(topicBreakdown)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8);

  const topicChartOption = {
    title: {
      text: 'Topic Mastery 🎯',
      subtext: 'Problems Solved by Topic',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      }
    },
    xAxis: {
      type: 'category',
      data: topicData.map(t => t.name),
      axisLabel: {
        rotate: 45,
        fontSize: 10
      }
    },
    yAxis: {
      type: 'value',
      name: 'Problems Solved'
    },
    series: [{
      name: 'Solved',
      type: 'bar',
      data: topicData.map(t => t.value),
      itemStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: '#3b82f6' },
            { offset: 1, color: '#1e40af' }
          ]
        }
      },
      emphasis: {
        itemStyle: {
          color: '#fbbf24'
        }
      }
    }],
    animation: true,
    animationDuration: 1500,
    animationDelay: (idx: number) => idx * 100
  };

  // Prepare difficulty distribution pie chart - filter out zero values
  const difficultyData = Object.entries(difficultyBreakdown)
    .filter(([_, value]) => value > 0)  // Only show difficulties with solved problems
    .map(([name, value]) => ({
      name,
      value,
      itemStyle: {
        color: DIFFICULTY_COLORS[name as keyof typeof DIFFICULTY_COLORS]
      }
    }));

  const difficultyChartOption = {
    title: {
      text: 'Difficulty Split 💪',
      subtext: 'Distribution by Difficulty',
      left: 'center'
    },
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)'
    },
    series: [{
      name: 'Difficulty',
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '60%'],
      data: difficultyData,
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      },
      label: {
        show: true,
        formatter: '{b}: {c}'
      }
    }],
    animation: true,
    animationDuration: 2000
  };

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4 flex items-center space-x-2">
        <TrendingUp className="h-6 w-6 text-blue-500" />
        <span>📈 Progress Charts</span>
      </h2>
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        <Card data-testid="card-calendar-heatmap" className="col-span-1 lg:col-span-2 xl:col-span-3">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Flame className="h-5 w-5 text-orange-500" />
              <span>Questions Solved</span>
            </CardTitle>
            <CardDescription>Daily activity for the past year</CardDescription>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <CalendarHeatmap
              startDate={startDate}
              endDate={today}
              values={heatmapValues}
              classForValue={(value) => {
                if (!value || value.count === 0) {
                  return 'color-empty';
                }
                if (value.count <= 2) return 'color-scale-1';
                if (value.count <= 4) return 'color-scale-2';
                if (value.count <= 6) return 'color-scale-3';
                return 'color-scale-4';
              }}
              tooltipDataAttrs={(value: any) => {
                if (!value || !value.date) {
                  return {};
                }
                return {
                  'data-tooltip-id': 'heatmap-tooltip',
                  'data-tooltip-content': `${format(new Date(value.date), 'MMM dd, yyyy')}: ${value.count || 0} problems solved`,
                };
              }}
              showWeekdayLabels={true}
            />
            <ReactTooltip id="heatmap-tooltip" />
          </CardContent>
        </Card>
        
        <Card data-testid="card-topic-breakdown">
          <CardContent className="p-4">
            <ReactECharts 
              option={topicChartOption} 
              style={{ height: '300px' }}
              opts={{ renderer: 'canvas' }}
            />
          </CardContent>
        </Card>
        
        <Card data-testid="card-difficulty-breakdown">
          <CardContent className="p-4">
            {difficultyData.length > 0 ? (
              <ReactECharts 
                option={difficultyChartOption} 
                style={{ height: '300px' }}
                opts={{ renderer: 'canvas' }}
                notMerge={true}
                lazyUpdate={false}
              />
            ) : (
              <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <p className="text-lg">No problems solved yet</p>
                  <p className="text-sm">Start solving to see your difficulty breakdown</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// 📜 Competitive Recent Activity
function CompetitiveRecentActivity({ recentActivity }: { recentActivity: RecentActivity[] }) {
  return (
    <Card data-testid="card-recent-activity" className="border-2 border-blue-200 dark:border-blue-800">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Clock className="h-5 w-5" />
          <span>📜 Recent Activity</span>
        </CardTitle>
        <CardDescription>Latest victories and achievements</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {recentActivity.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground" data-testid="text-no-activity">
              <RocketIcon className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p>No recent races yet!</p>
              <p className="text-sm">Start solving to see your progress here</p>
            </div>
          ) : (
            recentActivity.map((activity, index) => (
              <div key={index} className="flex items-center justify-between p-4 rounded-lg border-2 bg-gradient-to-r from-green-50 to-blue-50 dark:from-green-900 dark:to-blue-900 border-green-200 dark:border-green-700" data-testid={`activity-${index}`}>
                <div className="flex items-center space-x-4">
                  <div className="h-10 w-10 rounded-full bg-green-500 flex items-center justify-center">
                    <Trophy className="h-5 w-5 text-white" />
                  </div>
                  <div className="flex-1">
                    <div className="font-medium flex items-center space-x-2">
                      <span>{activity.problem_title}</span>
                      <Badge variant="outline" className="text-xs">
                        ✅ Solved
                      </Badge>
                    </div>
                    <div className="text-sm text-muted-foreground flex items-center space-x-4">
                      <span>{format(new Date(activity.submitted_at), "MMM dd, yyyy 'at' h:mm a")}</span>
                      {activity.execution_time && (
                        <span className="flex items-center space-x-1">
                          <Zap className="h-3 w-3" />
                          <span>{activity.execution_time}ms</span>
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <Badge 
                    variant={activity.difficulty === "Easy" ? "secondary" : 
                             activity.difficulty === "Medium" ? "default" : "destructive"}
                    className="font-medium"
                  >
                    {activity.difficulty}
                  </Badge>
                  {/* Add competitive elements */}
                  {index === 0 && (
                    <Badge className="bg-yellow-500 text-white">
                      🔥 Latest Win!
                    </Badge>
                  )}
                </div>
              </div>
            ))
          )}
          
          {/* Add mock competitive updates */}
          {recentActivity.length > 0 && (
            <div className="pt-4 border-t">
              <h5 className="font-medium mb-2 text-sm text-muted-foreground">🏁 Race Updates</h5>
              <div className="space-y-2 text-sm">
                <div className="flex items-center space-x-2 text-green-600 dark:text-green-400">
                  <TrendingUp className="h-4 w-4" />
                  <span>You passed @sql_ninja yesterday! 🎉</span>
                </div>
                <div className="flex items-center space-x-2 text-blue-600 dark:text-blue-400">
                  <Star className="h-4 w-4" />
                  <span>New personal best: 2:43 solve time!</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function RecentActivityCard({ recentActivity }: { recentActivity: RecentActivity[] }) {
  return (
    <Card data-testid="card-recent-activity">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Clock className="h-5 w-5" />
          <span>Recent Activity</span>
        </CardTitle>
        <CardDescription>Last 5 problems solved</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {recentActivity.length === 0 ? (
            <div className="text-center py-4 text-muted-foreground" data-testid="text-no-activity">
              No recent activity found
            </div>
          ) : (
            recentActivity.map((activity, index) => (
              <div key={index} className="flex items-center justify-between p-3 rounded-lg border" data-testid={`activity-${index}`}>
                <div className="flex-1">
                  <div className="font-medium">{activity.problem_title}</div>
                  <div className="text-sm text-muted-foreground">
                    {format(new Date(activity.submitted_at), "MMM dd, yyyy 'at' h:mm a")}
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Badge 
                    variant={activity.difficulty === "Easy" ? "secondary" : 
                             activity.difficulty === "Medium" ? "default" : "destructive"}
                  >
                    {activity.difficulty}
                  </Badge>
                  {activity.execution_time && (
                    <div className="text-sm text-muted-foreground">
                      {activity.execution_time}ms
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}



function ProfileSkeleton() {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center space-x-4">
            <Skeleton className="h-20 w-20 rounded-full" />
            <div className="space-y-2">
              <Skeleton className="h-6 w-48" />
              <Skeleton className="h-4 w-64" />
              <Skeleton className="h-4 w-32" />
            </div>
          </div>
        </CardHeader>
      </Card>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {[...Array(4)].map((_, i) => (
          <Card key={i}>
            <CardHeader>
              <Skeleton className="h-6 w-32" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-64 w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

export default function Profile() {
  const { data: profile, isLoading: profileLoading } = useQuery<UserProfile>({
    queryKey: ["/api/user/profile"],
  });

  if (profileLoading) {
    return <ProfileSkeleton />;
  }

  if (!profile || !profile.success) {
    return (
      <div className="container mx-auto p-6">
        <Card>
          <CardContent className="py-8">
            <div className="text-center">
              <div className="text-lg font-medium">Unable to load profile</div>
              <div className="text-muted-foreground">Please try again later</div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-8" data-testid="page-profile">
      {/* 👤 Competitive User Information Header */}
      <CompetitiveUserHeader 
        basicInfo={profile.basic_info} 
        performanceStats={profile.performance_stats} 
      />

      {/* 🏆 Competitive Overview */}
      <CompetitiveOverview 
        stats={profile.performance_stats} 
        recentActivity={profile.recent_activity}
      />

      {/* 👥 Friends & Resources */}
      <FriendsAndResourcesSection userId={profile.basic_info.user_id} isPremium={profile.basic_info.premium} />

      {/* 📈 Progress Charts with ECharts */}
      <ProgressChartsSection 
        progressOverTime={profile.progress_over_time}
        topicBreakdown={profile.topic_breakdown}
        difficultyBreakdown={profile.difficulty_breakdown}
      />

      {/* 📜 Recent Activity */}
      <CompetitiveRecentActivity recentActivity={profile.recent_activity} />
    </div>
  );
}