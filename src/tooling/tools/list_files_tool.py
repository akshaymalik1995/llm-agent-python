import json
from pathlib import Path
from typing import List, Dict, Any
from src.tooling.base_tool import BaseTool

class ListFilesTool(BaseTool):
    @property
    def name(self) -> str:
        return "list_files"
    
    @property
    def description(self) -> str:
        return """
        Lists files and directories in the specified directory (like 'ls' command).
        
        Features:
        - List files in current directory or specified path
        - Optional recursive listing for nested folders
        - Show hidden files (starting with .)
        - Include file details (size, permissions, modified time)
        - Filter by file extensions
        - Sort options (name, size, date)
        
        Arguments:
        - path: Directory path to list (default: current directory)
        - recursive: Include subdirectories recursively
        - show_hidden: Include hidden files/directories
        - show_details: Include file size, permissions, modification time
        - extensions: Filter by file extensions (e.g., ['.py', '.txt'])
        - sort_by: Sort by 'name', 'size', 'modified', or 'type'
        """
    
    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string", 
                    "description": "Directory path to list. Defaults to current directory if not provided.",
                    "default": "."
                },
                "recursive": {
                    "type": "boolean",
                    "description": "If true, list files recursively in subdirectories.",
                    "default": False
                },
                "show_hidden": {
                    "type": "boolean",
                    "description": "If true, include hidden files and directories (starting with '.').",
                    "default": False
                },
                "show_details": {
                    "type": "boolean",
                    "description": "If true, include file details like size, permissions, and modification time.",
                    "default": False
                },
                "extensions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter files by extensions. Example: ['.py', '.txt', '.md']",
                    "default": []
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["name", "size", "modified", "type"],
                    "description": "Sort files by name, size, modification time, or file type.",
                    "default": "name"
                }
            },
            "required": []
        }
    
    def execute(self, args: dict) -> str:
        try:
            # Extract arguments with defaults
            path = args.get("path", ".")
            recursive = args.get("recursive", False)
            show_hidden = args.get("show_hidden", False)
            show_details = args.get("show_details", False)
            extensions = args.get("extensions", [])
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
                target_path, recursive, show_hidden, show_details, extensions
            )
            
            # Sort files
            files_data = self._sort_files(files_data, sort_by)
            
            return json.dumps({
                "status": "success",
                "path": str(target_path),
                "total_items": len(files_data),
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
    
    def _collect_files(self, path: Path, recursive: bool, show_hidden: bool, 
                      show_details: bool, extensions: List[str]) -> List[Dict[str, Any]]:
        """Collect file information from the specified path."""
        files_data = []
        
        try:
            # Choose iteration method based on recursive flag
            if recursive:
                pattern = "**/*" if show_hidden else "**/[!.]*"
                items = path.glob(pattern)
            else:
                items = path.iterdir()
            
            for item in items:
                # Skip hidden files if not requested
                if not show_hidden and item.name.startswith('.'):
                    continue
                
                # Filter by extensions if specified
                if extensions and item.is_file():
                    if not any(item.name.lower().endswith(ext.lower()) for ext in extensions):
                        continue
                
                file_info = self._get_file_info(item, show_details)
                files_data.append(file_info)
                
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