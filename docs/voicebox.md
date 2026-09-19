# Voicebox in Alice

Alice can use profiles from [Voicebox](https://github.com/jamiepine/voicebox)
for speech previews, spoken chat replies, and hands-free replies. Playback stays
in Alice, so microphone turn-taking, volume, stop, and barge-in continue to use
Alice's existing controls. Speech recognition still uses Alice's current engine.

## First use

1. On Windows, run `.venv/Scripts/python.exe scripts/setup-voicebox.py` from the
   Alice source checkout. This downloads the official **v0.5.0** MSI, verifies
   its pinned SHA-256 digest, and administratively extracts it under
   `tools/voicebox-runtime`. It does not merge Python dependencies or globally
   install Voicebox. The installer is about 543 MB; speech models need extra disk
   space and download when first used.
2. Restart Alice and refresh the browser. Rebuild packaged EXEs for the new
   backend and web assets. For an EXE, place the runtime beside it under
   `tools/voicebox-runtime`, or set `ALICE_VOICEBOX_HOME` to the extracted folder.
3. Open **Voice → Voice profile → Voicebox → Start local Voicebox**. First startup
   can take a minute while the packaged backend initializes. If it reports that
   it is still starting, click **Refresh profiles** shortly afterward.
4. Click **Open Voicebox Studio**, create a preset or cloned profile, and prepare
   its model. The studio connects to the running local backend. Return to Alice
   and click **Refresh profiles**.
5. Choose **Voicebox · your profile** in **Base voice**, preview it, and save voice
   settings. Alice preserves the saved profile if Voicebox is temporarily offline
   and reports an error instead of silently substituting another voice.

An already-running Voicebox desktop app on `127.0.0.1:17493` works too. Alice
does not take ownership of or stop an externally started server. On macOS/Linux,
install Voicebox using its own instructions and use the same local API connection.
Custom loopback ports can be set with `ALICE_VOICEBOX_URL`; for those, open your
configured Voicebox app manually. Start/Studio buttons are restricted to the
computer hosting Alice; remote browsers can still request speech through Alice.

## Supported behavior

- Profiles supply their engine and language. Supported engine identifiers are
  Qwen, Qwen CustomVoice, LuxTTS, Chatterbox, Chatterbox Turbo, TADA, and Kokoro.
  Available models and hardware determine whether a particular profile can run.
- The private Windows release backend initially uses CPU. Use Voicebox's own
  installation/GPU controls for CUDA; this setup does not download the multi-GB
  CUDA runtime or every engine's models automatically.
- Effects configured on the Voicebox profile apply. Alice's OpenVoice reference,
  speed, and prosody sliders are disabled for Voicebox voices. Configure delivery
  in Voicebox where supported.
- Alice sends the reply text directly with `personality: false`; Voicebox does
  not rewrite Alice's answer through an additional personality model.
- Voicebox keeps generated text/audio in its local history. Manage that history
  in Voicebox. Alice does not delete profiles, recordings, or prior generations.
- Stop/barge-in ends Alice playback immediately and requests cancellation for
  only the generation created by that speech request. Engine inference may take
  time to notice cancellation. No global stop or model unload is issued.
- Each request has a 180-second deadline and a 30 MB audio limit. Prepare/download
  models in Voicebox before using them in live conversation.

Private runtime data is in `ALICE_HOME/voicebox`; downloaded models are under
`ALICE_VOICEBOX_HOME/models`, and logs are at `ALICE_HOME/logs/voicebox.log`.
Alice shuts down the backend it started when Alice exits. Closing the upstream
studio may also stop that backend, depending on Voicebox's keep-running setting.

## Integration contract

Alice authenticates `/api/voicebox/status`, `/api/voicebox/start`, and
`/api/voicebox/studio` with its normal session controls. Its speech endpoints accept
`VOICEBOX:<profile UUID>` as the speaker. The adapter uses Voicebox `/profiles`,
`/generate`, `/history/{id}`, `/audio/{id}`, and `/generate/{id}/cancel`.
It never follows upstream audio URLs or reads upstream filesystem paths.

Verified against official Voicebox **v0.5.0** and source commit
`51f49dea198384b4eb6087b72c17057c6eb1c1cd`. Voicebox is MIT licensed; its source,
license, and third-party model terms remain upstream. No Voicebox source code is
vendored into Alice's tracked files.
