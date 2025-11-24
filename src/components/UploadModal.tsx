import { useState, MouseEvent } from "react";
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
import { useToast } from "@/components/ui/use-toast";
import { Cloud, Database } from "lucide-react";

type CloudVendor = 'aws' | 'azure' | 'gcp' | null;
type DatastoreType = 'aws-s3' | 'aws-rds' | 'azure-blob' | 'azure-sql' | 'gcp-storage' | 'gcp-bigquery' | null;

interface UploadModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onUpload: (provider: string, credentials: Record<string, string>) => void;
  isUploading: boolean;
}

export const UploadModal = ({ open, onOpenChange, onUpload, isUploading }: UploadModalProps) => {
  const [cloudVendor, setCloudVendor] = useState<CloudVendor>(null);
  const [selectedDatastore, setSelectedDatastore] = useState<DatastoreType>(null);
  const [credentials, setCredentials] = useState<Record<string, string>>({});
  const { toast } = useToast();

  const handleVendorSelect = (vendor: CloudVendor) => {
    setCloudVendor(vendor);
  };

  const handleDatastoreSelect = (datastore: DatastoreType) => {
    setSelectedDatastore(datastore);
    setCredentials({});
  };

  const handleBackToVendor = () => {
    setCloudVendor(null);
    setSelectedDatastore(null);
    setCredentials({});
  };

  const handleBackToDatastore = () => {
    setSelectedDatastore(null);
    setCredentials({});
  };

  const handleCredentialChange = (field: string, value: string) => {
    setCredentials(prev => ({ ...prev, [field]: value }));
  };

  const handleUpload = async (event?: MouseEvent<HTMLButtonElement>) => {
    event?.preventDefault();

    if (!selectedDatastore || isUploading) {
      return;
    }

    // Special handling for AWS S3 bucket name - persist before upload
    if (selectedDatastore === "aws-s3") {
      const bucketName = credentials["AWS_BUCKET_NAME"]?.trim();
      if (!bucketName) {
        toast({
          title: "Bucket name required",
          description: "Please enter a valid AWS S3 bucket name before uploading.",
          variant: "destructive",
        });
        return;
      }

      try {
        const response = await fetch(`${import.meta.env.VITE_BACKEND_API}/store-s3-bucketname`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ bucket_name: bucketName }),
        });

        if (!response.ok) {
          const errorMessage = await response.text().catch(() => "");
          throw new Error(errorMessage || "Failed to store AWS bucket name");
        }

        toast({
          title: "Bucket name saved",
          description: "AWS S3 bucket name stored successfully.",
        });
      } catch (error) {
        toast({
          title: "Error saving bucket name",
          description: error instanceof Error ? error.message : "Failed to store AWS bucket name. Please try again.",
          variant: "destructive",
        });
        return;
      }
    }

    await onUpload(selectedDatastore, credentials);
  };

  const handleCancel = () => {
    setCloudVendor(null);
    setSelectedDatastore(null);
    setCredentials({});
    onOpenChange(false);
  };

  const getRequiredFields = (datastore: DatastoreType) => {
    switch (datastore) {
      case 'aws-s3':
        return [
          { key: 'AWS_BUCKET_NAME', label: 'AWS Bucket Name', placeholder: 'Enter your S3 bucket name' },
        ];
      case 'aws-rds':
        return [
          { key: 'RDS_HOST', label: 'RDS Host', placeholder: 'Enter your RDS host' },
          { key: 'RDS_PORT', label: 'RDS Port', placeholder: 'e.g., 3306 or 5432' },
          { key: 'RDS_USERNAME', label: 'RDS Username', placeholder: 'Enter your RDS username' },
          { key: 'RDS_PASSWORD', label: 'RDS Password', placeholder: 'Enter your RDS password' },
          { key: 'RDS_DB_NAME', label: 'RDS Database Name', placeholder: 'Enter your database name' },
        ];
      case 'azure-blob':
        return [
          { key: 'AZURE_STORAGE_ACCOUNT_NAME', label: 'Azure Storage Account Name', placeholder: 'Enter your Azure storage account name' },
          { key: 'AZURE_STORAGE_ACCOUNT_KEY', label: 'Azure Storage Account Key', placeholder: 'Enter your Azure storage account key' },
          { key: 'AZURE_CONTAINER_NAME', label: 'Azure Container Name', placeholder: 'Enter your Azure container name' },
        ];
      case 'azure-sql':
        return [
          { key: 'AZURE_SQL_SERVER', label: 'Azure SQL Server', placeholder: 'Enter your Azure SQL server name' },
          { key: 'AZURE_SQL_DATABASE', label: 'Azure SQL Database', placeholder: 'Enter your database name' },
          { key: 'AZURE_SQL_USERNAME', label: 'Azure SQL Username', placeholder: 'Enter your username' },
          { key: 'AZURE_SQL_PASSWORD', label: 'Azure SQL Password', placeholder: 'Enter your password' },
        ];
      case 'gcp-storage':
        return [
          { key: 'GCP_PROJECT_ID', label: 'GCP Project ID', placeholder: 'Enter your GCP project ID' },
          { key: 'GCP_BUCKET_NAME', label: 'GCP Bucket Name', placeholder: 'Enter your Cloud Storage bucket name' },
          { key: 'GCP_SERVICE_ACCOUNT_KEY', label: 'GCP Service Account Key (JSON)', placeholder: 'Paste your service account key JSON' },
        ];
      case 'gcp-bigquery':
        return [
          { key: 'GCP_PROJECT_ID', label: 'GCP Project ID', placeholder: 'Enter your GCP project ID' },
          { key: 'GCP_DATASET_ID', label: 'BigQuery Dataset ID', placeholder: 'Enter your dataset ID' },
          { key: 'GCP_TABLE_ID', label: 'BigQuery Table ID', placeholder: 'Enter your table ID' },
          { key: 'GCP_SERVICE_ACCOUNT_KEY', label: 'GCP Service Account Key (JSON)', placeholder: 'Paste your service account key JSON' },
        ];
      default:
        return [];
    }
  };

  const getDatastoresForVendor = (vendor: CloudVendor) => {
    switch (vendor) {
      case 'aws':
        return [
          { id: 'aws-s3' as DatastoreType, label: 'AWS S3', icon: Cloud, color: 'text-orange-500' },
          { id: 'aws-rds' as DatastoreType, label: 'AWS RDS', icon: Database, color: 'text-orange-600' },
        ];
      case 'azure':
        return [
          { id: 'azure-blob' as DatastoreType, label: 'Azure Blob Storage', icon: Cloud, color: 'text-blue-500' },
          { id: 'azure-sql' as DatastoreType, label: 'Azure SQL Database', icon: Database, color: 'text-blue-600' },
        ];
      case 'gcp':
        return [
          { id: 'gcp-storage' as DatastoreType, label: 'GCP Cloud Storage', icon: Cloud, color: 'text-yellow-500' },
          { id: 'gcp-bigquery' as DatastoreType, label: 'GCP BigQuery', icon: Database, color: 'text-yellow-600' },
        ];
      default:
        return [];
    }
  };

  const isFormValid = () => {
    const fields = getRequiredFields(selectedDatastore);
    return fields.every(field => credentials[field.key]?.trim());
  };

  const getModalTitle = () => {
    if (selectedDatastore) return 'Enter Cloud Credentials';
    if (cloudVendor) return 'Select Datastore';
    return 'Select Cloud Provider';
  };

  const getModalDescription = () => {
    if (selectedDatastore) return 'Enter your cloud storage credentials to upload the generated data.';
    if (cloudVendor) return 'Choose the datastore type for your generated data.';
    return 'Choose your cloud provider to get started.';
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>{getModalTitle()}</DialogTitle>
          <DialogDescription>{getModalDescription()}</DialogDescription>
        </DialogHeader>

        {!cloudVendor ? (
          <div className="grid grid-cols-1 gap-4 py-4">
            <Button
              type="button"
              variant="outline"
              className="h-24 flex flex-col gap-2 hover:border-primary hover:bg-primary/5"
              onClick={() => handleVendorSelect('aws')}
            >
              <Cloud className="h-8 w-8 text-orange-500" />
              <span className="font-semibold">AWS</span>
            </Button>
            
            <Button
              type="button"
              variant="outline"
              className="h-24 flex flex-col gap-2 hover:border-primary hover:bg-primary/5"
              onClick={() => handleVendorSelect('azure')}
            >
              <Cloud className="h-8 w-8 text-blue-500" />
              <span className="font-semibold">Azure</span>
            </Button>
            
            <Button
              type="button"
              variant="outline"
              className="h-24 flex flex-col gap-2 hover:border-primary hover:bg-primary/5"
              onClick={() => handleVendorSelect('gcp')}
            >
              <Cloud className="h-8 w-8 text-yellow-500" />
              <span className="font-semibold">GCP</span>
            </Button>
          </div>
        ) : !selectedDatastore ? (
          <div className="grid grid-cols-1 gap-4 py-4">
            {getDatastoresForVendor(cloudVendor).map((datastore) => {
              const Icon = datastore.icon;
              return (
                <Button
                  type="button"
                  key={datastore.id}
                  variant="outline"
                  className="h-24 flex flex-col gap-2 hover:border-primary hover:bg-primary/5"
                  onClick={() => handleDatastoreSelect(datastore.id)}
                >
                  <Icon className={`h-8 w-8 ${datastore.color}`} />
                  <span className="font-semibold">{datastore.label}</span>
                </Button>
              );
            })}
          </div>
        ) : (
          <div className="space-y-4 py-4">
            {getRequiredFields(selectedDatastore).map((field) => (
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
          {selectedDatastore ? (
            <>
              <Button
                type="button"
                variant="outline"
                onClick={handleBackToDatastore}
                disabled={isUploading}
              >
                Back
              </Button>
              <Button
                type="button"
                onClick={handleUpload}
                disabled={!isFormValid() || isUploading}
              >
                {isUploading ? 'Uploading...' : 'Save & Upload'}
              </Button>
            </>
          ) : cloudVendor ? (
            <>
              <Button
                type="button"
                variant="outline"
                onClick={handleBackToVendor}
                disabled={isUploading}
              >
                Back
              </Button>
            </>
          ) : (
            <Button type="button" variant="outline" onClick={handleCancel}>
              Cancel
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
