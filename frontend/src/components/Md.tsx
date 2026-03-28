/**
 * Md — full block markdown (headers, lists, code blocks, tables, etc.)
 * MdInline — inline-only markdown (bold, italic, `code`) — safe to use inside buttons, headings, list items
 */
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const codeClass = 'bg-surface-container-high px-1.5 py-0.5 text-secondary font-mono text-[0.85em] rounded-sm';
const codeBlockClass = 'block bg-surface-container-high p-4 font-mono text-sm text-secondary overflow-x-auto whitespace-pre my-2';

// Inline-only: renders bold, italic, inline code, links — no block elements
export function MdInline({ children }: { children: string }) {
  return (
    <ReactMarkdown
      allowedElements={['strong', 'em', 'code', 'a', 'p']}
      unwrapDisallowed
      components={{
        p: ({ children: c }) => <>{c}</>,
        code: ({ children: c }) => <code className={codeClass}>{c}</code>,
        strong: ({ children: c }) => <strong className="font-bold">{c}</strong>,
        em: ({ children: c }) => <em className="italic">{c}</em>,
        a: ({ href, children: c }) => (
          <a href={href} target="_blank" rel="noopener noreferrer" className="text-secondary hover:text-primary underline">
            {c}
          </a>
        ),
      }}
    >
      {children}
    </ReactMarkdown>
  );
}

// Full block markdown
export function Md({ children, className }: { children: string; className?: string }) {
  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children: c }) => <h1 className="text-2xl font-headline font-bold text-on-surface mt-6 mb-3 first:mt-0">{c}</h1>,
          h2: ({ children: c }) => <h2 className="text-xl font-headline font-bold text-on-surface mt-5 mb-2">{c}</h2>,
          h3: ({ children: c }) => <h3 className="text-base font-bold text-on-surface mt-4 mb-2">{c}</h3>,
          p: ({ children: c }) => <p className="text-on-surface/80 leading-relaxed mb-4 last:mb-0">{c}</p>,
          code: (props: any) => {
            const { children: c, className: cls } = props;
            return cls?.startsWith('language-')
              ? <code className={codeBlockClass}>{c}</code>
              : <code className={codeClass}>{c}</code>;
          },
          pre: ({ children: c }) => <pre className="mb-4">{c}</pre>,
          ul: ({ children: c }) => <ul className="list-disc list-inside space-y-1 mb-4 text-on-surface/80">{c}</ul>,
          ol: ({ children: c }) => <ol className="list-decimal list-inside space-y-1 mb-4 text-on-surface/80">{c}</ol>,
          li: ({ children: c }) => <li className="leading-relaxed">{c}</li>,
          blockquote: ({ children: c }) => (
            <blockquote className="border-l-2 border-primary pl-4 my-4 text-on-surface-variant italic">{c}</blockquote>
          ),
          a: ({ href, children: c }) => (
            <a href={href} target="_blank" rel="noopener noreferrer" className="text-secondary hover:text-primary underline transition-colors">
              {c}
            </a>
          ),
          table: ({ children: c }) => (
            <div className="overflow-x-auto mb-4">
              <table className="w-full text-sm border-collapse">{c}</table>
            </div>
          ),
          th: ({ children: c }) => (
            <th className="text-left border border-outline-variant/20 px-3 py-2 font-bold text-on-surface-variant bg-surface-container-high">{c}</th>
          ),
          td: ({ children: c }) => (
            <td className="border border-outline-variant/20 px-3 py-2 text-on-surface/80">{c}</td>
          ),
          hr: () => <hr className="border-outline-variant/20 my-6" />,
          strong: ({ children: c }) => <strong className="font-bold text-on-surface">{c}</strong>,
          em: ({ children: c }) => <em className="italic text-on-surface/80">{c}</em>,
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
