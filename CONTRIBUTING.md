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

## 1.5 必须标明设备（在哪台机器改的）

多设备、多 AI 环境下，同一个仓库可能从不同机器提交。
**每次提交必须带 `Device:` 行**，标明这次改动来自哪台设备。

### 自动机制（已配置）

本仓库已安装 `prepare-commit-msg` hook，**每次提交会自动追加**：

```
Device: mi8padpro
```

新环境首次使用前先装 hook：

```bash
cd /root/workspace/submix
./scripts/install-hooks.sh
```

### 设备标签来源

标签由 `.devtag` 文件定义，探测方式：

| 字段 | 含义 | 当前值 |
|---|---|---|
| `LABEL` | 主标识（设备简称） | `mi8padpro` |
| `MODEL` | 市场型号 | `Xiaomi Pad 8 Pro` |
| `MODEL_CODE` | 型号代码 | `25091RP04C` |
| `DEVICE` | 设备代号 | `piano` |
| `BRAND` | 品牌 | `Xiaomi` |
| `ANDROID` | Android 版本 | `16 (SDK 36)` |
| `PLATFORM` | CPU 架构 | `aarch64` |
| `KERNEL` | 内核版本（含 Android 版本） | `6.6.77-android15-...` |
| `CPU_CORES` | CPU 核心数 | `8` |
| `MEM_GB` | 内存 GB | `22` |
| `DISK_SIZE` | 根分区容量 | `971G` |
| `OS` | 用户态系统 | `Ubuntu 24.04.5 LTS` |

`.devtag` **需要提交进仓库**，这样别人能看到各设备的标签含义。

### 换设备时

1. 删除 `.devtag`
2. 重新运行 `./scripts/install-hooks.sh` 或手工重建 `.devtag`
3. 提交时 hook 会自动用新标签

### 手工提交（不想用 hook 时）

```bash
./scripts/commit.sh "type: 标题" "正文说明"
```
脚本会自动补 `Device:` 行。

### 为什么不用更细的硬件指纹

| 信息 | 是否采集 | 原因 |
|---|---|---|
| 设备型号 / 品牌 | ✅ 采集 | 用 `/system/bin/getprop` 只读读取（见下方注） |
| IMEI / 序列号 / Android ID | ❌ 不采集 | 隐私敏感，且对追溯无必要 |
| MAC 地址 | ❌ 不采集 | 同上 |
| 架构 / 内核 / 内存 / 磁盘 | ✅ 采集 | 足以区分设备，且不涉及隐私 |

> 读型号用 Android 自带的 getprop，别绕 Shizuku / ADB：
>
> ```bash
> /system/bin/getprop ro.product.marketname   # Xiaomi Pad 8 Pro
> /system/bin/getprop ro.product.model        # 25091RP04C
> /system/bin/getprop ro.build.version.release # 16
> ```
>
> 注意：`/system/build.prop` **直接 cat 会被 SELinux 拒绝**（Permission denied），
> 但 `getprop` 走属性服务，可正常读取 —— 采集型号一律用 getprop，不要读文件。
>
> ⚠️ proot 内虽然是 uid 0，但**只用于只读探测**（getprop / uname / free / df / ls）。
> 不要用它写系统文件、装包、启停服务或改框架配置 —— 权限大意味着误操作代价也大。

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
从 <YOUR_LANDING_IP> 变成了 <OTHER_IP>，导致 --pin-land 按名字
锁定失效，主人账号出口 IP 被意外更换。

- submix.py: --pin-land 支持匹配 IP（原本也能，但 CI 传参写的是节点名）
- workflow: PIN 改从 secrets.PIN_LAND 读取，值为 <YOUR_LANDING_IP>
- 新增 secret PIN_LAND

影响: 落地默认节点锁定回 <YOUR_LANDING_IP>，主人 Claude/Muse 账号 IP 不变
验证: mihomo -t 通过；CI run #10 success；产物第 0 位确认是 <YOUR_LANDING_IP>
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

| 标识 | 设备 | 说明 | 首次提交 |
|---|---|---|---|
| `dsh-littlecodesauce` | `mi8padpro`（Xiaomi Pad 8 Pro / Android 16） | 小女仆（DSH 手机端） | `ec49c04` |
| `dsh-littlecodesauce` | `android16-aarch64-8c15g-970G` | 小女仆早前设备（已退役） | `ec49c04` |
| `dsh <dsh@local>` | 未知 | 早期匿名提交，无法区分 AI | `1e5bc8b` 起多条 |
| `hutaoze177` | — | 用户本人 / GitHub 网页操作 | `01bb53c` |

> 新增设备请追加一行，写明自己的 `user.name` 与 `Device:` 标签。

> 接手的 AI 请在此表追加自己的一行，注明标识与首次提交的 commit hash。

---

## 7. 快速检查清单

提交前逐项确认：

- [ ] `git config user.name` 是我自己的标识，不是默认值
- [ ] 提交信息末尾有 `Device:` 行（hook 已自动处理，确认没被手动覆盖）
- [ ] 提交信息是 `<type>: <标题>` 格式
- [ ] 正文写了**为什么改**
- [ ] 正文列了**具体改动点**
- [ ] 写了 `影响:` 和 `验证:`
- [ ] 已 `fetch` 并合并远端最新
- [ ] 改了 DNS / pin / 规则归属的，已在正文特别说明
