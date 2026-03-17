interface ProgressBarProps {
  current: number;
  max: number;
  color?: string;
  height?: number;
  showLabel?: boolean;
  label?: string;
  labelColor?: string;
}

function ProgressBar({
  current,
  max,
  color = '#c9a84c',
  height = 6,
  showLabel = false,
  label,
  labelColor,
}: ProgressBarProps) {
  const percent = max > 0 ? (current / max) * 100 : 0;

  return (
    <div className="w-full">
      {showLabel && (
        <div className="flex justify-between items-baseline mb-1 text-[11px] font-medium tracking-wide">
          <span style={{ color: labelColor ?? '#9898a8' }}>
            {label ?? ''}
          </span>
          <span style={{ color: labelColor ?? '#9898a8' }}>
            {current}/{max}
          </span>
        </div>
      )}
      <div
        className="w-full bg-white/8 overflow-hidden relative"
        style={{ height, borderRadius: height / 2 }}
      >
        <div
          className="h-full transition-[width] duration-400 ease-out"
          style={{
            width: `${Math.min(100, Math.max(0, percent))}%`,
            backgroundColor: color,
            borderRadius: height / 2,
            boxShadow: percent > 0 ? `0 0 6px ${color}40` : 'none',
          }}
        />
      </div>
    </div>
  );
}

export default ProgressBar;
