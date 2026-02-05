#!/usr/bin/env python3
"""
Script de prueba para Qwen3-TTS Service API
"""

import requests
import base64
import sys
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v1"


def test_health():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()
    return response.status_code == 200


def test_models():
    """Test models info endpoint"""
    print("🔍 Testing models info...")
    response = requests.get(f"{BASE_URL}/models")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Available speakers: {len(data['available_speakers'])}")
    print(f"Supported languages: {len(data['supported_languages'])}")
    print(f"CUDA available: {data['cuda_available']}")
    print()
    return response.status_code == 200


def test_speakers():
    """Test speakers endpoint"""
    print("🔍 Testing speakers endpoint...")
    response = requests.get(f"{BASE_URL}/speakers")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Speakers: {', '.join(data['speakers'][:5])}...")
    print()
    return response.status_code == 200


def test_custom_voice():
    """Test custom voice generation"""
    print("🔍 Testing custom voice generation...")
    print("   (Este test puede tardar 30-60 segundos la primera vez)")
    
    payload = {
        "text": "¡Hola! Esta es una prueba del servicio Qwen3-TTS.",
        "speaker": "Ryan",
        "language": "Spanish",
        "instruction": "Feliz y enérgica",
        "output_format": "wav"
    }
    
    response = requests.post(f"{BASE_URL}/tts/custom", json=payload)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            print(f"✓ Audio generado: {data['duration_seconds']:.2f}s")
            print(f"✓ Modelo usado: {data['model_used']}")
            print(f"✓ Tiempo de procesamiento: {data['processing_time_seconds']:.2f}s")
            
            # Guardar audio
            audio_data = base64.b64decode(data['audio_base64'])
            output_file = "test_output.wav"
            with open(output_file, "wb") as f:
                f.write(audio_data)
            print(f"✓ Audio guardado: {output_file}")
        else:
            print(f"✗ Error: {data.get('error')}")
    else:
        print(f"✗ Error: {response.text}")
    
    print()
    return response.status_code == 200


def main():
    print("=" * 60)
    print("Qwen3-TTS Service API - Test Script")
    print("=" * 60)
    print()
    
    # Check if service is running
    try:
        requests.get(f"{BASE_URL}/health", timeout=2)
    except requests.exceptions.ConnectionError:
        print("❌ Error: No se puede conectar al servicio")
        print("   Asegúrate de que el contenedor esté corriendo:")
        print("   docker-compose up -d")
        sys.exit(1)
    
    tests = [
        ("Health", test_health),
        ("Models", test_models),
        ("Speakers", test_speakers),
        ("Custom Voice", test_custom_voice),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Error en {name}: {e}")
            results.append((name, False))
    
    print("=" * 60)
    print("Resultados de los tests:")
    print("=" * 60)
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    print()
    print(f"Total: {passed}/{total} tests pasados")


if __name__ == "__main__":
    main()