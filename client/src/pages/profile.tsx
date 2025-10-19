import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useAuth } from "@/hooks/use-auth";
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
import { User, Trophy, Target, TrendingUp, Clock, Star, Award, BookOpen, Lightbulb, Users, Flag, Zap, Crown, Flame, Medal, Gauge, RocketIcon, Search, UserPlus, UserMinus, Pencil, Linkedin, Building, ExternalLink, Trash2, Loader2 } from "lucide-react";
import { format, subDays } from "date-fns";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogDescription } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { UserProfilePopover } from "@/components/UserProfilePopover";
import CalendarHeatmap from 'react-calendar-heatmap';
import 'react-calendar-heatmap/dist/styles.css';
import { Tooltip as ReactTooltip } from 'react-tooltip';

// ... (keep all existing interfaces - BasicInfo, PerformanceStats, etc.)
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
  total_problems_by_difficulty: DifficultyBreakdown;
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

// ============================================
// SIMPLE CLIENT-SIDE FUZZY SEARCH UTILITY
// ============================================
function fuzzyMatch(str: string, pattern: string): { matches: boolean; score: number } {
  str = str.toLowerCase();
  pattern = pattern.toLowerCase();

  let patternIdx = 0;
  let score = 0;
  let consecutiveMatches = 0;

  for (let i = 0; i < str.length && patternIdx < pattern.length; i++) {
    if (str[i] === pattern[patternIdx]) {
      score += 1 + consecutiveMatches;
      consecutiveMatches++;
      patternIdx++;
    } else {
      consecutiveMatches = 0;
    }
  }

  const matches = patternIdx === pattern.length;
  return { matches, score };
}

function searchUsers(users: FollowerUser[], query: string): FollowerUser[] {
  if (!query.trim()) return [];

  const results = users
    .map(user => {
      const searchableText = [
        user.username,
        user.firstName || '',
        user.lastName || '',
        user.companyName || ''
      ].join(' ');

      const { matches, score } = fuzzyMatch(searchableText, query);
      return { user, matches, score };
    })
    .filter(result => result.matches)
    .sort((a, b) => b.score - a.score)
    .slice(0, 10)
    .map(result => result.user);

  return results;
}

// ... (keep all existing components: EditProfileDialog, CompetitiveUserHeader, CompetitiveOverview, ProgressChartsSection, CompetitiveRecentActivity, RecentActivityCard, ProfileSkeleton)

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

          <div className="text-right space-y-2">
            <EditProfileDialog basicInfo={basicInfo} />
            <Badge variant={basicInfo.premium ? "default" : "secondary"} data-testid="badge-premium" className="block">
              {basicInfo.premium ? "Premium Racer 🏎️" : "Free Rider 🚗"}
            </Badge>
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
  const globalAvgAccuracy = allUsersStats?.avgAccuracy || 73;
  const top10PercentAverage = allUsersStats?.avgSolved || Math.ceil(userSolved * 1.5);

  const executionTimes = (recentActivity || [])
    .filter(a => a.execution_time !== null && a.execution_time > 0)
    .map(a => a.execution_time as number);

  const fastestTime = executionTimes.length > 0 ? Math.min(...executionTimes) : null;

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
          <span>Competitive Overview</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="text-center p-4 bg-blue-50 dark:bg-blue-950 rounded-lg" data-testid="stat-accuracy">
            <div className="text-3xl font-bold text-blue-600">{stats.accuracy_rate}%</div>
            <div className="text-sm text-muted-foreground mt-1">Accuracy Rate</div>
            <div className="text-xs mt-2">
              {stats.accuracy_rate > globalAvgAccuracy ? (
                <Badge variant="default" className="bg-green-500">
                  <TrendingUp className="h-3 w-3 mr-1" />
                  Above Average
                </Badge>
              ) : (
                <Badge variant="secondary">Below Average</Badge>
              )}
            </div>
          </div>

          <div className="text-center p-4 bg-green-50 dark:bg-green-950 rounded-lg" data-testid="stat-solved">
            <div className="text-3xl font-bold text-green-600">{userSolved}</div>
            <div className="text-sm text-muted-foreground mt-1">Problems Solved</div>
            <div className="text-xs mt-2">
              <Badge variant="secondary">
                Top 10%: {top10PercentAverage}
              </Badge>
            </div>
          </div>

          <div className="text-center p-4 bg-purple-50 dark:bg-purple-950 rounded-lg" data-testid="stat-fastest">
            <div className="text-3xl font-bold text-purple-600">
              {fastestTime ? formatTime(fastestTime) : 'N/A'}
            </div>
            <div className="text-sm text-muted-foreground mt-1">Fastest Time</div>
            <div className="text-xs mt-2">
              <Badge variant="secondary">
                <Zap className="h-3 w-3 mr-1" />
                Personal Best
              </Badge>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
// 📊 Progress Charts Section
function ProgressChartsSection({ progressOverTime, difficultyBreakdown, topicBreakdown }: {
  progressOverTime: ProgressOverTime[];
  difficultyBreakdown: DifficultyBreakdown;
  topicBreakdown: Record<string, number>;
}) {
  const chartData = progressOverTime.map(p => ({
    date: format(new Date(p.date), "MMM dd"),
    solved: p.solved_count
  }));

  const difficultyChartData = Object.entries(difficultyBreakdown).map(([difficulty, count]) => ({
    name: difficulty,
    value: count,
    itemStyle: { color: DIFFICULTY_COLORS[difficulty as keyof typeof DIFFICULTY_COLORS] }
  }));

  const topicChartData = Object.entries(topicBreakdown || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([topic, count]) => ({
      topic,
      count
    }));

  const progressChartOption = {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: chartData.map(d => d.date) },
    yAxis: { type: 'value' },
    series: [{
      data: chartData.map(d => d.solved),
      type: 'line',
      smooth: true,
      areaStyle: {}
    }]
  };

  const difficultyChartOption = {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: difficultyChartData,
      label: { formatter: '{b}: {c}' }
    }]
  };

  const topicChartOption = {
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: topicChartData.map(d => d.topic),
      axisLabel: { interval: 0, rotate: 30 }
    },
    yAxis: { type: 'value' },
    series: [{
      data: topicChartData.map(d => d.count),
      type: 'bar',
      itemStyle: { color: '#3b82f6' }
    }]
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Card data-testid="card-progress-chart">
        <CardHeader>
          <CardTitle>Progress Over Time</CardTitle>
        </CardHeader>
        <CardContent>
          <ReactECharts option={progressChartOption} style={{ height: '300px' }} />
        </CardContent>
      </Card>

      <Card data-testid="card-difficulty-breakdown">
        <CardHeader>
          <CardTitle>Difficulty Breakdown</CardTitle>
        </CardHeader>
        <CardContent>
          <ReactECharts option={difficultyChartOption} style={{ height: '300px' }} />
        </CardContent>
      </Card>

      <Card data-testid="card-topic-breakdown" className="lg:col-span-2">
        <CardHeader>
          <CardTitle>Top Topics</CardTitle>
        </CardHeader>
        <CardContent>
          <ReactECharts option={topicChartOption} style={{ height: '300px' }} />
        </CardContent>
      </Card>
    </div>
  );
}

// 🔥 Recent Activity with Competitive Styling
function CompetitiveRecentActivity({ recentActivity }: { recentActivity: RecentActivity[] }) {
  if (!recentActivity || recentActivity.length === 0) {
    return (
      <Card data-testid="card-recent-activity">
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">No recent activity</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card data-testid="card-recent-activity">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Flame className="h-5 w-5 text-orange-500" />
          <span>Recent Activity</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {recentActivity.map((activity, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-3 bg-muted/50 rounded-lg hover:bg-muted transition-colors"
              data-testid={`activity-${index}`}
            >
              <div className="flex items-center space-x-3">
                <Badge
                  className={`${
                    activity.difficulty === 'Easy' ? 'bg-green-500' :
                    activity.difficulty === 'Medium' ? 'bg-yellow-500' :
                    'bg-red-500'
                  }`}
                >
                  {activity.difficulty}
                </Badge>
                <span className="font-medium">{activity.problem_title}</span>
              </div>
              <div className="flex items-center space-x-3 text-sm text-muted-foreground">
                {activity.execution_time && (
                  <div className="flex items-center space-x-1">
                    <Zap className="h-4 w-4 text-yellow-500" />
                    <span>{activity.execution_time}ms</span>
                  </div>
                )}
                <Clock className="h-4 w-4" />
                <span>{format(new Date(activity.submitted_at), "MMM dd, yyyy")}</span>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ⏳ Profile Loading Skeleton
function ProfileSkeleton() {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <Skeleton className="h-32 w-full" />
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Skeleton className="h-48" />
        <Skeleton className="h-48" />
        <Skeleton className="h-48" />
      </div>
      <Skeleton className="h-96 w-full" />
    </div>
  );
}

// 🏁 Main Profile Component
export default function Profile() {
  const { user } = useAuth();

  const { data: profile, isLoading } = useQuery<UserProfile>({
    queryKey: ["/api/user/profile"],
    enabled: !!user,
  });

  if (isLoading) {
    return <ProfileSkeleton />;
  }

  if (!profile) {
    return (
      <div className="container mx-auto p-6">
        <Card>
          <CardContent className="p-6">
            <p>Unable to load profile data</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6" data-testid="profile-page">
      <CompetitiveUserHeader
        basicInfo={profile.basic_info}
        performanceStats={profile.performance_stats}
      />

      <CompetitiveOverview
        stats={profile.performance_stats}
        recentActivity={profile.recent_activity}
      />

      <ProgressChartsSection
        progressOverTime={profile.progress_over_time}
        difficultyBreakdown={profile.difficulty_breakdown}
        topicBreakdown={profile.topic_breakdown}
      />

      <CompetitiveRecentActivity recentActivity={profile.recent_activity} />
    </div>
  );
}
