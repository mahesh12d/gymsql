import { useQuery } from '@tanstack/react-query';
import { Play, CheckCircle, Trophy } from 'lucide-react';
import { Link } from 'wouter';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { useAuth } from '@/hooks/use-auth';
import { problemsApi } from '@/lib/auth';
import ProgressBar from '@/components/progress-bar';

function getLevelInfo(problemsSolved: number): { level: string; color: string } {
  if (problemsSolved >= 50) return { level: 'Senior Developer', color: 'text-purple-600' };
  if (problemsSolved >= 25) return { level: 'Mid-Level Developer', color: 'text-blue-600' };
  if (problemsSolved >= 10) return { level: 'Junior Developer', color: 'text-green-600' };
  return { level: 'Beginner', color: 'text-gray-600' };
}

export default function Home() {
  const { user } = useAuth();

  const { data: problems } = useQuery({
    queryKey: ['/api/problems'],
    queryFn: () => problemsApi.getAll(),
  });

  const totalProblems = problems?.length || 100;
  const problemsSolved = user?.problemsSolved || 0;
  const progressPercentage = Math.round((problemsSolved / totalProblems) * 100);
  const levelInfo = getLevelInfo(problemsSolved);

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Section */}
      <section className="bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            {/* Left Column - Content */}
            <div className="space-y-8">
              <div>
                <h1 className="text-5xl font-bold text-foreground leading-tight">
                  Master <span className="text-primary">SQL Skills</span> for
                  Interviews & Work
                </h1>
                <p className="text-xl text-muted-foreground mt-6 leading-relaxed">
                  Practice SQL with real-world problems designed for interviews
                  and professional development. Progress from Junior to Senior
                  level with our comprehensive platform.
                </p>
              </div>

              {/* Progress Card */}
              <Card className="p-6 border-2">
                <h3 className="font-semibold text-foreground mb-4 text-lg">
                  Your Progress
                </h3>
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm mb-2">
                    <span className="text-muted-foreground">Progress</span>
                    <span className="font-semibold text-foreground">{progressPercentage}%</span>
                  </div>
                  <ProgressBar value={problemsSolved} max={totalProblems} showText={false} />
                </div>
              </Card>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-4">
                <Link href="/problems">
                  <Button
                    size="lg"
                    className="w-full sm:w-auto bg-primary text-primary-foreground px-8 py-6 text-lg hover:bg-primary/90"
                    data-testid="button-start-practicing"
                  >
                    <Play className="mr-3 h-5 w-5" />
                    Start Practicing
                  </Button>
                </Link>
              </div>
            </div>

            {/* Right Column - Image with Floating Cards */}
            <div className="relative">
              <img
                src="https://images.unsplash.com/photo-1517077304055-6e89abbf09b0?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&h=600"
                alt="Professional coding workspace"
                className="rounded-xl shadow-2xl w-full"
              />

              {/* Floating achievement card - Top Right */}
              <Card className="absolute -top-4 -right-4 p-4 shadow-lg bg-white">
                <div className="flex items-center space-x-3">
                  <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center">
                    <Trophy className={`${levelInfo.color} text-xl`} />
                  </div>
                  <div>
                    <p className="font-semibold text-foreground">
                      {levelInfo.level}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Level Achieved!
                    </p>
                  </div>
                </div>
              </Card>

              {/* Floating achievement card - Bottom Left */}
              <Card className="absolute -bottom-4 -left-4 p-4 shadow-lg bg-white">
                <div className="flex items-center space-x-3">
                  <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                    <CheckCircle className="text-green-600 text-xl" />
                  </div>
                  <div>
                    <p className="font-semibold text-foreground">
                      Problem Solved!
                    </p>
                    <p className="text-sm text-muted-foreground">
                      +50 XP Gained
                    </p>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="bg-muted/30 py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-3 gap-8 text-center">
            <div>
              <div className="text-4xl font-bold text-primary mb-2">{problemsSolved}</div>
              <div className="text-muted-foreground">Problems Solved</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-primary mb-2">{user?.xp || 0}</div>
              <div className="text-muted-foreground">Total XP</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-primary mb-2">{levelInfo.level.split(' ')[0]}</div>
              <div className="text-muted-foreground">Current Level</div>
            </div>
          </div>
        </div>
      </section>

      {/* Quick Actions Section */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-foreground mb-8 text-center">
            Continue Your Journey
          </h2>
          <div className="grid md:grid-cols-3 gap-6">
            <Link href="/problems">
              <Card className="p-6 hover:shadow-lg transition-shadow cursor-pointer border-2">
                <div className="text-center">
                  <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Play className="w-8 h-8 text-primary" />
                  </div>
                  <h3 className="font-semibold text-foreground mb-2 text-lg">
                    Browse Problems
                  </h3>
                  <p className="text-muted-foreground text-sm">
                    Explore {totalProblems}+ SQL challenges
                  </p>
                </div>
              </Card>
            </Link>

            <Link href="/leaderboard">
              <Card className="p-6 hover:shadow-lg transition-shadow cursor-pointer border-2">
                <div className="text-center">
                  <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Trophy className="w-8 h-8 text-yellow-600" />
                  </div>
                  <h3 className="font-semibold text-foreground mb-2 text-lg">
                    Leaderboard
                  </h3>
                  <p className="text-muted-foreground text-sm">
                    See where you rank globally
                  </p>
                </div>
              </Card>
            </Link>

            <Link href="/community">
              <Card className="p-6 hover:shadow-lg transition-shadow cursor-pointer border-2">
                <div className="text-center">
                  <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <CheckCircle className="w-8 h-8 text-green-600" />
                  </div>
                  <h3 className="font-semibold text-foreground mb-2 text-lg">
                    Join Community
                  </h3>
                  <p className="text-muted-foreground text-sm">
                    Share solutions and learn together
                  </p>
                </div>
              </Card>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
