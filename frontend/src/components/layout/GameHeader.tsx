interface GameHeaderProps {
  location?: string;
  timeOfDay?: string;
  isConnected: boolean;
  modelName?: string;
}

function GameHeader({
  location,
  timeOfDay,
  isConnected,
  modelName,
}: GameHeaderProps) {
  const parts = [location, timeOfDay].filter(Boolean);

  return (
    <div className="flex items-center justify-between h-full px-4 bg-bg-panel">
      <span className="text-sm font-bold tracking-[0.12em] text-gold uppercase whitespace-nowrap select-none">
        TAVERNE DU VIEUX GREG
      </span>

      <div className="flex items-center gap-1.5 text-xs text-text-secondary tracking-[0.04em]">
        {parts.length > 0 ? (
          parts.map((part, i) => (
            <span key={i}>
              {i > 0 && <span className="text-border-primary select-none"> &middot; </span>}
              {part}
            </span>
          ))
        ) : (
          <span className="text-border-primary">---</span>
        )}
        {modelName && (
          <>
            <span className="text-border-primary select-none"> &middot; </span>
            <span className="text-blue text-[10px]">{modelName}</span>
          </>
        )}
      </div>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 text-[11px] font-semibold tracking-[0.04em]">
          <span
            className={`w-[7px] h-[7px] rounded-full shrink-0 ${
              isConnected
                ? 'bg-green shadow-[0_0_6px_rgba(83,215,105,0.5)]'
                : 'bg-red shadow-[0_0_6px_rgba(233,69,96,0.5)]'
            }`}
          />
          <span className={isConnected ? 'text-green' : 'text-red'}>
            {isConnected ? 'Connecte' : 'Deconnecte'}
          </span>
        </div>
      </div>
    </div>
  );
}

export default GameHeader;
