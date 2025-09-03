# Use Node.js Alpine image
FROM node:18-alpine AS build

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy source code and build
COPY . .
RUN npm run build

# # Serve with a lightweight web server
# FROM node:18-alpine AS production
# WORKDIR /app

# # Install `serve` globally
# RUN npm install -g serve

# # Copy only the built output from the build stage
# COPY --from=build /app/dist ./dist

EXPOSE 3000

# Serve the app
# CMD ["serve", "-s", "dist", "-l", "5173"]
# Run dev server in container
CMD ["npm", "start"]