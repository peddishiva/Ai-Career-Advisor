import { NextResponse } from 'next/server';

export function middleware(request) {
  // Check if the user is authenticated
  const isAuthenticated = request.cookies.get('auth-token')?.value;
  
  // If user is not authenticated and trying to access protected routes
  if (!isAuthenticated && 
      (request.nextUrl.pathname.startsWith('/dashboard') ||
       request.nextUrl.pathname === '/')) {
    // Redirect to login page
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('from', request.nextUrl.pathname);
    return NextResponse.redirect(loginUrl);
  }

  // If user is authenticated and trying to access login/signup, redirect to dashboard
  if (isAuthenticated && 
      (request.nextUrl.pathname === '/login' || 
       request.nextUrl.pathname === '/signup')) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    '/',
    '/dashboard/:path*',
    '/login',
    '/signup'
  ],
};
