// Parse the desync log to find when effects diverge
const desyncLog = [
  {
    "unit_id": "opp_2",
    "unit_name": "Alyson Stark",
    "seq": 92,
    "timestamp": 0.9999999999999999,
    "diff": {
      "effects": {
        "ui": [],
        "server": [
          {
            "type": "stun",
            "duration": 1.5
          },
          {
            "id": "fa2ef812-4dc9-47ee-915f-a6053960a51e",
            "type": "damage_over_time"
          }
        ]
      }
    },
    "pending_events": [],
    "note": "event mana_update diff (opponent)"
  }
];

console.log("CRITICAL FINDING:");
console.log("- At seq 92 (t=1.0s), event type is 'mana_update'");
console.log("- UI has effects: []");
console.log("- Server has effects: [stun, DoT]");
console.log("");
console.log("This means:");
console.log("1. Stun and DoT effects were applied BEFORE seq 92");
console.log("2. The UI is missing these effects during mana_update event");
console.log("3. Effects were either:");
console.log("   a) Never added to UI state (unit_stunned/damage_over_time_applied events missing or broken)");
console.log("   b) Incorrectly removed from UI state before they should be");
console.log("");
console.log("HYPOTHESIS: UI is filtering/removing effects somewhere that it shouldn't.");
