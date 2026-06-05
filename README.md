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
