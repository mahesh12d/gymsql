import { useState, useEffect } from "react";
import { Play, Users } from "lucide-react";
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
    <div className="min-h-screen bg-gradient-to-br from-pink-400 via-orange-300 to-yellow-300 relative overflow-hidden">
      {/* Gradient decorations */}
      <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-br from-pink-500 to-orange-400 rounded-full blur-3xl opacity-30 -mr-48 -mt-48" />
      <div className="absolute bottom-0 left-0 w-96 h-96 bg-gradient-to-tr from-green-400 to-cyan-300 rounded-full blur-3xl opacity-30 -ml-48 -mb-48" />
      <div className="absolute bottom-20 right-20 w-64 h-64 bg-gradient-to-tr from-yellow-300 to-green-400 rounded-full blur-3xl opacity-20" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 min-h-screen flex items-center">
        <div className="bg-white rounded-3xl shadow-2xl p-8 md:p-12 lg:p-16 relative overflow-hidden w-full">
          {/* Content Container */}
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            {/* Left Content */}
            <div className="space-y-8">
              <div>
                <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-gray-900 leading-tight mb-4">
                  Master <span className="text-transparent bg-clip-text bg-gradient-to-r from-pink-500 to-orange-500">SQL Skills</span> for
                  <br />
                  Interviews & Work
                </h1>
                <p className="text-gray-600 text-lg leading-relaxed">
                  Practice SQL with real-world problems designed for interviews and professional development. 
                  Progress from Junior to Senior level with our comprehensive platform.
                </p>
              </div>

              {/* Your Progress Card */}
              <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-2xl p-6 border-2 border-dashed border-gray-300">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Your Progress</h3>
                <div className="mb-2 flex justify-between items-center">
                  <span className="text-sm text-gray-600">Week</span>
                  <span className="text-sm font-semibold text-gray-900">10%</span>
                </div>
                <ProgressBar value={15} max={20} />
                <div className="mt-3 flex items-center space-x-2">
                  <div className="w-6 h-6 bg-gradient-to-br from-red-500 to-orange-500 rounded flex items-center justify-center">
                    <span className="text-white text-xs font-bold">S</span>
                  </div>
                  <span className="text-sm font-medium text-gray-700">
                    15/20 completed
                  </span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-4">
                <Dialog open={isRegisterOpen} onOpenChange={setIsRegisterOpen}>
                  <DialogTrigger asChild>
                    <Button
                      size="lg"
                      className="w-full sm:w-auto bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white px-8 py-6 rounded-xl shadow-lg hover:shadow-xl transition-all duration-200 text-lg font-semibold"
                      data-testid="button-start-practicing"
                    >
                      <Play className="mr-2 h-5 w-5 fill-current" />
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

                <Dialog open={isLoginOpen} onOpenChange={setIsLoginOpen}>
                  <DialogTrigger asChild>
                    <Button
                      size="lg"
                      variant="outline"
                      className="w-full sm:w-auto border-2 border-gray-300 hover:border-gray-400 px-8 py-6 rounded-xl text-lg font-semibold transition-all duration-200"
                      data-testid="button-login"
                    >
                      <Users className="mr-2 h-5 w-5" />
                      Join Community
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
              </div>
            </div>

            {/* Right Content - Illustration Area */}
            <div className="relative hidden lg:block">
              <div className="relative w-full h-[500px] flex items-center justify-center">
                {/* Isometric Platform Illustration */}
                <div className="relative w-full h-full">
                  {/* Achievement Badge 1 */}
                  <div className="absolute top-8 right-12 bg-white rounded-2xl shadow-lg p-4 border-2 border-purple-200 transform rotate-3 hover:rotate-0 transition-transform">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-gradient-to-br from-purple-400 to-purple-600 rounded-full flex items-center justify-center">
                        <span className="text-white text-xl">🏆</span>
                      </div>
                      <div>
                        <p className="text-sm font-bold text-gray-900">Senior Developer</p>
                        <p className="text-xs text-gray-600">Level Achieved!</p>
                      </div>
                    </div>
                  </div>

                  {/* Achievement Badge 2 */}
                  <div className="absolute bottom-24 left-8 bg-white rounded-2xl shadow-lg p-4 border-2 border-green-200 transform -rotate-3 hover:rotate-0 transition-transform">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-gradient-to-br from-green-400 to-green-600 rounded-full flex items-center justify-center">
                        <span className="text-white text-xl">✓</span>
                      </div>
                      <div>
                        <p className="text-sm font-bold text-gray-900">Problem Solved!</p>
                        <p className="text-xs text-gray-600">+50 XP Gained</p>
                      </div>
                    </div>
                  </div>

                  {/* Central Illustration Placeholder */}
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="relative w-80 h-80">
                      {/* Platform layers with gradient backgrounds */}
                      <div className="absolute bottom-0 w-full h-48 bg-gradient-to-br from-purple-200 to-purple-300 rounded-2xl transform perspective-1000 rotate-y-12" />
                      <div className="absolute bottom-12 left-8 w-56 h-40 bg-gradient-to-br from-cyan-200 to-cyan-300 rounded-2xl transform perspective-1000 rotate-y-12" />
                      <div className="absolute bottom-24 right-8 w-48 h-32 bg-gradient-to-br from-pink-200 to-pink-300 rounded-2xl transform perspective-1000 rotate-y-12" />
                      
                      {/* Decorative elements */}
                      <div className="absolute top-8 right-12 w-16 h-16 bg-gradient-to-br from-yellow-300 to-yellow-400 rounded-full shadow-lg flex items-center justify-center text-2xl">
                        🌍
                      </div>
                      <div className="absolute top-20 left-8 w-12 h-12 bg-gradient-to-br from-green-300 to-green-400 rounded-lg shadow-lg flex items-center justify-center text-xl">
                        🌳
                      </div>
                      <div className="absolute bottom-32 right-4 w-14 h-14 bg-gradient-to-br from-orange-300 to-orange-400 rounded-full shadow-lg flex items-center justify-center text-2xl">
                        💰
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
