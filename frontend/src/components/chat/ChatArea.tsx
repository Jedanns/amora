import {
  type KeyboardEvent,
  useState,
  useRef,
  useEffect,
  useCallback,
} from 'react';
import { SendHorizonal } from 'lucide-react';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
  location?: string;
  timeOfDay?: string;
}

interface ChatAreaProps {
  messages: ChatMessage[];
  isGenerating: boolean;
  onSendMessage: (message: string) => void;
  playerName?: string;
}

function TypingDot({ delay }: { delay: number }) {
  const [opacity, setOpacity] = useState(0.3);

  useEffect(() => {
    let frame: number;
    let start: number | null = null;

    function animate(ts: number) {
      if (start === null) start = ts;
      const elapsed = (ts - start + delay) % 1200;
      const o = elapsed < 400 ? 0.3 + 0.7 * (elapsed / 400) : 1.0 - 0.7 * Math.min((elapsed - 400) / 400, 1);
      setOpacity(o);
      frame = requestAnimationFrame(animate);
    }

    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
  }, [delay]);

  return (
    <span
      className="w-[5px] h-[5px] rounded-full bg-gold transition-opacity duration-100"
      style={{ opacity }}
    />
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-2 px-4.5 py-2.5 bg-gold/5 border border-gold/10 rounded-[10px]">
      <div className="flex items-center gap-[3px]">
        <TypingDot delay={0} />
        <TypingDot delay={200} />
        <TypingDot delay={400} />
      </div>
      <span className="text-xs text-gold italic tracking-[0.02em]">Le Maitre du Donjon reflechit...</span>
    </div>
  );
}

function AssistantMessage({ message }: { message: ChatMessage }) {
  const contextParts = [message.location, message.timeOfDay].filter(Boolean);

  return (
    <div className="relative bg-bg-card border border-border-primary rounded-[10px] px-4.5 py-3.5 max-w-full">
      <div className="text-[10px] font-bold tracking-[0.1em] uppercase text-gold mb-0.5">Maitre du Donjon</div>
      {contextParts.length > 0 && (
        <div className="text-[10px] text-text-secondary tracking-[0.03em] mb-2.5 opacity-70">
          {contextParts.join(' \u00B7 ')}
        </div>
      )}
      <div className="text-sm leading-[1.7] text-text-primary whitespace-pre-wrap break-words">{message.content}</div>
      {message.timestamp && (
        <div className="text-[9px] text-text-secondary mt-2 opacity-50">
          {message.timestamp}
        </div>
      )}
    </div>
  );
}

function UserMessage({ message, playerName }: { message: ChatMessage; playerName?: string }) {
  return (
    <div className="self-end bg-red/[0.08] border border-red/20 rounded-[10px] px-4 py-2.5 max-w-[75%]">
      <div className="text-[10px] font-bold tracking-[0.1em] uppercase text-red mb-1 text-right">{playerName ?? 'Joueur'}</div>
      <div className="text-sm leading-relaxed text-text-primary whitespace-pre-wrap break-words">{message.content}</div>
      {message.timestamp && (
        <div className="text-[9px] text-text-secondary mt-1.5 opacity-50 text-right">
          {message.timestamp}
        </div>
      )}
    </div>
  );
}

function SystemMessage({ message }: { message: ChatMessage }) {
  return (
    <div className="self-center bg-gold/[0.08] border border-gold/20 rounded-md px-5 py-2 max-w-[85%] text-center">
      <div className="text-xs leading-normal text-gold italic">{message.content}</div>
    </div>
  );
}

function ChatArea({ messages, isGenerating, onSendMessage, playerName }: ChatAreaProps) {
  const [draft, setDraft] = useState('');
  const listRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = listRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages.length, isGenerating]);

  const autoResize = useCallback(() => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
    }
  }, []);

  const handleSend = useCallback(() => {
    const text = draft.trim();
    if (!text || isGenerating) return;
    onSendMessage(text);
    setDraft('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [draft, isGenerating, onSendMessage]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  const canSend = draft.trim() && !isGenerating;

  return (
    <div className="flex flex-col h-full overflow-hidden bg-bg-primary">
      {/* Message list */}
      <div ref={listRef} className="flex-1 overflow-y-auto px-6 py-4 flex flex-col gap-4">
        {messages.map((msg) => {
          switch (msg.role) {
            case 'assistant':
              return <AssistantMessage key={msg.id} message={msg} />;
            case 'user':
              return <UserMessage key={msg.id} message={msg} playerName={playerName} />;
            case 'system':
              return <SystemMessage key={msg.id} message={msg} />;
          }
        })}
        {isGenerating && <TypingIndicator />}
      </div>

      {/* Input area */}
      <div className="shrink-0 border-t border-border-primary bg-bg-panel px-4 py-3 flex items-end gap-2.5">
        <textarea
          ref={textareaRef}
          className="flex-1 resize-none border border-border-primary rounded-lg bg-bg-input text-text-primary text-sm leading-normal px-3.5 py-2.5 font-[inherit] outline-none min-h-[42px] max-h-[160px] overflow-auto transition-colors duration-200 focus:border-gold"
          value={draft}
          onChange={(e) => {
            setDraft(e.target.value);
            autoResize();
          }}
          onKeyDown={handleKeyDown}
          placeholder="Que faites-vous ?"
          rows={1}
          disabled={isGenerating}
        />
        <button
          className={`inline-flex items-center justify-center w-[42px] h-[42px] border border-gold rounded-lg text-gold text-lg shrink-0 p-0 font-[inherit] leading-none transition-all duration-200 ${
            canSend
              ? 'bg-gold/12 cursor-pointer hover:bg-gold/25 hover:shadow-[0_0_10px_rgba(201,168,76,0.2)]'
              : 'bg-gold/12 opacity-40 cursor-not-allowed'
          }`}
          onClick={handleSend}
          disabled={!canSend}
          aria-label="Envoyer"
          title="Envoyer (Entree)"
        >
          <SendHorizonal size={18} />
        </button>
      </div>
    </div>
  );
}

export default ChatArea;
