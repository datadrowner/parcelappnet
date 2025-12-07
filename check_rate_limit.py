"""Check API key rate limit status - standalone."""
import asyncio
import aiohttp
import json


async def check_rate_limit():
    """Check if the API key has hit the rate limit."""
    api_key = "_ayJuDtsz9AIYqItWTUZPutUq5xDIdjyPSwVCyALdDPd2Iyk60XImyZ2HXGDzbrHYnR3H7NxwTK"
    api_url = "https://api.parcel.app/external/deliveries/?filter_mode=active"
    
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json",
    }

    try:
        print("Checking API key rate limit status...")
        print(f"API Key: {api_key[:20]}...")
        print(f"Endpoint: {api_url}")
        print()

        async with aiohttp.ClientSession() as session:
            for attempt in range(1, 6):
                print(f"Attempt {attempt}...")
                try:
                    async with session.get(api_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        status = resp.status
                        text = await resp.text()
                        
                        if status == 200:
                            data = await resp.json()
                            print(f"  ✓ Status {status}: Request successful")
                            if data.get("success"):
                                deliveries = data.get("deliveries", [])
                                print(f"    Found {len(deliveries)} deliveries")
                            else:
                                error = data.get("error_message", "Unknown error")
                                print(f"    Error: {error}")
                        elif status == 429:
                            print(f"  ✗ Status {status}: RATE LIMITED")
                            print(f"\n{'='*60}")
                            print(f"⚠️  API KEY HAS REACHED ITS RATE LIMIT!")
                            print(f"Status: HTTP {status} - Too Many Requests")
                            print(f"{'='*60}")
                            print(f"\nResponse: {text}")
                            break
                        else:
                            print(f"  ✗ Status {status}: {text}")
                            
                except asyncio.TimeoutError:
                    print(f"  ✗ Request timeout")
                except Exception as e:
                    print(f"  ✗ Request failed: {e}")
                
                if attempt < 5:
                    await asyncio.sleep(1)

    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(check_rate_limit())
