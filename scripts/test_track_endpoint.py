#!/usr/bin/env python3
"""
Test script to verify Meta track is accessible via CO API endpoints.
"""

import asyncio
import httpx
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000"  # Adjust if running on different port

async def test_list_tracks() -> None:
    """Test GET /v1/tracks endpoint."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/v1/tracks")
            response.raise_for_status()
            data = response.json()
            
            print("✅ GET /v1/tracks successful")
            print(f"   Found {len(data.get('items', []))} tracks")
            
            # Check if Meta track is in the list
            meta_track = None
            for track in data.get("items", []):
                if track.get("slug") == "coding-interview-meta":
                    meta_track = track
                    break
            
            if meta_track:
                print(f"   ✅ Meta track found: {meta_track['title']}")
            else:
                print("   ⚠️  Meta track not found in list")
                
        except httpx.HTTPError as e:
            print(f"❌ GET /v1/tracks failed: {e}")

async def test_get_track_by_slug() -> None:
    """Test GET /v1/tracks/{track_id} endpoint with slug."""
    track_slug = "coding-interview-meta"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/v1/tracks/{track_slug}")
            response.raise_for_status()
            track = response.json()
            
            print(f"\n✅ GET /v1/tracks/{track_slug} successful")
            print(f"   Title: {track['title']}")
            print(f"   Subject: {track['subject']}")
            print(f"   Modules: {len(track.get('modules', []))}")
            print(f"   Labels: {', '.join(track.get('labels', []))}")
            
            # Display module information
            if track.get("modules"):
                print("\n   Modules breakdown:")
                for module in track["modules"]:
                    print(f"     - {module['title']} ({module['id']})")
                    print(f"       Difficulty: {module.get('difficulty_range', 'N/A')}")
                    print(f"       Est. hours: {module.get('estimated_hours', 'N/A')}")
                    
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                print(f"❌ Track '{track_slug}' not found (404)")
                print("   Run 'python scripts/import_meta_track.py' first")
            else:
                print(f"❌ GET /v1/tracks/{track_slug} failed: {e}")
        except httpx.HTTPError as e:
            print(f"❌ GET /v1/tracks/{track_slug} failed: {e}")

async def test_filter_by_subject() -> None:
    """Test filtering tracks by subject."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/v1/tracks?subject=coding")
            response.raise_for_status()
            data = response.json()
            
            print("\n✅ GET /v1/tracks?subject=coding successful")
            print(f"   Found {len(data.get('items', []))} coding tracks")
            
        except httpx.HTTPError as e:
            print(f"❌ GET /v1/tracks?subject=coding failed: {e}")

async def test_filter_by_label() -> None:
    """Test filtering tracks by label."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/v1/tracks?label=company:meta")
            response.raise_for_status()
            data = response.json()
            
            print("\n✅ GET /v1/tracks?label=company:meta successful")
            print(f"   Found {len(data.get('items', []))} Meta tracks")
            
        except httpx.HTTPError as e:
            print(f"❌ GET /v1/tracks?label=company:meta failed: {e}")

async def main():
    """Run all endpoint tests."""
    print("🧪 Testing Curriculum Orchestrator Track Endpoints")
    print("=" * 60)
    print(f"Target: {BASE_URL}")
    print("=" * 60)
    
    # Check if server is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health")
            response.raise_for_status()
            print("✅ Server is healthy\n")
    except httpx.HTTPError:
        print("❌ Server is not running!")
        print("   Start with: uvicorn co.server:app --reload --port 8000")
        return
    
    # Run tests
    await test_list_tracks()
    await test_get_track_by_slug()
    await test_filter_by_subject()
    await test_filter_by_label()
    
    print("\n" + "=" * 60)
    print("🎯 Test Summary:")
    print("   - Track endpoints are working if all tests passed")
    print("   - Run 'python scripts/import_meta_track.py' if track not found")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())