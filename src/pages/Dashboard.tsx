import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { 
  Cloud, 
  Settings, 
  Shield, 
  RotateCcw,
  Plus,
  Play
} from "lucide-react";

const Dashboard = () => {
  return (
    <div className="p-6 space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Connect to Cloud Account */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Cloud className="h-5 w-5 text-primary" />
              Connect to Cloud Account
            </CardTitle>
            <CardDescription>
              Connect to your cloud provider to begin analyzing resources.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Connect your AWS, Azure, GCP, or IBM Cloud account.
            </p>
            <Button className="w-full">
              Connect To Cloud
            </Button>
          </CardContent>
        </Card>

        {/* Create Resources In Cloud */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Plus className="h-5 w-5 text-primary" />
              Create Resources In Cloud
            </CardTitle>
            <CardDescription>
              Create cloud resources with AI-generated code.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Describe resource configuration.
            </p>
            <Button variant="secondary" className="w-full" disabled>
              Create Resources
            </Button>
          </CardContent>
        </Card>

        {/* Analyze Resources for Compliance */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-primary" />
              Analyze Resources for Compliance
            </CardTitle>
            <CardDescription>
              Analyze your resources against cloud security benchmarks controls.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Run compliance checks and get detailed reports.
            </p>
            <Button variant="secondary" className="w-full" disabled>
              <Play className="h-4 w-4 mr-2" />
              Start Compliance Analysis
            </Button>
          </CardContent>
        </Card>

        {/* Reset Progress */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <RotateCcw className="h-5 w-5 text-primary" />
              Reset Progress
            </CardTitle>
            <CardDescription>
              Clear your current session progress.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Reset cloud connection, resource creation and compliance analysis data.
            </p>
            <Button variant="destructive" className="w-full bg-success hover:bg-success/90">
              Reset Progress
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Dashboard;