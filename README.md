# 域名生成与阿里云可注册查询

先用 Python 本地跑通，再接入 Coze 等工作流。

## 说明

- **可注册查询**使用阿里云 `CheckDomain`（不是 `DescribeDomainInfo`）。后者用于查询**已注册**域名的详情。
- RAM 用户需具备 `domain:QueryDomain` 权限。
- `CheckDomain` 频率约 **10 QPS/账号**，脚本默认每次查询间隔 0.12 秒。

## 同事使用（双击即可）

| 系统 | 操作 |
|------|------|
| Windows | 双击 `run.bat`（需已 `pip install -r requirements.txt` 并配置 `.env`） |
| Mac | 终端执行一次 `chmod +x run.sh`，之后双击或在终端 `./run.sh` |

交互提示：输入行业范围 → 步骤1~3 → 可选步骤4 → 最终 list → **询问是否继续生成** → 退出前汇总本次会话 list。

开发者在 Windows 上检查 `run.sh` 语法：`powershell -File scripts/test-run-sh.ps1`（需 Git Bash），或在 WSL 里 `bash -n run.sh`。

## 流水线（一条，非两轮）

| 步骤 | 说明 |
|------|------|
| 1 | LLM 生成候选 |
| 2 | LLM 自检（读音/寓意/四维分） |
| 3 | 阿里云 CheckDomain |
| 4（可选） | 对可注册域名：LLM 修改建议 + 修复变体 → **直接**阿里云再查 → 最终 list |

步骤4 **不再**跑第二轮 LLM 自检；变体优先排在最终 list 前面。

## 快速开始

```powershell
cd d:\domain_inquiry
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# 编辑 .env 填入 AccessKey
```

### 1. 不连阿里云，验证解析

```powershell
python main.py parse -i data\sample_domains.json
python main.py check -i data\sample_domains.json --dry-run
```

### 2. 连接阿里云查询

```powershell
python main.py check -i data\sample_domains.json
python main.py check -d metfab.com google.com
python main.py check -i data\sample_domains.json --limit 3 --json
```

### 3. 从 LLM 文本（或 Coze 输出）查询

将 Coze/LLM 返回的 JSON 保存为 `domains.txt`，或管道传入：

```powershell
Get-Content domains.txt | python main.py check -i -
```

### 4. 完整流程（生成 → 自检 → 查可注册 → output）

```powershell
python main.py generate -b "钣金加工，出口欧美" --check
```

加 `--variants` 在同一次任务里自动进入步骤4：

```powershell
python main.py generate -b "钣金加工，出口欧美" --check --variants
```

或双击 `run.bat` / Mac 上 `./run.sh`（步骤4 在交互里可选确认）。

每次任务写入 `output/20260525_143022_钣金加工/`，并同步副本到 `output/latest/report.md`：

| 文件 | 内容 |
|------|------|
| `01_candidates.json` | LLM 生成的全部候选 |
| `02_reviews.json` | LLM 自检（读音、寓意、四维分） |
| `03_availability.json` | 阿里云查询结果 |
| `04_variant_suggestions.json` | 步骤4：修改建议（可选） |
| `05_variants.json` | 步骤4：变体候选（可选） |
| `06_variant_availability.json` | 步骤4：变体阿里云结果（可选） |
| `07_final_list.json` / `final_list.md` | 最终推荐 list |
| `report.md` | 可读报告（推荐列表含释义） |
| `report.json` | 结构化结果 |

默认会打印每个域名的查询进度，如 `[3/50] 正在查询: xxx.com`。

## 公司上下文

编辑 `context/company.md`（产业、工艺、材料、质量体系）与 `context/naming_prefs.md`（命名偏好）。生成域名时会自动注入 prompt，无需每次重复粘贴。

## 域名缓存与避让（减少重复查询）


| 文件                         | 作用                                                 |
| -------------------------- | -------------------------------------------------- |
| `data/domain_cache.json`   | 自动写入：每次 API 查询结果；**14 天内**已确认「不可注册」的域名下次**跳过 API** |
| `data/blocked_domains.txt` | 人工维护：主观否决的域名；并注入 LLM prompt 避让                     |


```powershell
# 默认使用缓存
python main.py check -i data\user_domains.json

# 强制全部实时查阿里云
python main.py check -i data\user_domains.json --no-cache

# 调整不可注册缓存天数
python main.py check -d metfab.com --cache-ttl-days 30
```

`generate` 时会读取避让列表写入 prompt（`{{avoid_domains}}`），减少 LLM 重复造已占用的名。**可注册**结果不会用于跳过 API（防止被抢注）。

一键清空缓存（查错旧名单时用）：

```powershell
python main.py cache clear --reset-blocked
```

**注意**：`check -i data\user_domains.json` 只会查该文件里的域名；`generate --check` 才查本次 LLM 新生成的列表。旧版含 fab/mfg 的名单勿再使用该文件。

## 目录结构

```
prompts/domain_generator.txt   # LLM 提示词（{{business}}、{{avoid_domains}}）
data/blocked_domains.txt       # 人工否决列表
data/domain_cache.json         # 查询缓存（自动生成，已 gitignore）
data/sample_domains.json       # 测试用域名列表
src/domain_cache.py            # 缓存与避让逻辑
src/domain_parser.py           # 解析 LLM JSON
src/aliyun_checker.py          # CheckDomain 封装
src/pipeline.py              # 生成→自检→查询→输出
src/domain_reviewer.py       # LLM 二层自检
src/output_writer.py         # output/ 按任务存档
src/deepseek_client.py       # DeepSeek API
prompts/domain_reviewer.txt  # 自检 prompt
main.py                        # CLI 入口
```

