# Deploy to production: K8s setup, CI/CD pipeline, rollback


# Deploy to production: K8s setup, CI/CD pipeline, rollback


/cuongdn_workspace_company/robot-lesson-agent$ uvicorn app.server:app --reload --port 8002 --env-
file=/home/ubuntu/cuongdn_workspace_company/robot-lesson-agent/deploy/.env

```bash
uvicorn app.server:app \
  --reload \
  --reload-dir /home/ubuntu/cuongdn_workspace_company/robot-lesson-agent/app \
  --port 8002 \
  --env-file /home/ubuntu/cuongdn_workspace_company/robot-lesson-agent/deploy/.env
```

- Chỉ reload khi file trong app/ thay đổi. Mặc định watch toàn bộ project.
```bash
uvicorn app.server:app --reload --port 8002 --env-file=/home/ubuntu/cuongdn_workspace_company/robot-lesson-agent/deploy/.env --reload-dir app
```

- Hoặc muốn exclude thư mục cụ thể (thay vì whitelist):
```bash
uvicorn app.server:app --reload --port 8002 --env-file=... --reload-dir . --exclude-dir tests --exclude-dir .git
```