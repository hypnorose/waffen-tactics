import type { RankInfo, RankTier } from '@reforged/schema';

const TIER_ICON: Record<RankTier, string> = {
  bronze: '🥉',
  silver: '🥈',
  gold: '🥇',
  platinum: '💠',
  diamond: '💎',
  master: '👑',
};

const TIER_LABEL: Record<RankTier, string> = {
  bronze: 'Brąz',
  silver: 'Srebro',
  gold: 'Złoto',
  platinum: 'Platyna',
  diamond: 'Diament',
  master: 'Mistrz',
};

const DIVISION_ROMAN = ['', 'I', 'II', 'III', 'IV'];

export function RankBadge({ rank }: { rank: RankInfo }) {
  return (
    <div className={`rank-badge tier-${rank.tier}`}>
      <span className="rank-icon">{TIER_ICON[rank.tier]}</span>
      <span className="rank-label">
        {TIER_LABEL[rank.tier]}
        {rank.division ? ` ${DIVISION_ROMAN[rank.division]}` : ''}
      </span>
      <span className="rank-elo">{rank.elo} ELO</span>
    </div>
  );
}
