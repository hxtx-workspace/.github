# hxtx-workspace 组织主页维护

组织首页读取 [`profile/README.md`](profile/README.md)。该文件和 `profile/assets/` 均由脚本生成，不要直接编辑。

## 新增项目

编辑 [`projects.json`](projects.json)，在 `projects` 数组增加一条配置：

```json
{
  "name": "项目显示名",
  "repo": "tool-example",
  "category": "tools",
  "description": "一句话介绍项目用途",
  "access": "public"
}
```

分类：`ios`（iOS 插件）、`web`（Web 与低代码）、`ai`（AI 应用）、`tools`（工具与脚本）。空分类自动隐藏。新增分类时，在 `categories` 数组补充 `id`、`title` 和建议前缀。

公开项目必须实际存在于组织公开仓库列表中才会显示。公开数据看板统计所有公开项目，不仅是配置中的精选项目；排除 `.github`。

**本仓库全部内容公开，配置和提交历史也公开。不要将未获准公开的私有项目名称或简介写入配置。** 只有获得披露授权的私有项目才可添加 `"access": "private", "publish_summary": true`；展示内容来自手工配置，不查询其代码、语言、提交、Issues 或 PR。AutoSwipe 已获准披露名称与简介。

## 更新机制与口径

- 每天 01:23 UTC（北京时间 09:23）计划运行；GitHub 可能延迟调度，长期无活动的公开仓库定时任务可能被平台暂停。
- 修改配置、生成脚本、测试或工作流后自动运行；也可在 Actions → Update organization profile → Run workflow 手动触发。
- 工作流仅使用此主页仓库的自动 `GITHUB_TOKEN`，不需要个人 PAT，不申请其他私有仓库访问权。
- 公开仓库查询使用 `type=public`，并再次检查 `private=false`、`visibility=public`、组织归属；明细采集前复核可见性。
- Stars、Forks 为公开项目合计；开放 Issues 排除 PR；开放 PR 单独计数。
- 活跃度是最近 28 个 UTC 日历日（含当天）的默认分支提交次数，按提交者日期统计，不是贡献者人数或开发时长；不同仓库中的相同提交分别计数。
- 语言分布按公开仓库 languages API 的字节数汇总，不代表技术熟练度。
- 最近更新展示公开非空仓库的 `pushed_at`；不包含主页机器人的提交。
- 没有公开项目时如实显示 0 和空状态，不填充模拟活动。
- API 报错时任务失败，不提交部分结果，保留上一版并通过更新时间及 Actions 状态提示是否过期。
- GitHub Profile Views Counter 是第三方图片请求计数，不是独立访客统计，受缓存和机器人影响；外部图片服务可能不可用。GitHub 代理通常负责图片加载，计数器只使用公开组织标识。
- 项目改为私有后，下次刷新不再统计；已经公开过的历史 Git 提交和统计不会自动消失。

## 命名

| 分类 | 仓库名 |
| --- | --- |
| iOS 插件 | `ios-tweak-<插件名>` |
| Web 与低代码 | `web-<项目名>` |
| AI 应用 | `ai-<项目名>` |
| 工具与脚本 | `tool-<工具名>` |

全部小写，多词用短横线连接；一个独立项目一个仓库；版本通过 `v1.0.0` 等 Git 标签管理。

## 本地验证

Python 3.12，标准库，无第三方依赖：

```sh
python -m unittest discover -s tests -v
python scripts/update_profile.py
```

生成器可从环境变量 `GH_TOKEN` 读取凭据以避免匿名限流。不要将凭据写入文件或提交到仓库。自动流程只更新 `profile/README.md` 和 `profile/assets/`。
