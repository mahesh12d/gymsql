import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, LineChart, Line, ResponsiveContainer } from "recharts";
import { User, Trophy, Target, TrendingUp, Clock, Star, Award, BookOpen, Lightbulb } from "lucide-react";
import { format } from "date-fns";

interface BasicInfo {
  user_id: string;
  username: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
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

interface WeakTopic {
  topic: string;
  solved_count: number;
  recommendation: string;
}

interface RecommendedProblem {
  id: string;
  title: string;
  difficulty: string;
  tags: string[];
  company: string | null;
}

interface Recommendations {
  success: boolean;
  weak_topics: WeakTopic[];
  recommended_difficulty: string;
  recommended_problems: RecommendedProblem[];
  learning_path: string;
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

function ProfileHeader({ basicInfo, performanceStats }: { basicInfo: BasicInfo; performanceStats: PerformanceStats }) {
  const displayName = basicInfo.first_name && basicInfo.last_name 
    ? `${basicInfo.first_name} ${basicInfo.last_name}`
    : basicInfo.username;

  return (
    <Card data-testid="profile-header">
      <CardHeader>
        <div className="flex items-center space-x-4">
          <Avatar className="h-20 w-20" data-testid="avatar-profile">
            <AvatarImage src={basicInfo.profile_image_url || undefined} />
            <AvatarFallback className="text-lg">
              {displayName.charAt(0).toUpperCase()}
            </AvatarFallback>
          </Avatar>
          <div className="flex-1">
            <CardTitle className="text-2xl" data-testid="text-username">{displayName}</CardTitle>
            <CardDescription data-testid="text-email">{basicInfo.email}</CardDescription>
            <div className="flex items-center space-x-4 mt-2">
              <Badge variant={basicInfo.premium ? "default" : "secondary"} data-testid="badge-premium">
                {basicInfo.premium ? "Premium" : "Free"}
              </Badge>
              <div className="flex items-center space-x-1" data-testid="text-rank">
                <Trophy className="h-4 w-4 text-yellow-500" />
                <span className="text-sm font-medium">Rank #{performanceStats.rank}</span>
              </div>
              <div className="flex items-center space-x-1" data-testid="text-joined">
                <User className="h-4 w-4" />
                <span className="text-sm text-muted-foreground">
                  Joined {format(new Date(basicInfo.created_at), "MMM yyyy")}
                </span>
              </div>
            </div>
          </div>
        </div>
      </CardHeader>
    </Card>
  );
}

function PerformanceStatsCard({ stats }: { stats: PerformanceStats }) {
  return (
    <Card data-testid="card-performance">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <TrendingUp className="h-5 w-5" />
          <span>Performance Stats</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div className="text-center" data-testid="stat-solved">
            <div className="text-2xl font-bold text-primary">{stats.correct_submissions}</div>
            <div className="text-sm text-muted-foreground">Problems Solved</div>
          </div>
          <div className="text-center" data-testid="stat-accuracy">
            <div className="text-2xl font-bold text-green-600">{stats.accuracy_rate}%</div>
            <div className="text-sm text-muted-foreground">Accuracy Rate</div>
          </div>
          <div className="text-center" data-testid="stat-current-streak">
            <div className="text-2xl font-bold text-orange-500">{stats.current_streak}</div>
            <div className="text-sm text-muted-foreground">Current Streak</div>
          </div>
          <div className="text-center" data-testid="stat-longest-streak">
            <div className="text-2xl font-bold text-purple-600">{stats.longest_streak}</div>
            <div className="text-sm text-muted-foreground">Longest Streak</div>
          </div>
          <div className="text-center" data-testid="stat-submissions">
            <div className="text-2xl font-bold text-blue-600">{stats.total_submissions}</div>
            <div className="text-sm text-muted-foreground">Total Submissions</div>
          </div>
          <div className="text-center" data-testid="stat-rank">
            <div className="text-2xl font-bold text-yellow-600">#{stats.rank}</div>
            <div className="text-sm text-muted-foreground">Global Rank</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function DifficultyChart({ difficultyBreakdown }: { difficultyBreakdown: DifficultyBreakdown }) {
  const data = Object.entries(difficultyBreakdown).map(([key, value]) => ({
    name: key,
    value,
    color: DIFFICULTY_COLORS[key as keyof typeof DIFFICULTY_COLORS]
  }));

  const total = data.reduce((sum, entry) => sum + entry.value, 0);

  return (
    <Card data-testid="card-difficulty-chart">
      <CardHeader>
        <CardTitle>By Difficulty</CardTitle>
        <CardDescription>Distribution of solved problems</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={5}
                dataKey="value"
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip formatter={(value: number) => [value, "Problems"]} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="grid grid-cols-3 gap-4 mt-4">
          {data.map((entry) => (
            <div key={entry.name} className="text-center" data-testid={`difficulty-${entry.name.toLowerCase()}`}>
              <div className="flex items-center justify-center space-x-2">
                <div 
                  className="w-3 h-3 rounded-full" 
                  style={{ backgroundColor: entry.color }}
                />
                <span className="text-sm font-medium">{entry.name}</span>
              </div>
              <div className="text-lg font-bold">{entry.value}</div>
              <div className="text-xs text-muted-foreground">
                {total > 0 ? Math.round((entry.value / total) * 100) : 0}%
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function TopicChart({ topicBreakdown }: { topicBreakdown: Record<string, number> }) {
  const data = Object.entries(topicBreakdown)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8); // Show top 8 topics

  return (
    <Card data-testid="card-topic-chart">
      <CardHeader>
        <CardTitle>By Topic</CardTitle>
        <CardDescription>Problems solved per topic</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="name" 
                angle={-45}
                textAnchor="end"
                height={60}
                fontSize={12}
              />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" fill="#3b82f6" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

function ProgressChart({ progressOverTime }: { progressOverTime: ProgressOverTime[] }) {
  return (
    <Card data-testid="card-progress-chart">
      <CardHeader>
        <CardTitle>Over Time</CardTitle>
        <CardDescription>Problems solved in the last 30 days</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={progressOverTime} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="date" 
                tickFormatter={(value) => format(new Date(value), "MMM dd")}
              />
              <YAxis />
              <Tooltip 
                labelFormatter={(value) => format(new Date(value), "MMM dd, yyyy")}
                formatter={(value: number) => [value, "Problems Solved"]}
              />
              <Line 
                type="monotone" 
                dataKey="solved_count" 
                stroke="#10b981" 
                strokeWidth={2}
                dot={{ fill: "#10b981", strokeWidth: 2, r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
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

function BadgesCard({ badges }: { badges: UserBadge[] }) {
  return (
    <Card data-testid="card-badges">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Award className="h-5 w-5" />
          <span>Achievements</span>
        </CardTitle>
        <CardDescription>Badges and milestones unlocked</CardDescription>
      </CardHeader>
      <CardContent>
        {badges.length === 0 ? (
          <div className="text-center py-4 text-muted-foreground" data-testid="text-no-badges">
            No badges earned yet. Keep solving problems to unlock achievements!
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {badges.map((badge) => (
              <div key={badge.id} className="flex items-center space-x-3 p-3 rounded-lg border" data-testid={`badge-${badge.id}`}>
                <div className="flex-shrink-0">
                  {badge.icon_url ? (
                    <img src={badge.icon_url} alt={badge.name} className="w-8 h-8" />
                  ) : (
                    <Star className="h-8 w-8 text-yellow-500" />
                  )}
                </div>
                <div className="flex-1">
                  <div className="font-medium">{badge.name}</div>
                  <div className="text-sm text-muted-foreground">{badge.description}</div>
                  <div className="flex items-center space-x-2 mt-1">
                    <Badge 
                      style={{ 
                        backgroundColor: RARITY_COLORS[badge.rarity as keyof typeof RARITY_COLORS] || RARITY_COLORS.common,
                        color: "white"
                      }}
                    >
                      {badge.rarity}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {format(new Date(badge.earned_at), "MMM yyyy")}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function RecommendationsCard({ recommendations }: { recommendations: Recommendations | undefined }) {
  if (!recommendations) return null;

  return (
    <Card data-testid="card-recommendations">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Lightbulb className="h-5 w-5" />
          <span>Recommendations</span>
        </CardTitle>
        <CardDescription>Personalized suggestions for improvement</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Learning Path */}
        <div data-testid="learning-path">
          <h4 className="font-medium mb-2">🎯 Your Learning Path</h4>
          <p className="text-sm text-muted-foreground">{recommendations.learning_path}</p>
        </div>

        <Separator />

        {/* Weak Topics */}
        {recommendations.weak_topics.length > 0 && (
          <div data-testid="weak-topics">
            <h4 className="font-medium mb-3">📚 Areas for Improvement</h4>
            <div className="space-y-2">
              {recommendations.weak_topics.map((topic, index) => (
                <div key={index} className="flex items-center justify-between p-2 rounded border" data-testid={`weak-topic-${index}`}>
                  <div>
                    <span className="font-medium">{topic.topic}</span>
                    <div className="text-sm text-muted-foreground">{topic.recommendation}</div>
                  </div>
                  <Badge variant="outline">{topic.solved_count} solved</Badge>
                </div>
              ))}
            </div>
          </div>
        )}

        <Separator />

        {/* Recommended Problems */}
        {recommendations.recommended_problems.length > 0 && (
          <div data-testid="recommended-problems">
            <h4 className="font-medium mb-3">💡 Recommended Problems</h4>
            <div className="space-y-2">
              {recommendations.recommended_problems.map((problem) => (
                <div key={problem.id} className="flex items-center justify-between p-2 rounded border" data-testid={`recommended-problem-${problem.id}`}>
                  <div className="flex-1">
                    <div className="font-medium">{problem.title}</div>
                    {problem.company && (
                      <div className="text-sm text-muted-foreground">{problem.company}</div>
                    )}
                    {problem.tags && problem.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {problem.tags.slice(0, 3).map((tag, index) => (
                          <Badge key={index} variant="outline" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                  <Badge 
                    variant={problem.difficulty === "Easy" ? "secondary" : 
                             problem.difficulty === "Medium" ? "default" : "destructive"}
                  >
                    {problem.difficulty}
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        )}
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

  const { data: recommendations } = useQuery<Recommendations>({
    queryKey: ["/api/user/profile/recommendations"],
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
    <div className="container mx-auto p-6 space-y-6" data-testid="page-profile">
      {/* Profile Header */}
      <ProfileHeader 
        basicInfo={profile.basic_info} 
        performanceStats={profile.performance_stats} 
      />

      {/* Performance Stats */}
      <PerformanceStatsCard stats={profile.performance_stats} />

      {/* Visual Insights */}
      <div>
        <h2 className="text-2xl font-bold mb-4">📊 Visual Insights</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
          <DifficultyChart difficultyBreakdown={profile.difficulty_breakdown} />
          <TopicChart topicBreakdown={profile.topic_breakdown} />
          <ProgressChart progressOverTime={profile.progress_over_time} />
        </div>
      </div>

      {/* Recent Activity and Badges */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RecentActivityCard recentActivity={profile.recent_activity} />
        <BadgesCard badges={profile.badges} />
      </div>

      {/* Recommendations */}
      <RecommendationsCard recommendations={recommendations} />
    </div>
  );
}