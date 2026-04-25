# Build stage
FROM node:20-alpine AS build
WORKDIR /app
ARG VITE_USER_SERVICE_PROXY_TARGET
ENV VITE_USER_SERVICE_PROXY_TARGET=$VITE_USER_SERVICE_PROXY_TARGET
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.mfe.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
