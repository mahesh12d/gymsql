import { memo } from 'react';
import { Timer, Play, Pause, Square } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useTimer } from '@/hooks/use-timer';

interface TimerControlsProps {
  className?: string;
}

const TimerControls = memo(function TimerControls({ className }: TimerControlsProps) {
  const { formattedTime, isRunning, start, pause, reset } = useTimer();

  return (
    <div className={`flex items-center space-x-1 px-2 py-1 rounded border bg-muted text-muted-foreground border-border ${className || ''}`}>
      {/* Play/Pause Toggle button */}
      <Button
        onClick={isRunning ? pause : start}
        variant="ghost"
        size="sm"
        className={`h-5 w-5 p-0 hover:bg-transparent ${
          isRunning
            ? "text-orange-600 dark:text-orange-400"
            : "text-muted-foreground"
        }`}
        data-testid={
          isRunning
            ? "button-pause-timer"
            : "button-start-timer"
        }
        aria-label={isRunning ? "Pause timer" : "Start timer"}
      >
        {isRunning ? (
          <Pause className="h-3 w-3" />
        ) : (
          <Play className="h-3 w-3" />
        )}
      </Button>

      {/* Timer Display */}
      <div className="flex items-center space-x-1">
        <Timer
          className={`h-3 w-3 ${
            isRunning
              ? "text-orange-600 dark:text-orange-400"
              : "text-muted-foreground"
          }`}
        />
        <span
          className={`font-mono text-xs ${
            isRunning
              ? "text-orange-600 dark:text-orange-400 font-medium"
              : "text-muted-foreground"
          }`}
          data-testid="text-timer"
        >
          {formattedTime}
        </span>
      </div>

      {/* Reset button */}
      <Button
        onClick={reset}
        variant="ghost"
        size="sm"
        className={`h-5 w-5 p-0 hover:bg-transparent ${
          isRunning
            ? "text-orange-600 dark:text-orange-400"
            : "text-muted-foreground"
        }`}
        data-testid="button-reset-timer"
        aria-label="Reset timer"
      >
        <Square className="h-3 w-3" />
      </Button>
    </div>
  );
});

export default TimerControls;