FROM node:14

WORKDIR /app

COPY ./frontend /app/frontend
COPY ./backend /app/backend

# Install frontend dependencies
WORKDIR /app/frontend
RUN npm install
RUN npm run build

# Install backend dependencies
WORKDIR /app/backend
RUN npm install

# Serve backend and frontend
EXPOSE 8001
CMD ["sh", "-c", "(cd /app/backend && node server.js) & (cd /app/frontend && serve -s build) && wait"]