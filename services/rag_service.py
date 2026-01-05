import os
import threading
from typing import Optional, Tuple
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import GoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.language_models.llms import LLM
from dependency_injector.wiring import inject, Provide
from datetime import datetime


class RAGService:
    
    @inject
    def __init__(self, 
                 config = Provide["Container.config_service"],
                 logging_service = Provide["Container.logging_service"]):
        
        os.environ['GOOGLE_API_KEY'] = os.getenv('GOOGLE_API_KEY')
        
        self.config = config
        self.logger = logging_service.get_logger(__name__)
        
        self.llm: Optional[LLM] = None
        self.vectorstore: Optional[Chroma] = None
        self._lock = threading.Lock()

    def load_llm_and_db(self) -> Tuple[Optional[LLM], Optional[Chroma]]:
        with self._lock:
            if self.llm and self.vectorstore:
                self.logger.info("RAG: LLM and DB already initialized")
                return self.llm, self.vectorstore
            
            self.logger.info("RAG: Initializing LLM and DB")
            try:
                self.llm = GoogleGenerativeAI(
                    model=self.config.llm_model_name,
                    temperature=self.config.temperature,
                    max_output_tokens=self.config.max_response_tokens,
                )
                
                embeddings = HuggingFaceEmbeddings(model_name=self.config.embedding_model_name)
                self.vectorstore = Chroma(
                    persist_directory=self.config.vector_db_path,
                    embedding_function=embeddings
                )
                self.logger.info("RAG: LLM and Vector DB are ready")
                return self.llm, self.vectorstore
            except Exception as e:
                self.logger.error(f"RAG: Initialization error - {e}")
                return None, None

    def generate_response(self, question: str) -> str:
        if not self.llm or not self.vectorstore:
            return "Lỗi: Hệ thống đang bảo trì, vui lòng thử lại sau."
        
        retriever = self.vectorstore.as_retriever(search_kwargs={"k": self.config.retrieval_k_chunks})
        retrieved_docs = retriever.invoke(question)
        context_text = "\n\n".join([" ".join(doc.page_content.split()) for doc in retrieved_docs])

        template = (
            "{system_prompt}"
            "NGỮ CẢNH:\n"
            "--- Bối cảnh dữ liệu hiện tại (Ngày {current_date}) ---\n"
            "{context}\n"
            "--- KẾT THÚC NGỮ CẢNH ---\n\n"
            "Câu hỏi của sinh viên:\n"
            "{question}\n\n"
            "Hãy đưa ra câu trả lời trực tiếp:"
        )

        rag_prompt = PromptTemplate(
            template=template,
            input_variables=["context", "question", "system_prompt"]
        )

        final_prompt = rag_prompt.format(
            context=context_text,
            current_date=datetime.now().strftime("%d/%m/%Y"),
            system_prompt=self.config.system_prompt,
            question=question
        )

        try:
            response = self.llm.invoke(final_prompt)
            return response if response else "Không có phản hồi từ AI."
        except Exception as e:
            self.logger.error(f"LLM API error: {e}")
            return "Lỗi kết nối AI."