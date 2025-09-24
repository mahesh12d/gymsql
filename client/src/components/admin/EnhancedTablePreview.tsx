import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Edit2, Save, X, Eye, EyeOff, Database, Columns, Hash } from 'lucide-react';

interface TableColumn {
  name: string;
  type: string;
}

interface TableData {
  name: string;
  columns: TableColumn[];
  sample_data: Record<string, any>[];
}

interface EnhancedTablePreviewProps {
  tables: TableData[];
  onTableUpdate?: (tables: TableData[]) => void;
  readOnly?: boolean;
}

const COLUMN_TYPES = [
  'VARCHAR', 'TEXT', 'INTEGER', 'BIGINT', 'DECIMAL', 'FLOAT', 'DOUBLE',
  'BOOLEAN', 'DATE', 'TIMESTAMP', 'TIME', 'JSON', 'UUID'
];

export function EnhancedTablePreview({ tables, onTableUpdate, readOnly = false }: EnhancedTablePreviewProps) {
  const [editingTable, setEditingTable] = useState<number | null>(null);
  const [showSampleData, setShowSampleData] = useState<{ [key: number]: boolean }>({});
  const [editedTables, setEditedTables] = useState<TableData[]>([]);

  // Deep clone helper function
  const deepCloneTables = (tablesToClone: TableData[]): TableData[] => {
    return tablesToClone.map(table => ({
      name: table.name,
      columns: table.columns.map(col => ({
        name: col.name,
        type: col.type
      })),
      sample_data: table.sample_data.map(row => ({ ...row }))
    }));
  };

  const handleEditTable = (index: number) => {
    setEditingTable(index);
    // Create a deep clone to prevent mutations to the original data
    setEditedTables(deepCloneTables(tables));
  };

  const handleSaveTable = (index: number) => {
    if (onTableUpdate) {
      // Pass the deep-cloned edited tables to the parent
      onTableUpdate(deepCloneTables(editedTables));
    }
    setEditingTable(null);
    setEditedTables([]);
  };

  const handleCancelEdit = () => {
    setEditingTable(null);
    // Clear the edited tables to prevent any lingering references
    setEditedTables([]);
  };

  const handleColumnNameChange = (tableIndex: number, columnIndex: number, newName: string) => {
    const updated = deepCloneTables(editedTables);
    updated[tableIndex].columns[columnIndex].name = newName;
    setEditedTables(updated);
  };

  const handleColumnTypeChange = (tableIndex: number, columnIndex: number, newType: string) => {
    const updated = deepCloneTables(editedTables);
    updated[tableIndex].columns[columnIndex].type = newType;
    setEditedTables(updated);
  };

  const handleTableNameChange = (tableIndex: number, newName: string) => {
    const updated = deepCloneTables(editedTables);
    updated[tableIndex].name = newName;
    setEditedTables(updated);
  };

  const toggleSampleData = (tableIndex: number) => {
    setShowSampleData(prev => ({
      ...prev,
      [tableIndex]: !prev[tableIndex]
    }));
  };

  const renderSampleData = (table: TableData) => {
    if (!table.sample_data || table.sample_data.length === 0) return null;

    const headers = Object.keys(table.sample_data[0]);
    const displayRows = table.sample_data.slice(0, 5); // Show first 5 rows

    return (
      <div className="mt-4 border rounded-lg overflow-hidden">
        <div className="bg-muted/30 px-3 py-2 border-b">
          <h5 className="text-sm font-medium text-muted-foreground">Sample Data</h5>
        </div>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/20">
                {headers.map((header) => (
                  <TableHead key={header} className="font-medium text-xs">
                    {header}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {displayRows.map((row, index) => (
                <TableRow key={index} className="text-xs">
                  {headers.map((header) => (
                    <TableCell key={header} className="py-1 px-2 max-w-32 truncate">
                      {String(row[header] ?? '')}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        {table.sample_data.length > 5 && (
          <div className="px-3 py-2 text-xs text-muted-foreground bg-muted/10 border-t">
            ... and {table.sample_data.length - 5} more rows
          </div>
        )}
      </div>
    );
  };

  if (tables.length === 0) {
    return (
      <Card>
        <CardContent className="p-6 text-center text-muted-foreground">
          <Database className="mx-auto h-12 w-12 mb-3 opacity-50" />
          <p>No tables loaded yet</p>
          <p className="text-sm">Load tables from a datasource to see the preview</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <Database className="h-5 w-5" />
          Tables Preview ({tables.length})
        </h3>
        {!readOnly && (
          <Badge variant="outline" className="text-xs">
            Click table names or columns to edit
          </Badge>
        )}
      </div>

      {tables.map((table, tableIndex) => {
        const isEditing = editingTable === tableIndex;
        const currentTable = isEditing && editedTables.length > 0 ? editedTables[tableIndex] : table;

        return (
          <Card key={tableIndex} className="overflow-hidden">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {isEditing ? (
                    <Input
                      value={currentTable.name}
                      onChange={(e) => handleTableNameChange(tableIndex, e.target.value)}
                      className="text-lg font-semibold h-auto py-1 px-2 w-48"
                      data-testid={`input-table-name-${tableIndex}`}
                    />
                  ) : (
                    <CardTitle 
                      className={`flex items-center gap-2 ${!readOnly ? 'cursor-pointer hover:text-primary transition-colors' : ''}`}
                      onClick={() => !readOnly && handleEditTable(tableIndex)}
                      data-testid={`text-table-name-${tableIndex}`}
                    >
                      <Columns className="h-4 w-4 text-primary" />
                      {table.name}
                    </CardTitle>
                  )}
                  
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Badge variant="secondary" className="text-xs bg-blue-50 text-blue-700 dark:bg-blue-900 dark:text-blue-300">
                      <Hash className="h-3 w-3 mr-1" />
                      {table.columns.length} column{table.columns.length !== 1 ? 's' : ''}
                    </Badge>
                    <Badge variant="secondary" className="text-xs bg-green-50 text-green-700 dark:bg-green-900 dark:text-green-300">
                      <Database className="h-3 w-3 mr-1" />
                      {table.sample_data.length} row{table.sample_data.length !== 1 ? 's' : ''}
                    </Badge>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {table.sample_data.length > 0 && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => toggleSampleData(tableIndex)}
                      data-testid={`button-toggle-sample-${tableIndex}`}
                    >
                      {showSampleData[tableIndex] ? (
                        <>
                          <EyeOff className="h-4 w-4 mr-1" />
                          Hide Data
                        </>
                      ) : (
                        <>
                          <Eye className="h-4 w-4 mr-1" />
                          Show Data
                        </>
                      )}
                    </Button>
                  )}

                  {!readOnly && (
                    <>
                      {isEditing ? (
                        <div className="flex gap-1">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleSaveTable(tableIndex)}
                            data-testid={`button-save-table-${tableIndex}`}
                          >
                            <Save className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={handleCancelEdit}
                            data-testid={`button-cancel-edit-${tableIndex}`}
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                      ) : (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleEditTable(tableIndex)}
                          data-testid={`button-edit-table-${tableIndex}`}
                        >
                          <Edit2 className="h-4 w-4 mr-1" />
                          Edit
                        </Button>
                      )}
                    </>
                  )}
                </div>
              </div>
            </CardHeader>

            <CardContent className="pt-0">
              {/* Schema Display */}
              <div className="border rounded-lg overflow-hidden">
                <div className="bg-muted/30 px-3 py-2 border-b">
                  <h5 className="text-sm font-medium text-muted-foreground">Table Schema</h5>
                </div>
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/20">
                      <TableHead className="font-medium">Column Name</TableHead>
                      <TableHead className="font-medium">Data Type</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {currentTable.columns.map((column, columnIndex) => (
                      <TableRow key={columnIndex}>
                        <TableCell className="py-2">
                          {isEditing ? (
                            <Input
                              value={column.name}
                              onChange={(e) => handleColumnNameChange(tableIndex, columnIndex, e.target.value)}
                              className="font-mono text-sm h-8"
                              data-testid={`input-column-name-${tableIndex}-${columnIndex}`}
                            />
                          ) : (
                            <span 
                              className={`font-mono text-sm ${!readOnly ? 'cursor-pointer hover:text-primary' : ''}`}
                              onClick={() => !readOnly && handleEditTable(tableIndex)}
                              data-testid={`text-column-name-${tableIndex}-${columnIndex}`}
                            >
                              {column.name}
                            </span>
                          )}
                        </TableCell>
                        <TableCell className="py-2">
                          {isEditing ? (
                            <select
                              value={column.type}
                              onChange={(e) => handleColumnTypeChange(tableIndex, columnIndex, e.target.value)}
                              className="h-8 w-full border rounded px-2 text-sm"
                              data-testid={`select-column-type-${tableIndex}-${columnIndex}`}
                            >
                              {COLUMN_TYPES.map((type) => (
                                <option key={type} value={type}>
                                  {type}
                                </option>
                              ))}
                            </select>
                          ) : (
                            <Badge 
                              variant="outline" 
                              className={`text-xs ${!readOnly ? 'cursor-pointer hover:bg-primary/10' : ''}`}
                              onClick={() => !readOnly && handleEditTable(tableIndex)}
                              data-testid={`text-column-type-${tableIndex}-${columnIndex}`}
                            >
                              {column.type}
                            </Badge>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Sample Data */}
              {showSampleData[tableIndex] && renderSampleData(table)}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}