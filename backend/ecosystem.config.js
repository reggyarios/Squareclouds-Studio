module.exports = {
  apps: [
    {
      name: "backend",
      script: "/www/server/pyporject_evn/backend_venv/bin/uvicorn",
      args: "main:app --host 127.0.0.1 --port 8000",
      cwd: "/www/wwwroot/squarecloudsmc.com/backend",
      interpreter: "none",
      autorestart: true,
      watch: false,
    },
  ],
};
