import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AlertCircle, CheckCircle, XCircle, Download } from "lucide-react";

const Report = () => {
  const mockResults = [
    {
      id: 1,
      control: "CIS-1.1",
      description: "Ensure MFA is enabled for root account",
      status: "passed",
      severity: "high",
      resource: "AWS Root Account"
    },
    {
      id: 2,
      control: "CIS-1.2",
      description: "Ensure security contact information is provided",
      status: "failed",
      severity: "medium",
      resource: "AWS Account Settings"
    },
    {
      id: 3,
      control: "CIS-2.1",
      description: "Ensure CloudTrail is enabled in all regions",
      status: "warning",
      severity: "high",
      resource: "AWS CloudTrail"
    }
  ];

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "passed":
        return <CheckCircle className="h-4 w-4 text-success" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-destructive" />;
      case "warning":
        return <AlertCircle className="h-4 w-4 text-warning" />;
      default:
        return null;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "passed":
        return "bg-success/10 text-success";
      case "failed":
        return "bg-destructive/10 text-destructive";
      case "warning":
        return "bg-warning/10 text-warning";
      default:
        return "bg-muted text-muted-foreground";
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Compliance Report</h1>
          <p className="text-muted-foreground">Review your security posture analysis results</p>
        </div>
        <Button>
          <Download className="h-4 w-4 mr-2" />
          Export Report
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-success" />
              <div>
                <p className="text-2xl font-bold">12</p>
                <p className="text-sm text-muted-foreground">Passed</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2">
              <XCircle className="h-5 w-5 text-destructive" />
              <div>
                <p className="text-2xl font-bold">5</p>
                <p className="text-sm text-muted-foreground">Failed</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-warning" />
              <div>
                <p className="text-2xl font-bold">3</p>
                <p className="text-sm text-muted-foreground">Warnings</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Compliance Results</CardTitle>
          <CardDescription>
            Detailed breakdown of security controls assessment
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {mockResults.map((result) => (
              <div key={result.id} className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center gap-3">
                  {getStatusIcon(result.status)}
                  <div>
                    <p className="font-medium">{result.control}</p>
                    <p className="text-sm text-muted-foreground">{result.description}</p>
                    <p className="text-xs text-muted-foreground">{result.resource}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className={getStatusColor(result.severity)}>
                    {result.severity}
                  </Badge>
                  <Badge className={getStatusColor(result.status)}>
                    {result.status}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Report;