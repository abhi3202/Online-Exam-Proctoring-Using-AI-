document.addEventListener("DOMContentLoaded", () => {
    // Simple exam timer (minutes:seconds)
    const timerEl = document.getElementById("exam-timer");
    let seconds = 0;

    function updateTimer() {
        seconds += 1;
        const m = String(Math.floor(seconds / 60)).padStart(2, "0");
        const s = String(seconds % 60).padStart(2, "0");
        if (timerEl) {
            timerEl.textContent = `${m}:${s}`;
        }
    }
    setInterval(updateTimer, 1000);

    // Detect when student switches tab / minimizes
    document.addEventListener("visibilitychange", () => {
        if (document.hidden) {
            console.warn("Tab hidden: possible focus loss.");
            alert("Please stay on the exam tab. Your activity is being monitored.");
        }
    });
});
