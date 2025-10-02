import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useToast } from "@/hooks/use-toast";
import { apiRequest, queryClient } from "@/lib/queryClient";
import ReactECharts from "echarts-for-react";
import { User, Trophy, Target, TrendingUp, Clock, Star, Award, BookOpen, Lightbulb, Users, Flag, Zap, Crown, Flame, Medal, Gauge, RocketIcon } from "lucide-react";
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
                  #{performanceStats.rank} / 10,000
                </span>
                <span className="text-sm text-muted-foreground">Global Rank</span>
              </div>
              
              <div className="flex items-center space-x-6 text-sm">
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
              </div>
            </div>
          </div>
          
          {/* Quick Stats Badge */}
          <div className="text-right">
            <Badge variant={basicInfo.premium ? "default" : "secondary"} data-testid="badge-premium" className="mb-2">
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
function CompetitiveOverview({ stats }: { stats: PerformanceStats }) {
  // Mock data for comparison with top 10% users
  const top10PercentAverage = 85;
  const leaderSolved = 150;
  const userSolved = stats.correct_submissions;
  const progressToLeader = Math.min(100, (userSolved / leaderSolved) * 100);

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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
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
              vs Global avg: 73%
            </div>
            <Badge variant={stats.accuracy_rate > 73 ? "default" : "secondary"}>
              {stats.accuracy_rate > 90 ? "Elite Precision 🎯" : stats.accuracy_rate > 73 ? "Above Average ⬆️" : "Keep Practicing 💪"}
            </Badge>
          </div>

          {/* Fastest Solve Time Record */}
          <div className="text-center p-4 bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900 dark:to-purple-800 rounded-lg" data-testid="stat-fastest-time">
            <div className="flex items-center justify-center space-x-2 mb-2">
              <Zap className="h-5 w-5 text-purple-600" />
              <span className="text-sm font-medium">Fastest Solve</span>
            </div>
            <div className="text-3xl font-bold text-purple-600">2:43</div>
            <div className="text-sm text-muted-foreground mb-2">
              Personal best 🏁
            </div>
            <Badge variant="outline" className="border-purple-600 text-purple-600">
              Lightning Fast ⚡
            </Badge>
          </div>

          {/* Head-to-Head Wins */}
          <div className="text-center p-4 bg-gradient-to-br from-orange-50 to-orange-100 dark:from-orange-900 dark:to-orange-800 rounded-lg" data-testid="stat-head-to-head">
            <div className="flex items-center justify-center space-x-2 mb-2">
              <Users className="h-5 w-5 text-orange-600" />
              <span className="text-sm font-medium">Head-to-Head</span>
            </div>
            <div className="text-3xl font-bold text-orange-600">12</div>
            <div className="text-sm text-muted-foreground mb-2">
              Wins this month
            </div>
            <Badge variant="outline" className="border-orange-600 text-orange-600">
              Champion Fighter 🥊
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}


// 📊 Leaderboard Comparison Section
function LeaderboardComparison({ stats }: { stats: PerformanceStats }) {
  const topicLeaderboards = [
    { topic: "Joins", userRank: 5, totalUsers: 1000 },
    { topic: "Window Functions", userRank: 12, totalUsers: 800 },
    { topic: "Subqueries", userRank: 8, totalUsers: 1200 },
    { topic: "Aggregations", userRank: 3, totalUsers: 900 }
  ];

  return (
    <Card data-testid="card-leaderboard-comparison" className="border-2 border-green-200 dark:border-green-800">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Users className="h-6 w-6 text-green-500" />
          <span>📊 Topic Leaderboards</span>
        </CardTitle>
        <CardDescription>How you rank by topic</CardDescription>
      </CardHeader>
      <CardContent>
        <div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {topicLeaderboards.map((topic, index) => (
              <div key={index} className="p-3 bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900 dark:to-pink-900 rounded-lg" data-testid={`topic-rank-${index}`}>
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">{topic.topic}</span>
                  <Badge variant="outline" className={topic.userRank <= 5 ? 'border-green-500 text-green-600' : topic.userRank <= 20 ? 'border-yellow-500 text-yellow-600' : 'border-gray-500 text-gray-600'}>
                    #{topic.userRank}
                  </Badge>
                </div>
                <div className="text-sm text-muted-foreground">
                  You're #{topic.userRank} out of {topic.totalUsers.toLocaleString()} users
                </div>
                <Progress value={(1 - topic.userRank / topic.totalUsers) * 100} className="mt-2" />
              </div>
            ))}
          </div>
        </div>
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
  // Prepare data for solved questions over time (race speed)
  const solvedOverTimeOption = {
    title: {
      text: 'Your Speed 🏁',
      subtext: 'Solved Questions Over Time',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const data = params[0];
        return `${data.name}<br/>Problems Solved: ${data.value}`;
      }
    },
    xAxis: {
      type: 'category',
      data: progressOverTime.map(p => format(new Date(p.date), "MMM dd")),
      axisLabel: {
        rotate: 45
      }
    },
    yAxis: {
      type: 'value',
      name: 'Problems Solved'
    },
    series: [{
      name: 'Solved',
      type: 'line',
      data: progressOverTime.map(p => p.solved_count),
      smooth: true,
      lineStyle: {
        color: '#10b981',
        width: 3
      },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(16, 185, 129, 0.3)' },
            { offset: 1, color: 'rgba(16, 185, 129, 0.1)' }
          ]
        }
      },
      symbol: 'circle',
      symbolSize: 8,
      itemStyle: {
        color: '#10b981'
      }
    }],
    animation: true,
    animationDuration: 2000
  };

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

  // Prepare difficulty distribution pie chart
  const difficultyData = Object.entries(difficultyBreakdown).map(([name, value]) => ({
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
        <Card data-testid="card-progress-over-time">
          <CardContent className="p-4">
            <ReactECharts 
              option={solvedOverTimeOption} 
              style={{ height: '300px' }}
              opts={{ renderer: 'canvas' }}
            />
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
            <ReactECharts 
              option={difficultyChartOption} 
              style={{ height: '300px' }}
              opts={{ renderer: 'canvas' }}
            />
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
    <div className="container mx-auto p-6 space-y-8" data-testid="page-profile">
      {/* 👤 Competitive User Information Header */}
      <CompetitiveUserHeader 
        basicInfo={profile.basic_info} 
        performanceStats={profile.performance_stats} 
      />

      {/* 🏆 Competitive Overview */}
      <CompetitiveOverview stats={profile.performance_stats} />

      {/* 📊 Leaderboard Comparison */}
      <LeaderboardComparison stats={profile.performance_stats} />



      {/* 📈 Progress Charts with ECharts */}
      <ProgressChartsSection 
        progressOverTime={profile.progress_over_time}
        topicBreakdown={profile.topic_breakdown}
        difficultyBreakdown={profile.difficulty_breakdown}
      />

      {/* 📜 Recent Activity */}
      <CompetitiveRecentActivity recentActivity={profile.recent_activity} />

      {/* Recommendations */}
      <RecommendationsCard recommendations={recommendations} />
    </div>
  );
}