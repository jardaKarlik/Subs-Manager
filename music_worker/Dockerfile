FROM node:22-slim

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install all dependencies (dev included for type declarations), build, then prune
RUN npm ci

# Copy source code
COPY . .

# Build TypeScript
RUN npm run build && npm prune --omit=dev

# Start worker
CMD ["node", "dist/worker.js"]