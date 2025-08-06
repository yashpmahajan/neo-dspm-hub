import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const ApiKey = () => {
  const [apiKey, setApiKey] = useState("");

  const handleSave = () => {
    // Handle API key save logic
    console.log("Saving API key:", apiKey);
  };

  return (
    <div className="p-6">
      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Set OpenAI API Key</CardTitle>
          <CardDescription>
            Enter your OpenAI API key to enable AI features. You can find your key in your OpenAI account dashboard.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="api-key">API Key</Label>
            <Input
              id="api-key"
              type="password"
              placeholder="sk-BGUDtEXGnGYQT6-s-ExBrey6Z_mCsKKWZQA"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="font-mono"
            />
          </div>
          <Button onClick={handleSave} className="w-full sm:w-auto">
            Save API Key
          </Button>
        </CardContent>
      </Card>
    </div>
  );
};

export default ApiKey;