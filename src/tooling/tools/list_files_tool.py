import json
import fnmatch
from pathlib import Path
from typing import List, Dict, Any
from src.tooling.base_tool import BaseTool

class ListFilesTool(BaseTool):
    @property
    def name(self) -> str:
        return "list_files"
    
    @property
    def keywords(self) -> List[str]:
        return [
            "list", "files", "directory", "folder", "find", "search", 
            "explore", "contents", "structure", "ls", "dir", "tree", "filesystem"
        ]
    
    @property
    def signature(self) -> str:
        return "list_files(path: str = '.', pattern: str = '*') -> file_list"
    
    @property
    def description(self) -> str:
        return """
        Lists files and directories in the specified directory ONLY (no recursion).
        
        HARD LIMIT: Maximum 20 files returned to keep LLM context manageable.
        Use pattern matching to find specific files. For nested exploration, 
        call this tool multiple times with different paths.
        
        Features:
        - List files in specified directory only (not subdirectories)
        - Pattern matching with glob syntax (*.py, test_*, *config*)
        - Substring search with name_contains
        - Filter by file extensions
        - Show hidden files (starting with .)
        - Include file details (size, permissions, modified time)
        - Sort options (name, size, date, type)
        
        Exploration Strategy:
        - Start with root directory to see structure
        - Navigate into specific subdirectories as needed
        - Use patterns to find specific file types
        
        Usage Examples:
        - Directory overview: {"path": "src"}
        - Find Python files: {"path": "src", "pattern": "*.py"}
        - Find test files: {"path": "tests", "pattern": "test_*"}
        - Find config files: {"name_contains": "config"}
        - Explore subdirectory: {"path": "src/tooling/tools"}
        
        Arguments:
        - path: Directory path to list (defaults to current directory)
        - pattern: Glob pattern for filename matching (e.g., '*.py', 'test_*')
        - name_contains: Substring to match in filenames (case-insensitive)
        - extensions: Filter by file extensions (e.g., ['.py', '.txt'])
        - show_hidden: Include hidden files/directories
        - show_details: Include file size, permissions, modification time
        - sort_by: Sort by 'name', 'size', 'modified', or 'type'
        """
    
    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string", 
                    "description": "Directory path to list. Defaults to current directory if not provided."
                },
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to match filenames (e.g., '*.py', 'test_*', '*config*'). Use this to find specific files when 20 limit is too restrictive."
                },
                "name_contains": {
                    "type": "string",
                    "description": "Filter files whose names contain this substring (case-insensitive). Alternative to pattern for simple searches."
                },
                "extensions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter files by extensions. Example: ['.py', '.txt', '.md']"
                },
                "show_hidden": {
                    "type": "boolean",
                    "description": "If true, include hidden files and directories (starting with '.')."
                },
                "show_details": {
                    "type": "boolean",
                    "description": "If true, include file details like size, permissions, and modification time."
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["name", "size", "modified", "type"],
                    "description": "Sort files by name, size, modification time, or file type."
                }
            },
            "required": []
        }
    
    @property
    def response_format(self) -> dict:
        return {
            "status": "string",
            "path": "string", 
            "total_items": "number",
            "truncated": "boolean",
            "files": "array"
        }
    
    def execute(self, args: dict) -> str:
        try:
            # Hard limit for LLM context management
            MAX_FILES = 20
            
            # Extract arguments with defaults
            path = args.get("path", ".")
            pattern = args.get("pattern", "*")  # Default to all files
            name_contains = args.get("name_contains", "")
            extensions = args.get("extensions", [])
            show_hidden = args.get("show_hidden", False)
            show_details = args.get("show_details", False)
            sort_by = args.get("sort_by", "name")
            
            # Convert to Path object and resolve
            target_path = Path(path).resolve()
            
            # Validate path exists
            if not target_path.exists():
                return json.dumps({
                    "status": "error",
                    "message": f"Path does not exist: {target_path}"
                })
            
            if not target_path.is_dir():
                return json.dumps({
                    "status": "error",
                    "message": f"Path is not a directory: {target_path}"
                })
            
            # Collect files
            files_data = self._collect_files(
                target_path, show_hidden, show_details, extensions, 
                pattern, name_contains, MAX_FILES
            )
            
            # Sort files
            files_data = self._sort_files(files_data, sort_by)
            
            # Check if we hit the limit
            truncated = len(files_data) >= MAX_FILES
            
            return json.dumps({
                "status": "success",
                "path": str(target_path),
                "total_items": len(files_data),
                "max_files": MAX_FILES,
                "truncated": truncated,
                "truncated_message": f"Results limited to {MAX_FILES} files. Use 'pattern' or 'name_contains' to narrow search." if truncated else None,
                "search_criteria": {
                    "pattern": pattern if pattern != "*" else None,
                    "name_contains": name_contains if name_contains else None,
                    "extensions": extensions if extensions else None
                },
                "files": files_data
            }, indent=2)
            
        except PermissionError as e:
            return json.dumps({
                "status": "error",
                "message": f"Permission denied: {e}"
            })
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Unexpected error: {str(e)}"
            })
    
    def _collect_files(self, path: Path, show_hidden: bool, show_details: bool, 
                      extensions: List[str], pattern: str, name_contains: str, 
                      max_files: int) -> List[Dict[str, Any]]:
        """Collect file information from the specified path only (no recursion)."""
        files_data = []
        files_found = 0
        
        def _should_include_file(item: Path) -> bool:
            """Check if file should be included based on all filters."""
            # Skip hidden files if not requested
            if not show_hidden and item.name.startswith('.'):
                return False
            
            # Apply pattern matching (case-insensitive)
            if not fnmatch.fnmatch(item.name.lower(), pattern.lower()):
                return False
            
            # Apply name contains filter (case-insensitive)
            if name_contains and name_contains.lower() not in item.name.lower():
                return False
            
            # Filter by extensions if specified (only for files)
            if extensions and item.is_file():
                if not any(item.name.lower().endswith(ext.lower()) for ext in extensions):
                    return False
            
            return True
        
        try:
            # Simple directory iteration - no recursion
            items = path.iterdir()
            
            for item in items:
                # Stop if we've found enough files
                if files_found >= max_files:
                    break
                    
                if _should_include_file(item):
                    file_info = self._get_file_info(item, show_details)
                    files_data.append(file_info)
                    files_found += 1
                    
        except PermissionError:
            # Skip directories we can't access
            pass
        
        return files_data
    
    def _get_file_info(self, path: Path, show_details: bool) -> Dict[str, Any]:
        """Extract information about a single file or directory."""
        info = {
            "name": path.name,
            "path": str(path),
            "type": "directory" if path.is_dir() else "file"
        }
        
        if show_details:
            try:
                stat_info = path.stat()
                info.update({
                    "size": stat_info.st_size,
                    "size_human": self._human_readable_size(stat_info.st_size),
                    "modified": stat_info.st_mtime,
                    "modified_human": self._format_timestamp(stat_info.st_mtime),
                    "permissions": oct(stat_info.st_mode)[-3:],
                    "owner_readable": bool(stat_info.st_mode & 0o400),
                    "owner_writable": bool(stat_info.st_mode & 0o200),
                    "owner_executable": bool(stat_info.st_mode & 0o100)
                })
                
                if path.is_file():
                    info["extension"] = path.suffix
                    
            except (OSError, PermissionError):
                info["details_error"] = "Permission denied or file not accessible"
        
        return info
    
    def _sort_files(self, files_data: List[Dict[str, Any]], sort_by: str) -> List[Dict[str, Any]]:
        """Sort files based on the specified criteria."""
        if sort_by == "name":
            return sorted(files_data, key=lambda x: x["name"].lower())
        elif sort_by == "size":
            return sorted(files_data, key=lambda x: x.get("size", 0), reverse=True)
        elif sort_by == "modified":
            return sorted(files_data, key=lambda x: x.get("modified", 0), reverse=True)
        elif sort_by == "type":
            # Sort directories first, then files
            return sorted(files_data, key=lambda x: (x["type"] == "file", x["name"].lower()))
        else:
            return files_data
    
    def _human_readable_size(self, size_bytes: int) -> str:
        """Convert bytes to human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def _format_timestamp(self, timestamp: float) -> str:
        """Format Unix timestamp to readable date."""
        from datetime import datetime
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")