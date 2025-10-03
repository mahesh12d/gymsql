import { useState, useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Bold,
  Italic,
  Strikethrough,
  Code,
  List,
  ListOrdered,
  Quote,
  Type,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import CodeMirror from "@uiw/react-codemirror";
import { oneDark } from "@codemirror/theme-one-dark";

interface RichTextEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  minHeight?: string;
  testId?: string;
}

export function RichTextEditor({
  value,
  onChange,
  placeholder = "Type your content here...",
  minHeight = "120px",
  testId,
}: RichTextEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [codeDialogOpen, setCodeDialogOpen] = useState(false);
  const [codeContent, setCodeContent] = useState("");

  const insertAtCursor = useCallback(
    (before: string, after: string = "", placeholder: string = "") => {
      const textarea = textareaRef.current;
      if (!textarea) return;

      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const selectedText = value.substring(start, end);
      
      const textToInsert = selectedText || "";

      const newValue =
        value.substring(0, start) +
        before +
        textToInsert +
        after +
        value.substring(end);

      onChange(newValue);

      setTimeout(() => {
        textarea.focus();
        const newCursorPos = start + before.length;
        textarea.setSelectionRange(newCursorPos, newCursorPos);
      }, 0);
    },
    [value, onChange]
  );

  const handleBold = () => insertAtCursor("**", "**", "bold text");
  const handleItalic = () => insertAtCursor("*", "*", "italic text");
  const handleStrikethrough = () => insertAtCursor("~~", "~~", "strikethrough");
  const handleInlineCode = () => insertAtCursor("`", "`", "code");
  const handleQuote = () => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const lineStart = value.lastIndexOf("\n", start - 1) + 1;
    const newValue =
      value.substring(0, lineStart) + "> " + value.substring(lineStart);

    onChange(newValue);
  };

  const handleUnorderedList = () => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const lineStart = value.lastIndexOf("\n", start - 1) + 1;
    const newValue =
      value.substring(0, lineStart) + "- " + value.substring(lineStart);

    onChange(newValue);
  };

  const handleOrderedList = () => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const lineStart = value.lastIndexOf("\n", start - 1) + 1;
    const newValue =
      value.substring(0, lineStart) + "1. " + value.substring(lineStart);

    onChange(newValue);
  };

  const handleInsertCodeBlock = () => {
    if (!codeContent.trim()) return;

    const codeBlock = `\n\`\`\`\n${codeContent}\n\`\`\`\n`;
    const textarea = textareaRef.current;
    if (!textarea) {
      onChange(value + codeBlock);
    } else {
      const start = textarea.selectionStart;
      const newValue =
        value.substring(0, start) + codeBlock + value.substring(start);
      onChange(newValue);
    }

    setCodeContent("");
    setCodeDialogOpen(false);
  };

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1 p-2 border border-border rounded-t-md bg-muted/30">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={handleBold}
          data-testid="button-format-bold"
          className="h-8 w-8 p-0"
          title="Bold"
        >
          <Bold className="h-4 w-4" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={handleItalic}
          data-testid="button-format-italic"
          className="h-8 w-8 p-0"
          title="Italic"
        >
          <Italic className="h-4 w-4" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={handleStrikethrough}
          data-testid="button-format-strikethrough"
          className="h-8 w-8 p-0"
          title="Strikethrough"
        >
          <Strikethrough className="h-4 w-4" />
        </Button>
        <div className="w-px h-8 bg-border mx-1" />
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={handleInlineCode}
          data-testid="button-format-inline-code"
          className="h-8 w-8 p-0"
          title="Inline Code"
        >
          <Type className="h-4 w-4" />
        </Button>
        <Dialog open={codeDialogOpen} onOpenChange={setCodeDialogOpen}>
          <DialogTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              data-testid="button-format-code-block"
              className="h-8 w-8 p-0"
              title="Code Block"
            >
              <Code className="h-4 w-4" />
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-3xl">
            <DialogHeader>
              <DialogTitle>Insert Code Block</DialogTitle>
            </DialogHeader>
            <div className="border border-border rounded-md overflow-hidden">
              <CodeMirror
                value={codeContent}
                onChange={setCodeContent}
                theme={oneDark}
                extensions={[]}
                minHeight="200px"
                maxHeight="400px"
                basicSetup={{
                  lineNumbers: true,
                  highlightActiveLineGutter: true,
                  highlightActiveLine: true,
                  foldGutter: true,
                }}
              />
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setCodeDialogOpen(false)}
                data-testid="button-cancel-code"
              >
                Cancel
              </Button>
              <Button
                type="button"
                onClick={handleInsertCodeBlock}
                data-testid="button-insert-code"
              >
                Insert Code
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
        <div className="w-px h-8 bg-border mx-1" />
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={handleUnorderedList}
          data-testid="button-format-list"
          className="h-8 w-8 p-0"
          title="Unordered List"
        >
          <List className="h-4 w-4" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={handleOrderedList}
          data-testid="button-format-ordered-list"
          className="h-8 w-8 p-0"
          title="Ordered List"
        >
          <ListOrdered className="h-4 w-4" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={handleQuote}
          data-testid="button-format-quote"
          className="h-8 w-8 p-0"
          title="Quote"
        >
          <Quote className="h-4 w-4" />
        </Button>
      </div>
      <Textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="resize-none rounded-t-none border-t-0 font-mono text-sm"
        style={{ minHeight }}
        data-testid={testId}
      />
    </div>
  );
}
