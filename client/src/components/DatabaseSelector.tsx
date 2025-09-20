import { memo, useState, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface DatabaseSelectorProps {
  className?: string;
  problem?: any;
}

const DatabaseSelector = memo(function DatabaseSelector({ className, problem }: DatabaseSelectorProps) {
  // Always use DuckDB to prevent access to main database
  const [selectedDatabase, setSelectedDatabase] = useState("DuckDB");

  // Always keep DuckDB selected regardless of problem data
  useEffect(() => {
    setSelectedDatabase("DuckDB");
  }, [problem]);

  const databases = [
    "DuckDB"
  ];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className={`h-7 px-2 text-xs text-muted-foreground hover:text-foreground border border-border bg-muted ${className || ''}`}
          data-testid="button-db-selector"
        >
          <span>{selectedDatabase}</span>
          <ChevronDown className="h-3 w-3 ml-1" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        {databases.map((db) => (
          <DropdownMenuItem
            key={db}
            onClick={() => setSelectedDatabase(db)}
            className={selectedDatabase === db ? "bg-accent" : ""}
          >
            {db}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
});

export default DatabaseSelector;