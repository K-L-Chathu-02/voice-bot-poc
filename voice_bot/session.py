import asyncio
import logging

from google import genai
from google.genai import types

from .audio import AudioIO, INPUT_SAMPLE_RATE
from .config import LIVE_MODEL, LanguageProfile
from .mcp_bridge import McpBridge
from .prompts import build_system_instruction

log = logging.getLogger(__name__)

AUDIO_QUEUE_MAXSIZE = 20


async def run_session(profile: LanguageProfile, api_key: str, mcp_url: str) -> None:
    async with McpBridge(mcp_url) as bridge:
        declarations = await bridge.list_function_declarations()
        log.info("Loaded %d tools from MCP server", len(declarations))

        client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})

        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                language_code=profile.language_code,
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=profile.voice_name
                    )
                ),
            ),
            system_instruction=types.Content(
                parts=[types.Part(text=build_system_instruction(profile))]
            ),
            tools=[types.Tool(function_declarations=declarations)],
        )

        audio = AudioIO()
        audio_out_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=AUDIO_QUEUE_MAXSIZE)

        try:
            async with client.aio.live.connect(model=LIVE_MODEL, config=config) as session:
                await session.send_client_content(
                    turns=[
                        types.Content(
                            role="user",
                            parts=[types.Part(text="(call connected — greet the caller now)")],
                        )
                    ],
                    turn_complete=True,
                )

                async with asyncio.TaskGroup() as tg:
                    tg.create_task(_send_mic(session, audio))
                    tg.create_task(_receive_server(session, audio_out_queue, bridge))
                    tg.create_task(_play_speaker(audio, audio_out_queue))
        finally:
            audio.close()


async def _send_mic(session, audio: AudioIO) -> None:
    mime = f"audio/pcm;rate={INPUT_SAMPLE_RATE}"
    while True:
        chunk = await asyncio.to_thread(audio.read_chunk)
        if not chunk:
            continue
        await session.send_realtime_input(audio=types.Blob(data=chunk, mime_type=mime))


async def _receive_server(
    session,
    audio_out_queue: asyncio.Queue[bytes],
    bridge: McpBridge,
) -> None:
    while True:
        async for response in session.receive():
            sc = getattr(response, "server_content", None)
            if sc is not None:
                if getattr(sc, "interrupted", False):
                    drained = _drain(audio_out_queue)
                    if drained:
                        log.info("Barge-in: dropped %d queued audio chunks", drained)
                model_turn = getattr(sc, "model_turn", None)
                if model_turn is not None:
                    for part in getattr(model_turn, "parts", None) or []:
                        inline = getattr(part, "inline_data", None)
                        if inline is not None and inline.data:
                            await audio_out_queue.put(inline.data)
                        text = getattr(part, "text", None)
                        if text:
                            log.debug("model text: %s", text)

            tool_call = getattr(response, "tool_call", None)
            if tool_call is not None and tool_call.function_calls:
                responses = []
                for fc in tool_call.function_calls:
                    args = dict(fc.args or {})
                    log.info("tool_call: %s(%s)", fc.name, args)
                    result = await bridge.call(fc.name, args)
                    log.info("tool_result: %s -> %s", fc.name, result)
                    responses.append(
                        types.FunctionResponse(
                            id=fc.id,
                            name=fc.name,
                            response=result,
                        )
                    )
                await session.send_tool_response(function_responses=responses)


async def _play_speaker(audio: AudioIO, audio_out_queue: asyncio.Queue[bytes]) -> None:
    while True:
        data = await audio_out_queue.get()
        await asyncio.to_thread(audio.write, data)


def _drain(q: asyncio.Queue) -> int:
    n = 0
    while not q.empty():
        try:
            q.get_nowait()
            n += 1
        except asyncio.QueueEmpty:
            break
    return n
