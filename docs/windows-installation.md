# Windows 安装指南

本文档说明在 Windows 10/11 上部署与运行 `domain_inquiry` 的步骤。

---

## 前置条件

| 组件 | 要求 |
|------|------|
| Python | 3.10 及以上；安装时勾选 **Add python.exe to PATH** |
| Git | 用于克隆仓库（可选，亦可用 ZIP 下载） |
| 密钥 | 阿里云 RAM（`domain:QueryDomain`）、DeepSeek API Key |

---

## 部署步骤

### 1. 获取代码

```powershell
cd C:\tools
git clone <仓库地址> domain_inquiry
cd domain_inquiry
```

建议路径不含中文与空格。

### 2. 首次安装

在资源管理器中双击项目根目录下的 **`setup_windows.bat`**。

脚本将自动：

- 检测 Python 环境
- 创建虚拟环境 `.venv` 并执行 `pip install -r requirements.txt`
- 若不存在 `.env`，从 `.env.example` 复制
- 在用户桌面（含 OneDrive 桌面）创建 **`域名工具.bat`**

### 3. 配置环境变量

编辑项目根目录 **`.env`**，填写：

- `ALIYUN_ACCESS_KEY_ID` / `ALIYUN_ACCESS_KEY_SECRET`
- `DEEPSEEK_API_KEY`

密钥不得提交至 Git 远程仓库。

### 4. 启动应用

| 方式 | 说明 |
|------|------|
| 桌面 `域名工具.bat` | 日常推荐 |
| 项目内 `run.bat` | 等效启动交互模式 |
| 命令行 | `\.venv\Scripts\python.exe main.py run` |

---

## 维护说明

- **依赖更新**：修改 `requirements.txt` 后，重新执行 `setup_windows.bat`。
- **目录迁移**：项目路径变更后，须重新执行 `setup_windows.bat` 以更新桌面启动器中的路径。
- **新机器部署**：重复「克隆 → setup_windows.bat → 配置 .env」流程。

---

## 故障排除

| 现象 | 处理 |
|------|------|
| 双击闪退 | 先运行 `setup_windows.bat`；检查 `.env` 是否配置完整 |
| 找不到 Python | 重装 Python 并勾选 PATH，重启终端 |
| 无 output 目录内容 | 须成功完成至少一次完整任务；结果位于项目根 `output/` |

更多说明见项目根目录 [README.md](../README.md)。
