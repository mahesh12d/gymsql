import { Badge } from "@/components/ui/badge";
import { Target, Zap, Flame, Award } from "lucide-react";

interface DifficultyBadgeProps {
  difficulty: string;
  variant?: "badge" | "full" | "minimal" | "skill";
  size?: "sm" | "md" | "lg";
  showIcon?: boolean;
  showBars?: boolean;
  className?: string;
  onClick?: () => void;
  "data-testid"?: string;
}

type DifficultyLevel = "Easy" | "Medium" | "Hard" | "Expert";

interface DifficultyConfig {
  level: DifficultyLevel;
  colors: {
    bg: string;
    text: string;
    border: string;
    primary: string;
    secondary: string;
  };
  icon: typeof Target;
  bars: number;
  label: string;
  description: string;
}

const DIFFICULTY_CONFIG: Record<string, DifficultyConfig> = {
  easy: {
    level: "Easy",
    colors: {
      bg: "bg-green-50",
      text: "text-green-700",
      border: "border-green-200", 
      primary: "#15803d",
      secondary: "#22c55e",
    },
    icon: Target,
    bars: 1,
    label: "Easy",
    description: "Perfect for beginners",
  },
  medium: {
    level: "Medium",
    colors: {
      bg: "bg-orange-50",
      text: "text-orange-700",
      border: "border-orange-200",
      primary: "#ea580c",
      secondary: "#f97316",
    },
    icon: Zap,
    bars: 2,
    label: "Medium",
    description: "Requires some experience",
  },
  hard: {
    level: "Hard",
    colors: {
      bg: "bg-red-50",
      text: "text-red-700",
      border: "border-red-200",
      primary: "#dc2626",
      secondary: "#ef4444",
    },
    icon: Flame,
    bars: 3,
    label: "Hard",
    description: "For experienced developers",
  },
  expert: {
    level: "Expert",
    colors: {
      bg: "bg-purple-50",
      text: "text-purple-700",
      border: "border-purple-200",
      primary: "#7c3aed",
      secondary: "#8b5cf6",
    },
    icon: Award,
    bars: 4,
    label: "Expert",
    description: "Challenge for experts",
  },
};

/**
 * Enhanced difficulty badge component with multiple variants and improved styling
 */
export function DifficultyBadge({
  difficulty,
  variant = "badge",
  size = "md",
  showIcon = true,
  showBars = false,
  className = "",
  onClick,
  "data-testid": testId,
}: DifficultyBadgeProps) {
  const difficultyKey = difficulty?.toLowerCase() || "easy";
  const config = DIFFICULTY_CONFIG[difficultyKey] || DIFFICULTY_CONFIG.easy;
  const IconComponent = config.icon;

  // Size configurations
  const sizeConfig = {
    sm: {
      badge: "text-xs px-2 py-0.5",
      icon: "w-3 h-3",
      text: "text-xs",
      bar: "w-1 h-2",
      gap: "gap-1",
    },
    md: {
      badge: "text-xs px-2 py-1",
      icon: "w-3.5 h-3.5",
      text: "text-sm",
      bar: "w-1.5 h-3",
      gap: "gap-1.5",
    },
    lg: {
      badge: "text-sm px-3 py-1.5",
      icon: "w-4 h-4",
      text: "text-base",
      bar: "w-2 h-4",
      gap: "gap-2",
    },
  };

  const sizeConf = sizeConfig[size];

  // Skill bars component
  const SkillBars = ({ count }: { count: number }) => (
    <div className={`flex items-end ${sizeConf.gap}`}>
      {Array.from({ length: 4 }, (_, i) => (
        <div
          key={i}
          className={`${sizeConf.bar} rounded-sm transition-all duration-300 ease-out`}
          style={{
            backgroundColor: i < count ? config.colors.primary : "#d1d5db",
            animationDelay: `${i * 100}ms`,
          }}
        />
      ))}
    </div>
  );

  // Render based on variant
  switch (variant) {
    case "minimal":
      return (
        <span
          className={`inline-flex items-center ${sizeConf.gap} ${sizeConf.text} font-medium ${className}`}
          onClick={onClick}
          data-testid={testId}
          style={{ 
            color: config.colors.primary,
            cursor: onClick ? "pointer" : "default"
          }}
        >
          {showIcon && <IconComponent className={sizeConf.icon} />}
          {config.label}
        </span>
      );

    case "skill":
      return (
        <div
          className={`inline-flex items-center ${sizeConf.gap} ${className}`}
          onClick={onClick}
          data-testid={testId}
          style={{ cursor: onClick ? "pointer" : "default" }}
        >
          {showIcon && (
            <IconComponent 
              className={sizeConf.icon} 
              style={{ color: config.colors.primary }}
            />
          )}
          <span 
            className={`${sizeConf.text} font-medium`}
            style={{ color: config.colors.primary }}
          >
            {config.label}
          </span>
          <SkillBars count={config.bars} />
        </div>
      );

    case "full":
      return (
        <div
          className={`difficulty-field ${difficultyKey} selected ${className}`}
          onClick={onClick}
          data-testid={testId}
        >
          <span className="difficulty-icon">
            {showIcon ? (
              <IconComponent className="w-3.5 h-3.5" style={{ color: config.colors.primary }} />
            ) : (
              "🎯"
            )}
          </span>
          <span className="difficulty-name">{config.label}</span>
          {showBars && (
            <div className="skill-bars">
              {Array.from({ length: 3 }, (_, i) => (
                <div
                  key={i}
                  className="skill-bar"
                  style={{
                    background: i < config.bars ? config.colors.secondary : "#d1d5db",
                  }}
                />
              ))}
            </div>
          )}
        </div>
      );

    case "badge":
    default:
      return (
        <Badge
          className={`${config.colors.bg} ${config.colors.text} ${config.colors.border} border font-medium inline-flex items-center ${sizeConf.gap} ${sizeConf.badge} ${className}`}
          onClick={onClick}
          data-testid={testId}
          style={{ cursor: onClick ? "pointer" : "default" }}
        >
          {showIcon && <IconComponent className={sizeConf.icon} />}
          {config.label}
          {showBars && (
            <div className={`flex items-end ${sizeConf.gap} ml-1`}>
              {Array.from({ length: 3 }, (_, i) => (
                <div
                  key={i}
                  className={`${sizeConf.bar} rounded-sm`}
                  style={{
                    backgroundColor: i < config.bars ? config.colors.primary : "#d1d5db",
                  }}
                />
              ))}
            </div>
          )}
        </Badge>
      );
  }
}

/**
 * Get difficulty color classes for legacy compatibility
 */
export function getDifficultyColor(difficulty: string): string {
  const difficultyKey = difficulty?.toLowerCase() || "easy";
  const config = DIFFICULTY_CONFIG[difficultyKey] || DIFFICULTY_CONFIG.easy;
  return `${config.colors.text} ${config.colors.bg} ${config.colors.border}`;
}

/**
 * Get difficulty configuration
 */
export function getDifficultyConfig(difficulty: string): DifficultyConfig {
  const difficultyKey = difficulty?.toLowerCase() || "easy";
  return DIFFICULTY_CONFIG[difficultyKey] || DIFFICULTY_CONFIG.easy;
}

/**
 * Simplified component for backward compatibility
 */
export function DifficultyTag({ difficulty, className, ...props }: Omit<DifficultyBadgeProps, "variant">) {
  return (
    <DifficultyBadge
      difficulty={difficulty}
      variant="badge"
      className={className}
      {...props}
    />
  );
}

export default DifficultyBadge;