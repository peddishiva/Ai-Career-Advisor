'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Home, FileText, User, LogIn, Upload as UploadIcon } from 'lucide-react';

export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="border-b bg-white">
      <div className="container mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center space-x-8">
          <Link href="/" className="flex items-center space-x-2">
            <FileText className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold">CareerAI</span>
          </Link>
          
          <div className="hidden md:flex items-center space-x-6">
            <Link 
              href="/dashboard" 
              className={`flex items-center space-x-2 ${pathname === '/dashboard' ? 'text-primary' : 'text-muted-foreground hover:text-foreground'}`}
            >
              <FileText className="h-4 w-4" />
              <span>Dashboard</span>
            </Link>
            <Link 
              href="/upload" 
              className={`flex items-center space-x-2 ${pathname === '/upload' ? 'text-primary' : 'text-muted-foreground hover:text-foreground'}`}
            >
              <UploadIcon className="h-4 w-4" />
              <span>Upload Resume</span>
            </Link>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <Link href="/login">
            <Button variant="outline" size="sm">
              <LogIn className="h-4 w-4 mr-2" />
              Login
            </Button>
          </Link>
        </div>
      </div>
    </nav>
  );
}
