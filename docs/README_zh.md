[English](../README.md)

# SublimeNoteSync

为 Sublime Text 提供简单的笔记与自动 Git 同步能力。  
本地文件存储 + 后台同步 + 秒级退出。

---

## 功能

- 按日期自动创建笔记文件
- 自动保存（带防抖）
- 自动执行 `git pull → add → commit → push`
- 安全退出（⌘Q）：保存 + 后台 push + 立即退出
- 离线可用（自动等待网络恢复再 push）

无界面、无打扰、无需手动 Git 操作。

<img src="./show.gif" width="600">

---


## 笔记目录结构

```
~/Documents/SublimeNotes/-notes/YYYY-MM/note_YYYY-MM-DD_HH-MM-SS.txt
```

`-notes` 会排在侧边栏最上面。启动时会把仓库根目录下遗留的 `YYYY-MM` 文件夹自动迁入其中。

示例：

```
-notes/
  2025-02/
    note_2025-02-18_21-44-11.txt
    note_2025-02-19_10-02-55.txt
```

---

## 安装

### 1) 插件脚本

Sublime → `Preferences → Browse Packages…`

创建文件：

```
Packages/User/notes_sync.py
```

粘贴本仓库的脚本内容。

---

### 2) 配置文件

创建：

```
~/.sublime_note_sync.json
```

内容：

```json
{
  "repo_path": "~/Documents/SublimeNotes",
  "auto_create_repo_dir": true,

  "git_remote": "git@github.com:YOUR_NAME/sublime-notes-sync.git",

  "auto_save_delay_ms": 800,
  "git_debounce_ms": 5000,
  "commit_prefix": "auto",

  "git_user": {
    "user.name": "你的名字",
    "user.email": "你的邮箱"
  }
}
```

---

### 3) 绑定 ⌘Q 安全退出

Sublime → Key Bindings (User)

```json
{ "keys": ["super+q"], "command": "notes_safe_exit" }
```

---

## 使用

### 新建笔记

命令面板：

```
New Note
```

可选快捷键：

```json
{ "keys": ["super+n"], "command": "new_note" }
```

### 日常流程

- 创建笔记
- 输入内容
- 关闭 Sublime
- Git 同步后台自动进行

---

## 首次仓库准备

方式 A（推荐）：打开 Sublime，插件会自动初始化。

方式 B：手动 clone：

```bash
git clone git@github.com:YOUR_NAME/sublime-notes-sync.git ~/Documents/SublimeNotes
```

---

## 补充说明

- push 日志保存在仓库目录下 `.notesync_push.log`
- 离线时会先本地 commit，连接网络后自动 push
- 同步使用 `git pull --rebase --autostash` 减少冲突

---

## License

MIT
