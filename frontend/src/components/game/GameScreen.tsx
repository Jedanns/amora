import { useState, useCallback, useEffect, useRef } from 'react';
import { ScrollText, User, Package, Heart } from 'lucide-react';
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
import { api, createGameStream } from '@/services/api.ts';
import type { Character, SkillCategory } from '@/types/character.ts';
import { DEFAULT_SKILL_CATEGORIES, CLASS_LABELS } from '@/types/character.ts';
import type { NpcRelationship } from '@/types/npc.ts';
import type { Item, Inventory } from '@/types/inventory.ts';
import type { StreamMessage } from '@/types/game.ts';

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
  isResumed?: boolean;
}

const TABS = [
  { id: 'quests', number: 1, icon: ScrollText },
  { id: 'character', number: 2, icon: User },
  { id: 'inventory', number: 3, icon: Package },
  { id: 'relations', number: 4, icon: Heart },
];

function buildDefaultInventory(): Inventory {
  return {
    crowns: 0,
    armor_class: 0,
    total_damage: '-',
    weapon_bonus: 0,
    equipment: {
      main_hand: null,
      off_hand: null,
      head: null,
      chest: null,
      arms: null,
      legs: null,
      cape: null,
    },
    items: [],
    weapons: [],
    armors: [],
    consumables: [],
  };
}

export default function GameScreen({
  sessionId,
  characterId,
  initialCharacter,
  onBackToHub,
  isResumed = false,
}: GameScreenProps) {
  const [activeTab, setActiveTab] = useState('quests');
  const [character, setCharacter] = useState<Character>(initialCharacter);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streamingContent, setStreamingContent] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [modelName, setModelName] = useState<string | undefined>();
  const [location, setLocation] = useState(initialCharacter.location || 'spawn');
  const [timeOfDay] = useState('Morning');
  const [skillCategories] = useState<SkillCategory[]>(DEFAULT_SKILL_CATEGORIES);
  const [quests, setQuests] = useState<Array<{
    id: string;
    name: string;
    description: string;
    level: number;
    xp_reward: number;
    status: 'active' | 'completed' | 'failed';
    reward_text?: string;
    bookmarked?: boolean;
    notes?: Array<{ source: string; text: string }>;
  }>>([]);
  const [rumors] = useState<Array<{
    id: string;
    name: string;
    description: string;
    level: number;
    xp_reward: number;
    bookmarked?: boolean;
    source?: string;
  }>>([]);
  const [relationships] = useState<NpcRelationship[]>([]);
  const [inventory, setInventory] = useState<Inventory>(buildDefaultInventory());

  const msgIdCounter = useRef(1);
  const wsRef = useRef<ReturnType<typeof createGameStream> | null>(null);
  const streamAccumulatorRef = useRef('');
  const initDone = useRef(false);

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

  const refreshCharacter = useCallback(async () => {
    try {
      const char = await api.character.get(characterId);
      setCharacter(char);
    } catch { /* character might not exist yet */ }
  }, [characterId]);

  const refreshInventory = useCallback(async () => {
    try {
      const inv = await api.character.getInventory(characterId);
      const weapons = inv.items
        .filter(i => i.item_type === 'weapon')
        .map(i => ({
          id: i.id, name: i.name, type: 'weapon' as const,
          rarity: (i.rarity || 'common') as Item['rarity'],
          value: i.value, quantity: i.quantity,
          description: i.description,
        }));
      const armors = inv.items
        .filter(i => i.item_type === 'armor')
        .map(i => ({
          id: i.id, name: i.name, type: 'armor' as const,
          rarity: (i.rarity || 'common') as Item['rarity'],
          value: i.value, quantity: i.quantity,
          description: i.description,
        }));
      const consumables = inv.items
        .filter(i => i.item_type === 'consumable')
        .map(i => ({
          id: i.id, name: i.name, type: 'consumable' as const,
          rarity: (i.rarity || 'common') as Item['rarity'],
          value: i.value, quantity: i.quantity,
          description: i.description,
        }));
      setInventory(prev => ({
        ...prev,
        items: inv.items.map(i => ({
          id: i.id,
          name: i.name,
          type: i.item_type as Item['type'],
          rarity: (i.rarity || 'common') as Item['rarity'],
          value: i.value,
          quantity: i.quantity,
          description: i.description,
        })),
        weapons,
        armors,
        consumables,
      }));
    } catch { /* inventory might be empty */ }
  }, [characterId]);

  const refreshQuests = useCallback(async () => {
    try {
      const result = await api.game.listQuests(sessionId);
      setQuests(result.quests.map(q => ({
        id: q.id,
        name: q.name,
        description: q.description,
        level: 1,
        xp_reward: 0,
        status: q.status as 'active' | 'completed' | 'failed',
        bookmarked: false,
      })));
    } catch { /* quests might not exist */ }
  }, [sessionId]);

  useEffect(() => {
    if (initDone.current) return;
    initDone.current = true;

    const init = async () => {
      await api.game.setActiveCharacter(sessionId, characterId).catch(() => {});

      await Promise.all([refreshCharacter(), refreshInventory(), refreshQuests()]);

      if (isResumed) {
        try {
          const history = await api.game.getHistory(sessionId, 100);
          const restored: ChatMessage[] = history.entries
            .filter(e => e.type === 'user' || e.type === 'assistant' || e.type === 'system')
            .map(e => ({
              id: e.id,
              role: e.type as ChatMessage['role'],
              content: e.content,
              timestamp: e.timestamp,
            }));

          if (restored.length > 0) {
            setMessages(restored);
          } else {
            addMessage('system', `Session reprise. ${initialCharacter.name} (${CLASS_LABELS[initialCharacter.character_class]}) est pret(e) a continuer !`);
          }
        } catch {
          addMessage('system', `Session reprise. ${initialCharacter.name} (${CLASS_LABELS[initialCharacter.character_class]}) est pret(e) a continuer !`);
        }

        try {
          const state = await api.game.getSession(sessionId);
          if (state.location) setLocation(state.location);
        } catch { /* ignore */ }
      } else {
        addMessage('system', `Session creee. ${initialCharacter.name} (${CLASS_LABELS[initialCharacter.character_class]}) est pret(e) a l'aventure !`);

        const introPrompt = `Je suis ${initialCharacter.name}, un(e) ${CLASS_LABELS[initialCharacter.character_class]}. Je viens d'arriver dans une taverne. Decris la scene et presente-moi l'endroit.`;
        sendMessage(introPrompt, true);
      }
    };

    init();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    return () => {
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, []);

  const sendViaWebSocket = useCallback((text: string, isIntro: boolean) => {
    if (!isIntro) {
      addMessage('user', text);
    }
    setIsGenerating(true);
    setStreamingContent('');
    streamAccumulatorRef.current = '';

    if (!wsRef.current) {
      wsRef.current = createGameStream(
        sessionId,
        (chunk) => {
          streamAccumulatorRef.current += chunk;
          setStreamingContent(streamAccumulatorRef.current);
        },
        (msg: StreamMessage & { type: 'complete' }) => {
          setIsGenerating(false);
          setStreamingContent(null);
          learnKeywords(msg.narrative);
          addMessage('assistant', msg.narrative);
          streamAccumulatorRef.current = '';

          if (msg.state) {
            if (msg.state.location) setLocation(msg.state.location);
          }

          refreshCharacter();
          refreshInventory();
          refreshQuests();
          api.game.save(sessionId).catch(() => {});
        },
        (error) => {
          setIsGenerating(false);
          setStreamingContent(null);
          streamAccumulatorRef.current = '';
          addMessage('system', `Erreur streaming: ${error}`);
          wsRef.current = null;
        },
      );

      setTimeout(() => {
        wsRef.current?.send(text);
      }, 200);
    } else {
      wsRef.current.send(text);
    }
  }, [sessionId, addMessage, refreshCharacter, refreshInventory, refreshQuests]);

  const sendViaHttp = useCallback(async (text: string, isIntro: boolean) => {
    if (!isIntro) {
      addMessage('user', text);
    }
    setIsGenerating(true);
    try {
      const resp = await api.game.sendInput(sessionId, text);
      learnKeywords(resp.narrative);
      addMessage('assistant', resp.narrative);

      if (resp.state) {
        if (resp.state.location) setLocation(resp.state.location);
      }

      await Promise.all([refreshCharacter(), refreshInventory(), refreshQuests()]);
      api.game.save(sessionId).catch(() => {});
    } catch (err) {
      addMessage('system', `Erreur: ${err instanceof Error ? err.message : 'Erreur inconnue'}`);
    }
    setIsGenerating(false);
  }, [sessionId, addMessage, refreshCharacter, refreshInventory, refreshQuests]);

  const sendMessage = useCallback((text: string, isIntro = false) => {
    if (isConnected) {
      sendViaWebSocket(text, isIntro);
    } else {
      sendViaHttp(text, isIntro);
    }
  }, [isConnected, sendViaWebSocket, sendViaHttp]);

  const handleSendMessage = useCallback((text: string) => {
    if (text.startsWith('/roll ')) {
      const notation = text.slice(6).trim();
      if (notation) {
        api.game.rollDice(sessionId, notation).then(result => {
          addMessage('system', `Lancer de des: ${result.notation} = ${result.total} (${result.individual.join(' + ')}${result.modifier ? ` + ${result.modifier}` : ''})`);
        }).catch(err => {
          addMessage('system', `Erreur de: ${err instanceof Error ? err.message : 'Erreur'}`);
        });
        return;
      }
    }
    sendMessage(text, false);
  }, [sendMessage, sessionId, addMessage]);

  const handleSave = useCallback(async () => {
    try {
      await api.game.save(sessionId);
      addMessage('system', 'Partie sauvegardee.');
    } catch (err) {
      addMessage('system', `Erreur sauvegarde: ${err instanceof Error ? err.message : 'Erreur'}`);
    }
  }, [sessionId, addMessage]);

  const handleBackToHub = useCallback(async () => {
    try {
      await api.game.save(sessionId);
    } catch { /* ignore */ }
    onBackToHub();
  }, [sessionId, onBackToHub]);

  const displayMessages = streamingContent !== null
    ? [
        ...messages,
        {
          id: 'streaming',
          role: 'assistant' as const,
          content: streamingContent || '...',
          timestamp: new Date().toISOString(),
        },
      ]
    : messages;

  const renderLeftPanel = () => {
    return (
      <div className="flex flex-col h-full bg-bg-panel">
        <div className="px-3 py-2 border-b border-border-primary">
          <TabBar tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />
        </div>
        <div className="flex-1 overflow-y-auto min-h-0">
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
          onClick={handleBackToHub}
          className="mx-3 my-2 px-4 py-2 bg-transparent border border-border-primary text-text-secondary rounded-md cursor-pointer text-xs hover:border-text-secondary hover:text-text-primary transition-all duration-200"
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
          messages={displayMessages}
          isGenerating={isGenerating}
          onSendMessage={handleSendMessage}
          playerName={initialCharacter.name}
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
