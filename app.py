import gradio as gr
import sqlite3
import requests
import json
import os
import pickle
from bs4 import BeautifulSoup
from datetime import datetime
from duckduckgo_search import DDGS
from fastapi import Request

# Initialize database
def init_db():
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        user_message TEXT,
        assistant_message TEXT,
        model TEXT,
        system_prompt TEXT
    )
    ''')
    conn.commit()
    conn.close()

# Save conversation to database
def save_to_db(user_message, assistant_message, model, system_prompt):
    conn = sqlite3.connect('chat_history.db')
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO conversations (timestamp, user_message, assistant_message, model, system_prompt) VALUES (?, ?, ?, ?, ?)",
        (timestamp, user_message, assistant_message, model, system_prompt)
    )
    conn.commit()
    conn.close()

# Web search function using DuckDuckGo API (now using duckduckgo-search for real results)
def web_search(query, num_results=5):
    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=num_results):
                results.append(r)
                if len(results) >= num_results:
                    break
        if not results:
            return f"No search results found for '{query}'. Try refining your search terms."
        formatted_results = ""
        for i, result in enumerate(results, 1):
            formatted_results += f"{i}. {result.get('title', '[No title]')[:120]}\n"
            formatted_results += f"   URL: {result.get('href', result.get('url', '[No URL]'))}\n"
            snippet = result.get('body') or result.get('snippet')
            if snippet:
                formatted_results += f"   {snippet[:400]}\n\n"
            else:
                formatted_results += f"   [No description available]\n\n"
        return formatted_results
    except Exception as e:
        return f"Error during web search: {str(e)}"

# Wikipedia search as a fallback
def wikipedia_search(query, num_results=3):
    try:
        # Wikipedia API endpoint
        search_url = "https://en.wikipedia.org/w/api.php"
        
        # First, search for relevant articles
        search_params = {
            'action': 'query',
            'list': 'search',
            'srsearch': query,
            'format': 'json',
            'srlimit': num_results
        }
        
        response = requests.get(search_url, params=search_params)
        if response.status_code != 200:
            return None
        
        data = response.json()
        if 'query' not in data or 'search' not in data['query']:
            return None
        
        search_results = []
        
        # For each search result, get a summary
        for result in data['query']['search']:
            title = result['title']
            page_id = result['pageid']
            
            # Get the summary for this article
            summary_params = {
                'action': 'query',
                'prop': 'extracts',
                'exintro': True,
                'explaintext': True,
                'pageids': page_id,
                'format': 'json'
            }
            
            summary_response = requests.get(search_url, params=summary_params)
            if summary_response.status_code == 200:
                summary_data = summary_response.json()
                if 'query' in summary_data and 'pages' in summary_data['query']:
                    page_data = summary_data['query']['pages'][str(page_id)]
                    snippet = page_data.get('extract', '')
                    
                    # Truncate long snippets
                    if len(snippet) > 300:
                        snippet = snippet[:300] + "..."
                    
                    search_results.append({
                        'title': title,
                        'link': f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                        'snippet': snippet
                    })
        
        # Format results
        formatted_results = "Wikipedia Search Results:\n\n"
        for i, result in enumerate(search_results, 1):
            formatted_results += f"{i}. {result['title']}\n"
            formatted_results += f"   URL: {result['link']}\n"
            if result['snippet']:
                formatted_results += f"   {result['snippet']}\n\n"
            else:
                formatted_results += f"   [No description available]\n\n"
        
        return formatted_results if search_results else None
    
    except Exception as e:
        print(f"Wikipedia search error: {str(e)}")
        return None

# Function to get webpage content
def get_webpage_content(url):
    try:
        # Check if URL has a scheme, add https:// if not
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Set a timeout to avoid hanging on slow websites
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return f"Error: Could not fetch the webpage. Status code: {response.status_code}"
            
        # Try to detect the encoding
        if response.encoding == 'ISO-8859-1':
            # Try to find better encoding
            possible_encoding = response.apparent_encoding
            if possible_encoding and possible_encoding.lower() != 'iso-8859-1':
                response.encoding = possible_encoding
                
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try to get the main content
        main_content = None
        
        # Look for common content containers
        for container in ['main', 'article', 'div.content', 'div.main-content', '#content', '#main']:
            content = soup.select_one(container)
            if content and len(content.get_text(strip=True)) > 200:  # Ensure it has substantial content
                main_content = content
                break
        
        # If no main content container found, use the whole body
        if not main_content:
            main_content = soup
        
        # Remove unwanted elements
        for element in main_content(["script", "style", "nav", "header", "footer", "aside", "iframe", "noscript", 
                                    "meta", "button", "svg", "form", "input", "textarea"]):
            element.extract()
            
        # Remove elements with common ad/nav/sidebar class names
        for element in main_content.select('.ad, .ads, .advertisement, .sidebar, .nav, .menu, .comment, .footer, .header'):
            element.extract()
            
        # Get text
        text = main_content.get_text()
        
        # Process text
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Remove blank lines and join with newlines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Remove excessive newlines (more than 2 in a row)
        import re
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Get page title
        title = soup.title.string if soup.title else "No title"
        
        # Format the output with title and URL
        formatted_text = f"Title: {title.strip()}\nURL: {url}\n\n{text}"
        
        # Limit text length to avoid token limits
        if len(formatted_text) > 8000:
            formatted_text = formatted_text[:8000] + "...\n[Content truncated due to length]"
            
        return formatted_text
    
    except requests.exceptions.Timeout:
        return f"Error: Request to {url} timed out after 10 seconds."
    except requests.exceptions.ConnectionError:
        return f"Error: Could not connect to {url}. Please check the URL and try again."
    except requests.exceptions.MissingSchema:
        return f"Error: Invalid URL format for {url}. Make sure it includes http:// or https://."
    except Exception as e:
        return f"Error fetching webpage: {str(e)}"

# Function to fetch available models from OpenRouter
def fetch_available_models(api_key, base_url="https://openrouter.ai/api/v1"):
    try:
        url = f"{base_url}/models"
        
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            models_data = response.json()
            available_models = {}
            
            if 'data' in models_data:
                for model in models_data['data']:
                    if 'id' in model and 'name' in model:
                        # Use the model's name as the key and ID as the value
                        available_models[model['name']] = model['id']
            
            return available_models
        else:
            print(f"Error fetching models: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error fetching models: {str(e)}")
        return None

# OpenRouter API call
def chat_with_openrouter(messages, model, api_key, base_url="https://openrouter.ai/api/v1"):
    url = f"{base_url}/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = {
        "model": model,
        "messages": messages
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response_data = response.json()
        
        if 'choices' in response_data and len(response_data['choices']) > 0:
            return response_data['choices'][0]['message']['content']
        else:
            return f"Error: {json.dumps(response_data)}"
    except Exception as e:
        return f"Error: {str(e)}"

# Chat function for Gradio
def chat(message, history, model, system_prompt, api_key, enable_web_search, base_url):
    try:
        # Check if API key is provided
        if not api_key:
            return "Error: Please provide an OpenRouter API key in the settings panel."
            
        # Format messages for API
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add chat history
        for human, assistant in history:
            messages.append({"role": "user", "content": human})
            messages.append({"role": "assistant", "content": assistant})
        
        # Add current message
        current_message = message
        
        # Check if web search is enabled and message contains a search command
        if enable_web_search and message.lower().startswith("search:"):
            search_query = message[7:].strip()
            if not search_query:
                return "Please provide a search query after 'search:'"
            
            # Inform the user that search is in progress
            print(f"Searching for: {search_query}")
            
            # Perform the search
            search_results = web_search(search_query)
            
            # Create a prompt that helps the model use the search results effectively
            current_message = (
                f"The user wants information about: {search_query}\n\n"
                f"Here are some search results from DuckDuckGo and Wikipedia to help you answer:\n\n"
                f"{search_results}\n\n"
                f"Based on these search results, please provide a comprehensive and accurate response to the user's query. "
                f"Cite specific information from the search results when possible. "
                f"If the search results don't contain enough information, acknowledge the limitations "
                f"and provide the best answer you can with the available information."
            )
        
        # Check if the message is a URL to fetch content
        elif enable_web_search and message.lower().startswith("url:"):
            url = message[4:].strip()
            if not url:
                return "Please provide a URL after 'url:'"
            
            # Inform the user that content fetching is in progress
            print(f"Fetching content from: {url}")
            
            # Fetch the webpage content
            webpage_content = get_webpage_content(url)
            
            # Create a prompt that helps the model summarize the content effectively
            current_message = (
                f"The user wants information from this URL: {url}\n\n"
                f"Here's the content of the webpage:\n\n{webpage_content}\n\n"
                f"Please provide a comprehensive summary of this webpage content. "
                f"Focus on the main points, key information, and any important details. "
                f"If the content is technical or specialized, explain it in a way that's easy to understand. "
                f"If there are any limitations in the extracted content, acknowledge them in your response."
            )
        
        messages.append({"role": "user", "content": current_message})
        
        # Get response from OpenRouter
        response = chat_with_openrouter(messages, model, api_key, base_url)
        
        # Save to database
        try:
            save_to_db(message, response, model, system_prompt)
        except Exception as db_error:
            print(f"Warning: Could not save to database: {str(db_error)}")
        
        return response
        
    except Exception as e:
        error_message = f"An error occurred: {str(e)}"
        print(error_message)
        return error_message

# Available models
MODELS = {
    "O4 Mini High (Default)": "anthropic/claude-3-opus",
    # Anthropic Models
    "Claude 3 Opus": "anthropic/claude-3-opus",
    "Claude 3 Sonnet": "anthropic/claude-3-sonnet",
    "Claude 3 Haiku": "anthropic/claude-3-haiku",
    "Claude 2": "anthropic/claude-2",
    # OpenAI Models
    "GPT-4o": "openai/gpt-4o",
    "GPT-4 Turbo": "openai/gpt-4-turbo",
    "GPT-4": "openai/gpt-4",
    "GPT-3.5 Turbo": "openai/gpt-3.5-turbo",
    # Meta Models
    "Llama 3 70B": "meta-llama/llama-3-70b-instruct",
    "Llama 3 8B": "meta-llama/llama-3-8b-instruct",
    "Llama 2 70B": "meta-llama/llama-2-70b-chat",
    "Llama 2 13B": "meta-llama/llama-2-13b-chat",
    # Mistral Models
    "Mistral Large": "mistralai/mistral-large-latest",
    "Mistral Medium": "mistralai/mistral-medium-latest",
    "Mistral Small": "mistralai/mistral-small-latest",
    # Google Models
    "Gemini Pro": "google/gemini-pro",
    "Gemini Flash": "google/gemini-flash",
    # Cohere Models
    "Cohere Command R": "cohere/command-r",
    "Cohere Command R+": "cohere/command-r-plus",
    # Other Models
    "Perplexity Online": "perplexity/online",
    "Groq Llama 3 70B": "groq/llama3-70b-8192",
    "Groq Mixtral 8x7B": "groq/mixtral-8x7b-32768"
}

# Settings management
def save_settings(api_key, base_url, system_prompt, enable_web_search):
    settings = {
        "api_key": api_key,
        "base_url": base_url,
        "system_prompt": system_prompt,
        "enable_web_search": enable_web_search
    }
    try:
        with open('settings.pkl', 'wb') as f:
            pickle.dump(settings, f)
        return "Settings saved successfully!"
    except Exception as e:
        return f"Error saving settings: {str(e)}"

def load_settings():
    try:
        if os.path.exists('settings.pkl'):
            with open('settings.pkl', 'rb') as f:
                settings = pickle.load(f)
            # Ensure backward compatibility
            if "enable_web_search" not in settings:
                settings["enable_web_search"] = True
            return settings
        else:
            return {
                "api_key": "",
                "base_url": "https://openrouter.ai/api/v1",
                "system_prompt": "",
                "enable_web_search": True
            }
    except Exception as e:
        print(f"Error loading settings: {str(e)}")
        return {
            "api_key": "",
            "base_url": "https://openrouter.ai/api/v1",
            "system_prompt": "",
            "enable_web_search": True
        }

# Custom CSS
custom_css = """
:root {
    --primary-color: #6366f1;
    --secondary-color: #8b5cf6;
    --accent-color: #ec4899;
    --background-color: #f8fafc;
    --text-color: #1e293b;
    --card-bg: #ffffff;
    --border-color: #e2e8f0;
    --shadow-color: rgba(0, 0, 0, 0.1);
}

body {
    background-color: var(--background-color);
    color: var(--text-color);
    font-family: 'Inter', sans-serif;
}

.gradio-container {
    max-width: 1200px !important;
    margin: 0 auto;
}

.main-container {
    border-radius: 12px;
    box-shadow: 0 10px 25px var(--shadow-color);
    background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
    padding: 2px;
    margin: 20px 0;
}

.inner-container {
    background-color: var(--card-bg);
    border-radius: 10px;
    padding: 20px;
}

.chat-container {
    border-radius: 10px;
    background-color: var(--card-bg);
    border: 1px solid var(--border-color);
}

.message-user {
    background-color: #e0e7ff;
    border-radius: 18px 18px 0 18px;
    padding: 12px 16px;
    margin: 8px;
    box-shadow: 0 2px 5px var(--shadow-color);
}

.message-bot {
    background-color: #ddd6fe;
    border-radius: 18px 18px 18px 0;
    padding: 12px 16px;
    margin: 8px;
    box-shadow: 0 2px 5px var(--shadow-color);
}

.input-container {
    border: 2px solid var(--border-color);
    border-radius: 8px;
    transition: border-color 0.3s ease;
}

.input-container:focus-within {
    border-color: var(--primary-color);
}

button.primary {
    background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
    border: none;
    border-radius: 8px;
    color: white;
    padding: 10px 20px;
    font-weight: 600;
    transition: transform 0.2s, box-shadow 0.2s;
}

button.primary:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px var(--shadow-color);
}

.settings-container {
    background-color: var(--card-bg);
    border-radius: 10px;
    border: 1px solid var(--border-color);
    padding: 16px;
    margin-top: 16px;
}

.settings-title {
    font-weight: 600;
    color: var(--primary-color);
    margin-bottom: 12px;
}

select, input[type="text"], textarea {
    border: 1px solid var(--border-color);
    border-radius: 6px;
    padding: 8px 12px;
    transition: border-color 0.3s ease;
}

select:focus, input[type="text"]:focus, textarea:focus {
    border-color: var(--primary-color);
    outline: none;
}

.footer {
    text-align: center;
    margin-top: 20px;
    font-size: 0.9rem;
    color: #64748b;
}
"""

# Initialize database
init_db()

ALLOWED_IP = os.environ.get("ALLOWED_IP", "YOUR_IP_ADDRESS")  # Replace with your actual IP or set as env var
API_KEY = os.environ.get("API_KEY", "your_api_key_here")  # Set your API key here or as env var

def is_request_from_allowed_ip(request: Request):
    client_ip = request.client.host
    return client_ip == ALLOWED_IP

# Create Gradio interface
with gr.Blocks(css=custom_css) as demo:
    gr.HTML("""
    <div style="text-align: center; margin-bottom: 1rem">
        <h1 style="font-size: 2.5rem; font-weight: 700; background: linear-gradient(135deg, #6366f1, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            AI Chat with OpenRouter
        </h1>
        <p style="font-size: 1.1rem; color: #64748b;">
            Chat with various AI models using OpenRouter API
        </p>
    </div>
    """)
    
    # Load saved settings
    saved_settings = load_settings()
    
    # Try to fetch available models if API key is provided
    dynamic_models = None
    if saved_settings["api_key"]:
        dynamic_models = fetch_available_models(saved_settings["api_key"], saved_settings["base_url"])
    
    # Use fetched models if available, otherwise use the predefined list
    model_choices = list(dynamic_models.keys()) if dynamic_models else list(MODELS.keys())
    default_model = "Claude 3 Opus" if "Claude 3 Opus" in model_choices else model_choices[0]
    
    with gr.Row():
        with gr.Column(scale=7):
            chatbot = gr.Chatbot(
                label="Conversation",
                elem_classes="chat-container",
                bubble_full_width=False,
                avatar_images=(None, "https://api.dicebear.com/7.x/bottts/svg?seed=openrouter"),
                height=600
            )
            
            with gr.Row():
                msg = gr.Textbox(
                    placeholder="Type your message here... (Use 'search: query' for web search or 'url: website' to fetch webpage content)",
                    label="Message",
                    elem_classes="input-container",
                    scale=9
                )
                submit_btn = gr.Button("Send", variant="primary", elem_classes="primary", scale=1)
            
            with gr.Accordion("How to use", open=False):
                gr.Markdown("""
                ## Basic Usage
                - Type your message and press Send or Enter
                - Your conversation history is saved automatically
                
                ## Web Search Integration
                - Start your message with `search:` followed by your query to search the web
                - Uses DuckDuckGo and Wikipedia for reliable, free search results
                - Example: `search: latest AI developments`
                
                ## Webpage Content Fetching
                - Start your message with `url:` followed by a website URL to fetch its content
                - The AI will summarize the content for you
                - Example: `url: https://example.com`
                
                ## System Prompts
                - Use the System Prompt field to set context for the AI
                - Example: "You are a helpful coding assistant specialized in Python"
                
                ## Settings
                - Your API key and other settings can be saved for future sessions
                - Click "Save Settings" to store your preferences
                - Click "Refresh Models List" to update available models from OpenRouter
                """)
        
        with gr.Column(scale=3):
            with gr.Group(elem_classes="settings-container"):
                gr.HTML("<div class='settings-title'>Chat Settings</div>")
                api_key = gr.Textbox(
                    label="OpenRouter API Key",
                    placeholder="Enter your OpenRouter API key",
                    type="password",
                    value=saved_settings["api_key"]
                )
                base_url = gr.Textbox(
                    label="API Base URL",
                    placeholder="OpenRouter API base URL",
                    value=saved_settings["base_url"]
                )
                model_dropdown = gr.Dropdown(
                    choices=model_choices,
                    label="Select Model",
                    value=default_model
                )
                system_prompt = gr.Textbox(
                    label="System Prompt",
                    placeholder="Optional: Set a system prompt to guide the AI's behavior",
                    lines=3,
                    value=saved_settings["system_prompt"]
                )
                enable_web_search = gr.Checkbox(
                    label="Enable Web Search",
                    value=saved_settings["enable_web_search"],
                    info="Allow using 'search:' and 'url:' commands"
                )
                with gr.Row():
                    save_settings_btn = gr.Button("Save Settings", variant="primary", elem_classes="primary")
                    clear_btn = gr.Button("Clear Conversation", variant="secondary")
                refresh_models_btn = gr.Button("Refresh Models List", variant="secondary")
                save_notification = gr.Textbox(
                    visible=False,
                    label="Notification"
                )
            # Add read-only box for previous conversations
            previous_convos = gr.Textbox(
                label="Previous Conversations (Read Only)",
                lines=20,
                interactive=False,
                value="Loading..."
            )
    
    gr.HTML("""
    <div class="footer">
        <p>Powered by OpenRouter API • Using Gradio for UI • Web search with BeautifulSoup</p>
    </div>
    """)
    
    # Set up event handlers
    def respond(message, chat_history, model_name, system_prompt, api_key, enable_web_search, base_url):
        try:
            if not message.strip():
                return "", chat_history
            # Try to get model ID from dynamic models first, then fall back to predefined models
            if dynamic_models and model_name in dynamic_models:
                model_id = dynamic_models[model_name]
            elif model_name in MODELS:
                model_id = MODELS[model_name]
            else:
                # If model not found, use Claude 3 Opus as fallback
                model_id = "anthropic/claude-3-opus"

            # If search: command, show results as a separate message
            if enable_web_search and message.lower().startswith("search:"):
                search_query = message[7:].strip()
                if not search_query:
                    chat_history.append((message, "Please provide a search query after 'search:'"))
                    return "", chat_history
                search_results = web_search(search_query)
                chat_history.append((message, search_results))
                # Now get the model's answer using the search results as context
                bot_message = chat(message, chat_history[:-1], model_id, system_prompt, api_key, enable_web_search, base_url)
                chat_history.append(("[AI Response]", bot_message))
                return "", chat_history
            else:
                bot_message = chat(message, chat_history, model_id, system_prompt, api_key, enable_web_search, base_url)
                chat_history.append((message, bot_message))
                return "", chat_history
        except Exception as e:
            error_message = f"Error: {str(e)}"
            chat_history.append((message, error_message))
            return "", chat_history
    
    def save_user_settings(api_key, base_url, system_prompt, enable_web_search):
        result = save_settings(api_key, base_url, system_prompt, enable_web_search)
        return gr.update(value=result, visible=True)
    
    def refresh_models_list(api_key, base_url):
        if not api_key:
            return gr.update(value="Please provide an API key to fetch models.", visible=True), gr.update()
        
        fetched_models = fetch_available_models(api_key, base_url)
        if fetched_models:
            model_names = list(fetched_models.keys())
            default = "Claude 3 Opus" if "Claude 3 Opus" in model_names else model_names[0]
            return gr.update(value="Models list refreshed successfully!", visible=True), gr.update(choices=model_names, value=default)
        else:
            return gr.update(value="Failed to fetch models. Check your API key and connection.", visible=True), gr.update()
    
    msg.submit(
        respond,
        [msg, chatbot, model_dropdown, system_prompt, api_key, enable_web_search, base_url],
        [msg, chatbot]
    )
    
    submit_btn.click(
        respond,
        [msg, chatbot, model_dropdown, system_prompt, api_key, enable_web_search, base_url],
        [msg, chatbot]
    )
    
    save_settings_btn.click(
        save_user_settings,
        [api_key, base_url, system_prompt, enable_web_search],
        [save_notification]
    )
    
    refresh_models_btn.click(
        refresh_models_list,
        [api_key, base_url],
        [save_notification, model_dropdown]
    )
    
    clear_btn.click(lambda: None, None, chatbot, queue=False)

    # Function to fetch and format all previous conversations
    def get_all_conversations():
        conn = sqlite3.connect('chat_history.db')
        cursor = conn.cursor()
        cursor.execute("SELECT user_message, assistant_message FROM conversations ORDER BY id DESC")
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return "No previous conversations."
        formatted = []
        for user, assistant in rows:
            formatted.append(f"User: {user}\nAssistant: {assistant}\n{'-'*30}")
        return '\n'.join(formatted)

    # Set the value of the previous conversations box on load
    previous_convos.value = get_all_conversations()

    # Add a manual refresh button for chat history
    refresh_convos_btn = gr.Button("Refresh Chat History")
    refresh_convos_btn.click(
        lambda: get_all_conversations(),
        None,
        previous_convos
    )

# Launch the app
if __name__ == "__main__":
    demo.launch()