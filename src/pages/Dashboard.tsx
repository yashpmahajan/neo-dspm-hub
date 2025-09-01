import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { 
  Database, 
  Upload, 
  Scan,
  Download,
  CheckCircle,
  XCircle,
  FileText,
  Table,
  Code,
  Loader2,
  RotateCcw
} from "lucide-react";

const Dashboard = () => {
  const [syntheticData, setSyntheticData] = useState<any[]>([]);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [scanResults, setScanResults] = useState<string | null>(null);
  const [generateDataBtnDisabled, setGenerateDataBtnDisabled] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedFileUrl, setUploadedFileUrl] = useState<string>('');
  const [isResetDialogOpen, setIsResetDialogOpen] = useState(false);
  const [showScanForm, setShowScanForm] = useState(false);
  const [scanFormData, setScanFormData] = useState({
    bearerToken: '',
    scanDataCurl: '',
    inventoryDataCurl: ''
  });
  const { toast } = useToast();

  // Get auth token from localStorage
  const getAuthHeaders = () => {
    const token = localStorage.getItem("authToken");
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
  };

  const generateSyntheticData = () => {
    const mockData = [
      { name: "John Smith", email: "john.smith@email.com", phone: "(555) 123-4567", ssn: "***-**-1234" },
      { name: "Jane Doe", email: "jane.doe@email.com", phone: "(555) 987-6543", ssn: "***-**-5678" },
      { name: "Bob Johnson", email: "bob.johnson@email.com", phone: "(555) 456-7890", ssn: "***-**-9012" },
    ];
    setSyntheticData(mockData);
  };

  // Generate data using backend API
  const generateDataFile = async (filetype: 'pdf' | 'csv' | 'json') => {
    setIsGenerating(true);
    try {
      const token = localStorage.getItem("authToken");
      const response = await fetch(`/api/generatedata?filetype=${filetype}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (response.ok) {
        // Download the file
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `data.${filetype}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        toast({
          title: "File generated successfully",
          description: `${filetype.toUpperCase()} file has been downloaded`,
        });
      } else {
        throw new Error('Failed to generate file');
      }
    } catch (error) {
      toast({
        title: "Error",
        description: `Failed to generate ${filetype.toUpperCase()} file`,
        variant: "destructive",
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const generateDataAsPDF = () => generateDataFile('pdf');
  const generateDataAsCSV = () => generateDataFile('csv');
  const generateDataAsJSON = () => generateDataFile('json');

  // Upload to S3 using backend API  
  const uploadToS3 = async (filetype: 'pdf' | 'csv' | 'json') => {
    setIsUploading(true);
    setUploadStatus('idle');
    
    try {
      const token = localStorage.getItem("authToken");
      const formData = new FormData();
      
      const response = await fetch('/api/uploadtobucket', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      const result = await response.json();
      
      if (response.ok) {
        setUploadStatus('success');
        setUploadedFileUrl(result.file_url);
        toast({
          title: "Upload successful",
          description: `${filetype.toUpperCase()} file uploaded to S3`,
        });
      } else {
        throw new Error(result.detail || 'Upload failed');
      }
    } catch (error) {
      setUploadStatus('error');
      toast({
        title: "Upload failed",
        description: error instanceof Error ? error.message : "Failed to upload file",
        variant: "destructive",
      });
    } finally {
      setIsUploading(false);
    }
  };

  const runPIIScan = () => {
    // Simulate scan process
    setTimeout(() => {
      setScanResults("Found: 3 emails, 3 phone numbers, 3 SSNs");
    }, 2000);
  };

  const showScanFormHandler = () => {
    setShowScanForm(true);
  };

  const handleScanFormSubmit = () => {
    // Validate all fields are filled
    if (!scanFormData.bearerToken.trim() || !scanFormData.scanDataCurl.trim() || !scanFormData.inventoryDataCurl.trim()) {
      toast({
        title: "Validation Error",
        description: "Please fill in all required fields",
        variant: "destructive",
      });
      return;
    }
    
    // Run the actual scan (placeholder for now)
    setTimeout(() => {
      setScanResults("Found: 3 emails, 3 phone numbers, 3 SSNs");
      toast({
        title: "Scan completed",
        description: "PII scan has been completed successfully",
      });
    }, 2000);
  };

  const handleScanFormChange = (field: string, value: string) => {
    setScanFormData(prev => ({
      ...prev,
      [field]: value
    }));
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

  const resetConfiguration = () => {
    // Clear all UI state
    setSyntheticData([]);
    setUploadStatus('idle');
    setScanResults(null);
    setGenerateDataBtnDisabled(false);
    setIsGenerating(false);
    setIsUploading(false);
    setUploadedFileUrl('');
    setShowScanForm(false);
    setScanFormData({
      bearerToken: '',
      scanDataCurl: '',
      inventoryDataCurl: ''
    });
    setIsResetDialogOpen(false);
    
    toast({
      title: "Configuration reset",
      description: "All configurations and progress have been cleared",
    });
  };

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-foreground">
          Data Security Posture Management
        </h1>
        <p className="text-muted-foreground mt-2">
          Follow the workflow from left to right, top to bottom
        </p>
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
            {/* <Button onClick={generateSyntheticData} className="w-full">
              Generate Data
            </Button> */}
            <Button
              onClick={() => setGenerateDataBtnDisabled(true)}
              className="w-full"
            >
              Generate Data
            </Button>

            {generateDataBtnDisabled && (
              <>
                {/* Export Options */}
                <div className="space-y-2 pt-2 border-t">
                  <h4 className="font-medium text-sm">Export Options:</h4>
                  <div className="grid grid-cols-3 gap-2">
                    <Button
                      onClick={generateDataAsPDF}
                      variant="outline"
                      size="sm"
                      disabled={isGenerating}
                    >
                      {isGenerating ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <FileText className="h-4 w-4 mr-2" />}
                      PDF
                    </Button>
                    <Button
                      onClick={generateDataAsCSV}
                      variant="outline"
                      size="sm"
                      disabled={isGenerating}
                    >
                      {isGenerating ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Table className="h-4 w-4 mr-2" />}
                      CSV
                    </Button>
                    <Button
                      onClick={generateDataAsJSON}
                      variant="outline"
                      size="sm"
                      disabled={isGenerating}
                    >
                      {isGenerating ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Code className="h-4 w-4 mr-2" />}
                      JSON
                    </Button>
                  </div>
                </div>
                {syntheticData.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="font-medium text-sm">
                      Generated Data Preview:
                    </h4>
                    <div className="space-y-2 max-h-32 overflow-y-auto">
                      {syntheticData.map((item, index) => (
                        <div
                          key={index}
                          className="text-xs p-2 bg-muted rounded"
                        >
                          <div>
                            {item.name} - {item.email}
                          </div>
                          <div>
                            {item.phone} - {item.ssn}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
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
              onClick={() => uploadToS3('pdf')}
              className="w-full"
              disabled={isUploading}
            >
              {isUploading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Upload className="h-4 w-4 mr-2" />}
              Upload
            </Button>

            {uploadStatus === "success" && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-green-600">
                  <CheckCircle className="h-4 w-4" />
                  <span className="text-sm">Upload successful!</span>
                </div>
                {uploadedFileUrl && (
                  <div className="p-2 bg-muted rounded text-xs">
                    <p className="font-medium">File URL:</p>
                    <p className="break-all">{uploadedFileUrl}</p>
                  </div>
                )}
              </div>
            )}

            {uploadStatus === "error" && (
              <div className="flex items-center gap-2 text-red-600">
                <XCircle className="h-4 w-4" />
                <span className="text-sm">
                  Upload failed. Please try again.
                </span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Run Scan */}
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Scan className="h-6 w-6 text-primary" />
              Run Scan
            </CardTitle>
            <CardDescription>
              Configure and run scan for sensitive data patterns.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {!showScanForm ? (
              <Button
                onClick={showScanFormHandler}
                className="w-full"
              >
                Run Scan
              </Button>
            ) : (
              <>
                {/* Scan Configuration Form */}
                <div className="space-y-4 pt-2 border-t">
                  <div className="grid grid-cols-1 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="bearerToken">Bearer Token *</Label>
                      <Input
                        id="bearerToken"
                        placeholder="Enter your bearer token"
                        value={scanFormData.bearerToken}
                        onChange={(e) => handleScanFormChange('bearerToken', e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="scanDataCurl">Curl Command for Scan Data *</Label>
                      <Textarea
                        id="scanDataCurl"
                        placeholder="Enter curl command for scan data"
                        value={scanFormData.scanDataCurl}
                        onChange={(e) => handleScanFormChange('scanDataCurl', e.target.value)}
                        className="min-h-[100px]"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="inventoryDataCurl">Curl Command for Fetching Inventory Data *</Label>
                      <Textarea
                        id="inventoryDataCurl"
                        placeholder="Enter curl command for fetching inventory data"
                        value={scanFormData.inventoryDataCurl}
                        onChange={(e) => handleScanFormChange('inventoryDataCurl', e.target.value)}
                        className="min-h-[100px]"
                      />
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      onClick={() => setShowScanForm(false)}
                      variant="outline"
                      className="flex-1"
                    >
                      Cancel
                    </Button>
                    <Button
                      onClick={handleScanFormSubmit}
                      className="flex-1"
                      disabled={!scanFormData.bearerToken.trim() || !scanFormData.scanDataCurl.trim() || !scanFormData.inventoryDataCurl.trim()}
                    >
                      Run Scan
                    </Button>
                  </div>
                </div>
              </>
            )}

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
            >
              Download Report
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Reset Configuration Button */}
      <div className="mt-8 flex justify-center max-w-6xl">
        <AlertDialog open={isResetDialogOpen} onOpenChange={setIsResetDialogOpen}>
          <AlertDialogTrigger asChild>
            <Button variant="destructive" className="gap-2">
              <RotateCcw className="h-4 w-4" />
              Reset Configuration
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Reset Configuration</AlertDialogTitle>
              <AlertDialogDescription>
                Are you sure you want to reset all configurations and progress? This action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={resetConfiguration}>
                Yes, Reset
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </div>
  );
};

export default Dashboard;