import { Trophy, Dumbbell, Flame, Award } from 'lucide-react';

interface Badge {
  badgeType: string;
  badgeName: string;
  earnedAt: string;
}

interface BadgeDisplayProps {
  badges: Badge[];
  className?: string;
}

const badgeIcons: Record<string, { icon: any; color: string }> = {
  first_rep: { icon: Dumbbell, color: 'bg-primary/10 text-primary' },
  hot_streak: { icon: Flame, color: 'bg-red-100 text-red-600' },
  champion: { icon: Trophy, color: 'bg-yellow-100 text-yellow-600' },
  default: { icon: Award, color: 'bg-gray-100 text-gray-600' },
};

export default function BadgeDisplay({ badges, className = '' }: BadgeDisplayProps) {
  if (badges.length === 0) {
    return (
      <div className={`text-center py-8 ${className}`}>
        <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-4">
          <Trophy className="w-8 h-8 text-muted-foreground" />
        </div>
        <p className="text-muted-foreground">No badges earned yet</p>
        <p className="text-sm text-muted-foreground mt-1">Start solving problems to earn badges!</p>
      </div>
    );
  }

  return (
    <div className={`space-y-4 ${className}`}>
      <h3 className="font-semibold text-foreground">Badges Earned</h3>
      <div className="grid grid-cols-3 gap-3">
        {badges.map((badge, index) => {
          const badgeConfig = badgeIcons[badge.badgeType] || badgeIcons.default;
          const IconComponent = badgeConfig.icon;
          
          return (
            <div key={index} className="text-center" data-testid={`badge-${badge.badgeType}`}>
              <div className={`w-12 h-12 ${badgeConfig.color} rounded-full flex items-center justify-center mx-auto mb-2`}>
                <IconComponent className="w-6 h-6" />
              </div>
              <span className="text-xs text-muted-foreground">{badge.badgeName}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
