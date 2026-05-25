# 域名生成与阿里云可注册查询

先用 Python 本地跑通，再接入 Coze 等工作流。

## 说明

- **可注册查询**使用阿里云 `CheckDomain`（不是 `DescribeDomainInfo`）。后者用于查询**已注册**域名的详情。
- RAM 用户需具备 `domain:QueryDomain` 权限。
- `CheckDomain` 频率约 **10 QPS/账号**，脚本默认每次查询间隔 0.12 秒。

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

### 4. LLM 生成 + 查询（推荐 DeepSeek）

```env
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_MODEL=deepseek-chat
```

```powershell
python main.py generate -b "钣金加工，出口欧美" --check --limit 5
```

MiniMax Token Plan（`sk-cp-`）若报 `1004`，多为 Key/额度问题，与脚本无关；可改用 DeepSeek。

```powershell
python main.py generate -b "精密加工外贸独立站" --check --limit 5
```

默认会打印每个域名的查询进度，如 `[3/50] 正在查询: xxx.com`。

## 域名缓存与避让（减少重复查询）

| 文件 | 作用 |
|------|------|
| `data/domain_cache.json` | 自动写入：每次 API 查询结果；**14 天内**已确认「不可注册」的域名下次**跳过 API** |
| `data/blocked_domains.txt` | 人工维护：主观否决的域名；并注入 LLM prompt 避让 |

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
src/llm_client.py              # LLM 生成域名
main.py                        # CLI 入口
```

