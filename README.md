# AI Chat Interface with OpenRouter

A visually appealing chat interface that uses OpenRouter API to access various AI models, with O4 Mini High as the default model. The application includes web search integration, system prompt customization, and settings persistence.

## Features

- Chat with various AI models through OpenRouter API
- Default model: O4 Mini High
- Web search integration using requests and BeautifulSoup
- System prompt customization
- SQLite database for conversation history
- Customizable API base URL
- Save settings functionality
- Comprehensive model selection with all OpenRouter models
- Visually appealing UI with colorful CSS

## Installation

1. Clone this repository
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

3. Get an API key from [OpenRouter](https://openrouter.ai/)

## Usage

1. Run the application:

```bash
python app.py
```

2. Open the provided URL in your web browser
3. Enter your OpenRouter API key in the settings panel
4. Customize the API base URL if needed (default is "https://openrouter.ai/api/v1")
5. Click "Save Settings" to store your preferences for future sessions
6. Start chatting!

### Web Search Integration

- To search the web, start your message with `search:` followed by your query
  - Example: `search: latest AI developments`

- To fetch content from a webpage, start your message with `url:` followed by the URL
  - Example: `url: https://example.com`

### System Prompts

You can customize the AI's behavior by setting a system prompt in the settings panel. For example:

- "You are a helpful coding assistant specialized in Python"
- "You are a creative writing assistant who helps with storytelling"
- "You are a knowledgeable research assistant who provides detailed information"

## Models Available

The application includes a comprehensive list of models available through OpenRouter:

### Default Model
- O4 Mini High (Default)

### Anthropic Models
- Claude 3 Opus
- Claude 3 Sonnet
- Claude 3 Haiku
- Claude 2

### OpenAI Models
- GPT-4o
- GPT-4 Turbo
- GPT-4
- GPT-3.5 Turbo

### Meta Models
- Llama 3 70B
- Llama 3 8B
- Llama 2 70B
- Llama 2 13B

### Mistral Models
- Mistral Large
- Mistral Medium
- Mistral Small

### Google Models
- Gemini Pro
- Gemini Flash

### Cohere Models
- Cohere Command R
- Cohere Command R+

### Other Models
- Perplexity Online
- Groq Llama 3 70B
- Groq Mixtral 8x7B

## Requirements

- Python 3.7+
- Gradio
- Requests
- BeautifulSoup4
- SQLite3