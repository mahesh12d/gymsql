import { useQuery } from '@tanstack/react-query';
import { Play, TrendingUp, Users, Target, Building, ExternalLink, Link2 } from 'lucide-react';
import { Link } from 'wouter';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth } from '@/hooks/use-auth';
import { problemsApi } from '@/lib/auth';
import { DifficultyBadge } from '@/components/DifficultyBadge';
import { CompanyLogo } from '@/components/CompanyLogo';
import { useMemo } from 'react';

function getDynamicMessage(problemsSolved: number): { message: string; emoji: string } {
  if (problemsSolved === 0) {
    return {
      message: "Let's start your SQL training journey!",
      emoji: '🚀'
    };
  }
  
  if (problemsSolved < 5) {
    return {
      message: "You're off to a great start!",
      emoji: '🌱'
    };
  }
  
  if (problemsSolved < 10) {
    return {
      message: "Keep up the momentum!",
      emoji: '💪'
    };
  }
  
  if (problemsSolved < 25) {
    return {
      message: "You're making excellent progress!",
      emoji: '⭐'
    };
  }
  
  if (problemsSolved < 50) {
    return {
      message: "You're becoming a SQL athlete!",
      emoji: '🏃'
    };
  }
  
  if (problemsSolved < 100) {
    return {
      message: "Impressive dedication to SQL mastery!",
      emoji: '🔥'
    };
  }
  
  return {
    message: "You're a SQL champion!",
    emoji: '🏆'
  };
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

function HelpfulLinksSection() {
  const { data: links, isLoading } = useQuery<HelpfulLink[]>({
    queryKey: ['/api/helpful-links'],
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Link2 className="w-5 h-5 text-primary" />
          <span>Helpful Resources</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-16 bg-muted rounded-lg animate-pulse" />
            ))}
          </div>
        ) : links && links.length > 0 ? (
          <div className="space-y-3">
            {links.map((link) => (
              <div
                key={link.id}
                className="p-3 bg-muted/50 rounded-lg hover:bg-muted transition-colors"
                data-testid={`link-item-${link.id}`}
              >
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
                  by {link.user.firstName && link.user.lastName 
                    ? `${link.user.firstName} ${link.user.lastName}` 
                    : link.user.username}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <Link2 className="w-12 h-12 mx-auto mb-3 opacity-20" />
            <p className="text-sm">No helpful links yet</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function Home() {
  const { user } = useAuth();

  const { data: problems, isLoading: problemsLoading } = useQuery({
    queryKey: ['/api/problems'],
    queryFn: () => problemsApi.getAll(),
  });

  const recentProblems = problems?.slice(0, 3) || [];

  const bannerContent = useMemo(() => {
    const { message, emoji } = getDynamicMessage(user?.problemsSolved || 0);
    return { message, emoji };
  }, [user?.problemsSolved]);

  const displayName = useMemo(() => {
    if (user?.firstName && user?.lastName) {
      return `${user.firstName} ${user.lastName}`;
    }
    return user?.username || 'there';
  }, [user?.firstName, user?.lastName, user?.username]);

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-foreground mb-2">
            Welcome back, <span className="text-primary">{displayName}</span>! {bannerContent.emoji}
          </h1>
          <p className="text-xl text-muted-foreground">
            {bannerContent.message}
          </p>
          {user?.companyName && (
            <div className="flex items-center mt-2 text-muted-foreground">
              <Building className="h-4 w-4 mr-2" />
              <span className="text-sm">{user.companyName}</span>
            </div>
          )}
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
            <HelpfulLinksSection />
          </div>
        </div>
      </div>
    </div>
  );
}
