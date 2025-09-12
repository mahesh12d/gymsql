import { useState, useRef, useCallback, useEffect } from 'react';

interface ResizableSplitterProps {
  leftPanel: React.ReactNode;
  rightPanel: React.ReactNode;
  defaultLeftWidth?: number;
  minLeftWidth?: number;
  minRightWidth?: number;
  className?: string;
}

export default function ResizableSplitter({
  leftPanel,
  rightPanel,
  defaultLeftWidth = 50,
  minLeftWidth = 20,
  minRightWidth = 20,
  className = ''
}: ResizableSplitterProps) {
  const [leftWidth, setLeftWidth] = useState(defaultLeftWidth);
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    setIsDragging(true);
    e.preventDefault();
  }, []);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging || !containerRef.current) return;

    const containerRect = containerRef.current.getBoundingClientRect();
    const newLeftWidth = ((e.clientX - containerRect.left) / containerRect.width) * 100;
    
    // Apply constraints
    const constrainedWidth = Math.max(
      minLeftWidth,
      Math.min(100 - minRightWidth, newLeftWidth)
    );
    
    setLeftWidth(constrainedWidth);
  }, [isDragging, minLeftWidth, minRightWidth]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Add event listeners when dragging
  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
      
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      };
    }
  }, [isDragging, handleMouseMove, handleMouseUp]);

  return (
    <div 
      ref={containerRef}
      className={`flex h-full w-full ${className}`}
    >
      {/* Left Panel */}
      <div 
        style={{ width: `${leftWidth}%` }}
        className="flex-shrink-0 overflow-hidden"
      >
        {leftPanel}
      </div>
      
      {/* Resizer */}
      <div
        className="w-1 bg-border hover:bg-primary/50 cursor-col-resize flex-shrink-0 transition-colors relative group"
        onMouseDown={handleMouseDown}
      >
        <div className="absolute inset-y-0 -left-1 -right-1 group-hover:bg-primary/20" />
      </div>
      
      {/* Right Panel */}
      <div 
        style={{ width: `${100 - leftWidth}%` }}
        className="flex-1 overflow-hidden"
      >
        {rightPanel}
      </div>
    </div>
  );
}