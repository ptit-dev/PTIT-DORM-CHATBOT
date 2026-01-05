import os
from typing import Optional, List, Dict, TYPE_CHECKING
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from dependency_injector.wiring import inject, Provide

if TYPE_CHECKING:
    from common.container import Container

class DatabaseService:
    @inject
    def __init__(self, 
        config = Provide["Container.config_service"],
        logging_service = Provide["Container.logging_service"]
    ):
        self.config = config
        self.vector_db_path = self.config.vector_db_path
        self.embedding_model_name = self.config.embedding_model_name
        self.chunk_size = self.config.chunk_size
        self.chunk_overlap = self.config.chunk_overlap
        self._documents_cache = None
        self.logger = logging_service.get_logger(__name__)
    
    def set_documents_from_backend(self, documents: List[Dict]):
        self._documents_cache = documents
        self.logger.info(f"DB: Cached {len(documents)} documents from backend")
    
    def get_documents(self) -> List[Document]:
        if not self._documents_cache:
            return []
        
        documents = []
        for doc_data in self._documents_cache:
            doc = Document(
                page_content=doc_data.get('content', ''),
                metadata={
                    "id": doc_data.get('id', ''),
                    "description": doc_data.get('description', ''),
                    "source": "backend"
                }
            )
            documents.append(doc)
        return documents

    def setup_database(self) -> Optional[Chroma]:
        self.logger.info("DB: Processing documents from backend cache")
        documents = self.get_documents()
        
        if not documents:
            self.logger.warning("DB: No documents available")
            return None

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        chunks = text_splitter.split_documents(documents)

        embeddings = HuggingFaceEmbeddings(model_name=self.embedding_model_name)
        
        if os.path.exists(self.vector_db_path):
            vectorstore = Chroma(
                persist_directory=self.vector_db_path,
                embedding_function=embeddings
            )
            existing_ids = vectorstore.get()['ids']
            if len(existing_ids) > 0:
                vectorstore.delete(ids=existing_ids)
            vectorstore.add_documents(documents=chunks)
        else:
            vectorstore = Chroma.from_documents(
                documents=chunks,
                embedding=embeddings,
                persist_directory=self.vector_db_path
            )
            
        return vectorstore