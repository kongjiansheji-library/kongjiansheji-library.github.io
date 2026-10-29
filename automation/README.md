# 每日采集系统

这是普通程序和 GitHub Actions 定时任务，不调用 AI，不依赖聊天、电脑开机或人工每日触发。

## 调度与发布

- 每天 UTC 19:23，即北京时间次日03:23运行；GitHub排队可能延迟。
- 每次最多新增20张颜色贴图，每个已适配API最多10张。
- `workflow_dispatch` 支持手动触发验证。
- 从最新目录查找未入库素材，同时补充目录中缺失的旧素材；“本次新增”指新入本库，不代表源站当天发布。
- 采集结果提交到main，并在同一个任务中生成Pages部署产物。无需额外个人Token。
- 原站未更新时不会凭空产生新图片；公开索引未解析到素材时明确显示，不把首页或栏目计成素材。
- 已有图片不删除。图片空间达到850MB附近时停止新增，避免超过GitHub Pages容量；在状态中记录原因。

## 接入范围

`sources.json` 列出国内10站、国外5站，这是常用站清单，不是经第三方验证的流量排名。

原图自动下载已适配：ambientCG、Poly Haven的公开API。保存颜色图、缩略图、原站链接、授权和分类。分类使用关键词规则，颜色用图像估计，不使用AI；不确定的内容显示“待分类”。

其他13站每天检查公开页面和访问规则。能提取的详情链接记录为“公开素材线索”，仅指向原站；不能提取、禁止程序访问、需要登录和会员下载的内容，在状态页标明，不绕过、不假称已下载。不保存账号、Cookies或付费素材。CGBookcase目前仅适配公开详情索引。

## 运行与校验

```
python -m pip install 'Pillow>=11.3,<13'
python -m unittest discover -s automation -p 'test_*.py'
python automation/collect.py --max-new 20
python automation/build_site.py
```

新增数据在auto-data.json与auto-data.js；公开线索在discovery-data.json；各站结果在sync-status.json。页面“每日采集”可以查看。

若自动图片接口全部失败，仍保存错误报告并发布现有网站，任务最后标记失败。不会因为单个来源失败而清空图库。

公开仓库的GitHub定时任务在长期没有仓库活动时可能暂停；定期检查Actions是否仍启用。每日数据有更新时会提交运行记录。任务失败通知由GitHub账户通知设置控制。
