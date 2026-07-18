from .company import create_company_server
from .lion import SPEC


mcp = create_company_server(SPEC)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
