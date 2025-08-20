import { Card, CardContent, CardHeader } from "@/components/ui/card";
import Logo from "@/components/Logo";
import { Link } from "react-router-dom";

const ConnectAdmin = () => {
  return (
    <div className="min-h-screen flex items-center justify-center" 
         style={{ background: "var(--login-gradient)" }}>
      <Card className="w-full max-w-md mx-4">
        <CardHeader className="text-center space-y-6 pb-8">
          <div className="flex justify-center">
            <Logo />
          </div>
          <h1 className="text-2xl font-semibold text-neo-blue">Connect with Admin</h1>
        </CardHeader>
        
        <CardContent className="space-y-6">
          <div className="text-center space-y-4">
            <p className="text-lg text-muted-foreground">
              Please reach out to the administrator for assistance.
            </p>
            
            <Link 
              to="/login" 
              className="inline-block text-primary hover:underline font-medium"
            >
              ← Back to Login
            </Link>
          </div>
          
          <div className="text-center text-xs text-muted-foreground pt-4">
            COPYRIGHT 2025 © NEOVA TECH SOLUTIONS INC.
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default ConnectAdmin;