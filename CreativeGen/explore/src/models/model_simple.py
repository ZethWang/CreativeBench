"""Simplified model interface for API and VLLM calls
Minimal implementation based on AutoCodeBenchmark patterns
"""
import os
from abc import ABC, abstractmethod
from pathlib import Path
from openai import OpenAI
# from transformers import AutoTokenizer  # Commented out - not needed for API-only setup
# from vllm import LLM, SamplingParams  # Commented out - not needed for current setup
from dotenv import load_dotenv

def load_env_from_parents(start: Path) -> None:
    for parent in [start] + list(start.parents):
        env_path = parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            break

# Load environment variables from .env file
load_env_from_parents(Path(__file__).resolve())

# Global variables for compatibility
completion_tokens = prompt_tokens = 0

class OpenModel(ABC):
    """Base class for open source models"""
    def __init__(self, model_name: str, prompt: str):
        self.model_name = model_name
        self.prompt = prompt

    @abstractmethod
    def load_model(self):
        raise NotImplementedError

class APIModel:
    """API-compatible model"""

    def __init__(self, model: str, temperature: float = 1, max_tokens: int = 256,
                 top_p: float = 1, n: int = 1, gpt_setting: str = None):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.n = n
        self.gpt_setting = gpt_setting

        # Load API configuration from environment variables
        api_key = os.getenv("MODEL_API_KEY")
        base_url = os.getenv("MODEL_BASE_URL", "http://localhost:8000/v1")

        if not api_key:
            raise ValueError("MODEL_API_KEY not found in environment variables")

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=30.0
        )

        # Initialize message state and usage tracking
        self.total_tokens = 0
        self.restart()

    def restart(self):
        """Initialize message state"""
        if "davinci" in self.model:
            self.message = ""
        else:
            self.message = [{"role": "system", "content": self.gpt_setting}] if self.gpt_setting else []

    def __call__(self, input: str) -> list:
        """Make the model callable"""
        if "davinci" in self.model:
            self.message = self.message + "\nInput: " + input
            return self.completiongpt()
        else:
            self.message.append({"role": "user", "content": input})
            return self.chatgpt()

    def update_message(self, output: str):
        """Update message history with output"""
        if "davinci" in self.model:
            self.message = self.message + "\nOutput: " + output
        else:
            self.message.append({"role": "assistant", "content": output})

    def chatgpt(self) -> list:
        """Generate response using chat completion"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.message,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=self.top_p,
                n=self.n
            )

            # Return all responses
            return [choice.message.content for choice in response.choices]
        except Exception as e:
            print(f"API call failed: {e}")
            return [""] * self.n

    def completiongpt(self) -> list:
        """Generate response using text completion (for davinci models)"""
        try:
            response = self.client.completions.create(
                model=self.model,
                prompt=self.message,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=self.top_p,
                n=self.n
            )

            return [choice.text for choice in response.choices]
        except Exception as e:
            print(f"API call failed: {e}")
            return [""] * self.n

    def gpt_usage(self, model: str = None):
        """Return usage information - simplified for compatibility"""
        return f"Total API calls made with model {self.model}. Token tracking not fully implemented in simplified version."

class AltProviderModel:
    """Placeholder for alternative API"""
    def __init__(self, model: str, temperature: float = 1, max_tokens: int = 256,
                 top_p: float = 1, n: int = 1, gpt_setting: str = None):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.n = n
        self.gpt_setting = gpt_setting
        self.restart()

    def restart(self):
        """Initialize message state"""
        self.message = [{"role": "system", "content": self.gpt_setting}] if self.gpt_setting else []

    def __call__(self, input: str) -> list:
        """Make the model callable"""
        self.message.append({"role": "user", "content": input})
        return self.chatgpt()

    def update_message(self, output: str):
        """Update message history with output"""
        self.message.append({"role": "assistant", "content": output})

    def chatgpt(self) -> list:
        return ["Anthropic model placeholder"] * self.n

# class OpenModelVLLM(OpenModel):
#     """VLLM model implementation - COMMENTED OUT (vllm not available)"""
#
#     def __init__(self, model_name: str, prompt: str):
#         super().__init__(model_name, prompt)
#         self.load_model()
#
#     def load_model(self):
#         """Load VLLM model - simplified version"""
#         self.llm = LLM(
#             model=self.model_name,
#             tensor_parallel_size=1,
#             gpu_memory_utilization=0.9,
#             trust_remote_code=True
#         )
#         self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
#
#     def chatgpt(self) -> list:
#         """Generate single response for prompt"""
#         # Prepare message format
#         system_prompt = "You are an expert programmer. Your task is to provide a code solution within a single Markdown code block for the given programming problem."
#         messages = [
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": self.prompt}
#         ]
#
#         # Apply chat template
#         text = self.tokenizer.apply_chat_template(
#             messages,
#             tokenize=False,
#             add_generation_prompt=True
#         )
#
#         # Generate response
#         sampling_params = SamplingParams(
#             temperature=0.7,
#             max_tokens=8192,
#             n=1
#         )
#
#         outputs = self.llm.generate([text], sampling_params)
#         response_text = outputs[0].outputs[0].text
#
#         # Clean response
#         if "</think>" in response_text:
#             response_text = response_text.split("</think>")[-1]
#
#         return [response_text.strip()]

# Alias for backward compatibility - COMMENTED OUT
# OpenModelHF = OpenModelVLLM
