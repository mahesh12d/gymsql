import { useEffect, useRef } from 'react';

interface ProgressBarProps {
  value: number;
  max: number;
  className?: string;
  showText?: boolean;
}

export default function ProgressBar({ value, max, className = '', showText = true }: ProgressBarProps) {
  const progressRef = useRef<HTMLDivElement>(null);
  const percentage = Math.min((value / max) * 100, 100);

  useEffect(() => {
    if (progressRef.current) {
      progressRef.current.style.setProperty('--progress-width', `${percentage}%`);
      // Trigger animation
      progressRef.current.classList.add('progress-weight');
    }
  }, [percentage]);

  return (
    <div className={`space-y-2 ${className}`}>
      {showText && (
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">Progress</span>
          <span className="font-medium text-foreground">{Math.round(percentage)}%</span>
        </div>
      )}
      <div className="w-full bg-muted rounded-full h-3">
        <div 
          ref={progressRef}
          className="h-3 rounded-full transition-all duration-300"
          style={{ 
            background: 'linear-gradient(90deg, var(--primary) 0%, #f59e0b 100%)',
            width: `${percentage}%`
          }}
        />
      </div>
      {showText && (
        <div className="flex items-center space-x-2 mt-2">
          <div className="weight-plate" />
          <span className="text-xs text-muted-foreground">{value}/{max} completed</span>
        </div>
      )}
    </div>
  );
}
