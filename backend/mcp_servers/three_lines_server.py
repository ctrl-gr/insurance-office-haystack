from .company import create_company_server
from .three_lines import SPEC


mcp = create_company_server(SPEC)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
