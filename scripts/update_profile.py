"""Build an organization profile from public repositories and approved summaries."""
import collections
import datetime as dt
import html
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
ORG = "hxtx-workspace"
BASE = f"https://github.com/{ORG}/.github/blob/main"
RAW = f"https://raw.githubusercontent.com/{ORG}/.github/main/profile/assets"
UTC = dt.timezone.utc


def api(path):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "hxtx-public-profile", "X-GitHub-Api-Version": "2022-11-28"}
    if os.environ.get("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    req = urllib.request.Request("https://api.github.com/" + path, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def pages(path):
    separator = "&" if "?" in path else "?"
    for page in range(1, 1001):
        batch = api(f"{path}{separator}per_page=100&page={page}")
        if not isinstance(batch, list):
            raise ValueError("Expected a paginated list")
        yield from batch
        if len(batch) < 100:
            return
    raise ValueError("Pagination limit reached; refusing partial statistics")


def is_public(repo):
    # Fail closed when privacy fields are absent or disagree.
    return repo.get("private") is False and repo.get("visibility") == "public" and repo.get("owner", {}).get("login", "").lower() == ORG


def validate(config):
    categories = {c["id"] for c in config["categories"]}
    seen = set()
    for project in config["projects"]:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", project["repo"]):
            raise ValueError("Invalid repository slug")
        if project["repo"].lower() in seen or project["category"] not in categories:
            raise ValueError("Duplicate project or unknown category")
        seen.add(project["repo"].lower())
        if project["access"] not in ("public", "private"):
            raise ValueError("Access must be public or private")


def collect(now):
    repos = [r for r in pages(f"orgs/{ORG}/repos?type=public") if is_public(r) and r["name"] != ".github"]
    days = [(now.date() - dt.timedelta(days=27-i)).isoformat() for i in range(28)]
    data = {"repos": repos, "stars": 0, "forks": 0, "issues": 0, "prs": 0,
            "commits": dict.fromkeys(days, 0), "languages": collections.Counter(), "latest": []}
    since = days[0] + "T00:00:00Z"
    for repo in repos:
        path = f"repos/{ORG}/{urllib.parse.quote(repo['name'], safe='')}"
        # Recheck immediately before collecting detail; a newly private repo is skipped.
        if not is_public(api(path)):
            raise ValueError("Repository visibility changed; keeping the previous profile")
        data["stars"] += repo["stargazers_count"]
        data["forks"] += repo["forks_count"]
        for issue in pages(path + "/issues?state=open"):
            data["prs" if "pull_request" in issue else "issues"] += 1
        data["languages"].update(api(path + "/languages"))
        if repo.get("size", 0) > 0:
            for commit in pages(path + "/commits?since=" + since):
                day = commit["commit"]["committer"]["date"][:10]
                if day in data["commits"]:
                    data["commits"][day] += 1
        if repo.get("pushed_at") and repo.get("size", 0) > 0:
            data["latest"].append((repo["pushed_at"], repo["name"]))
    return data


def svg_start(width, height, title):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">',
            f'<title>{html.escape(title)}</title>',
            '<style>text{font-family:Segoe UI,Arial,sans-serif;fill:#dce7f5}.muted{fill:#91a6c2}.accent{fill:#6cb6ff}</style>',
            f'<rect width="{width}" height="{height}" rx="18" fill="#101c2e"/>']


def text(x, y, value, size=14, css=""):
    return f'<text x="{x}" y="{y}" font-size="{size}" class="{css}">{html.escape(str(value))}</text>'


def hero():
    s = svg_start(960, 230, "hxtx-workspace · Build. Explore. Share.")
    s += ['<path d="M680 0L480 230M820 0L620 230M960 0L760 230" stroke="#203b5b" stroke-width="1"/>',
          '<circle cx="830" cy="110" r="58" fill="none" stroke="#375f87" stroke-width="2"/>',
          '<circle cx="830" cy="110" r="35" fill="none" stroke="#6cb6ff" stroke-width="2"/>',
          text(40, 44, "INDEPENDENT DEVELOPMENT WORKSPACE", 12, "accent"),
          text(40, 107, "hxtx-workspace", 46),
          text(42, 151, "Build. Explore. Share.", 22, "muted"),
          text(42, 197, "iOS  /  WEB  /  AI  /  TOOLS", 12, "accent"), '</svg>']
    return "\n".join(s)


def dashboard(data):
    s = svg_start(960, 160, "Public project statistics")
    s.append(text(28, 31, "PUBLIC PROJECTS / 公开项目数据", 14, "muted"))
    metrics = [("项目", len(data["repos"])), ("Stars", data["stars"]), ("Forks", data["forks"]), ("开放 Issues", data["issues"]), ("开放 PRs", data["prs"]), ("28 天提交", sum(data["commits"].values()))]
    for i, (label, value) in enumerate(metrics):
        x = 28 + i*157
        s += [text(x, 90, value, 34, "accent"), text(x, 126, label, 13, "muted")]
    return "\n".join(s + ['</svg>'])


def activity(data):
    s = svg_start(960, 240, "Public default-branch commits over 28 UTC calendar days")
    s += [text(28, 34, "ACTIVITY / 近 28 天公开提交", 16), text(28, 59, "UTC · 默认分支 · 不含主页仓库及私有项目", 12, "muted")]
    values = list(data["commits"].values())
    maximum = max(max(values), 1)
    for i, value in enumerate(values):
        height = max(3, round(value/maximum*104))
        s.append(f'<rect x="{30+i*32}" y="{185-height}" width="20" height="{height}" rx="4" fill="{"#6cb6ff" if value else "#273b53"}"><title>{list(data["commits"])[i]}: {value}</title></rect>')
    s += [text(28, 213, list(data["commits"])[0], 12, "muted"), text(830, 213, list(data["commits"])[-1], 12, "muted")]
    if not any(values):
        s.append(text(290, 120, "暂无公开提交数据 / No public commits", 17, "muted"))
    return "\n".join(s + ['</svg>'])


def languages(data):
    s = svg_start(960, 170, "Public repository language distribution by bytes")
    s.append(text(28, 34, "LANGUAGES / 公开代码语言分布", 16))
    total = sum(data["languages"].values())
    if not total:
        s.append(text(28, 99, "暂无公开代码语言数据 / No public language data", 17, "muted"))
    else:
        items = data["languages"].most_common(5)
        remainder = total - sum(v for _, v in items)
        if remainder:
            items.append(("Other", remainder))
        colors = ["#6cb6ff", "#59d0c8", "#b6a0ff", "#ffcf76", "#f398b5", "#70869f"]
        x = 28
        for i, (name, count) in enumerate(items):
            width = 904*count/total
            s += [f'<rect x="{x:.2f}" y="65" width="{width:.2f}" height="19" fill="{colors[i]}"/>', text(28+i*151, 120, f"{name} {count/total:.0%}", 12)]
            x += width
        s.append(text(28, 149, "按 GitHub languages API 返回的字节数统计", 11, "muted"))
    return "\n".join(s + ['</svg>'])


def safe(value):
    return html.escape(str(value)).replace("|", "&#124;").replace("\n", " ")


def render(config, data, now):
    public = {r["name"] for r in data["repos"]}
    visible = [p for p in config["projects"] if (p["access"] == "public" and p["repo"] in public) or (p["access"] == "private" and p.get("publish_summary") is True)]
    active = [c for c in config["categories"] if any(p["category"] == c["id"] for p in visible)]
    lines = [f'![hxtx-workspace]({RAW}/hero.svg)', '',
             '<p align="center">个人项目与开发实践 · 从想法到工具，持续探索与积累。</p>', '',
             '<p align="center"><a href="https://github.com/orgs/hxtx-workspace/repositories">项目仓库</a> · <a href="https://github.com/maxueli">维护者 maxueli</a> · <a href="https://github.com/hxtx-workspace/.github/blob/main/README.md">新增项目指南</a></p>', '',
             f'[![主页自动更新](https://github.com/{ORG}/.github/actions/workflows/update-profile.yml/badge.svg)](https://github.com/{ORG}/.github/actions/workflows/update-profile.yml)', '',
             '## 项目导航', '',
             ' · '.join(f'[{safe(c["title"])}](#category-{c["id"]})' for c in active), '']
    for category in active:
        lines += [f'<a id="category-{category["id"]}"></a>', '', f'### {category["title"]}', '', '| 项目 | 简介 | 访问方式 |', '| :--- | :--- | :--- |']
        for p in visible:
            if p["category"] != category["id"]:
                continue
            link = f'https://github.com/{ORG}/{p["repo"]}'
            access = '🔒 私有 · 仅授权成员可访问' if p["access"] == 'private' else '🌐 公开'
            lines.append(f'| [{safe(p["name"])}]({link}) | {safe(p["description"])} | {access} |')
        lines.append('')
    lines += ['> 私有项目仅展示经授权的名称和简介；链接只对有权限的成员开放，不展示代码、提交记录或活动统计。', '',
              '## 公开项目看板', '', f'![公开项目数据]({RAW}/stats.svg)', '',
              f'公开项目 **{len(data["repos"])}** · Stars **{data["stars"]}** · Forks **{data["forks"]}** · 开放 Issues **{data["issues"]}** · 开放 PRs **{data["prs"]}**', '',
              'Stars 表示 GitHub 收藏支持，不是独立点赞指标。统计仅包含组织下公开项目，排除 `.github` 主页仓库；私有项目不参与统计。', '',
              f'![公开项目活跃度]({RAW}/activity.svg)', '', f'![公开代码语言分布]({RAW}/languages.svg)', '',
              '### 最近公开项目更新', '']
    if data['latest']:
        for date, name in sorted(data['latest'], reverse=True)[:5]:
            lines.append(f'- [{safe(name)}](https://github.com/{ORG}/{name}) · 最近推送 {date[:10]}（UTC）')
    else:
        lines.append('暂无公开项目更新。私有项目的开发活动不会出现在这里。')
    lines += ['', '## 访问记录', '',
              '<img src="https://count.getloli.com/@hxtx-workspace-profile?theme=morden-num" alt="主页计数器" height="90" />', '',
              '第三方计数器从接入后累计图片请求，受 GitHub 图片缓存、重复访问与机器人影响；不代表独立访客数，也不是 GitHub 官方浏览量。', '',
              '## 新项目如何加入', '',
              '在 [`projects.json`](https://github.com/hxtx-workspace/.github/blob/main/projects.json) 增加一条项目配置，提交后会自动更新主页。仅显示已有项目的分类。', '',
              '命名：`ios-tweak-<插件名>` · `web-<项目名>` · `ai-<项目名>` · `tool-<工具名>`。全部小写，多词用短横线；版本使用 Git 标签。', '',
              '---', '',
              f'数据更新：**{now.astimezone(dt.timezone(dt.timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")}（北京时间）**。每天约 09:23 自动刷新，也可手动运行；GitHub 调度可能延迟。', '',
              '数据来源：GitHub REST API（公开仓库） · [Moe Counter](https://github.com/journey-ad/Moe-Counter)（访问图片计数）', '']
    return '\n'.join(lines)


def main():
    config = json.loads((ROOT / 'projects.json').read_text(encoding='utf-8'))
    validate(config)
    now = dt.datetime.now(UTC)
    data = collect(now)
    # Complete all reads and rendering before replacing any generated output.
    outputs = {'README.md': render(config, data, now), 'assets/hero.svg': hero(),
               'assets/stats.svg': dashboard(data), 'assets/activity.svg': activity(data), 'assets/languages.svg': languages(data)}
    for path, content in outputs.items():
        target = ROOT / 'profile' / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
    print(f'Generated profile: {len(data["repos"])} public projects; no private repository API calls.')


if __name__ == '__main__':
    main()
