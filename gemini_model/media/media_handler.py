import os
import time
import google.generativeai as genai

class MediaHandler:
    """Clase auxiliar para manejar la carga y procesamiento de archivos multimedia"""
    def __init__(self):
        self.media_cache = {}  # Almacena {uri: file_object} para reutilización

    def get_mime_type(self, file_path):
        """Determina el tipo MIME basado en la extensión del archivo"""
        extension = file_path.lower().split('.')[-1]
        mime_types = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'mp4': 'video/mp4',
            'avi': 'video/x-msvideo',
            'mov': 'video/quicktime'
        }
        return mime_types.get(extension, 'application/octet-stream')

    def get_or_upload_file(self, path):
        """Obtiene un archivo del caché o lo sube si no existe"""
        try:
            file_name = os.path.basename(path)
            
            # Primero buscar en caché por nombre de archivo
            for uri, cached_file in self.media_cache.items():
                if cached_file.display_name == file_name:
                    try:
                        # Verificar si el archivo aún es válido
                        current_file = genai.get_file(cached_file.name)
                        if current_file.state.name == "ACTIVE":
                            print(f"Using cached file: {current_file.uri}")
                            return current_file
                    except:
                        print(f"Cached file {file_name} expired, uploading new one")
                    # Remover archivo expirado del caché
                    del self.media_cache[uri]
                    break

            # Si no está en caché o expiró, subir nuevo archivo
            mime_type = self.get_mime_type(path)
            file = genai.upload_file(path, mime_type=mime_type)
            print(f"Uploaded new file '{file.display_name}' as: {file.uri}")
            
            # Esperar a que esté activo antes de guardarlo en caché
            current_file = genai.get_file(file.name)
            while current_file.state.name == "PROCESSING":
                print(".", end="", flush=True)
                time.sleep(5)
                current_file = genai.get_file(file.name)
            
            if current_file.state.name == "ACTIVE":
                self.media_cache[current_file.uri] = current_file
                return current_file
            else:
                print(f"Warning: File {file_name} failed to process")
                return None
                
        except Exception as e:
            print(f"Error handling file: {str(e)}")
            return None

    def wait_for_files_active(self, files, polling_interval=10):
        """Espera a que los archivos estén activos"""
        print("Waiting for file processing...")
        for file in files:
            current_file = genai.get_file(file.name)
            while current_file.state.name == "PROCESSING":
                print(".", end="", flush=True)
                time.sleep(polling_interval)
                current_file = genai.get_file(file.name)
            if current_file.state.name != "ACTIVE":
                raise Exception(f"File {file.name} failed to process")
        print("...all files ready")
        print()

    def clear_cache(self):
        """Limpia el caché de archivos"""
        self.media_cache.clear()
