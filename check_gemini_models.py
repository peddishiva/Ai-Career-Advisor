#!/usr/bin/env python3
"""
Check available Gemini models for your API key
"""

import os
import requests
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from backend/.env
load_dotenv(Path("backend/.env"))

def list_gemini_models():
    """List all available Gemini models"""
    api_key = os.getenv('GEMINI_API_KEY')
    
    if not api_key:
        print("❌ GEMINI_API_KEY not found in backend/.env")
        return
    
    print(f"🔍 Checking available models for API key: {api_key[:8]}...{api_key[-4:]}")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            print("\n✅ Available Gemini Models:")
            print("=" * 50)
            
            gemini_models = []
            for model in data.get('models', []):
                if 'gemini' in model.get('name', '').lower():
                    model_name = model.get('name', '').split('/')[-1]
                    display_name = model.get('displayName', 'Unknown')
                    description = model.get('description', 'No description')
                    
                    gemini_models.append({
                        'name': model_name,
                        'display': display_name,
                        'description': description[:80] + '...' if len(description) > 80 else description
                    })
            
            # Sort by name
            gemini_models.sort(key=lambda x: x['name'])
            
            for model in gemini_models:
                print(f"\n📋 {model['name']}")
                print(f"   Display: {model['display']}")
                print(f"   Description: {model['description']}")
            
            # Find the best model for text generation
            text_models = [m for m in gemini_models if 'generateContent' in str(m.get('description', ''))]
            
            if text_models:
                print(f"\n🎯 Recommended model for text generation: {text_models[0]['name']}")
                print(f"   Use this model name in your API calls")
            
        else:
            print(f"❌ Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Details: {error_data.get('error', {}).get('message', 'Unknown error')}")
            except:
                print(f"   Details: {response.text}")
    
    except Exception as e:
        print(f"❌ Error checking models: {str(e)}")

if __name__ == "__main__":
    list_gemini_models()
