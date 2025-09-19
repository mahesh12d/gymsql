import { Switch, Route, useLocation } from "wouter";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "./lib/queryClient";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider, useAuth } from "@/hooks/use-auth";
import Landing from "@/pages/landing";
import Home from "@/pages/home";
import Problems from "@/pages/problems";
import ProblemDetail from "@/pages/problem-detail";
import Leaderboard from "@/pages/leaderboard";
import Community from "@/pages/community";
import Submissions from "@/pages/submissions";
import AdminPanel from "@/pages/admin-panel";
import NotFound from "@/pages/not-found";
import Navbar from "@/components/navbar";

function AppRouter() {
  const { isAuthenticated, isLoading } = useAuth();
  const [location] = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading SQLGym...</p>
        </div>
      </div>
    );
  }

  // Hide navbar on problem detail pages (routes like /problems/:id)
  const isOnProblemDetailPage = location.startsWith('/problems/');

  return (
    <>
      {isAuthenticated && !isOnProblemDetailPage && <Navbar />}
      <Switch>
        {!isAuthenticated ? (
          <Route path="/" component={Landing} />
        ) : (
          <>
            <Route path="/" component={Home} />
            <Route path="/problems" component={Problems} />
            <Route path="/problems/:id" component={ProblemDetail} />
            <Route path="/leaderboard" component={Leaderboard} />
            <Route path="/community" component={Community} />
            <Route path="/submissions" component={Submissions} />
            <Route path="/admin-panel" component={AdminPanel} />
          </>
        )}
        <Route component={NotFound} />
      </Switch>
    </>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <AuthProvider>
          <Toaster />
          <AppRouter />
        </AuthProvider>
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
