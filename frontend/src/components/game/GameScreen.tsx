import { useState, useCallback, useEffect, useRef } from 'react';
import GameLayout from '@/components/layout/GameLayout.tsx';
import GameHeader from '@/components/layout/GameHeader.tsx';
import ChatArea from '@/components/chat/ChatArea.tsx';
import RightPanel from '@/components/layout/RightPanel.tsx';
import TabBar from '@/components/common/TabBar.tsx';
import QuestsTab from '@/components/tabs/QuestsTab.tsx';
import CharacterTab from '@/components/tabs/CharacterTab.tsx';
import InventoryTab from '@/components/tabs/InventoryTab.tsx';
import RelationshipsTab from '@/components/tabs/RelationshipsTab.tsx';
import { learnKeywords } from '@/components/chat/NarrativeHighlighter.tsx';
import { api } from '@/services/api.ts';
import type { Character, SkillCategory } from '@/types/character.ts';
import { DEFAULT_SKILL_CATEGORIES, CLASS_LABELS } from '@/types/character.ts';
import type { Quest, Rumor } from '@/types/quest.ts';
import type { NpcRelationship } from '@/types/npc.ts';
import type { Item, EquipmentSlots } from '@/types/inventory.ts';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
  location?: string;
  timeOfDay?: string;
}

interface GameScreenProps {
  sessionId: string;
  characterId: string;
  initialCharacter: Character;
  onBackToHub: () => void;
}

const TABS = [
  { id: 'quests', number: 1, icon: '\u{1F4DC}' },
  { id: 'character', number: 2, icon: '\u{1F464}' },
  { id: 'inventory', number: 3, icon: '\u{1F4E6}' },
  { id: 'relations', number: 4, icon: '\u2764\uFE0F' },
];

const MOCK_QUESTS: Quest[] = [
  {
    id: 'q1',
    name: 'Get Your Bearings',
    description: "Explore the area and learn about your surroundings. Talk to the locals and find out what's happening.",
    level: 1,
    xp_reward: 10,
    status: 'active',
    reward_text: 'A helping hand in finding your first quest',
    bookmarked: true,
    notes: [
      { source: 'Old Greg', text: "Le forgeron indique que Greg possede des contacts parmi les Mercenaires Ironhand qui pourraient reveler des informations detaillees sur les paris et les marchands soutenant le tournoi." },
      { source: 'Old Greg', text: "Aldric mentionne que Greg se tient generalement pres de la porte nord du Vieux Quartier au crepuscule." },
    ],
  },
];

const MOCK_RUMORS: Rumor[] = [
  {
    id: 'r1',
    name: "The Temple's Long Memory",
    description: "A monk from the former temple has been tracking you across the realm, asking pointed questions in every settlement.",
    level: 1,
    xp_reward: 50,
    source: 'Overheard',
  },
];

const MOCK_RELATIONSHIPS: NpcRelationship[] = [
  {
    id: 'npc1',
    name: 'Aldric le Forgeron',
    disposition: 'Curious',
    relationship_level: 8,
    max_relationship: 10,
    is_dead: false,
  },
  {
    id: 'npc2',
    name: 'Old Greg',
    disposition: 'Guarded',
    relationship_level: 4,
    max_relationship: 10,
    is_dead: false,
  },
];

export default function GameScreen({ sessionId, characterId, initialCharacter, onBackToHub }: GameScreenProps) {
  const [activeTab, setActiveTab] = useState('quests');
  const [character, setCharacter] = useState<Character>(initialCharacter);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'system',
      content: `Session creee. ${initialCharacter.name} (${CLASS_LABELS[initialCharacter.character_class]}) est pret a l'aventure !`,
    },
  ]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [modelName, setModelName] = useState<string | undefined>();
  const [location, setLocation] = useState('Crosshaven');
  const [timeOfDay, setTimeOfDay] = useState('Morning');
  const [skillCategories] = useState<SkillCategory[]>(DEFAULT_SKILL_CATEGORIES);
  const [quests] = useState(MOCK_QUESTS);
  const [rumors] = useState(MOCK_RUMORS);
  const [relationships] = useState(MOCK_RELATIONSHIPS);
  const [keywords] = useState({
    playerName: initialCharacter.name,
    npcNames: ['Brok', 'Grim', 'Greg', 'Aldric'],
    locations: ['Taverne', 'Dragon Ivre', 'Crosshaven', 'Valcrest'],
    items: [] as string[],
    factions: ['Mercenaires de la Main de Fer'],
  });

  const [inventory] = useState({
    crowns: 25,
    armor_class: 4,
    total_damage: '1d4',
    weapon_bonus: 2,
    equipment: {
      main_hand: {
        id: 'w1', name: 'Cracked Leather Dagger', type: 'weapon' as const,
        rarity: 'common' as const, slot: 'main_hand', weapon_hand: 'one_hand',
        damage_dice: '1d4', value: 9, quantity: 1,
      },
      off_hand: null,
      head: null,
      chest: {
        id: 'a1', name: 'Worn Leather Jerkin', type: 'armor' as const,
        rarity: 'common' as const, slot: 'chest', armor_bonus: 3, value: 11, quantity: 1,
      },
      arms: null,
      legs: {
        id: 'a2', name: 'Tattered Leather Pants', type: 'armor' as const,
        rarity: 'common' as const, slot: 'legs', armor_bonus: 1, value: 9, quantity: 1,
      },
      cape: null,
    } as EquipmentSlots,
    weapons: [
      {
        id: 'w1', name: 'Cracked Leather Dagger', type: 'weapon' as const,
        rarity: 'common' as const, slot: 'main_hand', weapon_hand: 'one_hand',
        damage_dice: '1d4', value: 9, quantity: 1,
      },
    ] as Item[],
    armors: [
      {
        id: 'a1', name: 'Worn Leather Jerkin', type: 'armor' as const,
        rarity: 'common' as const, slot: 'chest', armor_bonus: 3, value: 11, quantity: 1,
      },
      {
        id: 'a2', name: 'Tattered Leather Pants', type: 'armor' as const,
        rarity: 'common' as const, slot: 'legs', armor_bonus: 1, value: 9, quantity: 1,
      },
      {
        id: 'a3', name: 'Gantelets De Marteau', type: 'armor' as const,
        rarity: 'uncommon' as const, slot: 'arms', armor_bonus: 1, value: 120, quantity: 1,
      },
    ] as Item[],
    consumables: [
      {
        id: 'c1', name: 'Faint Ember Tonic', type: 'consumable' as const,
        rarity: 'common' as const, heal_percent: 25, heal_type: 'Health',
        value: 23, quantity: 1,
      },
    ] as Item[],
  });

  const msgIdCounter = useRef(1);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const health = await api.llm.health();
        setIsConnected(health.healthy);
        if (health.model) setModelName(health.model);
      } catch {
        setIsConnected(false);
      }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const introPrompt = `Je suis ${initialCharacter.name}, un(e) ${CLASS_LABELS[initialCharacter.character_class]}. Je viens d'arriver dans une taverne. Decris la scene et presente-moi l'endroit.`;
    handleSendMessage(introPrompt, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const addMessage = useCallback((role: ChatMessage['role'], content: string) => {
    const id = `msg_${msgIdCounter.current++}`;
    setMessages(prev => [...prev, {
      id,
      role,
      content,
      timestamp: new Date().toISOString(),
      location: role === 'assistant' ? location : undefined,
      timeOfDay: role === 'assistant' ? timeOfDay : undefined,
    }]);
  }, [location, timeOfDay]);

  const handleSendMessage = useCallback(async (text: string, isIntro = false) => {
    if (!isIntro) {
      addMessage('user', text);
    }
    setIsGenerating(true);
    try {
      const resp = await api.game.sendInput(sessionId, text);
      learnKeywords(resp.narrative, keywords);
      addMessage('assistant', resp.narrative);

      if (resp.state) {
        if (resp.state.location) setLocation(resp.state.location);
      }

      try {
        const char = await api.character.get(characterId);
        setCharacter(char);
      } catch { /* ignore */ }
    } catch (err) {
      addMessage('system', `Erreur: ${err instanceof Error ? err.message : 'Erreur inconnue'}`);
    }
    setIsGenerating(false);
  }, [sessionId, characterId, addMessage, keywords]);

  const handleSave = useCallback(async () => {
    try {
      await api.game.save(sessionId);
      addMessage('system', 'Partie sauvegardee.');
    } catch (err) {
      addMessage('system', `Erreur sauvegarde: ${err instanceof Error ? err.message : 'Erreur'}`);
    }
  }, [sessionId, addMessage]);

  const renderLeftPanel = () => {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#151520' }}>
        <div style={{ padding: '8px 12px', borderBottom: '1px solid #2a2a3a' }}>
          <TabBar tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />
        </div>
        <div style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
          {activeTab === 'quests' && (
            <QuestsTab quests={quests} rumors={rumors} />
          )}
          {activeTab === 'character' && (
            <CharacterTab character={character} skillCategories={skillCategories} />
          )}
          {activeTab === 'inventory' && (
            <InventoryTab inventory={inventory} />
          )}
          {activeTab === 'relations' && (
            <RelationshipsTab relationships={relationships} />
          )}
        </div>
        <button
          onClick={onBackToHub}
          style={{
            padding: '8px 16px',
            margin: '8px 12px',
            background: 'transparent',
            border: '1px solid #2a2a3a',
            color: '#9898a8',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '12px',
          }}
        >
          Retour au Hub
        </button>
      </div>
    );
  };

  return (
    <GameLayout
      header={
        <GameHeader
          location={location}
          timeOfDay={timeOfDay}
          isConnected={isConnected}
          modelName={modelName}
        />
      }
      leftPanel={renderLeftPanel()}
      mainArea={
        <ChatArea
          messages={messages}
          isGenerating={isGenerating}
          onSendMessage={handleSendMessage}
          playerName={initialCharacter.name}
          keywords={keywords}
        />
      }
      rightPanel={
        <RightPanel
          character={character}
          playerName={initialCharacter.name}
          onSave={handleSave}
        />
      }
    />
  );
}
