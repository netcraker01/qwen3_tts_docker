#!/bin/bash

# Script de gestión de volúmenes persistentes para Qwen3-TTS
# Facilita backup, restore y gestión de las voces clonadas

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Nombre de los volúmenes
DATA_VOLUME="qwen3_tts_data"
OUTPUT_VOLUME="qwen3_tts_output"
BACKUP_DIR="./backups"

# Funciones de utilidad
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Verificar que Docker está disponible
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker no está instalado"
        exit 1
    fi
}

# Mostrar información de los volúmenes
show_info() {
    print_header "Información de Volúmenes"
    
    echo -e "\n${YELLOW}Volúmenes Docker:${NC}"
    docker volume ls | grep qwen3 || echo "No se encontraron volúmenes qwen3*"
    
    echo -e "\n${YELLOW}Detalles del volumen de datos (${DATA_VOLUME}):${NC}"
    if docker volume inspect "$DATA_VOLUME" &> /dev/null; then
        docker volume inspect "$DATA_VOLUME" --format='  - Nombre: {{.Name}}\n  - Driver: {{.Driver}}\n  - Mountpoint: {{.Mountpoint}}'
        
        echo -e "\n  Contenido:"
        docker run --rm -v "${DATA_VOLUME}:/data" busybox ls -la /data 2>/dev/null || echo "    (volumen vacío o no accesible)"
    else
        print_warning "El volumen ${DATA_VOLUME} no existe"
    fi
    
    echo -e "\n${YELLOW}Detalles del volumen de output (${OUTPUT_VOLUME}):${NC}"
    if docker volume inspect "$OUTPUT_VOLUME" &> /dev/null; then
        docker volume inspect "$OUTPUT_VOLUME" --format='  - Nombre: {{.Name}}\n  - Driver: {{.Driver}}\n  - Mountpoint: {{.Mountpoint}}'
        
        echo -e "\n  Contenido:"
        docker run --rm -v "${OUTPUT_VOLUME}:/output" busybox ls -la /output 2>/dev/null || echo "    (volumen vacío o no accesible)"
    else
        print_warning "El volumen ${OUTPUT_VOLUME} no existe"
    fi
}

# Backup de volúmenes
backup_volumes() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_name="${1:-backup_${timestamp}}"
    
    print_header "Creando Backup: ${backup_name}"
    
    # Crear directorio de backups si no existe
    mkdir -p "${BACKUP_DIR}"
    
    # Backup del volumen de datos
    echo -e "\n${YELLOW}Respaldando voces clonadas...${NC}"
    if docker volume inspect "$DATA_VOLUME" &> /dev/null; then
        docker run --rm \
            -v "${DATA_VOLUME}:/data:ro" \
            -v "$(realpath ${BACKUP_DIR}):/backup" \
            busybox tar czf "/backup/${backup_name}_data.tar.gz" -C / data
        print_success "Backup de datos creado: ${BACKUP_DIR}/${backup_name}_data.tar.gz"
    else
        print_warning "El volumen ${DATA_VOLUME} no existe, omitiendo..."
    fi
    
    # Backup del volumen de output
    echo -e "\n${YELLOW}Respaldando archivos generados...${NC}"
    if docker volume inspect "$OUTPUT_VOLUME" &> /dev/null; then
        docker run --rm \
            -v "${OUTPUT_VOLUME}:/output:ro" \
            -v "$(realpath ${BACKUP_DIR}):/backup" \
            busybox tar czf "/backup/${backup_name}_output.tar.gz" -C / output
        print_success "Backup de output creado: ${BACKUP_DIR}/${backup_name}_output.tar.gz"
    else
        print_warning "El volumen ${OUTPUT_VOLUME} no existe, omitiendo..."
    fi
    
    echo -e "\n${GREEN}Backup completado exitosamente!${NC}"
    echo -e "Archivos creados en: ${BACKUP_DIR}/"
    ls -lh "${BACKUP_DIR}/${backup_name}"*.tar.gz 2>/dev/null || true
}

# Restaurar volúmenes
restore_volumes() {
    local backup_name="$1"
    
    if [ -z "$backup_name" ]; then
        print_error "Debes especificar el nombre del backup"
        echo "Uso: $0 restore <nombre_backup>"
        echo ""
        echo "Backups disponibles:"
        ls -1 "${BACKUP_DIR}"/*.tar.gz 2>/dev/null | xargs -n1 basename | sed 's/_data.tar.gz//;s/_output.tar.gz//' | sort -u | sed 's/^/  - /' || echo "  (ninguno)"
        exit 1
    fi
    
    print_header "Restaurando Backup: ${backup_name}"
    
    # Verificar archivos de backup
    local data_backup="${BACKUP_DIR}/${backup_name}_data.tar.gz"
    local output_backup="${BACKUP_DIR}/${backup_name}_output.tar.gz"
    
    # Confirmar antes de restaurar
    print_warning "Esta operación SOBRESCRIBIRÁ los datos existentes"
    read -p "¿Estás seguro? Escribe 'yes' para continuar: " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Operación cancelada"
        exit 0
    fi
    
    # Restaurar datos
    if [ -f "$data_backup" ]; then
        echo -e "\n${YELLOW}Restaurando voces clonadas...${NC}"
        
        # Eliminar volumen existente si existe
        docker volume rm "$DATA_VOLUME" 2>/dev/null || true
        docker volume create "$DATA_VOLUME"
        
        # Restaurar
        docker run --rm \
            -v "${DATA_VOLUME}:/data" \
            -v "$(realpath ${BACKUP_DIR}):/backup:ro" \
            busybox tar xzf "/backup/${backup_name}_data.tar.gz" -C /
        print_success "Datos restaurados correctamente"
    else
        print_warning "No se encontró backup de datos: ${data_backup}"
    fi
    
    # Restaurar output
    if [ -f "$output_backup" ]; then
        echo -e "\n${YELLOW}Restaurando archivos generados...${NC}"
        
        # Eliminar volumen existente si existe
        docker volume rm "$OUTPUT_VOLUME" 2>/dev/null || true
        docker volume create "$OUTPUT_VOLUME"
        
        # Restaurar
        docker run --rm \
            -v "${OUTPUT_VOLUME}:/output" \
            -v "$(realpath ${BACKUP_DIR}):/backup:ro" \
            busybox tar xzf "/backup/${backup_name}_output.tar.gz" -C /
        print_success "Output restaurado correctamente"
    else
        print_warning "No se encontró backup de output: ${output_backup}"
    fi
    
    echo -e "\n${GREEN}Restauración completada!${NC}"
}

# Listar backups disponibles
list_backups() {
    print_header "Backups Disponibles"
    
    if [ ! -d "$BACKUP_DIR" ] || [ -z "$(ls -A ${BACKUP_DIR}/*.tar.gz 2>/dev/null)" ]; then
        echo "No hay backups disponibles en: ${BACKUP_DIR}/"
        return
    fi
    
    echo -e "\n${YELLOW}Backups encontrados:${NC}\n"
    
    # Obtener lista única de nombres de backup
    for backup in $(ls -1 "${BACKUP_DIR}"/*.tar.gz 2>/dev/null | xargs -n1 basename | sed 's/_data.tar.gz//;s/_output.tar.gz//' | sort -u); do
        local data_size=""
        local output_size=""
        
        [ -f "${BACKUP_DIR}/${backup}_data.tar.gz" ] && data_size=$(du -h "${BACKUP_DIR}/${backup}_data.tar.gz" | cut -f1)
        [ -f "${BACKUP_DIR}/${backup}_output.tar.gz" ] && output_size=$(du -h "${BACKUP_DIR}/${backup}_output.tar.gz" | cut -f1)
        
        echo "  📦 ${backup}"
        [ -n "$data_size" ] && echo "     └─ Datos: ${data_size}"
        [ -n "$output_size" ] && echo "     └─ Output: ${output_size}"
    done
}

# Migrar datos a bind mounts (para desarrollo)
migrate_to_bind() {
    print_header "Migrando a Bind Mounts (Desarrollo)"
    
    print_warning "Esto copiará los datos de los volúmenes a directorios locales"
    
    # Crear directorios locales
    mkdir -p ./data ./output
    
    # Migrar datos
    echo -e "\n${YELLOW}Migrando voces clonadas...${NC}"
    docker run --rm \
        -v "${DATA_VOLUME}:/from:ro" \
        -v "$(pwd)/data:/to" \
        busybox cp -r /from/. /to/ 2>/dev/null || true
    print_success "Datos migrados a: ./data/"
    
    # Migrar output
    echo -e "\n${YELLOW}Migrando archivos generados...${NC}"
    docker run --rm \
        -v "${OUTPUT_VOLUME}:/from:ro" \
        -v "$(pwd)/output:/to" \
        busybox cp -r /from/. /to/ 2>/dev/null || true
    print_success "Output migrado a: ./output/"
    
    echo -e "\n${GREEN}Migración completada!${NC}"
    echo -e "\nAhora puedes editar docker-compose.yml y cambiar:"
    echo -e "  - qwen3_tts_data:/app/data   →  ./data:/app/data"
    echo -e "  - qwen3_tts_output:/app/output  →  ./output:/app/output"
}

# Mostrar ayuda
show_help() {
    cat << EOF
Gestión de Volúmenes Persistentes para Qwen3-TTS

Uso: $0 <comando> [opciones]

Comandos:
  info              Mostrar información de los volúmenes
  backup [nombre]   Crear backup de los volúmenes (nombre opcional)
  restore <nombre>  Restaurar volúmenes desde un backup
  list              Listar backups disponibles
  migrate           Migrar datos de volúmenes a directorios locales (bind mounts)
  help              Mostrar esta ayuda

Ejemplos:
  # Ver información de volúmenes
  $0 info

  # Crear backup con timestamp automático
  $0 backup

  # Crear backup con nombre específico
  $0 backup mi_backup_importante

  # Listar backups disponibles
  $0 list

  # Restaurar un backup
  $0 restore backup_20240115_143022

EOF
}

# Main
main() {
    check_docker
    
    case "${1:-help}" in
        info)
            show_info
            ;;
        backup)
            backup_volumes "$2"
            ;;
        restore)
            restore_volumes "$2"
            ;;
        list)
            list_backups
            ;;
        migrate)
            migrate_to_bind
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Comando desconocido: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
