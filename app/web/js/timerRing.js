(function () {
  const R = 104;
  const CIRCUMFERENCE = 2 * Math.PI * R;

  function init(circleEl) {
    circleEl.style.strokeDasharray = `${CIRCUMFERENCE}`;
    circleEl.style.strokeDashoffset = `${CIRCUMFERENCE}`;
  }

  function setProgress(circleEl, fraction) {
    const f = Math.max(0, Math.min(1, fraction));
    circleEl.style.strokeDashoffset = `${CIRCUMFERENCE * (1 - f)}`;
  }

  function pad2(n) {
    return String(Math.floor(n)).padStart(2, "0");
  }

  function formatDuration(totalSeconds, withSign) {
    const sign = totalSeconds < 0 ? "-" : withSign ? "+" : "";
    const abs = Math.abs(Math.floor(totalSeconds));
    const h = Math.floor(abs / 3600);
    const m = Math.floor((abs % 3600) / 60);
    const s = abs % 60;
    return `${sign}${pad2(h)}:${pad2(m)}:${pad2(s)}`;
  }

  window.WT = window.WT || {};
  window.WT.timerRing = { init, setProgress, formatDuration, CIRCUMFERENCE };
})();
