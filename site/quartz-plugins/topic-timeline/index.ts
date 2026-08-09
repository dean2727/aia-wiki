/**
 * Topic timeline: renders a wiki page's `## Timeline` section as a month slider.
 *
 * A page reads as the current state of affairs. Scrubbing the slider walks the topic's history:
 * events after the selected month dim, the selected month highlights. The default position is the
 * most recent month, so at rest the page looks exactly as it did before this plugin existed.
 *
 * Local plugin, loaded from source by tsx. Two parts:
 *   - a transformer that parses the section into page data and removes it from the rendered body,
 *     so the section is not shown twice
 *   - an `afterBody` component (see `component.tsx`) that renders the slider plus the event list
 *
 * The list is server-rendered, so the timeline is complete and readable with JavaScript disabled.
 */

import type { QuartzTransformerPlugin } from "../../quartz/plugins/types"
import { parseTimeline } from "./timeline"
import { defaultOptions, type TopicTimelineOptions } from "./options"

export { TopicTimeline } from "./component"
export type { TopicTimelineOptions } from "./options"

/**
 * Drop the `## Timeline` section from an mdast tree.
 *
 * The component re-renders those events itself, so leaving the original list in the body would show
 * every event twice.
 *
 * @param tree - The page's mdast root.
 */
function removeTimelineSection(tree: { children: { type: string; depth?: number; children?: unknown[] }[] }): void {
  const start = tree.children.findIndex(
    (node) =>
      node.type === "heading" && node.depth === 2 && JSON.stringify(node.children ?? []).includes('"Timeline"'),
  )
  if (start === -1) return

  let end = tree.children.length
  for (let index = start + 1; index < tree.children.length; index++) {
    const node = tree.children[index]
    if (node.type === "heading" && (node.depth ?? 6) <= 2) {
      end = index
      break
    }
  }
  tree.children.splice(start, end - start)
}

export const TopicTimelineTransformer: QuartzTransformerPlugin<Partial<TopicTimelineOptions>> = (userOpts) => {
  const opts = { ...defaultOptions, ...userOpts }
  return {
    name: "TopicTimeline",
    markdownPlugins() {
      return [
        () => (tree: never, file: { value?: unknown; data: Record<string, unknown> }) => {
          const parsed = parseTimeline(String(file.value ?? ""))
          for (const problem of parsed.problems) {
            console.warn(`TopicTimeline: ${String(file.data.filePath ?? "?")} — ${problem}`)
          }
          if (parsed.events.length < opts.minEvents) return

          file.data.topicTimeline = { events: parsed.events, lead: parsed.lead }
          removeTimelineSection(tree as unknown as Parameters<typeof removeTimelineSection>[0])
        },
      ]
    },
  }
}

export const manifest = {
  name: "topic-timeline",
  displayName: "Topic Timeline",
  description: "Renders a page's ## Timeline section as a scrubable month slider.",
  version: "1.0.0",
  category: ["transformer", "component"] as const,
  quartzVersion: ">=5.0.0",
  defaultOrder: 55,
  defaultEnabled: true,
  defaultOptions,
  components: {
    TopicTimeline: {
      name: "TopicTimeline",
      displayName: "Topic Timeline",
      description: "Month slider over a topic's dated events.",
      version: "1.0.0",
      defaultPosition: "afterBody",
      defaultPriority: 5,
    },
  },
}

export default TopicTimelineTransformer
