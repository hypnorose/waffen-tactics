import React, { useState, useEffect, useRef } from 'react';
import api from '../services/api';
import NotificationModal from '../components/NotificationModal';

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
  board_units: Array<{
    id: string;
    name: string;
    cost: number;
    level: number;
    stars: number;
  }>;
  bench_units: Array<{
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
  const [unitPopularity, setUnitPopularity] = useState<Record<number, Record<string, number>>>({});
  const [selectedTraits, setSelectedTraits] = useState<Set<string>>(new Set());
  const [selectedUnits, setSelectedUnits] = useState<Set<string>>(new Set());
  const [activeFilter, setActiveFilter] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTeam, setSelectedTeam] = useState<TeamDetails | null>(null);
  const [showTeamModal, setShowTeamModal] = useState(false);
  const [unitsMap, setUnitsMap] = useState<Record<string, any>>({});
  const [unitsByName, setUnitsByName] = useState<Record<string, any>>({});
  const [unitsLoaded, setUnitsLoaded] = useState(false);
  const [gamesPage, setGamesPage] = useState(1);
  const [teamsPage, setTeamsPage] = useState(1);
  const [gamesTotalPages, setGamesTotalPages] = useState(1);
  const [teamsTotalPages, setTeamsTotalPages] = useState(1);
  const [currentTab, setCurrentTab] = useState<'games' | 'teams' | 'metrics' | 'traits' | 'units'>('games');
  const [showNotification, setShowNotification] = useState(false);
  const [notificationMessage, setNotificationMessage] = useState('');

  useEffect(() => {
    loadUnits();
    loadData();
  }, [activeFilter, gamesPage, teamsPage]);

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

  const showNotificationModal = (message: string) => {
    setNotificationMessage(message);
    setShowNotification(true);
  };

  const closeNotification = () => {
    setShowNotification(false);
    setNotificationMessage('');
  };

  useEffect(() => {
    // default: select top 6 units by total count
    const totals: Record<string, number> = {};
    Object.values(unitPopularity).forEach(map => {
      Object.entries(map).forEach(([u, v]) => { totals[u] = (totals[u] || 0) + v; });
    });
    const sorted = Object.keys(totals).sort((a,b) => (totals[b]||0) - (totals[a]||0));
    const initial = new Set(sorted.slice(0, 6));
    setSelectedUnits(initial);
  }, [unitPopularity]);

  // Initialize selected traits when popularity data changes
  

  const loadUnits = async () => {
    try {
      const res = await api.get('/game/units');
      const units = res.data;  // res.data is already the array
      const map: Record<string, any> = {};
      const nameMap: Record<string, any> = {};
      units.forEach((unit: any) => {
        map[unit.id] = unit;
        nameMap[unit.name] = unit;
      });
      setUnitsMap(map);
      setUnitsByName(nameMap);
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

      const [gamesRes, teamsRes, metricsRes, traitsRes, unitsRes] = await Promise.all([
        api.get('/api/admin/games', { params: { page: gamesPage, limit: 20 } }),
        api.get('/api/admin/teams', { params: { active: activeFilter, page: teamsPage, limit: 20 } }),
        api.get('/api/admin/metrics'),
        api.get('/api/admin/traits-popularity'),
        api.get('/api/admin/units-popularity')
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
      if (unitsRes?.data?.popularity) {
        setUnitPopularity(unitsRes.data.popularity);
      } else {
        setUnitPopularity({});
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
      showNotificationModal('Units not loaded yet, please wait...');
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

  const unitNamesSet = new Set<string>();
  rounds.forEach(r => {
    const m = unitPopularity[r];
    if (m) Object.keys(m).forEach(u => unitNamesSet.add(u));
  });
  const unitNames = Array.from(unitNamesSet).sort();

  const toggleTrait = (trait: string) => {
    setSelectedTraits(prev => {
      const copy = new Set(prev);
      if (copy.has(trait)) copy.delete(trait); else copy.add(trait);
      return copy;
    });
  };

  const toggleUnit = (unit: string) => {
    setSelectedUnits(prev => {
      const copy = new Set(prev);
      if (copy.has(unit)) copy.delete(unit); else copy.add(unit);
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

  const CombinedTraitChart: React.FC<{ traits: string[]; rounds: number[]; data: Record<number, Record<string, number>> }> = ({ traits, rounds, data }) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const [containerWidth, setContainerWidth] = useState(1200);

    useEffect(() => {
      const updateWidth = () => {
        if (containerRef.current) {
          setContainerWidth(containerRef.current.offsetWidth);
        }
      };

      updateWidth();
      window.addEventListener('resize', updateWidth);
      return () => window.removeEventListener('resize', updateWidth);
    }, []);

    const width = containerWidth;
    const height = 500;
    const padding = 60;
    const colors = ['#60a5fa', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1'];

    // Find global max across all traits
    const allValues = traits.flatMap(trait => rounds.map(r => data[r]?.[trait] || 0));
    const max = Math.max(...allValues, 1);

    return (
      <div ref={containerRef} className="bg-gray-700 p-4 rounded w-full">
        <h3 className="text-lg font-bold mb-4">Trait Popularity Over Rounds</h3>
        <svg width={width} height={height}>
          {/* Grid lines */}
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#374151" strokeWidth="0.5"/>
            </pattern>
          </defs>
          <rect width={width} height={height} fill="url(#grid)" />

          {/* X and Y axes */}
          <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#9ca3af" strokeWidth={1} />
          <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="#9ca3af" strokeWidth={1} />

          {/* Round labels */}
          {rounds.map((r, i) => {
            const x = padding + (i / Math.max(1, rounds.length - 1)) * (width - padding * 2);
            return (
              <text key={r} x={x} y={height - padding + 15} textAnchor="middle" fill="#9ca3af" fontSize="10">
                R{r}
              </text>
            );
          })}

          {/* Value labels */}
          {[0, 0.25, 0.5, 0.75, 1].map(ratio => {
            const y = height - padding - ratio * (height - padding * 2);
            const value = Math.round(max * ratio);
            return (
              <text key={ratio} x={padding - 10} y={y + 3} textAnchor="end" fill="#9ca3af" fontSize="10">
                {value}
              </text>
            );
          })}

          {/* Lines for each trait */}
          {traits.map((trait, traitIndex) => {
            const values = rounds.map(r => data[r]?.[trait] || 0);
            const points = values.map((v, i) => {
              const x = padding + (i / Math.max(1, values.length - 1)) * (width - padding * 2);
              const y = height - padding - (v / max) * (height - padding * 2);
              return `${x},${y}`;
            }).join(' ');
            const color = colors[traitIndex % colors.length];

            return (
              <g key={trait}>
                <polyline fill="none" stroke={color} strokeWidth={2} points={points} />
                {values.map((v, i) => {
                  const x = padding + (i / Math.max(1, values.length - 1)) * (width - padding * 2);
                  const y = height - padding - (v / max) * (height - padding * 2);
                  return <circle key={i} cx={x} cy={y} r={3} fill={color} />;
                })}
              </g>
            );
          })}
        </svg>

        {/* Legend */}
        <div className="flex flex-wrap gap-4 mt-4">
          {traits.map((trait, traitIndex) => {
            const color = colors[traitIndex % colors.length];
            return (
              <div key={trait} className="flex items-center gap-2">
                <div className="w-4 h-4 rounded" style={{ backgroundColor: color }}></div>
                <span className="text-sm">{trait}</span>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const CombinedUnitChart: React.FC<{ units: string[]; rounds: number[]; data: Record<number, Record<string, number>> }> = ({ units, rounds, data }) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const [containerWidth, setContainerWidth] = useState(1200);

    useEffect(() => {
      const updateWidth = () => {
        if (containerRef.current) {
          setContainerWidth(containerRef.current.offsetWidth);
        }
      };

      updateWidth();
      window.addEventListener('resize', updateWidth);
      return () => window.removeEventListener('resize', updateWidth);
    }, []);

    const width = containerWidth;
    const height = 500;
    const padding = 60;
    const colors = ['#60a5fa', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1'];

    // Find global max across all units
    const allValues = units.flatMap(unit => rounds.map(r => data[r]?.[unit] || 0));
    const max = Math.max(...allValues, 1);

    return (
      <div ref={containerRef} className="bg-gray-700 p-4 rounded w-full">
        <h3 className="text-lg font-bold mb-4">Unit Popularity Over Rounds</h3>
        <svg width={width} height={height}>
          {/* Grid lines */}
          <defs>
            <pattern id="grid-units" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#374151" strokeWidth="0.5"/>
            </pattern>
          </defs>
          <rect width={width} height={height} fill="url(#grid-units)" />

          {/* X and Y axes */}
          <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#9ca3af" strokeWidth={1} />
          <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="#9ca3af" strokeWidth={1} />

          {/* Round labels */}
          {rounds.map((r, i) => {
            const x = padding + (i / Math.max(1, rounds.length - 1)) * (width - padding * 2);
            return (
              <text key={r} x={x} y={height - padding + 15} textAnchor="middle" fill="#9ca3af" fontSize="10">
                R{r}
              </text>
            );
          })}

          {/* Value labels */}
          {[0, 0.25, 0.5, 0.75, 1].map(ratio => {
            const y = height - padding - ratio * (height - padding * 2);
            const value = Math.round(max * ratio);
            return (
              <text key={ratio} x={padding - 10} y={y + 3} textAnchor="end" fill="#9ca3af" fontSize="10">
                {value}
              </text>
            );
          })}

          {/* Lines for each unit */}
          {units.map((unit, unitIndex) => {
            const values = rounds.map(r => data[r]?.[unit] || 0);
            const points = values.map((v, i) => {
              const x = padding + (i / Math.max(1, values.length - 1)) * (width - padding * 2);
              const y = height - padding - (v / max) * (height - padding * 2);
              return `${x},${y}`;
            }).join(' ');
            const color = colors[unitIndex % colors.length];

            return (
              <g key={unit}>
                <polyline fill="none" stroke={color} strokeWidth={2} points={points} />
                {values.map((v, i) => {
                  const x = padding + (i / Math.max(1, values.length - 1)) * (width - padding * 2);
                  const y = height - padding - (v / max) * (height - padding * 2);
                  return <circle key={i} cx={x} cy={y} r={3} fill={color} />;
                })}
              </g>
            );
          })}
        </svg>

        {/* Legend */}
        <div className="flex flex-wrap gap-4 mt-4">
          {units.map((unit, unitIndex) => {
            const color = colors[unitIndex % colors.length];
            return (
              <div key={unit} className="flex items-center gap-2">
                <div className="w-4 h-4 rounded" style={{ backgroundColor: color }}></div>
                <span className="text-sm">{unit}</span>
              </div>
            );
          })}
        </div>
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
          <button onClick={() => setCurrentTab('units')} className={`px-4 py-2 rounded ${currentTab === 'units' ? 'bg-blue-600' : 'bg-gray-700'}`}>Units</button>
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

              {/* Combined Chart */}
              {selectedTraits.size > 0 && (
                <CombinedTraitChart traits={Array.from(selectedTraits)} rounds={rounds} data={traitPopularity} />
              )}
            </>
          )}
        </div>
      )}

      {/* Units Tab */}
      {currentTab === 'units' && (
        <div className="bg-gray-800 p-6 rounded-lg mb-8">
          <h2 className="text-2xl font-bold mb-4">Unit Popularity by Round</h2>
          {rounds.length === 0 ? (
            <div className="text-gray-300">No data available</div>
          ) : (
            <>
              <div className="overflow-x-auto mb-4">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-700">
                      <th className="text-left p-2">Unit</th>
                      {rounds.map((r) => (
                        <th key={r} className="text-left p-2">R{r}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {unitNames.map((unit) => (
                      <tr key={unit} className="border-b border-gray-700">
                        <td className="p-2">{unit}</td>
                        {rounds.map((r) => (
                          <td key={`${unit}-${r}`} className="p-2">{unitPopularity[r]?.[unit] || 0}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Unit selector */}
              <div className="mb-4">
                <div className="font-semibold mb-2">Toggle units to show charts</div>
                <div className="space-y-4">
                  {[1, 2, 3, 4, 5].map(cost => {
                    const unitsInCost = unitNames.filter(u => {
                      const unitData = unitsByName[u];
                      return unitData?.cost === cost;
                    });
                    if (unitsInCost.length === 0) return null;

                    return (
                      <div key={cost}>
                        <div className="text-sm font-medium text-gray-300 mb-2">
                          {cost} Gold Units ({unitsInCost.length})
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {unitsInCost.map(u => (
                            <label key={u} className={`px-3 py-1 rounded cursor-pointer ${selectedUnits.has(u) ? 'bg-blue-600' : 'bg-gray-700'}`}>
                              <input type="checkbox" checked={selectedUnits.has(u)} onChange={() => toggleUnit(u)} className="mr-2" />
                              {u}
                            </label>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Combined Chart */}
              {selectedUnits.size > 0 && (
                <CombinedUnitChart units={Array.from(selectedUnits)} rounds={rounds} data={unitPopularity} />
              )}
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
      <NotificationModal
        isOpen={showNotification}
        message={notificationMessage}
        onClose={closeNotification}
      />
    </div>
  );
};

export default Admin;