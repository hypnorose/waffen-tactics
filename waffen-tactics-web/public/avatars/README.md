# Unit Avatars

This directory contains avatar images for all units in the game.

## Image Requirements

- **Format**: PNG (recommended) or JPG
- **Size**: 64x64 pixels (or larger, will be scaled down)
- **Shape**: Square (will be displayed in a circle)
- **Naming**: Must match the unit's `id` field from `units.json`

## Example Files

Place images with filenames matching unit IDs:
- `rafcikd.png`
- `falconbalkon.png`
- `piwniczak.png`
- `capybara.png`
- etc.

## Fallback Behavior

If an avatar image is missing or fails to load, the UI will display a placeholder emoji (👤).

## Adding New Avatars

1. Create/obtain a square image (preferably 64x64px or larger)
2. Save it as `{unit_id}.png` in this directory
3. The image will automatically appear in:
   - Shop cards
   - Bench cards
   - Board units
   - Combat view

No code changes needed - just drop the image files here!
