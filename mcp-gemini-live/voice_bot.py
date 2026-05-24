# voice_bot.py
import asyncio
import os
import pyaudio
from google import genai
from google.genai import types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Audio constants for Gemini Live API
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 512

async def main():
    # 1. Connect to the local MCP Server
    server_params = StdioServerParameters(
        command="python", # Or "uv run" depending on your environment
        args=["mcp_server.py"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as mcp_session:
            await mcp_session.initialize()

            # A. Fetch tools from the MCP server
            mcp_tools_response = await mcp_session.list_tools()

            # B. Initialize an empty list to hold Gemini-formatted tools
            function_declarations = []

            # C. Map each MCP tool to a Gemini FunctionDeclaration
            for mcp_tool in mcp_tools_response.tools:
                print(f"Mapping tool from MCP: {mcp_tool.name}")
                
                gemini_func = types.FunctionDeclaration(
                    name=mcp_tool.name,
                    description=mcp_tool.description,
                    parameters=mcp_tool.inputSchema 
                )
                function_declarations.append(gemini_func)

            # D. Wrap the declarations in the final format Gemini expects
            gemini_tools = [{"function_declarations": function_declarations}]
            # ============================================================

            # 2. Connect to Gemini Live API using the mapped tools
            ai_client = genai.Client() 
            
            config = types.LiveConnectConfig(
                response_modalities=[types.Modality.AUDIO],
                tools=gemini_tools, # <-- Pass the mapped tools here!
                system_instruction=types.Content(parts=[
                    types.Part.from_text(text="You are an SLT customer service voice assistant. Speak naturally in Sinhala.")
                ])
            )

            print("Connecting to Gemini Live...")
            async with ai_client.aio.live.connect(model="gemini-3.1-flash-live-preview", config=config) as gemini_session:
                # ... (Rest of the file: PyAudio setup and concurrent loops remain unchanged)


            
            # # Fetch tools from the MCP server
            # mcp_tools_response = await mcp_session.list_tools()
            
            # # (Note: In a full implementation, you would map mcp_tools_response schemas 
            # # into google.genai.types.Tool objects here)
            # gemini_tools = [{"function_declarations": [...]}] # Placeholder for mapped tools

            # # 2. Connect to Gemini Live API
            # ai_client = genai.Client() # Uses GEMINI_API_KEY env var
            
            # config = types.LiveConnectConfig(
            #     response_modalities=[types.Modality.AUDIO],
            #     system_instruction=types.Content(parts=[
            #         types.Part.from_text("You are an SLT customer service voice assistant. Speak naturally in Sinhala.")
            #     ]),
            #     # Pass the tools fetched from MCP to Gemini
            #     tools=gemini_tools 
            # )

            # print("Connecting to Gemini Live...")
            #async with ai_client.aio.live.connect(model="gemini-2.0-flash-exp", config=config) as gemini_session:
                print("Connected! Start speaking...")
                
                # 3. Setup PyAudio streams
                p = pyaudio.PyAudio()
                mic_stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
                speaker_stream = p.open(format=FORMAT, channels=CHANNELS, rate=24000, output=True) # Gemini outputs at 24kHz
                # --- NEW: Flag to pause the mic during database lookups ---
                audio_out_queue = asyncio.Queue()
                is_tool_calling = False

                async def send_audio():
                    nonlocal is_tool_calling
                    while True:
                        # 1. Pause microphone upload if the bot is looking up data
                        if is_tool_calling:
                            await asyncio.sleep(0.1)
                            continue
                            
                        # 2. Read mic and send
                        data = await asyncio.to_thread(mic_stream.read, CHUNK, exception_on_overflow=False)
                        if data:
                            await gemini_session.send_realtime_input(
                                audio=types.Blob(data=data, mime_type="audio/pcm;rate=16000")
                            )
                            
                        # 3. CRITICAL: Give the event loop 1 millisecond to handle WebSocket pings!
                        await asyncio.sleep(0.001)
                
                async def play_audio():
                    while True:
                        # Wait for the network to drop a chunk into the queue
                        data = await audio_out_queue.get()
                        # Play it (this takes time, but won't block the network anymore!)
                        await asyncio.to_thread(speaker_stream.write, data)
                        audio_out_queue.task_done()
                
                
                async def receive_events():
                    nonlocal is_tool_calling

                    async for response in gemini_session.receive():
                        # 1. Handle Audio Output
                        if response.server_content and response.server_content.model_turn:
                            for part in response.server_content.model_turn.parts:
                                if getattr(part, "inline_data", None):
                                    # Play raw audio chunks through the speaker
                                    # This plays the audio in the background, keeping the connection alive
                                    #await asyncio.to_thread(speaker_stream.write, part.inline_data.data)
                                    audio_out_queue.put_nowait(part.inline_data.data)                                        
                        # 2. Handle Tool Calls
                        if response.tool_call:
                            is_tool_calling = True
                            for fn_call in response.tool_call.function_calls:
                                print(f"\n[Gemini requested tool]: {fn_call.name}")
                                
                                # Convert args safely to a standard dictionary for MCP
                                args_dict = dict(fn_call.args) if fn_call.args else {}
                                
                                # Route the call to our MCP server
                                result = await mcp_session.call_tool(fn_call.name, arguments=args_dict)
                                print(f"[Database returned]: {result.content[0].text}")
                                
                                # Send the result back to Gemini using strict SDK types
                                await gemini_session.send_tool_response(
                                    function_responses=[
                                        types.FunctionResponse(
                                            id=fn_call.id,
                                            name=fn_call.name,
                                            response={"result": result.content[0].text}
                                        )
                                    ]
                                )
                                is_tool_calling = False

                # Run mic capture and event receiving concurrently
                #await asyncio.gather(send_audio(), receive_events())
                await asyncio.gather(send_audio(), receive_events(), play_audio())

if __name__ == "__main__":
    asyncio.run(main())