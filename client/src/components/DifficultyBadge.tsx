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

type DifficultyLevel = "Easy" | "Medium" | "Hard" | "Expert" | (string & {});

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
 * Generate dynamic difficulty configuration for unknown difficulty levels
 * Creates appropriate colors and styling based on difficulty name
 */
function generateDynamicDifficultyConfig(difficulty: string): DifficultyConfig {
  const normalizedDifficulty = difficulty.trim();
  const hash = normalizedDifficulty.split('').reduce((a, b) => {
    a = ((a << 5) - a) + b.charCodeAt(0);
    return a & a;
  }, 0);
  
  // Generate colors based on hash for consistency
  const hue = Math.abs(hash) % 360;
  const saturation = 70;
  const lightness = 60;
  
  const primaryColor = `hsl(${hue}, ${saturation}%, ${lightness}%)`;
  const secondaryColor = `hsl(${hue}, ${saturation - 10}%, ${lightness + 10}%)`;
  const bgColor = `hsl(${hue}, ${saturation - 50}%, 97%)`;
  const textColor = `hsl(${hue}, ${saturation}%, 30%)`;
  const borderColor = `hsl(${hue}, ${saturation - 30}%, 85%)`;
  
  // Determine bars based on common difficulty patterns
  let bars = 2; // default
  const lowerDifficulty = normalizedDifficulty.toLowerCase();
  if (lowerDifficulty.includes('easy') || lowerDifficulty.includes('beginner') || lowerDifficulty.includes('basic')) {
    bars = 1;
  } else if (lowerDifficulty.includes('expert') || lowerDifficulty.includes('master') || lowerDifficulty.includes('advanced')) {
    bars = 4;
  } else if (lowerDifficulty.includes('hard') || lowerDifficulty.includes('difficult') || lowerDifficulty.includes('complex')) {
    bars = 3;
  }
  
  return {
    level: normalizedDifficulty,
    colors: {
      bg: `bg-gray-50`, // Use neutral background for better control
      text: `text-gray-700`, // Use neutral text for better control  
      border: `border-gray-200`, // Use neutral border for better control
      primary: primaryColor,
      secondary: secondaryColor,
    },
    icon: Target, // Default icon for unknown difficulties
    bars,
    label: normalizedDifficulty,
    description: `${normalizedDifficulty} level challenge`,
  };
}

/**
 * Enhanced difficulty badge component with multiple variants and improved styling
 * Now supports dynamic difficulty levels from the database with automatic color generation
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
  
  // Get config from predefined list or generate dynamic config for unknown difficulties
  const config = DIFFICULTY_CONFIG[difficultyKey] || generateDynamicDifficultyConfig(difficulty || "easy");
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
      // Check if this is a custom (dynamic) configuration
      const isCustomConfigFull = !DIFFICULTY_CONFIG[difficultyKey];
      
      return (
        <div
          className={`difficulty-field ${difficultyKey} selected ${className}`}
          onClick={onClick}
          data-testid={testId}
          style={{
            ...(isCustomConfigFull && {
              backgroundColor: config.colors.primary + '15', // 15% opacity
              borderColor: config.colors.primary + '40', // 40% opacity
            })
          }}
        >
          <span className="difficulty-icon">
            {showIcon ? (
              <IconComponent className="w-3.5 h-3.5" style={{ color: config.colors.primary }} />
            ) : (
              "🎯"
            )}
          </span>
          <span 
            className="difficulty-name"
            style={{
              ...(isCustomConfigFull && {
                color: config.colors.primary
              })
            }}
          >
            {config.label}
          </span>
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
      // Check if this is a custom (dynamic) configuration
      const isCustomConfig = !DIFFICULTY_CONFIG[difficultyKey];
      
      return (
        <Badge
          className={`${config.colors.bg} ${config.colors.text} ${config.colors.border} border font-medium inline-flex items-center ${sizeConf.gap} ${sizeConf.badge} ${className}`}
          onClick={onClick}
          data-testid={testId}
          style={{ 
            cursor: onClick ? "pointer" : "default",
            // Apply custom colors for dynamic configurations
            ...(isCustomConfig && {
              backgroundColor: config.colors.primary + '20', // 20% opacity
              borderColor: config.colors.primary + '50', // 50% opacity
              color: config.colors.primary,
            })
          }}
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
 * Now supports dynamic difficulties with custom colors
 */
export function getDifficultyColor(difficulty: string): string {
  const difficultyKey = difficulty?.toLowerCase() || "easy";
  const config = DIFFICULTY_CONFIG[difficultyKey] || generateDynamicDifficultyConfig(difficulty || "easy");
  
  // For custom configurations, return inline styles via CSS classes
  const isCustomConfig = !DIFFICULTY_CONFIG[difficultyKey];
  if (isCustomConfig) {
    return `text-gray-700 bg-gray-50 border-gray-200`; // Neutral classes for custom colors
  }
  
  return `${config.colors.text} ${config.colors.bg} ${config.colors.border}`;
}

/**
 * Get difficulty configuration
 * Now supports dynamic difficulties
 */
export function getDifficultyConfig(difficulty: string): DifficultyConfig {
  const difficultyKey = difficulty?.toLowerCase() || "easy";
  return DIFFICULTY_CONFIG[difficultyKey] || generateDynamicDifficultyConfig(difficulty || "easy");
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