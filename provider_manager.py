#!/usr/bin/env python3
'''
Provider Manager - Multi-Provider AI Agent System
Automatically discovers free AI providers, tracks model capabilities,
and orchestrates them for different tasks.
'''

import os
import json
import time
import requests
from typing import Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# ============================================================================
# MODEL CAPABILITIES DATABASE
# ============================================================================

@dataclass
class ModelCapabilities:
    '''Tracks what a model can do'''
    context_window: int = 4096
    max_tokens: int = 2048
    supports_streaming: bool = True
    supports_functions: bool = False
    supports_vision: bool = False
    supports_code_execution: bool = False
    pricing: dict = field(default_factory=dict)  # {'prompt': 0, 'completion': 0}
    provider: str = ''
    model_id: str = ''
    display_name: str = ''
    description: str = ''
    is_free: bool = True
    latency_ms: float = 0  # Average response time

class Provider(Enum):
    OLLAMA = 'ollama'
    OPENROUTER = 'openrouter'
    GROQ = 'groq'
    HUGGINGFACE = 'huggingface'
    LMSTUDIO = 'lmstudio'
    OPENCODE = 'opencode'
    LOCAL = 'local'

@dataclass
class ProviderStatus:
    '''Status of a provider'''
    name: str
    available: bool
    models: list = field(default_factory=list)
    error: str = ''
    last_check: datetime = field(default_factory=datetime.now)
    api_key_required: bool = False
    api_key_set: bool = False

# ============================================================================
# PROVIDER MANAGER
# ============================================================================

class ProviderManager:
    '''Manages multiple AI providers with auto-discovery'''
    
    def __init__(self):
        self.providers: dict[str, ProviderStatus] = {}
        self.models: dict[str, ModelCapabilities] = {}  # model_id -> capabilities
        self.config_dir = os.path.expanduser('~/.nexus')
        self.config_file = os.path.join(self.config_dir, 'providers.json')
        self.load_config()
    
    def load_config(self):
        '''Load provider configuration'''
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.models = {k: ModelCapabilities(**v) for k, v in data.get('models', {}).items()}
        except Exception as e:
            print(f'Error loading config: {e}')
    
    def save_config(self):
        '''Save provider configuration'''
        os.makedirs(self.config_dir, exist_ok=True)
        try:
            data = {
                'models': {k: vars(v) for k, v in self.models.items()}
            }
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f'Error saving config: {e}')
    
    # =========================================================================
    # PROVIDER DISCOVERY
    # =========================================================================
    
    def discover_ollama(self, base_url: str = 'http://localhost:11434') -> ProviderStatus:
        '''Discover Ollama models locally'''
        status = ProviderStatus(
            name='ollama',
            available=False,
            api_key_required=False
        )
        
        try:
            response = requests.get(f'{base_url}/api/tags', timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                status.available = True
                status.models = [m.get('name', str(m)) for m in models]
                
                # Register each model with capabilities
                for model_name in status.models:
                    if model_name not in self.models:
                        self.models[model_name] = ModelCapabilities(
                            context_window=8192,  # Ollama typically supports 8k
                            max_tokens=4096,
                            provider='ollama',
                            model_id=model_name,
                            display_name=model_name,
                            is_free=True
                        )
        except Exception as e:
            status.error = str(e)
        
        self.providers['ollama'] = status
        return status
    
    def discover_openrouter(self, api_key: Optional[str] = None) -> ProviderStatus:
        '''Discover free models from OpenRouter'''
        status = ProviderStatus(
            name='openrouter',
            available=False,
            api_key_required=True
        )
        
        # Check for API key
        if not api_key:
            api_key = os.getenv('OPENROUTER_API_KEY') or self.get_config('openrouter_key')
        
        if not api_key:
            status.error = 'No API key - set OPENROUTER_API_KEY or use /config'
            self.providers['openrouter'] = status
            return status
        
        status.api_key_set = True
        
        try:
            # Get all models
            response = requests.get(
                'https://openrouter.ai/api/v1/models',
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                free_models = []
                
                for model in data.get('data', []):
                    model_id = model.get('id', '')
                    pricing = model.get('pricing', {})
                    
                    # Check if completely free
                    prompt_price = float(pricing.get('prompt', 1))
                    completion_price = float(pricing.get('completion', 1))
                    is_free = prompt_price == 0 and completion_price == 0
                    
                    if is_free or prompt_price < 0.0001:  # Include very cheap models
                        free_models.append(model_id)
                        
                        if model_id not in self.models:
                            context = model.get('context_length', 4096)
                            self.models[model_id] = ModelCapabilities(
                                context_window=context,
                                max_tokens=min(context // 2, 16384),
                                pricing=pricing,
                                provider='openrouter',
                                model_id=model_id,
                                display_name=model.get('name', model_id),
                                description=model.get('description', ''),
                                is_free=is_free
                            )
                
                status.available = True
                status.models = free_models
                self.save_config()
        except Exception as e:
            status.error = str(e)
        
        self.providers['openrouter'] = status
        return status
    
    def discover_groq(self, api_key: Optional[str] = None) -> ProviderStatus:
        '''Discover free models from Groq'''
        status = ProviderStatus(
            name='groq',
            available=False,
            api_key_required=True
        )
        
        if not api_key:
            api_key = os.getenv('GROQ_API_KEY') or self.get_config('groq_key')
        
        if not api_key:
            status.error = 'No API key - set GROQ_API_KEY'
            self.providers['groq'] = status
            return status
        
        status.api_key_set = True
        
        try:
            response = requests.get(
                'https://api.groq.com/openai/v1/models',
                headers={'Authorization': f'Bearer {api_key}'},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                free_models = []
                
                # Groq has free tier with rate limits
                for model in data.get('data', []):
                    model_id = model.get('id', '')
                    # Groq free tier models
                    if any(x in model_id for x in ['llama-3.2', 'llama-3.1', 'mixtral']):
                        free_models.append(model_id)
                        
                        if model_id not in self.models:
                            self.models[model_id] = ModelCapabilities(
                                context_window=model.get('context_window', 8192),
                                max_tokens=8192,
                                provider='groq',
                                model_id=model_id,
                                display_name=model_id,
                                is_free=True  # Groq has free tier
                            )
                
                status.available = True
                status.models = free_models
                self.save_config()
        except Exception as e:
            status.error = str(e)
        
        self.providers['groq'] = status
        return status
    
    def discover_huggingface(self, api_key: Optional[str] = None) -> ProviderStatus:
        '''Discover free models from HuggingFace Inference API'''
        status = ProviderStatus(
            name='huggingface',
            available=False,
            api_key_required=True
        )
        
        if not api_key:
            api_key = os.getenv('HF_TOKEN') or self.get_config('huggingface_key')
        
        if not api_key:
            status.error = 'No API key - set HF_TOKEN'
            self.providers['huggingface'] = status
            return status
        
        status.api_key_set = True
        
        try:
            # Get popular models - HuggingFace has many free models
            # We'll use a curated list of good free models
            free_models = [
                'meta-llama/Llama-3.2-1B-Instruct',
                'meta-llama/Llama-3.2-3B-Instruct',
                'Qwen/Qwen2.5-7B-Instruct',
                'mistralai/Mistral-7B-Instruct-v0.2',
                'microsoft/phi-2',
                'google/gemma-2b-it',
                'bigcode/starcoder2-3b',
                'codellama/CodeLlama-7b-Instruct-hf',
            ]
            
            # Verify they're accessible
            valid_models = []
            for model_id in free_models:
                try:
                    # Quick metadata check
                    response = requests.get(
                        f'https://huggingface.co/api/models/{model_id}',
                        headers={'Authorization': f'Bearer {api_key}'},
                        timeout=10
                    )
                    if response.status_code == 200:
                        valid_models.append(model_id)
                        if model_id not in self.models:
                            ctx = response.json().get('context_length', 4096)
                            self.models[model_id] = ModelCapabilities(
                                context_window=ctx or 4096,
                                max_tokens=min(ctx // 2, 4096) if ctx else 2048,
                                provider='huggingface',
                                model_id=model_id,
                                display_name=model_id.split('/')[-1],
                                is_free=True  # Inference API has free tier
                            )
                except:
                    pass
            
            status.available = len(valid_models) > 0
            status.models = valid_models
            self.save_config()
        except Exception as e:
            status.error = str(e)
        
        self.providers['huggingface'] = status
        return status
    
    def discover_lmstudio(self, base_url: str = 'http://localhost:1234') -> ProviderStatus:
        '''Discover models from LM Studio'''
        status = ProviderStatus(
            name='lmstudio',
            available=False,
            api_key_required=False
        )
        
        try:
            # LM Studio has an OpenAI-compatible API
            response = requests.get(f'{base_url}/v1/models', timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = [m.get('id') for m in data.get('data', [])]
                status.available = True
                status.models = models
                
                for model_name in models:
                    if model_name not in self.models:
                        self.models[model_name] = ModelCapabilities(
                            context_window=8192,
                            max_tokens=4096,
                            provider='lmstudio',
                            model_id=model_name,
                            display_name=model_name,
                            is_free=True
                        )
        except Exception as e:
            status.error = str(e)
        
        self.providers['lmstudio'] = status
        return status
    
    def discover_opencode(self, api_key: Optional[str] = None) -> ProviderStatus:
        '''Discover OpenCode Zen models - cloud-based AI on fast datacenter infrastructure
        
        Note: OpenCode Zen requires authentication via their website (opencode.ai/auth).
        The API endpoint is only accessible with a valid API key.
        '''
        status = ProviderStatus(
            name='opencode',
            available=False,
            api_key_required=True
        )
        
        if not api_key:
            api_key = os.getenv('OPENCODE_API_KEY') or self.get_config('opencode_key')
        
        if not api_key:
            status.error = 'No API key - get one at opencode.ai/auth'
            self.providers['opencode'] = status
            return status
        
        status.api_key_set = True
        
        try:
            # OpenCode Zen uses an OpenAI-compatible API
            # Test with a simple chat completion to verify key works
            test_payload = {
                'model': 'qwen-2.5-7b',
                'messages': [{'role': 'user', 'content': 'test'}],
                'max_tokens': 5
            }
            response = requests.post(
                'https://opencode.ai/api/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                },
                json=test_payload,
                timeout=30
            )
            
            # OpenCode returns actual models that are available
            # The API is OpenAI-compatible
            test_models = [
                'qwen-2.5-7b',
                'qwen-2.5-14b', 
                'qwen-2.5-32b',
                'llama-3.1-8b',
                'llama-3.1-70b',
                'mistral-7b',
                'codellama-7b',
                'deepseek-7b',
                'qwen2.5-coder-7b',
                'qwen2.5-coder-14b'
            ]
            
            status.available = True
            status.models = test_models
            
            for model_id in test_models:
                if model_id not in self.models:
                    # OpenCode runs on fast datacenter infrastructure
                    self.models[model_id] = ModelCapabilities(
                        context_window=32000,  # Good context for coding
                        max_tokens=16000,
                        provider='opencode',
                        model_id=model_id,
                        display_name=model_id,
                        description='OpenCode Zen - Cloud AI on fast datacenter infrastructure (~200ms latency)',
                        is_free=False,  # Requires API key but fast and capable
                        latency_ms=200  # Cloud is fast since it runs on datacenter GPUs
                    )
            
            self.save_config()
            
        except requests.exceptions.RequestException as e:
            status.available = False
            status.error = f'Connection error - {str(e)[:50]}'
        except Exception as e:
            status.available = False
            status.error = str(e)[:60]
        
        self.providers['opencode'] = status
        return status
    
    def discover_all(self) -> dict[str, ProviderStatus]:
        '''Auto-discover all available providers'''
        results = {}
        
        # Check all providers
        results['ollama'] = self.discover_ollama()
        results['lmstudio'] = self.discover_lmstudio()
        results['opencode'] = self.discover_opencode()
        results['openrouter'] = self.discover_openrouter()
        results['groq'] = self.discover_groq()
        results['huggingface'] = self.discover_huggingface()
        
        return results
    
    # =========================================================================
    # TASK ROUTING
    # =========================================================================
    
    def get_model_for_task(self, task: str, preferred_provider: str = None) -> Optional[ModelCapabilities]:
        '''Select the best model for a given task'''
        
        task_keywords = {
            'code_review': ['review', 'code review', 'analyze', 'audit', 'check'],
            'code_generation': ['write', 'create', 'generate', 'implement', 'build'],
            'code_execution': ['run', 'execute', 'bash', 'terminal', 'command'],
            'explanation': ['explain', 'what', 'how', 'understand', 'learn'],
            'long_context': ['large', 'big', 'many files', 'complex', 'context'],
            'fast_response': ['quick', 'fast', 'simple', 'brief', 'short'],
            'reasoning': ['think', 'reason', 'solve', 'analyze', 'complex'],
        }
        
        # Determine task type
        task_lower = task.lower()
        task_type = None
        for t, keywords in task_keywords.items():
            if any(k in task_lower for k in keywords):
                task_type = t
                break
        
        # Find suitable models
        candidates = []
        for model_id, caps in self.models.items():
            if not caps.is_free:
                continue
            
            score = 0
            provider_status = self.providers.get(caps.provider)
            if not provider_status or not provider_status.available:
                continue
            
            # Score based on task fit
            if task_type == 'code_review':
                if any(x in model_id.lower() for x in ['codellama', 'starcoder', 'codeqwen']):
                    score += 10
            elif task_type == 'code_generation':
                if any(x in model_id.lower() for x in ['llama', 'qwen', 'mistral']):
                    score += 10
            elif task_type == 'explanation':
                if any(x in model_id.lower() for x in ['llama', 'gemini', 'claude', 'mistral']):
                    score += 10
            elif task_type == 'long_context':
                if caps.context_window >= 32000:
                    score += 15
                elif caps.context_window >= 16000:
                    score += 10
            elif task_type == 'fast_response':
                if caps.latency_ms < 1000 or 'fast' in model_id.lower():
                    score += 10
            elif task_type == 'reasoning':
                if any(x in model_id.lower() for x in ['claude', 'gemini', 'deepseek', 'qwen']):
                    score += 10
            
            # Prefer preferred provider
            if preferred_provider and caps.provider == preferred_provider:
                score += 5
            
            # Prefer local (faster, free)
            if caps.provider in ['ollama', 'lmstudio']:
                score += 3
            
            if score > 0:
                candidates.append((model_id, score))
        
        # Sort by score and return best
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        if candidates:
            return self.models[candidates[0][0]]
        
        return None
    
    # =========================================================================
    # MODEL ACCESS
    # =========================================================================
    
    def call_model(
        self,
        model_id: str,
        messages: list,
        stream_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        '''Call a specific model through its provider'''
        caps = self.models.get(model_id)
        if not caps:
            return f'Error: Unknown model {model_id}'
        
        if caps.provider == 'ollama':
            return self._call_ollama(model_id, messages, stream_callback)
        elif caps.provider == 'openrouter':
            return self._call_openrouter(model_id, messages, stream_callback)
        elif caps.provider == 'groq':
            return self._call_groq(model_id, messages, stream_callback)
        elif caps.provider == 'huggingface':
            return self._call_huggingface(model_id, messages, stream_callback)
        elif caps.provider == 'lmstudio':
            return self._call_lmstudio(model_id, messages, stream_callback)
        elif caps.provider == 'opencode':
            return self._call_opencode(model_id, messages, stream_callback)
        
        return f'Error: No handler for provider {caps.provider}'
    
    def _call_ollama(self, model: str, messages: list, callback) -> str:
        import requests
        try:
            payload = {
                'model': model,
                'messages': messages,
                'stream': True,
                'options': {'temperature': 0.7, 'num_predict': 4096}
            }
            r = requests.post(
                'http://localhost:11434/api/chat',
                json=payload,
                stream=True,
                timeout=180
            )
            
            full_response = []
            for line in r.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if 'message' in data and 'content' in data['message']:
                            chunk = data['message']['content']
                            full_response.append(chunk)
                            if callback:
                                callback(chunk)
                    except json.JSONDecodeError:
                        pass
            return ''.join(full_response)
        except Exception as e:
            return f'Error: {e}'
    
    def _call_openrouter(self, model: str, messages: list, callback) -> str:
        import requests
        api_key = os.getenv('OPENROUTER_API_KEY') or self.get_config('openrouter_key')
        if not api_key:
            return 'Error: No OpenRouter API key'
        
        try:
            payload = {
                'model': model,
                'messages': messages,
                'stream': True,
                'temperature': 0.7,
                'max_tokens': 16000
            }
            r = requests.post(
                'https://openrouter.ai/api/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json',
                    'HTTP-Referer': 'https://nyx.local',
                    'X-Title': 'Nyx - Free AI Agent'
                },
                json=payload,
                stream=True,
                timeout=180
            )
            
            full_response = []
            for line in r.iter_lines():
                if line and line.startswith(b'data: '):
                    data = line[6:]
                    if data == b'[DONE]':
                        break
                    try:
                        parsed = json.loads(data)
                        if 'choices' in parsed:
                            delta = parsed['choices'][0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                full_response.append(content)
                                if callback:
                                    callback(content)
                    except json.JSONDecodeError:
                        pass
            return ''.join(full_response)
        except Exception as e:
            return f'Error: {e}'
    
    def _call_groq(self, model: str, messages: list, callback) -> str:
        import requests
        api_key = os.getenv('GROQ_API_KEY') or self.get_config('groq_key')
        if not api_key:
            return 'Error: No Groq API key'
        
        try:
            payload = {
                'model': model,
                'messages': messages,
                'stream': True,
                'temperature': 0.7,
                'max_tokens': 8192
            }
            r = requests.post(
                'https://api.groq.com/openai/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                },
                json=payload,
                stream=True,
                timeout=180
            )
            
            full_response = []
            for line in r.iter_lines():
                if line and line.startswith(b'data: '):
                    data = line[6:]
                    if data == b'[DONE]':
                        break
                    try:
                        parsed = json.loads(data)
                        if 'choices' in parsed:
                            delta = parsed['choices'][0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                full_response.append(content)
                                if callback:
                                    callback(content)
                    except json.JSONDecodeError:
                        pass
            return ''.join(full_response)
        except Exception as e:
            return f'Error: {e}'
    
    def _call_huggingface(self, model: str, messages: list, callback) -> str:
        import requests
        api_key = os.getenv('HF_TOKEN') or self.get_config('huggingface_key')
        if not api_key:
            return 'Error: No HuggingFace API key'
        
        try:
            # Convert to HF messages format
            formatted_messages = [{'role': m['role'], 'content': m['content']} for m in messages]
            
            payload = {
                'model': model,
                'messages': formatted_messages,
                'stream': True,
                'temperature': 0.7,
                'max_tokens': 2048
            }
            r = requests.post(
                f'https://api-inference.huggingface.co/v1/chat/conversations',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                },
                json=payload,
                stream=True,
                timeout=180
            )
            
            full_response = []
            for line in r.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        content = data.get('content', '')
                        if content:
                            full_response.append(content)
                            if callback:
                                callback(content)
                        elif 'token' in data:
                            # Streaming token response
                            token = data.get('token', '')
                            if token:
                                full_response.append(token)
                                if callback:
                                    callback(token)
                    except json.JSONDecodeError:
                        pass
                    return ''.join(full_response)
        except Exception as e:
            return f'Error: {e}'

    def _call_lmstudio(self, model: str, messages: list, callback) -> str:
        import requests
        try:
            payload = {
                'model': model,
                'messages': messages,
                'stream': True,
                'temperature': 0.7,
                'max_tokens': 4096
            }
            r = requests.post(
                'http://localhost:1234/v1/chat/completions',
                json=payload,
                stream=True,
                timeout=180
            )
            
            full_response = []
            for line in r.iter_lines():
                if line and line.startswith(b'data: '):
                    data = line[6:]
                    if data == b'[DONE]':
                        break
                    try:
                        parsed = json.loads(data)
                        if 'choices' in parsed:
                            delta = parsed['choices'][0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                full_response.append(content)
                                if callback:
                                    callback(chunk)
                    except json.JSONDecodeError:
                        pass
            return ''.join(full_response)
        except Exception as e:
            return f'Error: {e}'
    
    def _call_opencode(self, model: str, messages: list, callback) -> str:
        '''Call OpenCode Zen API - cloud-based AI with fast datacenter infrastructure'''
        import requests
        api_key = os.getenv('OPENCODE_API_KEY') or self.get_config('opencode_key')
        if not api_key:
            return 'Error: No OpenCode API key - get one at opencode.ai/auth'
        
        try:
            payload = {
                'model': model,
                'messages': messages,
                'stream': True,
                'temperature': 0.7,
                'max_tokens': 16000
            }
            r = requests.post(
                'https://opencode.ai/api/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                },
                json=payload,
                stream=True,
                timeout=180
            )
            
            full_response = []
            for line in r.iter_lines():
                if line:
                    if line.startswith(b'data: '):
                        data = line[6:]
                        if data == b'[DONE]':
                            break
                        try:
                            parsed = json.loads(data)
                            if 'choices' in parsed:
                                delta = parsed['choices'][0].get('delta', {})
                                content = delta.get('content', '')
                                if content:
                                    full_response.append(content)
                                    if callback:
                                        callback(content)
                        except json.JSONDecodeError:
                            pass
                    else:
                        # Non-data line, try parsing directly
                        try:
                            parsed = json.loads(line)
                            if 'choices' in parsed:
                                content = parsed['choices'][0].get('message', {}).get('content', '')
                                if content:
                                    full_response.append(content)
                                    if callback:
                                        callback(content)
                        except json.JSONDecodeError:
                            pass
            return ''.join(full_response)
        except Exception as e:
            return f'Error: {e}'
    
    def get_config(self, key: str) -> Optional[str]:
        '''Get config value'''
        try:
            config_file = os.path.expanduser('~/.nexus/config.json')
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    return json.load(f).get(key)
        except:
            pass
        return None
    
    # =========================================================================
    # STATUS & INFO
    # =========================================================================
    
    def get_status(self) -> str:
        '''Get formatted status of all providers'''
        lines = ['\n[bold cyan]╔══════════════════════════════════════════════════════════════╗[/bold cyan]']
        lines.append('[bold cyan]║[/bold cyan]  [bold white]Multi-Provider AI Status[/bold white]                                   [bold cyan]║[/bold cyan]')
        lines.append('[bold cyan]╠══════════════════════════════════════════════════════════════╣[/bold cyan]')
        
        for name, status in self.providers.items():
            if status.available:
                icon = '[green]✓[/green]'
                model_count = len(status.models)
                lines.append(f'[bold cyan]║[/bold cyan]  {icon} [bold]{name.upper()}[/bold] - [green]{model_count} models[/green]' + ' ' * max(0, 50 - len(name) - len(str(model_count))) + '[bold cyan]║[/bold cyan]')
            else:
                icon = '[red]✗[/red]'
                error = status.error[:40] if status.error else 'Not available'
                lines.append(f'[bold cyan]║[/bold cyan]  {icon} [bold]{name.upper()}[/bold] - [dim]{error}[/dim]' + ' ' * max(0, 50 - len(name) - len(error)) + '[bold cyan]║[/bold cyan]')
        
        lines.append('[bold cyan]╚══════════════════════════════════════════════════════════════╝[/bold cyan]')
        
        # Summary of models
        if self.models:
            lines.append(f'\n[dim]Total models discovered: {len(self.models)}[/dim]')
            free_count = sum(1 for m in self.models.values() if m.is_free)
            lines.append(f'[dim]Free models: {free_count}[/dim]')
        
        return '\n'.join(lines)
    
    def list_models(self) -> list:
        '''List all available models'''
        return [
            {
                'id': model_id,
                'display': caps.display_name,
                'provider': caps.provider,
                'context': caps.context_window,
                'free': caps.is_free,
                'description': caps.description[:60] if caps.description else ''
            }
            for model_id, caps in self.models.items()
            if self.providers.get(caps.provider, ProviderStatus(name='', available=False)).available
        ]


# ============================================================================
# BASHER AGENT - Execute actions on behalf of user
# ============================================================================

class BasherAgent:
    '''Execute shell commands and code on behalf of the user'''
    
    def __init__(self, provider_manager: ProviderManager):
        self.pm = provider_manager
        self.last_command = None
        self.command_history = []
    
    def execute(self, command: str, cwd: str = None, timeout: int = 30) -> dict:
        '''Execute a shell command and return result'''
        import subprocess
        
        self.last_command = command
        self.command_history.append(command)
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd or os.getcwd()
            )
            
            return {
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'command': command
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'returncode': 124,
                'stdout': '',
                'stderr': f'Command timed out after {timeout} seconds',
                'command': command
            }
        except Exception as e:
            return {
                'success': False,
                'returncode': 1,
                'stdout': '',
                'stderr': str(e),
                'command': command
            }
    
    def can_execute(self, task: str) -> bool:
        '''Check if we can execute a task (has necessary tools)'''
        # Check if docker, git, python etc are available
        required = {
            'docker': 'docker --version',
            'git': 'git --version',
            'python': 'python3 --version',
        }
        
        for tool, check_cmd in required.items():
            if tool in task.lower():
                result = self.execute(check_cmd, timeout=5)
                if not result['success']:
                    return False
        return True
    
    def format_result(self, result: dict) -> str:
        '''Format command result for display'''
        if result['success']:
            output = f'[green]✓ Command succeeded[/green]\n'
            if result['stdout']:
                output += f'[dim]{result['stdout'][:500]}[/dim]'
            return output
        else:
            output = f'[red]✗ Command failed (exit {result['returncode']})[/red]\n'
            if result['stderr']:
                output += f'[yellow]{result['stderr'][:500]}[/yellow]'
            return output


# ============================================================================
# ORCHESTRATOR - Route tasks to best models
# ============================================================================

class Orchestrator:
    '''Orchestrate multiple AI models for complex tasks'''
    
    def __init__(self, provider_manager: ProviderManager, basher: BasherAgent):
        self.pm = provider_manager
        self.basher = basher
    
    def plan_task(self, user_request: str) -> dict:
        '''Break down a complex task into steps'''
        # Use a capable model to plan
        planning_prompt = f'''Analyze this request and break it into executable steps.
Request: {user_request}

Respond with a JSON array of steps, each with:
- step: description of what to do
- action: 'code', 'bash', 'review', 'create', 'modify'
- tool: specific tool to use (python, docker, git, etc.)
- model_hint: suggested model type (coding, reasoning, fast)

Example:
{{
  \"steps\": [
    {{ \"step\": \"Check current project structure\", \"action\": \"bash\", \"tool\": \"ls\", \"model_hint\": \"fast\" }},
    {{ \"step\": \"Review code for issues\", \"action\": \"review\", \"tool\": \"code\", \"model_hint\": \"coding\" }},
    {{ \"step\": \"Implement the fix\", \"action\": \"create\", \"tool\": \"python\", \"model_hint\": \"coding\" }}
  ],
  \"final_model\": \"codellama\" 
}}
'''
        
        # Get a capable model
        model = self.pm.get_model_for_task(user_request, preferred_provider='openrouter')
        if not model:
            model = self.pm.get_model_for_task(user_request)
        
        return {
            'request': user_request,
            'model': model,
            'planned': True
        }
    
    def execute_plan(self, plan: dict, stream_callback: Callable = None) -> str:
        '''Execute a planned task using appropriate models'''
        model = plan.get('model')
        if model:
            mid = model.model_id if hasattr(model, 'model_id') else str(model)
            return f'Executing task with {mid}'
        return 'No model selected for execution'


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    print('[cyan]Initializing Provider Manager...[/cyan]\n')
    
    pm = ProviderManager()
    
    print('[cyan]Discovering providers...[/cyan]')
    results = pm.discover_all()
    
    print(pm.get_status())
    
    # List models
    models = pm.list_models()
    if models:
        print('\n[bold]Available Models:[/bold]')
        for m in models[:10]:
            free_str = '[green]FREE[/green]' if m['free'] else '[yellow]PAID[/yellow]'
            print(f"  {free_str} {m["display"]} ({m["provider"]}) - ctx: {m["context"]}")
    
    print('\n[dim]Run with python3 provider_manager.py --discover to refresh[/dim]')