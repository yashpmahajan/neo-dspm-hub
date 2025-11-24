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
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
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
  RotateCcw,
  ChevronDown
} from "lucide-react";
import { UploadModal } from "@/components/UploadModal";

const Dashboard = () => {
  const [syntheticData, setSyntheticData] = useState<any[]>([]);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [scanResults, setScanResults] = useState<string | null>(null);
  const [selectedDataType, setSelectedDataType] = useState<string>('');
  const [selectedExportFormat, setSelectedExportFormat] = useState<'pdf' | 'csv' | 'json' | ''>('');
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
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isGenerateExpanded, setIsGenerateExpanded] = useState(true);
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
    toast({
      title: "Data generated successfully",
      description: "Data has been generated.",
    });
  };

  // Generate data using backend API
  const generateDataFile = async () => {
    if (!selectedDataType || !selectedExportFormat) {
      return;
    }
    
    setIsGenerating(true);
    try {
      const token = localStorage.getItem("authToken");
      const backendApi = import.meta.env.VITE_BACKEND_API;
      const response = await fetch(`${backendApi}/generatedata?filetype=${selectedExportFormat}&datatype=${encodeURIComponent(selectedDataType)}`, {
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
        a.download = `data.${selectedExportFormat}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        toast({
          title: "Data generated successfully",
          description: `${selectedDataType} data generated and saved to ${selectedExportFormat.toUpperCase()} file`,
        });
      } else {
        throw new Error('Failed to generate file');
      }
    } catch (error) {
      toast({
        title: "Error",
        description: `Failed to generate ${selectedExportFormat.toUpperCase()} file`,
        variant: "destructive",
      });
    } finally {
      setIsGenerating(false);
    }
  };

  // Upload to cloud storage using backend API with credentials
  const handleUpload = async (provider: string | null, credentials: Record<string, string>) => {
    setIsUploading(true);
    setUploadStatus('idle');
    
    try {
      const token = localStorage.getItem("authToken");
      const backendApi = import.meta.env.VITE_BACKEND_API;
      
      const response = await fetch(`${backendApi}/upload-env-bucket`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          provider,
          credentials
        }),
      });

      const result = await response.json();
      
      if (response.ok) {
        setUploadStatus('success');
        setUploadedFileUrl(result.file_url);
        setIsUploadModalOpen(false);
        toast({
          title: "Upload successful",
          description: `File uploaded to ${provider?.toUpperCase()} successfully`,
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
          description: "Cloud Scan completed successfully",
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
    setSelectedDataType('');
    setSelectedExportFormat('');
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
      <div className="mb-8 ">
        <h1 className="text-3xl font-bold text-neo-blue">
          Data Security Posture Management
        </h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-6xl">
        {/* Generate Synthetic Data */}
        <Collapsible
          open={isGenerateExpanded}
          onOpenChange={setIsGenerateExpanded}
          className="h-fit"
        >
          <Card>
            <CollapsibleTrigger asChild>
              <CardHeader className="cursor-pointer hover:bg-accent/50 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <CardTitle className="flex items-center gap-2">
                      <Database className="h-6 w-6 text-primary" />
                      Generate Data
                    </CardTitle>
                    <CardDescription className="mt-1.5">
                      Generate realistic data via LLM.
                    </CardDescription>
                  </div>
                  <ChevronDown
                    className={`h-5 w-5 text-muted-foreground transition-transform duration-200 ${
                      isGenerateExpanded ? 'rotate-180' : ''
                    }`}
                  />
                </div>
              </CardHeader>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <CardContent className="space-y-4 pt-0">
                {/* Data Type Selection */}
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Data Type</Label>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {[
                      'PII Data',
                      'Financial / Credit Card Data',
                      'Employee / HR Data',
                      'Healthcare / Medical Records',
                      'Government Data',
                      'Insurance Data',
                      'Business Document'
                    ].map((type) => (
                      <Button
                        key={type}
                        variant={selectedDataType === type ? "default" : "outline"}
                        size="sm"
                        onClick={() => setSelectedDataType(type)}
                        className="text-xs h-auto py-2 px-3"
                      >
                        {type}
                      </Button>
                    ))}
                  </div>
                </div>

                {/* Export Format Selection */}
                <div className="space-y-2">
                  <Label className="text-sm font-medium">Export Format</Label>
                  <div className="flex gap-2">
                    <Button
                      variant={selectedExportFormat === 'pdf' ? "default" : "outline"}
                      size="sm"
                      onClick={() => setSelectedExportFormat('pdf')}
                    >
                      <FileText className="h-4 w-4 mr-2" />
                      PDF
                    </Button>
                    <Button
                      variant={selectedExportFormat === 'csv' ? "default" : "outline"}
                      size="sm"
                      onClick={() => setSelectedExportFormat('csv')}
                    >
                      <Table className="h-4 w-4 mr-2" />
                      CSV
                    </Button>
                    <Button
                      variant={selectedExportFormat === 'json' ? "default" : "outline"}
                      size="sm"
                      onClick={() => setSelectedExportFormat('json')}
                    >
                      <Code className="h-4 w-4 mr-2" />
                      JSON
                    </Button>
                  </div>
                </div>

                {/* Generate Data Button */}
                <div className="space-y-2 pt-2">
                  <Button
                    onClick={generateDataFile}
                    className="w-full"
                    disabled={!selectedDataType || !selectedExportFormat || isGenerating}
                  >
                    {isGenerating ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        Generating...
                      </>
                    ) : (
                      'Generate Data'
                    )}
                  </Button>
                  {(!selectedDataType || !selectedExportFormat) && (
                    <p className="text-xs text-muted-foreground text-center">
                      Select a data type and export format to continue.
                    </p>
                  )}
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
              </CardContent>
            </CollapsibleContent>
          </Card>
        </Collapsible>

        {/* Upload to S3 */}
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-6 w-6 text-primary" />
              Upload Generated Data To Cloud Datastore
            </CardTitle>
            <CardDescription>
              Upload the generated data file to your cloud datastore.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button
              onClick={() => setIsUploadModalOpen(true)}
              className="w-full"
              disabled={isUploading}
            >
              {isUploading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Upload className="h-4 w-4 mr-2" />}
              Upload
            </Button>

            <UploadModal
              open={isUploadModalOpen}
              onOpenChange={setIsUploadModalOpen}
              onUpload={handleUpload}
              isUploading={isUploading}
            />

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
                    <p className="text-xs text-muted-foreground">Cloud Scan In Progress. Do Not Go Back Or Refresh the Page.</p>
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
                    <Button onClick={downloadArtifacts} className="w-full">
                      <Download className="h-4 w-4 mr-2" />
                      Download Artifacts
                    </Button>
                  </div>
                  <Button
                    onClick={() => {
                      setIsScanExpanded(true);
                      setScanCompleted(false);
                      setIsScanning(false);
                      setScanStep(1);
                    }}
                    className="w-full mt-2"
                  >
                    Re-Run Scan
                  </Button>
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

