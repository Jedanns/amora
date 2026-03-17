import { useRef, useCallback, useEffect, useState } from 'react';
import { createGameStream } from '@/services/api';
import { learnKeywords } from '@/components/chat/NarrativeHighlighter';
import type { StreamMessage, GameState } from '@/types/game';

interface UseGameStreamOptions {
  sessionId: string;
  onNarrativeUpdate: (fullText: string) => void;
  onComplete: (narrative: string, state?: GameState) => void;
  onError: (error: string) => void;
}

export function useGameStream({ sessionId, onNarrativeUpdate, onComplete, onError }: UseGameStreamOptions) {
  const streamRef = useRef<ReturnType<typeof createGameStream> | null>(null);
  const accumulatorRef = useRef('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [isConnected, setIsConnected] = useState(false);

  const connect = useCallback(() => {
    if (streamRef.current) return;

    accumulatorRef.current = '';
    const stream = createGameStream(
      sessionId,
      (text) => {
        accumulatorRef.current += text;
        onNarrativeUpdate(accumulatorRef.current);
      },
      (msg: StreamMessage & { type: 'complete' }) => {
        setIsStreaming(false);
        learnKeywords(msg.narrative);
        onComplete(msg.narrative, msg.state);
        accumulatorRef.current = '';
      },
      (error) => {
        setIsStreaming(false);
        setIsConnected(false);
        onError(error);
        streamRef.current = null;
      },
    );

    streamRef.current = stream;
    setIsConnected(true);
  }, [sessionId, onNarrativeUpdate, onComplete, onError]);

  const send = useCallback((message: string) => {
    if (!streamRef.current) {
      connect();
    }
    accumulatorRef.current = '';
    setIsStreaming(true);
    setTimeout(() => {
      streamRef.current?.send(message);
    }, 100);
  }, [connect]);

  const disconnect = useCallback(() => {
    streamRef.current?.close();
    streamRef.current = null;
    setIsConnected(false);
    setIsStreaming(false);
    accumulatorRef.current = '';
  }, []);

  useEffect(() => {
    return () => {
      streamRef.current?.close();
      streamRef.current = null;
    };
  }, []);

  return { send, connect, disconnect, isStreaming, isConnected };
}
