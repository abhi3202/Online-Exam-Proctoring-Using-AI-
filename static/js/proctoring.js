// Proctoring JavaScript - Load immediately
(function() {
    console.log("Proctoring.js loaded");
    
    // Tab switch tracking
    let tabSwitchCount = 0;
    let isShowingWarning = false;
    let warningTimeout = null;
    
    // Get student and exam IDs from page
    const studentIdElement = document.getElementById("student-id");
    const examIdElement = document.getElementById("exam-id");
    const studentId = studentIdElement ? studentIdElement.textContent : null;
    const examId = examIdElement ? examIdElement.textContent : null;
    
    // Function to log tab switch to server
    function logTabSwitchToServer(count) {
        if (!studentId || !examId) {
            console.warn("Cannot log tab switch: missing student or exam ID");
            return;
        }
        
        fetch(`/log_tab_switch/${studentId}/${examId}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ switch_count: count })
        })
        .then(response => response.json())
        .then(data => {
            console.log("Tab switch logged to server:", data);
        })
        .catch(error => {
            console.error("Error logging tab switch:", error);
        });
    }
    
    // Exam timer - COUNTDOWN from 60 seconds
    const timerEl = document.getElementById("exam-timer");
    const EXAM_DURATION_SECONDS = 120;  // 2 minutes exam
    let remainingSeconds = EXAM_DURATION_SECONDS;
    let timerInterval = null;
    let isSubmitted = false;

    function updateTimer() {
        console.log("Timer tick, remaining:", remainingSeconds);
        
        if (remainingSeconds <= 0) {
            // Time's up - stop timer FIRST
            if (timerInterval) {
                clearInterval(timerInterval);
                timerInterval = null;
                console.log("Timer interval cleared");
            }
            
            // Only submit once
            if (!isSubmitted) {
                isSubmitted = true;
                console.log("Calling submitExamDirectly");
                
                // Small delay to let the alert complete
                setTimeout(() => {
                    if (typeof window.submitExamDirectly === 'function') {
                        console.log("Executing submit");
                        window.submitExamDirectly();
                    } else {
                        console.error("submitExamDirectly not found on window!");
                        const submitBtn = document.getElementById("submit-btn");
                        if (submitBtn) {
                            console.log("Falling back to button click");
                            submitBtn.click();
                        } else {
                            alert("Error: Submit function not found. Please click Submit manually.");
                        }
                    }
                }, 100);
            }
            return;
        }

        remainingSeconds--;
        
        const m = String(Math.floor(remainingSeconds / 60)).padStart(2, "0");
        const s = String(remainingSeconds % 60).padStart(2, "0");
        
        if (timerEl) {
            timerEl.textContent = `${m}:${s}`;
            
            // Change color when time is running low (less than 10 seconds)
            if (remainingSeconds < 10) {
                timerEl.style.color = "red";
            }
        }
    }
    
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', startTimer);
    } else {
        startTimer();
    }

    function startTimer() {
        // Update immediately, then every second
        updateTimer();
        timerInterval = setInterval(updateTimer, 1000);
        console.log("Timer started");
    }

    // Show warning with delay to prevent loop
    function showWarning(message) {
        // Prevent multiple warnings at once
        if (isShowingWarning) return;
        
        isShowingWarning = true;
        
        // Clear any pending warning
        if (warningTimeout) {
            clearTimeout(warningTimeout);
        }
        
        // Delay showing warning to avoid triggering visibility change
        warningTimeout = setTimeout(() => {
            alert(message);
            // Reset flag after alert is closed
            setTimeout(() => {
                isShowingWarning = false;
            }, 500);
        }, 100);
    }

    // Detect when student switches tab / minimizes window
    function handleVisibilityChange() {
        // Skip if already showing a warning
        if (isShowingWarning) return;
        
        if (document.hidden) {
            // User has left the exam tab/window
            tabSwitchCount++;
            
            console.warn("Tab/window hidden! Switch count:", tabSwitchCount);
            
            // Logic: 1 = warning 1, 2 = warning 2, 3+ = violation
            let message = "";
            let shouldLogViolation = false;
            
            if (tabSwitchCount === 1) {
                // First tab switch - warning 1
                message = "WARNING 1: You have left the exam tab!\n\n" +
                          "Please stay on the exam page.\n" +
                          "(1 more warning allowed)";
            } else if (tabSwitchCount === 2) {
                // Second tab switch - warning 2
                message = "WARNING 2: This is your FINAL warning!\n\n" +
                          "You have left the exam tab again.\n" +
                          "Next tab switch will be recorded as a VIOLATION!";
            } else if (tabSwitchCount >= 3) {
                // Third+ tab switch - violation
                message = "VIOLATION RECORDED!\n\n" +
                          "You have switched tabs " + tabSwitchCount + " times.\n" +
                          "This has been recorded as a VIOLATION in your exam report.";
                shouldLogViolation = true;
            }
            
            if (message) {
                showWarning(message);
            }
            
            // Log violation to server only after 3+ switches
            if (shouldLogViolation) {
                logTabSwitchToServer(tabSwitchCount);
                console.log("VIOLATION LOGGED: Tab switch #" + tabSwitchCount);
            }
        }
    }

    // Listen for visibility changes
    document.addEventListener("visibilitychange", handleVisibilityChange);
    
    // Window blur detection (less aggressive, just log)
    window.addEventListener("blur", function() {
        console.warn("Window lost focus!");
    });

    // Prevent right-click context menu
    document.addEventListener("contextmenu", function(e) {
        e.preventDefault();
        return false;
    });

    // Prevent keyboard shortcuts
    document.addEventListener("keydown", function(e) {
        if (e.ctrlKey && ['u', 'c', 'p', 's', 'a', 'i'].includes(e.key.toLowerCase())) {
            e.preventDefault();
            return false;
        }
        
        if (e.key === 'F12') {
            e.preventDefault();
            return false;
        }
    });
    
    // ============ GAZE WARNING POLLING ============
    // Poll for gaze warnings and show popup messages
    let lastWarningTypes = [];
    const WARNING_MESSAGES = {
        "EYES_CLOSED": "⚠️ Please open your eyes!",
        "LOOKING_AWAY": "⚠️ Please look at the screen!",
        "HEAD_TURNED_AWAY": "⚠️ Please face the camera!"
    };
    
    function pollForWarnings() {
        fetch("/get_warnings")
            .then(response => response.json())
            .then(data => {
                if (data.status === "ok" && data.warnings && data.warnings.length > 0) {
                    const currentWarnings = data.warnings;
                    
                    // Check if there are new warnings
                    const newWarnings = currentWarnings.filter(w => !lastWarningTypes.includes(w));
                    
                    if (newWarnings.length > 0) {
                        // Build message for all current warnings
                        const warningMessages = currentWarnings
                            .map(w => WARNING_MESSAGES[w] || `⚠️ ${w}`)
                            .join("\n");
                        
                        // Show popup (non-blocking alert with custom UI would be better, but alert works)
                        showGazeWarning(warningMessages);
                    }
                    
                    lastWarningTypes = currentWarnings;
                } else {
                    // No warnings - reset
                    lastWarningTypes = [];
                }
            })
            .catch(err => {
                // Silently ignore errors - don't flood console
            });
    }
    
    function showGazeWarning(message) {
        // Create a custom warning overlay instead of alert
        const existingWarning = document.getElementById('gaze-warning-overlay');
        if (existingWarning) {
            existingWarning.remove();
        }
        
        const overlay = document.createElement('div');
        overlay.id = 'gaze-warning-overlay';
        overlay.innerHTML = `
            <div style="
                position: fixed;
                top: 20px;
                right: 20px;
                background: linear-gradient(135deg, #ff9800, #f57c00);
                color: white;
                padding: 15px 25px;
                border-radius: 10px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.3);
                z-index: 10000;
                font-family: Arial, sans-serif;
                font-size: 16px;
                max-width: 350px;
                animation: slideIn 0.3s ease-out;
            ">
                <div style="font-weight: bold; margin-bottom: 5px;">⚠️ Attention Required</div>
                <div style="white-space: pre-line;">${message}</div>
            </div>
            <style>
                @keyframes slideIn {
                    from { transform: translateX(400px); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
            </style>
        `;
        document.body.appendChild(overlay);
        
        // Auto-hide after 3 seconds
        setTimeout(() => {
            if (overlay && overlay.parentNode) {
                overlay.style.animation = 'slideOut 0.3s ease-in';
                setTimeout(() => {
                    if (overlay.parentNode) {
                        overlay.remove();
                    }
                }, 300);
            }
        }, 3000);
    }
    
    // Add CSS for slideOut animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(400px); opacity: 0; }
        }
    `;
    document.head.appendChild(style);
    
    // Start polling for warnings every 2 seconds when on exam page
    if (document.getElementById('exam-timer') || document.querySelector('.exam-container')) {
        setInterval(pollForWarnings, 2000);
    }
})();