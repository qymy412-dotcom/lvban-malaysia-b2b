# Lvban Furniture — Daily Malaysia B2B Outreach (GitHub Actions)

**完全托管于 GitHub Actions, 零本地操作**: 每天 MYT 09:00 自动触发, 从仓库 `sent_addresses.txt` 续跑去重, 通过 Gmail API 发送开发信, 跑完自动 commit dedup log。

## 架构

```
┌──────────────────────────────────────────────────────────┐
│  GitHub Actions (ubuntu-latest runner, 美国/欧洲机房)    │
│  ┌────────────────────────────────────────────────────┐  │
│  │  1. checkout repo (含 sent_addresses.txt 历史)    │  │
│  │  2. setup python 3.13                              │  │
│  │  3. python send_malaysia_tier1_via_refresh_token.py │ │
│  │       --start-now --auto-progress --interval 90    │  │
│  │  4. commit + push sent_addresses.txt + send_log    │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
                          │
                          ▼ HTTPS 443
                  ┌───────────────────┐
                  │  Google OAuth2    │
                  │  (refresh_token)  │
                  └────────┬──────────┘
                           ▼
                  ┌───────────────────┐
                  │  Gmail API send   │
                  │  qymy412@gmail.com│
                  └────────┬──────────┘
                           ▼
                  ┌───────────────────┐
                  │  马来西亚 B2B     │
                  │  家具经销商邮箱   │
                  └───────────────────┘
```

## 优势

| 项 | 沙箱 (旧) | GitHub Actions (新) |
|---|---|---|
| 网络到 Google | ❌ 9-05 起被封 (~13 天) | ✅ 美国/欧洲机房直通 |
| 续跑去重 | 内存/文件易丢 | 仓库 commit 持久化 |
| 触发可靠性 | 依赖沙箱在线 | GitHub SLA 99.9% |
| 维护成本 | 修脚本 + 重启 | 改代码 commit 即可 |
| 月度成本 | 0 | 0 (免费 2000min/月 够用) |

## 必需配置 (一次性, 楠总)

### 1. GitHub 仓库 Secrets (Settings → Secrets and variables → Actions → New repository secret)

| Secret 名称 | 值 (从哪里取) |
|---|---|
| `LVBAN_GMAIL_CLIENT_ID` | 你的 Google OAuth client_id (在 `.env` 文件) |
| `LVBAN_GMAIL_CLIENT_SECRET` | 你的 Google OAuth client_secret (在 `.env` 文件) |
| `LVBAN_GMAIL_REFRESH_TOKEN` | 你的 refresh_token (在 `.env` 文件, 142h 有效) |

### 2. (可选) 修改 `daily.yml` 的 cron 表达式

默认 MYT 09:00 (UTC 01:00)。如要换时间, 改:
```yaml
schedule:
  - cron: '0 1 * * *'   # UTC 01:00 = MYT 09:00
```

### 3. 手动测试 (首次配置必跑)

在 GitHub → Actions 标签页 → 左侧 `Daily Lvban Outreach` → 右侧 `Run workflow` → `Run`

预期看到:
- ✅ Setup Python
- ✅ 今日发件 (开始打 log)
- ✅ Commit dedup log

## 故障诊断

### "Run workflow" 后失败: 401 / 403 from oauth2.googleapis.com

- 检查 3 个 secrets 是否正确粘贴 (无空格/换行)
- 检查 `LVBAN_GMAIL_REFRESH_TOKEN` 是否过期 (Google 6 个月有效, 闲置可能被撤销)
- 重新走 OAuth flow 拿新 refresh_token, 更新 secret

### "Run workflow" 后成功但 0 封发件

- 检查 `sent_addresses.txt` 是否包含所有客户 (dedup 跳过了)
- 跑 `python send_malaysia_tier1_via_refresh_token.py --dry-run` 看队列

### 漏发 1 天后没自动补发

- 这是设计行为: GitHub Actions cron 触发器错过就跳过, 不补发
- 下一天继续按规则发

## 文件清单

| 文件 | 用途 |
|---|---|
| `send_malaysia_tier1_via_refresh_token.py` | 主发件脚本 (含 46 封 EMAILS 草稿) |
| `sent_addresses.txt` | 续跑去重 (commit 进 repo) |
| `send_log_v2.txt` | 每次发件日志 (commit 进 repo, 留痕) |
| `.github/workflows/daily.yml` | GitHub Actions workflow |
| `README.md` | 本文件 |

## 配额监控

- **GitHub Actions 免费**: 2000 分钟/月
- **当前用量**: 12 封/天 × 90s = 18 分钟/天 = 540 分钟/月 ✓ 安全
- **单 job 上限**: 60 分钟 (足够)
