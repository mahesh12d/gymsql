import { memo, useState } from 'react';
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
}

const DatabaseSelector = memo(function DatabaseSelector({ className }: DatabaseSelectorProps) {
  const [selectedDatabase, setSelectedDatabase] = useState("PostgreSQL 14");

  const databases = [
    "PostgreSQL 14",
    "PostgreSQL 15", 
    "PostgreSQL 16",
    "MySQL 8.0",
    "SQLite"
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