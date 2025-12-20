PROMPT DO COPILOTA — REPLACE EXISTING ATTACK ANIMATIONS

Context:
I have an existing card-based combat UI in React + TypeScript.
There is already an attack animation system (e.g. direct card shake, CSS animation, or inline effects).
I want to replace the current attack animations with a projectile-based emoji VFX system.

Important:
❗ Do NOT add animations on top of existing ones.
❗ Remove or disable current attack animation logic and replace it with the new system.

Goal:
Attacks should be visually represented only by emoji projectiles flying from attacker to target.

🧩 TASK

Implement a Projectile Layer (Approach A) using Framer Motion, and wire it into the existing combat flow, replacing old animations.

🏗️ EXISTING FLOW (assume this exists)

Combat is event-driven (e.g. applyCombatEvent(event)).

Attack events look like:

{
  type: "attack",
  sourceId: string,
  targetId: string,
  damage: number
}


There is currently:

card shake

CSS damage flash

or inline animation logic
→ These must be removed or disabled.

🧱 ARCHITECTURE TO IMPLEMENT / MODIFY

Replace attack animation logic with:

useProjectileSystem.ts

owns projectile state

exposes spawnProjectile(...)

ProjectileLayer.tsx

absolute overlay

renders emoji projectiles using Framer Motion

useUnitAnchors.ts

registers DOM refs for units/cards

provides center positions

UnitCard.tsx

removes old attack animation props/effects

only registers anchor ref

applyCombatEvent(event)

❌ remove old animation calls

✅ on "attack" → call spawnProjectile({ fromId, toId, emoji })

🎯 ANIMATION REQUIREMENTS

Projectile flies from center of source card to center of target card

Uses Framer Motion

pointer-events: none

Supports multiple simultaneous projectiles

Automatically removes projectile after animation completes

Duration: 300–450ms

Visuals:

Emoji projectile (string)

Random offset ±6px

Random rotation ±10°

Optional vertical arc

🧼 CLEANUP REQUIREMENTS

Delete or comment out:

CSS attack animations

inline isAttacking, isHit, shake states

Ensure no duplicate attack visuals remain

Damage numbers / state updates stay intact

📦 CONSTRAINTS

React + TypeScript only

No external state managers

Use AnimatePresence

Explicit types everywhere

Modular, production-ready code