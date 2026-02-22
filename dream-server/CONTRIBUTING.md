# Contributing to Dream Server

Thanks for wanting to help! Here's how to get involved.

## Reporting Issues

Found a bug? Please open an issue with:
- Your hardware (GPU, RAM, OS)
- What you expected to happen
- What actually happened
- Logs if relevant (`docker compose logs`)

## Pull Requests

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/cool-thing`)
3. Make your changes
4. Test on your hardware
5. Submit PR with clear description

## What We're Looking For

**High Value:**
- New workflow templates (n8n JSON exports)
- Hardware-specific optimizations
- Better error messages
- Documentation improvements

**Good First Issues:**
- Fix typos in docs
- Add more troubleshooting cases
- Improve comments in install.sh

**Harder But Appreciated:**
- Multi-GPU support improvements
- New model presets
- Alternative TTS/STT engines

## Testing Your Changes

```bash
# Fresh install test
rm -rf ~/dream-server
./install.sh --dry-run  # Check what would happen
./install.sh            # Actually install

# Run the status check
./status.sh
```

## Code Style

- Bash: Use ShellCheck. We're not religious about style, just be consistent.
- YAML: 2-space indent, no tabs.
- Markdown: Keep it readable. No 80-char wrapping.

## Questions?

Open an issue or find us in Discord.

---

*Your contributions help bring local AI to everyone.*
