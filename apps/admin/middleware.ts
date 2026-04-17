import { createJanuaMiddleware } from '@janua/nextjs/middleware';

export default createJanuaMiddleware({
    jwtSecret: process.env.JANUA_SECRET_KEY || '',
    publicRoutes: ['/sign-in', '/sign-in/*', '/api/auth/*', '/api/v1/auth/*', '/api/health'],
    redirectUrl: '/sign-in',
});

export const config = {
    matcher: [
        '/((?!_next/static|_next/image|favicon.ico|icon.svg|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico)$).*)',
    ],
};
