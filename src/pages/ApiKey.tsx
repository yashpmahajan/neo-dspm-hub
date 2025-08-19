import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/hooks/use-toast";

const ApiKey = () => {
  const [apiKey, setApiKey] = useState("");
  const { toast } = useToast();

  useEffect(() => {
    // Load existing API key from localStorage
    const savedKey = localStorage.getItem("openai_api_key");
    if (savedKey) {
      setApiKey(savedKey);
    }
  }, []);

  const handleSave = () => {
    if (!apiKey.trim()) {
      toast({
        title: "Error",
        description: "Please enter a valid API key.",
        variant: "destructive",
        duration: 4000,
      });
      return;
    }

    try {
      localStorage.setItem("openai_api_key", apiKey);
      toast({
        title: "Success",
        description: "API key saved successfully.",
        duration: 3000,
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to save API key.",
        variant: "destructive",
        duration: 4000,
      });
    }
  };

  const handleClear = () => {
    try {
      localStorage.removeItem("openai_api_key");
      setApiKey("");
      toast({
        title: "Success",
        description: "API key cleared successfully.",
        duration: 3000,
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to clear API key.",
        variant: "destructive",
        duration: 4000,
      });
    }
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
          <div className="flex gap-2">
            <Button onClick={handleSave} className="flex-1 sm:flex-none">
              Save Key
            </Button>
            <Button onClick={handleClear} variant="outline" className="flex-1 sm:flex-none">
              Clear Key
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default ApiKey;