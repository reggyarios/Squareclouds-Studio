module.exports = {
  apps: [
    {
      name: "squareclouds-api",
      cwd: "/var/www/squareclouds-studio/backend",
      script: "venv/bin/python",
      args: "-m uvicorn main:app --host 127.0.0.1 --port 8000",
      interpreter: "none",
      autorestart: true,
      watch: false,
      max_memory_restart: "500M",
    },
    {
      name: "squareclouds-frontend",
      cwd: "/var/www/squareclouds-studio/frontend",
      script: "node_modules/.bin/next",
      args: "start -p 3000",
      interpreter: "none",
      autorestart: true,
      watch: false,
      env: { NODE_ENV: "production" },
    },
  ],
};
