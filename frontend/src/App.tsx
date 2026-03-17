import { useState, useCallback, useEffect, useRef } from 'react';
import '@/styles/theme.css';
import HubScreen from '@/components/hub/HubScreen.tsx';
import NewCampaignModal from '@/components/hub/NewCampaignModal.tsx';
import GameScreen from '@/components/game/GameScreen.tsx';
import { api } from '@/services/api.ts';
import type { Character } from '@/types/character.ts';
import type { Campaign } from '@/types/game.ts';
import { check } from '@tauri-apps/plugin-updater';
import { relaunch } from '@tauri-apps/plugin-process';

interface ActiveGame {
  sessionId: string;
  characterId: string;
  character: Character;
  isResumed: boolean;
}

function LoadingScreen({ status, error, onRetry, updateProgress }: {
  status: string;
  error?: boolean;
  onRetry?: () => void;
  updateProgress?: number;
}) {
  return (
    <div className="flex flex-col items-center justify-center h-screen bg-bg-primary text-text-primary font-[Georgia,serif]">
      <h1 className="text-[72px] font-bold text-gold mb-2 tracking-[8px]">
        AMORA
      </h1>
      <p className="text-sm text-text-dim mb-12 tracking-[4px] uppercase">
        AI-Powered RPG Engine
      </p>

      {!error && (
        <div className="w-[300px] h-1 bg-[#1a1a2a] rounded-sm overflow-hidden mb-6">
          {updateProgress !== undefined ? (
            <div
              className="h-full bg-gold rounded-sm transition-all duration-300"
              style={{ width: `${updateProgress}%` }}
            />
          ) : (
            <div className="h-full bg-[linear-gradient(90deg,var(--color-gold),var(--color-red),var(--color-gold))] bg-[length:200%_100%] animate-[shimmer_2s_ease-in-out_infinite] rounded-sm" />
          )}
        </div>
      )}

      <p className={`text-[13px] ${error ? 'text-red' : 'text-text-secondary'}`}>
        {status}
      </p>

      {error && onRetry && (
        <button
          className="mt-6 px-6 py-2.5 bg-transparent text-gold border border-border-gold rounded-lg text-[13px] font-semibold cursor-pointer transition-all duration-200 hover:bg-gold/10"
          onClick={onRetry}
        >
          Reessayer
        </button>
      )}
    </div>
  );
}

export default function App() {
  const [screen, setScreen] = useState<'loading' | 'hub' | 'game'>('loading');
  const [loadingStatus, setLoadingStatus] = useState('Demarrage...');
  const [loadingError, setLoadingError] = useState(false);
  const [bootAttempt, setBootAttempt] = useState(0);
  const [showNewCampaign, setShowNewCampaign] = useState(false);
  const [activeGame, setActiveGame] = useState<ActiveGame | null>(null);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [isLoadingCampaigns, setIsLoadingCampaigns] = useState(true);
  const [isResumingSession, setIsResumingSession] = useState<string | null>(null);
  const [updateProgress, setUpdateProgress] = useState<number | undefined>(undefined);
  const updateCheckedRef = useRef(false);

  useEffect(() => {
    if (screen !== 'loading') return;

    let cancelled = false;

    const boot = async () => {
      setLoadingError(false);

      if (!updateCheckedRef.current) {
        updateCheckedRef.current = true;
        setLoadingStatus('Recherche de mises a jour...');
        try {
          const update = await check();
          if (update) {
            setLoadingStatus(`Mise a jour v${update.version} trouvee. Telechargement...`);
            let downloaded = 0;
            let contentLength = 0;
            await update.downloadAndInstall((event) => {
              switch (event.event) {
                case 'Started':
                  contentLength = event.data.contentLength ?? 0;
                  break;
                case 'Progress':
                  downloaded += event.data.chunkLength;
                  if (contentLength > 0) {
                    setUpdateProgress(Math.round((downloaded / contentLength) * 100));
                  }
                  break;
                case 'Finished':
                  setUpdateProgress(100);
                  break;
              }
            });
            setLoadingStatus('Mise a jour installee. Redemarrage...');
            await relaunch();
            return;
          }
        } catch {
          // Update check failed — continue boot normally
        }
        setUpdateProgress(undefined);
      }

      setLoadingStatus('Connexion au serveur...');
      let serverReady = false;
      for (let i = 0; i < 30; i++) {
        if (cancelled) return;
        try {
          await api.game.listSessions();
          serverReady = true;
          break;
        } catch {
          await new Promise(r => setTimeout(r, 1000));
        }
      }

      if (!serverReady) {
        if (!cancelled) {
          setLoadingStatus('Impossible de se connecter au serveur.');
          setLoadingError(true);
        }
        return;
      }

      setLoadingStatus('Chargement du modele IA...');
      let aiReady = false;
      for (let i = 0; i < 120; i++) {
        if (cancelled) return;
        try {
          const health = await api.llm.health();
          if (health.healthy) {
            aiReady = true;
            break;
          }
        } catch { /* not ready */ }
        await new Promise(r => setTimeout(r, 2000));
      }

      if (!aiReady) {
        if (!cancelled) {
          setLoadingStatus('Le modele IA n\'a pas pu etre charge. Verifiez que le serveur est demarre.');
          setLoadingError(true);
        }
        return;
      }

      if (cancelled) return;
      setLoadingStatus('Chargement des campagnes...');
      try {
        const sessions = await api.game.listSessions();
        setCampaigns(sessions);
      } catch {
        setCampaigns([]);
      }
      setIsLoadingCampaigns(false);

      if (!cancelled) {
        setScreen('hub');
      }
    };

    boot();
    return () => { cancelled = true; };
  }, [screen, bootAttempt]);

  const loadCampaigns = useCallback(async () => {
    try {
      const sessions = await api.game.listSessions();
      setCampaigns(sessions);
    } catch {
      setCampaigns([]);
    } finally {
      setIsLoadingCampaigns(false);
    }
  }, []);

  const handleNewCampaign = useCallback(async (data: { sessionName: string; charName: string; charClass: string }) => {
    const session = await api.game.createSession(data.sessionName);
    const char = await api.character.create({
      name: data.charName,
      character_class: data.charClass,
      player_id: 'player_1',
    });

    setCampaigns(prev => [
      {
        session_id: session.session_id,
        name: data.sessionName,
        character_name: data.charName,
        character_class: data.charClass,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      ...prev,
    ]);

    setActiveGame({
      sessionId: session.session_id,
      characterId: char.id,
      character: char,
      isResumed: false,
    });
    setShowNewCampaign(false);
    setScreen('game');
  }, []);

  const handlePlayCampaign = useCallback(async (sessionId: string) => {
    setIsResumingSession(sessionId);
    try {
      const state = await api.game.getSession(sessionId);

      let character: Character | null = null;

      if (state.active_character_id) {
        try {
          character = await api.character.get(state.active_character_id);
        } catch {
          character = null;
        }
      }

      if (!character) {
        try {
          const charList = await api.character.list();
          if (charList.characters.length > 0) {
            character = charList.characters[0];
          }
        } catch {
          character = null;
        }
      }

      if (!character) {
        setIsResumingSession(null);
        return;
      }

      setActiveGame({
        sessionId,
        characterId: character.id,
        character,
        isResumed: true,
      });
      setScreen('game');
    } catch {
      // session might be corrupted or deleted
    } finally {
      setIsResumingSession(null);
    }
  }, []);

  const handleDeleteCampaign = useCallback(async (sessionId: string) => {
    try {
      await api.game.deleteSession(sessionId);
      setCampaigns(prev => prev.filter(c => c.session_id !== sessionId));
    } catch {
      // ignore delete errors
    }
  }, []);

  const handleBackToHub = useCallback(() => {
    setScreen('hub');
    setActiveGame(null);
    loadCampaigns();
  }, [loadCampaigns]);

  const handleRetry = useCallback(() => {
    setLoadingError(false);
    setLoadingStatus('Demarrage...');
    setBootAttempt(prev => prev + 1);
  }, []);

  if (screen === 'loading') {
    return <LoadingScreen status={loadingStatus} error={loadingError} onRetry={handleRetry} updateProgress={updateProgress} />;
  }

  if (screen === 'game' && activeGame) {
    return (
      <GameScreen
        sessionId={activeGame.sessionId}
        characterId={activeGame.characterId}
        initialCharacter={activeGame.character}
        onBackToHub={handleBackToHub}
        isResumed={activeGame.isResumed}
      />
    );
  }

  return (
    <>
      <HubScreen
        campaigns={campaigns}
        isLoading={isLoadingCampaigns}
        resumingSessionId={isResumingSession}
        onNewCampaign={() => setShowNewCampaign(true)}
        onPlayCampaign={handlePlayCampaign}
        onDeleteCampaign={handleDeleteCampaign}
      />
      <NewCampaignModal
        isOpen={showNewCampaign}
        onClose={() => setShowNewCampaign(false)}
        onSubmit={handleNewCampaign}
      />
    </>
  );
}
