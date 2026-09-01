# Checklist

🟢 erledigt · 🟡 offen · 🔴 kritisch/broken/wichtig

- 🟢 SSH-Zugriff zum Pi (Alias `rasp-local` / `rasp-lan`)
- 🟢 Altes Projekt vom Pi gelöscht (drop_project, drop_project_01, Bilder, Videos)
- 🟢 Debug_frames & measure_logs (root-owned) gelöscht
- 🟢 Stereo-Kamera erkannt (arducam-pivariety, Slots MIPIRX2/3, 2560x800)
- 🟢 Stereo-Testbild aufgenommen & verifiziert (beide Kameras liefern synchrones Bild)
- 🟢 IPA-Tuning-Datei-Fix: Symlink `arducam-pivariety_mono.json` → `ov9281_mono.json` in `/usr/share/libcamera/ipa/rpi/vc4/` angelegt (verifiziert via `rpicam-still`)
- 🟢 Echtes git clone auf Pi (ersetzt Dateikopie)
- 🟢 GitHub-SSH-Zugriff vom Pi (Deploy-Key mit Schreibrechten)
- 🟢 Node.js 22 (NodeSource) auf Pi installiert
- 🟢 Claude Code auf Pi installiert (`~/.npm-global`, kein sudo nötig)
- 🟢 VS Code Remote-SSH Setup (Extension installiert, Server läuft auf Pi)
- 🟢 VS Code App auf Mac aktualisiert (1.73.0 → 1.135.0, via Homebrew Cask, alte Downloads-Kopie entfernt)
