// --- DOM Elements ---
const myBehaviorLogListDiv = document.getElementById('my-behavior-log-list');
const messageAreaChildBehavior = document.getElementById('message-area-child-behavior');

// --- Utility Functions ---
function displayChildBehaviorMessage(message, type = 'danger') {
    if (messageAreaChildBehavior) {
        messageAreaChildBehavior.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
    } else {
        console.error("Message area for child behavior log not found.");
        alert(message); // Fallback
    }
}

// --- API Calls and Data Handling ---

// Fetch and Display Child's Behavior Log
async function fetchAndDisplayMyBehaviorLog() {
    if (!myBehaviorLogListDiv) return;
    myBehaviorLogListDiv.innerHTML = '<p>Loading your behavior history...</p>';

    try {
        const response = await fetch('/api/child/behaviorlogs'); 
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        const logs = await response.json();

        if (logs.length === 0) {
            myBehaviorLogListDiv.innerHTML = '<p>No behavior has been logged for you yet.</p>';
            return;
        }

        let logsHTML = '<ul class="list-group">';
        logs.forEach(log => {
            const behaviorClass = log.behavior_type === 'positive' ? 'text-success' : 'text-danger';
            const pointsClass = log.points_change >= 0 ? 'text-success' : 'text-danger';
            logsHTML += `
                <li class="list-group-item">
                    <h5 class="mb-1">
                        <span class="${behaviorClass}">${log.behavior_type === 'positive' ? 'Positive' : 'Negative'} Behavior</span>
                    </h5>
                    <p class="mb-1"><strong>Description:</strong> ${log.description}</p>
                    <p class="mb-1"><strong>Points Change:</strong> <span class="${pointsClass}">${log.points_change}</span></p>
                    <small>Recorded by: ${log.recorded_by_parent_username || 'Parent'} on ${new Date(log.timestamp).toLocaleString()}</small>
                </li>`;
        });
        logsHTML += '</ul>';
        myBehaviorLogListDiv.innerHTML = logsHTML;
    } catch (error) {
        console.error('Error fetching your behavior log:', error);
        displayChildBehaviorMessage(`Error fetching your behavior log: ${error.message}`);
        myBehaviorLogListDiv.innerHTML = '<p>Could not load your behavior history. Please try again later.</p>';
    }
}

// --- Event Listeners ---
document.addEventListener('DOMContentLoaded', () => {
    if (myBehaviorLogListDiv) { // Ensure this script only runs on the child's behavior log page
        fetchAndDisplayMyBehaviorLog();
    }
});
