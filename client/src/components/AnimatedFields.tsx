import { motion, AnimatePresence } from 'framer-motion';
import { useState, useEffect } from 'react';
import { Building2, Star, Zap, Target, TrendingUp, Award } from 'lucide-react';

// Custom hook for reduced motion support
function useReducedMotion() {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mediaQuery.matches);

    const handleChange = (event: MediaQueryListEvent) => {
      setPrefersReducedMotion(event.matches);
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  return prefersReducedMotion;
}

// Company Field Component
interface CompanyFieldProps {
  company: string;
  logo?: string;
  isSelected: boolean;
  onClick: () => void;
  className?: string;
  disabled?: boolean;
  'data-testid'?: string;
}

export function CompanyField({ 
  company, 
  logo, 
  isSelected, 
  onClick, 
  className = '', 
  disabled = false,
  'data-testid': testId,
  ...rest 
}: CompanyFieldProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [particles, setParticles] = useState<Array<{ id: number; x: number; y: number }>>([]);
  const prefersReducedMotion = useReducedMotion();

  // Generate floating particles on hover
  useEffect(() => {
    if (isHovered && !disabled) {
      const newParticles = Array.from({ length: 6 }, (_, i) => ({
        id: i,
        x: Math.random() * 100,
        y: Math.random() * 100,
      }));
      setParticles(newParticles);
    } else {
      setParticles([]);
    }
  }, [isHovered, disabled]);

  // Keyboard support
  const handleKeyDown = (event: React.KeyboardEvent) => {
    if ((event.key === 'Enter' || event.key === ' ') && !disabled) {
      event.preventDefault();
      onClick();
    }
  };

  return (
    <motion.button
      type="button"
      disabled={disabled}
      className={`relative w-full text-left p-2 rounded-lg border transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed ${
        isSelected 
          ? 'border-blue-500 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-950/30 dark:to-purple-950/30' 
          : 'border-border bg-background hover:border-blue-300 disabled:hover:border-border'
      } ${className}`}
      onClick={onClick}
      onKeyDown={handleKeyDown}
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
      whileHover={!disabled && !prefersReducedMotion ? { 
        scale: 1.05,
        y: -2,
        boxShadow: isSelected 
          ? '0 8px 25px rgba(59, 130, 246, 0.3)' 
          : '0 4px 15px rgba(0, 0, 0, 0.1)'
      } : {}}
      whileTap={!disabled && !prefersReducedMotion ? { scale: 0.98 } : {}}
      initial={prefersReducedMotion ? { opacity: 1 } : { opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={prefersReducedMotion ? { duration: 0 } : { duration: 0.3, type: "spring", stiffness: 300 }}
      data-testid={testId || `company-field-${company.toLowerCase().replace(/\s+/g, '-')}`}
      aria-pressed={isSelected}
      aria-label={`Select ${company} company`}
      role="button"
      {...rest}
    >
      {/* Gradient glow background */}
      <AnimatePresence>
        {isSelected && (
          <motion.div
            className="absolute inset-0 rounded-lg bg-gradient-to-r from-blue-400/20 to-purple-400/20 blur-sm"
            initial={prefersReducedMotion ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={prefersReducedMotion ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.8 }}
            transition={prefersReducedMotion ? { duration: 0 } : { duration: 0.3 }}
          />
        )}
      </AnimatePresence>

      {/* Floating particles */}
      <AnimatePresence>
        {!prefersReducedMotion && particles.map((particle) => (
          <motion.div
            key={particle.id}
            className="absolute w-1 h-1 bg-blue-400 rounded-full"
            style={{ left: `${particle.x}%`, top: `${particle.y}%` }}
            initial={{ opacity: 0, scale: 0 }}
            animate={{
              opacity: [0, 1, 0],
              scale: [0, 1, 0],
              y: [-10, -30],
            }}
            exit={{ opacity: 0 }}
            transition={{
              duration: 2,
              repeat: Infinity,
              delay: particle.id * 0.2,
            }}
          />
        ))}
      </AnimatePresence>

      <div className="relative flex items-center space-x-2">
        {/* Logo or Building icon */}
        <motion.div
          className="flex-shrink-0"
          whileHover={prefersReducedMotion ? {} : { rotate: 360 }}
          transition={prefersReducedMotion ? { duration: 0 } : { duration: 0.6, type: "spring" }}
          style={{ willChange: !prefersReducedMotion ? "transform" : "auto" }}
        >
          {logo ? (
            <img 
              src={logo} 
              alt={`${company} logo`} 
              className="w-5 h-5 rounded"
            />
          ) : (
            <Building2 className={`w-5 h-5 ${isSelected ? 'text-blue-600 dark:text-blue-400' : 'text-muted-foreground'}`} />
          )}
        </motion.div>

        {/* Company name with sliding animation */}
        <motion.div
          className="overflow-hidden"
          initial={prefersReducedMotion ? { width: 'auto' } : { width: 0 }}
          animate={{ width: 'auto' }}
          transition={prefersReducedMotion ? { duration: 0 } : { duration: 0.4, delay: 0.1 }}
        >
          <motion.span
            className={`text-sm font-medium whitespace-nowrap ${
              isSelected 
                ? 'text-blue-700 dark:text-blue-300' 
                : 'text-foreground'
            }`}
            initial={prefersReducedMotion ? { x: 0, opacity: 1 } : { x: -20, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={prefersReducedMotion ? { duration: 0 } : { duration: 0.3, delay: 0.2 }}
          >
            {company}
          </motion.span>
        </motion.div>

        {/* Pulse animation for selected state */}
        <AnimatePresence>
          {isSelected && (
            <motion.div
              className="w-2 h-2 bg-blue-500 rounded-full"
              initial={prefersReducedMotion ? { scale: 1 } : { scale: 0 }}
              animate={prefersReducedMotion ? { scale: 1 } : { scale: [1, 1.5, 1] }}
              exit={prefersReducedMotion ? { scale: 1 } : { scale: 0 }}
              transition={prefersReducedMotion ? { duration: 0 } : {
                duration: 1.5,
                repeat: Infinity,
                ease: "easeInOut"
              }}
            />
          )}
        </AnimatePresence>
      </div>
    </motion.button>
  );
}

// Difficulty Field Component
interface DifficultyFieldProps {
  difficulty: 'Easy' | 'Medium' | 'Hard';
  isSelected: boolean;
  onClick: () => void;
  className?: string;
  disabled?: boolean;
  'data-testid'?: string;
}

export function DifficultyField({ 
  difficulty, 
  isSelected, 
  onClick,
  className = '',
  disabled = false,
  'data-testid': testId,
  ...rest 
}: DifficultyFieldProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [skillBars, setSkillBars] = useState<Array<{ id: number; height: number }>>([]);
  const prefersReducedMotion = useReducedMotion();

  // Keyboard support
  const handleKeyDown = (event: React.KeyboardEvent) => {
    if ((event.key === 'Enter' || event.key === ' ') && !disabled) {
      event.preventDefault();
      onClick();
    }
  };

  // Static difficulty configuration with proper Tailwind classes
  const difficultyConfig = {
    Easy: { 
      icon: Star, 
      bars: 1,
      gradient: 'from-green-400 to-emerald-500',
      borderSelected: 'border-green-500',
      backgroundSelected: 'bg-gradient-to-r from-green-50 to-green-100 dark:from-green-950/30 dark:to-green-900/30',
      textSelected: 'text-green-700 dark:text-green-300',
      iconSelected: 'text-green-600 dark:text-green-400',
      shadowColor: 'rgba(34, 197, 94, 0.3)',
      pulseColor: 'bg-green-500',
      focusRing: 'focus:ring-green-500'
    },
    Medium: { 
      icon: Zap, 
      bars: 2,
      gradient: 'from-yellow-400 to-orange-500',
      borderSelected: 'border-yellow-500',
      backgroundSelected: 'bg-gradient-to-r from-yellow-50 to-yellow-100 dark:from-yellow-950/30 dark:to-yellow-900/30',
      textSelected: 'text-yellow-700 dark:text-yellow-300',
      iconSelected: 'text-yellow-600 dark:text-yellow-400',
      shadowColor: 'rgba(245, 158, 11, 0.3)',
      pulseColor: 'bg-yellow-500',
      focusRing: 'focus:ring-yellow-500'
    },
    Hard: { 
      icon: Award, 
      bars: 3,
      gradient: 'from-red-400 to-pink-500',
      borderSelected: 'border-red-500',
      backgroundSelected: 'bg-gradient-to-r from-red-50 to-red-100 dark:from-red-950/30 dark:to-red-900/30',
      textSelected: 'text-red-700 dark:text-red-300',
      iconSelected: 'text-red-600 dark:text-red-400',
      shadowColor: 'rgba(239, 68, 68, 0.3)',
      pulseColor: 'bg-red-500',
      focusRing: 'focus:ring-red-500'
    }
  };

  const config = difficultyConfig[difficulty];
  const IconComponent = config.icon;

  // Generate skill bars
  useEffect(() => {
    const bars = Array.from({ length: config.bars }, (_, i) => ({
      id: i,
      height: (i + 1) * 25 + Math.random() * 15,
    }));
    setSkillBars(bars);
  }, [difficulty, config.bars]);

  return (
    <motion.button
      type="button"
      disabled={disabled}
      className={`relative w-full text-left p-2 rounded-lg border transition-all duration-300 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed ${
        isSelected 
          ? `${config.borderSelected} ${config.backgroundSelected} ${config.focusRing}` 
          : 'border-border bg-background hover:border-gray-300 disabled:hover:border-border focus:ring-gray-500'
      } ${className}`}
      onClick={onClick}
      onKeyDown={handleKeyDown}
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
      whileHover={!disabled && !prefersReducedMotion ? { 
        scale: 1.05,
        rotateY: 5,
        boxShadow: `0 8px 25px ${config.shadowColor}`,
        z: 10
      } : {}}
      whileTap={!disabled && !prefersReducedMotion ? { scale: 0.98 } : {}}
      initial={prefersReducedMotion ? { opacity: 1, rotateX: 0 } : { opacity: 0, rotateX: -90 }}
      animate={{ opacity: 1, rotateX: 0 }}
      transition={prefersReducedMotion ? { duration: 0 } : { 
        duration: 0.6, 
        type: "spring", 
        stiffness: 200,
        delay: 0.1 
      }}
      style={{ 
        transformStyle: "preserve-3d", 
        perspective: "1000px",
        willChange: !prefersReducedMotion ? "transform, box-shadow" : "auto"
      }}
      data-testid={testId || `difficulty-field-${difficulty.toLowerCase()}`}
      aria-pressed={isSelected}
      aria-label={`Select ${difficulty} difficulty`}
      role="button"
      {...rest}
    >
      {/* Pulsing background */}
      <AnimatePresence>
        {isSelected && (
          <motion.div
            className={`absolute inset-0 rounded-lg bg-gradient-to-r ${config.gradient} opacity-20`}
            initial={prefersReducedMotion ? { scale: 1, opacity: 0.2 } : { scale: 0.8, opacity: 0 }}
            animate={prefersReducedMotion ? { scale: 1, opacity: 0.2 } : { 
              scale: [1, 1.1, 1], 
              opacity: [0.2, 0.3, 0.2] 
            }}
            exit={prefersReducedMotion ? { scale: 1, opacity: 0.2 } : { scale: 0.8, opacity: 0 }}
            transition={prefersReducedMotion ? { duration: 0 } : {
              duration: 2,
              repeat: Infinity,
              ease: "easeInOut"
            }}
          />
        )}
      </AnimatePresence>

      <div className="relative flex items-center space-x-2">
        {/* Bouncing icon */}
        <motion.div
          className="flex-shrink-0"
          animate={isHovered && !prefersReducedMotion ? {
            y: [0, -4, 0],
            rotate: [0, 10, -10, 0]
          } : {}}
          transition={prefersReducedMotion ? { duration: 0 } : {
            duration: 0.6,
            repeat: isHovered ? Infinity : 0,
            type: "spring",
            stiffness: 300
          }}
          style={{ willChange: !prefersReducedMotion && isHovered ? "transform" : "auto" }}
        >
          <IconComponent 
            className={`w-5 h-5 ${
              isSelected 
                ? config.iconSelected 
                : 'text-muted-foreground'
            }`} 
          />
        </motion.div>

        {/* Difficulty text with glow effect */}
        <motion.span
          className={`text-sm font-medium ${
            isSelected 
              ? config.textSelected
              : 'text-foreground'
          }`}
          style={{
            textShadow: isSelected && !prefersReducedMotion ? `0 0 8px ${config.shadowColor.replace('0.3', '0.5')}` : 'none'
          }}
          initial={prefersReducedMotion ? { opacity: 1, x: 0 } : { opacity: 0, x: 10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={prefersReducedMotion ? { duration: 0 } : { duration: 0.3, delay: 0.2 }}
        >
          {difficulty}
        </motion.span>

        {/* Animated skill bars */}
        <div className="flex items-end space-x-1 ml-2">
          {skillBars.map((bar, index) => (
            <motion.div
              key={bar.id}
              className={`w-1 bg-gradient-to-t ${config.gradient} rounded-full`}
              style={{ 
                height: `${bar.height}%`,
                willChange: !prefersReducedMotion ? "transform, height" : "auto"
              }}
              initial={prefersReducedMotion ? { scaleY: 1 } : { scaleY: 0 }}
              animate={{ 
                scaleY: 1,
                height: isHovered && !prefersReducedMotion ? `${bar.height + 10}%` : `${bar.height}%`
              }}
              transition={prefersReducedMotion ? { duration: 0 } : {
                duration: 0.4,
                delay: index * 0.1,
                type: "spring",
                stiffness: 300
              }}
            />
          ))}
        </div>

        {/* Floating particles for selected state */}
        <AnimatePresence>
          {isSelected && (
            <motion.div
              className="absolute -top-1 -right-1"
              initial={prefersReducedMotion ? { scale: 1, rotate: 0 } : { scale: 0, rotate: -180 }}
              animate={prefersReducedMotion ? { scale: 1, rotate: 0, y: 0 } : { 
                scale: [1, 1.2, 1], 
                rotate: 0,
                y: [0, -3, 0]
              }}
              exit={prefersReducedMotion ? { scale: 1, rotate: 0 } : { scale: 0, rotate: 180 }}
              transition={prefersReducedMotion ? { duration: 0 } : {
                duration: 1.5,
                repeat: Infinity,
                ease: "easeInOut"
              }}
            >
              <div className={`w-2 h-2 ${config.pulseColor} rounded-full opacity-80`} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.button>
  );
}