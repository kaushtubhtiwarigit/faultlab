FROM node:18-alpine

# Install tc and iptables for fault injection
RUN apk add --no-cache iproute2 iptables

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3000

CMD ["npm", "start"]
