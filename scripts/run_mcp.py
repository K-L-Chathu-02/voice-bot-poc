import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from slt_mcp_server.server import main

if __name__ == "__main__":
    main()
