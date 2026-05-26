# output 目录说明

本目录**不会**通过 Git 同步任务结果（已在 `.gitignore` 中忽略）。

每次在本机成功跑完「生成 → 自检 → 阿里云」后，会自动新建子文件夹，例如：

```
output/20260526_143022_钣金加工/
  01_candidates.json
  02_reviews.json
  03_availability.json
  report.md / report.json
  （可选步骤4）04~07、final_list.md
```

最近一次任务的报告副本在：`output/latest/report.md`

若跑完后这里没有新文件夹，请看终端是否出现：

`[输出] 已保存至 D:\...\output\...`
