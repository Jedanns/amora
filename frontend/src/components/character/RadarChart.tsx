import type { CSSProperties } from 'react';
import type { CharacterAttributes } from '../../types';

interface RadarChartProps {
  attributes: CharacterAttributes;
  maxValue?: number;
  size?: number;
}

const ATTRIBUTE_CONFIG: Array<{
  key: keyof CharacterAttributes;
  label: string;
  icon: string;
}> = [
  { key: 'strength', label: 'FOR', icon: '\u2694' },
  { key: 'dexterity', label: 'DEX', icon: '\u{1F5E1}' },
  { key: 'constitution', label: 'CON', icon: '\u2764' },
  { key: 'intelligence', label: 'INT', icon: '\u{1F9E0}' },
  { key: 'wisdom', label: 'SAG', icon: '\u{1F441}' },
  { key: 'charisma', label: 'CHA', icon: '\u2728' },
];

function hexagonPoints(cx: number, cy: number, radius: number): string {
  return Array.from({ length: 6 }, (_, i) => {
    const angle = (Math.PI / 3) * i - Math.PI / 2;
    return `${cx + radius * Math.cos(angle)},${cy + radius * Math.sin(angle)}`;
  }).join(' ');
}

function vertexPosition(
  cx: number,
  cy: number,
  radius: number,
  index: number,
): { x: number; y: number } {
  const angle = (Math.PI / 3) * index - Math.PI / 2;
  return {
    x: cx + radius * Math.cos(angle),
    y: cy + radius * Math.sin(angle),
  };
}

function RadarChart({
  attributes,
  maxValue = 20,
  size = 200,
}: RadarChartProps) {
  const cx = size / 2;
  const cy = size / 2;
  const outerRadius = size * 0.36;
  const gridLevels = [0.33, 0.66, 1.0];
  const labelRadius = outerRadius + 28;
  const iconRadius = outerRadius + 12;

  const dataPoints = ATTRIBUTE_CONFIG.map((attr, i) => {
    const value = Math.min(attributes[attr.key], maxValue);
    const ratio = value / maxValue;
    const pos = vertexPosition(cx, cy, outerRadius * ratio, i);
    return { ...attr, value, ratio, ...pos };
  });

  const dataPolygon = dataPoints.map(p => `${p.x},${p.y}`).join(' ');

  const containerStyle: CSSProperties = {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    padding: '4px 0',
  };

  return (
    <div style={containerStyle}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        style={{ overflow: 'visible' }}
      >
        {gridLevels.map(level => (
          <polygon
            key={level}
            points={hexagonPoints(cx, cy, outerRadius * level)}
            fill="none"
            stroke="#2a2a3a"
            strokeWidth={1}
          />
        ))}

        {ATTRIBUTE_CONFIG.map((_, i) => {
          const outer = vertexPosition(cx, cy, outerRadius, i);
          return (
            <line
              key={`spoke-${i}`}
              x1={cx}
              y1={cy}
              x2={outer.x}
              y2={outer.y}
              stroke="#2a2a3a"
              strokeWidth={0.5}
            />
          );
        })}

        <polygon
          points={dataPolygon}
          fill="rgba(201, 168, 76, 0.3)"
          stroke="#c9a84c"
          strokeWidth={1.5}
          strokeOpacity={0.8}
          strokeLinejoin="round"
        />

        {dataPoints.map(p => (
          <circle
            key={`dot-${p.key}`}
            cx={p.x}
            cy={p.y}
            r={2.5}
            fill="#c9a84c"
            stroke="#0a0a0f"
            strokeWidth={1}
          />
        ))}

        {ATTRIBUTE_CONFIG.map((attr, i) => {
          const iconPos = vertexPosition(cx, cy, iconRadius, i);
          return (
            <g key={`icon-${i}`}>
              <circle
                cx={iconPos.x}
                cy={iconPos.y}
                r={10}
                fill="#1a1a28"
                stroke="#2a2a3a"
                strokeWidth={1}
              />
              <text
                x={iconPos.x}
                y={iconPos.y}
                textAnchor="middle"
                dominantBaseline="central"
                fontSize={10}
                style={{ userSelect: 'none' }}
              >
                {attr.icon}
              </text>
            </g>
          );
        })}

        {ATTRIBUTE_CONFIG.map((attr, i) => {
          const labelPos = vertexPosition(cx, cy, labelRadius, i);
          const value = attributes[attr.key];
          return (
            <text
              key={`label-${i}`}
              x={labelPos.x}
              y={labelPos.y}
              textAnchor="middle"
              dominantBaseline="central"
              fontSize={10}
              fontWeight={600}
              fontFamily="inherit"
              fill="#9898a8"
              style={{ userSelect: 'none' }}
            >
              <tspan>{attr.label}</tspan>
              <tspan
                x={labelPos.x}
                dy={12}
                fill="#c9a84c"
                fontSize={9}
              >
                {value}
              </tspan>
            </text>
          );
        })}
      </svg>
    </div>
  );
}

export default RadarChart;
