#!/usr/bin/env python3
"""
Dream Server Voice Agent - Offline Mode
Main agent implementation for local-only voice chat
M1 Phase 2 - Zero cloud dependencies

Uses LiveKit Agents SDK v1.4+ with local model backends:
- LLM: vLLM (OpenAI-compatible)
- STT: Whisper (OpenAI-compatible API)
- TTS: Kokoro (OpenAI-compatible API)
- VAD: Silero (built-in)
"""

import os
import asyncio
import logging
import signal
from typing import Optional

from livekit.agents import (
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
)
from livekit.agents import Agent, AgentSession
from livekit.plugins import silero, openai as openai_plugin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger("dream-voice-offline")

# Environment config
LIVEKIT_URL = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
LLM_URL = os.getenv("LLM_URL", "http://vllm:8000/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "Qwen/Qwen2.5-32B-Instruct-AWQ")
STT_URL = os.getenv("STT_URL", "http://whisper:9000/v1")
TTS_URL = os.getenv("TTS_URL", "http://tts:8880/v1")
TTS_VOICE = os.getenv("TTS_VOICE", "af_heart")

# Offline mode settings
OFFLINE_MODE = os.getenv("OFFLINE_MODE", "true").lower() == "true"

# System prompt for offline mode
OFFLINE_SYSTEM_PROMPT = """You are Dream Agent running in offline mode on local hardware.
You have access to local tools and services only. Be helpful, accurate, and maintain privacy.
Keep responses conversational and concise - this is voice, not text.

Key capabilities:
- Answer questions using local knowledge
- Help with file operations and system tasks
- Provide technical assistance for local services
- Maintain conversation context

Limitations:
- Cannot access external websites or APIs
- Cannot provide real-time information
- Cannot perform web searches
- All processing happens locally on this machine

Always acknowledge when asked about external information that you operate in offline mode."""


async def check_service_health(url: str, name: str, timeout: int = 5) -> bool:
    """Check if a service is healthy before starting."""
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                healthy = resp.status == 200
                if healthy:
                    logger.info(f"  {name} is healthy")
                else:
                    logger.warning(f"  {name} returned status {resp.status}")
                return healthy
    except Exception as e:
        logger.warning(f"  {name} unreachable: {e}")
        return False


class OfflineVoiceAgent(Agent):
    """
    Voice agent for offline/local-only operation.

    Features:
    - Greets user on entry
    - Handles interruptions (user can stop bot speech)
    - Uses only local services (no cloud dependencies)
    - Falls back gracefully if services fail
    """

    def __init__(self) -> None:
        super().__init__(
            instructions=OFFLINE_SYSTEM_PROMPT,
            allow_interruptions=True,
        )
        self.error_count = 0
        self.max_errors = 3

    async def on_enter(self):
        """Called when agent becomes active. Send greeting."""
        logger.info("Agent entered - sending greeting")
        try:
            self.session.generate_reply(
                instructions="Greet the user warmly and briefly introduce yourself as their local offline voice assistant."
            )
        except Exception as e:
            logger.error(f"Failed to send greeting: {e}")
            self.error_count += 1

    async def on_exit(self):
        """Called when agent is shutting down."""
        logger.info("Agent exiting - cleanup")

    async def on_error(self, error: Exception):
        """Handle errors gracefully."""
        self.error_count += 1
        logger.error(f"Agent error ({self.error_count}/{self.max_errors}): {error}")

        if self.error_count >= self.max_errors:
            logger.critical("Max errors reached, agent will restart")
            raise error


async def create_llm() -> Optional[openai_plugin.LLM]:
    """Create local LLM instance."""
    try:
        llm = openai_plugin.LLM(
            model=LLM_MODEL,
            base_url=LLM_URL,
            api_key="not-needed",  # Local vLLM doesn't require API key
        )
        logger.info(f"  LLM configured: {LLM_MODEL}")
        return llm
    except Exception as e:
        logger.error(f"  Failed to create LLM: {e}")
        return None


async def create_stt() -> Optional[openai_plugin.STT]:
    """Create local STT instance."""
    try:
        stt_base_url = STT_URL.removesuffix('/v1').removesuffix('/')
        healthy = await check_service_health(f"{stt_base_url}/health", "STT (Whisper)")
        if not healthy:
            logger.warning("STT service not healthy, continuing without speech recognition")
            return None

        stt = openai_plugin.STT(
            model="whisper-1",
            base_url=STT_URL,
            api_key="not-needed",
        )
        logger.info("  STT configured")
        return stt
    except Exception as e:
        logger.error(f"  Failed to create STT: {e}")
        logger.warning("Continuing without speech recognition")
        return None


async def create_tts() -> Optional[openai_plugin.TTS]:
    """Create local TTS instance."""
    try:
        tts_base_url = TTS_URL.removesuffix('/v1').removesuffix('/')
        healthy = await check_service_health(f"{tts_base_url}/health", "TTS (Kokoro)")
        if not healthy:
            logger.warning("TTS service not healthy, continuing without speech synthesis")
            return None

        tts = openai_plugin.TTS(
            model="kokoro",
            voice=TTS_VOICE,
            base_url=TTS_URL,
            api_key="not-needed",
        )
        logger.info(f"  TTS configured with voice: {TTS_VOICE}")
        return tts
    except Exception as e:
        logger.error(f"  Failed to create TTS: {e}")
        logger.warning("Continuing without speech synthesis")
        return None


async def entrypoint(ctx: JobContext):
    """
    Main entry point for the offline voice agent job.

    Includes:
    - Service health checks
    - Graceful degradation if services fail
    - Reconnection logic
    """
    logger.info(f"Voice agent connecting to room: {ctx.room.name}")

    # Health check phase
    logger.info("Performing service health checks...")
    llm_healthy = await check_service_health(f"{LLM_URL}/models", "LLM (vLLM)")

    if not llm_healthy:
        logger.error("LLM service not healthy - cannot start agent")
        raise RuntimeError("LLM service required but not available")

    # Create components with error handling
    llm = await create_llm()
    if not llm:
        raise RuntimeError("Failed to create LLM - agent cannot start")

    stt = await create_stt()
    tts = await create_tts()

    # Create VAD from prewarmed cache or load fresh
    try:
        vad = ctx.proc.userdata.get("vad") or silero.VAD.load()
        logger.info("  VAD loaded")
    except Exception as e:
        logger.error(f"  Failed to load VAD: {e}")
        logger.warning("Starting without voice activity detection")
        vad = None

    # Create session - only include working components
    session_kwargs = {"llm": llm}
    if stt:
        session_kwargs["stt"] = stt
    if tts:
        session_kwargs["tts"] = tts
    if vad:
        session_kwargs["vad"] = vad

    session = AgentSession(**session_kwargs)

    # Create agent
    agent = OfflineVoiceAgent()

    # Setup graceful shutdown
    shutdown_event = asyncio.Event()

    def signal_handler(sig, frame):
        logger.info("Shutdown signal received")
        shutdown_event.set()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Connect to room first (required by LiveKit SDK)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            await ctx.connect()
            logger.info("Connected to room")
            break
        except Exception as e:
            logger.error(f"Room connection failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(1)

    # Start session after room connection
    for attempt in range(max_retries):
        try:
            await session.start(agent=agent, room=ctx.room)
            logger.info("Offline voice agent session started")
            break
        except Exception as e:
            logger.error(f"Session start failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(1)

    # Wait for shutdown signal
    try:
        await shutdown_event.wait()
    except asyncio.CancelledError:
        logger.info("Agent task cancelled")
    finally:
        logger.info("Shutting down offline voice agent...")
        try:
            await session.close()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


def prewarm(proc: JobProcess):
    """Prewarm function - load models before first job."""
    logger.info("Prewarming offline voice agent...")
    try:
        proc.userdata["vad"] = silero.VAD.load()
        logger.info("  VAD model loaded")
    except Exception as e:
        logger.error(f"  Failed to load VAD: {e}")
        proc.userdata["vad"] = None


if __name__ == "__main__":
    agent_port = int(os.getenv("AGENT_PORT", "8181"))

    # Log startup info
    logger.info("=" * 60)
    logger.info("Dream Server Voice Agent - OFFLINE MODE")
    logger.info(f"Port: {agent_port}")
    logger.info(f"LLM: {LLM_URL}")
    logger.info(f"STT: {STT_URL}")
    logger.info(f"TTS: {TTS_URL}")
    logger.info(f"Offline Mode: {OFFLINE_MODE}")
    logger.info("=" * 60)

    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            port=agent_port,
        )
    )
