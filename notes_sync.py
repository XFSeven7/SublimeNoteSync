import sublime
import sublime_plugin
import os
import json
import datetime
import threading
import subprocess
import shlex
import tempfile

# =============== 基础与工具 ===============
CONFIG_FILE = os.path.expanduser("~/.sublime_note_sync.json")

def _expand(p):
    return os.path.normpath(os.path.expanduser(os.path.expandvars(p or "")))

def _popen_kwargs():
    kw = {}
    if os.name == "nt":
        kw["creationflags"] = subprocess.CREATE_NO_WINDOW
    return kw

def _run(cmd, cwd=None):
    try:
        popen_kw = _popen_kwargs()
        if cwd:
            popen_kw["cwd"] = cwd
        p = subprocess.Popen(
            cmd if isinstance(cmd, list) else shlex.split(cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            **popen_kw
        )
        out, err = p.communicate()
        return p.returncode, (out or "").strip(), (err or "").strip()
    except Exception as e:
        return 1, "", str(e)

def _status(msg):
    sublime.status_message("[NotesSync] " + msg)
    print("[NotesSync]", msg)

def _log(msg):
    if CFG.get("log_level") == "debug":
        print("[NotesSync:debug]", msg)

def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# =============== 配置加载 ===============
def load_config():
    default = {
        "repo_path": "~/Documents/SublimeNotes",
        "auto_create_repo_dir": True,
        "git_remote": "",
        "auto_save_delay_ms": 800,
        "git_debounce_ms": 5000,
        "commit_prefix": "auto",
        "git_user": {"user.name": "", "user.email": ""},
        "log_level": "info"
    }
    if not os.path.exists(CONFIG_FILE):
        _status("Config not found, create: " + CONFIG_FILE)
        return default
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            user = json.load(f)
        for k, v in user.items():
            if isinstance(v, dict) and isinstance(default.get(k), dict):
                default[k].update(v)
            else:
                default[k] = v
    except Exception as e:
        _status("Config load error: {}".format(e))
    return default

CFG = load_config()
BASE_DIR = _expand(CFG.get("repo_path") or "~/Documents/SublimeNotes")
AUTO_SAVE_DELAY_MS = int(CFG.get("auto_save_delay_ms", 800))
GIT_DEBOUNCE_MS = int(CFG.get("git_debounce_ms", 5000))
COMMIT_PREFIX = CFG.get("commit_prefix", "auto")

# =============== Git 包装 ===============
def git(*args):
    return _run(["git", "-C", BASE_DIR] + list(args))

def ensure_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)

def is_git_repo():
    code, out, _ = _run(["git", "rev-parse", "--is-inside-work-tree"], cwd=BASE_DIR)
    return code == 0 and out == "true"

def git_set_local_identity():
    name = (CFG.get("git_user") or {}).get("user.name") or ""
    email = (CFG.get("git_user") or {}).get("user.email") or ""
    if name:
        git("config", "user.name", name)
    if email:
        git("config", "user.email", email)
    if name or email:
        _status("Git identity set: {} {}".format(name or "?", email or "?"))

def ensure_git_remote():
    remote = (CFG.get("git_remote") or "").strip()
    if not remote:
        return
    c, out, _ = git("remote", "get-url", "origin")
    if c == 0 and out.strip() == remote:
        return
    if c == 0:
        git("remote", "set-url", "origin", remote)
    else:
        git("remote", "add", "origin", remote)

def full_git_sync(status_callback=None, log_path=None):
    def report(msg):
        if status_callback:
            status_callback(msg)
        if log_path:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(msg + "\n")

    report("Syncing… pull")
    code, out, err = git("pull", "--rebase", "--autostash")
    if code != 0:
        msg = "Pull failed: {}".format(err or out)
        report(msg)
        _log(msg)
        return False, msg

    c, out, _ = git("status", "--porcelain")
    if c == 0 and out.strip():
        git("add", "-A")
        git("commit", "-m", "{}: {}".format(COMMIT_PREFIX, now_str()))

    pc, pout, perr = git("push")
    if pc == 0:
        report("Synced ✔")
        return True, "Synced"
    msg = "Push failed: {}".format(perr or pout)
    report(msg)
    _log(msg)
    return False, msg

# =============== 后台异步 Push（退出秒退） ===============
def spawn_async_push():
    """
    后台 push：退出后继续执行
    日志写入 repo/.notesync_push.log
    """
    log_path = os.path.join(BASE_DIR, ".notesync_push.log")
    stamp = now_str()
    commit_msg = "{}: {}".format(COMMIT_PREFIX, stamp)

    if os.name == "nt":
        try:
            fd, bat_path = tempfile.mkstemp(suffix=".cmd", prefix="notesync_")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write("@echo off\n")
                f.write('git -C "{}" pull --rebase --autostash >> "{}" 2>&1\n'.format(BASE_DIR, log_path))
                f.write('git -C "{}" add -A >> "{}" 2>&1\n'.format(BASE_DIR, log_path))
                f.write('git -C "{}" commit -m "{}" >> "{}" 2>&1\n'.format(
                    BASE_DIR, commit_msg.replace('"', '""'), log_path))
                f.write("if errorlevel 1 ver >nul\n")
                f.write('git -C "{}" push >> "{}" 2>&1\n'.format(BASE_DIR, log_path))
                f.write('del /f /q "{}"\n'.format(bat_path))

            kw = _popen_kwargs()
            kw["creationflags"] = kw.get("creationflags", 0) | 0x00000008  # DETACHED_PROCESS
            subprocess.Popen([bat_path], **kw)
        except Exception as e:
            _status("Async push spawn failed: {}".format(e))
    else:
        bash_cmd = (
            "git -C {repo} pull --rebase --autostash && "
            "git -C {repo} add -A && "
            "(git -C {repo} commit -m {msg} || true) && "
            "git -C {repo} push"
        ).format(
            repo=shlex.quote(BASE_DIR),
            msg=shlex.quote(commit_msg),
        )
        try:
            with open(log_path, "a", encoding="utf-8") as log_f:
                kw = _popen_kwargs()
                kw["start_new_session"] = True
                kw["stdout"] = log_f
                kw["stderr"] = subprocess.STDOUT
                subprocess.Popen(["bash", "-lc", bash_cmd], **kw)
        except Exception as e:
            _status("Async push spawn failed: {}".format(e))

# =============== 同步器（自动防抖） ===============
class GitSyncManager:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._timer = None
        self._busy = False
        self._pending = False

    @classmethod
    def get(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = GitSyncManager()
        return cls._instance

    def poke(self):
        if self._timer:
            try:
                self._timer.cancel()
            except Exception:
                pass
        self._timer = threading.Timer(GIT_DEBOUNCE_MS / 1000.0, self._run_async)
        self._timer.daemon = True
        self._timer.start()

    def _run_async(self):
        if self._busy:
            self._pending = True
            return
        self._busy = True
        threading.Thread(target=self._sync, daemon=True).start()

    def _sync(self):
        try:
            full_git_sync(status_callback=_status)
        finally:
            self._busy = False
            if self._pending:
                self._pending = False
                self._run_async()

    def cancel_timer(self):
        try:
            if self._timer:
                self._timer.cancel()
        except Exception:
            pass

# =============== 业务逻辑：新建/自动保存/清理 ===============
def in_repo(path):
    if not path:
        return False
    try:
        return os.path.commonpath([
            os.path.abspath(path),
            os.path.abspath(BASE_DIR),
        ]) == os.path.abspath(BASE_DIR)
    except ValueError:
        return False

def month_dir():
    d = os.path.join(BASE_DIR, datetime.datetime.now().strftime("%Y-%m"))
    ensure_dir(d)
    return d

class NewNoteCommand(sublime_plugin.WindowCommand):
    def run(self):
        if not os.path.isdir(BASE_DIR):
            sublime.error_message("NotesSync: repo_path invalid.\nEdit: {}".format(CONFIG_FILE))
            return
        d = month_dir()
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        fp = os.path.join(d, "note_{}.txt".format(ts))
        with open(fp, "w", encoding="utf-8"):
            pass
        self.window.open_file(fp)

class NotesAutoSaveListener(sublime_plugin.EventListener):
    def on_modified_async(self, view):
        fp = view.file_name()
        if not fp or not in_repo(fp):
            return
        if view.is_read_only() or view.is_scratch():
            return

        key = "notesync_auto_save_timer"
        old = view.settings().get(key)
        if old:
            try:
                sublime.cancel_timeout(old)
            except Exception:
                pass

        def do_save():
            if view.file_name() and in_repo(view.file_name()) and view.is_dirty():
                view.run_command("save")

        tid = sublime.set_timeout_async(do_save, int(CFG.get("auto_save_delay_ms", 800)))
        view.settings().set(key, tid)

    def on_post_save_async(self, view):
        fp = view.file_name()
        if not fp or not in_repo(fp):
            return
        GitSyncManager.get().poke()

class DeleteEmptyNoteOnClose(sublime_plugin.EventListener):
    def on_pre_close(self, view):
        fp = view.file_name()
        if not fp or not in_repo(fp):
            return
        content = view.substr(sublime.Region(0, view.size()))
        if content.strip():
            return
        try:
            if os.path.exists(fp):
                os.remove(fp)
                _status("Removed empty note: " + fp)
        except Exception as e:
            _status("Remove failed: {}".format(e))

# =============== 安全退出（异步 push，秒退） ===============
class NotesSafeExitCommand(sublime_plugin.ApplicationCommand):
    """
    安全退出：保存全部 → 启动后台 push → 立即退出
    """
    def run(self):
        try:
            for w in sublime.windows():
                for v in w.views():
                    try:
                        if v.is_dirty():
                            v.run_command("save")
                    except Exception:
                        pass

            GitSyncManager.get().cancel_timer()
            spawn_async_push()
        finally:
            sublime.run_command("exit")

# =============== 启动初始化 ===============
def plugin_loaded():
    if not BASE_DIR:
        sublime.error_message("NotesSync: repo_path missing.\nEdit: {}".format(CONFIG_FILE))
        return
    if not os.path.isdir(BASE_DIR):
        if bool(CFG.get("auto_create_repo_dir", True)):
            ensure_dir(BASE_DIR)
        else:
            sublime.error_message("NotesSync: repo_path not found.\n{}".format(BASE_DIR))
            return

    def init():
        if not is_git_repo():
            _status("Init git repo…")
            _run(["git", "init"], cwd=BASE_DIR)

        git_set_local_identity()
        ensure_git_remote()

        _status("Initializing pull…")
        git("pull", "--rebase", "--autostash")
        _status("Ready")
    threading.Thread(target=init, daemon=True).start()
