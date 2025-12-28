/**
 * Frontend Event Stream Logger
 *
 * Logs all combat events received from the backend SSE stream and provides
 * tools for debugging desyncs.
 */

import { CombatEvent } from './types'

interface EventLogEntry {
  index: number
  seq: number
  timestamp: number
  type: string
  event: CombatEvent
  receivedAt: number
}

class EventStreamLogger {
  private events: EventLogEntry[] = []
  private enabled: boolean = false
  private sessionStart: number = 0

  enable() {
    this.enabled = true
    this.sessionStart = Date.now()
    this.events = []
    console.log('[EventLogger] Logging enabled')
  }

  disable() {
    this.enabled = false
    console.log('[EventLogger] Logging disabled')
  }

  logEvent(event: CombatEvent) {
    if (!this.enabled) return

    const entry: EventLogEntry = {
      index: this.events.length,
      seq: event.seq ?? -1,
      timestamp: event.timestamp ?? 0,
      type: event.type,
      event: event,
      receivedAt: Date.now() - this.sessionStart
    }

    this.events.push(entry)

    // Log effect-related events immediately for visibility
    if (['unit_stunned', 'stat_buff', 'shield_applied', 'damage_over_time_applied', 'effect_expired'].includes(event.type)) {
      console.log(`[EventLogger] Effect event #${entry.index}: seq=${entry.seq} type=${event.type} unit=${(event as any).unit_id}`, event)
    }
  }

  getEvents(): EventLogEntry[] {
    return [...this.events]
  }

  getEventsByType(type: string): EventLogEntry[] {
    return this.events.filter(e => e.type === type)
  }

  getEventsForUnit(unitId: string): EventLogEntry[] {
    return this.events.filter(e => {
      const evt = e.event as any
      return evt.unit_id === unitId || evt.target_id === unitId || evt.caster_id === unitId
    })
  }

  exportToJSON(): string {
    return JSON.stringify(this.events.map(e => e.event), null, 2)
  }

  downloadLog(filename: string = 'combat_events.json') {
    const json = this.exportToJSON()
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    console.log(`[EventLogger] Downloaded ${this.events.length} events to ${filename}`)
  }

  printSummary() {
    console.log('\n' + '='.repeat(80))
    console.log('EVENT STREAM SUMMARY')
    console.log('='.repeat(80))
    console.log(`Total events: ${this.events.length}`)

    // Count by type
    const typeCounts = new Map<string, number>()
    this.events.forEach(e => {
      typeCounts.set(e.type, (typeCounts.get(e.type) || 0) + 1)
    })

    console.log('\nEvents by type:')
    Array.from(typeCounts.entries())
      .sort((a, b) => b[1] - a[1])
      .forEach(([type, count]) => {
        console.log(`  ${type}: ${count}`)
      })

    // Effect events
    const effectTypes = ['unit_stunned', 'stat_buff', 'shield_applied', 'damage_over_time_applied', 'effect_expired']
    console.log('\nEffect events:')
    effectTypes.forEach(type => {
      const count = typeCounts.get(type) || 0
      console.log(`  ${type}: ${count}`)
    })

    // Check for gaps in sequence numbers
    const seqs = this.events.map(e => e.seq).filter(s => s >= 0).sort((a, b) => a - b)
    const gaps: number[] = []
    for (let i = 1; i < seqs.length; i++) {
      if (seqs[i] - seqs[i-1] > 1) {
        for (let missing = seqs[i-1] + 1; missing < seqs[i]; missing++) {
          gaps.push(missing)
        }
      }
    }

    if (gaps.length > 0) {
      console.log(`\n⚠️  Missing sequence numbers: ${gaps.join(', ')}`)
    } else {
      console.log('\n✅ No gaps in sequence numbers')
    }

    console.log('='.repeat(80) + '\n')
  }

  /**
   * Analyze desync by comparing events received vs server snapshots
   */
  analyzeDesyncForUnit(unitId: string, serverSnapshot: any) {
    console.log(`\n${'='.repeat(80)}`)
    console.log(`DESYNC ANALYSIS FOR UNIT: ${unitId}`)
    console.log('='.repeat(80))

    const unitEvents = this.getEventsForUnit(unitId)
    console.log(`\nTotal events affecting this unit: ${unitEvents.length}`)

    // Group by type
    const byType = new Map<string, EventLogEntry[]>()
    unitEvents.forEach(e => {
      const events = byType.get(e.type) || []
      events.push(e)
      byType.set(e.type, events)
    })

    console.log('\nEvents by type:')
    byType.forEach((events, type) => {
      console.log(`  ${type}: ${events.length}`)
    })

    // Check for effect application events
    const effectEvents = unitEvents.filter(e =>
      ['unit_stunned', 'stat_buff', 'shield_applied', 'damage_over_time_applied'].includes(e.type)
    )
    console.log(`\nEffect application events: ${effectEvents.length}`)
    effectEvents.forEach(e => {
      const evt = e.event as any
      console.log(`  seq=${e.seq} type=${e.type} effect_id=${evt.effect_id}`)
    })

    // Compare with server snapshot
    if (serverSnapshot) {
      const serverEffects = serverSnapshot.effects || []
      console.log(`\nServer snapshot effects: ${serverEffects.length}`)
      serverEffects.forEach((eff: any) => {
        console.log(`  type=${eff.type} id=${eff.id} stat=${eff.stat} value=${eff.value}`)

        // Try to find corresponding event
        const found = effectEvents.find(e => {
          const evt = e.event as any
          return evt.effect_id === eff.id
        })

        if (!found) {
          console.log(`    ⚠️  NO MATCHING EVENT FOUND for effect_id=${eff.id}`)
        } else {
          console.log(`    ✅ Found matching event at seq=${found.seq}`)
        }
      })
    }

    console.log('='.repeat(80) + '\n')
  }

  clear() {
    this.events = []
    console.log('[EventLogger] Log cleared')
  }
}

// Global singleton instance
export const eventLogger = new EventStreamLogger()

// Make available in browser console for debugging
if (typeof window !== 'undefined') {
  (window as any).eventLogger = eventLogger
}

/**
 * Hook to enable event logging in development
 */
export function useEventLogger(enabled: boolean = false) {
  if (enabled && !eventLogger['enabled']) {
    eventLogger.enable()
  }

  return eventLogger
}
