import { Link } from "wouter";

export default function Footer() {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="border-t border-border bg-background dark:bg-background mt-auto">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Company Section */}
          <div>
            <h3 className="font-semibold text-foreground mb-4" data-testid="heading-footer-company">
              Company
            </h3>
            <ul className="space-y-2">
              <li>
                <Link 
                  href="/about"
                  className="text-muted-foreground hover:text-primary transition-colors"
                  data-testid="link-footer-about"
                >
                  About Us
                </Link>
              </li>
              <li>
                <Link 
                  href="/contact"
                  className="text-muted-foreground hover:text-primary transition-colors"
                  data-testid="link-footer-contact"
                >
                  Contact Us
                </Link>
              </li>
            </ul>
          </div>

          {/* Support Section */}
          <div>
            <h3 className="font-semibold text-foreground mb-4" data-testid="heading-footer-support">
              Support
            </h3>
            <ul className="space-y-2">
              <li>
                <Link 
                  href="/terms"
                  className="text-muted-foreground hover:text-primary transition-colors"
                  data-testid="link-footer-terms"
                >
                  Terms and Conditions
                </Link>
              </li>
              <li>
                <Link 
                  href="/privacy"
                  className="text-muted-foreground hover:text-primary transition-colors"
                  data-testid="link-footer-privacy"
                >
                  Privacy Policy
                </Link>
              </li>
            </ul>
          </div>

          {/* Resources Section */}
          <div>
            <h3 className="font-semibold text-foreground mb-4" data-testid="heading-footer-resources">
              Resources
            </h3>
            <ul className="space-y-2">
              <li>
                <Link 
                  href="/problems"
                  className="text-muted-foreground hover:text-primary transition-colors"
                  data-testid="link-footer-problems"
                >
                  Browse Problems
                </Link>
              </li>
              <li>
                <Link 
                  href="/leaderboard"
                  className="text-muted-foreground hover:text-primary transition-colors"
                  data-testid="link-footer-leaderboard"
                >
                  Leaderboard
                </Link>
              </li>
            </ul>
          </div>

          {/* Connect Section */}
          <div>
            <h3 className="font-semibold text-foreground mb-4" data-testid="heading-footer-connect">
              Connect
            </h3>
            <p className="text-sm text-muted-foreground mb-2">
              Join our community and start mastering SQL today.
            </p>
            <a 
              href="mailto:support@gymsql.com" 
              className="text-sm text-primary hover:underline"
              data-testid="link-footer-email"
            >
              support@gymsql.com
            </a>
          </div>
        </div>

        <div className="border-t border-border mt-8 pt-8 flex flex-col sm:flex-row justify-between items-center gap-4">
          <p className="text-sm text-muted-foreground" data-testid="text-copyright">
            © {currentYear} GymSql. All rights reserved.
          </p>
          <p className="text-sm text-muted-foreground">
            Made with ❤️ for SQL learners everywhere
          </p>
        </div>
      </div>
    </footer>
  );
}
