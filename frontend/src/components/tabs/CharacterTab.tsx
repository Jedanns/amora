import type { CSSProperties } from 'react';
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

const styles = {
  wrapper: {
    height: '100%',
    overflowY: 'auto',
    padding: '12px 10px',
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  } satisfies CSSProperties,

  emptyState: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    color: '#606070',
    fontSize: 13,
    fontStyle: 'italic',
  } satisfies CSSProperties,

  name: {
    fontSize: 20,
    fontWeight: 700,
    color: '#c9a84c',
    textAlign: 'center',
    letterSpacing: '0.02em',
    lineHeight: 1.2,
  } satisfies CSSProperties,

  portraitWrapper: {
    display: 'flex',
    justifyContent: 'center',
  } satisfies CSSProperties,

  portrait: {
    width: 120,
    height: 120,
    borderRadius: 12,
    backgroundColor: '#1a1a28',
    border: '2px solid #8b7340',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#606070',
    fontSize: 36,
    userSelect: 'none',
  } satisfies CSSProperties,

  classBadgeRow: {
    display: 'flex',
    justifyContent: 'center',
  } satisfies CSSProperties,

  classBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '3px 12px',
    borderRadius: 999,
    fontSize: 11,
    fontWeight: 600,
    letterSpacing: '0.04em',
    color: '#c9a84c',
    backgroundColor: 'rgba(201, 168, 76, 0.12)',
    border: '1px solid rgba(201, 168, 76, 0.25)',
  } satisfies CSSProperties,

  statsRow: {
    display: 'flex',
    gap: 8,
  } satisfies CSSProperties,

  statBlock: {
    flex: 1,
    minWidth: 0,
  } satisfies CSSProperties,

  statLabel: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'baseline',
    marginBottom: 3,
  } satisfies CSSProperties,

  statLabelText: (color: string): CSSProperties => ({
    fontSize: 9,
    fontWeight: 700,
    letterSpacing: '0.1em',
    textTransform: 'uppercase',
    color,
  }),

  statValue: {
    fontSize: 9,
    color: '#9898a8',
    fontFamily: "'Cascadia Code', 'Fira Code', 'Consolas', monospace",
  } satisfies CSSProperties,

  statTrack: {
    width: '100%',
    height: 5,
    backgroundColor: 'rgba(255, 255, 255, 0.06)',
    borderRadius: 3,
    overflow: 'hidden',
  } satisfies CSSProperties,

  statFill: (percent: number, color: string): CSSProperties => ({
    width: `${Math.min(100, Math.max(0, percent))}%`,
    height: '100%',
    backgroundColor: color,
    borderRadius: 3,
    transition: 'width 0.4s ease',
    boxShadow: percent > 0 ? `0 0 4px ${color}50` : 'none',
  }),

  sectionDivider: {
    height: 1,
    backgroundColor: '#2a2a3a',
    margin: '2px 0',
  } satisfies CSSProperties,

  skillsSection: {
    display: 'flex',
    flexDirection: 'column',
    gap: 0,
  } satisfies CSSProperties,
};

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
    <div style={styles.statBlock}>
      <div style={styles.statLabel}>
        <span style={styles.statLabelText(color)}>{label}</span>
        <span style={styles.statValue}>{displayValue}</span>
      </div>
      <div style={styles.statTrack}>
        <div style={styles.statFill(percent, color)} />
      </div>
    </div>
  );
}

function CharacterTab({ character, skillCategories }: CharacterTabProps) {
  if (!character) {
    return (
      <div style={styles.emptyState}>
        Aucun personnage
      </div>
    );
  }

  const xpMax = xpForLevel(character.level);

  return (
    <div style={styles.wrapper}>
      <div style={styles.name}>{character.name}</div>

      <div style={styles.portraitWrapper}>
        <div style={styles.portrait}>
          <span>{'\u{1F9D9}'}</span>
        </div>
      </div>

      <div style={styles.classBadgeRow}>
        <span style={styles.classBadge}>{character.character_class}</span>
      </div>

      <div style={styles.statsRow}>
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

      <div style={styles.sectionDivider} />

      <div style={styles.skillsSection}>
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
