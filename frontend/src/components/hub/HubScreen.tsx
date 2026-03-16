import { useState, useEffect, useMemo, type CSSProperties } from 'react';
import { CLASS_LABELS, type CharacterClass } from '../../types';

const THEME = {
  bgPrimary: '#0a0a0f',
  bgPanel: '#151520',
  bgCard: '#1a1a28',
  bgInput: '#1e1e2e',
  borderPrimary: '#2a2a3a',
  borderGold: '#8b7340',
  gold: '#c9a84c',
  textPrimary: '#e8e8f0',
  textSecondary: '#9898a8',
  red: '#e94560',
  green: '#53d769',
  blue: '#4a9eff',
} as const;

interface HubScreenProps {
  playerName?: string;
  campaigns: Array<{
    session_id: string;
    name: string;
    character_name?: string;
    character_class?: string;
    last_played?: string;
    player_count?: number;
    is_demo?: boolean;
  }>;
  onNewCampaign: () => void;
  onPlayCampaign: (sessionId: string) => void;
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

function GearIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 20 20"
      fill="none"
      stroke={THEME.textSecondary}
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="10" cy="10" r="3" />
      <path d="M10 1.5v2M10 16.5v2M3.4 3.4l1.4 1.4M15.2 15.2l1.4 1.4M1.5 10h2M16.5 10h2M3.4 16.6l1.4-1.4M15.2 4.8l1.4-1.4" />
    </svg>
  );
}

function PlusIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 18 18"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
    >
      <line x1="9" y1="3" x2="9" y2="15" />
      <line x1="3" y1="9" x2="15" y2="9" />
    </svg>
  );
}

function SwordIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      stroke={THEME.gold}
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M14 2L6 10M14 2l-1.5 5M14 2l-5 1.5M2 14l3-3M3 11l2 2" />
    </svg>
  );
}

const keyframesInjected = { current: false };
function injectKeyframes() {
  if (keyframesInjected.current) return;
  keyframesInjected.current = true;
  const style = document.createElement('style');
  style.textContent = `
    @keyframes hub-particle-float {
      0%, 100% { transform: translateY(0) translateX(0); opacity: var(--p-opacity); }
      25% { transform: translateY(-20px) translateX(10px); opacity: calc(var(--p-opacity) * 1.5); }
      50% { transform: translateY(-35px) translateX(-5px); opacity: var(--p-opacity); }
      75% { transform: translateY(-15px) translateX(-10px); opacity: calc(var(--p-opacity) * 0.6); }
    }
    @keyframes hub-pulse-glow {
      0%, 100% { box-shadow: 0 0 20px rgba(201, 168, 76, 0.1); }
      50% { box-shadow: 0 0 30px rgba(201, 168, 76, 0.2); }
    }
    @keyframes hub-gold-btn-hover {
      0%, 100% { box-shadow: 0 0 10px rgba(201, 168, 76, 0.3); }
      50% { box-shadow: 0 0 20px rgba(201, 168, 76, 0.5); }
    }
  `;
  document.head.appendChild(style);
}

type FilterOption = 'all' | 'recent' | 'demo';

function HubScreen({ playerName, campaigns, onNewCampaign, onPlayCampaign }: HubScreenProps) {
  const [filter, setFilter] = useState<FilterOption>('all');
  const [hoveredCard, setHoveredCard] = useState<string | null>(null);
  const [hoveredPlayBtn, setHoveredPlayBtn] = useState<string | null>(null);
  const [hoveredNewBtn, setHoveredNewBtn] = useState(false);
  const [hoveredSettingsBtn, setHoveredSettingsBtn] = useState(false);

  const particles = useMemo(() => generateParticles(40), []);

  useEffect(() => {
    injectKeyframes();
  }, []);

  const filteredCampaigns = useMemo(() => {
    switch (filter) {
      case 'demo':
        return campaigns.filter((c) => c.is_demo);
      case 'recent':
        return [...campaigns].sort((a, b) => {
          const da = a.last_played ? new Date(a.last_played).getTime() : 0;
          const db = b.last_played ? new Date(b.last_played).getTime() : 0;
          return db - da;
        });
      default:
        return campaigns;
    }
  }, [campaigns, filter]);

  const displayName = playerName || 'Aventurier';

  const styles = {
    root: {
      position: 'relative',
      minHeight: '100vh',
      background: THEME.bgPrimary,
      color: THEME.textPrimary,
      fontFamily: "'Segoe UI', system-ui, -apple-system, sans-serif",
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
    } satisfies CSSProperties,

    particlesContainer: {
      position: 'absolute',
      inset: 0,
      pointerEvents: 'none',
      zIndex: 0,
    } satisfies CSSProperties,

    particle: (p: Particle): CSSProperties => ({
      position: 'absolute',
      left: `${p.x}%`,
      top: `${p.y}%`,
      width: p.size,
      height: p.size,
      borderRadius: '50%',
      background: THEME.gold,
      animation: `hub-particle-float ${p.duration}s ease-in-out ${p.delay}s infinite`,
      '--p-opacity': p.opacity,
      opacity: p.opacity,
    } as CSSProperties),

    content: {
      position: 'relative',
      zIndex: 1,
      display: 'flex',
      flexDirection: 'column',
      minHeight: '100vh',
    } satisfies CSSProperties,

    header: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '16px 32px',
      borderBottom: `1px solid ${THEME.borderPrimary}`,
      background: 'rgba(10, 10, 15, 0.8)',
      backdropFilter: 'blur(10px)',
    } satisfies CSSProperties,

    headerTitle: {
      fontSize: 16,
      fontWeight: 700,
      color: THEME.gold,
      textTransform: 'uppercase',
      letterSpacing: '3px',
      margin: 0,
    } satisfies CSSProperties,

    settingsBtn: {
      background: hoveredSettingsBtn ? THEME.bgCard : 'transparent',
      border: `1px solid ${hoveredSettingsBtn ? THEME.borderGold : THEME.borderPrimary}`,
      borderRadius: 8,
      padding: '8px',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      transition: 'all 0.2s ease',
    } satisfies CSSProperties,

    welcomeSection: {
      textAlign: 'center',
      padding: '48px 32px 24px',
    } satisfies CSSProperties,

    welcomeTitle: {
      fontSize: 28,
      fontWeight: 700,
      color: THEME.gold,
      margin: '0 0 12px',
      textShadow: '0 0 30px rgba(201, 168, 76, 0.3)',
    } satisfies CSSProperties,

    welcomeSubtitle: {
      fontSize: 15,
      color: THEME.textSecondary,
      margin: 0,
      maxWidth: 500,
      marginLeft: 'auto',
      marginRight: 'auto',
      lineHeight: 1.6,
    } satisfies CSSProperties,

    actionBar: {
      display: 'flex',
      justifyContent: 'center',
      padding: '24px 32px 32px',
    } satisfies CSSProperties,

    newCampaignBtn: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 10,
      padding: '14px 32px',
      background: hoveredNewBtn
        ? `linear-gradient(135deg, ${THEME.gold}, #a8883a)`
        : `linear-gradient(135deg, ${THEME.gold}, #b8953e)`,
      color: '#0a0a0f',
      border: 'none',
      borderRadius: 10,
      fontSize: 15,
      fontWeight: 700,
      cursor: 'pointer',
      transition: 'all 0.25s ease',
      textTransform: 'uppercase',
      letterSpacing: '1px',
      animation: 'hub-pulse-glow 3s ease-in-out infinite',
      transform: hoveredNewBtn ? 'translateY(-2px)' : 'none',
    } satisfies CSSProperties,

    campaignsSection: {
      flex: 1,
      padding: '0 32px 32px',
      maxWidth: 800,
      margin: '0 auto',
      width: '100%',
      boxSizing: 'border-box',
    } satisfies CSSProperties,

    campaignsHeader: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      marginBottom: 16,
    } satisfies CSSProperties,

    campaignsTitle: {
      fontSize: 18,
      fontWeight: 600,
      color: THEME.textPrimary,
      margin: 0,
    } satisfies CSSProperties,

    filterSelect: {
      background: THEME.bgInput,
      color: THEME.textSecondary,
      border: `1px solid ${THEME.borderPrimary}`,
      borderRadius: 6,
      padding: '6px 12px',
      fontSize: 13,
      cursor: 'pointer',
      outline: 'none',
    } satisfies CSSProperties,

    campaignCard: (isHovered: boolean): CSSProperties => ({
      display: 'flex',
      alignItems: 'center',
      gap: 16,
      padding: '16px',
      background: isHovered ? THEME.bgCard : THEME.bgPanel,
      border: `1px solid ${isHovered ? THEME.borderGold : THEME.borderPrimary}`,
      borderRadius: 10,
      marginBottom: 10,
      transition: 'all 0.2s ease',
      cursor: 'pointer',
    }),

    portrait: {
      width: 48,
      height: 48,
      borderRadius: 10,
      background: '#252535',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      flexShrink: 0,
    } satisfies CSSProperties,

    portraitText: {
      fontSize: 18,
      fontWeight: 700,
      color: THEME.textSecondary,
    } satisfies CSSProperties,

    cardInfo: {
      flex: 1,
      minWidth: 0,
    } satisfies CSSProperties,

    cardName: {
      fontSize: 16,
      fontWeight: 700,
      color: THEME.textPrimary,
      margin: '0 0 6px',
      whiteSpace: 'nowrap',
      overflow: 'hidden',
      textOverflow: 'ellipsis',
    } satisfies CSSProperties,

    cardMeta: {
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      flexWrap: 'wrap',
    } satisfies CSSProperties,

    badge: (color: string): CSSProperties => ({
      display: 'inline-flex',
      alignItems: 'center',
      padding: '2px 8px',
      borderRadius: 4,
      fontSize: 11,
      fontWeight: 600,
      background: `${color}20`,
      color,
      letterSpacing: '0.5px',
    }),

    cardDate: {
      fontSize: 12,
      color: THEME.textSecondary,
      marginTop: 4,
    } satisfies CSSProperties,

    playBtn: (isHovered: boolean): CSSProperties => ({
      padding: '8px 20px',
      background: isHovered ? `${THEME.gold}18` : 'transparent',
      color: THEME.gold,
      border: `1px solid ${isHovered ? THEME.gold : THEME.borderGold}`,
      borderRadius: 8,
      fontSize: 13,
      fontWeight: 600,
      cursor: 'pointer',
      transition: 'all 0.2s ease',
      flexShrink: 0,
      animation: isHovered ? 'hub-gold-btn-hover 1.5s ease-in-out infinite' : 'none',
    }),

    emptyState: {
      textAlign: 'center',
      padding: '48px 24px',
      color: THEME.textSecondary,
    } satisfies CSSProperties,

    emptyIcon: {
      fontSize: 40,
      marginBottom: 16,
      opacity: 0.4,
    } satisfies CSSProperties,

    emptyText: {
      fontSize: 15,
      margin: '0 0 4px',
    } satisfies CSSProperties,

    emptyHint: {
      fontSize: 13,
      color: `${THEME.textSecondary}99`,
      margin: 0,
    } satisfies CSSProperties,

    footer: {
      padding: '24px 32px',
      borderTop: `1px solid ${THEME.borderPrimary}`,
      textAlign: 'center',
      background: 'rgba(10, 10, 15, 0.6)',
    } satisfies CSSProperties,

    footerText: {
      fontSize: 12,
      color: `${THEME.textSecondary}80`,
      margin: '0 0 4px',
    } satisfies CSSProperties,

    footerHeart: {
      fontSize: 12,
      color: `${THEME.textSecondary}80`,
      margin: 0,
    } satisfies CSSProperties,
  };

  return (
    <div style={styles.root}>
      <div style={styles.particlesContainer}>
        {particles.map((p) => (
          <div key={p.id} style={styles.particle(p)} />
        ))}
      </div>

      <div style={styles.content}>
        <header style={styles.header}>
          <h1 style={styles.headerTitle}>Taverne du Vieux Greg</h1>
          <button
            style={styles.settingsBtn}
            title="Parametres"
            aria-label="Parametres"
            onMouseEnter={() => setHoveredSettingsBtn(true)}
            onMouseLeave={() => setHoveredSettingsBtn(false)}
          >
            <GearIcon />
          </button>
        </header>

        <section style={styles.welcomeSection}>
          <h2 style={styles.welcomeTitle}>Bienvenue, {displayName}</h2>
          <p style={styles.welcomeSubtitle}>
            Vos quetes vous attendent. Creez une nouvelle aventure ou continuez votre voyage.
          </p>
        </section>

        <div style={styles.actionBar}>
          <button
            style={styles.newCampaignBtn}
            onClick={onNewCampaign}
            onMouseEnter={() => setHoveredNewBtn(true)}
            onMouseLeave={() => setHoveredNewBtn(false)}
          >
            <PlusIcon />
            Nouvelle Campagne
          </button>
        </div>

        <section style={styles.campaignsSection}>
          <div style={styles.campaignsHeader}>
            <h3 style={styles.campaignsTitle}>Vos Campagnes</h3>
            <select
              style={styles.filterSelect}
              value={filter}
              onChange={(e) => setFilter(e.target.value as FilterOption)}
            >
              <option value="all">All Campaigns</option>
              <option value="recent">Recent</option>
              <option value="demo">Demo Only</option>
            </select>
          </div>

          {filteredCampaigns.length === 0 ? (
            <div style={styles.emptyState}>
              <div style={styles.emptyIcon}>
                <SwordIcon />
              </div>
              <p style={styles.emptyText}>Aucune campagne trouvee</p>
              <p style={styles.emptyHint}>
                Creez une nouvelle campagne pour commencer votre aventure.
              </p>
            </div>
          ) : (
            filteredCampaigns.map((campaign) => {
              const initial = (campaign.character_name || campaign.name || '?')[0].toUpperCase();
              const classLabel = campaign.character_class
                ? CLASS_LABELS[campaign.character_class as CharacterClass] || campaign.character_class
                : null;

              return (
                <div
                  key={campaign.session_id}
                  style={styles.campaignCard(hoveredCard === campaign.session_id)}
                  onMouseEnter={() => setHoveredCard(campaign.session_id)}
                  onMouseLeave={() => setHoveredCard(null)}
                  onClick={() => onPlayCampaign(campaign.session_id)}
                >
                  <div style={styles.portrait}>
                    <span style={styles.portraitText}>{initial}</span>
                  </div>

                  <div style={styles.cardInfo}>
                    <p style={styles.cardName}>
                      {campaign.name}
                      {classLabel && (
                        <span style={{ fontWeight: 400, color: THEME.textSecondary, fontSize: 13, marginLeft: 8 }}>
                          {campaign.character_name} &mdash; {classLabel}
                        </span>
                      )}
                    </p>
                    <div style={styles.cardMeta}>
                      {campaign.is_demo && (
                        <span style={styles.badge(THEME.blue)}>Demo</span>
                      )}
                      <span style={styles.badge(THEME.green)}>
                        {campaign.player_count ?? 1}/6 joueurs
                      </span>
                    </div>
                    {campaign.last_played && (
                      <p style={styles.cardDate}>
                        Derniere partie : {formatDate(campaign.last_played)}
                      </p>
                    )}
                  </div>

                  <button
                    style={styles.playBtn(hoveredPlayBtn === campaign.session_id)}
                    onClick={(e) => {
                      e.stopPropagation();
                      onPlayCampaign(campaign.session_id);
                    }}
                    onMouseEnter={() => setHoveredPlayBtn(campaign.session_id)}
                    onMouseLeave={() => setHoveredPlayBtn(null)}
                  >
                    Jouer
                  </button>
                </div>
              );
            })
          )}
        </section>

        <footer style={styles.footer}>
          <p style={styles.footerText}>&copy; 2026 Taverne du Vieux Greg. Tous droits reserves.</p>
          <p style={styles.footerHeart}>Fait avec ❤ en local</p>
        </footer>
      </div>
    </div>
  );
}

export default HubScreen;
