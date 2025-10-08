# --- Stage 1: Build Vite app ---
FROM public.ecr.aws/docker/library/node:20-slim as build

WORKDIR /app
COPY package*.json ./

# Install dependencies needed for native modules
RUN apt-get update && apt-get install -y \
    python3 \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies with clean slate and fix esbuild issues
RUN npm cache clean --force && \
    rm -rf node_modules package-lock.json && \
    npm install && \
    npm uninstall esbuild @esbuild/linux-x64 @esbuild/darwin-arm64 || true && \
    npm install esbuild@0.25.6 --save-dev

COPY . .

# Platform-specific binaries are automatically handled by npm during installation
# No manual intervention needed for Rollup and esbuild

RUN npm run build

# --- Stage 2: Serve with Nginx ---
FROM nginx:stable-alpine

# Create a non-root user to run nginx
RUN addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup

# Clear default static content
RUN rm -rf /usr/share/nginx/html/*

# Copy Vite build output
COPY --from=build /app/dist /usr/share/nginx/html

# Optional: custom Nginx config (for SPA routing)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Change ownership of nginx directories to the non-root user
RUN chown -R appuser:appgroup /var/cache/nginx /var/log/nginx /etc/nginx/conf.d /usr/share/nginx/html && \
    touch /var/run/nginx.pid && \
    chown appuser:appgroup /var/run/nginx.pid

# Switch to non-root user
USER appuser

# Add health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:80/ || exit 1

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
