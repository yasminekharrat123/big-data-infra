FROM node:24-slim

RUN apt-get update && apt-get install -y curl && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -m appuser

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Change ownership to non-root user
RUN chown -R appuser:appuser /app

# Run as non-root user
USER appuser

EXPOSE 3000
CMD ["npm", "start"]