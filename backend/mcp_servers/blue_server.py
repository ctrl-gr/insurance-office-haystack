from .blue import SPEC
from .company import create_company_server


mcp = create_company_server(SPEC)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
