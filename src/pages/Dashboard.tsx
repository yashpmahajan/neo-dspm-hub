import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { 
  Database, 
  Upload, 
  Scan,
  Download,
  CheckCircle,
  XCircle
} from "lucide-react";

const Dashboard = () => {
  const [syntheticData, setSyntheticData] = useState<any[]>([]);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [scanResults, setScanResults] = useState<string | null>(null);

  const generateSyntheticData = () => {
    const mockData = [
      { name: "John Smith", email: "john.smith@email.com", phone: "(555) 123-4567", ssn: "***-**-1234" },
      { name: "Jane Doe", email: "jane.doe@email.com", phone: "(555) 987-6543", ssn: "***-**-5678" },
      { name: "Bob Johnson", email: "bob.johnson@email.com", phone: "(555) 456-7890", ssn: "***-**-9012" },
    ];
    setSyntheticData(mockData);
  };

  const uploadToS3 = () => {
    // Simulate upload process
    setTimeout(() => {
      setUploadStatus(Math.random() > 0.2 ? 'success' : 'error');
    }, 1500);
  };

  const runPIIScan = () => {
    // Simulate scan process
    setTimeout(() => {
      setScanResults("Found: 3 emails, 3 phone numbers, 3 SSNs");
    }, 2000);
  };

  const downloadReport = () => {
    // Simulate report download
    const element = document.createElement('a');
    element.href = 'data:text/plain;charset=utf-8,PII Scan Report\nGenerated Data Security Report\n\nFound sensitive data patterns:\n- 3 email addresses\n- 3 phone numbers\n- 3 SSN patterns';
    element.download = 'pii-scan-report.txt';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-foreground">Data Security Posture Management</h1>
        <p className="text-muted-foreground mt-2">Follow the workflow from left to right, top to bottom</p>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-6xl">
        {/* Generate Synthetic Data */}
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-6 w-6 text-primary" />
              Generate Synthetic Data
            </CardTitle>
            <CardDescription>
              Generate fake personal information for testing.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button onClick={generateSyntheticData} className="w-full">
              Generate Data
            </Button>
            
            {syntheticData.length > 0 && (
              <div className="space-y-2">
                <h4 className="font-medium text-sm">Generated Data Preview:</h4>
                <div className="space-y-2 max-h-32 overflow-y-auto">
                  {syntheticData.map((item, index) => (
                    <div key={index} className="text-xs p-2 bg-muted rounded">
                      <div>{item.name} - {item.email}</div>
                      <div>{item.phone} - {item.ssn}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Upload to S3 */}
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-6 w-6 text-primary" />
              Upload to S3
            </CardTitle>
            <CardDescription>
              Upload the generated data file to your AWS S3 bucket.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button 
              onClick={uploadToS3} 
              className="w-full"
              disabled={syntheticData.length === 0}
            >
              Upload to Cloud
            </Button>
            
            {uploadStatus === 'success' && (
              <div className="flex items-center gap-2 text-green-600">
                <CheckCircle className="h-4 w-4" />
                <span className="text-sm">Upload successful!</span>
              </div>
            )}
            
            {uploadStatus === 'error' && (
              <div className="flex items-center gap-2 text-red-600">
                <XCircle className="h-4 w-4" />
                <span className="text-sm">Upload failed. Please try again.</span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Run PII Scan */}
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Scan className="h-6 w-6 text-primary" />
              Run PII Scan
            </CardTitle>
            <CardDescription>
              Scan uploaded file for sensitive data patterns.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button 
              onClick={runPIIScan} 
              className="w-full"
              disabled={uploadStatus !== 'success'}
            >
              Run Scan
            </Button>
            
            {scanResults && (
              <div className="p-3 bg-muted rounded">
                <h4 className="font-medium text-sm mb-1">Scan Results:</h4>
                <p className="text-sm text-muted-foreground">{scanResults}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Download Report */}
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Download className="h-6 w-6 text-primary" />
              Download Report
            </CardTitle>
            <CardDescription>
              Download a full PDF report of scan results.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button 
              onClick={downloadReport} 
              className="w-full"
              disabled={!scanResults}
            >
              Download Report
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Dashboard;