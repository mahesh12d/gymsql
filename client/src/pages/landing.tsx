import { useState, useEffect } from "react";
import { useLocation } from "wouter";
import { Code } from "lucide-react";
import { FaGoogle } from "react-icons/fa";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useAuth } from "@/hooks/use-auth";
import { authApi } from "@/lib/auth";
import { useToast } from "@/hooks/use-toast";

const loginSchema = z.object({
  email: z.string().email("Invalid email address"),
  password: z.string().min(6, "Password must be at least 6 characters"),
});

const registerSchema = z.object({
  username: z.string().min(3, "Username must be at least 3 characters"),
  email: z.string().email("Invalid email address"),
  password: z.string().min(6, "Password must be at least 6 characters"),
  firstName: z.string().optional(),
  lastName: z.string().optional(),
});

export default function Landing() {
  const [, setLocation] = useLocation();
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [loginError, setLoginError] = useState<string>("");
  const [registerError, setRegisterError] = useState<string>("");
  const { login } = useAuth();
  const { toast } = useToast();

  // Dynamic date formatting
  const currentDate = new Date().toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const authStatus = urlParams.get("auth");
    const token = urlParams.get("token");

    if (token) {
      localStorage.setItem("auth_token", token);
      window.history.replaceState({}, document.title, "/");

      authApi
        .getCurrentUser()
        .then((user) => {
          login(token, user);
        })
        .catch((error) => {
          console.error("Authentication failed:", error);
        });
    } else if (authStatus === "success") {
      window.history.replaceState({}, document.title, "/");

      authApi
        .getCurrentUser()
        .then((user) => {
          login("cookie-based", user);
        })
        .catch((error) => {
          console.error("Authentication failed:", error);
        });
    } else if (authStatus === "failed") {
      const error = urlParams.get("error");
      window.history.replaceState({}, document.title, "/");
      console.error("Authentication failed:", error);
    }
  }, [login, toast]);

  const loginForm = useForm({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  const registerForm = useForm({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      username: "",
      email: "",
      password: "",
      firstName: "",
      lastName: "",
    },
  });

  const handleLogin = async (data: z.infer<typeof loginSchema>) => {
    setIsLoading(true);
    setLoginError("");
    try {
      const response = await authApi.login(data);
      login(response.token!, response.user!);
      setIsLoginOpen(false);
    } catch (error: any) {
      console.error("Login failed:", error);
      const errorMessage = error?.message || "Invalid email or password";
      setLoginError(errorMessage);
      
      // If error is about email verification, redirect to verification page
      if (errorMessage.includes("verify your email") || errorMessage.includes("verification")) {
        toast({
          title: "Email Not Verified",
          description: "Please verify your email to continue.",
          variant: "destructive",
        });
        setIsLoginOpen(false);
        setLocation(`/verify-email?email=${encodeURIComponent(data.email)}`);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async (data: z.infer<typeof registerSchema>) => {
    setIsLoading(true);
    setRegisterError("");
    try {
      const response = await authApi.register(data);
      
      // Check if email verification is required (no token returned)
      if (!response.token) {
        toast({
          title: "Registration Successful!",
          description: response.message || "Please check your email for a verification code.",
          duration: 5000,
        });
        setIsRegisterOpen(false);
        registerForm.reset();
        // Redirect to verification page with email in URL
        setLocation(`/verify-email?email=${encodeURIComponent(data.email)}`);
      } else {
        // OAuth users get immediate access
        login(response.token, response.user!);
        setIsRegisterOpen(false);
      }
    } catch (error: any) {
      console.error("Registration failed:", error);
      setRegisterError(error?.message || "Registration failed. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-background">
      <nav className="absolute top-4 left-6 text-sm uppercase tracking-wider text-foreground/70 font-serif z-50">
        SQLGym
      </nav>

      <section className="relative h-screen flex flex-col items-center justify-center text-center bg-gradient-to-br from-[#FDF6EC] to-[#F8E0C0] overflow-hidden">
        <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/dust.png')] opacity-30 mix-blend-overlay pointer-events-none"></div>

        <div className="absolute top-6 right-10 text-xs font-mono text-foreground/70 uppercase tracking-widest">
          {currentDate}
        </div>

        <h1 className="text-7xl font-display text-foreground leading-tight drop-shadow-[0_4px_2px_rgba(0,0,0,0.2)] relative z-10 mb-8">
          <span className="block font-script text-5xl text-primary/90">The</span>
          <span className="block mt-2">SQL Training</span>
          <span className="block font-script text-6xl text-primary mt-2">Gymnasium</span>
        </h1>

        <div className="relative z-10 flex gap-4 mb-8">
          <Dialog open={isLoginOpen} onOpenChange={(open) => {
            setIsLoginOpen(open);
            if (open) setLoginError("");
          }}>
            <DialogTrigger asChild>
              <Button 
                variant="outline" 
                size="lg"
                className="bg-white/80 hover:bg-white border-2 border-foreground/20 font-serif"
                data-testid="button-login"
              >
                Login
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Login to SQLGym</DialogTitle>
              </DialogHeader>
              <Form {...loginForm}>
                <form
                  onSubmit={loginForm.handleSubmit(handleLogin)}
                  className="space-y-4"
                >
                  <FormField
                    control={loginForm.control}
                    name="email"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Email</FormLabel>
                        <FormControl>
                          <Input
                            {...field}
                            type="email"
                            data-testid="input-email"
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={loginForm.control}
                    name="password"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Password</FormLabel>
                        <FormControl>
                          <Input
                            {...field}
                            type="password"
                            data-testid="input-password"
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  {loginError && (
                    <div className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-3 rounded-md" data-testid="error-login">
                      {loginError}
                    </div>
                  )}
                  
                  <Button
                    type="submit"
                    disabled={isLoading}
                    className="w-full"
                    data-testid="button-submit-login"
                  >
                    {isLoading ? "Logging in..." : "Login"}
                  </Button>

                  <div className="relative my-4">
                    <div className="absolute inset-0 flex items-center">
                      <div className="w-full border-t border-muted"></div>
                    </div>
                    <div className="relative flex justify-center text-xs uppercase">
                      <span className="bg-background px-2 text-muted-foreground">
                        Or continue with
                      </span>
                    </div>
                  </div>

                  <Button
                    type="button"
                    variant="outline"
                    className="w-full"
                    onClick={() =>
                      (window.location.href = "/api/auth/google/login")
                    }
                    data-testid="button-google-login"
                  >
                    <FaGoogle className="mr-2 h-4 w-4 text-red-500" />
                    Google
                  </Button>
                </form>
              </Form>
            </DialogContent>
          </Dialog>

          <Dialog open={isRegisterOpen} onOpenChange={(open) => {
            setIsRegisterOpen(open);
            if (open) setRegisterError("");
          }}>
            <DialogTrigger asChild>
              <Button
                size="lg"
                className="bg-primary text-white hover:bg-primary/90 px-8 font-serif"
                data-testid="button-register"
              >
                <Code className="mr-2 h-5 w-5" />
                Start Training
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Join SQLGym</DialogTitle>
              </DialogHeader>
              <Form {...registerForm}>
                <form
                  onSubmit={registerForm.handleSubmit(handleRegister)}
                  className="space-y-4"
                >
                  <FormField
                    control={registerForm.control}
                    name="username"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Username</FormLabel>
                        <FormControl>
                          <Input {...field} data-testid="input-username" />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={registerForm.control}
                    name="email"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Email</FormLabel>
                        <FormControl>
                          <Input
                            {...field}
                            type="email"
                            data-testid="input-register-email"
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={registerForm.control}
                    name="password"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Password</FormLabel>
                        <FormControl>
                          <Input
                            {...field}
                            type="password"
                            data-testid="input-register-password"
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <div className="grid grid-cols-2 gap-4">
                    <FormField
                      control={registerForm.control}
                      name="firstName"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>First Name (Optional)</FormLabel>
                          <FormControl>
                            <Input {...field} data-testid="input-firstname" />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={registerForm.control}
                      name="lastName"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Last Name (Optional)</FormLabel>
                          <FormControl>
                            <Input {...field} data-testid="input-lastname" />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                  
                  {registerError && (
                    <div className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-3 rounded-md" data-testid="error-register">
                      {registerError}
                    </div>
                  )}
                  
                  <Button
                    type="submit"
                    disabled={isLoading}
                    className="w-full"
                    data-testid="button-submit-register"
                  >
                    {isLoading ? "Creating account..." : "Create Account"}
                  </Button>

                  <div className="relative my-4">
                    <div className="absolute inset-0 flex items-center">
                      <div className="w-full border-t border-muted"></div>
                    </div>
                    <div className="relative flex justify-center text-xs uppercase">
                      <span className="bg-background px-2 text-muted-foreground">
                        Or continue with
                      </span>
                    </div>
                  </div>

                  <Button
                    type="button"
                    variant="outline"
                    className="w-full"
                    onClick={() =>
                      (window.location.href = "/api/auth/google/login")
                    }
                    data-testid="button-google-register"
                  >
                    <FaGoogle className="mr-2 h-4 w-4 text-red-500" />
                    Google
                  </Button>
                </form>
              </Form>
            </DialogContent>
          </Dialog>
        </div>

        <div className="absolute bottom-8 flex flex-wrap justify-center gap-6 text-sm text-foreground/70 font-serif">
          <span>License Free</span>
          <span>Membership Free</span>
          <span>Subscription Free</span>
          <span>1-800-SQLPOWER</span>
        </div>
      </section>
    </div>
  );
}
