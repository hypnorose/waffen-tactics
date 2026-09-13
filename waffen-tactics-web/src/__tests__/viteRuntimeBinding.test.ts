// @vitest-environment node

import { readFileSync } from 'node:fs'
import viteConfig from '../../vite.config'

describe('production Vite runtime binding', () => {
  it('binds the loaded server config to loopback', () => {
    expect(viteConfig.server?.host).toBe('127.0.0.1')
    expect(viteConfig.server?.port).toBe(3000)
  })

  it('keeps the production artifact path and development notes on loopback', () => {
    const startAll = readFileSync(new URL('../../../start-all.sh', import.meta.url), 'utf8')
    const developmentNotes = readFileSync(new URL('../../DEVELOPMENT_NOTES.md', import.meta.url), 'utf8')
    const caddyfile = readFileSync(new URL('../../Caddyfile', import.meta.url), 'utf8')

    expect(startAll).toContain('npm run build > frontend-build.log 2>&1')
    expect(startAll).not.toContain('npm run preview')
    expect(startAll).not.toContain('--host 0.0.0.0')
    expect(caddyfile).toContain('root * /home/ubuntu/waffen-tactics-game/waffen-tactics-web/dist')
    expect(caddyfile).toContain('try_files {path} /index.html')
    expect(caddyfile).toContain('file_server')
    expect(caddyfile).not.toContain('reverse_proxy localhost:3000')
    expect(developmentNotes).toContain('npm run dev -- --host 127.0.0.1')
    expect(developmentNotes).not.toContain('--host 0.0.0.0')
  })
})
