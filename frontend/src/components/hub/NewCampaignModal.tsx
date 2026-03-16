import { useState, useEffect, useRef, type CSSProperties } from 'react';
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

const CLASS_OPTIONS: Array<{ value: CharacterClass; label: string }> = (
  Object.entries(CLASS_LABELS) as Array<[CharacterClass, string]>
).map(([value, label]) => ({ value, label }));

interface NewCampaignModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: { sessionName: string; charName: string; charClass: string }) => Promise<void>;
}

type ModalState = 'idle' | 'loading' | 'error';

const keyframesInjected = { current: false };
function injectKeyframes() {
  if (keyframesInjected.current) return;
  keyframesInjected.current = true;
  const style = document.createElement('style');
  style.textContent = `
    @keyframes modal-fade-in {
      from { opacity: 0; }
      to { opacity: 1; }
    }
    @keyframes modal-slide-up {
      from { opacity: 0; transform: translateY(30px) scale(0.97); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }
    @keyframes modal-spinner {
      to { transform: rotate(360deg); }
    }
  `;
  document.head.appendChild(style);
}

function CloseIcon() {
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
      <line x1="4" y1="4" x2="14" y2="14" />
      <line x1="14" y1="4" x2="4" y2="14" />
    </svg>
  );
}

function NewCampaignModal({ isOpen, onClose, onSubmit }: NewCampaignModalProps) {
  const [sessionName, setSessionName] = useState('Nouvelle Aventure');
  const [charName, setCharName] = useState('');
  const [charClass, setCharClass] = useState<string>(CLASS_OPTIONS[0].value);
  const [state, setState] = useState<ModalState>('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const [hoveredSubmit, setHoveredSubmit] = useState(false);
  const [hoveredClose, setHoveredClose] = useState(false);
  const [hoveredRetry, setHoveredRetry] = useState(false);
  const charNameRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    injectKeyframes();
  }, []);

  useEffect(() => {
    if (isOpen) {
      setState('idle');
      setErrorMessage('');
      setSessionName('Nouvelle Aventure');
      setCharName('');
      setCharClass(CLASS_OPTIONS[0].value);
      setTimeout(() => charNameRef.current?.focus(), 100);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && state !== 'loading') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose, state]);

  if (!isOpen) return null;

  const canSubmit = charName.trim().length > 0 && state !== 'loading';

  async function handleSubmit() {
    if (!canSubmit) return;
    setState('loading');
    setErrorMessage('');
    try {
      await onSubmit({
        sessionName: sessionName.trim() || 'Nouvelle Aventure',
        charName: charName.trim(),
        charClass,
      });
    } catch (err) {
      setState('error');
      setErrorMessage(
        err instanceof Error ? err.message : 'Une erreur est survenue lors de la creation.'
      );
    }
  }

  function handleRetry() {
    handleSubmit();
  }

  const styles = {
    overlay: {
      position: 'fixed',
      inset: 0,
      zIndex: 1000,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'rgba(0, 0, 0, 0.75)',
      backdropFilter: 'blur(4px)',
      animation: 'modal-fade-in 0.2s ease-out',
    } satisfies CSSProperties,

    card: {
      position: 'relative',
      background: THEME.bgPanel,
      border: `1px solid ${THEME.borderGold}`,
      borderRadius: 14,
      padding: '32px',
      width: '100%',
      maxWidth: 460,
      margin: '0 16px',
      boxShadow: `0 0 40px rgba(201, 168, 76, 0.1), 0 20px 60px rgba(0, 0, 0, 0.5)`,
      animation: 'modal-slide-up 0.25s ease-out',
    } satisfies CSSProperties,

    closeBtn: {
      position: 'absolute',
      top: 16,
      right: 16,
      background: hoveredClose ? THEME.bgCard : 'transparent',
      border: `1px solid ${hoveredClose ? THEME.borderPrimary : 'transparent'}`,
      borderRadius: 8,
      padding: 6,
      cursor: 'pointer',
      color: THEME.textSecondary,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      transition: 'all 0.2s ease',
    } satisfies CSSProperties,

    title: {
      fontSize: 22,
      fontWeight: 700,
      color: THEME.gold,
      margin: '0 0 24px',
      textAlign: 'center',
    } satisfies CSSProperties,

    fieldGroup: {
      marginBottom: 18,
    } satisfies CSSProperties,

    label: {
      display: 'block',
      fontSize: 13,
      fontWeight: 600,
      color: THEME.textSecondary,
      marginBottom: 6,
      textTransform: 'uppercase',
      letterSpacing: '0.5px',
    } satisfies CSSProperties,

    input: {
      width: '100%',
      padding: '10px 14px',
      background: THEME.bgInput,
      border: `1px solid ${THEME.borderPrimary}`,
      borderRadius: 8,
      color: THEME.textPrimary,
      fontSize: 14,
      outline: 'none',
      transition: 'border-color 0.2s ease',
      boxSizing: 'border-box',
    } satisfies CSSProperties,

    select: {
      width: '100%',
      padding: '10px 14px',
      background: THEME.bgInput,
      border: `1px solid ${THEME.borderPrimary}`,
      borderRadius: 8,
      color: THEME.textPrimary,
      fontSize: 14,
      outline: 'none',
      cursor: 'pointer',
      boxSizing: 'border-box',
      appearance: 'none',
      backgroundImage: `url("data:image/svg+xml,%3Csvg width='12' height='8' viewBox='0 0 12 8' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1.5L6 6.5L11 1.5' stroke='%239898a8' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")`,
      backgroundRepeat: 'no-repeat',
      backgroundPosition: 'right 14px center',
    } satisfies CSSProperties,

    required: {
      color: THEME.red,
      marginLeft: 2,
    } satisfies CSSProperties,

    submitBtn: {
      width: '100%',
      padding: '14px 24px',
      background: canSubmit
        ? hoveredSubmit
          ? `linear-gradient(135deg, ${THEME.gold}, #a8883a)`
          : `linear-gradient(135deg, ${THEME.gold}, #b8953e)`
        : THEME.bgCard,
      color: canSubmit ? '#0a0a0f' : THEME.textSecondary,
      border: canSubmit ? 'none' : `1px solid ${THEME.borderPrimary}`,
      borderRadius: 10,
      fontSize: 15,
      fontWeight: 700,
      cursor: canSubmit ? 'pointer' : 'not-allowed',
      textTransform: 'uppercase',
      letterSpacing: '1px',
      transition: 'all 0.25s ease',
      marginTop: 8,
      transform: canSubmit && hoveredSubmit ? 'translateY(-1px)' : 'none',
      boxShadow: canSubmit && hoveredSubmit ? `0 0 20px rgba(201, 168, 76, 0.3)` : 'none',
    } satisfies CSSProperties,

    loadingContainer: {
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      padding: '32px 0',
      gap: 16,
    } satisfies CSSProperties,

    spinner: {
      width: 36,
      height: 36,
      border: `3px solid ${THEME.borderPrimary}`,
      borderTopColor: THEME.gold,
      borderRadius: '50%',
      animation: 'modal-spinner 0.8s linear infinite',
    } satisfies CSSProperties,

    loadingText: {
      fontSize: 15,
      color: THEME.gold,
      margin: 0,
      fontWeight: 600,
    } satisfies CSSProperties,

    errorContainer: {
      textAlign: 'center',
      padding: '16px 0 0',
    } satisfies CSSProperties,

    errorMessage: {
      fontSize: 13,
      color: THEME.red,
      margin: '0 0 14px',
      padding: '10px 14px',
      background: `${THEME.red}12`,
      border: `1px solid ${THEME.red}30`,
      borderRadius: 8,
    } satisfies CSSProperties,

    retryBtn: {
      padding: '10px 24px',
      background: hoveredRetry ? `${THEME.red}20` : 'transparent',
      color: THEME.red,
      border: `1px solid ${hoveredRetry ? THEME.red : `${THEME.red}60`}`,
      borderRadius: 8,
      fontSize: 13,
      fontWeight: 600,
      cursor: 'pointer',
      transition: 'all 0.2s ease',
    } satisfies CSSProperties,
  };

  return (
    <div style={styles.overlay} onClick={state !== 'loading' ? onClose : undefined}>
      <div style={styles.card} onClick={(e) => e.stopPropagation()}>
        <button
          style={styles.closeBtn}
          onClick={onClose}
          aria-label="Fermer"
          disabled={state === 'loading'}
          onMouseEnter={() => setHoveredClose(true)}
          onMouseLeave={() => setHoveredClose(false)}
        >
          <CloseIcon />
        </button>

        <h2 style={styles.title}>Nouvelle Aventure</h2>

        {state === 'loading' ? (
          <div style={styles.loadingContainer}>
            <div style={styles.spinner} />
            <p style={styles.loadingText}>Preparation du monde...</p>
          </div>
        ) : (
          <>
            <div style={styles.fieldGroup}>
              <label style={styles.label}>Nom de la session</label>
              <input
                style={styles.input}
                type="text"
                value={sessionName}
                onChange={(e) => setSessionName(e.target.value)}
                placeholder="Nouvelle Aventure"
                onFocus={(e) => {
                  (e.target as HTMLInputElement).style.borderColor = THEME.borderGold;
                }}
                onBlur={(e) => {
                  (e.target as HTMLInputElement).style.borderColor = THEME.borderPrimary;
                }}
              />
            </div>

            <div style={styles.fieldGroup}>
              <label style={styles.label}>
                Nom du personnage<span style={styles.required}>*</span>
              </label>
              <input
                ref={charNameRef}
                style={styles.input}
                type="text"
                value={charName}
                onChange={(e) => setCharName(e.target.value)}
                placeholder="Entrez le nom de votre heros"
                onFocus={(e) => {
                  (e.target as HTMLInputElement).style.borderColor = THEME.borderGold;
                }}
                onBlur={(e) => {
                  (e.target as HTMLInputElement).style.borderColor = THEME.borderPrimary;
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSubmit();
                }}
              />
            </div>

            <div style={styles.fieldGroup}>
              <label style={styles.label}>Classe</label>
              <select
                style={styles.select}
                value={charClass}
                onChange={(e) => setCharClass(e.target.value)}
              >
                {CLASS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            {state === 'error' && (
              <div style={styles.errorContainer}>
                <p style={styles.errorMessage}>{errorMessage}</p>
                <button
                  style={styles.retryBtn}
                  onClick={handleRetry}
                  onMouseEnter={() => setHoveredRetry(true)}
                  onMouseLeave={() => setHoveredRetry(false)}
                >
                  Reessayer
                </button>
              </div>
            )}

            <button
              style={styles.submitBtn}
              onClick={handleSubmit}
              disabled={!canSubmit}
              onMouseEnter={() => setHoveredSubmit(true)}
              onMouseLeave={() => setHoveredSubmit(false)}
            >
              Commencer l'aventure
            </button>
          </>
        )}
      </div>
    </div>
  );
}

export default NewCampaignModal;
