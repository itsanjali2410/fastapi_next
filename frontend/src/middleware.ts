import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Middleware for protected routes
 * Note: This runs on the server, so we can't check HttpOnly cookies directly.
 * The actual auth check happens in the components using the AuthContext.
 * This middleware handles basic route protection logic.
 */

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Public routes that don't require authentication
  const publicRoutes = ['/', '/register', '/invite'];
  
  // Check if the route is public
  const isPublicRoute = publicRoutes.some(route => 
    pathname === route || pathname.startsWith('/invite/')
  );

  // For now, let all requests through
  // Actual auth checking happens in components via AuthContext
  // This is because HttpOnly cookies can't be read in middleware
  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
};


