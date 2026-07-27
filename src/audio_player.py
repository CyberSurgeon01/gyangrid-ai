# src/audio_player.py
"""
Text-to-Speech audio player helper for GyanGrid AI.
Uses gTTS to generate audio in-memory and renders a custom HTML5 player
with a progress bar inside Streamlit.

Only active when language is English ('en').
"""

import io
import base64
import textwrap
import streamlit as st

MAX_TTS_CHARS = 5000


def _truncate_for_tts(text: str, max_chars: int = MAX_TTS_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars].rsplit(" ", 1)[0]
    return truncated + " … (audio truncated to first portion for performance)"


def _text_to_mp3_b64(text: str) -> str | None:
    try:
        from gtts import gTTS
    except ImportError:
        return None
    try:
        buf = io.BytesIO()
        tts = gTTS(text=text, lang="en", slow=False)
        tts.write_to_fp(buf)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")
    except Exception:
        return None


def _build_player_html(b64_audio: str, player_id: str) -> str:
    return textwrap.dedent(f"""
    <style>
      .gyangrid-player-{player_id} {{
        background: #1a1d24;
        border: 1px solid #2d323d;
        border-left: 4px solid #3d8b9e;
        border-radius: 6px;
        padding: 14px 18px;
        margin: 10px 0 4px 0;
        display: flex;
        align-items: center;
        gap: 14px;
        font-family: sans-serif;
      }}
      .gyangrid-player-{player_id} button {{
        background: #3d8b9e;
        border: none;
        border-radius: 50%;
        width: 38px;
        height: 38px;
        cursor: pointer;
        color: #fff;
        font-size: 16px;
        flex-shrink: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: background 0.2s;
      }}
      .gyangrid-player-{player_id} button:hover {{
        background: #4ea8be;
      }}
      .progress-wrap-{player_id} {{
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 4px;
      }}
      .progress-bar-{player_id} {{
        width: 100%;
        height: 5px;
        -webkit-appearance: none;
        appearance: none;
        background: #2d323d;
        border-radius: 3px;
        cursor: pointer;
        outline: none;
      }}
      .progress-bar-{player_id}::-webkit-slider-thumb {{
        -webkit-appearance: none;
        width: 13px;
        height: 13px;
        border-radius: 50%;
        background: #3d8b9e;
        cursor: pointer;
      }}
      .time-label-{player_id} {{
        color: #8a9ab0;
        font-size: 12px;
        letter-spacing: 0.3px;
      }}
    </style>

    <div class="gyangrid-player-{player_id}">
      <button id="playBtn-{player_id}" onclick="togglePlay_{player_id}()">▶</button>
      <div class="progress-wrap-{player_id}">
        <input
          type="range"
          class="progress-bar-{player_id}"
          id="bar-{player_id}"
          value="0" min="0" step="0.1"
          oninput="seek_{player_id}(this.value)"
        />
        <span class="time-label-{player_id}" id="timeLabel-{player_id}">0:00 / 0:00</span>
      </div>
    </div>

    <audio id="audio-{player_id}"
      src="data:audio/mp3;base64,{b64_audio}"
      preload="auto"
    ></audio>

    <script>
    (function() {{
      const audio  = document.getElementById('audio-{player_id}');
      const btn    = document.getElementById('playBtn-{player_id}');
      const bar    = document.getElementById('bar-{player_id}');
      const label  = document.getElementById('timeLabel-{player_id}');

      function fmt(s) {{
        const m = Math.floor(s / 60);
        return m + ':' + String(Math.floor(s % 60)).padStart(2, '0');
      }}

      audio.addEventListener('loadedmetadata', () => {{
        bar.max = audio.duration;
        label.textContent = '0:00 / ' + fmt(audio.duration);
      }});

      audio.addEventListener('timeupdate', () => {{
        bar.value = audio.currentTime;
        label.textContent = fmt(audio.currentTime) + ' / ' + fmt(audio.duration);
      }});

      audio.addEventListener('ended', () => {{
        btn.textContent = '▶';
        bar.value = 0;
      }});

      window['togglePlay_{player_id}'] = function() {{
        if (audio.paused) {{ audio.play(); btn.textContent = '⏸'; }}
        else             {{ audio.pause(); btn.textContent = '▶'; }}
      }};

      window['seek_{player_id}'] = function(val) {{
        audio.currentTime = parseFloat(val);
      }};
    }})();
    </script>
    """)


def render_audio_player(
    text: str,
    lang_code: str,
    label: str = "🔊 Listen",
    player_id: str = "default",
    session_key: str = "audio_b64_default",
):
    if lang_code != "en":
        return

    with st.expander(label, expanded=False):
        if session_key not in st.session_state:
            with st.spinner("Generating audio…"):
                safe_text = _truncate_for_tts(text)
                b64 = _text_to_mp3_b64(safe_text)
            if b64 is None:
                st.warning(
                    "Audio generation failed. Make sure `gTTS` is installed: "
                    "`pip install gTTS`"
                )
                return
            st.session_state[session_key] = b64

        b64_audio = st.session_state[session_key]
        html = _build_player_html(b64_audio, player_id)
        st.components.v1.html(html, height=90, scrolling=False)
