import type { ReactNode } from 'react';

export interface GameKeywords {
  playerName?: string;
  npcNames: string[];
  locations: string[];
  items: string[];
  factions: string[];
}

interface HighlightRule {
  pattern: RegExp;
  style: React.CSSProperties;
}

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function buildRules(keywords: GameKeywords): HighlightRule[] {
  const rules: HighlightRule[] = [];

  rules.push({
    pattern: /"[^"]*"/g,
    style: { color: '#f0c060', fontStyle: 'italic' },
  });

  rules.push({
    pattern: /\b\d*[dD](4|6|8|10|12|20|100)\b/g,
    style: { color: '#c9a84c', fontWeight: 700 },
  });

  if (keywords.playerName) {
    rules.push({
      pattern: new RegExp(`\\b${escapeRegex(keywords.playerName)}\\b`, 'gi'),
      style: { color: '#c9a84c', fontWeight: 700 },
    });
  }

  for (const name of keywords.npcNames) {
    if (!name) continue;
    rules.push({
      pattern: new RegExp(`\\b${escapeRegex(name)}\\b`, 'gi'),
      style: { color: '#e94560', fontWeight: 700 },
    });
  }

  for (const loc of keywords.locations) {
    if (!loc) continue;
    rules.push({
      pattern: new RegExp(`\\b${escapeRegex(loc)}\\b`, 'gi'),
      style: { color: '#53d769', fontWeight: 700 },
    });
  }

  for (const item of keywords.items) {
    if (!item) continue;
    rules.push({
      pattern: new RegExp(`\\b${escapeRegex(item)}\\b`, 'gi'),
      style: { color: '#4a9eff', fontWeight: 700 },
    });
  }

  for (const faction of keywords.factions) {
    if (!faction) continue;
    rules.push({
      pattern: new RegExp(`\\b${escapeRegex(faction)}\\b`, 'gi'),
      style: { color: '#c9a84c', fontWeight: 700, textDecoration: 'underline' },
    });
  }

  return rules;
}

interface Segment {
  text: string;
  style?: React.CSSProperties;
}

function applyRule(segments: Segment[], rule: HighlightRule): Segment[] {
  const result: Segment[] = [];

  for (const seg of segments) {
    if (seg.style) {
      result.push(seg);
      continue;
    }

    const text = seg.text;
    let lastIndex = 0;

    const regex = new RegExp(rule.pattern.source, rule.pattern.flags);
    let match: RegExpExecArray | null;

    while ((match = regex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        result.push({ text: text.slice(lastIndex, match.index) });
      }
      result.push({ text: match[0], style: rule.style });
      lastIndex = regex.lastIndex;
      if (match[0].length === 0) {
        regex.lastIndex++;
      }
    }

    if (lastIndex < text.length) {
      result.push({ text: text.slice(lastIndex) });
    }
  }

  return result;
}

export function highlightNarrative(text: string, keywords: GameKeywords): ReactNode {
  const rules = buildRules(keywords);
  let segments: Segment[] = [{ text }];

  for (const rule of rules) {
    segments = applyRule(segments, rule);
  }

  if (segments.length === 1 && !segments[0].style) {
    return text;
  }

  return segments.map((seg, i) =>
    seg.style ? (
      <span key={i} style={seg.style}>{seg.text}</span>
    ) : (
      <span key={i}>{seg.text}</span>
    ),
  );
}

interface LearnedKeywords {
  npcNames: string[];
  items: string[];
  locations: string[];
}

export function learnKeywords(text: string): LearnedKeywords {
  const npcNames: string[] = [];
  const items: string[] = [];
  const locations: string[] = [];

  const npcPatterns = [
    /[Jj]e m'appelle (\p{Lu}\p{L}+)/gu,
    /[Jj]e suis (\p{Lu}\p{L}+)/gu,
    /(?:nomm[ée]e?|appel[ée]e?) (\p{Lu}\p{L}+)/gu,
  ];

  for (const pat of npcPatterns) {
    const regex = new RegExp(pat.source, pat.flags);
    let m: RegExpExecArray | null;
    while ((m = regex.exec(text)) !== null) {
      const name = m[1];
      if (name && name.length > 2 && !npcNames.includes(name)) {
        npcNames.push(name);
      }
    }
  }

  const itemPatterns = [
    /(?:une?|le|la|l') ([\p{L}]+ (?:enchant[ée]e?|magique|l[ée]gendaire|maudit[e]?))/giu,
    /(?:une?) ([\p{L}]+(?:\s[\p{L}]+)?) (?:en (?:fer|acier|or|argent|mithril))/giu,
    /(?:une?) (?:potion|epee|ep[ée]e|dague|arc|bouclier|armure|anneau|amulette|baton|b[aâ]ton|parchemin|grimoire)/giu,
  ];

  for (const pat of itemPatterns) {
    const regex = new RegExp(pat.source, pat.flags);
    let m: RegExpExecArray | null;
    while ((m = regex.exec(text)) !== null) {
      const item = m[1] ?? m[0];
      const cleaned = item.replace(/^(?:une?|le|la|l')\s*/i, '').trim();
      if (cleaned.length > 2 && !items.includes(cleaned)) {
        items.push(cleaned);
      }
    }
  }

  const locPatterns = [
    /(?:la|le|l'|au|du) ((?:taverne|for[eê]t|donjon|cit[ée]|village|ch[aâ]teau|temple|grotte|montagne|rivi[eè]re|lac|march[ée])(?:\s+[\p{L}]+(?:\s+[\p{L}]+)?)?)/giu,
    /(?:[àa]|vers|dans) (\p{Lu}\p{L}+(?:\s+\p{Lu}\p{L}+)*)/gu,
  ];

  for (const pat of locPatterns) {
    const regex = new RegExp(pat.source, pat.flags);
    let m: RegExpExecArray | null;
    while ((m = regex.exec(text)) !== null) {
      const loc = m[1];
      if (loc && loc.length > 2 && !locations.includes(loc)) {
        locations.push(loc);
      }
    }
  }

  return { npcNames, items, locations };
}
