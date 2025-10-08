import ReactMarkdown from 'react-markdown';

interface MarkdownMessageProps {
  content: string;
  className?: string;
}

function MarkdownMessage({ content, className = '' }: MarkdownMessageProps) {
  return (
    <div className={`prose prose-sm max-w-none dark:prose-invert break-words overflow-hidden ${className}`}>
      <ReactMarkdown
        components={{
          // Customize heading styles
          h1: ({ children }) => <h1 className="text-lg font-bold mb-2">{children}</h1>,
          h2: ({ children }) => <h2 className="text-base font-bold mb-2">{children}</h2>,
          h3: ({ children }) => <h3 className="text-sm font-bold mb-1">{children}</h3>,
          
          // Customize paragraph styles
          p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
          
          // Customize list styles
          ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>,
          li: ({ children }) => <li className="text-sm">{children}</li>,
          
          // Customize code styles
          code: ({ children, className }) => {
            const isInline = !className;
            if (isInline) {
              return <code className="bg-muted px-1 py-0.5 rounded text-xs font-mono">{children}</code>;
            }
            return <code className="block bg-muted p-2 rounded text-xs font-mono overflow-x-auto">{children}</code>;
          },
          
          // Customize pre styles for code blocks
          pre: ({ children }) => <pre className="bg-muted p-2 rounded text-xs font-mono overflow-x-auto mb-2">{children}</pre>,
          
          // Customize blockquote styles
          blockquote: ({ children }) => <blockquote className="border-l-4 border-muted-foreground/20 pl-4 italic mb-2">{children}</blockquote>,
          
          // Customize strong/bold styles
          strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
          
          // Customize emphasis/italic styles
          em: ({ children }) => <em className="italic">{children}</em>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

export default MarkdownMessage;
