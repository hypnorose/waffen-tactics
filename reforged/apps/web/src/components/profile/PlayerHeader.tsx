import type { RunState, UserProfile } from '@reforged/schema';
import { RankBadge } from './RankBadge.js';

interface Props {
  profile: UserProfile;
  run: RunState | null;
}

export function PlayerHeader({ profile, run }: Props) {
  return (
    <header className="player-header">
      <div className="player-identity">
        {profile.avatarUrl ? (
          <img className="player-avatar" src={profile.avatarUrl} alt="" />
        ) : (
          <div className="player-avatar player-avatar-fallback">{profile.username.slice(0, 1).toUpperCase()}</div>
        )}
        <div className="player-identity-text">
          <div className="player-username">{profile.username}</div>
          <RankBadge rank={profile.rank} />
        </div>
      </div>

      {run && (
        <div className="run-stats">
          <span className="run-stat">Runda {run.roundNumber}</span>
          <span className="run-stat run-stat-win">🏆 {run.wins} / 10</span>
          <span className="run-stat run-stat-loss">💀 {run.losses} / 5</span>
        </div>
      )}
    </header>
  );
}
