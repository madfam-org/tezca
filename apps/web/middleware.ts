import { createJanuaMiddleware } from '@janua/nextjs/middleware';

export default createJanuaMiddleware({
  jwtSecret: process.env.JANUA_SECRET_KEY || '',
  publicRoutes: ['/*'], // Everything is public — Tezca is an open-access site
});

export const config = {
  matcher: [
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
  ],
};
