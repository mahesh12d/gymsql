import { useEffect } from "react";
import { Link } from "wouter";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

interface LegalLayoutProps {
  title: string;
  description: string;
  content: string;
  showBackButton?: boolean;
}

export default function LegalLayout({ 
  title, 
  description, 
  content, 
  showBackButton = true 
}: LegalLayoutProps) {
  useEffect(() => {
    // Set page title and meta description for SEO
    document.title = `${title} | GymSql`;
    
    // Update meta description
    let metaDescription = document.querySelector('meta[name="description"]');
    if (!metaDescription) {
      metaDescription = document.createElement('meta');
      metaDescription.setAttribute('name', 'description');
      document.head.appendChild(metaDescription);
    }
    metaDescription.setAttribute('content', description);

    // Update Open Graph tags for social sharing
    let ogTitle = document.querySelector('meta[property="og:title"]');
    if (!ogTitle) {
      ogTitle = document.createElement('meta');
      ogTitle.setAttribute('property', 'og:title');
      document.head.appendChild(ogTitle);
    }
    ogTitle.setAttribute('content', `${title} | GymSql`);

    let ogDescription = document.querySelector('meta[property="og:description"]');
    if (!ogDescription) {
      ogDescription = document.createElement('meta');
      ogDescription.setAttribute('property', 'og:description');
      document.head.appendChild(ogDescription);
    }
    ogDescription.setAttribute('content', description);
  }, [title, description]);

  return (
    <div className="min-h-screen bg-background dark:bg-background">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {showBackButton && (
          <div className="mb-6">
            <Link href="/">
              <Button 
                variant="ghost" 
                className="gap-2"
                data-testid="button-back-home"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to Home
              </Button>
            </Link>
          </div>
        )}

        <div className="max-w-4xl mx-auto">
          <article 
            className="prose prose-slate dark:prose-invert max-w-none
                       prose-headings:font-bold prose-headings:text-foreground dark:prose-headings:text-foreground
                       prose-h1:text-4xl prose-h1:mb-4
                       prose-h2:text-2xl prose-h2:mt-8 prose-h2:mb-4
                       prose-h3:text-xl prose-h3:mt-6 prose-h3:mb-3
                       prose-p:text-muted-foreground dark:prose-p:text-muted-foreground prose-p:leading-7
                       prose-a:text-primary hover:prose-a:text-primary/80 dark:prose-a:text-primary dark:hover:prose-a:text-primary/80
                       prose-strong:text-foreground dark:prose-strong:text-foreground
                       prose-ul:text-muted-foreground dark:prose-ul:text-muted-foreground
                       prose-ol:text-muted-foreground dark:prose-ol:text-muted-foreground
                       prose-li:my-2
                       prose-code:text-primary prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded
                       prose-pre:bg-muted prose-pre:border prose-pre:border-border
                       prose-blockquote:border-l-primary prose-blockquote:text-muted-foreground"
            data-testid="article-legal-content"
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {content}
            </ReactMarkdown>
          </article>
        </div>
      </div>
    </div>
  );
}
