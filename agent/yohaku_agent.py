#!/usr/bin/env python3
"""Provider-independent Yohaku tools, model loop, JSON CLI and MCP stdio server.
Only Python's standard library is needed. Workspace mutations go through Rust.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import yohaku_coordinates as coordinates

ROOT = Path(__file__).resolve().parents[1]
SYSTEM = """You work alongside the human inside Yohaku, a local editable world.
Use tools to inspect the current context and locate files before editing. Text
sources (.tex) are the source of truth; Loom generates outputs. Do not claim a
change succeeded unless its tool result confirms it, including Loom sync errors.
Keep human notes, links and provenance unless asked to change them. Read memory
when relevant; write factual notes only when useful, never invent experiences.
Loom tex sections use these exact Chinese names: 正文, 输出与关联, AI 笔记.
An optional AI note section is '## AI 笔记' followed by a yaml fenced block.
That block requires source_version (positive integer), writer (string) and summary (string).
Preserve the existing format when editing full tex; arbitrary headings are invalid.
Revisions detect concurrent changes: re-read on conflict. Unsaved human drafts
must be preserved. Tools return structured page state, not rendered screenshots.
For precise edits use read_range and edit_range. Address a world-relative file
path and 1-based line/column positions counting Unicode characters, not bytes
or screen pixels. End is exclusive. Use view=body on managed .tex to edit code
while preserving notes/routing; view=text addresses the full source or plain
world text. Copy the whole-file revision and exact selected original text into
edit_range. It saves through the existing workspace/Loom and reads back the
result; verified=true confirms the saved source view, not program execution.
Use create_document, or write_text followed by adopt_file for new nested files.
Local tools are registered in memory/tools.json (format yohaku-tools/1; tools
array with id/name/program/args/wayland). Use list_tools to discover them. On the
native connection, run_tool requests an offline world-contained sandbox launch,
tool_status reports whether it actually started/failed/finished, and stop_tool
stops it. Never claim launch success from state starting. Tool program is
/usr/bin/..., /bin/..., world:relative/path, builtin:window, or builtin:dev. Tool args are a JSON
string array, wayland is boolean. No arbitrary host mounts, network, host env or
host home can be configured. GUI support is Wayland only; incompatible tools may
fail. Run tools needed for the human's requested task when run permission is granted.
File-editing tools alone still do not execute generated code.
If memory/development.json exists, read memory/yohaku-development.md. It describes
the Loom-managed Yohaku default source copy and registered check/test/build/preview
tools. Edit its .tex sources; never claim that the currently running host changed.
run_tool(wait=true) and tool_status(wait=true) wait up to 30 seconds without model
polling. If still running, continue waiting; inspect exit_code, log_path and actual
logs before reporting success. Missing cached dependencies are real offline errors.
New nested world text can be registered with adopt_file to get a Loom .tex source.
Existing .tex sources can be registered with adopt_file without replacing them.
For node navigation start with list_entry_nodes, then get_node or walk_nodes.
find_nodes searches names/descriptions. Results contain body locations, not bodies.
Node metadata lives in the tex header; rebuild_node_index derives it from files/.
Duplicate IDs are ambiguous and broken links are reported; do not guess targets.
Node relations are navigation only; they never add Loom compilation dependencies.
Socius interaction settings are world text at memory/socius.json. Use read_text
and write_text/patch_text with revisions to configure them when the human asks;
native Yohaku hot reloads this file without restarting. Preserve unrelated macros.
The JSON object has format "yohaku-socius/1", macros (array), and chat (object).
chat fields: x/y null (auto position) or integers 0..32768; width 480..4096;
height 420..4096; font_scale 2..4 corresponds to 16/24/32 pixel text.
Each macro has name, trigger (context_menu, right_click or shortcut), optional
shortcut (Ctrl/Alt + letter/digit, optional Shift), action (open_chat, toggle_chat
or close_chat), prompt (optional text). Maximum 12 macros, one direct right_click,
unique shortcuts; prompt supports {selection}, {source}, {page}, {root}.
Macros open/prefill chat, never auto-send or execute code. Human instructions can
be ordinary language; you translate the request into valid file settings and
verify the tool result. These settings configure existing behavior, not arbitrary
new native features. Never store API keys in this world settings file.
File-editing tools do not execute generated code. Reply in the user's language.
"""

def definition(name, description, properties=None, required=()):
    return {"name": name, "description": description, "parameters": {
        "type": "object", "properties": properties or {},
        "required": list(required), "additionalProperties": False}}

S = {"type": "string"}
B = {"type": "boolean"}
REV = {"type": "string", "description": "revision returned by reading this exact file"}
N = {"type":"integer", "minimum":1}
VIEW = {"type":"string", "enum":["body","text"]}
LIMIT = {"type":"integer", "minimum":1, "maximum":100}
TOOLS = [
    definition("list_entry_nodes", "List entry node summaries and body read locations from tex metadata; default 20, maximum 100.", {"limit":LIMIT}),
    definition("find_nodes", "Find nodes by name or description. Returns summaries and body locations, not full documents.", {"query":S,"limit":LIMIT}, ("query",)),
    definition("get_node", "Get one unambiguous stable node ID, its typed links and body read location.", {"id":S}, ("id",)),
    definition("walk_nodes", "Breadth-first traversal including the start; cycles/duplicates visited once. Depth 0..8, result limit 1..100. Reports broken links.", {"id":S,"max_depth":{"type":"integer","minimum":0,"maximum":8},"limit":LIMIT}, ("id",)),
    definition("rebuild_node_index", "Rebuild the derived node index from tex sources. Queries also rebuild; no body content is indexed."),
    definition("read_range", "Read an exact text range with whole-file revision. World-relative path; body view requires a managed .tex. Positions start at 1, count Unicode characters; end is exclusive. Default page: 80 lines, maximum 128 KiB.", {"path":S,"view":VIEW,"start_line":N,"start_column":N,"end_line":N,"end_column":N}, ("path","view")),
    definition("edit_range", "Replace/insert/delete an exact range; empty range inserts, empty text deletes. Require revision and exact expected selection. Saves via Rust/Loom and reads back; body view preserves notes/routing. This does not run code.", {"path":S,"view":VIEW,"revision":REV,"start_line":N,"start_column":N,"end_line":N,"end_column":N,"expected":S,"text":S}, ("path","view","revision","start_line","start_column","end_line","end_column","expected","text")),
    definition("list_tools", "List configured local tools from memory/tools.json; sandbox policy is fixed."),
    definition("run_tool", "Launch a registered offline tool. wait=true waits up to 30 seconds for exit; starting/running is not success. Native only.", {"id":S,"wait":B}, ("id",)),
    definition("tool_status", "Current local tool state, exit_code, log_path and recent log. wait=true waits up to 30 seconds. Native only.", {"wait":B}),
    definition("stop_tool", "Stop the current sandboxed local tool. Completed world files remain. Native connection only."),
    definition("context", "Current world, page, active document, draft, caret and selection."),
    definition("list_files", "List Loom managed tex sources and their generated outputs."),
    definition("list_directory", "List actual world folders/files, including memory and macros.", {"path": S}, ("path",)),
    definition("read_document", "Read managed tex and its extracted body; returns revision.", {"source": S}, ("source",)),
    definition("create_document", "Create a named text output and its tex source via Loom reverse.", {"name": S, "body": S}, ("name", "body")),
    definition("adopt_file", "Register existing world text below files/. Existing .tex is validated and registered unchanged; plain files get a Loom source. Registration of existing tex does not generate output.", {"path":S}, ("path",)),
    definition("import_document", "Copy one external UTF-8 file into this world and reverse via Loom; original stays untouched.", {"path": S}, ("path",)),
    definition("write_document", "Save whole tex or only body; preserve notes for body_only=true; sync Loom.", {"source": S, "revision": REV, "text": S, "body_only": B}, ("source", "revision", "text", "body_only")),
    definition("patch_document", "Replace a unique exact substring in body or tex, then sync. Reject ambiguous matches.", {"source": S, "revision": REV, "old": S, "new": S, "body_only": B}, ("source", "revision", "old", "new", "body_only")),
    definition("sync_document", "Run Loom for an existing source; returns generation/cleanup status.", {"source": S}, ("source",)),
    definition("delete_document", "Delete a source and clean up its owned output via Loom.", {"source": S, "revision": REV}, ("source", "revision")),
    definition("read_text", "Read UTF-8 world text; memory/socius.json holds hot-reloaded macros and chat layout. Returns revision.", {"path": S}, ("path",)),
    definition("write_text", "Write world text with revision (null only for new path). memory/socius.json configures macros/chat and is validated and hot reloaded. Tracked tex syncs; edit outputs through source.", {"path": S, "revision": {"type": ["string", "null"]}, "text": S}, ("path", "revision", "text")),
    definition("patch_text", "Replace one unique substring in any editable world text using its revision.", {"path": S, "revision": REV, "old": S, "new": S}, ("path", "revision", "old", "new")),
    definition("delete_text", "Delete one read world text using its revision; managed sources use Loom cleanup.", {"path": S, "revision": REV}, ("path", "revision")),
    definition("search_text", "Search literal text recursively within a world folder; bounded results include paths/line numbers.", {"path": S, "query": S}, ("path", "query")),
]

GROUPS = {
    "run": {"run_tool", "stop_tool"},
    "read": {"read_range","list_entry_nodes","find_nodes","get_node","walk_nodes","rebuild_node_index","list_tools","tool_status","context", "list_files", "list_directory", "read_document", "read_text", "search_text"},
    "write": {"edit_range","create_document", "adopt_file", "write_document", "patch_document", "sync_document", "write_text", "patch_text"},
    "delete": {"delete_document", "delete_text"},
    "import": {"import_document"},
}

DEFAULT_PERMISSIONS = object()

def allowed_tools(permissions=DEFAULT_PERMISSIONS):
    if permissions is DEFAULT_PERMISSIONS:
        return [t for t in TOOLS if t["name"] not in GROUPS["run"]]
    if not isinstance(permissions, dict):
        raise ToolError("permissions must be an object")
    allowed = set().union(*(names for group, names in GROUPS.items() if permissions.get(group, group != "run") is True))
    return [t for t in TOOLS if t["name"] in allowed]


def revision(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

class ToolError(Exception):
    pass

class Workspace:
    def __init__(self, root, loom, executable=None):
        self.root = str(Path(root).resolve())
        self.loom = str(Path(loom).resolve())
        self.executable = str(executable or ROOT / "bin/yohaku_workspace")

    def execute(self, request):
        try:
            result = subprocess.run([self.executable, "--root", self.root, "--loom", self.loom],
                input=json.dumps(request, ensure_ascii=False), capture_output=True, text=True, timeout=60)
            value = json.loads(result.stdout)
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            raise ToolError(f"Workspace command failed: {type(exc).__name__}") from exc
        if not value.get("ok"):
            raise ToolError(value.get("error", "Workspace failed"))
        return value["result"]

class Tools:
    def __init__(self, execute, context=None, permissions=DEFAULT_PERMISSIONS, native=True):
        self.execute = execute
        self.definitions = [t for t in allowed_tools(permissions) if native or t["name"] not in {"run_tool","stop_tool","tool_status"}]
        self.active_name = None
        self.current_context = context or (lambda: {"page": "external", "draft": None})

    def call(self, name, args):
        try:
            schema = next((t for t in TOOLS if t["name"] == name), None)
            if schema is None:
                raise ToolError(f"Unknown tool: {name}")
            if name not in {t["name"] for t in self.definitions}:
                raise ToolError(f"Tool permission denied: {name}")
            if not isinstance(args, dict):
                raise ToolError("Tool arguments must be an object")
            props = schema["parameters"]["properties"]
            if set(args) - set(props) or set(schema["parameters"]["required"]) - set(args):
                raise ToolError("Missing or unknown tool argument")
            for key, value in args.items():
                kind = props[key]["type"]
                kinds = kind if isinstance(kind, list) else [kind]
                if not (("string" in kinds and isinstance(value, str)) or
                    ("integer" in kinds and type(value) is int) or
                    ("boolean" in kinds and isinstance(value, bool)) or ("null" in kinds and value is None)):
                    raise ToolError(f"Invalid type for {key}")
                if "enum" in props[key] and value not in props[key]["enum"]:
                    raise ToolError(f"Invalid value for {key}")
                if "minimum" in props[key] and value < props[key]["minimum"]:
                    raise ToolError(f"Invalid value for {key}")
                if "maximum" in props[key] and value > props[key]["maximum"]:
                    raise ToolError(f"Invalid value for {key}")
            previous_name = self.active_name
            self.active_name = name
            try:
                result = self._call(name, args)
            finally:
                self.active_name = previous_name
            if isinstance(result, dict):
                if name in ("read_range","edit_range") and result.get("ok") is False:
                    return result
                loom = result.get("loom", result)
                if result.get("sync_error") or (isinstance(loom, dict) and loom.get("ok") is False):
                    return {"ok": False, "error": result.get("sync_error") or "Loom reported a failure or retained output; inspect result", "result": result}
            return {"ok": True, "result": result}
        except (ToolError, ValueError, KeyError) as exc:
            return {"ok": False, "error": str(exc)}

    def _read(self, path, document):
        req = {"command": "read", "source": path} if document else {"command": "read_text", "path": path}
        result = self.execute(req)
        result["revision"] = revision(result["text"])
        return result

    def _checked(self, path, version, document):
        value = self._read(path, document)
        if value["revision"] != version:
            raise ToolError("File changed since reading; re-read it before editing")
        return value

    def _call(self, name, a):
        if name in ("read_range", "edit_range"):
            return self.coordinate(name, a)
        if name=="list_tools":
            from yohaku_tools import validate
            value=self._read("memory/tools.json",False)
            return validate(json.loads(value["text"]))
        if name in ("run_tool","tool_status","stop_tool"):
            request={k:v for k,v in a.items() if k!='wait'}
            result=self.execute({"command":{"run_tool":"tool_run","tool_status":"tool_status","stop_tool":"tool_stop"}[name], **request})
            if a.get('wait'):
                deadline=time.monotonic()+30
                while result.get('state') in ('starting','running') and time.monotonic()<deadline:
                    time.sleep(.25)
                    result=self.execute({'command':'tool_status'})
            return result
        if name == "context":
            return self.current_context()
        simple = {"list_entry_nodes":"node_entries", "find_nodes":"node_search", "get_node":"node_get", "walk_nodes":"node_walk", "rebuild_node_index":"node_index",
            "list_files": "list", "list_directory": "directory", "create_document": "create", "adopt_file":"adopt",
            "import_document": "import", "sync_document": "sync"}
        if name in simple:
            return self.execute({"command": simple[name], **a})
        if name.startswith("read_"):
            document = name == "read_document"
            return self._read(a["source" if document else "path"], document)
        if name == "search_text":
            return self.search(a["path"], a["query"])
        document = name.endswith("_document")
        path = a["source" if document else "path"]
        if name == "write_text" and a["revision"] is None:
            # Rust rejects expected:null if this path already exists.
            return self.execute({"command": "write_text", "path": path, "expected": None, "text": a["text"]})
        old = self._checked(path, a["revision"], document)
        if name.startswith("delete_"):
            return self.execute({"command": "delete" if document else "delete_text",
                "source" if document else "path": path, "expected": old["text"]})
        body_only = a.get("body_only", False)
        text = a.get("text")
        if name.startswith("patch_"):
            basis = old["body"] if body_only else old["text"]
            if not a["old"] or basis.count(a["old"]) != 1:
                raise ToolError("Patch must match exactly one nonempty substring; read and narrow the target")
            text = basis.replace(a["old"], a["new"], 1)
        return self.execute({"command": "save" if document else "write_text",
            "source" if document else "path": path, "expected": old["text"], "text": text,
            **({"body_only": body_only} if document else {})})

    def coordinate(self, name, a):
        path, view = a['path'], a['view']
        if not path or path.startswith('/') or '\\' in path or any(p in ('..','') for p in path.split('/')):
            raise ToolError('Use a world-relative file path, for example files/demo.py.tex')
        document = path.endswith('.tex')
        if view == 'body' and not document:
            raise ToolError('Body coordinates require the managed .tex source; use view=text for plain files')
        read_tool = 'read_document' if document else 'read_text'
        read_args = {'source' if document else 'path':path}
        # Delegate through the existing allowed tools, preserving their native
        # RPC tags. Rust still checks read/write permissions and file ownership.
        def delegate(tool, args):
            reply = self.call(tool,args)
            if not reply['ok']:
                return None, reply
            return reply['result'], None
        old, error = delegate(read_tool,read_args)
        if error:
            return error
        if view == 'body' and old.get('valid') is not True:
            raise ToolError('Document is invalid; read view=text to repair its source before editing the body')
        basis = old['body'] if view == 'body' else old['text']
        if name == 'read_range':
            result = coordinates.read(basis, **{k:v for k,v in a.items() if k not in ('path','view')})
            return dict(result,path=path,view=view,revision=old['revision'])
        if old['revision'] != a['revision']:
            raise ToolError('File changed since reading; no edit made, read the range again')
        updated = coordinates.replace(basis,a['start_line'],a['start_column'],a['end_line'],a['end_column'],a['expected'],a['text'])
        write_tool = 'write_document' if document else 'write_text'
        write_args = dict(read_args,revision=old['revision'],text=updated)
        if document:
            write_args['body_only'] = view == 'body'
        saved, error = delegate(write_tool,write_args)
        if error:
            # Keep Loom failures visible, including a source saved before a
            # generation conflict. Never report an unsuccessful sync as success.
            return error
        current, error = delegate(read_tool,read_args)
        if error:
            return {'ok':False,'error':'Edit was saved but read-back failed; inspect the document', 'saved':True,'verified':False,'details':error}
        actual = current['body'] if view == 'body' else current['text']
        try:
            digest = coordinates.verify(actual,updated)
        except ValueError as error:
            return {'ok':False,'error':str(error),'saved':True,'verified':False,'revision':current['revision']}
        return {'path':path,'view':view,'saved':True,'verified':True,
                'revision':current['revision'],'view_hash':digest,
                'replaced_characters':len(a['expected']),'inserted_characters':len(a['text']),
                'loom':saved.get('loom') if isinstance(saved,dict) else None}

    def search(self, start, query):
        if not query:
            raise ToolError("Search query must not be empty")
        pending = [start]; matches = []; scanned = 0; skipped = []
        while pending:
            folder = pending.pop()
            entries = self.execute({"command": "directory", "path": folder})["entries"]
            for item in entries:
                if item["kind"] == "directory":
                    pending.append(item["path"])
                elif item["kind"] == "file":
                    scanned += 1
                    if scanned > 1000:
                        return {"matches": matches, "truncated": True, "skipped": skipped}
                    try:
                        text = self.execute({"command": "read_text", "path": item["path"]})["text"]
                    except ToolError:
                        skipped.append(item["path"]); continue
                    for n, line in enumerate(text.splitlines(), 1):
                        if query in line:
                            matches.append({"path": item["path"], "line": n, "text": line[:600]})
                            if len(matches) >= 100:
                                return {"matches": matches, "truncated": True, "skipped": skipped}
        return {"matches": matches, "truncated": False, "skipped": skipped}

def read_config(path=None):
    config = {"protocol": "chat", "base_url": "https://api.deepseek.com", "model": "deepseek-flash",
        "api_key_env": "DEEPSEEK_API_KEY", "max_tokens": 4096, "max_rounds": 12, "timeout": 120}
    path = Path(path or ROOT / "config/ai.json")
    if path.exists():
        config.update(json.loads(path.read_text()))
    return config

class Provider:
    def __init__(self, config):
        self.config = config
        self.definitions = allowed_tools(config.get("permissions", DEFAULT_PERMISSIONS))
        self.system = SYSTEM + "\nAI name: " + str(config.get("name", "AI")) + "\nPersonality defined by the human:\n" + str(config.get("personality", ""))
        self.protocol = config.get("protocol", "chat")
        if self.protocol not in ("chat", "responses", "anthropic"):
            raise ToolError("Protocol must be chat, responses or anthropic")
        base = config.get("base_url", "").rstrip("/")
        u = urllib.parse.urlsplit(base)
        if u.scheme not in ("http", "https") or not u.netloc or u.username or u.password or u.query or u.fragment:
            raise ToolError("Invalid API base URL")
        if u.scheme == "http" and u.hostname not in ("localhost", "127.0.0.1", "::1"):
            raise ToolError("Use HTTPS for remote APIs; HTTP is supported for local models")
        self.url = base + {"chat": "/chat/completions", "responses": "/responses", "anthropic": "/messages"}[self.protocol]
        self.key = config.get("api_key") or os.environ.get(config.get("api_key_env", "DEEPSEEK_API_KEY"), "")
        if not isinstance(self.key, str):
            raise ToolError("API key must be a string")
        if not self.key and u.hostname not in ("localhost", "127.0.0.1", "::1"):
            raise ToolError("Set the API key in Socius or the configured environment variable")
        if not config.get("model"):
            raise ToolError("Choose a model")

    def initial(self, prompt, context, history=None):
        user = prompt + "\n\nCurrent Yohaku context:\n" + json.dumps(context, ensure_ascii=False)
        history = list(history or [])
        if self.protocol == "chat":
            return history + [{"role": "user", "content": user}]
        return history + [{"role": "user", "content": user}]

    def request(self, messages):
        c = self.config
        common = {"model": c["model"], "stream": False}
        if self.protocol == "chat":
            body = {**common, "messages": [{"role": "system", "content": self.system}] + messages,
                "max_tokens": c.get("max_tokens", 4096), "tools": [{"type": "function", "function": t} for t in self.definitions]}
            if urllib.parse.urlsplit(c["base_url"]).hostname == "api.deepseek.com":
                body["thinking"] = {"type": "disabled"}
        elif self.protocol == "responses":
            body = {**common, "instructions": self.system, "input": messages,
                "max_output_tokens": c.get("max_tokens", 4096),
                "tools": [{"type": "function", **t, "strict": False} for t in self.definitions]}
        else:
            body = {**common, "system": self.system, "messages": messages, "max_tokens": c.get("max_tokens", 4096),
                "tools": [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in self.definitions]}
        if not self.definitions:
            body.pop("tools", None)
        options = c.get("request_options", {})
        if not isinstance(options, dict) or set(options) & {"model", "messages", "input", "instructions", "system", "tools", "stream"}:
            raise ToolError("Invalid request_options; message/tool structure must remain managed by Yohaku")
        if self.protocol == "chat" and "max_completion_tokens" in options:
            body.pop("max_tokens", None)
        body.update(options)
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.protocol == "anthropic":
            headers.update({"x-api-key": self.key, "anthropic-version": "2023-06-01"})
        elif self.key:
            headers["Authorization"] = "Bearer " + self.key
        request = urllib.request.Request(self.url, data=json.dumps(body, ensure_ascii=False).encode(), headers=headers)
        try:
            # No redirect can send a credential to a different API host.
            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, *args, **kwargs):
                    return None
            with urllib.request.build_opener(NoRedirect).open(request, timeout=c.get("timeout", 120)) as r:
                data = r.read(16 * 1024 * 1024 + 1)
            if len(data) > 16 * 1024 * 1024:
                raise ToolError("API response is too large")
            result = json.loads(data)
        except urllib.error.HTTPError as e:
            # Error bodies can echo prompts or credentials; do not log them.
            e.close()
            raise ToolError(f"API HTTP {e.code}; check model, key, quota and endpoint") from e
        except (OSError, ValueError) as e:
            raise ToolError(f"API request failed: {type(e).__name__}") from e
        try:
            return self.decode(result)
        except (AttributeError, KeyError, TypeError, IndexError) as exc:
            raise ToolError("API returned an invalid response shape; no tools were executed") from exc

    def decode(self, r):
        if self.protocol == "chat":
            choice = (r.get("choices") or [{}])[0]
            if choice.get("finish_reason") not in ("stop", "tool_calls"):
                raise ToolError("API response is incomplete; no tools were executed")
            msg = choice.get("message", {})
            calls = [{"id": t.get("id"), "name": t.get("function", {}).get("name"),
                "arguments": t.get("function", {}).get("arguments")} for t in msg.get("tool_calls", [])]
            return msg, calls, msg.get("content") or "", r.get("usage", {})
        if self.protocol == "responses":
            if r.get("status") != "completed":
                raise ToolError("API response is incomplete; no tools were executed")
            output = r.get("output", [])
            calls = [{"id": t.get("call_id"), "name": t.get("name"), "arguments": t.get("arguments")}
                for t in output if t.get("type") == "function_call"]
            text = "\n".join(p.get("text", "") for item in output if item.get("type") == "message"
                for p in item.get("content", []) if p.get("type") == "output_text")
            return output, calls, text, r.get("usage", {})
        if r.get("stop_reason") not in ("end_turn", "tool_use"):
            raise ToolError("API response is incomplete; no tools were executed")
        blocks = r.get("content", [])
        calls = [{"id": t.get("id"), "name": t.get("name"), "arguments": t.get("input")}
            for t in blocks if t.get("type") == "tool_use"]
        return blocks, calls, "\n".join(t["text"] for t in blocks if t.get("type") == "text"), r.get("usage", {})

    def append(self, messages, assistant, results):
        if self.protocol == "chat":
            messages.append(assistant)
            messages.extend({"role": "tool", "tool_call_id": c["id"], "content": json.dumps(r, ensure_ascii=False)} for c,r in results)
        elif self.protocol == "responses":
            messages.extend(assistant)
            messages.extend({"type": "function_call_output", "call_id": c["id"], "output": json.dumps(r, ensure_ascii=False)} for c,r in results)
        else:
            messages.append({"role": "assistant", "content": assistant})
            if results:
                messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": c["id"],
                    "content": json.dumps(r, ensure_ascii=False), "is_error": not r.get("ok", False)} for c,r in results]})

class Agent:
    def __init__(self, provider, tools, emit=lambda e: None):
        self.provider = provider; self.tools = tools; self.emit = emit

    def run(self, prompt, context, history=None):
        messages = self.provider.initial(prompt, context, history)
        max_rounds = max(1, min(int(self.provider.config.get("max_rounds", 12)), 50))
        total = 0
        usage_rounds = []
        for n in range(max_rounds):
            self.emit({"event": "status", "text": f"Model round {n+1}/{max_rounds}"})
            assistant, calls, text, usage = self.provider.request(messages)
            usage_rounds.append(usage)
            if len(calls) > 32 or any(not isinstance(c["id"],str) or not c["id"] or not isinstance(c["name"],str) for c in calls) or len({c["id"] for c in calls}) != len(calls):
                raise ToolError("Invalid tool call batch; no tools were executed")
            if text:
                self.emit({"event": "assistant", "text": text})
            if not calls:
                self.provider.append(messages, assistant, [])
                input_tokens = sum(u.get("input_tokens", u.get("prompt_tokens", 0)) for u in usage_rounds)
                output_tokens = sum(u.get("output_tokens", u.get("completion_tokens", 0)) for u in usage_rounds)
                return {"text": text, "history": messages,
                    "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens, "total_tokens": input_tokens + output_tokens},
                    "usage_by_round": usage_rounds, "tool_calls": total}
            results = []
            for call in calls:
                try:
                    args = call["arguments"] if isinstance(call["arguments"], dict) else json.loads(call["arguments"])
                    result = self.tools.call(call["name"], args)
                except (ValueError, TypeError):
                    result = {"ok": False, "error": "Tool arguments are not valid JSON"}
                results.append((call,result)); total += 1
                self.emit({"event": "tool_result", "name": call["name"], "result": result})
            self.provider.append(messages, assistant, results)
        raise ToolError("Model round limit reached; completed changes remain saved. Start a new turn to continue.")

def output(value):
    print(json.dumps(value, ensure_ascii=False), flush=True)

def wire():
    initial = json.loads(sys.stdin.readline())
    sequence = 0
    def remote(request):
        nonlocal sequence
        sequence += 1
        output({"event": "request", "id": sequence, "tool": tools.active_name, "request": request})
        reply = json.loads(sys.stdin.readline())
        if reply.get("id") != sequence:
            raise ToolError("UI tool reply mismatch")
        if not reply.get("ok"):
            raise ToolError(reply.get("error", "UI tool failed"))
        return reply["result"]
    tools = Tools(remote, lambda: remote({"command": "context"}), initial["config"].get("permissions", DEFAULT_PERMISSIONS))
    try:
        if initial['config'].get('protocol')=='codex-local':
            import yohaku_codex
            try:result=yohaku_codex.run(initial,tools,output)
            except (yohaku_codex.CodexError,OSError,subprocess.SubprocessError) as exc:raise ToolError(str(exc)) from exc
        else:result = Agent(Provider(initial["config"]),tools,output).run(initial["prompt"],initial["context"],initial.get("history"))
        output({"event": "done", **result})
    except (ToolError, ValueError, KeyError) as exc:
        output({"event": "error", "text": str(exc)})

def mcp(tools):
    # Newline-delimited JSON-RPC on stdio. No diagnostics on stdout.
    initialized = False
    negotiated = False
    for line in sys.stdin:
        try:
            request = json.loads(line)
            if not isinstance(request, dict) or request.get("jsonrpc") != "2.0" or not isinstance(request.get("method"), str):
                output({"jsonrpc":"2.0", "id":None, "error":{"code":-32600,"message":"Invalid request"}})
                continue
            method = request["method"]; params = request.get("params", {})
            if not isinstance(params, dict):
                raise TypeError("params")
            if "id" not in request:
                if method == "notifications/initialized" and negotiated: initialized = True
                continue
            if method == "initialize":
                version = params.get("protocolVersion", "2025-06-18")
                if version not in ("2024-11-05", "2025-03-26", "2025-06-18"): version = "2025-06-18"
                value = {"protocolVersion": version, "capabilities": {"tools": {}},
                    "serverInfo": {"name": "yohaku", "version": "0.1.6"}}
                negotiated = True
            elif method == "ping": value = {}
            elif not initialized:
                output({"jsonrpc":"2.0", "id":request["id"], "error":{"code":-32002,"message":"Initialize first"}})
                continue
            elif method == "tools/list": value = {"tools": [{"name": t["name"], "description": t["description"], "inputSchema": t["parameters"]} for t in tools.definitions]}
            elif method == "tools/call":
                result = tools.call(params.get("name"), params.get("arguments", {}))
                value = {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}], "isError": not result["ok"]}
            else:
                output({"jsonrpc": "2.0", "id": request["id"], "error": {"code": -32601,"message":"Method not found"}}); continue
            output({"jsonrpc": "2.0", "id": request["id"], "result": value})
        except (ValueError, TypeError, KeyError):
            output({"jsonrpc":"2.0", "id":None, "error":{"code":-32700,"message":"Invalid JSON-RPC request"}})

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT/"worlds/default"))
    parser.add_argument("--loom", default=str(ROOT/"bin/loom-linux-x86_64"))
    parser.add_argument("--config")
    parser.add_argument("mode", choices=("chat", "tool", "tools", "mcp", "wire"))
    parser.add_argument("arguments", nargs="*")
    a = parser.parse_args()
    if a.mode == "wire": wire(); return
    w = Workspace(a.root,a.loom)
    config = read_config(a.config)
    tools = Tools(w.execute,lambda:{"root":w.root,"page":"external","draft":None,"socius":{"settings_path":"memory/socius.json"}}, config.get("permissions", DEFAULT_PERMISSIONS),native=False)
    if a.mode == "tools": output(tools.definitions)
    elif a.mode == "tool":
        if len(a.arguments) != 2: parser.error("tool needs NAME and JSON_ARGS")
        output(tools.call(a.arguments[0],json.loads(a.arguments[1])))
    elif a.mode == "mcp": mcp(tools)
    else:
        prompt = " ".join(a.arguments) or input("You> ")
        try:
            provider=Provider(config);provider.definitions=tools.definitions
            result = Agent(provider,tools,output).run(prompt,tools.current_context())
            output({"event":"done",**result})
        except ToolError as exc: output({"event":"error","text":str(exc)});sys.exit(1)

if __name__ == "__main__": main()
