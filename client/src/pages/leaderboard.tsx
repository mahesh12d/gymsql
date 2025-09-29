import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Trophy, Medal, Award, TrendingUp, Users, Target } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { leaderboardApi } from '@/lib/auth';
import { useAuth } from '@/hooks/use-auth';
import { UserProfilePopover } from '@/components/UserProfilePopover';

export default function Leaderboard() {
  const [limit, setLimit] = useState(50);
  const { user } = useAuth();

  const { data: leaderboard, isLoading } = useQuery({
    queryKey: ['/api/leaderboard', limit],
    queryFn: () => leaderboardApi.get(limit),
  });


  const getRankIcon = (rank: number) => {
    switch (rank) {
      case 1: return <Trophy className="w-6 h-6 text-yellow-500" />;
      case 2: return <Medal className="w-6 h-6 text-gray-400" />;
      case 3: return <Award className="w-6 h-6 text-orange-400" />;
      default: return null;
    }
  };


  const currentUserRank = leaderboard?.findIndex(u => u.id === user?.id) ?? -1;

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-foreground mb-4">SQL Athletes Leaderboard</h1>
          <p className="text-xl text-muted-foreground">See who's crushing their SQL workouts</p>
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Main Leaderboard */}
          <div className="lg:col-span-2">
            <Card className="overflow-hidden">
              <CardHeader className="bg-gradient-to-r from-primary to-orange-400 text-white">
                <CardTitle className="text-2xl font-bold mb-2">Top SQL Athletes</CardTitle>
                <p className="opacity-90">This week's strongest performers</p>
              </CardHeader>
              
              <CardContent className="p-6">
                {isLoading ? (
                  <div className="space-y-4">
                    {[...Array(10)].map((_, i) => (
                      <div key={i} className="flex items-center space-x-4 py-4 animate-pulse">
                        <div className="w-12 h-12 bg-muted rounded-full" />
                        <div className="w-12 h-12 bg-muted rounded-full" />
                        <div className="flex-1 space-y-2">
                          <div className="h-4 bg-muted rounded w-1/3" />
                          <div className="h-3 bg-muted rounded w-1/4" />
                        </div>
                        <div className="space-y-2">
                          <div className="h-4 bg-muted rounded w-16" />
                          <div className="h-3 bg-muted rounded w-12" />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="space-y-2">
                    {leaderboard?.map((athlete, index) => (
                      <div 
                        key={athlete.id} 
                        className={`flex items-center space-x-4 py-4 border-b border-border last:border-b-0 rounded-lg transition-colors ${
                          athlete.id === user?.id ? 'bg-primary/5 border-primary/20' : 'hover:bg-muted/50'
                        }`}
                        data-testid={`leaderboard-rank-${index + 1}`}
                      >
                        {/* Rank */}
                        <div className="flex items-center justify-center w-12 h-12">
                          {getRankIcon(index + 1) || (
                            <div className={`flex items-center justify-center w-12 h-12 rounded-full font-bold text-lg ${
                              index < 3 ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'
                            }`}>
                              {index + 1}
                            </div>
                          )}
                        </div>

                        {/* Avatar - Clickable for Chat */}
                        <UserProfilePopover 
                          user={{
                            id: athlete.id,
                            username: athlete.username,
                            first_name: athlete.firstName,
                            last_name: athlete.lastName,
                            profileImageUrl: athlete.profileImageUrl,
                            problemsSolved: athlete.problemsSolved,
                            rank: index + 1,
                            premium: athlete.premium
                          }}
                        >
                          <Avatar className="w-12 h-12 ring-2 ring-transparent hover:ring-primary/50 transition-all cursor-pointer">
                            <AvatarImage src={athlete.profileImageUrl} alt={athlete.username} />
                            <AvatarFallback>
                              {athlete.username?.charAt(0).toUpperCase() || 'U'}
                            </AvatarFallback>
                          </Avatar>
                        </UserProfilePopover>

                        {/* User Info - Clickable for Chat */}
                        <div className="flex-1">
                          <div className="flex items-center space-x-2">
                            <UserProfilePopover 
                              user={{
                                id: athlete.id,
                                username: athlete.username,
                                first_name: athlete.firstName,
                                last_name: athlete.lastName,
                                profileImageUrl: athlete.profileImageUrl,
                                problemsSolved: athlete.problemsSolved,
                                rank: index + 1,
                                premium: athlete.premium
                              }}
                            >
                              <h4 className="font-semibold text-foreground hover:text-primary cursor-pointer transition-colors" 
                                  data-testid={`text-username-${index + 1}`}>
                                {athlete.firstName && athlete.lastName 
                                  ? `${athlete.firstName} ${athlete.lastName}` 
                                  : athlete.username}
                              </h4>
                            </UserProfilePopover>
                            {athlete.id === user?.id && (
                              <Badge variant="outline" className="text-xs">You</Badge>
                            )}
                          </div>
                          <div className="flex items-center space-x-2">
                            <span className="text-sm text-muted-foreground">@{athlete.username}</span>
                          </div>
                        </div>

                        {/* Stats */}
                        <div className="text-right">
                          <p className="font-bold text-foreground" data-testid={`text-problems-${index + 1}`}>
                            {athlete.problemsSolved} solved
                          </p>
                        </div>

                        {/* Achievement Icons */}
                        <div className="flex items-center space-x-1">
                          {index === 0 && <Trophy className="w-4 h-4 text-yellow-400" />}
                          {index <= 1 && <Medal className="w-4 h-4 text-gray-400" />}
                          {index <= 2 && <Award className="w-4 h-4 text-orange-400" />}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Load More */}
                {!isLoading && leaderboard && leaderboard.length >= limit && (
                  <div className="text-center mt-6">
                    <Button 
                      variant="outline" 
                      onClick={() => setLimit(limit + 50)}
                      data-testid="button-load-more"
                    >
                      Load More Athletes
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Your Stats */}
            {user && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <Target className="w-5 h-5 text-primary" />
                    <span>Your Stats</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Rank</span>
                    <span className="font-bold text-foreground" data-testid="text-user-rank">
                      #{currentUserRank >= 0 ? currentUserRank + 1 : '?'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Problems Solved</span>
                    <span className="font-bold text-foreground" data-testid="text-user-problems">
                      {user.problemsSolved}
                    </span>
                  </div>
                </CardContent>
              </Card>
            )}



            {/* Leaderboard Stats */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Users className="w-5 h-5 text-primary" />
                  <span>Community Stats</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Total Athletes</span>
                  <span className="font-bold text-foreground">
                    {leaderboard?.length.toLocaleString() || 0}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Top Problems Solved</span>
                  <span className="font-bold text-foreground">
                    {leaderboard?.[0]?.problemsSolved || 0}
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
