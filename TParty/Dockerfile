# TParty React Frontend Dockerfile
# Optimized for development with hot reload

FROM node:18-alpine as base

WORKDIR /app

# Install dependencies for better caching
COPY package*.json ./
RUN npm ci --only=production && npm cache clean --force

# Development stage
FROM base as development

# Install all dependencies including dev dependencies
RUN npm ci

# Copy source code
COPY . .

# Expose port
EXPOSE 3000

# Set environment for development
ENV NODE_ENV=development
ENV REACT_APP_API_URL=http://localhost:8000

# Start development server with hot reload
CMD ["npm", "start"]

# Production build stage
FROM base as build

# Install all dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the app
RUN npm run build

# Production stage
FROM nginx:alpine as production

# Copy build files
COPY --from=build /app/build /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
