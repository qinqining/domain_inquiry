# Windows 同事安装说明

## 你需要准备什么

| 项目 | 谁负责 | 说明 |
|------|--------|------|
| Git 仓库 | 你 push，同事 clone | 代码用 Git 同步 |
| Python 3.10+ | **同事电脑安装一次** | 不能靠 Git 带过去，需本机安装 |
| `.env` 密钥 | **不要 push** | 阿里云 + DeepSeek 的 Key，单独发给同事或各自申请 |
| 桌面「域名工具」 | `setup_windows.bat` 自动生成 | 双击即可启动 |

---

## 你这边（维护人）

1. 确认 `.env` 已在 `.gitignore` 里（已配置），**不要**把密钥提交到 Git。
2. 推送代码：

```powershell
cd d:\domain_inquiry
git add .
git commit -m "Windows 安装脚本与桌面启动"
git push
```

3. 把 **仓库地址** 和 **`.env` 填写说明**（或脱敏后的模板）私发给同事。  
   Key 建议走企业微信/邮件，不要写在群里明文。

---

## 同事那边（只需做一次）

### 1. 安装 Git（若无）

https://git-scm.com/download/win  

安装后打开 **PowerShell** 或 **命令提示符**。

### 2. 安装 Python（必做）

https://www.python.org/downloads/  

- 选 **3.10 或更高**
- 安装界面勾选：**Add python.exe to PATH**
- 装完后新开一个终端，输入 `python --version` 应能看到版本号

### 3. 克隆项目

```powershell
cd C:\Users\你的用户名\Documents
git clone <你的仓库地址> domain_inquiry
cd domain_inquiry
```

建议路径**不要有中文空格**，例如 `C:\tools\domain_inquiry`。

### 4. 首次安装（只需一次）

在资源管理器中进入 `domain_inquiry` 文件夹，**双击**：

```
setup_windows.bat
```

脚本会：

- 创建 `.venv` 虚拟环境
- `pip install` 安装依赖
- 从 `.env.example` 复制 `.env`（若还没有）
- 在**桌面**生成 **`域名工具.bat`**

按提示用记事本填写 `.env` 里的阿里云、DeepSeek 密钥。

### 5. 日常使用

双击桌面 **`域名工具.bat`** 即可，无需再输入 `python` 命令。

---

## 常见问题

**双击桌面图标闪退？**  
先运行一次项目里的 `setup_windows.bat`；或检查 `.env` 是否填好。

**移动了项目文件夹？**  
在新位置再双击一次 `setup_windows.bat`，会重新生成桌面启动器。

**换电脑？**  
重新：装 Python → `git clone` → `setup_windows.bat` → 配置 `.env`。

**Mac 同事？**  
仍可用仓库里的 `run.sh`（需 `chmod +x`），与 Windows 桌面方式无关。

---

## 文件说明

| 文件 | 作用 |
|------|------|
| `setup_windows.bat` | 首次安装 + 创建桌面启动器 |
| `run.bat` | 在项目目录内启动（开发用） |
| 桌面 `域名工具.bat` | 同事日常双击入口 |
| `.env` | 本机密钥，**不提交 Git** |
