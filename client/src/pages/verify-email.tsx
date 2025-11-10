import { useState } from "react";
import { useLocation } from "wouter";
import { useToast } from "@/hooks/use-toast";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { CheckCircle2, Mail, Loader2 } from "lucide-react";
import { apiRequest } from "@/lib/queryClient";

export default function VerifyEmail() {
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const [code, setCode] = useState("");
  // Get email from URL params
  const urlParams = new URLSearchParams(window.location.search);
  const emailFromUrl = urlParams.get("email") || "";
  const [email, setEmail] = useState(emailFromUrl);
  const [isVerifying, setIsVerifying] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [verified, setVerified] = useState(false);

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!email || !code) {
      toast({
        title: "Missing Information",
        description: "Please enter both your email and verification code",
        variant: "destructive",
      });
      return;
    }

    if (code.length !== 6 || !/^\d+$/.test(code)) {
      toast({
        title: "Invalid Code",
        description: "Please enter a valid 6-digit verification code",
        variant: "destructive",
      });
      return;
    }

    setIsVerifying(true);

    try {
      const res = await apiRequest("POST", "/api/auth/verify-code", { email, code });
      const response = await res.json();

      if (response.token) {
        localStorage.setItem("auth_token", response.token);
      }

      setVerified(true);

      toast({
        title: "Email Verified",
        description: "Your email has been verified successfully. Welcome to GymSql!",
      });

      // Redirect to home after 2 seconds
      setTimeout(() => {
        window.location.href = "/";
      }, 2000);
    } catch (error: any) {
      toast({
        title: "Verification Failed",
        description: error.message || "Invalid or expired verification code",
        variant: "destructive",
      });
    } finally {
      setIsVerifying(false);
    }
  };

  const handleResend = async () => {
    if (!email) {
      toast({
        title: "Email Required",
        description: "Please enter your email address to resend the code",
        variant: "destructive",
      });
      return;
    }

    setIsResending(true);

    try {
      await apiRequest("POST", "/api/auth/resend-verification", { email });

      toast({
        title: "Code Resent",
        description: "A new verification code has been sent to your email",
      });
    } catch (error: any) {
      toast({
        title: "Resend Failed",
        description: error.message || "Failed to resend verification code",
        variant: "destructive",
      });
    } finally {
      setIsResending(false);
    }
  };

  if (verified) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-purple-50 via-white to-blue-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 p-4">
        <Card className="w-full max-w-md" data-testid="card-verification-success">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4">
              <CheckCircle2 className="w-16 h-16 text-green-600" data-testid="icon-success" />
            </div>
            <CardTitle className="text-2xl font-bold" data-testid="text-title">
              Email Verified!
            </CardTitle>
            <CardDescription data-testid="text-message">
              Redirecting to home...
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-purple-50 via-white to-blue-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 p-4">
      <Card className="w-full max-w-md" data-testid="card-verification">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4">
            <Mail className="w-16 h-16 text-purple-600" data-testid="icon-mail" />
          </div>
          <CardTitle className="text-2xl font-bold" data-testid="text-title">
            Verify Your Email
          </CardTitle>
          <CardDescription data-testid="text-description">
            Enter the 6-digit code sent to your email
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleVerify} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email" data-testid="label-email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="your@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={!!emailFromUrl}
                className={emailFromUrl ? "bg-muted" : ""}
                data-testid="input-email"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="code" data-testid="label-code">Verification Code</Label>
              <Input
                id="code"
                type="text"
                placeholder="000000"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                maxLength={6}
                className="text-center text-2xl tracking-widest font-mono"
                required
                data-testid="input-code"
              />
            </div>
            <Button
              type="submit"
              className="w-full"
              disabled={isVerifying}
              data-testid="button-verify"
            >
              {isVerifying ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Verifying...
                </>
              ) : (
                "Verify Email"
              )}
            </Button>
          </form>
          <div className="mt-4 text-center">
            <Button
              variant="link"
              onClick={handleResend}
              disabled={isResending}
              data-testid="button-resend"
            >
              {isResending ? "Resending..." : "Resend Code"}
            </Button>
          </div>
          <div className="mt-4 text-center">
            <Button
              variant="ghost"
              onClick={() => setLocation("/")}
              data-testid="button-back"
            >
              Back to Login
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
