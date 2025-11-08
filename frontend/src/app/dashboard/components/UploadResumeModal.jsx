'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { FileUp, UploadCloud, Loader2, X } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';

export default function UploadResumeModal({ isOpen, onClose, onUploadSuccess }) {
  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const { toast } = useToast();

  if (!isOpen) return null;

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
    } else {
      toast({
        title: 'Invalid file type',
        description: 'Please upload a PDF file.',
        variant: 'destructive',
      });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      toast({
        title: 'No file selected',
        description: 'Please select a file to upload.',
        variant: 'destructive',
      });
      return;
    }

    setIsUploading(true);
    const formData = new FormData();
    formData.append('resume', file);

    try {
      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }

      const data = await response.json();
      
      toast({
        title: 'Success',
        description: 'Resume uploaded successfully!',
      });

      onUploadSuccess(data);
      onClose();

    } catch (error) {
      console.error('Upload error:', error);
      toast({
        title: 'Upload failed',
        description: 'There was an error uploading your resume. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-background rounded-lg p-6 w-full max-w-md relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-muted-foreground hover:text-foreground"
        >
          <X className="h-5 w-5" />
        </button>
        
        <div className="text-center mb-6">
          <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-primary/10 mb-3">
            <FileUp className="h-6 w-6 text-primary" />
          </div>
          <h2 className="text-xl font-bold">Upload Your Resume</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Upload your resume in PDF format for analysis.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div
            className={`flex flex-col items-center justify-center w-full h-48 border-2 border-dashed rounded-lg cursor-pointer bg-background hover:bg-accent/50 transition-colors ${
              file ? 'border-primary' : 'border-border'
            }`}
          >
            <input
              type="file"
              id="resume-upload"
              accept=".pdf"
              className="hidden"
              onChange={handleFileChange}
              disabled={isUploading}
            />
            <label
              htmlFor="resume-upload"
              className="flex flex-col items-center justify-center w-full h-full p-4 cursor-pointer"
            >
              {file ? (
                <div className="text-center">
                  <FileUp className="mx-auto h-8 w-8 text-primary mb-2" />
                  <p className="text-sm font-medium">{file.name}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {Math.round(file.size / 1024)} KB
                  </p>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="mt-2"
                    onClick={(e) => {
                      e.stopPropagation();
                      setFile(null);
                    }}
                    disabled={isUploading}
                  >
                    Change file
                  </Button>
                </div>
              ) : (
                <div className="text-center p-4">
                  <UploadCloud className="mx-auto h-8 w-8 text-muted-foreground mb-2" />
                  <p className="text-sm text-muted-foreground">
                    <span className="font-medium text-foreground">Click to upload</span> or drag and drop
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    PDF (max. 5MB)
                  </p>
                </div>
              )}
            </label>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isUploading}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={!file || isUploading}
            >
              {isUploading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Uploading...
                </>
              ) : (
                'Upload & Analyze'
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
