import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

interface Column {
  name: string;
  type: string;
}

interface TableData {
  name: string;
  columns: Column[];
  sampleData: Record<string, any>[];
}

interface TableDisplayProps {
  tables: TableData[];
  expectedOutput?: Record<string, any>[];
}

export default function TableDisplay({ tables, expectedOutput }: TableDisplayProps) {
  const renderDataTable = (data: Record<string, any>[], title: string) => {
    if (!data || data.length === 0) return null;

    const headers = Object.keys(data[0]);
    
    return (
      <div className="mb-6">
        <h4 className="font-semibold text-sm text-foreground mb-3">{title}</h4>
        <div className="border rounded-lg overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/50">
                {headers.map((header) => (
                  <TableHead key={header} className="font-semibold text-foreground">
                    {header}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((row, index) => (
                <TableRow key={index}>
                  {headers.map((header) => (
                    <TableCell key={header} className="py-2">
                      {row[header]}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {tables.map((table) => (
        <div key={table.name} className="space-y-4">
          {/* Table Schema */}
          <div>
            <h4 className="font-semibold text-sm text-foreground mb-3">
              <span className="font-bold">{table.name}</span> Table:
            </h4>
            <div className="border rounded-lg overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/50">
                    <TableHead className="font-semibold text-foreground">Column Name</TableHead>
                    <TableHead className="font-semibold text-foreground">Type</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {table.columns.map((column) => (
                    <TableRow key={column.name}>
                      <TableCell className="py-2 font-mono text-sm">{column.name}</TableCell>
                      <TableCell className="py-2">{column.type}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>

          {/* Sample Data */}
          {table.sampleData && table.sampleData.length > 0 && 
            renderDataTable(table.sampleData, `${table.name} Example Input:`)
          }
        </div>
      ))}

      {/* Expected Output */}
      {expectedOutput && expectedOutput.length > 0 && 
        renderDataTable(expectedOutput, "Expected Output:")
      }
    </div>
  );
}