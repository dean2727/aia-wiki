/**
 * The topic timeline component: a month slider over a page's dated events.
 *
 * Split out of `index.ts` because the plugin is loaded straight from source by tsx, which only
 * parses JSX in a `.tsx` file.
 */

import type { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../../quartz/components/types"
import { monthAxis, type TimelineEvent } from "./timeline"
import { timelineStyles } from "./styles"
import { timelineScript } from "./slider"
import { type TimelineData, type TopicTimelineOptions, currentMonth, defaultOptions } from "./options"

export const TopicTimeline: QuartzComponentConstructor<Partial<TopicTimelineOptions>> = (userOpts) => {
  const opts = { ...defaultOptions, ...(userOpts ?? {}) }

  const Timeline: QuartzComponent = ({ fileData }: QuartzComponentProps) => {
    const data = fileData.topicTimeline as TimelineData | undefined
    if (!data || data.events.length < opts.minEvents) return null

    const axis = monthAxis(data.events, opts.extendToToday ? currentMonth() : undefined)
    const latest = axis[axis.length - 1]
    const populated = new Set(data.events.map((event) => event.month))

    return (
      <section class="topic-timeline">
        <header>
          <h2>{opts.title}</h2>
          <span class="tt-readout">
            <strong>{latest}</strong> · <span class="tt-count">{`${data.events.length} of ${data.events.length}`}</span>
          </span>
        </header>

        {data.lead.map((line) => (
          <p class="tt-lead">{line.replace(/^_|_$/g, "")}</p>
        ))}

        <div class="tt-control">
          <input
            type="range"
            min={0}
            max={axis.length - 1}
            value={axis.length - 1}
            step={1}
            data-months={axis.join(",")}
            aria-label={`Scrub this topic's history, ${axis[0]} to ${latest}`}
          />
          <button class="tt-now" type="button" hidden>
            now
          </button>
        </div>

        <div class="tt-ticks" aria-hidden="true">
          {axis.map((month) => (
            <span class="tt-tick" data-populated={String(populated.has(month))} title={month} />
          ))}
        </div>

        <ol>
          {data.events.map((event) => (
            <li data-month={event.month} data-state="past">
              <span class="tt-when">{event.label}</span>
              <span class="tt-what">
                <span class="tt-kind">{event.kind}</span>
                {event.text}
                {event.sources.map((url, index) => (
                  <a class="tt-sources" href={url} target="_blank" rel="noopener noreferrer">
                    {`[${index + 1}]`}
                  </a>
                ))}
                {event.significance ? <span class="tt-significance">{event.significance}</span> : null}
              </span>
            </li>
          ))}
        </ol>
      </section>
    )
  }

  Timeline.displayName = "TopicTimeline"
  Timeline.css = timelineStyles
  Timeline.afterDOMLoaded = timelineScript
  return Timeline
}
