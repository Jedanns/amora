import { User } from 'lucide-react';
import type { CharacterAttributes, SkillCategory as SkillCategoryType } from '../../types';
import RadarChart from '../character/RadarChart';
import SkillCategory from '../character/SkillCategory';

interface CharacterTabProps {
  character: {
    name: string;
    character_class: string;
    level: number;
    experience: number;
    hp_current: number;
    hp_max: number;
    mana_current: number;
    mana_max: number;
    attributes: CharacterAttributes;
  } | null;
  skillCategories: SkillCategoryType[];
}

function xpForLevel(level: number): number {
  return level * 100;
}

function StatBar({
  label,
  current,
  max,
  color,
  prefix,
}: {
  label: string;
  current: number;
  max: number;
  color: string;
  prefix?: string;
}) {
  const percent = max > 0 ? (current / max) * 100 : 0;
  const displayValue = prefix
    ? `${prefix}  ${current}/${max}`
    : `${current}/${max}`;

  return (
    <div className="flex-1 min-w-0">
      <div className="flex justify-between items-baseline mb-[3px]">
        <span className="text-[9px] font-bold tracking-[0.1em] uppercase" style={{ color }}>{label}</span>
        <span className="text-[9px] text-text-secondary font-mono">{displayValue}</span>
      </div>
      <div className="w-full h-[5px] bg-white/[0.06] rounded-[3px] overflow-hidden">
        <div
          className="h-full rounded-[3px] transition-[width] duration-400"
          style={{
            width: `${Math.min(100, Math.max(0, percent))}%`,
            backgroundColor: color,
            boxShadow: percent > 0 ? `0 0 4px ${color}50` : 'none',
          }}
        />
      </div>
    </div>
  );
}

function CharacterTab({ character, skillCategories }: CharacterTabProps) {
  if (!character) {
    return (
      <div className="flex items-center justify-center h-full text-text-dim text-[13px] italic">
        Aucun personnage
      </div>
    );
  }

  const xpMax = xpForLevel(character.level);

  return (
    <div className="h-full overflow-y-auto px-2.5 py-3 flex flex-col gap-3">
      <div className="text-xl font-bold text-gold text-center tracking-[0.02em] leading-tight">{character.name}</div>

      <div className="flex justify-center">
        <div className="w-[120px] h-[120px] rounded-xl bg-bg-card border-2 border-border-gold flex items-center justify-center text-text-dim text-4xl select-none">
          <User size={48} className="text-text-dim" />
        </div>
      </div>

      <div className="flex justify-center">
        <span className="inline-flex items-center justify-center px-3 py-[3px] rounded-full text-[11px] font-semibold tracking-[0.04em] text-gold bg-gold/12 border border-gold/25">
          {character.character_class}
        </span>
      </div>

      <div className="flex gap-2">
        <StatBar
          label="HP"
          current={character.hp_current}
          max={character.hp_max}
          color="#e94560"
        />
        <StatBar
          label="Soul"
          current={character.mana_current}
          max={character.mana_max}
          color="#a0a0b0"
        />
        <StatBar
          label="XP"
          current={character.experience}
          max={xpMax}
          color="#a0a0b0"
          prefix={`Niv ${character.level}`}
        />
      </div>

      <RadarChart attributes={character.attributes} />

      <div className="h-px bg-border-primary my-0.5" />

      <div className="flex flex-col">
        {skillCategories.map(cat => (
          <SkillCategory
            key={cat.name}
            name={cat.name}
            icon={cat.icon}
            color={cat.color}
            skills={cat.skills}
          />
        ))}
      </div>
    </div>
  );
}

export default CharacterTab;
