/**
 * Client script for the topic timeline slider, injected via `afterDOMLoaded`.
 *
 * Everything the slider needs is already in the server-rendered DOM: each event carries its month,
 * and the range input carries the month axis. So this only adds interactivity — with JavaScript off
 * or broken, the page still shows the complete timeline.
 *
 * Written as a string because Quartz re-runs `afterDOMLoaded` on every SPA navigation, which is the
 * only way a per-page widget survives client-side routing here.
 */

export const timelineScript = `
document.querySelectorAll(".topic-timeline").forEach((root) => {
  if (root.dataset.bound === "true") return;
  root.dataset.bound = "true";

  const slider = root.querySelector('input[type="range"]');
  const readout = root.querySelector(".tt-readout strong");
  const counter = root.querySelector(".tt-readout .tt-count");
  const nowButton = root.querySelector(".tt-now");
  const items = Array.from(root.querySelectorAll("li[data-month]"));
  const ticks = Array.from(root.querySelectorAll(".tt-tick"));
  if (!slider || items.length === 0) return;

  const axis = (slider.dataset.months || "").split(",").filter(Boolean);
  if (axis.length === 0) return;

  const render = (index) => {
    const cutoff = axis[index];
    let shown = 0;
    for (const item of items) {
      const month = item.dataset.month;
      if (month > cutoff) {
        item.dataset.state = "future";
      } else {
        shown += 1;
        item.dataset.state = month === cutoff ? "current" : "past";
      }
    }
    if (readout) readout.textContent = cutoff;
    if (counter) counter.textContent = shown + " of " + items.length;
    ticks.forEach((tick, position) => {
      tick.dataset.reached = String(position <= index);
    });
    if (nowButton) nowButton.hidden = index >= axis.length - 1;
  };

  slider.addEventListener("input", () => render(Number(slider.value)));
  if (nowButton) {
    nowButton.addEventListener("click", () => {
      slider.value = String(axis.length - 1);
      render(axis.length - 1);
    });
  }
  render(Number(slider.value));
});
`
