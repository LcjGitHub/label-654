# 待办事项应用 (Todo App)

一个使用 Python Flask + React + SQLite 开发的现代化待办事项管理应用。

## 功能特性

- ✅ **任务管理**: 添加、编辑、删除任务
- ✅ **标记完成**: 点击复选框标记任务完成/未完成
- ✅ **任务筛选**: 按全部/待完成/已完成筛选任务
- ✅ **批量清除**: 一键清除所有已完成任务
- ✅ **现代化界面**: 渐变紫色主题，流畅动画效果
- ✅ **响应式设计**: 完美适配桌面端和移动端

## 技术栈

### 后端
- **Python 3.8+**
- **Flask 3.0** - Web 框架
- **Flask-CORS** - 跨域支持
- **SQLite** - 轻量级数据库

### 前端
- **React 18** - UI 框架
- **React Scripts** - 构建工具

## 项目结构

```
label-654/
├── backend/                    # Flask 后端
│   ├── __init__.py
│   ├── app.py                 # 主应用文件（包含 API 和数据库）
│   ├── requirements.txt       # Python 依赖
│   └── todo.db                # SQLite 数据库（运行后自动创建）
└── frontend/                   # React 前端
    ├── package.json           # Node 依赖
    ├── public/
    │   └── index.html         # HTML 入口
    └── src/
        ├── index.js           # React 入口
        ├── App.js             # 主应用组件
        ├── App.css            # 主样式
        ├── index.css          # 全局样式
        ├── services/
        │   └── api.js         # API 服务层
        └── components/
            ├── AddTask.js     # 添加任务组件
            ├── TaskList.js    # 任务列表组件
            └── TaskItem.js    # 任务项组件
```

## API 接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/tasks` | 获取所有任务列表 |
| GET | `/api/tasks/<id>` | 获取单个任务详情 |
| POST | `/api/tasks` | 创建新任务 |
| PUT | `/api/tasks/<id>` | 更新任务 |
| PUT | `/api/tasks/<id>/toggle` | 切换任务完成状态 |
| DELETE | `/api/tasks/<id>` | 删除任务 |

### 请求示例

**创建任务:**
```bash
curl -X POST http://localhost:5000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "学习 Flask", "description": "完成 Todo 应用开发"}'
```

**获取所有任务:**
```bash
curl http://localhost:5000/api/tasks
```

**切换任务状态:**
```bash
curl -X PUT http://localhost:5000/api/tasks/1/toggle
```

## 快速开始

### 1. 启动后端服务

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 启动服务
python app.py
```

后端服务将在 `http://localhost:5000` 启动。

### 2. 启动前端服务

**新打开一个终端窗口:**

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm start
```

前端应用将在 `http://localhost:3000` 自动打开。

## 使用说明

1. **添加任务**: 点击顶部的「添加新任务...」输入框，填写标题和描述后点击「添加任务」
2. **标记完成**: 点击任务左侧的复选框即可标记为完成
3. **编辑任务**: 点击「编辑」按钮或双击任务内容进行编辑
4. **删除任务**: 点击「删除」按钮移除任务
5. **筛选任务**: 使用顶部的标签切换查看全部/待完成/已完成任务
6. **清除已完成**: 点击底部的「清除已完成任务」一键清理

## 数据库说明

- 数据库文件 `todo.db` 会在首次启动后端时自动创建
- 任务表包含以下字段：
  - `id` - 主键，自增
  - `title` - 任务标题（必填）
  - `description` - 任务描述（可选）
  - `completed` - 完成状态（0/1）
  - `created_at` - 创建时间
  - `updated_at` - 更新时间

## 开发说明

- 后端启用了调试模式，代码修改后会自动重启
- 前端配置了代理，API 请求会自动转发到 `http://localhost:5000`
- CORS 已配置，允许跨域请求

## 常见问题

**Q: 前端无法连接后端？**
A: 请确保后端服务已在 5000 端口启动，并检查防火墙设置。

**Q: 数据库错误？**
A: 删除 `backend/todo.db` 文件，重新启动后端会自动创建新数据库。

**Q: npm install 失败？**
A: 尝试使用国内镜像：`npm config set registry https://registry.npmmirror.com`

---

## Docker 容器化部署

本项目支持使用 Docker Compose 进行一键部署，包含前端 Nginx 服务、后端 Flask 应用以及 PostgreSQL 数据库。

### 架构说明

- **前端 (frontend)**: React 应用通过 Nginx 提供静态文件服务，同时配置反向代理将 `/api/` 请求转发到后端服务
- **后端 (backend)**: Flask 应用使用 Gunicorn 作为 WSGI 服务器运行
- **数据库 (db)**: PostgreSQL 15，数据通过 Docker Volume 持久化存储

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+

### 快速部署步骤

#### 1. 配置环境变量

复制 `.env.example` 为 `.env` 并根据需要修改配置：

```bash
cp .env.example .env
```

环境变量说明：

| 变量名 | 说明 | 默认值 | 必填 |
|--------|------|--------|------|
| `SECRET_KEY` | JWT 签名密钥（生产环境必须修改） | 无 | **是** |
| `DB_USER` | PostgreSQL 用户名 | `postgres` | 否 |
| `DB_PASSWORD` | PostgreSQL 密码 | `postgres` | 否 |
| `DB_NAME` | PostgreSQL 数据库名 | `todo_app` | 否 |

> **安全提示**: 生产环境请务必使用强随机密钥替换 `SECRET_KEY`！可以使用 `openssl rand -hex 32` 生成随机密钥。

#### 2. 一键启动所有服务

```bash
docker-compose up -d --build
```

该命令会：
1. 构建前端和后端的 Docker 镜像
2. 启动 PostgreSQL 数据库容器
3. 等待数据库健康检查通过后启动后端
4. 启动前端 Nginx 服务并反向代理到后端

#### 3. 访问应用

服务启动后，在浏览器中访问：

```
http://localhost
```

各服务端口映射：

| 服务 | 容器端口 | 主机端口 | 说明 |
|------|----------|----------|------|
| 前端 (Nginx) | 80 | 80 | Web 界面访问 |
| 后端 (Flask) | 5000 | 5000 | API 服务（也可通过 Nginx 代理访问） |
| 数据库 (PostgreSQL) | 5432 | 5432 | 数据库（仅限本地调试用） |

### 常用管理命令

#### 查看服务状态

```bash
docker-compose ps
```

#### 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 只查看后端日志
docker-compose logs -f backend

# 只查看数据库日志
docker-compose logs -f db
```

#### 停止服务

```bash
docker-compose down
```

#### 停止服务并清除所有数据（⚠️ 危险操作）

```bash
docker-compose down -v
```

> **注意**: `-v` 参数会删除所有 Docker Volume，包括 PostgreSQL 数据和上传的附件！

#### 重新构建并启动

当代码有更新时：

```bash
docker-compose up -d --build
```

### 数据持久化

所有数据通过 Docker Volume 持久化存储，即使容器删除也不会丢失：

| Volume 名称 | 用途 |
|-------------|------|
| `postgres_data` | PostgreSQL 数据库文件 |
| `backend_uploads` | 任务附件上传目录 |

查看 Volume：

```bash
docker volume ls | grep label-654
```

备份数据库：

```bash
docker exec todo-postgres pg_dump -U postgres todo_app > backup_$(date +%Y%m%d).sql
```

恢复数据库：

```bash
docker exec -i todo-postgres psql -U postgres todo_app < backup_20240101.sql
```

### Nginx 反向代理配置

前端 Nginx 已配置以下反向代理规则：

- `/` - 提供 React 前端静态文件（SPA 路由支持）
- `/api/` - 反向代理到后端 Flask 服务 `http://backend:5000/api/`
- `/uploads/` - 反向代理到后端附件文件服务

配置文件位置：[frontend/nginx.conf](file:///f:/Lcj/0602/label-654/frontend/nginx.conf)

### 生产环境部署建议

1. **配置 HTTPS**: 在 Nginx 前添加 SSL 终止（推荐使用 Traefik 或 Nginx Proxy Manager）
2. **加强密钥**: 使用强随机密钥替换所有默认密码
3. **数据库端口**: 生产环境建议移除 `docker-compose.yml` 中 PostgreSQL 的端口映射，不对外暴露
4. **资源限制**: 根据服务器配置为各容器添加 CPU 和内存限制
5. **日志轮转**: 配置 Docker 日志驱动避免日志文件无限增长
6. **定期备份**: 设置定时任务自动备份数据库 Volume

### 故障排查

**Q: 后端服务启动失败，日志显示数据库连接失败？**
A: PostgreSQL 容器启动需要时间，后端服务配置了自动等待重试（最多 30 次，每次间隔 2 秒）。如果多次尝试仍失败，请检查数据库密码配置是否正确。

**Q: 前端页面无法加载或 API 请求返回 404？**
A: 请确认 Nginx 容器是否正常运行：`docker-compose logs frontend`。检查前端 API 基础 URL 是否使用相对路径 `/api`。

**Q: 上传附件功能不可用？**
A: 请检查 `backend_uploads` Volume 是否存在：`docker volume ls`，以及后端容器对 `/app/uploads` 目录的权限。

**Q: 如何切换回 SQLite 开发模式？**
A: 直接在本地运行而不使用 Docker 时，后端默认使用 SQLite。只需要在环境变量中不设置 `DB_TYPE=postgresql` 即可。
