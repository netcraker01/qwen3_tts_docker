# Qwen3-TTS C# Client

Cliente .NET moderno para el servicio Qwen3-TTS API. Permite generar voz sintética, clonar voces y gestionar voces clonadas.

## Instalación

Copia `Qwen3TTSClient.cs` a tu proyecto. No requiere dependencias externas más allá de .NET 6+.

## Uso Rápido

```csharp
using Qwen3TTS.Client;

// Crear cliente
using var client = new Qwen3TTSClient("http://192.168.1.235:8080");

// Verificar salud del servicio
var health = await client.GetHealthAsync();
Console.WriteLine($"GPU: {health.GpuName}, Status: {health.Status}");

// Generar voz con personaje preestablecido
var response = await client.GenerateCustomVoiceAsync(new CustomVoiceRequest
{
    Text = "Hola, esta es una prueba de síntesis de voz.",
    Speaker = "Ryan",
    Language = "Spanish",
    ModelSize = "1.7B",
    OutputFormat = "wav"
});

if (response.Success)
{
    // Guardar a archivo
    client.SaveAudioToFile(response, "output.wav");
    
    // O obtener como stream
    using var stream = client.GetAudioStream(response);
    // Procesar stream...
}
```

## Ejemplos por Funcionalidad

### 1. Voz Predefinida (Custom Voice)

```csharp
var request = new CustomVoiceRequest
{
    Text = "Bienvenido al sistema de voz",
    Speaker = "Vivian",  // Ryan, Serena, Uncle_Fu, Dylan, Eric, Aiden, Ono_Anna, Sohee
    Language = "Spanish",
    Instruction = "Habla con entusiasmo",  // Opcional: modifica estilo/emoción
    ModelSize = "1.7B",  // o "0.6B" para más velocidad
    OutputFormat = "wav"  // wav, mp3, ogg
};

var result = await client.GenerateCustomVoiceAsync(request);
```

### 2. Diseñar Voz (Voice Design)

```csharp
var request = new VoiceDesignRequest
{
    Text = "Mensaje importante del sistema",
    VoiceDescription = "gender: Female, pitch: High, speed: Moderate, emotion: Professional",
    Language = "Spanish",
    OutputFormat = "wav"
};

var result = await client.GenerateVoiceDesignAsync(request);
```

### 3. Clonar Voz desde URL

```csharp
var request = new VoiceCloneRequest
{
    Text = "Este es el texto a convertir con la voz clonada",
    RefAudioUrl = "https://ejemplo.com/voz-referencia.mp3",
    RefText = "Texto exacto del audio de referencia",
    Language = "Spanish",
    OutputFormat = "wav"
};

var result = await client.CloneVoiceFromUrlAsync(request);
```

### 4. Clonar Voz desde Archivo

```csharp
// Desde archivo local
var result = await client.CloneVoiceFromFileAsync(
    audioFilePath: @"C:\Audio\referencia.mp3",
    text: "Texto a convertir",
    refText: "Texto del audio de referencia",
    language: "Spanish",
    outputFormat: "wav"
);

// O desde stream
using var stream = File.OpenRead("referencia.mp3");
var result2 = await client.CloneVoiceFromStreamAsync(
    audioStream: stream,
    fileName: "referencia.mp3",
    text: "Texto a convertir",
    refText: "Texto del audio de referencia"
);
```

### 5. Gestión de Voces Clonadas Persistentes

```csharp
// Crear voz persistente
var created = await client.CreateClonedVoiceAsync(new CreateClonedVoiceRequest
{
    Name = "Voz de Juan",
    Description = "Voz clonada de Juan para notificaciones",
    RefAudioUrl = "https://ejemplo.com/juan.mp3",
    RefText = "Hola, soy Juan",
    Language = "Spanish"
});

Console.WriteLine($"Voz creada con ID: {created.Voice.Id}");

// Listar voces guardadas
var voices = await client.GetClonedVoicesAsync();
foreach (var voice in voices.Voices)
{
    Console.WriteLine($"{voice.Name} - Usada {voice.UseCount} veces");
}

// Generar con voz guardada (más rápido que clonar cada vez)
var ttsResult = await client.GenerateFromClonedVoiceAsync(new GenerateFromClonedVoiceRequest
{
    VoiceId = created.Voice.Id,
    Text = "Nuevo mensaje con la voz de Juan",
    Language = "Spanish",
    OutputFormat = "wav"
});

// Actualizar voz
await client.UpdateClonedVoiceAsync(created.Voice.Id, new UpdateClonedVoiceRequest
{
    Name = "Voz de Juan Actualizada",
    Description = "Nueva descripción"
});

// Eliminar voz
await client.DeleteClonedVoiceAsync(created.Voice.Id);
```

## Manejo de Errores

```csharp
try
{
    var result = await client.GenerateCustomVoiceAsync(request);
}
catch (Qwen3TTSException ex)
{
    // Error específico de la API
    Console.WriteLine($"Error {ex.StatusCode}: {ex.Message}");
    if (ex.ResponseContent != null)
    {
        Console.WriteLine($"Respuesta: {ex.ResponseContent}");
    }
}
catch (HttpRequestException ex)
{
    // Error de conexión
    Console.WriteLine($"Error de conexión: {ex.Message}");
}
```

## Información del Sistema

```csharp
// Modelos disponibles
var models = await client.GetModelsInfoAsync();
Console.WriteLine($"GPU: {models.GpuInfo?.Name}");
Console.WriteLine($"VRAM: {models.GpuInfo?.AllocatedMemoryGb}/{models.GpuInfo?.TotalMemoryGb} GB");
Console.WriteLine($"Modelos cargados: {string.Join(", ", models.LoadedModels)}");

// Speakers disponibles
var speakers = await client.GetSpeakersAsync();
foreach (var speaker in speakers.Speakers)
{
    var info = speakers.Details[speaker];
    Console.WriteLine($"{speaker}: {info.Gender}, {info.Language}");
}

// Idiomas soportados
var languages = await client.GetLanguagesAsync();
```

## Características

- ✅ Todas las funcionalidades de la API
- ✅ Async/await completo
- ✅ Manejo de excepciones específico
- ✅ Soporte multipart para upload de archivos
- ✅ Serialización JSON automática
- ✅ IDisposable para liberación de recursos
- ✅ Compatible con .NET 6, 7, 8+
- ✅ Sin dependencias externas (solo System.Net.Http)

## Constantes Útiles

```csharp
// Speakers disponibles
public static readonly string[] Speakers = new[]
{
    "Vivian", "Serena", "Uncle_Fu", "Dylan", 
    "Eric", "Ryan", "Aiden", "Ono_Anna", "Sohee"
};

// Idiomas soportados
public static readonly string[] Languages = new[]
{
    "Spanish", "English", "Chinese", "Japanese", 
    "Korean", "French", "German"
};

// Modelos
public const string ModelLarge = "1.7B";   // Mejor calidad
public const string ModelFast = "0.6B";    // Más rápido

// Formatos
public const string FormatWav = "wav";
public const string FormatMp3 = "mp3";
public const string FormatOgg = "ogg";
```

## Licencia

MIT - Usa este código libremente en tus proyectos.