# Dockerfile.frontend
FROM node:20-alpine

WORKDIR /app

# Install dependencies first for better caching
COPY package.json package-lock.json ./
RUN npm install

# Copy source code
COPY . .

# Expose port
EXPOSE 5173

# Start development server
CMD ["npm", "run", "dev"]
