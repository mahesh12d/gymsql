import { memo } from 'react';
import { CardHeader } from '@/components/ui/card';
import { CompanyLogo } from '@/components/CompanyLogo';
import { DifficultyBadge } from '@/components/DifficultyBadge';
import TimerControls from '@/components/TimerControls';
import DatabaseSelector from '@/components/DatabaseSelector';

interface EditorHeaderProps {
  company: string;
  difficulty: string;
  onCompanyClick: (company: string) => void;
  onDifficultyClick: (difficulty: string) => void;
  className?: string;
  problem?: any;
}

const EditorHeader = memo(function EditorHeader({
  company,
  difficulty,
  onCompanyClick,
  onDifficultyClick,
  className,
  problem,
}: EditorHeaderProps) {
  return (
    <CardHeader className={`bg-muted/50 px-4 py-2 flex-shrink-0 ${className || ''}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          {/* Company field */}
          <CompanyLogo
            companyName={company}
            variant="full"
            size="md"
            onClick={() => onCompanyClick(company)}
            data-testid="company-selector"
          />

          {/* Difficulty field */}
          <DifficultyBadge
            difficulty={difficulty}
            variant="full"
            size="md"
            showIcon={true}
            showBars={true}
            onClick={() => onDifficultyClick(difficulty)}
            data-testid="difficulty-selector"
          />
        </div>

        <div className="flex items-center space-x-3">
          {/* Timer Controls */}
          <TimerControls />

          {/* Database Selector */}
          <DatabaseSelector problem={problem} />
        </div>
      </div>
    </CardHeader>
  );
});

export default EditorHeader;