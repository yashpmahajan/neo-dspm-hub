import { useState, useEffect } from "react";
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
  const [isScanning, setIsScanning] = useState(false);
  const [scanCompleted, setScanCompleted] = useState(false);
  const [scanStep, setScanStep] = useState(1);
  const [isScanExpanded, setIsScanExpanded] = useState(false);
  const [scanFormData, setScanFormData] = useState({
    bearerTokenCurl: '',
    scanTriggerCurl: '',
    clientResultCurl: ''
  });
  const { toast } = useToast();

  // LocalStorage keys for persistence
  const SCAN_STATE_KEY = 'dashboardScanState';

  // Save scan state to localStorage
  const saveScanState = (state: {
    isScanning: boolean;
    scanCompleted: boolean;
    isScanExpanded: boolean;
    scanFormData: typeof scanFormData;
  }) => {
    localStorage.setItem(SCAN_STATE_KEY, JSON.stringify(state));
  };

  // Load scan state from localStorage
  const loadScanState = () => {
    try {
      const saved = localStorage.getItem(SCAN_STATE_KEY);
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (error) {
      console.error('Failed to load scan state:', error);
    }
    return null;
  };

  // Clear scan state from localStorage
  const clearScanState = () => {
    localStorage.removeItem(SCAN_STATE_KEY);
  };

  // Restore state from localStorage on component mount
  useEffect(() => {
    const savedState = loadScanState();
    if (savedState) {
      setIsScanning(savedState.isScanning || false);
      setScanCompleted(savedState.scanCompleted || false);
      setIsScanExpanded(savedState.isScanExpanded || false);
      setScanFormData(savedState.scanFormData || {
        bearerTokenCurl: '',
        scanTriggerCurl: '',
        clientResultCurl: ''
      });
    }
  }, []);

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
      const backendApi = import.meta.env.VITE_BACKEND_API;
      const response = await fetch(`${backendApi}/generatedata?filetype=${filetype}`, {
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
      
      const backendApi = import.meta.env.VITE_BACKEND_API;
      const response = await fetch(`${backendApi}/upload-env-bucket`, {
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

  const handleScanFormSubmit = () => {
    // Validate all fields are filled
    if (!scanFormData.bearerTokenCurl.trim() || !scanFormData.scanTriggerCurl.trim() || !scanFormData.clientResultCurl.trim()) {
      toast({
        title: "Validation Error",
        description: "Please fill in all required fields",
        variant: "destructive",
      });
      return;
    }
    
    // Start the scan process with progress
    setIsScanning(true);
    setScanStep(1);
    
    // Save scan state to localStorage
    saveScanState({
      isScanning: true,
      scanCompleted: false,
      isScanExpanded: true,
      scanFormData
    });
    
    // Simulate step progression
    setTimeout(() => setScanStep(2), 2000);
    setTimeout(() => setScanStep(3), 300000); // 5 minutes for step 3
    
    // Run the actual scan using user input and auth token
    const myHeaders = new Headers();
    myHeaders.append("Content-Type", "application/json");
    const token = localStorage.getItem("authToken");
    if (!token) {
      toast({
        title: "Not authenticated",
        description: "Please log in to run the scan.",
        variant: "destructive",
      });
      setIsScanning(false);
      setScanStep(1);
      saveScanState({
        isScanning: false,
        scanCompleted: false,
        isScanExpanded: true,
        scanFormData
      });
      return;
    }
    myHeaders.append("Authorization", `Bearer ${token}`);

    const raw = JSON.stringify({
      "curl_commands": [
        scanFormData.bearerTokenCurl,
        scanFormData.scanTriggerCurl,
        scanFormData.clientResultCurl
      ]
    });

    const requestOptions = {
      method: "POST",
      headers: myHeaders,
      body: raw,
      redirect: "follow"
    } as RequestInit;

    const baseUrl = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000'
    fetch(`${baseUrl}/data-scan`, requestOptions)
      .then((response) => response.text())
      .then((result) => {
        console.log(result);
        setScanResults(result || "Scan completed");
        setIsScanning(false);
        setScanCompleted(true);
        setScanStep(1);
        
        // Save completed state to localStorage
        saveScanState({
          isScanning: false,
          scanCompleted: true,
          isScanExpanded: true,
          scanFormData
        });
        
        toast({
          title: "Scan completed",
          description: "PII scan has been completed successfully",
        });
      })
      .catch((error) => {
        console.error(error);
        setIsScanning(false);
        setScanStep(1);
        
        // Save error state to localStorage
        saveScanState({
          isScanning: false,
          scanCompleted: false,
          isScanExpanded: true,
          scanFormData
        });
        
        toast({
          title: "Scan failed",
          description: "Failed to run scan",
          variant: "destructive",
        });
      });
  };

  const handleScanFormChange = (field: string, value: string) => {
    const newFormData = {
      ...scanFormData,
      [field]: value
    };
    setScanFormData(newFormData);
    
    // Save updated form data to localStorage
    saveScanState({
      isScanning,
      scanCompleted,
      isScanExpanded,
      scanFormData: newFormData
    });
  };

  const downloadReport = async () => {
    try {
      const baseUrl = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000'
      const res = await fetch(`${baseUrl}/download/report`, { method: 'GET' })
      if (!res.ok) {
        throw new Error(`Failed to download report: ${res.status}`)
      }
      const blob = await res.blob()
      let filename = 'dspm_validation_report.pdf'
      const cd = res.headers.get('Content-Disposition') || res.headers.get('content-disposition')
      if (cd) {
        const m = cd.match(/filename="?([^";]+)"?/i)
        if (m && m[1]) filename = m[1]
      }
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error(err)
    }
  };

  const downloadArtifacts = async () => {
    try {
      const baseUrl = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000'
      const res = await fetch(`${baseUrl}/download/artifacts-zip`, { method: 'GET' })
      if (!res.ok) {
        throw new Error(`Failed to download artifacts: ${res.status}`)
      }
      const blob = await res.blob()
      let filename = 'scan_artifacts.zip'
      const cd = res.headers.get('Content-Disposition') || res.headers.get('content-disposition')
      if (cd) {
        const m = cd.match(/filename="?([^";]+)"?/i)
        if (m && m[1]) filename = m[1]
      }
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
      
      toast({
        title: "Artifacts downloaded",
        description: "Scan artifacts have been downloaded successfully",
      });
    } catch (err) {
      console.error(err)
      toast({
        title: "Download failed",
        description: "Failed to download artifacts",
        variant: "destructive",
      });
    }
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
    setIsScanning(false);
    setScanCompleted(false);
    setScanStep(1);
    setIsScanExpanded(false);
    setScanFormData({
      bearerTokenCurl: '',
      scanTriggerCurl: '',
      clientResultCurl: ''
    });
    setIsResetDialogOpen(false);
    
    // Clear localStorage
    clearScanState();
    
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
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-6xl">
        {/* Generate Synthetic Data */}
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-6 w-6 text-primary" />
              Generate Data
            </CardTitle>
            <CardDescription>
              <div>
                Generate realistic data via LLM.
              </div>
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
              Upload Generated Data To S3
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
        <div className="lg:col-span-2 flex justify-center">
        <Card className="h-fit w-full max-w-2xl">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Scan className="h-6 w-6 text-primary" />
              Run Data Scan
            </CardTitle>
            <CardDescription>
              {!isScanExpanded && !isScanning && !scanCompleted 
                ? "Click to trigger a new data scan"
                : "Use Valid API cURL commands to run the scan"
              }
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {!isScanExpanded && !isScanning && !scanCompleted ? (
              <>
                {/* Collapsed State - Default View */}
                <Button
                  onClick={() => setIsScanExpanded(true)}
                  className="w-full"
                >
                  <Scan className="h-4 w-4 mr-2" />
                  Start Scan
                </Button>
              </>
            ) : isScanExpanded && !isScanning && !scanCompleted ? (
              <>
                {/* Expanded State - Form View */}
                <div className="space-y-4">
                  <div className="grid grid-cols-1 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="bearerTokenCurl">Bearer Token API *</Label>
                      <Textarea
                        id="bearerTokenCurl"
                        placeholder="Enter bearer token API cURL command"
                        value={scanFormData.bearerTokenCurl}
                        onChange={(e) => handleScanFormChange('bearerTokenCurl', e.target.value)}
                        className="min-h-[100px]"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="scanTriggerCurl">Data Scanning API *</Label>
                      <Textarea
                        id="scanTriggerCurl"
                        placeholder="Enter data scanning API cURL command"
                        value={scanFormData.scanTriggerCurl}
                        onChange={(e) => handleScanFormChange('scanTriggerCurl', e.target.value)}
                        className="min-h-[100px]"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="clientResultCurl">Fetch Inventory Data API *</Label>
                      <Textarea
                        id="clientResultCurl"
                        placeholder="Enter fetch inventory data cURL command"
                        value={scanFormData.clientResultCurl}
                        onChange={(e) => handleScanFormChange('clientResultCurl', e.target.value)}
                        className="min-h-[100px]"
                      />
                    </div>
                  </div>
                  <Button
                    onClick={handleScanFormSubmit}
                    className="w-full"
                    disabled={!scanFormData.bearerTokenCurl.trim() || !scanFormData.scanTriggerCurl.trim() || !scanFormData.clientResultCurl.trim()}
                  >
                    Run Scan
                  </Button>
                </div>
              </>
            ) : isScanning ? (
              <>
                {/* Scan Progress - Loading State */}
                <div className="space-y-4 pt-2 border-t">
                  <div className="flex items-center justify-center p-6">
                    <Loader2 className="h-8 w-8 animate-spin text-primary" />
                  </div>
                  
                  <div className="text-center space-y-2">
                    <p className="text-sm font-medium">🔄 Scan in progress...</p>
                    <p className="text-xs text-muted-foreground">This may take up to 15 minutes. Please keep this tab open.</p>
                  </div>
                </div>
              </>
            ) : scanCompleted ? (
              <>
                {/* Scan Completion - Success State */}
                <div className="space-y-4 pt-2 border-t">
                  <div className="flex items-center justify-center p-6">
                    <CheckCircle className="h-8 w-8 text-green-600" />
                  </div>
                  
                  <div className="text-center space-y-2">
                    <p className="text-sm font-medium text-green-600">✅ Run Scan completed.</p>
                    <p className="text-xs text-muted-foreground">Please download the report or artifacts.</p>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <Button onClick={downloadReport} className="w-full">
                      <Download className="h-4 w-4 mr-2" />
                      Download Report
                    </Button>
                    <Button onClick={downloadArtifacts} variant="outline" className="w-full">
                      <Download className="h-4 w-4 mr-2" />
                      Download Artifacts
                    </Button>
                  </div>
                </div>
              </>
            ) : null}
          </CardContent>
        </Card>
        </div>

        
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

