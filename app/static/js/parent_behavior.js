// --- DOM Elements ---
const logBehaviorForm = document.getElementById('log-behavior-form');
const childSelectBehavior = document.getElementById('behavior-child-select');
const behaviorLogListDiv = document.getElementById('behavior-log-list');
const messageAreaBehavior = document.getElementById('message-area-behavior');

// --- Utility Functions ---
function displayBehaviorMessage(message, type = 'danger') {
    if (messageAreaBehavior) {
        messageAreaBehavior.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
    } else {
        console.error("Message area for behavior logging not found.");
        alert(message); // Fallback
    }
}

// --- API Calls and Data Handling ---

// Populate Children Select Dropdown
async function populateChildrenSelectBehavior() {
    if (!childSelectBehavior) return;

    try {
        const response = await fetch('/api/parent/children');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const children = await response.json();
        
        childSelectBehavior.innerHTML = '<option value="">-- Select Child --</option>'; // Reset
        children.forEach(child => {
            const option = document.createElement('option');
            option.value = child.id;
            option.textContent = child.username;
            childSelectBehavior.appendChild(option);
        });
    } catch (error) {
        console.error('Error fetching children:', error);
        displayBehaviorMessage('Could not load children for selection.', 'warning');
    }
}

// Handle Log Behavior Form Submission
async function handleLogBehavior(event) {
    event.preventDefault();
    displayBehaviorMessage('', 'success'); // Clear previous messages

    const formData = new FormData(logBehaviorForm);
    const childId = formData.get('child_id');
    const behaviorType = formData.get('behavior_type');
    const description = formData.get('description');
    const pointsChangeString = formData.get('points_change');

    if (!childId || !behaviorType || !description || pointsChangeString === null || pointsChangeString.trim() === '') {
        displayBehaviorMessage('All fields are required.');
        return;
    }

    const pointsChange = parseInt(pointsChangeString, 10);
    if (isNaN(pointsChange)) {
        displayBehaviorMessage('Points change must be a valid number.');
        return;
    }

    // Optional: More strict validation for points based on behavior type
    if (behaviorType === "positive" && pointsChange < 0) {
        displayBehaviorMessage('Positive behavior should have non-negative points. Please correct.', 'warning');
        // return; // Could uncomment to enforce strictness
    } else if (behaviorType === "negative" && pointsChange > 0) {
        displayBehaviorMessage('Negative behavior should have non-positive points (e.g., -5). Please correct.', 'warning');
        // return; // Could uncomment to enforce strictness
    }
    
    const data = {
        child_id: parseInt(childId, 10),
        behavior_type: behaviorType,
        description: description,
        points_change: pointsChange
    };

    try {
        const response = await fetch('/api/behaviors', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        const result = await response.json();

        if (response.ok) {
            let successMsg = result.message || 'Behavior logged successfully!';
            if (result.child_new_balance !== undefined && result.behavior_log && result.behavior_log.child_username) {
                successMsg += ` ${result.behavior_log.child_username} now has ${result.child_new_balance} points.`;
            }
            displayBehaviorMessage(successMsg, 'success');
            logBehaviorForm.reset();
            fetchAndDisplayBehaviorLog(); // Refresh the log list
        } else {
            displayBehaviorMessage(result.error || 'Failed to log behavior.');
        }
    } catch (error) {
        console.error('Error logging behavior:', error);
        displayBehaviorMessage('An unexpected error occurred while logging behavior.');
    }
}

// Fetch and Display Behavior Log History
async function fetchAndDisplayBehaviorLog() {
    if (!behaviorLogListDiv) return;
    behaviorLogListDiv.innerHTML = '<p>Loading behavior history...</p>';

    try {
        const response = await fetch('/api/behaviors'); // Parent's endpoint to get all their recorded logs
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        const logs = await response.json();

        if (logs.length === 0) {
            behaviorLogListDiv.innerHTML = '<p>No behavior logs found yet.</p>';
            return;
        }

        let logsHTML = '<ul class="list-group">';
        logs.forEach(log => {
            logsHTML += `
                <li class="list-group-item">
                    <h5 class="mb-1">${log.child_username || 'N/A'} - ${log.behavior_type === 'positive' ? 'Positive' : 'Negative'} Behavior</h5>
                    <p class="mb-1"><strong>Description:</strong> ${log.description}</p>
                    <p class="mb-1"><strong>Points Change:</strong> <span class="${log.points_change >= 0 ? 'text-success' : 'text-danger'}">${log.points_change}</span></p>
                    <small>Recorded by: ${log.recorded_by_parent_username || 'N/A'} on ${new Date(log.timestamp).toLocaleString()}</small>
                </li>`;
        });
        logsHTML += '</ul>';
        behaviorLogListDiv.innerHTML = logsHTML;
    } catch (error) {
        console.error('Error fetching behavior logs:', error);
        displayBehaviorMessage(`Error fetching behavior log: ${error.message}`);
        behaviorLogListDiv.innerHTML = '<p>Could not load behavior history.</p>';
    }
}

// --- Event Listeners ---
document.addEventListener('DOMContentLoaded', () => {
    if (logBehaviorForm) { // Ensure elements are present (i.e., we are on the correct page)
        populateChildrenSelectBehavior();
        fetchAndDisplayBehaviorLog();
        logBehaviorForm.addEventListener('submit', handleLogBehavior);
    }
});
