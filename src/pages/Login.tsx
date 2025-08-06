import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import Logo from "@/components/Logo";
import { Link } from "react-router-dom";

const Login = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Handle login logic here
    console.log("Login attempt:", { email, password });
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
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="Enter your email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
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
            
            <Button type="submit" className="w-full">
              Login
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