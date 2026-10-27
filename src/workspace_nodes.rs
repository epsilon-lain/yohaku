use super::{Result, Workspace, atomic, contained, io, string};
use serde_json::{Value, json};
use std::collections::{BTreeMap, BTreeSet, VecDeque};
use std::fs;

fn identifier(value: &str) -> bool {
    !value.is_empty() && value.len() <= 128
        && value.bytes().all(|byte| byte.is_ascii_alphanumeric() || b"._:-".contains(&byte))
}

fn bounded(request: &Value, key: &str, default: u64, maximum: u64) -> Result<usize> {
    let value = match request.get(key) {
        None => default,
        Some(value) => value.as_u64().ok_or_else(|| format!("{key} must be an integer"))?,
    };
    if value > maximum || (key != "max_depth" && value == 0) {
        return Err(format!("{key} is outside its allowed range (maximum {maximum})"));
    }
    Ok(value as usize)
}

pub(super) fn metadata(header: &Value, source: &str, registered: bool) -> Result<Option<Value>> {
    let Some(node) = header.get("node") else { return Ok(None) };
    let id = string(node, "id")?;
    let name = string(node, "name")?;
    let description = string(node, "description")?;
    if !identifier(id) || name.trim().is_empty() || name.chars().count() > 160
        || description.chars().count() > 500 {
        return Err("Invalid node ID, name or description length".into());
    }
    let entry = node.get("entry").map_or(Ok(false), |value| value.as_bool().ok_or("node.entry must be boolean"))?;
    let items = node["links"].as_array().ok_or("node.links must be an array")?;
    if items.len() > 64 { return Err("A node supports at most 64 links".into()) }
    let mut links = Vec::new();
    let mut seen = BTreeSet::new();
    for item in items {
        let relation = string(item, "relation")?;
        let target = string(item, "target")?;
        if !matches!(relation, "contains" | "related" | "tests") || !identifier(target) {
            return Err("Invalid node link relation or target ID".into());
        }
        if seen.insert((relation, target)) { links.push(json!({"relation":relation,"target":target})); }
    }
    Ok(Some(json!({"id":id,"name":name,"description":description,"entry":entry,"links":links,
        "location":{"path":source,"view":"body","start_line":1,"start_column":1},"registered":registered})))
}

fn summary(node: &Value) -> Value {
    let mut result = node.clone();
    result["link_count"] = json!(node["links"].as_array().unwrap().len());
    result.as_object_mut().unwrap().remove("links");
    result
}

pub(super) fn node_exclusions(root: &std::path::Path) -> Result<Vec<std::path::PathBuf>> {
    let path = contained(root, "memory/node-index-policy.json")?;
    let metadata = match fs::symlink_metadata(&path) {
        Ok(value) => value,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(Vec::new()),
        Err(error) => return Err(io(error)),
    };
    if !metadata.is_file() || metadata.len() > 65536 {
        return Err("Node index policy must be a regular file no larger than 64 KiB".into());
    }
    let bytes = fs::read(path).map_err(io)?;
    if bytes.len() > 65536 { return Err("Node index policy exceeds 64 KiB".into()) }
    let value: Value = serde_json::from_slice(&bytes).map_err(|_| "Invalid node index policy JSON")?;
    let object = value.as_object().ok_or("Node index policy must be an object")?;
    if object.len() != 2 || value["format"] != "yohaku-node-index-policy/1" || !object.contains_key("exclude_paths") {
        return Err("Node index policy requires format=yohaku-node-index-policy/1 and exclude_paths".into());
    }
    let paths = value["exclude_paths"].as_array().ok_or("Node exclude_paths must be an array")?;
    if paths.len() > 128 { return Err("Node exclude_paths supports at most 128 paths".into()) }
    let mut result = Vec::new();
    for value in paths {
        let text = value.as_str().ok_or("Node exclusion must be a literal files/... path")?;
        if text.len() > 1024 || text.contains('\\') || text.split('/').any(|part| part.is_empty() || part == "." || part == "..") {
            return Err("Node exclusion must be a literal files/... path".into());
        }
        let relative = super::relative(text)?;
        if !relative.starts_with("files") || relative == std::path::Path::new("files") {
            return Err("Node exclusion must be below files/, not the whole world".into());
        }
        contained(root, text)?;
        if !result.contains(&relative) { result.push(relative); }
    }
    Ok(result)
}

impl Workspace {
    pub(super) fn node_query(&self, request: &Value) -> Result<Value> {
        let excluded = node_exclusions(&self.root)?;
        let mut pending = vec![contained(&self.root, "files")?];
        let mut candidates: BTreeMap<String, Vec<Value>> = BTreeMap::new();
        let mut issues = Vec::new();
        let mut issue_count = 0;
        let mut scanned = 0;
        let mut report = |issue: Value| {
            issue_count += 1;
            if issues.len() < 100 { issues.push(issue); }
        };
        while let Some(folder) = pending.pop() {
            let mut entries = fs::read_dir(folder).map_err(io)?.collect::<std::io::Result<Vec<_>>>().map_err(io)?;
            entries.sort_by_key(|entry| entry.file_name());
            for entry in entries {
                scanned += 1;
                if scanned > 20000 { return Err("Node scan exceeds 20000 entries; use a smaller world".into()) }
                let path = entry.path();
                let relative = path.strip_prefix(&self.root).map_err(io)?;
                if excluded.iter().any(|excluded| relative.starts_with(excluded)) { continue }
                let kind = entry.file_type().map_err(io)?;
                let name = entry.file_name();
                if kind.is_symlink() || matches!(name.to_str(), Some(".git" | ".loom" | ".yohaku" | "target" | "__pycache__")) { continue }
                if kind.is_dir() { pending.push(entry.path()); continue }
                if !kind.is_file() || entry.path().extension().is_none_or(|ext| ext != "tex") { continue }
                let source = entry.path().strip_prefix(&self.root).map_err(io)?.to_str().ok_or("Node paths must be UTF-8")?.to_owned();
                let parsed = (|| {
                    if entry.metadata().map_err(io)?.len() > 2 * 1024 * 1024 { return Err("Source exceeds 2 MiB".into()) }
                    let doc = self.inspect(&entry.path())?;
                    metadata(&doc["header"], &source, self.entries.contains_key(&source))
                })();
                match parsed {
                    Ok(Some(node)) => candidates.entry(string(&node, "id")?.to_owned()).or_default().push(node),
                    Ok(None) => (),
                    Err(error) => report(json!({"kind":"invalid_document","source":source,"error":error})),
                }
            }
        }
        let duplicate_sources: BTreeMap<String, Vec<Value>> = candidates.iter().filter(|(_,items)| items.len()>1)
            .map(|(id,items)| (id.clone(),items.iter().map(|node| node["location"]["path"].clone()).collect())).collect();
        let duplicates: BTreeSet<String> = candidates.iter().filter(|(_, nodes)| nodes.len() > 1).map(|(id, _)| id.clone()).collect();
        let mut nodes = BTreeMap::new();
        for (id, mut items) in candidates {
            if items.len() == 1 { nodes.insert(id, items.remove(0)); }
            else { report(json!({"kind":"duplicate_id","id":id,"sources":items.iter().map(|node| &node["location"]["path"]).collect::<Vec<_>>()})); }
        }
        let ids: BTreeSet<String> = nodes.keys().cloned().collect();
        for node in nodes.values_mut() {
            let source_id = node["id"].clone();
            for link in node["links"].as_array_mut().unwrap() {
                let target = string(link, "target")?;
                let status = if ids.contains(target) { "resolved" } else if duplicates.contains(target) { "ambiguous" } else { "missing" };
                if status != "resolved" { report(json!({"kind":"broken_link","from":source_id,"target":target,"status":status})); }
                link["status"] = json!(status);
            }
        }
        let index = json!({"format":"yohaku-nodes/1","nodes":nodes,"issues":issues,"issue_count":issue_count});
        atomic(&contained(&self.root, ".yohaku/nodes.json")?, &serde_json::to_vec_pretty(&index).map_err(io)?)?;
        let command = string(request, "command")?;
        let mut result = match command {
            "node_index" => json!({"node_count":nodes.len(),"rebuilt":true}),
            "node_get" => {
                let id = string(request, "id")?;
                json!({"node":nodes.get(id).ok_or("Node ID is missing or ambiguous; rebuild/search and inspect issues")?})
            }
            "node_entries" | "node_search" => {
                let limit = bounded(request, "limit", 20, 100)?;
                let query = if command == "node_search" { string(request, "query")?.to_lowercase() } else { String::new() };
                if command == "node_search" && (query.trim().is_empty() || query.len() > 1000) { return Err("Use a nonempty search query up to 1000 bytes".into()) }
                let matches: Vec<&Value> = nodes.values().filter(|node| {
                    if command == "node_entries" { node["entry"] == true }
                    else { node["name"].as_str().unwrap().to_lowercase().contains(&query) || node["description"].as_str().unwrap().to_lowercase().contains(&query) }
                }).collect();
                json!({"nodes":matches.iter().take(limit).map(|node| summary(node)).collect::<Vec<_>>(),"truncated":matches.len()>limit})
            }
            "node_walk" => {
                let id = string(request, "id")?;
                if !nodes.contains_key(id) { return Err("Start node ID is missing or ambiguous".into()) }
                let depth = bounded(request, "max_depth", 2, 8)?;
                let limit = bounded(request, "limit", 20, 100)?;
                let mut queue = VecDeque::from([(id.to_owned(), 0)]);
                let mut seen = BTreeSet::from([id.to_owned()]);
                let mut found = Vec::new();
                let mut depth_limited = false;
                while found.len() < limit {
                    let Some((current, distance)) = queue.pop_front() else { break };
                    let node = &nodes[&current];
                    found.push(json!({"node":summary(node),"depth":distance}));
                    for link in node["links"].as_array().unwrap() {
                        let target = string(link, "target")?;
                        if link["status"] != "resolved" || seen.contains(target) { continue }
                        if distance == depth { depth_limited = true; continue }
                        seen.insert(target.to_owned());
                        queue.push_back((target.to_owned(), distance+1));
                    }
                }
                json!({"nodes":found,"truncated":!queue.is_empty(),"depth_limited":depth_limited})
            }
            _ => return Err("Unknown node command".into()),
        };
        // Batch lookup for a note result page, reusing this exact active graph.
        // No second graph scanner or persisted note content.
        if command == "node_index" {
            if let Some(requested) = request.get("resolve_ids") {
                let ids = requested.as_array().filter(|v| v.len() <= 100).ok_or("resolve_ids must be an array of at most 100 IDs")?;
                let mut resolved = serde_json::Map::new();
                for value in ids {
                    let id = value.as_str().filter(|s| identifier(s)).ok_or("Invalid resolve ID")?;
                    let value = if let Some(node) = nodes.get(id) {
                        let incoming: Vec<Value> = nodes.values().flat_map(|from| {
                            from["links"].as_array().unwrap().iter().filter(move |link| link["target"] == id)
                                .map(move |link| json!({"id":from["id"],"relation":link["relation"],"source":from["location"]["path"]}))
                        }).collect();
                        json!({"status":"resolved","node":summary(node),"incoming":incoming.iter().take(8).collect::<Vec<_>>(),"incoming_count":incoming.len(),"incoming_truncated":incoming.len()>8})
                    } else if let Some(sources) = duplicate_sources.get(id) {
                        json!({"status":"ambiguous","sources":sources.iter().take(8).collect::<Vec<_>>(),"source_count":sources.len(),"sources_truncated":sources.len()>8})
                    } else { json!({"status":"missing"}) };
                    resolved.insert(id.to_owned(),value);
                }
                result["resolutions"] = json!(resolved);
            }
        }
        result["issues"] = index["issues"].clone();
        result["issue_count"] = index["issue_count"].clone();
        Ok(result)
    }
}
