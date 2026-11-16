# 提交规范（所有 AI / 协作者必读）

> 本项目的每一次 git 提交都必须能让下一个人**仅凭提交记录**就知道：谁改的、改了什么、为什么改、影响范围。
> 违反此规范的提交会被要求重写。

---

## 1. 必须署名（谁改的）

### 1.1 设置身份

每个接手的 AI / 环境在首次提交前，**必须**设置自己的身份：

```bash
cd /root/workspace/submix
git config user.name "<你的标识>"
git config user.email "<你的标识>@local"
```

推荐命名（便于追溯）：

| 场景 | user.name | user.email |
|---|---|---|
| DSH 手机端（小女仆 / Little Code Sauce） | `dsh-littlecodesauce` | `littlecodesauce@dsh.local` |
| 其他 AI agent | `<模型名>-agent` 例如 `gemini-agent`、`claude-agent` | `<模型名>@agent.local` |
| 用户本人手动改 | `hutaoze177` | `hutaoze177@users.noreply.github.com` |

### 1.2 禁止使用全局默认

不要依赖 `dsh <dsh@local>` 这种无标识的默认值 —— 无法区分是哪个 AI 改的。
**每次提交前确认：**

```bash
git config user.name   # 必须输出你自己的标识
```

---

## 2. 提交信息格式（改了什么 + 为什么）

### 2.1 结构

```
<type>: <一句话标题，不超过 50 字>

<正文：为什么改、改了什么、影响范围>

- 具体改动点 1
- 具体改动点 2

影响: <对产物 / 客户端 / 账号的具体影响>
验证: <怎么验证的>
```

### 2.2 type 取值

| type | 用途 |
|---|---|
| `feat` | 新功能（新增参数、新能力） |
| `fix` | 修 bug / 修错误行为 |
| `rules` | 仅改动规则模板 `rules/ai-meta.json` |
| `ci` | 改动 `.github/workflows/` |
| `docs` | 仅文档 |
| `refactor` | 重构，行为不变 |
| `revert` | 回退某次提交（须在正文注明被回退的 commit hash） |
| `chore` | 杂项（忽略规则、依赖等） |

### 2.3 正文必须包含的三要素

1. **原因**：为什么要改（用户要求 / 实测发现 / 上游变化）
2. **改动范围**：动了哪些文件、哪些函数、哪些规则
3. **影响**：对订阅产物、客户端行为、账号 IP 的具体影响

### 2.4 推荐附加两行

- `影响:` 具体影响（例如"落地默认节点从 A 换成 B"）
- `验证:` 验证方式（例如"mihomo -t 通过 / CI run #12 success / 实测 api.anthropic.com 405"）

---

## 3. 好例子 vs 坏例子

### ✅ 好例子

```
fix: 落地 pin 改为按 IP 锁定

上游虾蹬订阅 2026-11-15 整体重编号，「US-静态23」这个名字
从 203.0.113.1 变成了 203.0.113.2，导致 --pin-land 按名字
锁定失效，主人账号出口 IP 被意外更换。

- submix.py: --pin-land 支持匹配 IP（原本也能，但 CI 传参写的是节点名）
- workflow: PIN 改从 secrets.PIN_LAND 读取，值为 203.0.113.1
- 新增 secret PIN_LAND

影响: 落地默认节点锁定回 203.0.113.1，主人 Claude/Muse 账号 IP 不变
验证: mihomo -t 通过；CI run #10 success；产物第 0 位确认是 203.0.113.1
```

### ❌ 坏例子

```
update
```

```
fix bug
```

```
改了点东西
```

**问题**：完全看不出改了什么、为什么改、谁改的、有什么影响。

---

## 4. 多 AI 协作约定

### 4.1 提交前必须先拉取

```bash
B64=$(python3 -c "
import base64;t=open('/root/.gh_token').read().strip()
print(base64.b64encode(('x-access-token:'+t).encode()).decode())")
git -c http.extraheader="Authorization: Basic $B64" fetch https://github.com/hutaoze177/submix.git main
git merge --ff-only FETCH_HEAD
```

**禁止 force push**，会覆盖其他 AI 的提交。

### 4.2 改动冲突时的原则

1. 先看 `git log` 最近 5 条，理解别人在做什么
2. 如果发现别人的改动有疑问，**先问主人**，不要直接覆盖
3. 同一文件被两人改时，优先保留后者的语义意图，手动合并

### 4.3 订阅产物仓库（`hutaoze177/sub`）的提交

CI 自动推送的提交信息格式固定：

```
update subscription via submix
```

手动推送时必须写清原因：

```
<type>: <改了什么>

影响: <订阅内容变化的实际影响>
```

---

## 5. 必须写进提交记录的重大变更

以下情况**必须**在提交正文里明确写出，否则后续排查会非常困难：

| 场景 | 必须记录的内容 |
|---|---|
| 改了 DNS 段任何字段 | 改了哪个字段、为什么（DNS 是命根子，换错会让节点全挂） |
| 改了 `--pin-land` 的值 | 旧值 → 新值，以及原因（会影响账号 IP） |
| 增删落地节点 | 数量变化、增删的是哪些账号 |
| 改动规则归属 | 哪个域名从哪条链路挪到哪条，为什么 |
| 改动 workflow | 是否影响 secrets、是否影响调度时间 |
| 回退提交 | 被回退的 commit hash、回退原因 |

---

## 6. 当前身份登记表

| 标识 | 说明 | 首次提交 |
|---|---|---|
| `dsh <dsh@local>` | DSH 手机端默认（**应改为具名**） | — |
| `hutaoze177` | 用户本人 / GitHub 网页操作 | — |

> 接手的 AI 请在此表追加自己的一行，注明标识与首次提交的 commit hash。

---

## 7. 快速检查清单

提交前逐项确认：

- [ ] `git config user.name` 是我自己的标识，不是默认值
- [ ] 提交信息是 `<type>: <标题>` 格式
- [ ] 正文写了**为什么改**
- [ ] 正文列了**具体改动点**
- [ ] 写了 `影响:` 和 `验证:`
- [ ] 已 `fetch` 并合并远端最新
- [ ] 改了 DNS / pin / 规则归属的，已在正文特别说明
