import { useState, useRef, useEffect } from "react";
import { useAuth } from "@/hooks/use-auth";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { User, Trophy, Clock, X, Linkedin, Building } from "lucide-react";
import { cn } from "@/lib/utils";

interface UserData {
  id: string;
  username: string;
  first_name?: string;
  last_name?: string;
  companyName?: string;
  linkedinUrl?: string;
  profileImageUrl?: string;
  problemsSolved?: number;
  rank?: number;
  email?: string;
  premium?: boolean;
}

interface UserProfilePopoverProps {
  user: UserData;
  children: React.ReactNode;
  trigger?: 'click' | 'hover';
  className?: string;
}

export function UserProfilePopover({ 
  user, 
  children, 
  trigger = 'click', 
  className 
}: UserProfilePopoverProps) {
  const { user: currentUser } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const closeTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Don't show popover for current user
  if (user.id === currentUser?.id) {
    return <>{children}</>;
  }

  const displayName = user.first_name && user.last_name 
    ? `${user.first_name} ${user.last_name}`
    : user.username;

  const getRankDisplay = () => {
    if (!user.rank) return null;
    
    if (user.rank === 1) return <Trophy className="h-4 w-4 text-yellow-500" />;
    if (user.rank === 2) return <Trophy className="h-4 w-4 text-gray-400" />;
    if (user.rank === 3) return <Trophy className="h-4 w-4 text-orange-400" />;
    return <span className="text-xs text-muted-foreground">#{user.rank}</span>;
  };

  const handleMouseEnter = () => {
    if (trigger === 'hover') {
      if (closeTimeoutRef.current) {
        clearTimeout(closeTimeoutRef.current);
        closeTimeoutRef.current = null;
      }
      setIsOpen(true);
    }
  };

  const handleMouseLeave = () => {
    if (trigger === 'hover') {
      if (closeTimeoutRef.current) {
        clearTimeout(closeTimeoutRef.current);
      }
      closeTimeoutRef.current = setTimeout(() => {
        setIsOpen(false);
      }, 200);
    }
  };

  useEffect(() => {
    return () => {
      if (closeTimeoutRef.current) {
        clearTimeout(closeTimeoutRef.current);
      }
    };
  }, []);

  return (
    <>
      <Popover open={isOpen} onOpenChange={setIsOpen}>
        <PopoverTrigger asChild>
          <div 
            className={cn(
              "cursor-pointer transition-colors hover:bg-muted/50 rounded-md", 
              className
            )}
            onClick={(e) => {
              if (trigger === 'click') {
                e.preventDefault();
                e.stopPropagation();
                setIsOpen(true);
              }
            }}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
            data-testid={`user-profile-trigger-${user.id}`}
          >
            {children}
          </div>
        </PopoverTrigger>
        
        <PopoverContent 
          className="w-80 p-0" 
          side="top" 
          align="center"
          data-testid={`user-profile-popover-${user.id}`}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
        >
          <div className="relative">
            {/* Close button */}
            <Button
              variant="ghost"
              size="icon"
              className="absolute top-2 right-2 h-6 w-6 z-10"
              onClick={() => setIsOpen(false)}
            >
              <X className="h-4 w-4" />
            </Button>

            {/* Header */}
            <div className="bg-gradient-to-r from-blue-500 to-purple-600 text-white p-4 rounded-t-lg">
              <div className="flex items-center space-x-3">
                <Avatar className="h-16 w-16 ring-2 ring-white/20">
                  <AvatarImage src={user.profileImageUrl} alt={displayName} />
                  <AvatarFallback className="bg-white/20 text-white text-lg font-bold">
                    {user.username?.[0]?.toUpperCase() || '?'}
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <h3 className="font-bold text-lg">{displayName}</h3>
                    {user.premium && (
                      <Badge variant="secondary" className="bg-yellow-400 text-yellow-900 text-xs">
                        ⭐ Premium
                      </Badge>
                    )}
                  </div>
                  <p className="text-white/80">@{user.username}</p>
                  <div className="flex items-center space-x-2 mt-1">
                    {getRankDisplay()}
                    {user.problemsSolved !== undefined && (
                      <span className="text-sm text-white/90">
                        {user.problemsSolved} problems solved
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Content */}
            <div className="p-4 space-y-4">
              {/* Quick Stats */}
              <div className="grid grid-cols-2 gap-3">
                <div className="text-center p-3 bg-muted/50 rounded-lg">
                  <div className="flex items-center justify-center mb-1">
                    <Trophy className="h-4 w-4 text-muted-foreground mr-1" />
                    <span className="text-xs text-muted-foreground">Rank</span>
                  </div>
                  <div className="font-bold text-foreground">
                    {user.rank ? `#${user.rank}` : 'Unranked'}
                  </div>
                </div>
                <div className="text-center p-3 bg-muted/50 rounded-lg">
                  <div className="flex items-center justify-center mb-1">
                    <User className="h-4 w-4 text-muted-foreground mr-1" />
                    <span className="text-xs text-muted-foreground">Problems</span>
                  </div>
                  <div className="font-bold text-foreground">
                    {user.problemsSolved || 0}
                  </div>
                </div>
              </div>

              {/* Company and LinkedIn Info */}
              {(user.companyName || user.linkedinUrl) && (
                <div className="space-y-2 pt-2 border-t">
                  {user.companyName && (
                    <div className="flex items-center text-sm text-muted-foreground">
                      <Building className="h-4 w-4 mr-2" />
                      <span>{user.companyName}</span>
                    </div>
                  )}
                  {user.linkedinUrl && (
                    <a
                      href={user.linkedinUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Linkedin className="h-4 w-4 mr-2" />
                      <span>View LinkedIn Profile</span>
                    </a>
                  )}
                </div>
              )}

              {/* Status or additional info */}
              <div className="text-center">
                <div className="flex items-center justify-center text-xs text-muted-foreground">
                  <Clock className="h-3 w-3 mr-1" />
                  Member since 2024
                </div>
              </div>
            </div>
          </div>
        </PopoverContent>
      </Popover>

    </>
  );
}

// Convenience wrapper for avatar-only triggers
export function UserAvatarChat({ user, size = "default", className }: { 
  user: UserData; 
  size?: "sm" | "default" | "lg";
  className?: string;
}) {
  const sizeClasses = {
    sm: "h-8 w-8",
    default: "h-12 w-12", 
    lg: "h-16 w-16"
  };

  return (
    <UserProfilePopover user={user} className={className}>
      <Avatar className={sizeClasses[size]}>
        <AvatarImage src={user.profileImageUrl} alt={user.username} />
        <AvatarFallback>
          {user.username?.[0]?.toUpperCase() || '?'}
        </AvatarFallback>
      </Avatar>
    </UserProfilePopover>
  );
}

// Convenience wrapper for username triggers
export function UsernameChatLink({ 
  user, 
  showFullName = true,
  className,
  children
}: { 
  user: UserData; 
  showFullName?: boolean;
  className?: string;
  children?: React.ReactNode;
}) {
  const displayText = children || (
    showFullName && user.first_name && user.last_name
      ? `${user.first_name} ${user.last_name}`
      : user.username
  );

  return (
    <UserProfilePopover user={user} className={className}>
      <span className="text-foreground hover:text-primary cursor-pointer transition-colors">
        {displayText}
      </span>
    </UserProfilePopover>
  );
}