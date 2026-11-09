"""Bounded literal Rust source references, shared by development snapshots and packaging.
No cfg/feature activation inference; Cargo remains the final dependency resolver.
"""
import re
from pathlib import Path
ATTR=re.compile(r'^\s*#\[\s*path\s*=\s*"([^"]+)"\s*\]',re.M)
INCLUDE=re.compile(r'\binclude(?:_str|_bytes)?!\(\s*"([^"]+)"\s*\)')
def source_closure(package,names):
 package=Path(package).resolve(strict=True);result=set(names);queue=[n for n in result if n.endswith('.rs')]
 while queue:
  name=queue.pop();source=package/name
  text=source.read_text('utf-8')
  for match in list(ATTR.finditer(text))+list(INCLUDE.finditer(text)):
   target=source.parent/match[1]
   if target.is_symlink():raise ValueError('Rust source reference is a symlink: '+name+' -> '+match[1])
   resolved=target.resolve()
   if not resolved.is_relative_to(package):raise ValueError('Rust source reference escapes package: '+name+' -> '+match[1])
   logical=resolved.relative_to(package).as_posix()
   if logical.startswith(('worlds/','.git/')):raise ValueError('Product source must not require a user-world file: '+name+' -> '+logical)
   if not resolved.is_file():raise ValueError('Missing declared Rust source: '+name+' -> '+logical)
   if logical not in result:
    result.add(logical)
    if logical.endswith('.rs'):queue.append(logical)
 return sorted(result)
