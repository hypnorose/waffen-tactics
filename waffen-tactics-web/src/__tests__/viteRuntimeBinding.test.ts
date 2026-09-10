// @vitest-environment node

import { readFileSync } from 'node:fs'
import viteConfig from '../../vite.config'

describe('production Vite runtime binding', () => {
  it('binds the loaded server config to loopback', () => {
    expect(viteConfig.server?.host).toBe('127.0.0.1')
    expect(viteConfig.server?.port).toBe(3000)
  })

  it('keeps the canonical startup and development notes on loopback', () => {
    const startAll = readFileSync(new URL('../../../start-all.sh', import.meta.url), 'utf8')
    const developmentNotes = readFileSync(new URL('../../DEVELOPMENT_NOTES.md', import.meta.url), 'utf8')

    expect(startAll).toContain('nohup npm run dev -- --host 127.0.0.1 > vite.log 2>&1 &')
    expect(startAll).not.toContain('--host 0.0.0.0')
    expect(developmentNotes).toContain('npm run dev -- --host 127.0.0.1')
    expect(developmentNotes).not.toContain('--host 0.0.0.0')
  })
})
