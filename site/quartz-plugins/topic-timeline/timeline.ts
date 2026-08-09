/**
 * Parser for a wiki page's `## Timeline` section.
 *
 * The grammar is owned by `research/scripts/events.py` and documented in CLAUDE.md:
 *
 *   - `YYYY-MM` (kind) sentence — significance. [source](url)
 *
 * Only `merge_timeline.py` writes those bullets, so this parser can be strict. Anything it cannot
 * read is reported rather than guessed at, and the build carries on.
 */

export type EventKind =
  | "paper"
  | "method"
  | "release"
  | "benchmark"
  | "tooling"
  | "org"
  | "milestone"
  | "wiki"

export const EVENT_KINDS: ReadonlySet<string> = new Set<EventKind>([
  "paper",
  "method",
  "release",
  "benchmark",
  "tooling",
  "org",
  "milestone",
  "wiki",
])

export interface TimelineEvent {
  /** The label as authored, e.g. `2021-07` or `~2021`. */
  label: string
  /** Month bucket the slider files this event under, always `YYYY-MM`. */
  month: string
  year: number
  /** True when the date was inferred (a year-only, quarter, or `~`/era form). */
  approximate: boolean
  kind: EventKind
  text: string
  significance: string
  sources: string[]
}

export interface ParsedTimeline {
  events: TimelineEvent[]
  /** Non-bullet lines in the section, i.e. an optional one-line arc sentence. */
  lead: string[]
  problems: string[]
}

const TIMELINE_HEADING = /^##\s+Timeline\s*$/
const NEXT_SECTION = /^##\s+/
const BULLET = /^-\s+`([^`]+)`\s+\(([a-z]+)\)\s+(.+?)\s*$/
const SOURCE_LINK = /\[source\]\(([^)\s]+)\)/g
const DATE = /^(~|c\.?\s*|circa\s+|early[-\s]|mid[-\s]|late[-\s])?(\d{4})(?:[-/](?:Q([1-4])|(\d{1,2})))?(?:[-/](\d{1,2}))?$/i
const ERA_MONTHS: Record<string, number> = { early: 2, mid: 6, late: 10 }
const SIGNIFICANCE_SEPARATOR = " — "

interface ParsedDate {
  label: string
  month: string
  year: number
  approximate: boolean
}

/**
 * Parse the partial date forms the event grammar allows.
 *
 * @param raw - The backticked date from a bullet.
 * @returns The parsed date, or null when it does not match the grammar.
 */
export function parseEventDate(raw: string): ParsedDate | null {
  const match = DATE.exec(raw.trim())
  if (!match) return null

  const [, approxToken, yearText, quarter, monthText, dayText] = match
  const year = Number(yearText)
  const era = (approxToken ?? "").trim().replace(/[-.\s]+$/, "").toLowerCase()
  let approximate = Boolean(era)
  let month = monthText ? Number(monthText) : undefined

  if (quarter) {
    month = (Number(quarter) - 1) * 3 + 2 // Mid-quarter, so ordering stays sane.
    approximate = true
  } else if (era in ERA_MONTHS) {
    month = ERA_MONTHS[era]
  }

  const day = dayText ? Number(dayText) : undefined
  if ((month !== undefined && (month < 1 || month > 12)) || (day !== undefined && (day < 1 || day > 31))) {
    return null
  }

  let label = String(year).padStart(4, "0")
  if (month !== undefined) label += `-${String(month).padStart(2, "0")}`
  if (day !== undefined) label += `-${String(day).padStart(2, "0")}`

  return {
    label: approximate ? `~${label}` : label,
    month: `${String(year).padStart(4, "0")}-${String(month ?? 1).padStart(2, "0")}`,
    year,
    approximate,
  }
}

/**
 * Locate the `## Timeline` section in a page's raw markdown.
 *
 * @param source - Full markdown source of the page.
 * @returns Zero-based line bounds of the section including its heading, or null when absent.
 */
export function findSection(source: string): { start: number; end: number } | null {
  const lines = source.split("\n")
  const start = lines.findIndex((line) => TIMELINE_HEADING.test(line.trim()))
  if (start === -1) return null

  let end = lines.length
  for (let index = start + 1; index < lines.length; index++) {
    if (NEXT_SECTION.test(lines[index])) {
      end = index
      break
    }
  }
  return { start, end }
}

/**
 * Parse a page's Timeline section into events, oldest first.
 *
 * @param source - Full markdown source of the page.
 * @returns The parsed timeline; empty when the page has no Timeline section.
 */
export function parseTimeline(source: string): ParsedTimeline {
  const bounds = findSection(source)
  const result: ParsedTimeline = { events: [], lead: [], problems: [] }
  if (!bounds) return result

  const lines = source.split("\n").slice(bounds.start + 1, bounds.end)
  for (const raw of lines) {
    const line = raw.trim()
    if (!line) continue

    if (!line.startsWith("- ")) {
      result.lead.push(line)
      continue
    }

    const match = BULLET.exec(line)
    if (!match) {
      result.problems.push(`unreadable bullet: ${line.slice(0, 80)}`)
      continue
    }

    const [, dateText, kind, rest] = match
    const date = parseEventDate(dateText)
    if (!date) {
      result.problems.push(`unreadable date \`${dateText}\``)
      continue
    }
    if (!EVENT_KINDS.has(kind)) {
      result.problems.push(`unknown kind (${kind})`)
      continue
    }

    const sources = [...rest.matchAll(SOURCE_LINK)].map((source) => source[1])
    const body = rest.replace(SOURCE_LINK, "").trim()
    const separator = body.indexOf(SIGNIFICANCE_SEPARATOR)
    const text = separator === -1 ? body : body.slice(0, separator)
    const significance = separator === -1 ? "" : body.slice(separator + SIGNIFICANCE_SEPARATOR.length)

    result.events.push({
      label: date.label,
      month: date.month,
      year: date.year,
      approximate: date.approximate,
      kind: kind as EventKind,
      text: text.trim(),
      significance: significance.trim(),
      sources: [...new Set(sources)],
    })
  }

  result.events.sort((left, right) => left.month.localeCompare(right.month) || left.text.localeCompare(right.text))
  return result
}

/**
 * List every month from the first event to the last, inclusive, with no gaps.
 *
 * The slider needs a continuous axis so that a quiet stretch reads as a quiet stretch rather than
 * being compressed away.
 *
 * @param events - Parsed events, in any order.
 * @param through - Optional `YYYY-MM` to extend the axis to, normally the current month.
 * @returns Ascending `YYYY-MM` keys, empty when there are no events.
 */
export function monthAxis(events: TimelineEvent[], through?: string): string[] {
  if (events.length === 0) return []

  const months = events.map((event) => event.month).sort()
  const last = through && through > months[months.length - 1] ? through : months[months.length - 1]
  const [startYear, startMonth] = months[0].split("-").map(Number)
  const [endYear, endMonth] = last.split("-").map(Number)

  const axis: string[] = []
  for (let year = startYear, month = startMonth; year < endYear || (year === endYear && month <= endMonth); ) {
    axis.push(`${String(year).padStart(4, "0")}-${String(month).padStart(2, "0")}`)
    month += 1
    if (month > 12) {
      month = 1
      year += 1
    }
  }
  return axis
}
