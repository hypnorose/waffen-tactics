import React, { useState, useEffect } from 'react';
import api from '../services/api';

interface Game {
  user_id: number;
  nickname: string;
  level: number;
  gold: number;
  health: number;
  round: number;
  xp: number;
  board: any[];
  bench: any[];
  updated_at: string;
}

interface Team {
  id: number;
  user_id: number;
  nickname: string;
  team: {board: any[]; bench: any[];};
  wins: number;
  losses: number;
  level: number;
  is_active: boolean;
  created_at: string;
}

interface GamesResponse {
  games: Game[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

interface TeamsResponse {
  teams: Team[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

interface TeamDetails {
  id: number;
  user_id: number;
  nickname: string;
  units: Array<{
    id: string;
    name: string;
    cost: number;
    level: number;
    stars: number;
  }>;
  wins: number;
  losses: number;
  level: number;
  is_active: boolean;
  created_at: string;
}

interface Metrics {
  total_players: number;
  total_teams: number;
  active_teams: number;
  total_wins: number;
  total_losses: number;
  recent_games: number;
}

const Admin: React.FC = () => {
  const [games, setGames] = useState<Game[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [traitPopularity, setTraitPopularity] = useState<Record<number, Record<string, number>>>({});
  const [selectedTraits, setSelectedTraits] = useState<Set<string>>(new Set());
  const [activeFilter, setActiveFilter] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTeam, setSelectedTeam] = useState<TeamDetails | null>(null);
  const [showTeamModal, setShowTeamModal] = useState(false);
  const [unitsMap, setUnitsMap] = useState<Record<string, any>>({});
  const [unitsLoaded, setUnitsLoaded] = useState(false);
  const [gamesPage, setGamesPage] = useState(1);
  const [teamsPage, setTeamsPage] = useState(1);
  const [gamesTotalPages, setGamesTotalPages] = useState(1);
  const [teamsTotalPages, setTeamsTotalPages] = useState(1);
  const [currentTab, setCurrentTab] = useState<'games' | 'teams' | 'metrics' | 'traits'>('games');

  useEffect(() => {
    loadUnits();
    loadData();
  }, [activeFilter, gamesPage, teamsPage]);

  // Initialize selected traits when popularity data changes
  

  const loadUnits = async () => {
    try {
      const res = await api.get('/game/units');
      const units = res.data;  // res.data is already the array
      const map: Record<string, any> = {};
      units.forEach((unit: any) => {
        map[unit.id] = unit;
      });
      setUnitsMap(map);
      setUnitsLoaded(true);
      console.log('Units loaded:', Object.keys(map).length);
    } catch (err) {
      console.error('Failed to load units:', err);
    }
  };

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [gamesRes, teamsRes, metricsRes, traitsRes] = await Promise.all([
        api.get('/api/admin/games', { params: { page: gamesPage, limit: 20 } }),
        api.get('/api/admin/teams', { params: { active: activeFilter, page: teamsPage, limit: 20 } }),
        api.get('/api/admin/metrics'),
        api.get('/api/admin/traits-popularity')
      ]);

      setGames(gamesRes.data.games);
      setGamesTotalPages(gamesRes.data.total_pages);
      setTeams(teamsRes.data.teams);
      setTeamsTotalPages(teamsRes.data.total_pages);
      setMetrics(metricsRes.data);
      if (traitsRes?.data?.popularity) {
        setTraitPopularity(traitsRes.data.popularity);
      } else {
        setTraitPopularity({});
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to load admin data');
    } finally {
      setLoading(false);
    }
  };

  const loadTeamDetails = async (teamId: number) => {
    try {
      const res = await api.get(`/api/admin/team/${teamId}`);
      setSelectedTeam(res.data);
      setShowTeamModal(true);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to load team details');
    }
  };

  const showPlayerTeam = (game: Game) => {
    if (!unitsLoaded) {
      alert('Units not loaded yet, please wait...');
      return;
    }

    console.log('Showing team for', game.nickname, 'units loaded:', unitsLoaded);
    // Convert player team to similar format as TeamDetails
    const boardUnitsDetails = game.board.map((unit: any) => {
      const unitData = unitsMap[unit.unit_id];
      console.log('Unit', unit.unit_id, 'data:', unitData);
      return {
        id: unit.unit_id,
        name: unitData?.name || 'Unknown',
        cost: unitData?.cost || 0,
        level: unit.star_level || 1,
        stars: unit.star_level || 1
      };
    });

    const benchUnitsDetails = game.bench.map((unit: any) => {
      const unitData = unitsMap[unit.unit_id];
      console.log('Unit', unit.unit_id, 'data:', unitData);
      return {
        id: unit.unit_id,
        name: unitData?.name || 'Unknown',
        cost: unitData?.cost || 0,
        level: unit.star_level || 1,
        stars: unit.star_level || 1
      };
    });

    const playerTeamDetails = {
      id: 0, // Not applicable
      user_id: game.user_id,
      nickname: game.nickname,
      board_units: boardUnitsDetails,
      bench_units: benchUnitsDetails,
      wins: 0, // Not available
      losses: 0, // Not available
      level: game.level,
      is_active: true,
      created_at: game.updated_at
    };

    setSelectedTeam(playerTeamDetails);
    setShowTeamModal(true);
  };

  if (loading) {
    return <div className="min-h-screen bg-gray-900 text-white p-8">Loading...</div>;
  }

  if (error) {
    return <div className="min-h-screen bg-gray-900 text-white p-8">Error: {error}</div>;
  }

  const rounds = Object.keys(traitPopularity).map(k => parseInt(k, 10)).sort((a, b) => a - b);
  const traitNamesSet = new Set<string>();
  rounds.forEach(r => {
    const m = traitPopularity[r];
    if (m) Object.keys(m).forEach(t => traitNamesSet.add(t));
  });
  const traitNames = Array.from(traitNamesSet).sort();

  useEffect(() => {
    // default: select top 6 traits by total count
    const totals: Record<string, number> = {};
    Object.values(traitPopularity).forEach(map => {
      Object.entries(map).forEach(([t, v]) => { totals[t] = (totals[t] || 0) + v; });
    });
    const sorted = Object.keys(totals).sort((a,b) => (totals[b]||0) - (totals[a]||0));
    const initial = new Set(sorted.slice(0, 6));
    setSelectedTraits(initial);
  }, [traitPopularity]);

  const toggleTrait = (trait: string) => {
    setSelectedTraits(prev => {
      const copy = new Set(prev);
      if (copy.has(trait)) copy.delete(trait); else copy.add(trait);
      return copy;
    });
  };

  const TraitChart: React.FC<{ trait: string; rounds: number[]; data: Record<number, Record<string, number>> }> = ({ trait, rounds, data }) => {
    // Build values array aligned to rounds
    const values = rounds.map(r => data[r]?.[trait] || 0);
    const width = 300;
    const height = 80;
    const padding = 8;
    const max = Math.max(...values, 1);
    const points = values.map((v, i) => {
      const x = padding + (i / Math.max(1, values.length - 1)) * (width - padding * 2);
      const y = height - padding - (v / max) * (height - padding * 2);
      return `${x},${y}`;
    }).join(' ');

    return (
      <div className="bg-gray-700 p-3 rounded mb-3" style={{ width }}>
        <div className="flex justify-between items-center mb-2">
          <div className="font-bold">{trait}</div>
          <div className="text-sm text-gray-300">Total: {values.reduce((a,b) => a+b, 0)}</div>
        </div>
        <svg width={width} height={height}>
          <polyline fill="none" stroke="#60a5fa" strokeWidth={2} points={points} />
          {values.map((v, i) => {
            const x = padding + (i / Math.max(1, values.length - 1)) * (width - padding * 2);
            const y = height - padding - (v / max) * (height - padding * 2);
            return <circle key={i} cx={x} cy={y} r={2.2} fill="#60a5fa" />;
          })}
        </svg>
        <div className="text-xs text-gray-400 mt-1">Rounds: {rounds.join(', ')}</div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <h1 className="text-3xl font-bold mb-8">Admin Panel</h1>


      {/* Navbar / Tabs */}
      <div className="mb-6">
        <div className="flex gap-2">
          <button onClick={() => setCurrentTab('games')} className={`px-4 py-2 rounded ${currentTab === 'games' ? 'bg-blue-600' : 'bg-gray-700'}`}>Games</button>
          <button onClick={() => setCurrentTab('teams')} className={`px-4 py-2 rounded ${currentTab === 'teams' ? 'bg-blue-600' : 'bg-gray-700'}`}>Teams</button>
          <button onClick={() => setCurrentTab('metrics')} className={`px-4 py-2 rounded ${currentTab === 'metrics' ? 'bg-blue-600' : 'bg-gray-700'}`}>Metrics</button>
          <button onClick={() => setCurrentTab('traits')} className={`px-4 py-2 rounded ${currentTab === 'traits' ? 'bg-blue-600' : 'bg-gray-700'}`}>Traits</button>
        </div>
      </div>

      {/* Metrics Tab */}
      {currentTab === 'metrics' && metrics && (
        <div className="bg-gray-800 p-6 rounded-lg mb-8">
          <h2 className="text-2xl font-bold mb-4">Metrics</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="bg-gray-700 p-4 rounded">
              <div className="text-2xl font-bold">{metrics.total_players}</div>
              <div className="text-sm text-gray-300">Total Players</div>
            </div>
            <div className="bg-gray-700 p-4 rounded">
              <div className="text-2xl font-bold">{metrics.total_teams}</div>
              <div className="text-sm text-gray-300">Total Teams</div>
            </div>
            <div className="bg-gray-700 p-4 rounded">
              <div className="text-2xl font-bold">{metrics.active_teams}</div>
              <div className="text-sm text-gray-300">Active Teams</div>
            </div>
            <div className="bg-gray-700 p-4 rounded">
              <div className="text-2xl font-bold">{metrics.total_wins}</div>
              <div className="text-sm text-gray-300">Total Wins</div>
            </div>
            <div className="bg-gray-700 p-4 rounded">
              <div className="text-2xl font-bold">{metrics.total_losses}</div>
              <div className="text-sm text-gray-300">Total Losses</div>
            </div>
            <div className="bg-gray-700 p-4 rounded">
              <div className="text-2xl font-bold">{metrics.recent_games}</div>
              <div className="text-sm text-gray-300">Games (24h)</div>
            </div>
          </div>
        </div>
      )}

      {/* Traits Tab */}
      {currentTab === 'traits' && (
        <div className="bg-gray-800 p-6 rounded-lg mb-8">
          <h2 className="text-2xl font-bold mb-4">Trait Popularity by Round</h2>
          {rounds.length === 0 ? (
            <div className="text-gray-300">No data available</div>
          ) : (
            <>
              <div className="overflow-x-auto mb-4">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-700">
                      <th className="text-left p-2">Trait</th>
                      {rounds.map((r) => (
                        <th key={r} className="text-left p-2">R{r}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {traitNames.map((trait) => (
                      <tr key={trait} className="border-b border-gray-700">
                        <td className="p-2">{trait}</td>
                        {rounds.map((r) => (
                          <td key={`${trait}-${r}`} className="p-2">{traitPopularity[r]?.[trait] || 0}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Trait selector */}
              <div className="mb-4">
                <div className="font-semibold mb-2">Toggle traits to show charts</div>
                <div className="flex flex-wrap gap-2">
                  {traitNames.map(t => (
                    <label key={t} className={`px-3 py-1 rounded cursor-pointer ${selectedTraits.has(t) ? 'bg-blue-600' : 'bg-gray-700'}`}>
                      <input type="checkbox" checked={selectedTraits.has(t)} onChange={() => toggleTrait(t)} className="mr-2" />
                      {t}
                    </label>
                  ))}
                </div>
              </div>

              {/* Charts grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {Array.from(selectedTraits).map(trait => (
                  <TraitChart key={trait} trait={trait} rounds={rounds} data={traitPopularity} />
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* Active Games */}
      {currentTab === 'games' && (
        <div className="bg-gray-800 p-6 rounded-lg mb-8">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold">Active Games ({games.length})</h2>
          {/* Pagination */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setGamesPage(Math.max(1, gamesPage - 1))}
              disabled={gamesPage <= 1}
              className="px-3 py-1 bg-gray-600 hover:bg-gray-500 disabled:bg-gray-700 disabled:cursor-not-allowed rounded"
            >
              Prev
            </button>
            <span className="text-sm">
              Page {gamesPage} of {gamesTotalPages}
            </span>
            <button
              onClick={() => setGamesPage(Math.min(gamesTotalPages, gamesPage + 1))}
              disabled={gamesPage >= gamesTotalPages}
              className="px-3 py-1 bg-gray-600 hover:bg-gray-500 disabled:bg-gray-700 disabled:cursor-not-allowed rounded"
            >
              Next
            </button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="text-left p-2">User ID</th>
                <th className="text-left p-2">Nickname</th>
                <th className="text-left p-2">Level</th>
                <th className="text-left p-2">Gold</th>
                <th className="text-left p-2">Health</th>
                <th className="text-left p-2">Round</th>
                <th className="text-left p-2">XP</th>
                <th className="text-left p-2">Team Size</th>
                <th className="text-left p-2">Last Update</th>
                <th className="text-left p-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {games.map((game) => (
                <tr key={game.user_id} className="border-b border-gray-700">
                  <td className="p-2">{game.user_id}</td>
                  <td className="p-2">{game.nickname}</td>
                  <td className="p-2">{game.level}</td>
                  <td className="p-2">{game.gold}</td>
                  <td className="p-2">{game.health}</td>
                  <td className="p-2">{game.round}</td>
                  <td className="p-2">{game.xp}</td>
                  <td className="p-2">{(game.board?.length || 0) + (game.bench?.length || 0)}</td>
                  <td className="p-2">{new Date(game.updated_at).toLocaleString()}</td>
                  <td className="p-2">
                    <button
                      onClick={() => showPlayerTeam(game)}
                      className="bg-blue-600 hover:bg-blue-700 px-3 py-1 rounded text-sm"
                    >
                      View Team
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        </div>
      )}

      {/* Teams */}
      {currentTab === 'teams' && (
        <div className="bg-gray-800 p-6 rounded-lg">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold">Team History ({teams.length})</h2>
          <div className="flex items-center gap-4">
            {/* Filter buttons */}
            <div className="flex gap-2">
              <button
                onClick={() => { setActiveFilter(true); setTeamsPage(1); }}
                className={`px-4 py-2 rounded ${activeFilter ? 'bg-blue-600' : 'bg-gray-600'}`}
              >
                Active
              </button>
              <button
                onClick={() => { setActiveFilter(false); setTeamsPage(1); }}
                className={`px-4 py-2 rounded ${!activeFilter ? 'bg-blue-600' : 'bg-gray-600'}`}
              >
                Inactive
              </button>
            </div>
            {/* Pagination */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => setTeamsPage(Math.max(1, teamsPage - 1))}
                disabled={teamsPage <= 1}
                className="px-3 py-1 bg-gray-600 hover:bg-gray-500 disabled:bg-gray-700 disabled:cursor-not-allowed rounded"
              >
                Prev
              </button>
              <span className="text-sm">
                Page {teamsPage} of {teamsTotalPages}
              </span>
              <button
                onClick={() => setTeamsPage(Math.min(teamsTotalPages, teamsPage + 1))}
                disabled={teamsPage >= teamsTotalPages}
                className="px-3 py-1 bg-gray-600 hover:bg-gray-500 disabled:bg-gray-700 disabled:cursor-not-allowed rounded"
              >
                Next
              </button>
            </div>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="text-left p-2">ID</th>
                <th className="text-left p-2">User ID</th>
                <th className="text-left p-2">Nickname</th>
                <th className="text-left p-2">Level</th>
                <th className="text-left p-2">Wins</th>
                <th className="text-left p-2">Losses</th>
                <th className="text-left p-2">Team Size</th>
                <th className="text-left p-2">Active</th>
                <th className="text-left p-2">Created</th>
                <th className="text-left p-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {teams.map((team) => (
                <tr key={team.id} className="border-b border-gray-700">
                  <td className="p-2">{team.id}</td>
                  <td className="p-2">{team.user_id}</td>
                  <td className="p-2">{team.nickname}</td>
                  <td className="p-2">{team.level}</td>
                  <td className="p-2">{team.wins}</td>
                  <td className="p-2">{team.losses}</td>
                  <td className="p-2">{team.team.board.length + team.team.bench.length}</td>
                  <td className="p-2">{team.is_active ? 'Yes' : 'No'}</td>
                  <td className="p-2">{new Date(team.created_at).toLocaleString()}</td>
                  <td className="p-2">
                    <button
                      onClick={() => loadTeamDetails(team.id)}
                      className="bg-blue-600 hover:bg-blue-700 px-3 py-1 rounded text-sm"
                    >
                      View Team
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        </div>
      )}

      {/* Team Details Modal */}
      {showTeamModal && selectedTeam && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4">
          <div className="bg-gray-800 p-6 rounded-lg max-w-2xl w-full max-h-96 overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-bold">Team Details - {selectedTeam.nickname}</h3>
              <button
                onClick={() => setShowTeamModal(false)}
                className="text-gray-400 hover:text-white"
              >
                ✕
              </button>
            </div>
            
            <div className="mb-4">
              <p><strong>User ID:</strong> {selectedTeam.user_id}</p>
              <p><strong>Nickname:</strong> {selectedTeam.nickname}</p>
              <p><strong>Level:</strong> {selectedTeam.level}</p>
              {selectedTeam.wins !== undefined && (
                <p><strong>Wins:</strong> {selectedTeam.wins} | <strong>Losses:</strong> {selectedTeam.losses}</p>
              )}
              {selectedTeam.is_active !== undefined && (
                <p><strong>Active:</strong> {selectedTeam.is_active ? 'Yes' : 'No'}</p>
              )}
              <p><strong>Created:</strong> {new Date(selectedTeam.created_at).toLocaleString()}</p>
            </div>

            <h4 className="text-lg font-bold mb-2">Board Units ({selectedTeam.board_units?.length || 0})</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mb-4">
              {selectedTeam.board_units?.map((unit, index) => (
                <div key={index} className="bg-gray-700 p-3 rounded">
                  <div className="font-bold">{unit.name}</div>
                  <div className="text-sm text-gray-300">
                    Cost: {unit.cost} | Level: {unit.level} | Stars: {'★'.repeat(unit.stars)}
                  </div>
                </div>
              )) || []}
            </div>

            <h4 className="text-lg font-bold mb-2">Bench Units ({selectedTeam.bench_units?.length || 0})</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {selectedTeam.bench_units?.map((unit, index) => (
                <div key={index} className="bg-gray-700 p-3 rounded">
                  <div className="font-bold">{unit.name}</div>
                  <div className="text-sm text-gray-300">
                    Cost: {unit.cost} | Level: {unit.level} | Stars: {'★'.repeat(unit.stars)}
                  </div>
                </div>
              )) || []}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Admin;