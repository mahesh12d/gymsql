import { useEffect, useState } from "react";
import { useLocation } from "wouter";
import { useToast } from "@/hooks/use-toast";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function VerifyEmail() {
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const verifyEmail = async () => {
      const params = new URLSearchParams(window.location.search);
      const token = params.get("token");

      if (!token) {
        setStatus("error");
        setMessage("Invalid verification link");
        return;
      }

      try {
        const response = await fetch(`/api/auth/verify-email?token=${token}`);
        const data = await response.json();

        if (response.ok) {
          setStatus("success");
          setMessage("Email verified successfully! Redirecting to home...");
          
          // Store the auth token with correct key
          if (data.token) {
            localStorage.setItem("auth_token", data.token);
          }

          toast({
            title: "Email Verified",
            description: "Your email has been verified successfully. Welcome to SQLGym!",
          });

          // Redirect to home after 2 seconds
          setTimeout(() => {
            window.location.href = "/";
          }, 2000);
        } else {
          setStatus("error");
          setMessage(data.detail || "Email verification failed");
        }
      } catch (error) {
        setStatus("error");
        setMessage("An error occurred during verification");
        console.error("Email verification error:", error);
      }
    };

    verifyEmail();
  }, [toast]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-purple-50 via-white to-blue-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900 p-4">
      <Card className="w-full max-w-md" data-testid="card-verification">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4">
            {status === "loading" && (
              <Loader2 className="w-16 h-16 text-purple-600 animate-spin" data-testid="icon-loading" />
            )}
            {status === "success" && (
              <CheckCircle2 className="w-16 h-16 text-green-600" data-testid="icon-success" />
            )}
            {status === "error" && (
              <XCircle className="w-16 h-16 text-red-600" data-testid="icon-error" />
            )}
          </div>
          <CardTitle className="text-2xl font-bold" data-testid="text-title">
            {status === "loading" && "Verifying Email..."}
            {status === "success" && "Email Verified!"}
            {status === "error" && "Verification Failed"}
          </CardTitle>
          <CardDescription data-testid="text-message">{message}</CardDescription>
        </CardHeader>
        <CardContent className="text-center">
          {status === "error" && (
            <Button
              onClick={() => setLocation("/")}
              className="w-full"
              data-testid="button-back-home"
            >
              Back to Home
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
