"""webrtcvad-wheels exposes `webrtcvad`, but its distribution metadata has a
different name. Avoid the upstream hook's invalid metadata lookup."""

from PyInstaller.utils.hooks import collect_dynamic_libs

binaries = collect_dynamic_libs("webrtcvad")
