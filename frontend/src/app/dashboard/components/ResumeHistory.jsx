'use client';

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { FileText, Download, Eye, Trash2 } from 'lucide-react';
import { format } from 'date-fns';

export default function ResumeHistory({ resumes = [], showAll = false }) {
  // If showAll is false, only show the first 3 items
  const displayedResumes = showAll ? resumes : resumes.slice(0, 3);

  if (resumes.length === 0) {
    return (
      <div className="text-center py-6">
        <FileText className="mx-auto h-12 w-12 text-muted-foreground" />
        <h3 className="mt-2 text-sm font-medium">No resumes uploaded yet</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          Upload your first resume to get started with the analysis.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-md border
    
    ">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Resume Name</TableHead>
            <TableHead>Upload Date</TableHead>
            <TableHead className="text-right">Score</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {displayedResumes.map((resume) => (
            <TableRow key={resume.id}>
              <TableCell className="font-medium">
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  {resume.name}
                </div>
              </TableCell>
              <TableCell>
                {format(new Date(resume.date), 'MMM d, yyyy')}
              </TableCell>
              <TableCell className="text-right">
                <div className="flex items-center justify-end gap-2">
                  <div className="relative">
                    <div className="h-2 w-16 rounded-full bg-gray-200">
                      <div 
                        className={`h-full rounded-full ${
                          resume.score >= 80 ? 'bg-green-500' : 
                          resume.score >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                        }`}
                        style={{ width: `${resume.score}%` }}
                      />
                    </div>
                  </div>
                  <span className="font-medium">{resume.score}</span>
                </div>
              </TableCell>
              <TableCell className="text-right">
                <div className="flex justify-end gap-2">
                  <Button variant="ghost" size="icon" className="h-8 w-8">
                    <Eye className="h-4 w-4" />
                    <span className="sr-only">View</span>
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8">
                    <Download className="h-4 w-4" />
                    <span className="sr-only">Download</span>
                  </Button>
                  <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive hover:text-destructive">
                    <Trash2 className="h-4 w-4" />
                    <span className="sr-only">Delete</span>
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      
      {!showAll && resumes.length > 3 && (
        <div className="flex items-center justify-end border-t px-4 py-3">
          <Button variant="ghost" className="text-sm">
            View all {resumes.length} resumes
          </Button>
        </div>
      )}
    </div>
  );
}
