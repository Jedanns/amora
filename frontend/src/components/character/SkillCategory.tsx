import type { CSSProperties } from 'react';

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

const ICON_MAP: Record<string, string> = {
  sparkles: '\u2728',
  swords: '\u2694',
  lock: '\u{1F512}',
  chat: '\u{1F4AC}',
  shield: '\u{1F6E1}',
  magic: '\u{1FA84}',
};

const styles = {
  container: {
    marginBottom: 8,
  } satisfies CSSProperties,

  header: (color: string): CSSProperties => ({
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '6px 10px',
    backgroundColor: '#111118',
    borderLeft: `4px solid ${color}`,
    borderRadius: '0 4px 4px 0',
  }),

  headerIcon: {
    fontSize: 14,
    lineHeight: 1,
    flexShrink: 0,
  } satisfies CSSProperties,

  headerName: {
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: '0.08em',
    color: '#e8e8f0',
    textTransform: 'uppercase' as const,
  } satisfies CSSProperties,

  skillList: {
    padding: '4px 0',
  } satisfies CSSProperties,

  skillRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '4px 10px',
    minHeight: 28,
  } satisfies CSSProperties,

  modifierBase: (modifier: number): CSSProperties => {
    const isPositive = modifier >= 0;
    const isExceptional = modifier >= 5 || modifier <= -3;
    const color = isPositive ? '#53d769' : '#e94560';

    return {
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      minWidth: 32,
      fontSize: 12,
      fontWeight: 700,
      fontFamily: "'Cascadia Code', 'Fira Code', 'Consolas', monospace",
      color,
      border: isExceptional ? '1px solid #c9a84c' : '1px solid transparent',
      borderRadius: 3,
      padding: '1px 4px',
      backgroundColor: isExceptional ? 'rgba(201, 168, 76, 0.1)' : 'transparent',
      flexShrink: 0,
    };
  },

  skillName: {
    fontSize: 12,
    color: '#e8e8f0',
    whiteSpace: 'nowrap' as const,
    overflow: 'hidden' as const,
    textOverflow: 'ellipsis' as const,
    minWidth: 0,
    flex: 1,
  } satisfies CSSProperties,

  xpSection: {
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'flex-end',
    gap: 2,
    flexShrink: 0,
    minWidth: 60,
  } satisfies CSSProperties,

  xpText: {
    fontSize: 9,
    color: '#606070',
    fontFamily: "'Cascadia Code', 'Fira Code', 'Consolas', monospace",
    letterSpacing: '0.02em',
  } satisfies CSSProperties,

  xpTrack: {
    width: 60,
    height: 3,
    backgroundColor: 'rgba(255, 255, 255, 0.06)',
    borderRadius: 2,
    overflow: 'hidden' as const,
  } satisfies CSSProperties,

  xpFill: (percent: number): CSSProperties => ({
    width: `${Math.min(100, Math.max(0, percent))}%`,
    height: '100%',
    backgroundColor: '#53d769',
    borderRadius: 2,
    transition: 'width 0.3s ease',
  }),
};

function formatModifier(value: number): string {
  return value >= 0 ? `+${value}` : `${value}`;
}

function SkillCategory({ name, icon, color, skills }: SkillCategoryProps) {
  const iconChar = ICON_MAP[icon] ?? icon;

  return (
    <div style={styles.container}>
      <div style={styles.header(color)}>
        <span style={styles.headerIcon}>{iconChar}</span>
        <span style={styles.headerName}>{name}</span>
      </div>

      <div style={styles.skillList}>
        {skills.map(skill => {
          const xpPercent = skill.max_xp > 0
            ? (skill.current_xp / skill.max_xp) * 100
            : 0;

          return (
            <div key={skill.name} style={styles.skillRow}>
              <span style={styles.modifierBase(skill.modifier)}>
                {formatModifier(skill.modifier)}
              </span>
              <span style={styles.skillName}>{skill.name}</span>
              <div style={styles.xpSection}>
                <span style={styles.xpText}>
                  {skill.current_xp}/{skill.max_xp}
                </span>
                <div style={styles.xpTrack}>
                  <div style={styles.xpFill(xpPercent)} />
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
