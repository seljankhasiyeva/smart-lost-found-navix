import asyncio
import os
import time
import httpx
from src.config import settings

# Fetch API configurations from settings (No hardcoding)
API_HOST = settings.http_host
API_PORT = settings.http_port
BASE_URL = f"http://{API_HOST}:{API_PORT}"

# Dynamic resolution of absolute paths for starter kit test images
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOST_IMG = os.path.join(ROOT_DIR, "data", "lost", "keys_silver.png")
FOUND_IMG = os.path.join(ROOT_DIR, "data", "found", "keys_silver_2.png")

async def register_item(client: httpx.AsyncClient, image_path: str, text: str, status: str):
    """Lightweight worker to register a single item via HTTP API."""
    if not os.path.exists(image_path):
        print(f"[ERROR] Test image not found at path: {image_path}")
        return None

    with open(image_path, "rb") as f:
        files = {"image": (os.path.basename(image_path), f, "image/png")}
        data = {"text": text}
        
        response = await client.post(f"{BASE_URL}/items/{status}", files=files, data=data, timeout=10.0)
        if response.status_code == 200:
            item_id = response.json()["item_id"]
            print(f"[SUCCESS] {status.upper()} item registered successfully. Assigned ID: {item_id}")
            return item_id
        return None

async def run_demo():
    print("=== team-NaviX Core Complete Demo ===")
    print(f"[CONFIG] Target API URL base: {BASE_URL}")
    
    async with httpx.AsyncClient() as client:
        # 1. Verify API Health status
        try:
            await client.get(f"{BASE_URL}/items")
        except httpx.ConnectError:
            print(f"[ERROR] Cannot connect to API. Is the FastAPI server running via Uvicorn?")
            return

        # 2. CONCURRENT BATCH REGISTRATION (Demonstrating Day 4/5 Concurrency)
        print("[PROCESS] Dispatching concurrent batch registration via asyncio.gather...")
        start_time = time.time()
        
        tasks = [
            register_item(client, LOST_IMG, "Lost silver keys near the department entrance", "lost"),
            register_item(client, FOUND_IMG, "Found silver keys on the ground near the steps", "found")
        ]
        results = await asyncio.gather(*tasks)
        
        print(f"[BENCHMARK] Parallel batch execution pipeline time: {time.time() - start_time:.2f} seconds.\n")

        # 3. SEMANTIC MATCH SEARCH
        valid_ids = [rid for rid in results if rid is not None]
        if valid_ids:
            target_id = valid_ids[0]
            print(f"[PROCESS] Running semantic similarity search for registered item ID: {target_id}...")
            res = await client.get(f"{BASE_URL}/items/{target_id}/matches?k=2")
            if res.status_code == 200:
                print(f"[RESULTS] Identified cross-pool matches successfully:")
                print(res.json())

if __name__ == "__main__":
    asyncio.run(run_demo())