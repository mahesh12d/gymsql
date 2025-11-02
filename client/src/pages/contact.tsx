import { useState, useEffect } from "react";
import { Link } from "wouter";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ArrowLeft, Mail, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";
import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import contactContent from "@/data/legal/contact.md?raw";

interface ContactFormData {
  name: string;
  email: string;
  subject: string;
  message: string;
}

export default function ContactPage() {
  const [formData, setFormData] = useState<ContactFormData>({
    name: "",
    email: "",
    subject: "",
    message: ""
  });
  const { toast } = useToast();

  useEffect(() => {
    // Set page title and meta description for SEO
    document.title = "Contact Us | SQLGym";
    
    let metaDescription = document.querySelector('meta[name="description"]');
    if (!metaDescription) {
      metaDescription = document.createElement('meta');
      metaDescription.setAttribute('name', 'description');
      document.head.appendChild(metaDescription);
    }
    metaDescription.setAttribute('content', "Get in touch with the SQLGym team. We're here to help with questions, feedback, and support.");

    // Add Open Graph tags for social sharing
    let ogTitle = document.querySelector('meta[property="og:title"]');
    if (!ogTitle) {
      ogTitle = document.createElement('meta');
      ogTitle.setAttribute('property', 'og:title');
      document.head.appendChild(ogTitle);
    }
    ogTitle.setAttribute('content', "Contact Us | SQLGym");

    let ogDescription = document.querySelector('meta[property="og:description"]');
    if (!ogDescription) {
      ogDescription = document.createElement('meta');
      ogDescription.setAttribute('property', 'og:description');
      document.head.appendChild(ogDescription);
    }
    ogDescription.setAttribute('content', "Get in touch with the SQLGym team. We're here to help with questions, feedback, and support.");
  }, []);

  const contactMutation = useMutation({
    mutationFn: async (data: ContactFormData) => {
      const response = await apiRequest("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
      });
      return response;
    },
    onSuccess: () => {
      toast({
        title: "Message Sent!",
        description: "Thank you for contacting us. We'll get back to you within 24-48 hours.",
      });
      // Reset form
      setFormData({
        name: "",
        email: "",
        subject: "",
        message: ""
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Error",
        description: error.message || "Failed to send message. Please try again or email us directly at support@sqlgym.com",
        variant: "destructive",
      });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Basic validation
    if (!formData.name || !formData.email || !formData.subject || !formData.message) {
      toast({
        title: "Missing Information",
        description: "Please fill in all fields before submitting.",
        variant: "destructive",
      });
      return;
    }

    // Email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(formData.email)) {
      toast({
        title: "Invalid Email",
        description: "Please enter a valid email address.",
        variant: "destructive",
      });
      return;
    }

    contactMutation.mutate(formData);
  };

  const handleChange = (field: keyof ContactFormData, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  return (
    <div className="min-h-screen bg-background dark:bg-background">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
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

        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12">
            {/* Contact Form */}
            <Card data-testid="card-contact-form">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Mail className="h-5 w-5" />
                  Send Us a Message
                </CardTitle>
                <CardDescription>
                  Fill out the form below and we'll get back to you as soon as possible.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="name">Name *</Label>
                    <Input
                      id="name"
                      data-testid="input-contact-name"
                      placeholder="Your full name"
                      value={formData.name}
                      onChange={(e) => handleChange("name", e.target.value)}
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="email">Email *</Label>
                    <Input
                      id="email"
                      type="email"
                      data-testid="input-contact-email"
                      placeholder="your.email@example.com"
                      value={formData.email}
                      onChange={(e) => handleChange("email", e.target.value)}
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="subject">Subject *</Label>
                    <Input
                      id="subject"
                      data-testid="input-contact-subject"
                      placeholder="What is this regarding?"
                      value={formData.subject}
                      onChange={(e) => handleChange("subject", e.target.value)}
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="message">Message *</Label>
                    <Textarea
                      id="message"
                      data-testid="textarea-contact-message"
                      placeholder="Tell us how we can help..."
                      rows={6}
                      value={formData.message}
                      onChange={(e) => handleChange("message", e.target.value)}
                      required
                    />
                  </div>

                  <Button
                    type="submit"
                    className="w-full gap-2"
                    disabled={contactMutation.isPending}
                    data-testid="button-submit-contact"
                  >
                    {contactMutation.isPending ? (
                      <>
                        <div className="w-4 h-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin" />
                        Sending...
                      </>
                    ) : (
                      <>
                        <Send className="h-4 w-4" />
                        Send Message
                      </>
                    )}
                  </Button>
                </form>
              </CardContent>
            </Card>

            {/* Quick Contact Info */}
            <div className="space-y-6">
              <Card data-testid="card-contact-info">
                <CardHeader>
                  <CardTitle>Other Ways to Reach Us</CardTitle>
                  <CardDescription>
                    Choose the contact method that works best for you
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-start gap-3">
                    <Mail className="h-5 w-5 text-primary mt-0.5" />
                    <div>
                      <p className="font-medium">Email Support</p>
                      <a 
                        href="mailto:support@sqlgym.com" 
                        className="text-sm text-primary hover:underline"
                        data-testid="link-email-support"
                      >
                        support@sqlgym.com
                      </a>
                      <p className="text-xs text-muted-foreground mt-1">
                        Response time: 24-48 hours
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <Mail className="h-5 w-5 text-primary mt-0.5" />
                    <div>
                      <p className="font-medium">Business Inquiries</p>
                      <a 
                        href="mailto:business@sqlgym.com" 
                        className="text-sm text-primary hover:underline"
                        data-testid="link-email-business"
                      >
                        business@sqlgym.com
                      </a>
                      <p className="text-xs text-muted-foreground mt-1">
                        For partnerships and enterprise solutions
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <Mail className="h-5 w-5 text-primary mt-0.5" />
                    <div>
                      <p className="font-medium">Bug Reports</p>
                      <a 
                        href="mailto:bugs@sqlgym.com" 
                        className="text-sm text-primary hover:underline"
                        data-testid="link-email-bugs"
                      >
                        bugs@sqlgym.com
                      </a>
                      <p className="text-xs text-muted-foreground mt-1">
                        Help us improve by reporting issues
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card data-testid="card-faq">
                <CardHeader>
                  <CardTitle>Quick Answers</CardTitle>
                  <CardDescription>
                    Common questions answered
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div>
                    <p className="font-medium text-sm">Forgot your password?</p>
                    <p className="text-xs text-muted-foreground">
                      Click "Forgot Password" on the login page
                    </p>
                  </div>
                  <div>
                    <p className="font-medium text-sm">Code not running?</p>
                    <p className="text-xs text-muted-foreground">
                      Check syntax and error messages carefully
                    </p>
                  </div>
                  <div>
                    <p className="font-medium text-sm">Premium questions?</p>
                    <p className="text-xs text-muted-foreground">
                      See our <Link href="/pricing"><a className="text-primary hover:underline">Pricing page</a></Link>
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>

          {/* Additional Information from Markdown */}
          <article 
            className="prose prose-slate dark:prose-invert max-w-none mt-12
                       prose-headings:font-bold prose-headings:text-foreground dark:prose-headings:text-foreground
                       prose-h2:text-2xl prose-h2:mt-8 prose-h2:mb-4
                       prose-h3:text-xl prose-h3:mt-6 prose-h3:mb-3
                       prose-p:text-muted-foreground dark:prose-p:text-muted-foreground
                       prose-a:text-primary hover:prose-a:text-primary/80"
            data-testid="article-contact-info"
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {contactContent}
            </ReactMarkdown>
          </article>
        </div>
      </div>
    </div>
  );
}
