import type { ComponentType } from 'react';
import { Sparkles, Sword, Lock, MessageCircle, Shield, Wand2 } from 'lucide-react';

interface SkillCategoryProps {
  name: string;
  icon: string;
  color: string;
  skills: Array<{
    name: string;
    modifier: number;
    current_xp: number;
    max_xp: number;
  }>;
}

const ICON_MAP: Record<string, ComponentType<{ size?: number; className?: string }>> = {
  sparkles: Sparkles,
  swords: Sword,
  lock: Lock,
  chat: MessageCircle,
  shield: Shield,
  magic: Wand2,
};

function formatModifier(value: number): string {
  return value >= 0 ? `+${value}` : `${value}`;
}

function SkillCategory({ name, icon, color, skills }: SkillCategoryProps) {
  const Icon = ICON_MAP[icon];

  return (
    <div className="mb-2">
      <div
        className="flex items-center gap-2 px-2.5 py-1.5 bg-bg-secondary rounded-r-sm border-l-4"
        style={{ borderLeftColor: color }}
      >
        {Icon && <span className="shrink-0" style={{ color }}><Icon size={14} /></span>}
        <span className="text-[11px] font-bold tracking-[0.08em] uppercase text-text-primary">{name}</span>
      </div>

      <div className="py-1">
        {skills.map(skill => {
          const xpPercent = skill.max_xp > 0
            ? (skill.current_xp / skill.max_xp) * 100
            : 0;
          const isPositive = skill.modifier >= 0;
          const isExceptional = skill.modifier >= 5 || skill.modifier <= -3;

          return (
            <div key={skill.name} className="flex items-center gap-2 px-2.5 py-1 min-h-[28px]">
              <span
                className={`inline-flex items-center justify-center min-w-[32px] text-xs font-bold font-mono rounded-[3px] px-1 py-px shrink-0 ${
                  isExceptional
                    ? 'border border-gold bg-gold/10'
                    : 'border border-transparent'
                }`}
                style={{ color: isPositive ? '#53d769' : '#e94560' }}
              >
                {formatModifier(skill.modifier)}
              </span>
              <span className="text-xs text-text-primary whitespace-nowrap overflow-hidden text-ellipsis min-w-0 flex-1">
                {skill.name}
              </span>
              <div className="flex flex-col items-end gap-0.5 shrink-0 min-w-[60px]">
                <span className="text-[9px] text-text-dim font-mono tracking-[0.02em]">
                  {skill.current_xp}/{skill.max_xp}
                </span>
                <div className="w-[60px] h-[3px] bg-white/[0.06] rounded-sm overflow-hidden">
                  <div
                    className="h-full bg-green rounded-sm transition-[width] duration-300"
                    style={{ width: `${Math.min(100, Math.max(0, xpPercent))}%` }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default SkillCategory;
