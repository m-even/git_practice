// --- DOM Elements ---
const myChoresListDiv = document.getElementById('my-chores-list');
const messageAreaChildChores = document.getElementById('message-area-child-chores');

// --- Utility Functions ---
function displayChildChoresMessage(message, type = 'danger') {
    if (messageAreaChildChores) {
        messageAreaChildChores.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
    } else {
        console.error("Message area for child chores not found.");
        alert(message); // Fallback
    }
}

// --- API Calls and Data Handling ---

// Fetch and Display Child's Assigned Chores
async function fetchAndDisplayMyChores() {
    if (!myChoresListDiv) return;
    myChoresListDiv.innerHTML = '<p>Loading your chores...</p>';

    try {
        const response = await fetch('/api/child/chores'); 
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        const chores = await response.json();

        if (chores.length === 0) {
            myChoresListDiv.innerHTML = '<p>You have no assigned chores. Great job, or check back later!</p>';
            return;
        }

        let choresHTML = '<div class="list-group">';
        chores.forEach(chore => {
            choresHTML += `
                <div class="list-group-item">
                    <div class="d-flex w-100 justify-content-between">
                        <h5 class="mb-1">${chore.name}</h5>
                        <small>Points: ${chore.points_value}</small>
                    </div>
                    <p class="mb-1">${chore.description || 'No specific description.'}</p>
                    <small>Status: <strong>${chore.status}</strong></small>
                    <small class="ml-2">Due: ${chore.date_due ? new Date(chore.date_due).toLocaleDateString() : 'N/A'}</small>
                    ${chore.status === 'assigned' ? 
                        `<button class="btn btn-primary btn-sm float-right mark-complete-btn" data-chore-id="${chore.id}" onclick="handleMarkAsComplete(${chore.id})">Mark as Complete</button>` 
                        : ''
                    }
                    ${chore.status === 'completed_pending_approval' ? 
                        '<small class="float-right text-info"><em>Waiting for parent approval</em></small>' 
                        : ''
                    }
                     ${chore.status === 'approved' ? 
                        '<small class="float-right text-success"><em>Approved! Points awarded.</em></small>' 
                        : ''
                    }
                </div>`;
        });
        choresHTML += '</div>';
        myChoresListDiv.innerHTML = choresHTML;
    } catch (error) {
        console.error('Error fetching your chores:', error);
        displayChildChoresMessage(`Error fetching your chores: ${error.message}`);
        myChoresListDiv.innerHTML = '<p>Could not load your chores. Please try again later.</p>';
    }
}

// Handle Mark Chore as Complete
async function handleMarkAsComplete(choreId) {
    if (!confirm('Are you sure you want to mark this chore as complete?')) {
        return;
    }
    displayChildChoresMessage('', 'success'); // Clear previous messages

    try {
        const response = await fetch(`/api/child/chores/${choreId}/complete`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
        });
        const result = await response.json();

        if (response.ok) {
            displayChildChoresMessage('Chore marked as complete, pending parent approval!', 'success');
            fetchAndDisplayMyChores(); // Refresh the list
        } else {
            displayChildChoresMessage(result.error || 'Failed to mark chore as complete.', 'danger');
        }
    } catch (error) {
        console.error('Error marking chore complete:', error);
        displayChildChoresMessage('An unexpected error occurred.', 'danger');
    }
}

// --- Event Listeners ---
document.addEventListener('DOMContentLoaded', () => {
    if (myChoresListDiv) { // Ensure this script only runs on the child's chores page
        fetchAndDisplayMyChores();
    }
    // No dynamic listeners needed for "Mark as Complete" if using onclick,
    // otherwise an attachCompleteListeners function would be called here after fetchAndDisplayMyChores.
});
