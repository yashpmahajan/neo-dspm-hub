import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Checkbox } from "@/components/ui/checkbox";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import { Key, Cloud, Shield, UserPlus } from "lucide-react";

type CloudProvider = 'aws' | 'azure' | 'gcp';

const Settings = () => {
  const [selectedProvider, setSelectedProvider] = useState<CloudProvider>('aws');
  
  const [awsCredentials, setAwsCredentials] = useState({
    accessKey: "",
    secretKey: "",
    region: "us-east-1",
    bucketName: ""
  });

  const [azureCredentials, setAzureCredentials] = useState({
    tenantId: "",
    clientId: "",
    clientSecret: "",
    subscriptionId: "",
    resourceGroup: "",
    location: "centralindia"
  });

  const [gcpCredentials, setGcpCredentials] = useState({
    projectId: "",
    privateKeyId: "",
    privateKey: "",
    clientEmail: "",
    authUri: "https://accounts.google.com/o/oauth2/auth",
    tokenUri: "https://oauth2.googleapis.com/token"
  });

  useEffect(() => {
    // Load existing credentials from localStorage
    const savedAws = localStorage.getItem("aws_credentials");
    const savedAzure = localStorage.getItem("azure_credentials");
    const savedGcp = localStorage.getItem("gcp_credentials");
    
    if (savedAws) setAwsCredentials(JSON.parse(savedAws));
    if (savedAzure) setAzureCredentials(JSON.parse(savedAzure));
    if (savedGcp) setGcpCredentials(JSON.parse(savedGcp));
  }, []);

  const [apiKey, setApiKey] = useState("");
  const [newUser, setNewUser] = useState({
    userId: "",
    password: "",
    isAdmin: false
  });
  const { toast } = useToast();

  const handleAwsSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      // Persist locally for UX
      localStorage.setItem("aws_credentials", JSON.stringify(awsCredentials));

      // Persist to backend (.env)
      const response = await fetch(`${import.meta.env.VITE_BACKEND_API}/store-aws-creds`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          access_key_id: awsCredentials.accessKey,
          secret_access_key: awsCredentials.secretKey,
          region: awsCredentials.region,
          bucket_name: awsCredentials.bucketName,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text().catch(() => "");
        throw new Error(errorText || "Failed to store AWS credentials on server");
      }

      toast({
        title: "AWS Configuration saved",
        duration: 3000,
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to save AWS configuration. Please try again.",
        variant: "destructive",
        duration: 4000,
      });
    }
  };

  const handleAzureSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      // Persist locally for UX
      localStorage.setItem("azure_credentials", JSON.stringify(azureCredentials));

      // Persist to backend
      const response = await fetch(`${import.meta.env.VITE_BACKEND_API}/store-blob-creds`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          account_name: azureCredentials.tenantId,
          account_key: azureCredentials.clientSecret,
          container_name: azureCredentials.resourceGroup,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to store Azure credentials");
      }

      toast({
        title: "Azure Configuration saved",
        duration: 3000,
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to save Azure configuration. Please try again.",
        variant: "destructive",
        duration: 4000,
      });
    }
  };

  const handleGcpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      // Persist locally for UX
      localStorage.setItem("gcp_credentials", JSON.stringify(gcpCredentials));

      // Note: Backend endpoint for GCP needs to be created
      toast({
        title: "GCP Configuration saved locally",
        description: "GCP backend integration pending.",
        duration: 3000,
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to save GCP configuration. Please try again.",
        variant: "destructive",
        duration: 4000,
      });
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const myHeaders = new Headers();
      myHeaders.append("Content-Type", "application/json");

      const raw = JSON.stringify({
        username: newUser.userId,
        password: newUser.password,
        name: newUser.userId,
        is_admin: newUser.isAdmin
      });

      const requestOptions: RequestInit = {
        method: "POST",
        headers: myHeaders,
        body: raw,
        redirect: "follow" as RequestRedirect
      };

      const response = await fetch(
        `${import.meta.env.VITE_BACKEND_API}/create-user`,
        requestOptions
      );

      if (response.ok) {
        toast({
          title: "User created successfully",
          description: `User ${newUser.userId} has been created.`,
          duration: 3000,
        });
        setNewUser({ userId: "", password: "", isAdmin: false });
      } else {
        throw new Error('Failed to create user');
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to create user. Please try again.",
        variant: "destructive",
        duration: 4000,
      });
    }
  };

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-foreground">Settings</h1>
        <p className="text-muted-foreground mt-2">Configure your cloud provider credentials and manage users</p>
      </div>

      <div className="max-w-2xl">
        <Tabs defaultValue="cloud" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="cloud">Cloud Configuration</TabsTrigger>
            <TabsTrigger value="security">Add User</TabsTrigger>
          </TabsList>

          <TabsContent value="cloud">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Cloud className="h-5 w-5 text-primary" />
                  Cloud Provider Configuration
                </CardTitle>
                <CardDescription>
                  Configure credentials for AWS, Azure, or GCP cloud services.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Tabs value={selectedProvider} onValueChange={(v) => setSelectedProvider(v as CloudProvider)} className="w-full">
                  <TabsList className="grid w-full grid-cols-3 mb-6">
                    <TabsTrigger value="aws" className="flex items-center gap-2">
                      <Cloud className="h-4 w-4 text-orange-500" />
                      AWS
                    </TabsTrigger>
                    <TabsTrigger value="azure" className="flex items-center gap-2">
                      <Cloud className="h-4 w-4 text-blue-500" />
                      Azure
                    </TabsTrigger>
                    <TabsTrigger value="gcp" className="flex items-center gap-2">
                      <Cloud className="h-4 w-4 text-yellow-500" />
                      GCP
                    </TabsTrigger>
                  </TabsList>

                  {/* AWS Configuration */}
                  <TabsContent value="aws" className="space-y-4">
                    <form onSubmit={handleAwsSubmit} className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="accessKey">Access Key ID</Label>
                        <Input
                          id="accessKey"
                          type="password"
                          value={awsCredentials.accessKey}
                          onChange={(e) => setAwsCredentials(prev => ({ ...prev, accessKey: e.target.value }))}
                          placeholder="AKIAxxxxxxxxxxxxxxx"
                          required
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
                          required
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="region">Region</Label>
                        <Input
                          id="region"
                          value={awsCredentials.region}
                          onChange={(e) => setAwsCredentials(prev => ({ ...prev, region: e.target.value }))}
                          placeholder="e.g., ap-south-1"
                          required
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="bucketName">Bucket Name</Label>
                        <Input
                          id="bucketName"
                          value={awsCredentials.bucketName}
                          onChange={(e) => setAwsCredentials(prev => ({ ...prev, bucketName: e.target.value }))}
                          placeholder="my-app-bucket"
                          required
                        />
                      </div>

                      <Button type="submit" className="w-full">
                        Save AWS Configuration
                      </Button>
                    </form>
                  </TabsContent>

                  {/* Azure Configuration */}
                  <TabsContent value="azure" className="space-y-4">
                    <form onSubmit={handleAzureSubmit} className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="tenantId">Tenant ID</Label>
                        <Input
                          id="tenantId"
                          type="password"
                          value={azureCredentials.tenantId}
                          onChange={(e) => setAzureCredentials(prev => ({ ...prev, tenantId: e.target.value }))}
                          placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                          required
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="clientId">Client ID</Label>
                        <Input
                          id="clientId"
                          type="password"
                          value={azureCredentials.clientId}
                          onChange={(e) => setAzureCredentials(prev => ({ ...prev, clientId: e.target.value }))}
                          placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                          required
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="clientSecret">Client Secret</Label>
                        <Input
                          id="clientSecret"
                          type="password"
                          value={azureCredentials.clientSecret}
                          onChange={(e) => setAzureCredentials(prev => ({ ...prev, clientSecret: e.target.value }))}
                          placeholder="Enter your client secret"
                          required
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="subscriptionId">Subscription ID</Label>
                        <Input
                          id="subscriptionId"
                          type="password"
                          value={azureCredentials.subscriptionId}
                          onChange={(e) => setAzureCredentials(prev => ({ ...prev, subscriptionId: e.target.value }))}
                          placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                          required
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="resourceGroup">Resource Group</Label>
                        <Input
                          id="resourceGroup"
                          value={azureCredentials.resourceGroup}
                          onChange={(e) => setAzureCredentials(prev => ({ ...prev, resourceGroup: e.target.value }))}
                          placeholder="my-resource-group"
                          required
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="location">Location</Label>
                        <Input
                          id="location"
                          value={azureCredentials.location}
                          onChange={(e) => setAzureCredentials(prev => ({ ...prev, location: e.target.value }))}
                          placeholder="centralindia"
                          required
                        />
                      </div>

                      <Button type="submit" className="w-full">
                        Save Azure Configuration
                      </Button>
                    </form>
                  </TabsContent>

                  {/* GCP Configuration */}
                  <TabsContent value="gcp" className="space-y-4">
                    <form onSubmit={handleGcpSubmit} className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="projectId">Project ID</Label>
                        <Input
                          id="projectId"
                          value={gcpCredentials.projectId}
                          onChange={(e) => setGcpCredentials(prev => ({ ...prev, projectId: e.target.value }))}
                          placeholder="my-project-id"
                          required
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="privateKeyId">Private Key ID</Label>
                        <Input
                          id="privateKeyId"
                          type="password"
                          value={gcpCredentials.privateKeyId}
                          onChange={(e) => setGcpCredentials(prev => ({ ...prev, privateKeyId: e.target.value }))}
                          placeholder="Enter private key ID"
                          required
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="privateKey">Private Key</Label>
                        <Textarea
                          id="privateKey"
                          value={gcpCredentials.privateKey}
                          onChange={(e) => setGcpCredentials(prev => ({ ...prev, privateKey: e.target.value }))}
                          placeholder="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
                          rows={4}
                          required
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="clientEmail">Client Email</Label>
                        <Input
                          id="clientEmail"
                          type="email"
                          value={gcpCredentials.clientEmail}
                          onChange={(e) => setGcpCredentials(prev => ({ ...prev, clientEmail: e.target.value }))}
                          placeholder="my-service-account@my-project-id.iam.gserviceaccount.com"
                          required
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="authUri">Auth URI</Label>
                        <Input
                          id="authUri"
                          value={gcpCredentials.authUri}
                          onChange={(e) => setGcpCredentials(prev => ({ ...prev, authUri: e.target.value }))}
                          placeholder="https://accounts.google.com/o/oauth2/auth"
                          required
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="tokenUri">Token URI</Label>
                        <Input
                          id="tokenUri"
                          value={gcpCredentials.tokenUri}
                          onChange={(e) => setGcpCredentials(prev => ({ ...prev, tokenUri: e.target.value }))}
                          placeholder="https://oauth2.googleapis.com/token"
                          required
                        />
                      </div>

                      <Button type="submit" className="w-full">
                        Save GCP Configuration
                      </Button>
                    </form>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="security">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <UserPlus className="h-5 w-5 text-primary" />
                  Add User
                </CardTitle>
                <CardDescription>
                  Create new users
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleCreateUser} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="userId">User ID</Label>
                    <Input
                      id="userId"
                      type="text"
                      value={newUser.userId}
                      onChange={(e) => setNewUser(prev => ({ ...prev, userId: e.target.value }))}
                      placeholder="Enter user ID"
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="userPassword">Password</Label>
                    <Input
                      id="userPassword"
                      type="password"
                      value={newUser.password}
                      onChange={(e) => setNewUser(prev => ({ ...prev, password: e.target.value }))}
                      placeholder="Enter password"
                      required
                    />
                  </div>

                  <div className="flex items-center space-x-2">
                    <Checkbox
                      id="isAdmin"
                      checked={newUser.isAdmin}
                      onCheckedChange={(checked) => setNewUser(prev => ({ ...prev, isAdmin: !!checked }))}
                    />
                    <Label htmlFor="isAdmin" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
                      Make this user an admin
                    </Label>
                  </div>

                  <Button type="submit" className="w-full">
                    <UserPlus className="h-4 w-4 mr-2" />
                    Create User
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