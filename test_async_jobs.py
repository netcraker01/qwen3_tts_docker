#!/usr/bin/env python3
"""
Script de ejemplo para usar la API de Jobs Asíncronos de Qwen3-TTS.

Este script demuestra cómo:
1. Crear un job de generación de audio
2. Conectarse al stream SSE para recibir progreso en tiempo real
3. Obtener el resultado final

Uso:
    python test_async_jobs.py

Requiere:
    pip install requests sseclient-py
"""

import json
import time
import sys
import requests


def create_job(base_url: str, job_type: str, request_data: dict) -> dict:
    """
    Crea un nuevo job de generación de audio.
    
    Args:
        base_url: URL base de la API
        job_type: Tipo de job (custom_voice, voice_design, voice_clone_url, etc.)
        request_data: Datos específicos del request
    
    Returns:
        Información del job creado
    """
    url = f"{base_url}/api/v1/jobs"
    
    payload = {
        "job_type": job_type,
        "request_data": request_data
    }
    
    print(f"\n{'='*60}")
    print(f"Creando job de tipo: {job_type}")
    print(f"{'='*60}")
    
    response = requests.post(url, json=payload)
    response.raise_for_status()
    
    result = response.json()
    print(f"✅ Job creado exitosamente!")
    print(f"   Job ID: {result['job_id']}")
    print(f"   Status URL: {result['status_url']}")
    print(f"   Stream URL: {result['stream_url']}")
    
    return result


def stream_progress(base_url: str, job_id: str):
    """
    Conecta al stream SSE y muestra el progreso en tiempo real.
    
    Args:
        base_url: URL base de la API
        job_id: ID del job a monitorear
    
    Returns:
        True si se completó exitosamente, False si hubo error
    """
    url = f"{base_url}/api/v1/jobs/{job_id}/stream"
    
    print(f"\n{'='*60}")
    print(f"Conectando al stream de progreso...")
    print(f"{'='*60}\n")
    
    try:
        # Usar sseclient para procesar eventos SSE
        import sseclient
        
        response = requests.get(url, stream=True, headers={'Accept': 'text/event-stream'})
        client = sseclient.SSEClient(response)
        
        result = None
        
        for event in client.events():
            if event.event == 'progress':
                data = json.loads(event.data)
                percent = data.get('percent', 0)
                message = data.get('message', '')
                stage = data.get('stage', '')
                
                # Mostrar barra de progreso
                bar_length = 40
                filled = int(bar_length * percent / 100)
                bar = '█' * filled + '░' * (bar_length - filled)
                
                print(f"\r[{bar}] {percent:3d}% | {stage:15s} | {message}", end='', flush=True)
                
            elif event.event == 'heartbeat':
                # Mantener la conexión viva, no mostrar nada
                pass
                
            elif event.event == 'completed':
                print(f"\n\n{'='*60}")
                print("✅ Job completado exitosamente!")
                print(f"{'='*60}")
                data = json.loads(event.data)
                result = data.get('result', {})
                break
                
            elif event.event == 'error':
                print(f"\n\n{'='*60}")
                print("❌ Error en el job!")
                print(f"{'='*60}")
                data = json.loads(event.data)
                print(f"Error: {data.get('error', 'Desconocido')}")
                return False
                
            elif event.event == 'cancelled':
                print(f"\n\n{'='*60}")
                print("⚠️ Job cancelado")
                print(f"{'='*60}")
                return False
        
        if result:
            print(f"\nResultado:")
            print(f"  - Éxito: {result.get('success')}")
            print(f"  - Modelo usado: {result.get('model_used')}")
            print(f"  - Sample rate: {result.get('sample_rate')} Hz")
            print(f"  - Duración: {result.get('duration_seconds', 0):.2f} segundos")
            print(f"  - Tiempo de procesamiento: {result.get('processing_time_seconds', 0):.2f} segundos")
            
            audio_base64 = result.get('audio_base64')
            if audio_base64:
                print(f"  - Tamaño audio base64: {len(audio_base64)} caracteres")
                
                # Guardar el audio
                import base64
                output_file = f"output_{job_id[:8]}.wav"
                with open(output_file, "wb") as f:
                    f.write(base64.b64decode(audio_base64))
                print(f"\n💾 Audio guardado en: {output_file}")
        
        return True
        
    except ImportError:
        print("⚠️ sseclient-py no instalado. Instalando...")
        print("Ejecuta: pip install sseclient-py")
        return False
    except Exception as e:
        print(f"\n❌ Error en el stream: {e}")
        return False


def get_job_status(base_url: str, job_id: str) -> dict:
    """
    Consulta el estado actual de un job.
    
    Args:
        base_url: URL base de la API
        job_id: ID del job
    
    Returns:
        Información del estado del job
    """
    url = f"{base_url}/api/v1/jobs/{job_id}/status"
    
    response = requests.get(url)
    response.raise_for_status()
    
    return response.json()


def list_jobs(base_url: str, status: str = None) -> list:
    """
    Lista todos los jobs.
    
    Args:
        base_url: URL base de la API
        status: Filtrar por estado (opcional)
    
    Returns:
        Lista de jobs
    """
    url = f"{base_url}/api/v1/jobs"
    
    params = {}
    if status:
        params['status'] = status
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    result = response.json()
    return result.get('jobs', [])


def main():
    """Función principal del script de ejemplo."""
    
    # URL base de la API (cambiar según tu configuración)
    BASE_URL = "http://localhost:8000"
    
    print(f"{'='*60}")
    print("Qwen3-TTS Async Jobs API - Script de Ejemplo")
    print(f"{'='*60}")
    print(f"API URL: {BASE_URL}")
    
    # Verificar que la API está disponible
    try:
        response = requests.get(f"{BASE_URL}/api/v1/health")
        response.raise_for_status()
        health = response.json()
        print(f"Status: {health.get('status', 'unknown')}")
        print(f"CUDA disponible: {health.get('cuda_available', False)}")
    except Exception as e:
        print(f"❌ No se puede conectar a la API: {e}")
        print(f"Asegúrate de que el servidor esté corriendo en {BASE_URL}")
        sys.exit(1)
    
    # Ejemplo 1: Custom Voice
    print("\n\n" + "="*60)
    print("EJEMPLO 1: Generar Custom Voice (Sohee)")
    print("="*60)
    
    custom_voice_request = {
        "text": "¡Hola! Esta es una prueba de generación de audio asíncrono con voz personalizada.",
        "speaker": "Sohee",
        "language": "Spanish",
        "output_format": "wav",
        "temperature": 0.9,
        "top_p": 0.95
    }
    
    job = create_job(BASE_URL, "custom_voice", custom_voice_request)
    job_id = job['job_id']
    
    # Conectar al stream de progreso
    success = stream_progress(BASE_URL, job_id)
    
    if not success:
        print("\nEl job no se completó correctamente.")
    
    # Ejemplo 2: Voice Design
    print("\n\n" + "="*60)
    print("EJEMPLO 2: Diseñar Voz")
    print("="*60)
    
    voice_design_request = {
        "text": "Esta es una voz diseñada específicamente para este mensaje.",
        "voice_description": """gender: Female
pitch: Medium with warm tones
speed: Moderate and natural
age: Young adult
emotion: Friendly and welcoming
tone: Professional yet approachable""",
        "language": "Spanish",
        "output_format": "wav"
    }
    
    job = create_job(BASE_URL, "voice_design", voice_design_request)
    job_id = job['job_id']
    
    success = stream_progress(BASE_URL, job_id)
    
    # Listar jobs
    print("\n\n" + "="*60)
    print("Jobs recientes:")
    print("="*60)
    
    jobs = list_jobs(BASE_URL)
    for j in jobs[:5]:  # Mostrar solo los 5 más recientes
        print(f"  - {j['id'][:8]}... | {j['type']:20s} | {j['status']:12s} | {j['elapsed_seconds']:.1f}s")
    
    print("\n✅ Demo completada!")


if __name__ == "__main__":
    main()