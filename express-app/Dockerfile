FROM node:24-slim

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