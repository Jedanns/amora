import { useState, useMemo } from 'react';
import { Plus, Sword, Trash2 } from 'lucide-react';
import { CLASS_LABELS, type CharacterClass } from '../../types';
import type { Campaign } from '@/types/game';

interface HubScreenProps {
  playerName?: string;
  campaigns: Campaign[];
  isLoading?: boolean;
  resumingSessionId?: string | null;
  onNewCampaign: () => void;
  onPlayCampaign: (sessionId: string) => void;
  onDeleteCampaign?: (sessionId: string) => void;
}

interface Particle {
  id: number;
  x: number;
  y: number;
  size: number;
  opacity: number;
  duration: number;
  delay: number;
}

function generateParticles(count: number): Particle[] {
  return Array.from({ length: count }, (_, i) => ({
    id: i,
    x: Math.random() * 100,
    y: Math.random() * 100,
    size: Math.random() * 2.5 + 1,
    opacity: Math.random() * 0.5 + 0.1,
    duration: Math.random() * 8 + 6,
    delay: Math.random() * -10,
  }));
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  if (isNaN(date.getTime())) return dateStr;
  return date.toLocaleDateString('fr-FR', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

type FilterOption = 'all' | 'recent';

function HubScreen({ playerName, campaigns, isLoading, resumingSessionId, onNewCampaign, onPlayCampaign, onDeleteCampaign }: HubScreenProps) {
  const [filter, setFilter] = useState<FilterOption>('all');
  const [confirmingDelete, setConfirmingDelete] = useState<string | null>(null);

  const particles = useMemo(() => generateParticles(40), []);

  const filteredCampaigns = useMemo(() => {
    switch (filter) {
      case 'recent':
        return [...campaigns].sort((a, b) => {
          const da = a.updated_at || a.last_played ? new Date(a.updated_at || a.last_played || '').getTime() : 0;
          const db = b.updated_at || b.last_played ? new Date(b.updated_at || b.last_played || '').getTime() : 0;
          return db - da;
        });
      default:
        return campaigns;
    }
  }, [campaigns, filter]);

  const displayName = playerName || 'Aventurier';

  return (
    <div className="relative min-h-screen bg-bg-primary text-text-primary font-main flex flex-col overflow-hidden">
      {/* Particles */}
      <div className="absolute inset-0 pointer-events-none z-0">
        {particles.map((p) => (
          <div
            key={p.id}
            className="absolute rounded-full bg-gold"
            style={{
              left: `${p.x}%`,
              top: `${p.y}%`,
              width: p.size,
              height: p.size,
              animation: `particle-float ${p.duration}s ease-in-out ${p.delay}s infinite`,
              '--p-opacity': p.opacity,
              opacity: p.opacity,
            } as React.CSSProperties}
          />
        ))}
      </div>

      {/* Content */}
      <div className="relative z-1 flex flex-col min-h-screen">
        {/* Header */}
        <header className="flex items-center justify-between px-8 py-4 border-b border-border-primary bg-bg-primary/80 backdrop-blur-[10px]">
          <h1 className="text-base font-bold text-gold uppercase tracking-[3px]">AMORA</h1>
        </header>

        {/* Welcome */}
        <section className="text-center pt-12 pb-6 px-8">
          <h2 className="text-[28px] font-bold text-gold mb-3 [text-shadow:0_0_30px_rgba(201,168,76,0.3)]">
            Bienvenue, {displayName}
          </h2>
          <p className="text-[15px] text-text-secondary max-w-[500px] mx-auto leading-relaxed">
            Vos quetes vous attendent. Creez une nouvelle aventure ou continuez votre voyage.
          </p>
        </section>

        {/* New Campaign Button */}
        <div className="flex justify-center px-8 pt-6 pb-8">
          <button
            className="inline-flex items-center gap-2.5 px-8 py-3.5 bg-gradient-to-br from-gold to-[#b8953e] text-bg-primary rounded-[10px] text-[15px] font-bold cursor-pointer uppercase tracking-[1px] transition-all duration-250 animate-[pulse-glow_3s_ease-in-out_infinite] hover:from-gold hover:to-[#a8883a] hover:-translate-y-0.5"
            onClick={onNewCampaign}
          >
            <Plus size={18} strokeWidth={2} />
            Nouvelle Campagne
          </button>
        </div>

        {/* Campaigns List */}
        <section className="flex-1 px-8 pb-8 max-w-[800px] mx-auto w-full">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-text-primary">Vos Campagnes</h3>
            <select
              className="bg-bg-input text-text-secondary border border-border-primary rounded-md px-3 py-1.5 text-[13px] cursor-pointer outline-none"
              value={filter}
              onChange={(e) => setFilter(e.target.value as FilterOption)}
            >
              <option value="all">Toutes</option>
              <option value="recent">Recentes</option>
            </select>
          </div>

          {isLoading ? (
            <div className="flex justify-center items-center py-12 px-6 text-text-secondary text-sm">
              Chargement des campagnes...
            </div>
          ) : filteredCampaigns.length === 0 ? (
            <div className="text-center py-12 px-6 text-text-secondary">
              <div className="text-[40px] mb-4 opacity-40">
                <Sword size={40} className="mx-auto text-gold" />
              </div>
              <p className="text-[15px] mb-1">Aucune campagne trouvee</p>
              <p className="text-[13px] text-text-secondary/60">
                Creez une nouvelle campagne pour commencer votre aventure.
              </p>
            </div>
          ) : (
            filteredCampaigns.map((campaign) => {
              const initial = (campaign.character_name || campaign.name || '?')[0].toUpperCase();
              const classLabel = campaign.character_class
                ? CLASS_LABELS[campaign.character_class as CharacterClass] || campaign.character_class
                : null;
              const isResuming = resumingSessionId === campaign.session_id;
              const isConfirmingDelete = confirmingDelete === campaign.session_id;
              const dateStr = campaign.updated_at || campaign.last_played || campaign.created_at;

              return (
                <div
                  key={campaign.session_id}
                  className="relative flex items-center gap-4 p-4 bg-bg-panel border border-border-primary rounded-[10px] mb-2.5 transition-all duration-200 cursor-pointer hover:bg-bg-card hover:border-border-gold"
                  onClick={() => !isResuming && !isConfirmingDelete && onPlayCampaign(campaign.session_id)}
                >
                  {isResuming && (
                    <div className="absolute inset-0 bg-bg-primary/60 flex items-center justify-center rounded-[10px] z-2">
                      <span className="text-gold text-[13px] font-semibold">Chargement...</span>
                    </div>
                  )}

                  {/* Portrait */}
                  <div className="w-12 h-12 rounded-[10px] bg-bg-hover flex items-center justify-center shrink-0">
                    <span className="text-lg font-bold text-text-secondary">{initial}</span>
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <p className="text-base font-bold text-text-primary mb-1.5 whitespace-nowrap overflow-hidden text-ellipsis">
                      {campaign.name}
                      {classLabel && (
                        <span className="font-normal text-text-secondary text-[13px] ml-2">
                          {campaign.character_name} &mdash; {classLabel}
                        </span>
                      )}
                    </p>
                    <div className="flex items-center gap-2 flex-wrap">
                      {campaign.turn !== undefined && campaign.turn > 0 && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-sm text-[11px] font-semibold bg-blue/20 text-blue tracking-[0.5px]">
                          Tour {campaign.turn}
                        </span>
                      )}
                      {campaign.location && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-sm text-[11px] font-semibold bg-green/20 text-green tracking-[0.5px]">
                          {campaign.location}
                        </span>
                      )}
                    </div>
                    {dateStr && (
                      <p className="text-xs text-text-secondary mt-1">
                        Derniere partie : {formatDate(dateStr)}
                      </p>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 shrink-0">
                    {isConfirmingDelete ? (
                      <div className="flex items-center gap-1.5 shrink-0">
                        <span className="text-xs text-red whitespace-nowrap">Supprimer ?</span>
                        <button
                          className="px-2.5 py-1 bg-red text-white border-none rounded-sm text-[11px] font-semibold cursor-pointer"
                          onClick={(e) => {
                            e.stopPropagation();
                            onDeleteCampaign?.(campaign.session_id);
                            setConfirmingDelete(null);
                          }}
                        >
                          Oui
                        </button>
                        <button
                          className="px-2.5 py-1 bg-transparent text-text-secondary border border-border-primary rounded-sm text-[11px] cursor-pointer"
                          onClick={(e) => {
                            e.stopPropagation();
                            setConfirmingDelete(null);
                          }}
                        >
                          Non
                        </button>
                      </div>
                    ) : (
                      <>
                        {onDeleteCampaign && (
                          <button
                            className="p-1.5 bg-transparent text-text-secondary border border-transparent rounded-md text-xs cursor-pointer transition-all duration-200 hover:bg-red/20 hover:text-red hover:border-red"
                            onClick={(e) => {
                              e.stopPropagation();
                              setConfirmingDelete(campaign.session_id);
                            }}
                            title="Supprimer"
                          >
                            <Trash2 size={14} />
                          </button>
                        )}
                        <button
                          className="px-5 py-2 bg-transparent text-gold border border-border-gold rounded-lg text-[13px] font-semibold cursor-pointer transition-all duration-200 shrink-0 hover:bg-gold/10 hover:border-gold hover:animate-[gold-btn-hover_1.5s_ease-in-out_infinite]"
                          onClick={(e) => {
                            e.stopPropagation();
                            onPlayCampaign(campaign.session_id);
                          }}
                        >
                          Jouer
                        </button>
                      </>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </section>

        {/* Footer */}
        <footer className="px-8 py-6 border-t border-border-primary text-center bg-bg-primary/60">
          <p className="text-xs text-text-secondary/50 mb-1">&copy; 2026 AMORA. Tous droits reserves.</p>
          <p className="text-xs text-text-secondary/50">Fait avec ❤ en local</p>
        </footer>
      </div>
    </div>
  );
}

export default HubScreen;
