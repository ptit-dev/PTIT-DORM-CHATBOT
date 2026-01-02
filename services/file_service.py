import os
import shutil
from typing import List
from fastapi import UploadFile


class FileService:
    
    def __init__(self, data_folder: str = "data_documents", vector_db_path: str = "rag_chroma_db"):
        self.data_folder = data_folder
        self.vector_db_path = vector_db_path
    
    def list_txt_files(self) -> List[str]:
        if not os.path.exists(self.data_folder):
            return []
        return [f for f in os.listdir(self.data_folder) if f.endswith('.txt')]
    
    def file_exists(self, filename: str) -> bool:
        file_path = os.path.join(self.data_folder, filename)
        return os.path.exists(file_path)
    
    async def add_txt_file(self, file: UploadFile) -> str:
        if not file.filename.endswith('.txt'):
            raise ValueError("Only .txt files are allowed")
        
        file_path = os.path.join(self.data_folder, file.filename)
        
        if os.path.exists(file_path):
            raise FileExistsError(f"File '{file.filename}' already exists")
        
        os.makedirs(self.data_folder, exist_ok=True)
        content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(content)
        
        return file.filename
    
    def delete_txt_file(self, filename: str) -> str:
        if not filename.endswith('.txt'):
            raise ValueError("Only .txt files can be deleted")
        
        file_path = os.path.join(self.data_folder, filename)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File '{filename}' not found")
        
        os.remove(file_path)
        return filename
    
    def reset_all_data(self) -> dict:
        deleted_files = []
        
        if os.path.exists(self.vector_db_path):
            shutil.rmtree(self.vector_db_path)
        
        if os.path.exists(self.data_folder):
            for filename in os.listdir(self.data_folder):
                if filename.endswith('.txt'):
                    file_path = os.path.join(self.data_folder, filename)
                    os.remove(file_path)
                    deleted_files.append(filename)
        
        return {
            "deleted_files": deleted_files,
            "vector_db_cleared": True
        }
    
    def get_file_content(self, filename: str) -> str:
        if not filename.endswith('.txt'):
            raise ValueError("Only .txt files can be read")
        
        file_path = os.path.join(self.data_folder, filename)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File '{filename}' not found")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()


file_service = FileService()
