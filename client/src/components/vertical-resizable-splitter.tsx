import { useState, useRef, useCallback, useEffect } from 'react';

interface VerticalResizableSplitterProps {
  topPanel: React.ReactNode;
  bottomPanel: React.ReactNode;
  defaultTopHeight?: number;
  minTopHeight?: number;
  minBottomHeight?: number;
  className?: string;
}

export default function VerticalResizableSplitter({
  topPanel,
  bottomPanel,
  defaultTopHeight = 70,
  minTopHeight = 30,
  minBottomHeight = 20,
  className = ''
}: VerticalResizableSplitterProps) {
  const [topHeight, setTopHeight] = useState(defaultTopHeight);
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    setIsDragging(true);
    e.preventDefault();
  }, []);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging || !containerRef.current) return;

    const containerRect = containerRef.current.getBoundingClientRect();
    const newTopHeight = ((e.clientY - containerRect.top) / containerRect.height) * 100;
    
    // Apply constraints
    const constrainedHeight = Math.max(
      minTopHeight,
      Math.min(100 - minBottomHeight, newTopHeight)
    );
    
    setTopHeight(constrainedHeight);
  }, [isDragging, minTopHeight, minBottomHeight]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Add event listeners when dragging
  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = 'row-resize';
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
      className={`flex flex-col h-full w-full ${className}`}
    >
      {/* Top Panel */}
      <div 
        style={{ height: `${topHeight}%` }}
        className="flex-shrink-0 overflow-hidden"
      >
        {topPanel}
      </div>
      
      {/* Resizer */}
      <div
        className="h-1 bg-border hover:bg-primary/50 cursor-row-resize flex-shrink-0 transition-colors relative group"
        onMouseDown={handleMouseDown}
      >
        <div className="absolute inset-x-0 -top-1 -bottom-1 group-hover:bg-primary/20" />
      </div>
      
      {/* Bottom Panel */}
      <div 
        style={{ height: `${100 - topHeight}%` }}
        className="flex-1 overflow-hidden"
      >
        {bottomPanel}
      </div>
    </div>
  );
}