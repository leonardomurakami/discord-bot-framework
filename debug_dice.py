#!/usr/bin/env python3

import asyncio
import aiohttp

async def debug_dice_api():
    """Debug the dice API response"""
    print("Testing dice API response...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("http://127.0.0.1:8082/plugin/fun/api/roll", data={"dice": "2d6"}) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    print(f"Response content: '{content}'")
                    print(f"Contains 'rolled': {'rolled' in content.lower()}")
                    print(f"Contains 'total': {'total' in content.lower()}")
                    print(f"Response length: {len(content)}")
                else:
                    print(f"Status: {resp.status}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(debug_dice_api())