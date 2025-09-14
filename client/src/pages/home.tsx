import { useQuery } from '@tanstack/react-query';
import { Play, TrendingUp, Users, Target } from 'lucide-react';
import { Link } from 'wouter';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth } from '@/hooks/use-auth';
import { problemsApi, leaderboardApi } from '@/lib/auth';
import { DifficultyBadge } from '@/components/DifficultyBadge';
import { CompanyLogo } from '@/components/CompanyLogo';

export default function Home() {
  const { user } = useAuth();

  const { data: problems, isLoading: problemsLoading } = useQuery({
    queryKey: ['/api/problems'],
    queryFn: () => problemsApi.getAll(),
  });

  const { data: leaderboard, isLoading: leaderboardLoading } = useQuery({
    queryKey: ['/api/leaderboard'],
    queryFn: () => leaderboardApi.get(5),
  });



  const recentProblems = problems?.slice(0, 3) || [];
  const topUsers = leaderboard?.slice(0, 3) || [];

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-foreground mb-2">
            Welcome back, <span className="text-primary">{user?.username}</span>! 💪
          </h1>
          <p className="text-xl text-muted-foreground">
            Ready to continue your SQL training journey?
          </p>
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-8">
            {/* Progress Overview */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <TrendingUp className="w-5 h-5 text-primary" />
                  <span>Your Progress</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="text-center">
                  <div className="text-3xl font-bold text-green-600">{user?.problemsSolved || 0}</div>
                  <div className="text-sm text-muted-foreground">Problems Solved</div>
                  <p className="text-sm text-muted-foreground mt-2">Keep solving problems to improve your skills!</p>
                </div>
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Target className="w-5 h-5 text-primary" />
                  <span>Quick Actions</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-2 gap-4">
                  <Link href="/problems">
                    <Button 
                      className="w-full dumbbell-btn bg-primary text-primary-foreground hover:bg-primary/90 h-16"
                      data-testid="button-browse-problems"
                    >
                      <Play className="mr-2 h-5 w-5" />
                      <div className="text-left">
                        <div className="font-semibold">Browse Problems</div>
                        <div className="text-sm opacity-90">Find your next challenge</div>
                      </div>
                    </Button>
                  </Link>
                  
                  <Link href="/community">
                    <Button 
                      variant="outline" 
                      className="w-full h-16"
                      data-testid="button-join-community"
                    >
                      <Users className="mr-2 h-5 w-5" />
                      <div className="text-left">
                        <div className="font-semibold">Join Community</div>
                        <div className="text-sm opacity-70">Share and learn together</div>
                      </div>
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>

            {/* Recent Problems */}
            <Card>
              <CardHeader>
                <div className="flex justify-between items-center">
                  <CardTitle>Recommended Problems</CardTitle>
                  <Link href="/problems">
                    <Button variant="ghost" size="sm" data-testid="link-view-all-problems">
                      View All
                    </Button>
                  </Link>
                </div>
              </CardHeader>
              <CardContent>
                {problemsLoading ? (
                  <div className="space-y-4">
                    {[...Array(3)].map((_, i) => (
                      <div key={i} className="h-20 bg-muted rounded-lg animate-pulse" />
                    ))}
                  </div>
                ) : (
                  <div className="space-y-4">
                    {recentProblems.map((problem) => (
                      <Link key={problem.id} href={`/problems/${problem.id}`}>
                        <Card className="hover:shadow-md transition-shadow cursor-pointer" data-testid={`card-problem-${problem.id}`}>
                          <CardContent className="p-4">
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <h3 className="font-semibold text-foreground mb-2">{problem.title}</h3>
                                <p className="text-sm text-muted-foreground line-clamp-2">
                                  {problem.description}
                                </p>
                              </div>
                              <div className="ml-4">
                                <DifficultyBadge
                                  difficulty={problem.difficulty}
                                  variant="badge"
                                  size="sm"
                                  showIcon={true}
                                  data-testid={`difficulty-badge-home-${problem.id}`}
                                />
                              </div>
                            </div>
                            <div className="flex items-center justify-between mt-3">
                              <div className="flex items-center space-x-4">
                                {problem.company && (
                                  <CompanyLogo
                                    companyName={problem.company}
                                    variant="minimal"
                                    size="sm"
                                    data-testid={`company-logo-home-${problem.id}`}
                                  />
                                )}
                                <span className="text-xs text-muted-foreground">
                                  {problem.solvedCount} solved
                                </span>
                              </div>
                              <Button size="sm" variant="ghost" className="text-primary">
                                Start Training →
                              </Button>
                            </div>
                          </CardContent>
                        </Card>
                      </Link>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">

            {/* Leaderboard Preview */}
            <Card>
              <CardHeader>
                <div className="flex justify-between items-center">
                  <CardTitle>Top Athletes</CardTitle>
                  <Link href="/leaderboard">
                    <Button variant="ghost" size="sm" data-testid="link-view-leaderboard">
                      View All
                    </Button>
                  </Link>
                </div>
              </CardHeader>
              <CardContent>
                {leaderboardLoading ? (
                  <div className="space-y-3">
                    {[...Array(3)].map((_, i) => (
                      <div key={i} className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-muted rounded-full" />
                        <div className="flex-1 space-y-1">
                          <div className="h-4 bg-muted rounded w-3/4" />
                          <div className="h-3 bg-muted rounded w-1/2" />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="space-y-3">
                    {topUsers.map((topUser, index) => (
                      <div key={topUser.id} className="flex items-center space-x-3" data-testid={`user-rank-${index + 1}`}>
                        <div className="w-10 h-10 bg-primary text-primary-foreground rounded-full flex items-center justify-center font-bold text-sm">
                          {index + 1}
                        </div>
                        <div className="flex-1">
                          <div className="font-medium text-foreground">{topUser.username}</div>
                          <div className="text-sm text-muted-foreground">{topUser.problemsSolved} problems solved</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

          </div>
        </div>
      </div>
    </div>
  );
}
