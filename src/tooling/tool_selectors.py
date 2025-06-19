from src.tooling.tool_registry import ToolRegistry
from typing import List
    
class KeywordToolSelector:
    """
    Selects tools based on keyword matching and query classification.
    More reliable than embeddings for your current use case.
    """

    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self.tool_keywords = self._build_tool_keywords_from_registry()

    def _build_tool_keywords_from_registry(self) -> dict:
        """Build keyword mapping from all registered tools."""
        tool_keywords = {}
        
        # Get all registered tools dynamically
        all_tools_info = self.tool_registry.get_all_tools_info()
        
        for tool_info in all_tools_info:
            tool_name = tool_info['name']
            tool = self.tool_registry.get_tool(tool_name)
            
            if tool and hasattr(tool, 'keywords'):
                tool_keywords[tool_name] = tool.keywords
    
        return tool_keywords

    def select_relevant_tools(self, query: str, max_tools: int = 3) -> List[dict]:
        """
        Select tools based on keyword matching.
        
        More deterministic and debuggable than embeddings.
        """
        query_lower = query.lower()
        tool_scores = []

        for tool_name, keywords in self.tool_keywords.items():
            # Skip if tool doesn't exist in registry
            if not self.tool_registry.get_tool(tool_name):
                continue

            # Calculate keyword match score
            matches = sum(1 for keyword in keywords if keyword in query_lower)

            score = matches / len(keywords)  # Normalize by keyword count

            if score > 0:  # Only include tools with some relevance
                tool_scores.append((tool_name, score))

        # Sort by relevance and select top tools
        tool_scores.sort(key=lambda x: x[1], reverse=True)
        selected_tools = tool_scores[:max_tools]

        # Always include essential tools if no specific matches
        if not selected_tools:
            # Fallback to most general tools
            return self._get_default_tools(max_tools)
        
        return [
            self.tool_registry.get_tool(tool_name).get_tool_info()
            for tool_name, _ in selected_tools
        ]
    
    def _get_default_tools(self, max_tools: int) -> List[dict]:
        """Fallback tools when no specific matches are found."""
        
        return []

if __name__ == "__main__":
    """
    Test the KeywordToolSelector with sample queries.
    Run with: python -m src.tooling.tool_selectors
    """
    from src.tooling.tools import GetCurrentTimeTool, ListFilesTool

    print("🔧 Testing KeywordToolSelector")
    print("=" * 50)

    # Initialize tool registry
    tool_registry = ToolRegistry()
    tool_registry.register_tool(GetCurrentTimeTool())
    tool_registry.register_tool(ListFilesTool())
    
    # Initialize selector
    selector = KeywordToolSelector(tool_registry)

    # Test queries
    test_queries = [
        "What time is it right now?",
        "List all Python files in the current directory", 
        "Show me the files in the src folder",
        "When was this project created?",
        "Find all .py files",
        "What's the current date and time?",
        "Browse the project structure",
        "This is a random query with no tool keywords",
        "Help me explore the codebase"
    ]

    print("\n📝 Test Results:")
    print("-" * 30)

    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Query: '{query}'")
        
        selected_tools = selector.select_relevant_tools(query, max_tools=2)
        
        if selected_tools:
            print(f"   🎯 Selected tools:")
            for tool in selected_tools:
                print(f"      - {tool['name']}: {tool['signature']}")
        else:
            print("   ❌ No tools selected (using defaults)")
    
    print("\n" + "=" * 50)
    print("🧪 Testing keyword extraction...")

    # Test the keyword matching system
    selector_with_debug = KeywordToolSelector(tool_registry)
    
    query = "List all Python files in the current directory"
    print(f"\nQuery: '{query}'")
    print("Keyword analysis:")
    
    query_lower = query.lower()
    for tool_name, keywords in selector_with_debug.tool_keywords.items():
        matches = [kw for kw in keywords if kw in query_lower]
        score = len(matches) / len(keywords) if keywords else 0
        print(f"  {tool_name}: {matches} (score: {score:.2f})")
    
    print("\n✅ Test completed!")

