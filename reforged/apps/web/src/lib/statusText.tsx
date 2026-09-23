import type { ReactNode } from 'react';

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

export function StatusText({ text }: { text: string }): ReactNode {
  return text.split(STATUS_KEYWORD_PATTERN).map((part, index) =>
    STATUS_KEYWORDS_LOWER.has(part.toLocaleLowerCase('pl-PL')) ? <strong key={part + '-' + index}>{part}</strong> : part,
  );
}
