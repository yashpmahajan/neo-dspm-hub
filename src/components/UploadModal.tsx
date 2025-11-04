import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Cloud, Database } from "lucide-react";

type CloudProvider = 'aws' | 'azure' | 'rds' | null;

interface UploadModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onUpload: (provider: CloudProvider, credentials: Record<string, string>) => void;
  isUploading: boolean;
}

export const UploadModal = ({ open, onOpenChange, onUpload, isUploading }: UploadModalProps) => {
  const [selectedProvider, setSelectedProvider] = useState<CloudProvider>(null);
  const [credentials, setCredentials] = useState<Record<string, string>>({});

  const handleProviderSelect = (provider: CloudProvider) => {
    setSelectedProvider(provider);
    setCredentials({});
  };

  const handleBack = () => {
    setSelectedProvider(null);
    setCredentials({});
  };

  const handleCredentialChange = (field: string, value: string) => {
    setCredentials(prev => ({ ...prev, [field]: value }));
  };

  const handleUpload = () => {
    onUpload(selectedProvider, credentials);
  };

  const handleCancel = () => {
    setSelectedProvider(null);
    setCredentials({});
    onOpenChange(false);
  };

  const getRequiredFields = (provider: CloudProvider) => {
    switch (provider) {
      case 'aws':
        return [
          { key: 'AWS_ACCESS_KEY_ID', label: 'AWS Access Key ID', placeholder: 'Enter your AWS Access Key ID' },
          { key: 'AWS_SECRET_ACCESS_KEY', label: 'AWS Secret Access Key', placeholder: 'Enter your AWS Secret Access Key' },
          { key: 'AWS_REGION', label: 'AWS Region', placeholder: 'e.g., us-east-1' },
          { key: 'AWS_BUCKET_NAME', label: 'AWS Bucket Name', placeholder: 'Enter your S3 bucket name' },
        ];
      case 'azure':
        return [
          { key: 'AZURE_STORAGE_ACCOUNT_NAME', label: 'Azure Storage Account Name', placeholder: 'Enter your Azure storage account name' },
          { key: 'AZURE_STORAGE_ACCOUNT_KEY', label: 'Azure Storage Account Key', placeholder: 'Enter your Azure storage account key' },
          { key: 'AZURE_CONTAINER_NAME', label: 'Azure Container Name', placeholder: 'Enter your Azure container name' },
        ];
      case 'rds':
        return [
          { key: 'RDS_HOST', label: 'RDS Host', placeholder: 'Enter your RDS host' },
          { key: 'RDS_PORT', label: 'RDS Port', placeholder: 'e.g., 3306 or 5432' },
          { key: 'RDS_USERNAME', label: 'RDS Username', placeholder: 'Enter your RDS username' },
          { key: 'RDS_PASSWORD', label: 'RDS Password', placeholder: 'Enter your RDS password' },
          { key: 'RDS_DB_NAME', label: 'RDS Database Name', placeholder: 'Enter your database name' },
        ];
      default:
        return [];
    }
  };

  const isFormValid = () => {
    const fields = getRequiredFields(selectedProvider);
    return fields.every(field => credentials[field.key]?.trim());
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>
            {selectedProvider ? 'Enter Cloud Credentials' : 'Select Cloud Provider'}
          </DialogTitle>
          <DialogDescription>
            {selectedProvider 
              ? 'Enter your cloud storage credentials to upload the generated data.'
              : 'Choose where to upload your generated data file.'}
          </DialogDescription>
        </DialogHeader>

        {!selectedProvider ? (
          <div className="grid grid-cols-1 gap-4 py-4">
            <Button
              variant="outline"
              className="h-24 flex flex-col gap-2 hover:border-primary hover:bg-primary/5"
              onClick={() => handleProviderSelect('aws')}
            >
              <Cloud className="h-8 w-8 text-orange-500" />
              <span className="font-semibold">AWS S3</span>
            </Button>
            
            <Button
              variant="outline"
              className="h-24 flex flex-col gap-2 hover:border-primary hover:bg-primary/5"
              onClick={() => handleProviderSelect('azure')}
            >
              <Cloud className="h-8 w-8 text-blue-500" />
              <span className="font-semibold">Azure Blob</span>
            </Button>
            
            <Button
              variant="outline"
              className="h-24 flex flex-col gap-2 hover:border-primary hover:bg-primary/5"
              onClick={() => handleProviderSelect('rds')}
            >
              <Database className="h-8 w-8 text-orange-600" />
              <span className="font-semibold">RDS</span>
            </Button>
          </div>
        ) : (
          <div className="space-y-4 py-4">
            {getRequiredFields(selectedProvider).map((field) => (
              <div key={field.key} className="space-y-2">
                <Label htmlFor={field.key}>{field.label}</Label>
                <Input
                  id={field.key}
                  type={field.key.toLowerCase().includes('password') || field.key.toLowerCase().includes('key') || field.key.toLowerCase().includes('secret') ? 'password' : 'text'}
                  placeholder={field.placeholder}
                  value={credentials[field.key] || ''}
                  onChange={(e) => handleCredentialChange(field.key, e.target.value)}
                />
              </div>
            ))}
          </div>
        )}

        <DialogFooter>
          {selectedProvider ? (
            <>
              <Button variant="outline" onClick={handleBack} disabled={isUploading}>
                Back
              </Button>
              <Button onClick={handleUpload} disabled={!isFormValid() || isUploading}>
                {isUploading ? 'Uploading...' : 'Save & Upload'}
              </Button>
            </>
          ) : (
            <Button variant="outline" onClick={handleCancel}>
              Cancel
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
