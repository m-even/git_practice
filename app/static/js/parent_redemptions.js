// --- DOM Elements ---
const redemptionRequestsListDiv = document.getElementById('redemption-requests-list');
const messageAreaRedemptions = document.getElementById('message-area-redemptions');

// --- Utility Functions ---
function displayRedemptionsMessage(message, type = 'danger') {
    if (messageAreaRedemptions) {
        messageAreaRedemptions.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
    } else {
        console.error("Message area for redemptions not found.");
        alert(message); // Fallback
    }
}

// --- API Calls and Data Handling ---

// Fetch and Display Redemption Requests
async function fetchAndDisplayRedemptionRequests() {
    if (!redemptionRequestsListDiv) return;
    redemptionRequestsListDiv.innerHTML = '<p>Loading redemption requests...</p>';

    try {
        const response = await fetch('/api/redemptions'); // Parent's endpoint
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        const requests = await response.json();

        if (requests.length === 0) {
            redemptionRequestsListDiv.innerHTML = '<p>No redemption requests found.</p>';
            return;
        }

        let requestsHTML = '<ul class="list-group">';
        requests.forEach(req => {
            requestsHTML += `
                <li class="list-group-item">
                    <h5>${req.reward_name} for ${req.child_username}</h5>
                    <p>Points: ${req.points_at_redemption}</p>
                    <p>Status: <strong>${req.status}</strong></p>
                    <p>Requested: ${new Date(req.timestamp_requested).toLocaleString()}</p>
                    ${req.timestamp_processed ? `<p>Processed: ${new Date(req.timestamp_processed).toLocaleString()}</p>` : ''}
                    <div class="redemption-actions mt-2">`;
            
            if (req.status === 'pending_approval') {
                requestsHTML += `
                    <button class="btn btn-sm btn-success process-redemption-btn" data-redemption-id="${req.id}" data-action="approve">Approve</button>
                    <button class="btn btn-sm btn-danger process-redemption-btn" data-redemption-id="${req.id}" data-action="reject">Reject</button>
                `;
            }
            requestsHTML += `</div></li>`;
        });
        requestsHTML += '</ul>';
        redemptionRequestsListDiv.innerHTML = requestsHTML;
        attachProcessRedemptionListeners();
    } catch (error) {
        console.error('Error fetching redemption requests:', error);
        displayRedemptionsMessage(`Error fetching requests: ${error.message}`);
        redemptionRequestsListDiv.innerHTML = '<p>Could not load redemption requests.</p>';
    }
}

// Handle Process Redemption (Approve/Reject)
async function handleProcessRedemption(redemptionId, action) {
    const confirmationMessage = action === 'approve' 
        ? `Are you sure you want to approve this redemption request (ID: ${redemptionId})?`
        : `Are you sure you want to reject this redemption request (ID: ${redemptionId})?`;

    if (!confirm(confirmationMessage)) {
        return;
    }
    displayRedemptionsMessage('', 'success'); // Clear previous messages

    try {
        const response = await fetch(`/api/parent/redemptions/${redemptionId}/process`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: action }),
        });
        const result = await response.json();

        if (response.ok) {
            let successMsg = result.message || `Redemption request ${action}d successfully.`;
            if (result.child_new_balance !== undefined) {
                 successMsg += ` Child's new balance: ${result.child_new_balance}.`;
            }
            if (result.reward_new_stock !== undefined && result.reward_new_stock !== null) {
                 successMsg += ` Reward new stock: ${result.reward_new_stock}.`;
            }
            displayRedemptionsMessage(successMsg, 'success');
            fetchAndDisplayRedemptionRequests(); // Refresh the list
        } else {
            displayRedemptionsMessage(result.error || `Failed to ${action} redemption request.`);
        }
    } catch (error) {
        console.error(`Error processing redemption (${action}):`, error);
        displayRedemptionsMessage(`An unexpected error occurred while processing the request.`);
    }
}

// Attach event listeners for process buttons
function attachProcessRedemptionListeners() {
    document.querySelectorAll('.process-redemption-btn').forEach(button => {
        button.addEventListener('click', (event) => {
            const redemptionId = event.target.dataset.redemptionId;
            const action = event.target.dataset.action;
            handleProcessRedemption(redemptionId, action);
        });
    });
}

// --- Initial Page Setup ---
document.addEventListener('DOMContentLoaded', () => {
    if (redemptionRequestsListDiv) { // Check if we are on the correct page
        fetchAndDisplayRedemptionRequests();
    }
});
