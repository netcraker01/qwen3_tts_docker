using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading;
using System.Threading.Tasks;

namespace Qwen3TTS.Client
{
    /// <summary>
    /// Cliente .NET para el servicio Qwen3-TTS API
    /// Permite generar voz sintética, clonar voces y diseñar voces personalizadas.
    /// </summary>
    public class Qwen3TTSClient : IDisposable
    {
        private readonly HttpClient _httpClient;
        private readonly JsonSerializerOptions _jsonOptions;
        private bool _disposed;

        /// <summary>
        /// Crea una nueva instancia del cliente Qwen3-TTS
        /// </summary>
        /// <param name="baseUrl">URL base del servicio (ej: http://192.168.1.235:8080)</param>
        public Qwen3TTSClient(string baseUrl)
        {
            _httpClient = new HttpClient
            {
                BaseAddress = new Uri(baseUrl.TrimEnd('/') + "/api/v1/"),
                Timeout = TimeSpan.FromMinutes(5) // Operaciones de TTS pueden tomar tiempo
            };

            _jsonOptions = new JsonSerializerOptions
            {
                PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
                DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
                WriteIndented = false
            };
        }

        /// <summary>
        /// Crea una nueva instancia del cliente con HttpClient personalizado
        /// </summary>
        public Qwen3TTSClient(HttpClient httpClient)
        {
            _httpClient = httpClient ?? throw new ArgumentNullException(nameof(httpClient));
            
            _jsonOptions = new JsonSerializerOptions
            {
                PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
                DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
            };
        }

        #region Health & Info

        /// <summary>
        /// Verifica el estado de salud del servicio
        /// </summary>
        public async Task<HealthResponse> GetHealthAsync(CancellationToken cancellationToken = default)
        {
            return await GetAsync<HealthResponse>("health", cancellationToken);
        }

        /// <summary>
        /// Obtiene información de modelos disponibles y estado del sistema
        /// </summary>
        public async Task<ModelsInfoResponse> GetModelsInfoAsync(CancellationToken cancellationToken = default)
        {
            return await GetAsync<ModelsInfoResponse>("models", cancellationToken);
        }

        /// <summary>
        /// Lista los speakers disponibles para Custom Voice
        /// </summary>
        public async Task<SpeakersResponse> GetSpeakersAsync(CancellationToken cancellationToken = default)
        {
            return await GetAsync<SpeakersResponse>("speakers", cancellationToken);
        }

        /// <summary>
        /// Lista los idiomas soportados
        /// </summary>
        public async Task<LanguagesResponse> GetLanguagesAsync(CancellationToken cancellationToken = default)
        {
            return await GetAsync<LanguagesResponse>("languages", cancellationToken);
        }

        #endregion

        #region Text-to-Speech

        /// <summary>
        /// Genera voz usando un personaje preestablecido
        /// </summary>
        /// <param name="request">Parámetros de generación</param>
        public async Task<TTSResponse> GenerateCustomVoiceAsync(CustomVoiceRequest request, CancellationToken cancellationToken = default)
        {
            return await PostAsync<CustomVoiceRequest, TTSResponse>("tts/custom", request, cancellationToken);
        }

        /// <summary>
        /// Genera voz usando un personaje preestablecido y guarda en archivo
        /// </summary>
        public async Task<TTSResponse> GenerateCustomVoiceFileAsync(CustomVoiceRequest request, CancellationToken cancellationToken = default)
        {
            return await PostAsync<CustomVoiceRequest, TTSResponse>("tts/custom/file", request, cancellationToken);
        }

        /// <summary>
        /// Diseña una voz personalizada mediante descripción de texto
        /// </summary>
        /// <param name="request">Descripción de la voz y texto a convertir</param>
        public async Task<TTSResponse> GenerateVoiceDesignAsync(VoiceDesignRequest request, CancellationToken cancellationToken = default)
        {
            return await PostAsync<VoiceDesignRequest, TTSResponse>("tts/design", request, cancellationToken);
        }

        #endregion

        #region Voice Cloning

        /// <summary>
        /// Clona una voz desde una URL de audio y genera texto
        /// </summary>
        /// <param name="request">URL del audio de referencia y texto</param>
        public async Task<TTSResponse> CloneVoiceFromUrlAsync(VoiceCloneRequest request, CancellationToken cancellationToken = default)
        {
            return await PostAsync<VoiceCloneRequest, TTSResponse>("tts/clone/url", request, cancellationToken);
        }

        /// <summary>
        /// Clona una voz subiendo un archivo de audio
        /// </summary>
        /// <param name="audioFilePath">Ruta al archivo de audio local</param>
        /// <param name="text">Texto a convertir</param>
        /// <param name="refText">Texto del audio de referencia</param>
        /// <param name="language">Idioma (default: Spanish)</param>
        /// <param name="outputFormat">Formato de salida (wav, mp3, ogg)</param>
        public async Task<TTSResponse> CloneVoiceFromFileAsync(
            string audioFilePath,
            string text,
            string refText,
            string language = "Spanish",
            string outputFormat = "wav",
            CancellationToken cancellationToken = default)
        {
            if (!File.Exists(audioFilePath))
                throw new FileNotFoundException("Audio file not found", audioFilePath);

            using var content = new MultipartFormDataContent();
            
            // Agregar archivo
            var fileStream = File.OpenRead(audioFilePath);
            var fileContent = new StreamContent(fileStream);
            fileContent.Headers.ContentType = new MediaTypeHeaderValue("audio/mpeg");
            content.Add(fileContent, "ref_audio", Path.GetFileName(audioFilePath));
            
            // Agregar campos de texto
            content.Add(new StringContent(text), "text");
            content.Add(new StringContent(refText), "ref_text");
            content.Add(new StringContent(language), "language");
            content.Add(new StringContent(outputFormat), "output_format");

            var response = await _httpClient.PostAsync("tts/clone/upload", content, cancellationToken);
            return await HandleResponseAsync<TTSResponse>(response);
        }

        /// <summary>
        /// Clona una voz desde un stream de audio
        /// </summary>
        public async Task<TTSResponse> CloneVoiceFromStreamAsync(
            Stream audioStream,
            string fileName,
            string text,
            string refText,
            string language = "Spanish",
            string outputFormat = "wav",
            CancellationToken cancellationToken = default)
        {
            using var content = new MultipartFormDataContent();
            
            var fileContent = new StreamContent(audioStream);
            fileContent.Headers.ContentType = new MediaTypeHeaderValue("audio/mpeg");
            content.Add(fileContent, "ref_audio", fileName);
            
            content.Add(new StringContent(text), "text");
            content.Add(new StringContent(refText), "ref_text");
            content.Add(new StringContent(language), "language");
            content.Add(new StringContent(outputFormat), "output_format");

            var response = await _httpClient.PostAsync("tts/clone/upload", content, cancellationToken);
            return await HandleResponseAsync<TTSResponse>(response);
        }

        #endregion

        #region Cloned Voices Management

        /// <summary>
        /// Crea una voz clonada persistente para uso futuro
        /// </summary>
        public async Task<CreateClonedVoiceResponse> CreateClonedVoiceAsync(CreateClonedVoiceRequest request, CancellationToken cancellationToken = default)
        {
            return await PostAsync<CreateClonedVoiceRequest, CreateClonedVoiceResponse>("cloned-voices", request, cancellationToken);
        }

        /// <summary>
        /// Lista todas las voces clonadas guardadas
        /// </summary>
        public async Task<ClonedVoiceListResponse> GetClonedVoicesAsync(CancellationToken cancellationToken = default)
        {
            return await GetAsync<ClonedVoiceListResponse>("cloned-voices", cancellationToken);
        }

        /// <summary>
        /// Obtiene información de una voz clonada específica
        /// </summary>
        public async Task<ClonedVoiceResponse> GetClonedVoiceAsync(string voiceId, CancellationToken cancellationToken = default)
        {
            return await GetAsync<ClonedVoiceResponse>($"cloned-voices/{voiceId}", cancellationToken);
        }

        /// <summary>
        /// Actualiza el nombre o descripción de una voz clonada
        /// </summary>
        public async Task<UpdateClonedVoiceResponse> UpdateClonedVoiceAsync(string voiceId, UpdateClonedVoiceRequest request, CancellationToken cancellationToken = default)
        {
            return await PutAsync<UpdateClonedVoiceRequest, UpdateClonedVoiceResponse>($"cloned-voices/{voiceId}", request, cancellationToken);
        }

        /// <summary>
        /// Elimina permanentemente una voz clonada
        /// </summary>
        public async Task<DeleteResponse> DeleteClonedVoiceAsync(string voiceId, CancellationToken cancellationToken = default)
        {
            return await DeleteAsync<DeleteResponse>($"cloned-voices/{voiceId}", cancellationToken);
        }

        /// <summary>
        /// Genera audio usando una voz clonada guardada
        /// </summary>
        public async Task<TTSResponse> GenerateFromClonedVoiceAsync(GenerateFromClonedVoiceRequest request, CancellationToken cancellationToken = default)
        {
            return await PostAsync<GenerateFromClonedVoiceRequest, TTSResponse>("tts/cloned-voice/generate", request, cancellationToken);
        }

        /// <summary>
        /// Obtiene estadísticas de uso de las voces clonadas
        /// </summary>
        public async Task<ClonedVoiceStatsResponse> GetClonedVoicesStatsAsync(CancellationToken cancellationToken = default)
        {
            return await GetAsync<ClonedVoiceStatsResponse>("cloned-voices/stats", cancellationToken);
        }

        #endregion

        #region Utilities

        /// <summary>
        /// Descarga un archivo de audio generado previamente
        /// </summary>
        public async Task<byte[]> DownloadFileAsync(string filename, CancellationToken cancellationToken = default)
        {
            var response = await _httpClient.GetAsync($"download/{filename}", cancellationToken);
            response.EnsureSuccessStatusCode();
            return await response.Content.ReadAsByteArrayAsync();
        }

        /// <summary>
        /// Guarda el audio de una respuesta TTS a un archivo
        /// </summary>
        public void SaveAudioToFile(TTSResponse response, string filePath)
        {
            if (!response.Success || string.IsNullOrEmpty(response.AudioBase64))
                throw new InvalidOperationException("No audio data available");

            var audioBytes = Convert.FromBase64String(response.AudioBase64);
            File.WriteAllBytes(filePath, audioBytes);
        }

        /// <summary>
        /// Obtiene un stream de audio desde una respuesta TTS
        /// </summary>
        public Stream GetAudioStream(TTSResponse response)
        {
            if (!response.Success || string.IsNullOrEmpty(response.AudioBase64))
                throw new InvalidOperationException("No audio data available");

            var audioBytes = Convert.FromBase64String(response.AudioBase64);
            return new MemoryStream(audioBytes);
        }

        #endregion

        #region Helper Methods

        private async Task<T> GetAsync<T>(string endpoint, CancellationToken cancellationToken)
        {
            var response = await _httpClient.GetAsync(endpoint, cancellationToken);
            return await HandleResponseAsync<T>(response);
        }

        private async Task<TResponse> PostAsync<TRequest, TResponse>(string endpoint, TRequest data, CancellationToken cancellationToken)
        {
            var json = JsonSerializer.Serialize(data, _jsonOptions);
            var content = new StringContent(json, Encoding.UTF8, "application/json");
            var response = await _httpClient.PostAsync(endpoint, content, cancellationToken);
            return await HandleResponseAsync<TResponse>(response);
        }

        private async Task<TResponse> PutAsync<TRequest, TResponse>(string endpoint, TRequest data, CancellationToken cancellationToken)
        {
            var json = JsonSerializer.Serialize(data, _jsonOptions);
            var content = new StringContent(json, Encoding.UTF8, "application/json");
            var response = await _httpClient.PutAsync(endpoint, content, cancellationToken);
            return await HandleResponseAsync<TResponse>(response);
        }

        private async Task<T> DeleteAsync<T>(string endpoint, CancellationToken cancellationToken)
        {
            var response = await _httpClient.DeleteAsync(endpoint, cancellationToken);
            return await HandleResponseAsync<T>(response);
        }

        private async Task<T> HandleResponseAsync<T>(HttpResponseMessage response)
        {
            var content = await response.Content.ReadAsStringAsync();
            
            if (!response.IsSuccessStatusCode)
            {
                throw new Qwen3TTSException(
                    $"API request failed: {response.StatusCode}", 
                    (int)response.StatusCode,
                    content);
            }

            try
            {
                return JsonSerializer.Deserialize<T>(content, _jsonOptions) 
                    ?? throw new JsonException("Deserialization returned null");
            }
            catch (JsonException ex)
            {
                throw new Qwen3TTSException(
                    $"Failed to deserialize response: {ex.Message}", 
                    (int)response.StatusCode,
                    content);
            }
        }

        #endregion

        #region IDisposable

        public void Dispose()
        {
            if (!_disposed)
            {
                _httpClient?.Dispose();
                _disposed = true;
            }
        }

        #endregion
    }

    #region Models

    // Request Models
    public class CustomVoiceRequest
    {
        [JsonPropertyName("text")]
        public string Text { get; set; } = string.Empty;

        [JsonPropertyName("speaker")]
        public string Speaker { get; set; } = "Ryan";

        [JsonPropertyName("language")]
        public string Language { get; set; } = "Spanish";

        [JsonPropertyName("instruction")]
        public string? Instruction { get; set; }

        [JsonPropertyName("model_size")]
        public string ModelSize { get; set; } = "1.7B";

        [JsonPropertyName("output_format")]
        public string OutputFormat { get; set; } = "wav";
    }

    public class VoiceDesignRequest
    {
        [JsonPropertyName("text")]
        public string Text { get; set; } = string.Empty;

        [JsonPropertyName("voice_description")]
        public string VoiceDescription { get; set; } = string.Empty;

        [JsonPropertyName("language")]
        public string Language { get; set; } = "Spanish";

        [JsonPropertyName("output_format")]
        public string OutputFormat { get; set; } = "wav";
    }

    public class VoiceCloneRequest
    {
        [JsonPropertyName("text")]
        public string Text { get; set; } = string.Empty;

        [JsonPropertyName("ref_audio_url")]
        public string RefAudioUrl { get; set; } = string.Empty;

        [JsonPropertyName("ref_text")]
        public string RefText { get; set; } = string.Empty;

        [JsonPropertyName("language")]
        public string Language { get; set; } = "Spanish";

        [JsonPropertyName("output_format")]
        public string OutputFormat { get; set; } = "wav";
    }

    public class CreateClonedVoiceRequest
    {
        [JsonPropertyName("name")]
        public string Name { get; set; } = string.Empty;

        [JsonPropertyName("description")]
        public string? Description { get; set; }

        [JsonPropertyName("ref_audio_url")]
        public string RefAudioUrl { get; set; } = string.Empty;

        [JsonPropertyName("ref_text")]
        public string RefText { get; set; } = string.Empty;

        [JsonPropertyName("language")]
        public string Language { get; set; } = "Spanish";
    }

    public class UpdateClonedVoiceRequest
    {
        [JsonPropertyName("name")]
        public string Name { get; set; } = string.Empty;

        [JsonPropertyName("description")]
        public string? Description { get; set; }
    }

    public class GenerateFromClonedVoiceRequest
    {
        [JsonPropertyName("voice_id")]
        public string VoiceId { get; set; } = string.Empty;

        [JsonPropertyName("text")]
        public string Text { get; set; } = string.Empty;

        [JsonPropertyName("language")]
        public string? Language { get; set; }

        [JsonPropertyName("output_format")]
        public string OutputFormat { get; set; } = "wav";
    }

    // Response Models
    public class TTSResponse
    {
        [JsonPropertyName("success")]
        public bool Success { get; set; }

        [JsonPropertyName("audio_base64")]
        public string? AudioBase64 { get; set; }

        [JsonPropertyName("audio_url")]
        public string? AudioUrl { get; set; }

        [JsonPropertyName("sample_rate")]
        public int SampleRate { get; set; }

        [JsonPropertyName("duration_seconds")]
        public double DurationSeconds { get; set; }

        [JsonPropertyName("model_used")]
        public string ModelUsed { get; set; } = string.Empty;

        [JsonPropertyName("processing_time_seconds")]
        public double ProcessingTimeSeconds { get; set; }

        [JsonPropertyName("error")]
        public string? Error { get; set; }
    }

    public class HealthResponse
    {
        [JsonPropertyName("status")]
        public string Status { get; set; } = string.Empty;

        [JsonPropertyName("cuda_available")]
        public bool CudaAvailable { get; set; }

        [JsonPropertyName("models_loaded")]
        public List<string> ModelsLoaded { get; set; } = new();

        [JsonPropertyName("default_model_size")]
        public string DefaultModelSize { get; set; } = string.Empty;

        [JsonPropertyName("gpu_name")]
        public string? GpuName { get; set; }
    }

    public class GpuInfo
    {
        [JsonPropertyName("name")]
        public string Name { get; set; } = string.Empty;

        [JsonPropertyName("total_memory_gb")]
        public double TotalMemoryGb { get; set; }

        [JsonPropertyName("allocated_memory_gb")]
        public double AllocatedMemoryGb { get; set; }

        [JsonPropertyName("reserved_memory_gb")]
        public double ReservedMemoryGb { get; set; }
    }

    public class ModelsInfoResponse
    {
        [JsonPropertyName("available_models")]
        public Dictionary<string, Dictionary<string, string>> AvailableModels { get; set; } = new();

        [JsonPropertyName("available_speakers")]
        public List<string> AvailableSpeakers { get; set; } = new();

        [JsonPropertyName("supported_languages")]
        public List<string> SupportedLanguages { get; set; } = new();

        [JsonPropertyName("loaded_models")]
        public List<string> LoadedModels { get; set; } = new();

        [JsonPropertyName("cuda_available")]
        public bool CudaAvailable { get; set; }

        [JsonPropertyName("gpu_info")]
        public GpuInfo? GpuInfo { get; set; }
    }

    public class SpeakerInfo
    {
        [JsonPropertyName("gender")]
        public string Gender { get; set; } = string.Empty;

        [JsonPropertyName("language")]
        public string Language { get; set; } = string.Empty;

        [JsonPropertyName("style")]
        public string Style { get; set; } = string.Empty;
    }

    public class SpeakersResponse
    {
        [JsonPropertyName("speakers")]
        public List<string> Speakers { get; set; } = new();

        [JsonPropertyName("details")]
        public Dictionary<string, SpeakerInfo> Details { get; set; } = new();
    }

    public class LanguagesResponse
    {
        [JsonPropertyName("languages")]
        public List<string> Languages { get; set; } = new();

        [JsonPropertyName("notes")]
        public string Notes { get; set; } = string.Empty;
    }

    public class ClonedVoice
    {
        [JsonPropertyName("id")]
        public string Id { get; set; } = string.Empty;

        [JsonPropertyName("name")]
        public string Name { get; set; } = string.Empty;

        [JsonPropertyName("description")]
        public string? Description { get; set; }

        [JsonPropertyName("ref_audio_path")]
        public string RefAudioPath { get; set; } = string.Empty;

        [JsonPropertyName("ref_text")]
        public string RefText { get; set; } = string.Empty;

        [JsonPropertyName("language")]
        public string Language { get; set; } = string.Empty;

        [JsonPropertyName("created_at")]
        public string CreatedAt { get; set; } = string.Empty;

        [JsonPropertyName("last_used")]
        public string? LastUsed { get; set; }

        [JsonPropertyName("use_count")]
        public int UseCount { get; set; }
    }

    public class ClonedVoiceListResponse
    {
        [JsonPropertyName("voices")]
        public List<ClonedVoice> Voices { get; set; } = new();

        [JsonPropertyName("total")]
        public int Total { get; set; }
    }

    public class ClonedVoiceResponse
    {
        [JsonPropertyName("voice")]
        public ClonedVoice Voice { get; set; } = new();
    }

    public class CreateClonedVoiceResponse
    {
        [JsonPropertyName("success")]
        public bool Success { get; set; }

        [JsonPropertyName("voice")]
        public ClonedVoice Voice { get; set; } = new();

        [JsonPropertyName("message")]
        public string Message { get; set; } = string.Empty;
    }

    public class UpdateClonedVoiceResponse
    {
        [JsonPropertyName("success")]
        public bool Success { get; set; }

        [JsonPropertyName("voice")]
        public ClonedVoice Voice { get; set; } = new();

        [JsonPropertyName("message")]
        public string Message { get; set; } = string.Empty;
    }

    public class DeleteResponse
    {
        [JsonPropertyName("success")]
        public bool Success { get; set; }

        [JsonPropertyName("message")]
        public string Message { get; set; } = string.Empty;
    }

    public class ClonedVoiceStatsResponse
    {
        [JsonPropertyName("total_voices")]
        public int TotalVoices { get; set; }

        [JsonPropertyName("most_used")]
        public ClonedVoice? MostUsed { get; set; }

        [JsonPropertyName("recently_created")]
        public List<ClonedVoice> RecentlyCreated { get; set; } = new();
    }

    #endregion

    #region Exceptions

    /// <summary>
    /// Excepción específica para errores del servicio Qwen3-TTS
    /// </summary>
    public class Qwen3TTSException : Exception
    {
        public int StatusCode { get; }
        public string? ResponseContent { get; }

        public Qwen3TTSException(string message, int statusCode, string? responseContent = null) 
            : base(message)
        {
            StatusCode = statusCode;
            ResponseContent = responseContent;
        }
    }

    #endregion
}