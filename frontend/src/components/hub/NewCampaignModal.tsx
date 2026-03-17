import { useState, useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { CLASS_LABELS, type CharacterClass } from '../../types';

const CLASS_OPTIONS: Array<{ value: CharacterClass; label: string }> = (
  Object.entries(CLASS_LABELS) as Array<[CharacterClass, string]>
).map(([value, label]) => ({ value, label }));

interface NewCampaignModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: { sessionName: string; charName: string; charClass: string }) => Promise<void>;
}

type ModalState = 'idle' | 'loading' | 'error';

function NewCampaignModal({ isOpen, onClose, onSubmit }: NewCampaignModalProps) {
  const [sessionName, setSessionName] = useState('Nouvelle Aventure');
  const [charName, setCharName] = useState('');
  const [charClass, setCharClass] = useState<string>(CLASS_OPTIONS[0].value);
  const [state, setState] = useState<ModalState>('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const charNameRef = useRef<HTMLInputElement>(null);
  const backdropMouseDownRef = useRef(false);

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

  return (
    <div
      className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/75 backdrop-blur-[4px] animate-[modal-fade-in_0.2s_ease-out]"
      onMouseDown={(e) => {
        backdropMouseDownRef.current = e.target === e.currentTarget;
      }}
      onMouseUp={(e) => {
        if (backdropMouseDownRef.current && e.target === e.currentTarget && state !== 'loading') {
          onClose();
        }
        backdropMouseDownRef.current = false;
      }}
    >
      <div
        className="relative bg-bg-panel border border-border-gold rounded-[14px] p-8 w-full max-w-[460px] mx-4 shadow-[0_0_40px_rgba(201,168,76,0.1),0_20px_60px_rgba(0,0,0,0.5)] animate-[modal-slide-up_0.25s_ease-out]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close button */}
        <button
          className="absolute top-4 right-4 bg-transparent border border-transparent rounded-lg p-1.5 cursor-pointer text-text-secondary flex items-center justify-center transition-all duration-200 hover:bg-bg-card hover:border-border-primary"
          onClick={onClose}
          aria-label="Fermer"
          disabled={state === 'loading'}
        >
          <X size={18} />
        </button>

        <h2 className="text-[22px] font-bold text-gold mb-6 text-center">Nouvelle Aventure</h2>

        {state === 'loading' ? (
          <div className="flex flex-col items-center py-8 gap-4">
            <div className="w-9 h-9 border-3 border-border-primary border-t-gold rounded-full animate-[spinner_0.8s_linear_infinite]" />
            <p className="text-[15px] text-gold font-semibold">Preparation du monde...</p>
          </div>
        ) : (
          <>
            {/* Session name */}
            <div className="mb-4.5">
              <label className="block text-[13px] font-semibold text-text-secondary mb-1.5 uppercase tracking-[0.5px]">
                Nom de la session
              </label>
              <input
                className="w-full px-3.5 py-2.5 bg-bg-input border border-border-primary rounded-lg text-text-primary text-sm outline-none transition-colors duration-200 focus:border-border-gold"
                type="text"
                value={sessionName}
                onChange={(e) => setSessionName(e.target.value)}
                placeholder="Nouvelle Aventure"
              />
            </div>

            {/* Character name */}
            <div className="mb-4.5">
              <label className="block text-[13px] font-semibold text-text-secondary mb-1.5 uppercase tracking-[0.5px]">
                Nom du personnage<span className="text-red ml-0.5">*</span>
              </label>
              <input
                ref={charNameRef}
                className="w-full px-3.5 py-2.5 bg-bg-input border border-border-primary rounded-lg text-text-primary text-sm outline-none transition-colors duration-200 focus:border-border-gold"
                type="text"
                value={charName}
                onChange={(e) => setCharName(e.target.value)}
                placeholder="Entrez le nom de votre heros"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSubmit();
                }}
              />
            </div>

            {/* Class select */}
            <div className="mb-4.5">
              <label className="block text-[13px] font-semibold text-text-secondary mb-1.5 uppercase tracking-[0.5px]">
                Classe
              </label>
              <select
                className="w-full px-3.5 py-2.5 bg-bg-input border border-border-primary rounded-lg text-text-primary text-sm outline-none cursor-pointer appearance-none bg-no-repeat bg-[right_14px_center] bg-[url('data:image/svg+xml,%3Csvg%20width%3D%2712%27%20height%3D%278%27%20viewBox%3D%270%200%2012%208%27%20fill%3D%27none%27%20xmlns%3D%27http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%27%3E%3Cpath%20d%3D%27M1%201.5L6%206.5L11%201.5%27%20stroke%3D%27%239898a8%27%20stroke-width%3D%271.5%27%20stroke-linecap%3D%27round%27%20stroke-linejoin%3D%27round%27%2F%3E%3C%2Fsvg%3E')]"
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

            {/* Error */}
            {state === 'error' && (
              <div className="text-center pt-4">
                <p className="text-[13px] text-red mb-3.5 px-3.5 py-2.5 bg-red/[0.07] border border-red/20 rounded-lg">
                  {errorMessage}
                </p>
                <button
                  className="px-6 py-2.5 bg-transparent text-red border border-red/60 rounded-lg text-[13px] font-semibold cursor-pointer transition-all duration-200 hover:bg-red/20 hover:border-red"
                  onClick={() => handleSubmit()}
                >
                  Reessayer
                </button>
              </div>
            )}

            {/* Submit */}
            <button
              className={`w-full py-3.5 px-6 rounded-[10px] text-[15px] font-bold uppercase tracking-[1px] transition-all duration-250 mt-2 ${
                canSubmit
                  ? 'bg-gradient-to-br from-gold to-[#b8953e] text-bg-primary cursor-pointer hover:to-[#a8883a] hover:-translate-y-px hover:shadow-[0_0_20px_rgba(201,168,76,0.3)]'
                  : 'bg-bg-card text-text-secondary border border-border-primary cursor-not-allowed'
              }`}
              onClick={handleSubmit}
              disabled={!canSubmit}
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
