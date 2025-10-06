import { useQuery } from '@tanstack/react-query';
import { Play, Users } from 'lucide-react';
import { Link } from 'wouter';
import { Button } from '@/components/ui/button';
import { useAuth } from '@/hooks/use-auth';
import { problemsApi } from '@/lib/auth';
import ProgressBar from '@/components/progress-bar';
import { useMemo } from 'react';

export default function Home() {
  const { user } = useAuth();

  const { data: problems } = useQuery({
    queryKey: ['/api/problems'],
    queryFn: () => problemsApi.getAll(),
  });

  const progressPercentage = useMemo(() => {
    const total = problems?.length || 100;
    const solved = user?.problemsSolved || 0;
    return Math.round((solved / total) * 100);
  }, [problems?.length, user?.problemsSolved]);

  const displayName = useMemo(() => {
    if (user?.firstName && user?.lastName) {
      return `${user.firstName} ${user.lastName}`;
    }
    return user?.username || 'there';
  }, [user?.firstName, user?.lastName, user?.username]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-pink-400 via-orange-300 to-yellow-300 relative overflow-hidden">
      {/* Gradient decorations */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-pink-500 to-orange-400 rounded-full blur-3xl opacity-30 -mr-48 -mt-48" />
      <div className="absolute bottom-0 left-0 w-96 h-96 bg-gradient-to-tr from-green-400 to-cyan-300 rounded-full blur-3xl opacity-30 -ml-48 -mb-48" />
      <div className="absolute bottom-20 right-20 w-64 h-64 bg-gradient-to-tr from-yellow-300 to-green-400 rounded-full blur-3xl opacity-20" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="bg-white rounded-3xl shadow-2xl p-8 md:p-12 lg:p-16 relative overflow-hidden">
          {/* Content Container */}
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            {/* Left Content */}
            <div className="space-y-8">
              <div>
                <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-gray-900 leading-tight mb-4">
                  Master <span className="text-transparent bg-clip-text bg-gradient-to-r from-pink-500 to-orange-500">SQL Skills</span> for
                  <br />
                  Interviews & Work
                </h1>
                <p className="text-gray-600 text-lg leading-relaxed">
                  Practice SQL with real-world problems designed for interviews and professional development. 
                  Progress from Junior to Senior level with our comprehensive platform.
                </p>
              </div>

              {/* Your Progress Card */}
              <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-2xl p-6 border-2 border-dashed border-gray-300">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Your Progress</h3>
                <div className="mb-2 flex justify-between items-center">
                  <span className="text-sm text-gray-600">Week</span>
                  <span className="text-sm font-semibold text-gray-900">{progressPercentage}%</span>
                </div>
                <ProgressBar value={user?.problemsSolved || 0} max={problems?.length || 100} />
                <div className="mt-3 flex items-center space-x-2">
                  <div className="w-6 h-6 bg-gradient-to-br from-red-500 to-orange-500 rounded flex items-center justify-center">
                    <span className="text-white text-xs font-bold">S</span>
                  </div>
                  <span className="text-sm font-medium text-gray-700">
                    {user?.problemsSolved || 0}/{problems?.length || 0} completed
                  </span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-4">
                <Link href="/problems">
                  <Button
                    size="lg"
                    className="w-full sm:w-auto bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white px-8 py-6 rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 text-lg font-semibold"
                    data-testid="button-start-practicing"
                  >
                    <Play className="mr-2 h-5 w-5 fill-current" />
                    Start Practicing
                  </Button>
                </Link>

                <Link href="/community">
                  <Button
                    size="lg"
                    variant="outline"
                    className="w-full sm:w-auto border-2 border-gray-300 hover:border-gray-400 px-8 py-6 rounded-xl text-lg font-semibold transition-all duration-200"
                    data-testid="button-join-community"
                  >
                    <Users className="mr-2 h-5 w-5" />
                    Join Community
                  </Button>
                </Link>
              </div>
            </div>

            {/* Right Content - Illustration Area */}
            <div className="relative hidden lg:block">
              <div className="relative w-full h-[500px] flex items-center justify-center">
                {/* Isometric Platform Illustration */}
                <div className="relative w-full h-full">
                  {/* Achievement Badge 1 */}
                  <div className="absolute top-8 right-12 bg-white rounded-2xl shadow-lg p-4 border-2 border-purple-200 transform rotate-3 hover:rotate-0 transition-transform">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-gradient-to-br from-purple-400 to-purple-600 rounded-full flex items-center justify-center">
                        <span className="text-white text-xl">🏆</span>
                      </div>
                      <div>
                        <p className="text-sm font-bold text-gray-900">Senior Developer</p>
                        <p className="text-xs text-gray-600">Level Achieved!</p>
                      </div>
                    </div>
                  </div>

                  {/* Achievement Badge 2 */}
                  <div className="absolute bottom-24 left-8 bg-white rounded-2xl shadow-lg p-4 border-2 border-green-200 transform -rotate-3 hover:rotate-0 transition-transform">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-gradient-to-br from-green-400 to-green-600 rounded-full flex items-center justify-center">
                        <span className="text-white text-xl">✓</span>
                      </div>
                      <div>
                        <p className="text-sm font-bold text-gray-900">Problem Solved!</p>
                        <p className="text-xs text-gray-600">+50 XP Gained</p>
                      </div>
                    </div>
                  </div>

                  {/* Central Illustration Placeholder */}
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="relative w-80 h-80">
                      {/* Platform layers with gradient backgrounds */}
                      <div className="absolute bottom-0 w-full h-48 bg-gradient-to-br from-purple-200 to-purple-300 rounded-2xl transform perspective-1000 rotate-y-12" />
                      <div className="absolute bottom-12 left-8 w-56 h-40 bg-gradient-to-br from-cyan-200 to-cyan-300 rounded-2xl transform perspective-1000 rotate-y-12" />
                      <div className="absolute bottom-24 right-8 w-48 h-32 bg-gradient-to-br from-pink-200 to-pink-300 rounded-2xl transform perspective-1000 rotate-y-12" />
                      
                      {/* Decorative elements */}
                      <div className="absolute top-8 right-12 w-16 h-16 bg-gradient-to-br from-yellow-300 to-yellow-400 rounded-full shadow-lg flex items-center justify-center text-2xl">
                        🌍
                      </div>
                      <div className="absolute top-20 left-8 w-12 h-12 bg-gradient-to-br from-green-300 to-green-400 rounded-lg shadow-lg flex items-center justify-center text-xl">
                        🌳
                      </div>
                      <div className="absolute bottom-32 right-4 w-14 h-14 bg-gradient-to-br from-orange-300 to-orange-400 rounded-full shadow-lg flex items-center justify-center text-2xl">
                        💰
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Bottom Stats Bar */}
          <div className="mt-12 pt-8 border-t border-gray-200">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
              <div>
                <div className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-pink-500 to-orange-500">
                  {user?.problemsSolved || 0}
                </div>
                <div className="text-sm text-gray-600 mt-1">Problems Solved</div>
              </div>
              <div>
                <div className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-500 to-pink-500">
                  {user?.xp || 0}
                </div>
                <div className="text-sm text-gray-600 mt-1">Total XP</div>
              </div>
              <div>
                <div className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-500 to-blue-500">
                  {user?.level || 'Beginner'}
                </div>
                <div className="text-sm text-gray-600 mt-1">Current Level</div>
              </div>
              <div>
                <div className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-green-500 to-emerald-500">
                  {progressPercentage}%
                </div>
                <div className="text-sm text-gray-600 mt-1">Completion</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
