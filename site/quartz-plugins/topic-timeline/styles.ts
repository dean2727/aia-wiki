/**
 * Styles for the topic timeline slider.
 *
 * Kept as a plain string rather than an `.scss` import: this plugin is loaded straight from source
 * by tsx, so it must not depend on the sass loader that the published plugins build with.
 */

export const timelineStyles = `
.topic-timeline {
  margin-top: 2rem;
  border-top: 1px solid var(--lightgray);
  padding-top: 1rem;
}

.topic-timeline > header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.topic-timeline h2 {
  margin: 0;
  font-size: 1.1rem;
}

.topic-timeline .tt-readout {
  font-family: var(--codeFont);
  font-size: 0.8rem;
  color: var(--gray);
}

.topic-timeline .tt-readout strong {
  color: var(--secondary);
}

.topic-timeline .tt-lead {
  margin: 0.4rem 0 0;
  font-size: 0.9rem;
  color: var(--darkgray);
}

.topic-timeline .tt-control {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin: 0.9rem 0 0.25rem;
}

.topic-timeline input[type="range"] {
  flex: 1;
  accent-color: var(--secondary);
  cursor: pointer;
}

.topic-timeline .tt-now {
  font-size: 0.75rem;
  padding: 0.2rem 0.6rem;
  border: 1px solid var(--lightgray);
  border-radius: 4px;
  background: var(--light);
  color: var(--darkgray);
  cursor: pointer;
}

.topic-timeline .tt-now[hidden] {
  display: none;
}

.topic-timeline .tt-ticks {
  display: flex;
  gap: 1px;
  height: 6px;
  margin-bottom: 0.75rem;
}

.topic-timeline .tt-tick {
  flex: 1;
  border-radius: 1px;
  background: var(--lightgray);
}

.topic-timeline .tt-tick[data-populated="true"] {
  background: var(--tertiary);
}

.topic-timeline ol {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.topic-timeline li {
  display: grid;
  grid-template-columns: 5.5rem 1fr;
  gap: 0.75rem;
  padding: 0.4rem 0.5rem;
  border-left: 2px solid var(--lightgray);
  border-radius: 0 3px 3px 0;
  transition: opacity 0.15s ease, background 0.15s ease;
}

.topic-timeline li[data-state="future"] {
  opacity: 0.32;
}

.topic-timeline li[data-state="current"] {
  background: var(--highlight);
  border-left-color: var(--secondary);
}

.topic-timeline .tt-when {
  font-family: var(--codeFont);
  font-size: 0.75rem;
  color: var(--gray);
  padding-top: 0.15rem;
}

.topic-timeline .tt-kind {
  display: inline-block;
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--gray);
  margin-right: 0.4rem;
}

.topic-timeline .tt-significance {
  display: block;
  font-size: 0.85rem;
  color: var(--darkgray);
  margin-top: 0.15rem;
}

.topic-timeline .tt-sources {
  font-size: 0.75rem;
  margin-left: 0.35rem;
}

.topic-timeline .tt-empty {
  font-size: 0.9rem;
  color: var(--gray);
}

@media (max-width: 600px) {
  .topic-timeline li {
    grid-template-columns: 1fr;
    gap: 0.15rem;
  }
}
`
