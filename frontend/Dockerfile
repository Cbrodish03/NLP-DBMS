FROM node:22-alpine

WORKDIR /app

COPY package.json .
COPY vite.config.js .
COPY index.html .
COPY src ./src

RUN npm install

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
