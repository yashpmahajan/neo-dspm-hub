import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import Logo from "@/components/Logo";
import { Link } from "react-router-dom";

const Login = () => {
  const [userId, setUserId] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    // try {
      // const response = await fetch("YOUR_API_ENDPOINT/login", {
      //   method: "POST",
      //   headers: {
      //     "Content-Type": "application/json",
      //   },
      //   body: JSON.stringify({
      //     user_id: userId,
      //     password: password,
      //   }),
      // });

      // if (response.ok) {
        // const data = await response.json();
        const data = {
          token: "authenticated",
          user_id: userId,
        };
        // Store authentication token/session
        localStorage.setItem("authToken", data.token || "authenticated");
        localStorage.setItem("userId", userId);
        // Redirect to dashboard
        window.location.href = "/";
      // } else {
      //   const errorData = await response.json();
      //   setError(errorData.message || "Invalid credentials");
      // }
    // } catch (error) {
    //   setError("Network error. Please try again.");
    // } finally {
      setIsLoading(false);
    // }
  };

  return (
    <div className="min-h-screen flex items-center justify-center" 
         style={{ background: "var(--login-gradient)" }}>
      <Card className="w-full max-w-md mx-4">
        <CardHeader className="text-center space-y-6 pb-8">
          <h1 className="text-2xl font-semibold text-neo-blue">Welcome to</h1>
          <div className="flex justify-center">
            <Logo />
          </div>
          <p className="text-lg font-medium text-muted-foreground">
            An AI-Powered Cloud Compliance Solution
          </p>
          <p className="text-sm text-muted-foreground">
            Login to begin using neoDSPM
          </p>
        </CardHeader>
        
        <CardContent className="space-y-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="userId">User ID</Label>
              <Input
                id="userId"
                type="text"
                placeholder="Enter your user ID"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                required
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            
            {error && (
              <div className="text-red-500 text-sm text-center">{error}</div>
            )}
            
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? "Logging in..." : "Login"}
            </Button>
          </form>
          
          <div className="text-center space-y-2 text-sm">
            <p className="text-muted-foreground">
              Do not have an account?{" "}
              <Link to="/signup" className="text-primary hover:underline">
                Sign up
              </Link>
            </p>
            <p className="text-muted-foreground">
              Forgot Password?{" "}
              <Link to="/reset-password" className="text-primary hover:underline">
                Click Here to reset your password
              </Link>
            </p>
            <p className="text-muted-foreground">
              Interested in using our service?{" "}
              <Link to="/contact" className="text-primary hover:underline">
                Contact Us
              </Link>
            </p>
          </div>
          
          <div className="text-center text-xs text-muted-foreground pt-4">
            COPYRIGHT 2025 © NEOVA TECH SOLUTIONS INC.
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Login;