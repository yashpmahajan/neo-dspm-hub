import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Key, Cloud } from "lucide-react";

const Settings = () => {
  const [awsCredentials, setAwsCredentials] = useState({
    accessKey: "",
    secretKey: "",
    region: "us-east-1",
    bucketName: ""
  });

  const [apiKey, setApiKey] = useState("");

  const handleAwsSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Handle AWS credentials save
    console.log("AWS Credentials saved:", awsCredentials);
  };

  const handleApiSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Handle API key save
    console.log("API Key saved:", apiKey);
  };

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-foreground">Settings</h1>
        <p className="text-muted-foreground mt-2">Configure your AWS credentials and API settings</p>
      </div>

      <div className="max-w-2xl">
        <Tabs defaultValue="aws" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="aws">AWS Configuration</TabsTrigger>
            <TabsTrigger value="api">API Configuration</TabsTrigger>
          </TabsList>

          <TabsContent value="aws">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Cloud className="h-5 w-5 text-primary" />
                  AWS Credentials
                </CardTitle>
                <CardDescription>
                  Configure your AWS credentials for S3 uploads and data management.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleAwsSubmit} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="accessKey">Access Key ID</Label>
                    <Input
                      id="accessKey"
                      type="password"
                      value={awsCredentials.accessKey}
                      onChange={(e) => setAwsCredentials(prev => ({ ...prev, accessKey: e.target.value }))}
                      placeholder="Enter your AWS Access Key ID"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="secretKey">Secret Access Key</Label>
                    <Input
                      id="secretKey"
                      type="password"
                      value={awsCredentials.secretKey}
                      onChange={(e) => setAwsCredentials(prev => ({ ...prev, secretKey: e.target.value }))}
                      placeholder="Enter your AWS Secret Access Key"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="region">Region</Label>
                    <Input
                      id="region"
                      value={awsCredentials.region}
                      onChange={(e) => setAwsCredentials(prev => ({ ...prev, region: e.target.value }))}
                      placeholder="e.g., us-east-1"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="bucketName">S3 Bucket Name</Label>
                    <Input
                      id="bucketName"
                      value={awsCredentials.bucketName}
                      onChange={(e) => setAwsCredentials(prev => ({ ...prev, bucketName: e.target.value }))}
                      placeholder="Enter your S3 bucket name"
                    />
                  </div>

                  <Button type="submit" className="w-full">
                    Save AWS Configuration
                  </Button>
                </form>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="api">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Key className="h-5 w-5 text-primary" />
                  API Configuration
                </CardTitle>
                <CardDescription>
                  Configure your OpenAI API key for enhanced data processing capabilities.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleApiSubmit} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="apiKey">OpenAI API Key</Label>
                    <Input
                      id="apiKey"
                      type="password"
                      value={apiKey}
                      onChange={(e) => setApiKey(e.target.value)}
                      placeholder="sk-..."
                    />
                    <p className="text-sm text-muted-foreground">
                      Your API key is stored securely and only used for processing requests.
                    </p>
                  </div>

                  <Button type="submit" className="w-full">
                    Save API Configuration
                  </Button>
                </form>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default Settings;