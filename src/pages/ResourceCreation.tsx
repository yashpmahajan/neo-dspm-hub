import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const ResourceCreation = () => {
  const [benchmark, setBenchmark] = useState("");
  const [platform, setPlatform] = useState("");

  return (
    <div className="p-6">
      <Card className="max-w-4xl">
        <CardHeader>
          <CardTitle>Resource Creation</CardTitle>
          <CardDescription>
            Select a compliance benchmark, cloud platform, resource type, and specific controls (if applicable), then edit the Terraform code to create the resource.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <Label>Choose a compliance benchmark...</Label>
              <Select value={benchmark} onValueChange={setBenchmark}>
                <SelectTrigger>
                  <SelectValue placeholder="Choose a compliance benchmark..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="cis">CIS Benchmarks</SelectItem>
                  <SelectItem value="nist">NIST Framework</SelectItem>
                  <SelectItem value="pci">PCI DSS</SelectItem>
                  <SelectItem value="iso">ISO 27001</SelectItem>
                  <SelectItem value="soc">SOC 2</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Choose a cloud platform...</Label>
              <Select value={platform} onValueChange={setPlatform}>
                <SelectTrigger>
                  <SelectValue placeholder="Choose a cloud platform..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="aws">AWS</SelectItem>
                  <SelectItem value="azure">Azure</SelectItem>
                  <SelectItem value="gcp">GCP</SelectItem>
                  <SelectItem value="ibm">IBM Cloud</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex gap-4">
            <Button 
              variant="outline" 
              disabled={!benchmark || !platform}
            >
              Generate Terraform Code
            </Button>
            <Button 
              disabled={!benchmark || !platform}
            >
              Create Resource
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default ResourceCreation;