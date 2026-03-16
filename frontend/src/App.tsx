import { useState, useCallback } from 'react';
import '@/styles/theme.css';
import HubScreen from '@/components/hub/HubScreen.tsx';
import NewCampaignModal from '@/components/hub/NewCampaignModal.tsx';
import GameScreen from '@/components/game/GameScreen.tsx';
import { api } from '@/services/api.ts';
import type { Character } from '@/types/character.ts';

interface ActiveGame {
  sessionId: string;
  characterId: string;
  character: Character;
}

interface CampaignEntry {
  session_id: string;
  name: string;
  character_name?: string;
  character_class?: string;
  last_played?: string;
  player_count?: number;
  is_demo?: boolean;
}

export default function App() {
  const [screen, setScreen] = useState<'hub' | 'game'>('hub');
  const [showNewCampaign, setShowNewCampaign] = useState(false);
  const [activeGame, setActiveGame] = useState<ActiveGame | null>(null);
  const [campaigns, setCampaigns] = useState<CampaignEntry[]>([]);

  const handleNewCampaign = useCallback(async (data: { sessionName: string; charName: string; charClass: string }) => {
    const session = await api.game.createSession(data.sessionName);
    const char = await api.character.create({
      name: data.charName,
      character_class: data.charClass,
      player_id: 'player_1',
    });

    setCampaigns(prev => [
      ...prev,
      {
        session_id: session.session_id,
        name: data.sessionName,
        character_name: data.charName,
        character_class: data.charClass,
        last_played: new Date().toISOString(),
        player_count: 1,
      },
    ]);

    setActiveGame({
      sessionId: session.session_id,
      characterId: char.id,
      character: char,
    });
    setShowNewCampaign(false);
    setScreen('game');
  }, []);

  const handleBackToHub = useCallback(() => {
    setScreen('hub');
    setActiveGame(null);
  }, []);

  if (screen === 'game' && activeGame) {
    return (
      <GameScreen
        sessionId={activeGame.sessionId}
        characterId={activeGame.characterId}
        initialCharacter={activeGame.character}
        onBackToHub={handleBackToHub}
      />
    );
  }

  return (
    <>
      <HubScreen
        campaigns={campaigns}
        onNewCampaign={() => setShowNewCampaign(true)}
        onPlayCampaign={() => {}}
      />
      <NewCampaignModal
        isOpen={showNewCampaign}
        onClose={() => setShowNewCampaign(false)}
        onSubmit={handleNewCampaign}
      />
    </>
  );
}
