FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

RUN npm run build

EXPOSE 3000

# Start with a fallback for PORT, although Grid will provide it.
CMD ["sh", "-c", "npm start -- -p ${PORT:-3000}"]
