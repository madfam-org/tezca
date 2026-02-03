# apps/admin/Dockerfile
FROM node:20-alpine

WORKDIR /app

# Copy package files
# We assume the build context is the project root
COPY apps/admin/package.json apps/admin/package-lock.json* ./

# Install dependencies (use install since no lockfile potentially)
RUN npm install

# Copy source code
COPY apps/admin .

# Build the app
RUN npm run build

# Expose port
EXPOSE 3001

# Start the app
CMD ["npm", "start"]
