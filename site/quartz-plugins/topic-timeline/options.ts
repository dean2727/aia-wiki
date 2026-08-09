/**
 * Options and shared page-data types for the topic timeline.
 *
 * Kept in its own module so the transformer (`index.ts`) and the component (`component.tsx`) share
 * one definition without either importing the other.
 */

import type { TimelineEvent } from "./timeline"

export interface TopicTimelineOptions {
  /** Hide the widget on pages with fewer than this many events. */
  minEvents: number
  /** Extend the axis to the current month even when the last event is older. */
  extendToToday: boolean
  /** Heading shown above the slider. */
  title: string
}

export const defaultOptions: TopicTimelineOptions = {
  minEvents: 1,
  extendToToday: true,
  title: "Timeline",
}

export interface TimelineData {
  events: TimelineEvent[]
  /** Non-bullet lines from the section, i.e. an optional one-line arc sentence. */
  lead: string[]
}

declare module "vfile" {
  interface DataMap {
    topicTimeline: TimelineData
  }
}

/**
 * Current month as a `YYYY-MM` key.
 *
 * @returns The month key for today in UTC.
 */
export function currentMonth(): string {
  const now = new Date()
  return `${now.getUTCFullYear()}-${String(now.getUTCMonth() + 1).padStart(2, "0")}`
}
