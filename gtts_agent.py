# import os
from smolagents import CodeAgent, DuckDuckGoSearchTool, ChatMessage
from openai import OpenAI
from dotenv import load_dotenv
import io
from pygame import mixer
from gtts import gTTS
import warnings
import os

warnings.filterwarnings("ignore")
load_dotenv()
client = OpenAI()

class OpenRouterModel:
    def __init__(self, model_name, base_url="https://openrouter.ai/api/v1", api_key=None):
        self.client = OpenAI(base_url=base_url, api_key=api_key or None)
        self.model_name = model_name

    def _to_message_dict(self, m):
        if isinstance(m, str):
            return {"role": "user", "content": m}
        if isinstance(m, dict):
            return m
        role = getattr(m, "role", None) or getattr(m, "type", None) or "user"
        content = getattr(m, "content", None) or getattr(m, "text", None) or str(m)
        if isinstance(content, dict):
            content = content.get("text") or str(content)
        return {"role": role, "content": content}

    def _extract_text(self, choice):
        if choice is None:
            return ""
        msg = getattr(choice, "message", None) or (choice.get("message") if isinstance(choice, dict) else None)
        if isinstance(msg, str):
            return msg
        if msg is not None:
            if hasattr(msg, "content"):
                return msg.content
            if isinstance(msg, dict):
                return msg.get("content") or msg.get("text") or str(msg)
        if hasattr(choice, "text"):
            return choice.text
        if isinstance(choice, dict):
            return choice.get("text") or str(choice)
        return str(choice)

    def _normalize_usage(self, usage):
        class TU:
            def __init__(self, in_t=0, out_t=0, tot=0):
                self.input_tokens = int(in_t) if in_t is not None else 0
                self.output_tokens = int(out_t) if out_t is not None else 0
                self.total_tokens = int(tot) if tot is not None else 0
            def __repr__(self):
                return f"<TokenUsage in={self.input_tokens} out={self.output_tokens} tot={self.total_tokens}>"

        if usage is None:
            return TU(0,0,0)

        try:
            prompt = usage.get("prompt_tokens") or usage.get("input_tokens") or usage.get("prompt") or None
            comp = usage.get("completion_tokens") or usage.get("output_tokens") or usage.get("completion") or None
            total = usage.get("total_tokens") or usage.get("total") or None
        except Exception:
            prompt = getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", None)
            comp = getattr(usage, "completion_tokens", None) or getattr(usage, "output_tokens", None)
            total = getattr(usage, "total_tokens", None) or getattr(usage, "total", None)

        def to_int(x):
            try:
                return int(x)
            except Exception:
                return 0

        return TU(to_int(prompt), to_int(comp), to_int(total))

    def generate(self, messages, **kwargs):
        if isinstance(messages, str):
            msg_list = [{"role": "user", "content": messages}]
        else:
            msg_list = [self._to_message_dict(m) for m in messages]

        ALLOWED_ROLES = {"system", "user", "assistant", "developer"}
        normalized_msgs = []
        for m in msg_list:
            role = (m.get("role") if isinstance(m, dict) else getattr(m, "role", None)) or "user"
            if role not in ALLOWED_ROLES:
                role = "assistant"
            content = m.get("content") if isinstance(m, dict) else getattr(m, "content", str(m))
            normalized_msgs.append({"role": role, "content": str(content)})

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=normalized_msgs,
            temperature=kwargs.get("temperature", 0.8),
            max_tokens=kwargs.get("max_new_tokens", 512)
        )

        if hasattr(response, "choices") and len(response.choices) > 0:
            choice = response.choices[0]
        elif isinstance(response, dict) and response.get("choices"):
            choice = response["choices"][0]
        else:
            choice = None

        text = self._extract_text(choice).strip()
        token_usage = self._normalize_usage(getattr(response, "usage", None) or (response.get("usage") if isinstance(response, dict) else None))

        return ChatMessage(role="assistant", content=text, token_usage=token_usage)

MODEL = "meta-llama/llama-3.3-70b-instruct:free"
search_tool = DuckDuckGoSearchTool()
agent = CodeAgent(
    tools=[search_tool],
    model=OpenRouterModel(MODEL)
)

if __name__ == "__main__":
    print("Welcome to the llama 70B Code Agent!")
    print("You can ask it to write code, search for information, or answer questions.")
    while True:
        try:
            prompt = input("Enter your prompt: \n")
            response = agent.run(prompt).split("Final Answer:")[-1].strip()
            tts = gTTS(response, lang='en')
            
            wav_path = "./audio/assistant_output.wav"
            tts.save("assistant_output.mp3")
            
            os.system(f"ffmpeg -y -i assistant_output.mp3 {wav_path}")
            print(f"WAV saved as {wav_path} (ready for Rhubarb)")
            os.system("rhubarb -f json ./audio/assistant_output.wav -o lipsync.json")
            
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            
            mixer.init()
            mixer.music.load(fp, 'mp3')
            # mixer.music.play()

            while mixer.music.get_busy():
                pass
            
        except KeyboardInterrupt:
            print("\nExiting the program. Goodbye!")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            continue
