import { useMemo } from 'react';
import { sql, PostgreSQL } from '@codemirror/lang-sql';
import { autocompletion } from '@codemirror/autocomplete';
import { EditorView, keymap, placeholder } from '@codemirror/view';
import { defaultKeymap, indentWithTab } from '@codemirror/commands';
import { oneDark } from '@codemirror/theme-one-dark';

interface Problem {
  question?: {
    tables?: Array<{ name: string }>;
  };
}

interface UseCodeMirrorConfigOptions {
  problem?: Problem;
  isDarkMode: boolean;
  onRunQuery: () => void;
}

export function useCodeMirrorConfig({ problem, isDarkMode, onRunQuery }: UseCodeMirrorConfigOptions) {
  // Generate dynamic placeholder based on first table in problem
  const placeholderText = useMemo(() => {
    if (problem?.question?.tables && problem.question.tables.length > 0) {
      const firstTable = problem.question.tables[0];
      const tableName = firstTable.name;
      return `-- Write your SQL query here\nSELECT * FROM "${tableName}";`;
    }
    return "-- Write your SQL query here\nSELECT \n    column1,\n    column2\nFROM table_name\nWHERE condition;";
  }, [problem?.question?.tables]);

  // Memoize extensions to prevent recreation on every render
  const extensions = useMemo(() => [
    sql({
      dialect: PostgreSQL,
      upperCaseKeywords: true,
      schema: {
        customers: ["id", "name", "email"],
        employees: ["id", "name", "department"],
        orders: ["id", "customer_id", "total"],
        order_items: ["id", "order_id", "price", "quantity"],
      },
    }),
    autocompletion(),
    EditorView.lineWrapping,
    placeholder(placeholderText),
    keymap.of([
      ...defaultKeymap,
      indentWithTab,
      {
        key: "Mod-Enter",
        run: () => {
          onRunQuery();
          return true;
        },
      },
    ]),
  ], [placeholderText, onRunQuery]);

  // Memoize theme configuration
  const theme = useMemo(() => {
    if (isDarkMode) {
      return [oneDark];
    }
    return [
      EditorView.theme({
        "&": {
          color: "hsl(var(--foreground))",
          backgroundColor: "hsl(var(--background))",
        },
        ".cm-content": {
          padding: "16px",
          fontSize: "14px",
          fontFamily: "var(--font-mono)",
          minHeight: "200px",
        },
        ".cm-focused": {
          outline: "none",
        },
        ".cm-editor": {
          borderRadius: "0",
        },
        ".cm-scroller": {
          fontFamily: "var(--font-mono)",
        },
        ".cm-line": {
          lineHeight: "1.5",
        },
        "&.cm-focused .cm-cursor": {
          borderLeftColor: "hsl(var(--primary))",
        },
        "&.cm-focused .cm-selectionBackground, .cm-selectionBackground": {
          backgroundColor: "hsl(var(--primary) / 0.2)",
        },
      }),
    ];
  }, [isDarkMode]);

  return {
    extensions,
    theme,
    placeholderText,
  };
}