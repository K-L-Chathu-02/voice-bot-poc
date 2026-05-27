import asyncio
import logging

from .config import get_google_api_key, get_mcp_server_url, pick_language
from .session import run_session


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    api_key = get_google_api_key()
    mcp_url = get_mcp_server_url()
    profile = pick_language()
    print(f"\n[Connecting in {profile.name}. Press Ctrl+C to hang up.]\n")
    try:
        asyncio.run(run_session(profile, api_key, mcp_url))
    except KeyboardInterrupt:
        print("\n[Call ended.]")


if __name__ == "__main__":
    main()
