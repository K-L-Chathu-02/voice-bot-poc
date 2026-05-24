import os
import sqlite3
import azure.cognitiveservices.speech as speechsdk
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.tools import tool
from langchain.agents import create_agent

# 1. Connect to the database globally so the tool can use it
conn = sqlite3.connect('slt_mock_data.db', check_same_thread=False)
cursor = conn.cursor()

# 2. Define the tool for the LLM
@tool
def get_broadband_packages(max_price: float = None, min_data: int = None) -> str:
    """
    Use this tool to look up SLT broadband packages based on price or data limits.
    Pass max_price to filter by budget, or min_data to filter by data volume.
    """
    query = "SELECT name, data_limit_gb, price_lkr FROM packages WHERE 1=1"
    params = []
    
    if max_price:
        query += " AND price_lkr <= ?"
        params.append(max_price)
    if min_data:
        query += " AND data_limit_gb >= ?"
        params.append(min_data)
        
    cursor.execute(query, params)
    results = cursor.fetchall()
    
    # Return raw data to the LLM
    return str(results) if results else "No packages found matching those criteria."
# --- TOOL 2: Check Balance ---
@tool
def check_account_balance(phone_number: str) -> str:
    """
    Use this to check a customer's outstanding bill and remaining data balance. 
    You MUST ask the user for their phone number before calling this tool.
    """
    cursor.execute("SELECT name, outstanding_bill_lkr, remaining_data_gb FROM customers WHERE phone_number = ?", (phone_number,))
    result = cursor.fetchone()
    
    if result:
        return f"Customer {result[0]} owes {result[1]} LKR and has {result[2]} GB of data remaining."
    else:
        return f"No account found for phone number {phone_number}."

# --- TOOL 3: Report Fault ---
@tool
def report_network_fault(phone_number: str, issue_description: str) -> str:
    """
    Use this to log a network issue, router problem, or internet outage. 
    You MUST ask the user for their phone number and the issue description before calling this tool.
    """
    # Insert the new ticket into the database
    cursor.execute(
        "INSERT INTO fault_tickets (phone_number, issue_description, status) VALUES (?, ?, 'OPEN')", 
        (phone_number, issue_description)
    )
    conn.commit()
    
    # Get the auto-generated ticket ID
    ticket_id = cursor.lastrowid
    return f"Successfully created support ticket #{ticket_id}. The engineering team has been notified."


def main():
    # 1. Check for API Keys
    if not os.environ.get("OPENAI_API_KEY") or not os.environ.get("SPEECH_KEY") or not os.environ.get("SPEECH_REGION"):
        print("ERROR: Missing environment variables.")
        return

    # 2. Ask the user for their language (The IVR Workaround)
    print("\n--- SLT Voice Bot PoC ---")
    print("Select your language for this interaction:")
    print("1. English")
    print("2. Sinhala")
    print("3. Tamil")
    choice = input("Enter 1, 2, or 3: ")
    
    stt_lang_map = {"1": "en-US", "2": "si-LK", "3": "ta-LK"}
    tts_voice_map = {"1": "en-US-AvaNeural", "2": "si-LK-ThiliniNeural", "3": "ta-LK-PallaviNeural"}
    
    selected_lang = stt_lang_map.get(choice, "en-US")
    selected_voice = tts_voice_map.get(choice, "en-US-AvaNeural")

    # 3. Set up the LangChain Agent
    llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash", temperature=0)
    tools = [get_broadband_packages, check_account_balance, report_network_fault]    
    agent = create_agent(
        model=llm, 
        tools=tools,
        system_prompt=f"""You are an SLT customer service voice assistant. 
        You have access to tools to look up broadband packages. 
        CRITICAL RULE: The user is speaking in language code: {selected_lang}. 
        You MUST reply naturally in that exact language. 
        Never use Markdown, bullet points, or tables. Respond with natural spoken text only."""
    )

    # 4. Set up Azure Speech
    speech_config = speechsdk.SpeechConfig(
        subscription=os.environ.get("SPEECH_KEY"), 
        region=os.environ.get("SPEECH_REGION")
    )
    speech_config.speech_recognition_language = selected_lang
    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
    
    recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config, 
        audio_config=audio_config
    )
    
    # Configure Synthesizer once
    speech_config.speech_synthesis_voice_name = selected_voice
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)

    # --- MEMORY INITIALIZATION ---
    # This array will hold the entire conversation history
    chat_history = []
    
    print(f"\n📞 Call Connected in {selected_lang}... (Say 'bye' or press Ctrl+C to hang up)")

    # --- THE CONVERSATION LOOP ---
    while True:
        print("\n🎤 [Listening...]")
        
        # This pauses the loop and listens until the user stops speaking
        result = recognizer.recognize_once_async().get()

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            user_text = result.text
            print(f"\n[User Said]: {user_text}")

            # Exit condition: Hang up if the user says bye
            exit_words = ["bye", "goodbye", "exit", "stop", "බයි", "ස්තූතියි", "நன்றி"]
            if any(word in user_text.lower() for word in exit_words):
                print("\n[Hanging up the call...]")
                break

            # 1. Add user's new question to the memory array
            chat_history.append({"role": "user", "content": user_text})

            print("\n[Thinking...]")
            # 2. Pass the ENTIRE memory array to the LLM so it has full context
            agent_result = agent.invoke({"messages": chat_history})
            raw_content = agent_result["messages"][-1].content
            
            # Extract text safely
            if isinstance(raw_content, list):
                agent_response = raw_content[0].get("text", "")
            else:
                agent_response = raw_content
                
            print(f"\n[Bot Answering]: {agent_response}")

            # 3. Add the Bot's answer back into the memory array for the next loop
            chat_history.append({"role": "assistant", "content": agent_response})

            # 4. Speak the response. The .get() ensures the mic stays muted until the bot finishes speaking!
            synthesizer.speak_text_async(agent_response).get()
            
        elif result.reason == speechsdk.ResultReason.NoMatch:
            print("[Bot didn't hear anything. Still listening...]")
        elif result.reason == speechsdk.ResultReason.Canceled:
            print("\n[Call Dropped: Speech Recognition canceled]")
            break

if __name__ == "__main__":
    main()









# def main():
#     # 1. Check for API Keys
#     if not os.environ.get("GOOGLE_API_KEY") or not os.environ.get("SPEECH_KEY") or not os.environ.get("SPEECH_REGION"):
#         print("ERROR: Missing environment variables.")
#         return

#     # 2. Ask the user for their language (The IVR Workaround)
#     print("\n--- SLT Voice Bot PoC ---")
#     print("Select your language for this interaction:")
#     print("1. English")
#     print("2. Sinhala")
#     print("3. Tamil")
#     choice = input("Enter 1, 2, or 3: ")
    
#     # Map the choice to the correct Azure Language Codes
#     stt_lang_map = {"1": "en-US", "2": "si-LK", "3": "ta-LK"}
#     tts_voice_map = {"1": "en-US-AvaNeural", "2": "si-LK-ThiliniNeural", "3": "ta-LK-PallaviNeural"}
    
#     selected_lang = stt_lang_map.get(choice, "en-US")
#     selected_voice = tts_voice_map.get(choice, "en-US-AvaNeural")

#     # 3. Set up the LangChain Agent
#     llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash", temperature=0)
#     tools = [get_broadband_packages]
    
#     agent = create_agent(
#         model=llm, 
#         tools=tools,
#         system_prompt=f"""You are an SLT customer service voice assistant. 
#         You have access to tools to look up broadband packages. 
#         CRITICAL RULE: The user is speaking in language code: {selected_lang}. 
#         You MUST reply naturally in that exact language. 
#         Never use Markdown, bullet points, or tables. Respond with natural spoken text only."""
#     )

#     # 4. Set up Azure Speech-to-Text (Hardcoded to the chosen language)
#     speech_config = speechsdk.SpeechConfig(
#         subscription=os.environ.get("SPEECH_KEY"), 
#         region=os.environ.get("SPEECH_REGION")
#     )
#     speech_config.speech_recognition_language = selected_lang
#     audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
    
#     recognizer = speechsdk.SpeechRecognizer(
#         speech_config=speech_config, 
#         audio_config=audio_config
#     )

#     print(f"\n🎤 Listening in {selected_lang}... Speak now!")
#     result = recognizer.recognize_once_async().get()

#     if result.reason == speechsdk.ResultReason.RecognizedSpeech:
#         user_text = result.text
#         print(f"\n[User Said]: {user_text}")

#         # 5. Pass text to the LLM
#         print("\n[Thinking...]")
#         agent_result = agent.invoke({"messages": [{"role": "user", "content": user_text}]})
#         raw_content = agent_result["messages"][-1].content
        
#         # Extract the string if LangChain returns a list block
#         if isinstance(raw_content, list):
#             agent_response = raw_content[0].get("text", "")
#         else:
#             agent_response = raw_content
            
#         print(f"\n[Bot Answering]: {agent_response}")

#         # 6. Set up Azure Text-to-Speech
#         speech_config.speech_synthesis_voice_name = selected_voice
#         synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
#         synthesizer.speak_text_async(agent_response).get()
        
#     elif result.reason == speechsdk.ResultReason.NoMatch:
#         print("Could not understand the audio.")
#     elif result.reason == speechsdk.ResultReason.Canceled:
#         cancellation_details = result.cancellation_details
#         print(f"Speech Recognition canceled: {cancellation_details.reason}")
#         if cancellation_details.reason == speechsdk.CancellationReason.Error:
#             print(f"Error details: {cancellation_details.error_details}")

# if __name__ == "__main__":
#     main()







