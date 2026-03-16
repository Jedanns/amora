import {
  type CSSProperties,
  type KeyboardEvent,
  useState,
  useRef,
  useEffect,
  useCallback,
} from 'react';

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

const containerStyle: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  height: '100%',
  overflow: 'hidden',
  backgroundColor: '#0a0a0f',
};

const messageListStyle: CSSProperties = {
  flex: 1,
  overflowY: 'auto',
  padding: '16px 24px',
  display: 'flex',
  flexDirection: 'column',
  gap: 16,
};

const inputContainerStyle: CSSProperties = {
  flexShrink: 0,
  borderTop: '1px solid #2a2a3a',
  backgroundColor: '#151520',
  padding: '12px 16px',
  display: 'flex',
  alignItems: 'flex-end',
  gap: 10,
};

const textareaStyle: CSSProperties = {
  flex: 1,
  resize: 'none',
  border: '1px solid #2a2a3a',
  borderRadius: 8,
  backgroundColor: '#1e1e2e',
  color: '#e8e8f0',
  fontSize: 14,
  lineHeight: 1.5,
  padding: '10px 14px',
  fontFamily: 'inherit',
  outline: 'none',
  minHeight: 42,
  maxHeight: 160,
  overflow: 'auto',
  transition: 'border-color 0.2s ease',
};

const sendButtonBase: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: 42,
  height: 42,
  border: '1px solid #c9a84c',
  borderRadius: 8,
  backgroundColor: 'rgba(201, 168, 76, 0.12)',
  color: '#c9a84c',
  fontSize: 18,
  cursor: 'pointer',
  transition: 'all 0.2s ease',
  flexShrink: 0,
  padding: 0,
  fontFamily: 'inherit',
  lineHeight: 1,
};

function assistantBubbleStyle(): CSSProperties {
  return {
    position: 'relative',
    backgroundColor: '#1a1a28',
    border: '1px solid #2a2a3a',
    borderRadius: 10,
    padding: '14px 18px',
    maxWidth: '100%',
  };
}

const assistantLabel: CSSProperties = {
  fontSize: 10,
  fontWeight: 700,
  letterSpacing: '0.1em',
  textTransform: 'uppercase',
  color: '#c9a84c',
  marginBottom: 2,
};

const assistantContext: CSSProperties = {
  fontSize: 10,
  color: '#9898a8',
  letterSpacing: '0.03em',
  marginBottom: 10,
  opacity: 0.7,
};

const narrativeText: CSSProperties = {
  fontSize: 14,
  lineHeight: 1.7,
  color: '#e8e8f0',
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
};

const ttsButtonStyle: CSSProperties = {
  position: 'absolute',
  top: 10,
  right: 10,
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: 24,
  height: 24,
  border: '1px solid #2a2a3a',
  borderRadius: 4,
  backgroundColor: 'transparent',
  color: '#9898a8',
  fontSize: 12,
  cursor: 'pointer',
  padding: 0,
  fontFamily: 'inherit',
  lineHeight: 1,
  transition: 'all 0.2s ease',
};

function userBubbleStyle(): CSSProperties {
  return {
    alignSelf: 'flex-end',
    backgroundColor: 'rgba(233, 69, 96, 0.08)',
    border: '1px solid rgba(233, 69, 96, 0.2)',
    borderRadius: 10,
    padding: '10px 16px',
    maxWidth: '75%',
  };
}

const userLabel: CSSProperties = {
  fontSize: 10,
  fontWeight: 700,
  letterSpacing: '0.1em',
  textTransform: 'uppercase',
  color: '#e94560',
  marginBottom: 4,
  textAlign: 'right',
};

const userText: CSSProperties = {
  fontSize: 14,
  lineHeight: 1.6,
  color: '#e8e8f0',
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
};

function systemBubbleStyle(): CSSProperties {
  return {
    alignSelf: 'center',
    backgroundColor: 'rgba(201, 168, 76, 0.08)',
    border: '1px solid rgba(201, 168, 76, 0.2)',
    borderRadius: 6,
    padding: '8px 20px',
    maxWidth: '85%',
    textAlign: 'center',
  };
}

const systemText: CSSProperties = {
  fontSize: 12,
  lineHeight: 1.5,
  color: '#c9a84c',
  fontStyle: 'italic',
};

const typingContainer: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  padding: '10px 18px',
  backgroundColor: 'rgba(201, 168, 76, 0.05)',
  border: '1px solid rgba(201, 168, 76, 0.1)',
  borderRadius: 10,
};

const typingText: CSSProperties = {
  fontSize: 12,
  color: '#c9a84c',
  fontStyle: 'italic',
  letterSpacing: '0.02em',
};

const dotContainer: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 3,
};

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

  const style: CSSProperties = {
    width: 5,
    height: 5,
    borderRadius: '50%',
    backgroundColor: '#c9a84c',
    opacity,
    transition: 'opacity 0.1s',
  };

  return <span style={style} />;
}

function TypingIndicator() {
  return (
    <div style={typingContainer}>
      <div style={dotContainer}>
        <TypingDot delay={0} />
        <TypingDot delay={200} />
        <TypingDot delay={400} />
      </div>
      <span style={typingText}>Le Maitre du Donjon reflechit...</span>
    </div>
  );
}

function AssistantMessage({ message }: { message: ChatMessage }) {
  const [ttsHovered, setTtsHovered] = useState(false);

  const contextParts = [message.location, message.timeOfDay].filter(Boolean);

  const ttsStyle: CSSProperties = {
    ...ttsButtonStyle,
    borderColor: ttsHovered ? '#9898a8' : '#2a2a3a',
    color: ttsHovered ? '#e8e8f0' : '#9898a8',
  };

  return (
    <div style={assistantBubbleStyle()}>
      <div style={assistantLabel}>Maitre du Donjon</div>
      {contextParts.length > 0 && (
        <div style={assistantContext}>
          {contextParts.join(' \u00B7 ')}
        </div>
      )}
      <div style={narrativeText}>{message.content}</div>
      <button
        style={ttsStyle}
        onMouseEnter={() => setTtsHovered(true)}
        onMouseLeave={() => setTtsHovered(false)}
        aria-label="Text to speech"
        title="Lire a voix haute"
      >
        &#9835;
      </button>
      {message.timestamp && (
        <div style={{ fontSize: 9, color: '#9898a8', marginTop: 8, opacity: 0.5 }}>
          {message.timestamp}
        </div>
      )}
    </div>
  );
}

function UserMessage({ message, playerName }: { message: ChatMessage; playerName?: string }) {
  return (
    <div style={userBubbleStyle()}>
      <div style={userLabel}>{playerName ?? 'Joueur'}</div>
      <div style={userText}>{message.content}</div>
      {message.timestamp && (
        <div style={{ fontSize: 9, color: '#9898a8', marginTop: 6, opacity: 0.5, textAlign: 'right' }}>
          {message.timestamp}
        </div>
      )}
    </div>
  );
}

function SystemMessage({ message }: { message: ChatMessage }) {
  return (
    <div style={systemBubbleStyle()}>
      <div style={systemText}>{message.content}</div>
    </div>
  );
}

function ChatArea({ messages, isGenerating, onSendMessage, playerName }: ChatAreaProps) {
  const [draft, setDraft] = useState('');
  const [sendHovered, setSendHovered] = useState(false);
  const [inputFocused, setInputFocused] = useState(false);
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

  const currentTextareaStyle: CSSProperties = {
    ...textareaStyle,
    borderColor: inputFocused ? '#c9a84c' : '#2a2a3a',
  };

  const currentSendStyle: CSSProperties = {
    ...sendButtonBase,
    backgroundColor: sendHovered
      ? 'rgba(201, 168, 76, 0.25)'
      : 'rgba(201, 168, 76, 0.12)',
    boxShadow: sendHovered ? '0 0 10px rgba(201, 168, 76, 0.2)' : 'none',
    opacity: draft.trim() && !isGenerating ? 1 : 0.4,
    cursor: draft.trim() && !isGenerating ? 'pointer' : 'not-allowed',
  };

  return (
    <div style={containerStyle}>
      <div ref={listRef} style={messageListStyle}>
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

      <div style={inputContainerStyle}>
        <textarea
          ref={textareaRef}
          style={currentTextareaStyle}
          value={draft}
          onChange={(e) => {
            setDraft(e.target.value);
            autoResize();
          }}
          onKeyDown={handleKeyDown}
          onFocus={() => setInputFocused(true)}
          onBlur={() => setInputFocused(false)}
          placeholder="Que faites-vous ?"
          rows={1}
          disabled={isGenerating}
        />
        <button
          style={currentSendStyle}
          onClick={handleSend}
          onMouseEnter={() => setSendHovered(true)}
          onMouseLeave={() => setSendHovered(false)}
          disabled={!draft.trim() || isGenerating}
          aria-label="Envoyer"
          title="Envoyer (Entree)"
        >
          &#10148;
        </button>
      </div>
    </div>
  );
}

export default ChatArea;
