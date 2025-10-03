import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import CodeMirror from "@uiw/react-codemirror";
import { sql } from "@codemirror/lang-sql";
import { javascript } from "@codemirror/lang-javascript";
import { python } from "@codemirror/lang-python";
import { java } from "@codemirror/lang-java";
import { cpp } from "@codemirror/lang-cpp";
import { materialDark } from "@uiw/codemirror-theme-material";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({
  content,
  className = "",
}: MarkdownRendererProps) {
  return (
    <div className={`prose prose-sm dark:prose-invert max-w-none ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
        code({ inline, className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || "");
          const language = match ? match[1] : "";

          if (!inline) {
            const getLanguageExtension = () => {
              switch (language.toLowerCase()) {
                case 'sql':
                case 'postgres':
                case 'postgresql':
                case 'mysql':
                  return [sql()];
                case 'javascript':
                case 'js':
                case 'jsx':
                  return [javascript()];
                case 'python':
                case 'py':
                  return [python()];
                case 'java':
                  return [java()];
                case 'cpp':
                case 'c++':
                  return [cpp()];
                default:
                  return [];
              }
            };

            return (
              <div className="rounded-md my-2 overflow-hidden">
                <CodeMirror
                  value={String(children).replace(/\n$/, "")}
                  theme={materialDark}
                  extensions={getLanguageExtension()}
                  editable={false}
                  basicSetup={{
                    lineNumbers: false,
                    foldGutter: false,
                    highlightActiveLineGutter: false,
                    highlightActiveLine: false,
                  }}
                  style={{
                    fontSize: '16px',
                  }}
                />
              </div>
            );
          }

          return <code className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono">{children}</code>;
        },
        p({ children }) {
          return <p className="mb-3 last:mb-0">{children}</p>;
        },
        ul({ children }) {
          return <ul className="list-disc list-inside mb-3">{children}</ul>;
        },
        ol({ children }) {
          return <ol className="list-decimal list-inside mb-3">{children}</ol>;
        },
        blockquote({ children }) {
          return (
            <blockquote className="border-l-4 border-primary pl-4 italic my-3 text-muted-foreground">
              {children}
            </blockquote>
          );
        },
        h1({ children }) {
          return (
            <h1 className="text-2xl font-bold mb-3 mt-4 first:mt-0">
              {children}
            </h1>
          );
        },
        h2({ children }) {
          return (
            <h2 className="text-xl font-bold mb-2 mt-3 first:mt-0">
              {children}
            </h2>
          );
        },
        h3({ children }) {
          return (
            <h3 className="text-lg font-semibold mb-2 mt-2 first:mt-0">
              {children}
            </h3>
          );
        },
        a({ href, children }) {
          return (
            <a
              href={href}
              className="text-primary hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              {children}
            </a>
          );
        },
        strong({ children }) {
          return <strong className="font-bold">{children}</strong>;
        },
        em({ children }) {
          return <em className="italic">{children}</em>;
        },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
