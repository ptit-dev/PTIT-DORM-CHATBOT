from dependency_injector.wiring import inject, Provide

class AppLifecycle:

    @inject
    def __init__(
        self, 
        rag_service = Provide["Container.rag_service"], 
        db_service = Provide["Container.db_service"],
        config = Provide["Container.config"],
        logging_service = Provide["Container.logging_service"],
        connection_manager = Provide["Container.connection_manager"],
        backend_api_service = Provide["Container.backend_api_service"],
    ):
        self.rag_service = rag_service
        self.db_service = db_service
        self.config = config
        self.connection_manager = connection_manager
        self.backend_api_service = backend_api_service
        self.logger = logging_service.get_logger(__name__)
        
        instance_id = id(self)
        self.logger.info(f"AppLifecycle initialized (Singleton ID: {hex(instance_id)})")
    
    async def startup(self):
        self.logger.info("Application Startup")
        
        self.logger.info("Fetching initial data from backend API...")
        initial_data = self.backend_api_service.fetch_initial_data()
        
        if initial_data:
            documents = initial_data.get('documents', [])
            if documents:
                self.db_service.set_documents_from_backend(documents)
                self.logger.info(f"Loaded {len(documents)} documents from backend")
            
            guest_prompt = initial_data.get('prompting')
            if guest_prompt:
                prompt_content = guest_prompt.get('content', '')
                
                try:
                    self.config.system_prompt = prompt_content
                    self.logger.info("System prompt set from backend data")
                except ValueError as ve:
                    self.logger.error(f"Invalid system prompt from backend: {ve}")
        else:
            self.logger.warning("No data fetched from backend API, using local data")
        
        self.logger.info("Loading LLM and Vector Database...")
        llm, vectorstore = self.rag_service.load_llm_and_db()
        
        if llm and vectorstore:
            self.logger.info("LLM and Vector DB loaded successfully")
        else:
            self.logger.error("Failed to load LLM or Vector DB")
        
        self.logger.info("Startup Complet")
    
    async def shutdown(self):
        self.logger.info("Application Shutdown")
        self.logger.info("Cleanup completed")