import { motion, AnimatePresence } from 'framer-motion';
import { useState, useEffect } from 'react';
import { Building2, Star, Zap, Target, TrendingUp, Award } from 'lucide-react';

// Company Field Component
interface CompanyFieldProps {
  company: string;
  logo?: string;
  isSelected: boolean;
  onClick: () => void;
}

export function CompanyField({ company, logo, isSelected, onClick }: CompanyFieldProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [particles, setParticles] = useState<Array<{ id: number; x: number; y: number }>>([]);

  // Generate floating particles on hover
  useEffect(() => {
    if (isHovered) {
      const newParticles = Array.from({ length: 6 }, (_, i) => ({
        id: i,
        x: Math.random() * 100,
        y: Math.random() * 100,
      }));
      setParticles(newParticles);
    } else {
      setParticles([]);
    }
  }, [isHovered]);

  return (
    <motion.div
      className={`relative cursor-pointer p-2 rounded-lg border transition-all duration-300 ${
        isSelected 
          ? 'border-blue-500 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-950/30 dark:to-purple-950/30' 
          : 'border-border bg-background hover:border-blue-300'
      }`}
      onClick={onClick}
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
      whileHover={{ 
        scale: 1.05,
        y: -2,
        boxShadow: isSelected 
          ? '0 8px 25px rgba(59, 130, 246, 0.3)' 
          : '0 4px 15px rgba(0, 0, 0, 0.1)'
      }}
      whileTap={{ scale: 0.98 }}
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3, type: "spring", stiffness: 300 }}
      data-testid={`company-field-${company.toLowerCase().replace(/\s+/g, '-')}`}
    >
      {/* Gradient glow background */}
      <AnimatePresence>
        {isSelected && (
          <motion.div
            className="absolute inset-0 rounded-lg bg-gradient-to-r from-blue-400/20 to-purple-400/20 blur-sm"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ duration: 0.3 }}
          />
        )}
      </AnimatePresence>

      {/* Floating particles */}
      <AnimatePresence>
        {particles.map((particle) => (
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
          whileHover={{ rotate: 360 }}
          transition={{ duration: 0.6, type: "spring" }}
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
          initial={{ width: 0 }}
          animate={{ width: 'auto' }}
          transition={{ duration: 0.4, delay: 0.1 }}
        >
          <motion.span
            className={`text-sm font-medium whitespace-nowrap ${
              isSelected 
                ? 'text-blue-700 dark:text-blue-300' 
                : 'text-foreground'
            }`}
            initial={{ x: -20, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ duration: 0.3, delay: 0.2 }}
          >
            {company}
          </motion.span>
        </motion.div>

        {/* Pulse animation for selected state */}
        <AnimatePresence>
          {isSelected && (
            <motion.div
              className="w-2 h-2 bg-blue-500 rounded-full"
              initial={{ scale: 0 }}
              animate={{ scale: [1, 1.5, 1] }}
              exit={{ scale: 0 }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                ease: "easeInOut"
              }}
            />
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

// Difficulty Field Component
interface DifficultyFieldProps {
  difficulty: 'Easy' | 'Medium' | 'Hard';
  isSelected: boolean;
  onClick: () => void;
}

export function DifficultyField({ difficulty, isSelected, onClick }: DifficultyFieldProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [skillBars, setSkillBars] = useState<Array<{ id: number; height: number }>>([]);

  // Difficulty configuration
  const difficultyConfig = {
    Easy: { 
      icon: Star, 
      color: 'green', 
      bars: 1,
      gradient: 'from-green-400 to-emerald-500'
    },
    Medium: { 
      icon: Zap, 
      color: 'yellow', 
      bars: 2,
      gradient: 'from-yellow-400 to-orange-500'
    },
    Hard: { 
      icon: Award, 
      color: 'red', 
      bars: 3,
      gradient: 'from-red-400 to-pink-500'
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
    <motion.div
      className={`relative cursor-pointer p-2 rounded-lg border transition-all duration-300 ${
        isSelected 
          ? `border-${config.color}-500 bg-gradient-to-r from-${config.color}-50 to-${config.color}-100 dark:from-${config.color}-950/30 dark:to-${config.color}-900/30` 
          : 'border-border bg-background hover:border-gray-300'
      }`}
      onClick={onClick}
      onHoverStart={() => setIsHovered(true)}
      onHoverEnd={() => setIsHovered(false)}
      whileHover={{ 
        scale: 1.05,
        rotateY: 5,
        boxShadow: `0 8px 25px rgba(${config.color === 'green' ? '34, 197, 94' : config.color === 'yellow' ? '245, 158, 11' : '239, 68, 68'}, 0.3)`
      }}
      whileTap={{ scale: 0.98 }}
      initial={{ opacity: 0, rotateX: -90 }}
      animate={{ opacity: 1, rotateX: 0 }}
      transition={{ 
        duration: 0.6, 
        type: "spring", 
        stiffness: 200,
        delay: 0.1 
      }}
      style={{ transformStyle: "preserve-3d" }}
      data-testid={`difficulty-field-${difficulty.toLowerCase()}`}
    >
      {/* Pulsing background */}
      <AnimatePresence>
        {isSelected && (
          <motion.div
            className={`absolute inset-0 rounded-lg bg-gradient-to-r ${config.gradient} opacity-20`}
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ 
              scale: [1, 1.1, 1], 
              opacity: [0.2, 0.3, 0.2] 
            }}
            exit={{ scale: 0.8, opacity: 0 }}
            transition={{
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
          animate={isHovered ? {
            y: [0, -4, 0],
            rotate: [0, 10, -10, 0]
          } : {}}
          transition={{
            duration: 0.6,
            repeat: isHovered ? Infinity : 0,
            type: "spring",
            stiffness: 300
          }}
        >
          <IconComponent 
            className={`w-5 h-5 ${
              isSelected 
                ? `text-${config.color}-600 dark:text-${config.color}-400` 
                : 'text-muted-foreground'
            }`} 
          />
        </motion.div>

        {/* Difficulty text with glow effect */}
        <motion.span
          className={`text-sm font-medium ${
            isSelected 
              ? `text-${config.color}-700 dark:text-${config.color}-300` 
              : 'text-foreground'
          }`}
          style={{
            textShadow: isSelected ? `0 0 8px rgba(${config.color === 'green' ? '34, 197, 94' : config.color === 'yellow' ? '245, 158, 11' : '239, 68, 68'}, 0.5)` : 'none'
          }}
          initial={{ opacity: 0, x: 10 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3, delay: 0.2 }}
        >
          {difficulty}
        </motion.span>

        {/* Animated skill bars */}
        <div className="flex items-end space-x-1 ml-2">
          {skillBars.map((bar, index) => (
            <motion.div
              key={bar.id}
              className={`w-1 bg-gradient-to-t ${config.gradient} rounded-full`}
              style={{ height: `${bar.height}%` }}
              initial={{ scaleY: 0 }}
              animate={{ 
                scaleY: 1,
                height: isHovered ? `${bar.height + 10}%` : `${bar.height}%`
              }}
              transition={{
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
              initial={{ scale: 0, rotate: -180 }}
              animate={{ 
                scale: [1, 1.2, 1], 
                rotate: 0,
                y: [0, -3, 0]
              }}
              exit={{ scale: 0, rotate: 180 }}
              transition={{
                duration: 1.5,
                repeat: Infinity,
                ease: "easeInOut"
              }}
            >
              <div className={`w-2 h-2 bg-${config.color}-500 rounded-full opacity-80`} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}