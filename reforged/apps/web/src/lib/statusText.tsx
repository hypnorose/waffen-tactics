import type { ReactNode } from 'react';

export type StatusTone =
  | 'strength'
  | 'haste'
  | 'dodge'
  | 'vampirism'
  | 'shield'
  | 'poison'
  | 'slow'
  | 'regen'
  | 'fragility'
  | 'thorns'
  | 'execution'
  | 'multicast';

// Keep player-facing status names localized and visually scannable in every
// tooltip that renders authored content descriptions.
const STATUS_KEYWORDS = [
  'Przyspieszenia',
  'Przyspieszenie',
  'Spowolnienia',
  'Spowolnienie',
  'Regeneracji',
  'Regeneracja',
  'Wampiryzmu',
  'Wampiryzm',
  'Kruchości',
  'Kruchość',
  'Egzekucji',
  'Egzekucja',
  'Trucizny',
  'Trucizna',
  'Tarczy',
  'Tarczę',
  'Tarcza',
  'Kolców',
  'Kolce',
  'Uniku',
  'Unik',
  'Siły',
  'Siła',
].sort((a, b) => b.length - a.length);

const STATUS_KEYWORDS_LOWER = new Set(STATUS_KEYWORDS.map((keyword) => keyword.toLocaleLowerCase('pl-PL')));
const STATUS_KEYWORD_PATTERN = new RegExp('(' + STATUS_KEYWORDS.join('|') + ')', 'gi');
const STATUS_TONE_BY_KEYWORD: Record<string, StatusTone> = {
  'siła': 'strength',
  'siły': 'strength',
  'przyspieszenie': 'haste',
  'przyspieszenia': 'haste',
  'unik': 'dodge',
  'uniku': 'dodge',
  'wampiryzm': 'vampirism',
  'wampiryzmu': 'vampirism',
  'tarcza': 'shield',
  'tarczy': 'shield',
  'tarczę': 'shield',
  'trucizna': 'poison',
  'trucizny': 'poison',
  'spowolnienie': 'slow',
  'spowolnienia': 'slow',
  'regeneracja': 'regen',
  'regeneracji': 'regen',
  'kruchość': 'fragility',
  'kruchości': 'fragility',
  'kolce': 'thorns',
  'kolców': 'thorns',
  'egzekucja': 'execution',
  'egzekucji': 'execution',
};

export function StatusText({ text }: { text: string }): ReactNode {
  return text.split(STATUS_KEYWORD_PATTERN).map((part, index) => {
    if (!STATUS_KEYWORDS_LOWER.has(part.toLocaleLowerCase('pl-PL'))) return part;
    const tone = STATUS_TONE_BY_KEYWORD[part.toLocaleLowerCase('pl-PL')];
    return <strong key={part + '-' + index} className={'status-keyword status-keyword-' + tone}>{part}</strong>;
  });
}
