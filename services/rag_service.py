import os
import sys
import traceback
from typing import Optional, Tuple
from datetime import datetime

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_google_genai import GoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.language_models.llms import LLM
from google.genai.errors import APIError as GoogleAPIError
from services.config_service import config_service

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass


class RAGService:
    
    VECTOR_DB_PATH = "rag_chroma_db"
    EMBEDDING_MODEL_NAME = "bkai-foundation-models/vietnamese-bi-encoder"
    API_TIMEOUT_SECONDS = int(os.getenv("RAG_API_TIMEOUT_SECONDS", 30))
    RETRIEVAL_K_CHUNKS = int(os.getenv("RAG_RETRIEVAL_K_CHUNKS", 5))
    
    def __init__(self):
        load_dotenv()
        os.environ['GOOGLE_API_KEY'] = os.getenv('GOOGLE_API_KEY')
        self.llm: Optional[LLM] = None
        self.vectorstore: Optional[Chroma] = None
        self.config = config_service
    
    def load_llm_and_db(self) -> Tuple[Optional[LLM], Optional[Chroma]]:
        print("RAG: Initializing LLM")
        try:
            if not os.getenv('GOOGLE_API_KEY'):
                print("RAG: GOOGLE_API_KEY not set")
                return None, None
            
            self.llm = GoogleGenerativeAI(
                model=self.config.llm_model_name,
                temperature=self.config.temperature,
                max_output_tokens=10000,
            )
            print(f"RAG: LLM {self.config.llm_model_name} ready")
        except GoogleAPIError as e:
            print(f"RAG: LLM API error - {e}")
            return None, None
        except Exception as e:
            print(f"RAG: LLM init error - {e}")
            return None, None

        print("RAG: Loading vector database")
        if not os.path.exists(self.VECTOR_DB_PATH):
            print(f"RAG: Database path '{self.VECTOR_DB_PATH}' not found")
            return self.llm, None
        
        embeddings = HuggingFaceEmbeddings(model_name=self.EMBEDDING_MODEL_NAME)
        self.vectorstore = Chroma(
            persist_directory=self.VECTOR_DB_PATH,
            embedding_function=embeddings
        )
        print("RAG: Vector database loaded")

        return self.llm, self.vectorstore
    
    def generate_response(self, question: str) -> str:
        if not self.llm or not self.vectorstore:
            return "Lỗi: Hệ thống đang bảo trì, vui lòng thử lại sau."
        
        retriever = self.vectorstore.as_retriever(search_kwargs={"k": self.RETRIEVAL_K_CHUNKS})
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
            input_variables=["context", "question", "current_date", "system_prompt"]
        )

        current_date = datetime.now().strftime("%d/%m/%Y")
        final_prompt = rag_prompt.format(
            context=context_text,
            question=question,
            current_date=current_date,
            system_prompt=self.config.system_prompt
        )

        print("RAG: Calling LLM API")

        try:
            response = self.llm.invoke(final_prompt)
            print("RAG: API call successful")

            if not response or response.strip() == "":
                return (
                    "Xin lỗi, hệ thống không thể tạo ra câu trả lời "
                    "hợp lệ dựa trên ngữ cảnh được cung cấp. "
                    "Vui lòng thử lại hoặc thay đổi câu hỏi."
                )

            return response
        except Exception as e:
            traceback.print_exc()
            raise Exception(f"LLM API error: {str(e)}")


rag_service = RAGService()


def load_llm_and_db():
    return rag_service.load_llm_and_db()


def generate_response(llm: LLM, vectorstore: Chroma, question: str) -> str:
    rag_service.llm = llm
    rag_service.vectorstore = vectorstore
    return rag_service.generate_response(question)