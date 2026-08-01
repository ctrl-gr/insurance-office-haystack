from .blue import SPEC
from .company import create_company_server
from backend.mcp_protocol import streamable_http_options


mcp = create_company_server(SPEC)

if __name__ == "__main__":
    mcp.run(**streamable_http_options(SPEC.port))
