import { useState, useEffect } from "react";
import { Play, Users, Code, CheckCircle } from "lucide-react";
import { FaGoogle } from "react-icons/fa";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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
import ProgressBar from "@/components/progress-bar";

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
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const { toast } = useToast();

  // Handle OAuth callback
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const authStatus = urlParams.get("auth");
    const token = urlParams.get("token");

    // Handle token-based auth (if implemented)
    if (token) {
      localStorage.setItem("auth_token", token);
      window.history.replaceState({}, document.title, "/");
      
      authApi
        .getCurrentUser()
        .then((user) => {
          login(token, user);
          toast({
            title: "Welcome!",
            description: "Successfully logged into SQL Practice Hub.",
          });
        })
        .catch(() => {
          toast({
            title: "Authentication failed",
            description: "Please try logging in again.",
            variant: "destructive",
          });
        });
    }
    // Handle cookie-based auth (Google OAuth)
    else if (authStatus === "success") {
      window.history.replaceState({}, document.title, "/");
      
      authApi
        .getCurrentUser()
        .then((user) => {
          login("cookie-based", user);
          toast({
            title: "Welcome!",
            description: "Successfully logged into SQL Practice Hub.",
          });
        })
        .catch(() => {
          toast({
            title: "Authentication failed",
            description: "Please try logging in again.",
            variant: "destructive",
          });
        });
    }
    // Handle auth failure
    else if (authStatus === "failed") {
      const error = urlParams.get("error");
      window.history.replaceState({}, document.title, "/");
      toast({
        title: "Authentication failed",
        description: error || "Please try logging in again.",
        variant: "destructive",
      });
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
    try {
      const response = await authApi.login(data);
      login(response.token!, response.user!);
      setIsLoginOpen(false);
      toast({
        title: "Welcome back!",
        description: "Successfully logged into SQL Practice Hub.",
      });
    } catch (error) {
      toast({
        title: "Login failed",
        description:
          error instanceof Error
            ? error.message
            : "Please check your credentials.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async (data: z.infer<typeof registerSchema>) => {
    setIsLoading(true);
    try {
      const response = await authApi.register(data);
      login(response.token!, response.user!);
      setIsRegisterOpen(false);
      toast({
        title: "Welcome to SQL Practice Hub!",
        description: "Your account has been created successfully.",
      });
    } catch (error) {
      toast({
        title: "Registration failed",
        description:
          error instanceof Error ? error.message : "Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-background">
      {/* Navigation */}
      <nav className="bg-white border-b border-border shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-2">
              <Code className="text-primary text-2xl" />
              <span className="text-2xl font-bold text-foreground">
                SQL Practice Hub
              </span>
            </div>

            <div className="flex items-center space-x-3">
              <Dialog open={isLoginOpen} onOpenChange={setIsLoginOpen}>
                <DialogTrigger asChild>
                  <Button variant="ghost" data-testid="button-login">
                    Login
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Login to SQL Practice Hub</DialogTitle>
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

              <Dialog open={isRegisterOpen} onOpenChange={setIsRegisterOpen}>
                <DialogTrigger asChild>
                  <Button
                    className="bg-primary text-primary-foreground hover:bg-primary/90"
                    data-testid="button-register"
                  >
                    <Code className="mr-2 h-4 w-4" />
                    Start Practicing
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Join SQL Practice Hub</DialogTitle>
                  </DialogHeader>
                  <Form {...registerForm}>
                    <form
                      onSubmit={registerForm.handleSubmit(handleRegister)}
                      className="space-y-4"
                    >
                      <div className="grid grid-cols-2 gap-4">
                        <FormField
                          control={registerForm.control}
                          name="firstName"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel>First Name</FormLabel>
                              <FormControl>
                                <Input
                                  {...field}
                                  data-testid="input-firstName"
                                />
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
                              <FormLabel>Last Name</FormLabel>
                              <FormControl>
                                <Input
                                  {...field}
                                  data-testid="input-lastName"
                                />
                              </FormControl>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                      </div>
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
                            Or sign up with
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
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-8">
              <div>
                <h1 className="text-5xl font-bold text-foreground leading-tight">
                  Master <span className="text-primary">SQL Skills</span> for
                  Interviews & Work
                </h1>
                <p className="text-xl text-muted-foreground mt-6 leading-relaxed">
                  Practice SQL with real-world problems designed for interviews
                  and professional development. Progress from Junior to Senior
                  level with our comprehensive platform.
                </p>
              </div>

              {/* Progress Showcase */}
              <Card className="p-6">
                <h3 className="font-semibold text-foreground mb-4">
                  Your Progress
                </h3>
                <ProgressBar value={15} max={20} />
              </Card>

              <div className="flex flex-col sm:flex-row gap-4">
                <Dialog>
                  <DialogTrigger asChild>
                    <Button
                      size="lg"
                      className="bg-primary text-primary-foreground px-8 py-4 text-lg hover:bg-primary/90"
                      data-testid="button-start-practice"
                    >
                      <Play className="mr-3 h-5 w-5" />
                      Start Practicing
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Join SQL Practice Hub</DialogTitle>
                    </DialogHeader>
                    <p className="text-muted-foreground mb-4">
                      Create your free account to access hundreds of
                      interview-focused SQL problems and join our professional
                      community.
                    </p>
                    <Button
                      onClick={() => {
                        setIsRegisterOpen(true);
                      }}
                      className="w-full"
                      data-testid="button-join-now"
                    >
                      Join Now - It's Free!
                    </Button>
                  </DialogContent>
                </Dialog>

                <Button
                  variant="outline"
                  size="lg"
                  className="px-8 py-4 text-lg"
                  onClick={() =>
                    document
                      .getElementById("community")
                      ?.scrollIntoView({ behavior: "smooth" })
                  }
                  data-testid="button-join-community"
                >
                  <Users className="mr-3 h-5 w-5" />
                  Join Community
                </Button>
              </div>
            </div>

            <div className="relative">
              <img
                src="https://images.unsplash.com/photo-1517077304055-6e89abbf09b0?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&h=600"
                alt="Professional coding workspace"
                className="rounded-xl shadow-2xl w-full"
              />

              {/* Floating achievement cards */}
              <Card className="absolute -top-4 -right-4 p-4 shadow-lg">
                <div className="flex items-center space-x-3">
                  <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center">
                    <CheckCircle className="text-primary text-xl" />
                  </div>
                  <div>
                    <p className="font-semibold text-foreground">
                      Senior Developer
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Level Achieved!
                    </p>
                  </div>
                </div>
              </Card>

              <Card className="absolute -bottom-4 -left-4 p-4 shadow-lg">
                <div className="flex items-center space-x-3">
                  <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                    <CheckCircle className="text-green-600 text-xl" />
                  </div>
                  <div>
                    <p className="font-semibold text-foreground">
                      Problem Solved!
                    </p>
                    <p className="text-sm text-muted-foreground">
                      +50 XP Gained
                    </p>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* Community Section */}
      <section id="community" className="bg-muted/30 py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-4xl font-bold text-foreground mb-4">
            Join the SQL Practice Community
          </h2>
          <p className="text-xl text-muted-foreground mb-8">
            Connect with fellow developers, share solutions, and advance your
            career
          </p>

          <div className="grid md:grid-cols-3 gap-8 mb-12">
            <div className="text-center">
              <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <Code className="w-8 h-8 text-primary" />
              </div>
              <h3 className="font-semibold text-foreground mb-2">
                Practice Together
              </h3>
              <p className="text-muted-foreground">
                Solve problems with peers and share your solutions
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Users className="w-8 h-8 text-green-600" />
              </div>
              <h3 className="font-semibold text-foreground mb-2">
                Learn from Experts
              </h3>
              <p className="text-muted-foreground">
                Get tips and tricks from senior developers
              </p>
            </div>

            <div className="text-center">
              <div className="w-16 h-16 bg-yellow-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="w-8 h-8 text-yellow-600" />
              </div>
              <h3 className="font-semibold text-foreground mb-2">
                Track Progress
              </h3>
              <p className="text-muted-foreground">
                Earn badges and climb the leaderboards
              </p>
            </div>
          </div>

          <Button
            onClick={() => setIsRegisterOpen(true)}
            size="lg"
            className="bg-primary text-primary-foreground px-8 py-4 text-lg hover:bg-primary/90"
            data-testid="button-get-started"
          >
            <Code className="mr-3 h-5 w-5" />
            Get Started Now
          </Button>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-foreground text-background py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-4 gap-8">
            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                <Code className="text-primary text-2xl" />
                <span className="text-2xl font-bold">SQL Practice Hub</span>
              </div>
              <p className="text-background/70">
                Master SQL skills for interviews and professional development
                with our comprehensive platform.
              </p>
            </div>

            <div>
              <h3 className="font-semibold mb-4">Platform</h3>
              <div className="space-y-2 text-background/70">
                <a
                  href="#"
                  className="block hover:text-primary transition-colors"
                >
                  Problems
                </a>
                <a
                  href="#"
                  className="block hover:text-primary transition-colors"
                >
                  Leaderboard
                </a>
                <a
                  href="#"
                  className="block hover:text-primary transition-colors"
                >
                  Community
                </a>
                <a
                  href="#"
                  className="block hover:text-primary transition-colors"
                >
                  Submissions
                </a>
              </div>
            </div>

            <div>
              <h3 className="font-semibold mb-4">Resources</h3>
              <div className="space-y-2 text-background/70">
                <a
                  href="#"
                  className="block hover:text-primary transition-colors"
                >
                  Documentation
                </a>
                <a
                  href="#"
                  className="block hover:text-primary transition-colors"
                >
                  SQL Guide
                </a>
                <a
                  href="#"
                  className="block hover:text-primary transition-colors"
                >
                  Video Tutorials
                </a>
                <a
                  href="#"
                  className="block hover:text-primary transition-colors"
                >
                  Blog
                </a>
              </div>
            </div>

            <div>
              <h3 className="font-semibold mb-4">Company</h3>
              <div className="space-y-2 text-background/70">
                <a
                  href="#"
                  className="block hover:text-primary transition-colors"
                >
                  About
                </a>
                <a
                  href="#"
                  className="block hover:text-primary transition-colors"
                >
                  Contact
                </a>
                <a
                  href="#"
                  className="block hover:text-primary transition-colors"
                >
                  Privacy
                </a>
                <a
                  href="#"
                  className="block hover:text-primary transition-colors"
                >
                  Terms
                </a>
              </div>
            </div>
          </div>

          <div className="border-t border-background/20 mt-8 pt-8 text-center text-background/70">
            <p>
              &copy; 2024 SQL Practice Hub. All rights reserved. Practice smart,
              code professionally.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
