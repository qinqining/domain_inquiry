# 生成 + 只查本次新域名（不要用旧 json）

python [main.py](http://main.py) generate -b "钣金加工，出口欧美" --check

# 查全部 50 个（不要加 --limit 3，除非只想试 3 个）

python [main.py](http://main.py) generate -b "钣金加工，出口欧美" --check --limit 0

# 需要时再清空缓存

python [main.py](http://main.py) cache clear --reset-blocked



