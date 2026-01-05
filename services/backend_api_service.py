import requests
from typing import Optional, Dict, List
from dependency_injector.wiring import inject, Provide

class BackendAPIService:
    
    @inject
    def __init__(self, 
                 config = Provide["Container.config"],
                 logging_service = Provide["Container.logging_service"]):
        self.config = config
        self.logger = logging_service.get_logger(__name__)
        self.backend_url = self.config.backend_api_url
        self.api_key = self.config.backend_api_key
        
    def fetch_initial_data(self) -> Optional[Dict]:
        if not self.backend_url:
            self.logger.warning("Backend API URL not configured")
            return None
            
        try:
            headers = {}
            if self.api_key:
                headers['API-key'] = f'{self.api_key}'
                
            self.logger.info(f"Fetching initial data from {self.backend_url}/api/chatbot/initialize")
            
            response = requests.get(
                f"{self.backend_url}/api/chatbot/initialize",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('code') == 200 and 'data' in data:
                    result = data['data']
                    
                    prompting_list = result.get('prompting', [])
                    guest_prompt = None
                    
                    for prompt in prompting_list:
                        if prompt.get('type') == 'guest':
                            guest_prompt = prompt
                            break
                    
                    self.logger.info(f"Fetched {len(result.get('documents', []))} documents and guest prompt")
                    
                    return {
                        "documents": result.get('documents', []),
                        "prompting": guest_prompt
                    }
                else:
                    self.logger.error(f"Invalid response format from backend: {data}")
                    return None
            else:
                self.logger.error(f"Backend API returned status {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            self.logger.error("Backend API request timeout")
            return None
        except requests.exceptions.ConnectionError:
            self.logger.error("Cannot connect to backend API")
            return None
        except Exception as e:
            self.logger.error(f"Error fetching initial data: {str(e)}")
            return None
    
    def fetch_documents(self) -> Optional[List[Dict]]:
        data = self.fetch_initial_data()
        return data.get('documents') if data else None
    
    def fetch_guest_prompt(self) -> Optional[Dict]:
        data = self.fetch_initial_data()
        return data.get('prompting') if data else None
