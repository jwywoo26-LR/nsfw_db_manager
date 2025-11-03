import requests
import os
import base64
import json
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from dotenv import load_dotenv
from .system_prompt_enums import SYSTEM_PROMPTS

load_dotenv()


class GrokAPIClient:
    def __init__(self, system_prompt: Optional[str] = None):
        self.base_url = "https://api.x.ai/v1"
        self.api_key = os.getenv("GROK_API_KEY")

        if not self.api_key:
            raise ValueError("GROK_API_KEY must be set in .env file")

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Use TAG_INITIAL_GENERATION as default system prompt
        if system_prompt is None:
            self.system_prompt = SYSTEM_PROMPTS["tag_initial_generation"]
        else:
            self.system_prompt = system_prompt
    
    def encode_image(self, image_path: str) -> str:
        """
        Encode image file to base64 string.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Base64 encoded image string
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def evaluate_image(
        self,
        image_path: str,
        prompt: str,
        context: str = "",
        model: str = "grok-2-vision-latest",
        detail: str = "high",
        use_system_prompt: bool = True
    ) -> Dict[str, Any]:
        """
        Evaluate an image using Grok's vision model.
        
        Args:
            image_path: Path to the image file or URL
            prompt: Text prompt for image evaluation
            context: Additional context for the analysis
            model: Model to use (default: grok-2-vision-latest)
            detail: Image processing detail level (high, low, auto)
            use_system_prompt: Whether to include system prompt (default: True)
            
        Returns:
            API response as dictionary
        """
        # Check if it's a URL or local file
        if image_path.startswith(('http://', 'https://')):
            image_content = {
                "type": "image_url",
                "image_url": {
                    "url": image_path,
                    "detail": detail
                }
            }
        else:
            # Local file - encode to base64
            base64_image = self.encode_image(image_path)
            image_content = {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}",
                    "detail": detail
                }
            }
        
        # Build messages array
        messages = []
        
        # Add system prompt if requested
        if use_system_prompt and self.system_prompt:
            messages.append({
                "role": "system",
                "content": self.system_prompt
            })
        
        # Build user content with image and prompt
        user_content = [
            image_content,
            {
                "type": "text",
                "text": prompt
            }
        ]
        
        # Add context if provided
        if context:
            user_content.append({
                "type": "text", 
                "text": f"Context: {context}"
            })
        
        # Add user message with image and text
        messages.append({
            "role": "user",
            "content": user_content
        })
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.5
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Grok API request failed: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")
            raise
    
    def evaluate_image_dual_prompts(
        self,
        image_path: str,
        tag_initial_prompt: str = None,
        enhancing_tag_prompt: str = None,
        context: str = "",
        model: str = "grok-2-vision-latest",
        detail: str = "high",
        use_system_prompt: bool = True
    ) -> Dict[str, Any]:
        """
        Send two requests with the same image using different prompts.
        
        Args:
            image_path: Path to the image file or URL
            tag_initial_prompt: First prompt for tag initial generation (defaults to system prompt)
            enhancing_tag_prompt: Second prompt for enhancing tag (defaults to system prompt)
            context: Additional context for the analysis
            model: Model to use (default: grok-2-vision-latest)
            detail: Image processing detail level (high, low, auto)
            use_system_prompt: Whether to include system prompt (default: True)
            
        Returns:
            Dictionary containing both responses
        """
        # Use predefined prompts if not provided
        if tag_initial_prompt is None:
            tag_initial_prompt = SYSTEM_PROMPTS["tag_initial_generation"]
        if enhancing_tag_prompt is None:
            enhancing_tag_prompt = SYSTEM_PROMPTS["enhancing_tag_prompt"]
            
        # First request - tag initial generation
        tag_initial_response = self.evaluate_image(
            image_path=image_path,
            prompt=tag_initial_prompt,
            context=context,
            model=model,
            detail=detail,
            use_system_prompt=use_system_prompt
        )

        # Extract content from initial response
        initial_content = ""
        if "choices" in tag_initial_response and len(tag_initial_response["choices"]) > 0:
            initial_content = tag_initial_response["choices"][0]["message"]["content"]
        
        enhanced_prompt = f"{enhancing_tag_prompt}\n\nPrevious tag analysis result:\n{initial_content}"

        enhancing_tag_response = self.evaluate_image(
            image_path=image_path,
            prompt=enhanced_prompt,
            context=context,
            model=model,
            detail=detail,
            use_system_prompt=use_system_prompt
        )
        
        return {
            "tag_initial_response": tag_initial_response,
            "enhancing_tag_response": enhancing_tag_response
        }

    def evaluate_multiple_images(
        self,
        images: List[Union[str, Dict[str, str]]],
        prompt: str,
        context: str = "",
        model: str = "grok-2-vision-latest",
        detail: str = "high",
        use_system_prompt: bool = True
    ) -> Dict[str, Any]:
        """
        Evaluate multiple images using Grok's vision model.
        
        Args:
            images: List of image paths/URLs or dicts with path and detail
            prompt: Text prompt for image evaluation
            context: Additional context for the analysis
            model: Model to use (default: grok-2-vision-latest)
            detail: Default image processing detail level
            use_system_prompt: Whether to include system prompt (default: True)
            
        Returns:
            API response as dictionary
        """
        # Build content starting with prompt
        content = [{"type": "text", "text": prompt}]
        
        # Add context if provided
        if context:
            content.append({"type": "text", "text": f"Context: {context}"})
        
        for img in images:
            if isinstance(img, dict):
                img_path = img.get("path", img.get("url"))
                img_detail = img.get("detail", detail)
            else:
                img_path = img
                img_detail = detail
            
            if img_path.startswith(('http://', 'https://')):
                image_content = {
                    "type": "image_url",
                    "image_url": {
                        "url": img_path,
                        "detail": img_detail
                    }
                }
            else:
                base64_image = self.encode_image(img_path)
                image_content = {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                        "detail": img_detail
                    }
                }
            
            content.append(image_content)
        
        # Build messages array
        messages = []
        
        # Add system prompt if requested
        if use_system_prompt and self.system_prompt:
            messages.append({
                "role": "system",
                "content": self.system_prompt
            })
        
        # Add user message with images
        messages.append({
            "role": "user",
            "content": content
        })
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.5
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Grok API request failed: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")
            raise

    def evaluate_text_only(
        self,
        prompt: str,
        context: str = "",
        model: str = "grok-2-1212",
        temperature: float = 0.3,
        use_system_prompt: bool = False
    ) -> Dict[str, Any]:
        """
        Evaluate text-only prompts using Grok's language model (no image processing).

        Args:
            prompt: Text prompt for evaluation
            context: Additional context for the analysis
            model: Model to use (default: grok-2-1212 for text-only)
            temperature: Randomness in responses (0.0-1.0)
            use_system_prompt: Whether to include system prompt (default: False)

        Returns:
            API response as dictionary
        """
        # Build messages array
        messages = []

        # Add system prompt if requested
        if use_system_prompt and self.system_prompt:
            messages.append({
                "role": "system",
                "content": self.system_prompt
            })

        # Build user content
        user_text = prompt
        if context:
            user_text = f"Context: {context}\n\n{prompt}"

        # Add user message
        messages.append({
            "role": "user",
            "content": user_text
        })

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"Grok API request failed: {e}")
            if hasattr(e.response, 'text'):
                print(f"Response: {e.response.text}")
            raise


def main():
    client = GrokAPIClient()
    
    # Example usage
    try:
        result = client.evaluate_image(
            "path/to/your/image.jpg",
            "What do you see in this image?"
        )
        
        if "choices" in result and len(result["choices"]) > 0:
            analysis = result["choices"][0]["message"]["content"]
            print("Image Analysis:")
            print(analysis)
        else:
            print("No analysis returned")
            
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()