# domain_inquiry

面向精密加工外贸独立站的 **.com 短域名** 生成与可注册性查询工具。基于 DeepSeek 完成候选生成与质量自检，通过阿里云 `CheckDomain` 核验注册状态，结果落盘至本地 `output/` 目录。

---

## 功能概述

- **LLM 生成**：按当次业务方向生成约 50 个候选域名（可虚构造词，4–6 字母为主）。
- **LLM 自检**：从可读性、可发音性、可记忆性、独特性等维度评分并筛选。
- **可注册查询**：对自检通过域名调用阿里云 `CheckDomain`（非 `DescribeDomainInfo`）。
- **可选终稿变体**：对首轮可注册域名生成修改建议与 coined 变体，再次查询；变体不重复自检。
- **本地归档**：每轮任务生成 JSON / Markdown 报告；`output/latest/` 保留最近一次副本。
- **缓存与避让**：不可注册结果缓存 14 天以减少 API 调用；人工否决列表注入生成 prompt。

---

## 处理流水线

单条流水线（非独立多轮任务）：


| 步骤    | 说明                                                              |
| ----- | --------------------------------------------------------------- |
| 1     | LLM 生成候选（`prompts/domain_generator.txt`）                        |
| 2     | LLM 自检（`prompts/domain_reviewer.txt`，默认 `REVIEW_MIN_SCORE=7`）   |
| 3     | 阿里云 `CheckDomain`                                               |
| 4（可选） | 修改建议 + 变体生成（`prompts/domain_refiner.txt`）→ 变体直接查阿里云 → 合并最终 list |


**业务方向**：每次运行通过 `-b` 或交互输入指定当次方向（例如「钣金加工」「自动化设备配件」）。公司级背景由 `context/company.md`、`context/naming_prefs.md` 注入，与当次方向组合使用。

**步骤 4 说明**：变体阶段不进行第二轮 LLM 自检；若首轮变体均不可注册，将自动重试一轮更虚构的造词。最终 list 中「变体可注册」条目优先于「首轮可注册」，并含读音与释义。

---

## 环境要求


| 组件       | 版本 / 说明                                      |
| -------- | -------------------------------------------- |
| Python   | 3.10 及以上                                     |
| 操作系统     | Windows 10/11（推荐）；macOS / Linux 可使用 `run.sh` |
| 阿里云 RAM  | 权限 `domain:QueryDomain`                      |
| DeepSeek | API Key（`deepseek-chat` 等）                   |
| 网络       | 可访问 `api.deepseek.com` 与阿里云域名 API            |


`CheckDomain` 账户级频率约 **10 QPS**；程序默认每次查询间隔 **0.12 秒**。

---

## 安装

### Windows（推荐）

1. 安装 [Python 3.10+](https://www.python.org/downloads/)，安装时勾选 **Add python.exe to PATH**。
2. 克隆仓库至本机（路径建议不含中文与空格），例如 `C:\tools\domain_inquiry`。
3. 进入项目根目录，双击执行 `**setup_windows.bat`**（仅首次）：
  - 创建 `.venv` 并安装 `requirements.txt`
  - 从 `.env.example` 复制 `.env`（若不存在）
  - 在桌面生成 `**域名工具.bat**` 快捷启动脚本
4. 编辑项目根目录 `**.env**`，填入密钥（勿提交版本库）。
5. 日常使用：双击桌面 `**域名工具.bat**`，或项目内 `**run.bat**`。

若项目目录迁移，需重新执行 `setup_windows.bat` 以更新桌面启动器路径。

详细步骤见 [docs/windows-installation.md](docs/windows-installation.md)。

### 手动安装（开发与跨平台）

```powershell
cd <项目根目录>
python -m venv .venv
.\.venv\Scripts\activate          # Windows
# source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
copy .env.example .env             # Windows
# cp .env.example .env            # macOS / Linux
```

macOS / Linux 交互入口：

```bash
chmod +x run.sh
./run.sh
```

---

## 配置

在项目根目录创建 `.env`（参考 `.env.example`）：


| 变量                         | 说明                            |
| -------------------------- | ----------------------------- |
| `ALIYUN_ACCESS_KEY_ID`     | 阿里云 AccessKey ID              |
| `ALIYUN_ACCESS_KEY_SECRET` | 阿里云 AccessKey Secret          |
| `ALIYUN_REGION`            | 区域，默认 `cn-hangzhou`           |
| `DEEPSEEK_API_KEY`         | DeepSeek API Key              |
| `DEEPSEEK_BASE_URL`        | 默认 `https://api.deepseek.com` |
| `DEEPSEEK_MODEL`           | 默认 `deepseek-chat`            |
| `REVIEW_MIN_SCORE`         | 自检四维最低均分门槛，默认 `7`             |


**安全**：`.env` 已列入 `.gitignore`，不得将密钥提交至远程仓库。

**公司上下文**（可选编辑）：

- `context/company.md` — 公司与产业背景
- `context/naming_prefs.md` — 命名长度、音节、禁用词根等偏好

---

## 使用方式

### 交互模式

```powershell
python main.py run
```

无子命令时默认进入交互模式。流程概要：

1. 输入当次业务/行业方向
2. 执行步骤 1–3，输出首轮可注册 list（含释义）
3. 可选执行步骤 4（修改建议 + 变体 + 再查）
4. 输出最终 list（含释义）
5. 询问是否继续下一轮（可更换业务方向）
6. 会话结束前汇总本次最终 list

### 命令行

```powershell
# 完整流水线（生成 → 自检 → 阿里云 → 写入 output/）
python main.py generate -b "钣金加工" --check

# 同上，并自动执行步骤 4
python main.py generate -b "钣金加工" --check --variants

# 仅生成候选（不查阿里云）
python main.py generate -b "钣金加工"

# 解析 LLM 输出的 JSON 域名列表
python main.py parse -i data\sample_domains.json

# 查询指定域名可注册性
python main.py check -d example.com another.com
python main.py check -i domains.json --json

# 清空查询缓存
python main.py cache clear
python main.py cache clear --reset-blocked
```

### 常用参数


| 参数                   | 适用命令                | 说明                  |
| -------------------- | ------------------- | ------------------- |
| `--check`            | `generate`          | 自检通过后查阿里云并写 output  |
| `--variants`         | `generate`          | 自动执行步骤 4            |
| `--no-output`        | `generate`          | 与 `--check` 联用时跳过写盘 |
| `--no-cache`         | `check`, `generate` | 禁用查询缓存              |
| `--cache-ttl-days N` | `check`, `generate` | 不可注册缓存天数，默认 14      |
| `--limit N`          | `check`, `generate` | 最多查询前 N 个域名         |
| `--dry-run`          | `check`, `generate` | 不调用阿里云、不写缓存         |
| `--quiet`            | `check`, `generate` | 关闭逐条查询日志            |
| `--json`             | `check`, `generate` | JSON 格式输出           |


---

## 输出目录

任务结果写入 **项目根目录下的 `output/`**，**不纳入 Git 同步**（见 `.gitignore`）。首次成功执行任务后自动创建带时间戳的子目录。

```
output/
  20260526_143022_钣金加工/
    meta.json
    01_candidates.json      # 全部候选
    02_reviews.json         # 自检结果
    03_availability.json    # 阿里云查询
    report.md / report.json   # 可读与结构化报告
    04_variant_suggestions.json   # 步骤 4（可选）
    05_variants.json
    06_variant_availability.json
    07_final_list.json
    final_list.md             # 最终推荐（含释义）
  latest/                     # 最近一次任务副本
    report.md
    report.json
    final_list.md
    task_path.txt
```

终端在步骤 3 完成后应出现：

```text
[输出] 已保存至 <项目根>\output\<时间戳>_<业务摘要>
[输出] 最新副本 output/latest/report.md
```

若目录为空，请确认任务已执行至步骤 3 且无异常中断，并在**项目根目录**下查看 `output/`（非仓库外的其他路径）。

说明文件见 [output/README.md](output/README.md)。

---

## 缓存与避让


| 文件                         | 作用                                      |
| -------------------------- | --------------------------------------- |
| `data/domain_cache.json`   | 自动记录 API 查询结果；14 天内已确认**不可注册**的域名跳过 API |
| `data/blocked_domains.txt` | 人工维护的否决列表，并注入 LLM 生成 prompt             |


规则摘要：

- **可注册**结果写入缓存，但**不**用于跳过后续 API（避免抢注误判）。
- **可注册**域名**不**进入 LLM 避让列表。
- `generate` 时避让列表上限约 80 条（blocked + 最近不可注册缓存）。
- `check -i <文件>` 仅查询文件内域名；`generate --check` 查询**本次新生成**的列表。

```powershell
python main.py check -i data\sample_domains.json --no-cache
python main.py cache clear --reset-blocked
```

---

## 项目结构

```
domain_inquiry/
├── main.py                 # CLI 入口
├── run.bat / run.sh        # 快捷启动
├── setup_windows.bat       # Windows 首次安装与桌面启动器
├── requirements.txt
├── .env.example
├── context/
│   ├── company.md          # 公司背景
│   └── naming_prefs.md     # 命名偏好
├── prompts/
│   ├── domain_generator.txt
│   ├── domain_reviewer.txt
│   └── domain_refiner.txt
├── data/
│   ├── blocked_domains.txt
│   ├── sample_domains.json
│   └── domain_cache.json   # 运行时生成，已 gitignore
├── src/
│   ├── pipeline.py         # 主流水线
│   ├── llm_client.py       # 生成
│   ├── domain_reviewer.py  # 自检
│   ├── domain_refiner.py   # 变体
│   ├── aliyun_checker.py   # CheckDomain
│   ├── domain_cache.py     # 缓存与避让
│   ├── output_writer.py    # 报告落盘
│   ├── interactive.py      # 交互模式
│   └── ...
├── output/                 # 任务结果（本机生成）
└── docs/
    └── windows-installation.md
```

---

## 常见问题


| 现象                   | 处理建议                                             |
| -------------------- | ------------------------------------------------ |
| 提示未找到 Python         | 安装 Python 3.10+ 并勾选 PATH，或执行 `setup_windows.bat` |
| 阿里云 403 / 5000       | 检查 RAM 是否具备 `domain:QueryDomain`                 |
| DeepSeek 鉴权失败        | 检查 `.env` 中 `DEEPSEEK_API_KEY`                   |
| clone 后无 `output` 内容 | 属正常；需本地执行任务后才会生成                                 |
| 避让列表始终显示 80          | 为 prompt 注入上限，不代表本次未写缓存                          |
| 变体全部不可注册             | 短 .com 竞争激烈；可保留首轮可注册域名或更换业务方向重跑                  |
| 移动项目目录后无法启动          | 重新运行 `setup_windows.bat`                         |


## 参考

- 阿里云域名 API：[CheckDomain](https://help.aliyun.com/document_detail/42875.html)
- 品牌名生成相关研究：[Generating Appealing Brand Names (arXiv:1706.09335)](https://arxiv.org/abs/1706.09335)

