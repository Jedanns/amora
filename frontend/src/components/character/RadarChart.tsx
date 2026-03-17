import type { ComponentType } from 'react';
import { Sword, Swords, Heart, Brain, Eye, Sparkles } from 'lucide-react';
import type { CharacterAttributes } from '../../types';

interface RadarChartProps {
  attributes: CharacterAttributes;
  maxValue?: number;
  size?: number;
}

const ATTRIBUTE_CONFIG: Array<{
  key: keyof CharacterAttributes;
  label: string;
  icon: ComponentType<{ size?: number; className?: string }>;
}> = [
  { key: 'strength', label: 'FOR', icon: Sword },
  { key: 'dexterity', label: 'DEX', icon: Swords },
  { key: 'constitution', label: 'CON', icon: Heart },
  { key: 'intelligence', label: 'INT', icon: Brain },
  { key: 'wisdom', label: 'SAG', icon: Eye },
  { key: 'charisma', label: 'CHA', icon: Sparkles },
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

  return (
    <div className="flex justify-center items-center py-1">
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="overflow-visible"
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
          const Icon = attr.icon;
          const iconSize = 20;
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
              <foreignObject
                x={iconPos.x - iconSize / 2}
                y={iconPos.y - iconSize / 2}
                width={iconSize}
                height={iconSize}
              >
                <div className="flex items-center justify-center w-full h-full">
                  <Icon size={10} className="text-gold" />
                </div>
              </foreignObject>
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
