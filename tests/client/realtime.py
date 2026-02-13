from __future__ import annotations

import json
import time
import asyncio
import contextlib
from dataclasses import dataclass

import websockets

from tests.params import config
from tests.utils.audio.streamer import AudioStreamer
from tests.params.env import build_ws_url, resolve_api_key


@dataclass(slots=True)
class StreamResult:
    text: str
    metrics: dict[str, float]
    error: str | None = None


@dataclass(slots=True)
class _RecvState:
    final_text: str = ""
    partials: int = 0
    ttfw_s: float | None = None
    handshake_ts: float | None = None
    final_recv_ts: float | None = None
    error: str | None = None


def _build_metrics(
    *,
    audio_s: float,
    partials: int,
    ttfw_s: float | None,
    session_start_ts: float,
    final_recv_ts: float | None,
    final_commit_sent_ts: float | None,
    send_finish_ts: float | None,
    send_info: dict,
    session_elapsed_s: float,
) -> dict[str, float]:
    wall_to_final_s = (final_recv_ts - session_start_ts) if final_recv_ts else session_elapsed_s

    tail_ms = 0.0
    if final_commit_sent_ts and final_recv_ts:
        tail_ms = max(0.0, (final_recv_ts - final_commit_sent_ts) * config.MS_PER_S)

    post_send_final_s = 0.0
    if send_finish_ts and final_recv_ts:
        post_send_final_s = max(0.0, final_recv_ts - send_finish_ts)

    rtf_full = (wall_to_final_s / audio_s) if audio_s > 0 else 0.0
    xrt = (audio_s / wall_to_final_s) if wall_to_final_s > 0 else 0.0

    return {
        "wall_s": wall_to_final_s,
        "wall_to_final_s": wall_to_final_s,
        "audio_s": audio_s,
        "rtf_full": rtf_full,
        "rtf": rtf_full,
        "xrt": xrt,
        "throughput_min_per_min": xrt,
        "partials": float(partials),
        "ttfw_s": float(ttfw_s or 0.0),
        "ttfw_text_s": float(ttfw_s or 0.0),
        "finalize_ms": tail_ms,
        "flush_to_final_ms": tail_ms,
        "post_send_final_s": post_send_final_s,
        "send_duration_s": float(send_info.get("send_duration_s") or 0.0),
        "delta_to_audio_ms": 0.0,
        "decode_tail_ms": tail_ms,
    }


class RealtimeClient:
    def __init__(
        self,
        server: str,
        secure: bool = False,
        *,
        debug: bool = False,
    ) -> None:
        self.server = server
        self.secure = secure
        self.debug = debug

        # Timing fields for printing helpers.
        self.session_start_ts: float = 0.0
        self.connect_elapsed_s: float = 0.0
        self.handshake_elapsed_s: float = 0.0
        self.first_audio_sent_ts: float = 0.0
        self.close_elapsed_s: float = 0.0
        self.finish_elapsed_s: float = 0.0
        self.session_elapsed_s: float = 0.0

    async def _recv_loop(self, ws, recv: _RecvState, done_event: asyncio.Event) -> None:
        try:
            while True:
                raw = await ws.recv()
                now = time.perf_counter()
                try:
                    msg = json.loads(raw)
                except (TypeError, json.JSONDecodeError):
                    continue
                if self.debug:
                    print(f"[recv] {msg}")

                msg_type = msg.get("type")
                payload = msg.get("payload") or {}

                if recv.handshake_ts is None and msg_type in {"session.created", "session.updated"}:
                    recv.handshake_ts = now
                    self.handshake_elapsed_s = recv.handshake_ts - self.session_start_ts

                if msg_type == "transcription.delta":
                    delta = payload.get("delta") or ""
                    if isinstance(delta, str) and delta:
                        if not self.first_audio_sent_ts:
                            # best-effort: if first audio time wasn't captured, approximate with handshake.
                            self.first_audio_sent_ts = recv.handshake_ts or self.session_start_ts
                        if recv.ttfw_s is None:
                            recv.ttfw_s = now - self.first_audio_sent_ts
                        recv.final_text += delta
                        recv.partials += 1

                if msg_type == "transcription.done":
                    txt = payload.get("text")
                    if isinstance(txt, str) and txt:
                        recv.final_text = txt
                    if recv.ttfw_s is None and self.first_audio_sent_ts:
                        recv.ttfw_s = now - self.first_audio_sent_ts
                    recv.final_recv_ts = now
                    done_event.set()
                    return

                if msg_type == "error":
                    err = payload.get("error") or payload
                    recv.error = json.dumps(err) if not isinstance(err, str) else err
                    done_event.set()
                    return
        except websockets.exceptions.ConnectionClosed as exc:
            # If the caller already recorded a higher-level error (e.g. timeout),
            # don't overwrite it with a generic close message.
            if recv.error is None:
                recv.error = f"connection closed code={exc.code} reason={exc.reason}"
            done_event.set()

    async def run_stream(
        self,
        pcm_bytes: bytes,
        *,
        session_id: str,
        request_id: str,
        rtf: float,
        timeout_s: float = config.DEFAULT_TIMEOUT_S,
    ) -> StreamResult:
        api_key = resolve_api_key()
        if not api_key:
            return StreamResult("", {}, error="VOXTRAL_API_KEY is required for test clients")

        ws_url = build_ws_url(self.server, secure=self.secure, api_key=api_key)

        audio_s = (len(pcm_bytes) / 2) / config.ASR_SAMPLE_RATE if pcm_bytes else 0.0

        self.session_start_ts = time.perf_counter()
        final_commit_sent_ts: float | None = None
        send_finish_ts: float | None = None

        done_event = asyncio.Event()
        recv = _RecvState()

        async with websockets.connect(
            ws_url,
            ping_interval=config.WS_PING_INTERVAL_S,
            ping_timeout=config.WS_PING_TIMEOUT_S,
            max_size=32 * 1024 * 1024,
        ) as ws:
            self.connect_elapsed_s = time.perf_counter() - self.session_start_ts

            recv_task = asyncio.create_task(self._recv_loop(ws, recv, done_event))

            # Start utterance
            await ws.send(
                json.dumps({
                    "type": "input_audio_buffer.commit",
                    "session_id": session_id,
                    "request_id": request_id,
                    "payload": {"final": False},
                })
            )

            streamer = AudioStreamer(rtf=rtf)

            def _on_first_audio(ts: float) -> None:
                self.first_audio_sent_ts = ts

            send_info = await streamer.stream(
                ws,
                session_id=session_id,
                request_id=request_id,
                pcm_bytes=pcm_bytes,
                on_first_audio=_on_first_audio,
            )
            send_finish_ts = send_info.get("send_finish_ts") or time.perf_counter()

            # Finalize utterance
            final_commit_sent_ts = time.perf_counter()
            await ws.send(
                json.dumps({
                    "type": "input_audio_buffer.commit",
                    "session_id": session_id,
                    "request_id": request_id,
                    "payload": {"final": True},
                })
            )

            async def _app_ping_loop() -> None:
                try:
                    while not done_event.is_set():
                        await asyncio.sleep(config.WS_APP_PING_INTERVAL_S)
                        if done_event.is_set():
                            return
                        await ws.send(
                            json.dumps({
                                "type": "ping",
                                "session_id": session_id,
                                "request_id": request_id,
                                "payload": {},
                            })
                        )
                except Exception:
                    return

            ping_task = asyncio.create_task(_app_ping_loop())

            try:
                await asyncio.wait_for(done_event.wait(), timeout=timeout_s)
            except TimeoutError:
                recv.error = f"timeout waiting for transcription.done (>{timeout_s:.1f}s)"
            finally:
                ping_task.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await ping_task

            # Graceful close
            close_start = time.perf_counter()
            with contextlib.suppress(Exception):
                await ws.close(code=1000)
            self.close_elapsed_s = time.perf_counter() - close_start

            recv_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await recv_task

        finish_ts = time.perf_counter()
        self.session_elapsed_s = finish_ts - self.session_start_ts
        self.finish_elapsed_s = (finish_ts - recv.final_recv_ts) if recv.final_recv_ts else 0.0

        metrics = _build_metrics(
            audio_s=audio_s,
            partials=recv.partials,
            ttfw_s=recv.ttfw_s,
            session_start_ts=self.session_start_ts,
            final_recv_ts=recv.final_recv_ts,
            final_commit_sent_ts=final_commit_sent_ts,
            send_finish_ts=send_finish_ts,
            send_info=send_info,
            session_elapsed_s=self.session_elapsed_s,
        )

        return StreamResult(text=recv.final_text, metrics=metrics, error=recv.error)


__all__ = ["RealtimeClient", "StreamResult"]
