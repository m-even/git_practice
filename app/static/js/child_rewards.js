// --- DOM Elements ---
const availableRewardsListDiv = document.getElementById('available-rewards-list');
const myRedemptionHistoryListDiv = document.getElementById('my-redemption-history-list');
const messageAreaChildRewards = document.getElementById('message-area-child-rewards');
const childCurrentPointsSpan = document.getElementById('child-current-points'); // To update points display

// --- Utility Functions ---
function displayChildRewardsMessage(message, type = 'danger') {
    if (messageAreaChildRewards) {
        messageAreaChildRewards.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
    } else {
        console.error("Message area for child rewards not found.");
        alert(message); // Fallback
    }
}

// Function to get current points from the span, or fetch if needed (simplified)
function getCurrentPoints() {
    if (childCurrentPointsSpan) {
        // Extract number from "X points"
        const pointsText = childCurrentPointsSpan.textContent.match(/(\d+)/);
        return pointsText ? parseInt(pointsText[0], 10) : 0;
    }
    return 0; // Fallback, ideally fetch from API if not available
}

// --- API Calls and Data Handling ---

// Fetch and Display Available Rewards
async function fetchAndDisplayAvailableRewards() {
    if (!availableRewardsListDiv) return;
    availableRewardsListDiv.innerHTML = '<p>Loading available rewards...</p>';

    try {
        const response = await fetch('/api/rewards/available'); 
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        const rewards = await response.json();

        if (rewards.length === 0) {
            availableRewardsListDiv.innerHTML = '<p>No rewards currently available. Check back later!</p>';
            return;
        }

        let rewardsHTML = '<ul class="list-group">';
        const currentPoints = getCurrentPoints();

        rewards.forEach(reward => {
            const canAfford = currentPoints >= reward.point_cost;
            const inStock = reward.availability !== 'limited_stock' || (reward.stock_quantity !== null && reward.stock_quantity > 0);
            const canRedeem = canAfford && inStock && reward.availability === 'available';

            rewardsHTML += `
                <li class="list-group-item">
                    <h5>${reward.name} - ${reward.point_cost} pts</h5>
                    <p>${reward.description || 'No description.'}</p>
                    <small>Availability: ${reward.availability} 
                           ${reward.availability === 'limited_stock' ? `(Stock: ${reward.stock_quantity !== null ? reward.stock_quantity : 'N/A'})` : ''}
                    </small>
                    ${canRedeem ? 
                        `<button class="btn btn-success btn-sm float-right redeem-reward-btn" 
                                 data-reward-id="${reward.id}" 
                                 data-point-cost="${reward.point_cost}">Redeem</button>` 
                        : 
                        `<button class="btn btn-secondary btn-sm float-right" disabled title="${!canAfford ? 'Not enough points' : !inStock ? 'Out of stock' : 'Unavailable'}">Redeem</button>`
                    }
                </li>`;
        });
        rewardsHTML += '</ul>';
        availableRewardsListDiv.innerHTML = rewardsHTML;
        attachRedeemButtonListeners();
    } catch (error) {
        console.error('Error fetching available rewards:', error);
        displayChildRewardsMessage(`Error fetching rewards: ${error.message}`);
        availableRewardsListDiv.innerHTML = '<p>Could not load available rewards.</p>';
    }
}

// Handle Redeem Reward
async function handleRedeemReward(rewardId, pointCost) {
    const currentPoints = getCurrentPoints();
    if (currentPoints < pointCost) {
        displayChildRewardsMessage('You do not have enough points to redeem this reward.', 'warning');
        return;
    }

    if (!confirm(`Are you sure you want to redeem this reward for ${pointCost} points?`)) {
        return;
    }
    displayChildRewardsMessage('', 'success'); // Clear previous messages

    try {
        const response = await fetch(`/api/child/rewards/${rewardId}/redeem`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
        });
        const result = await response.json();

        if (response.ok) {
            displayChildRewardsMessage(result.message || 'Redemption request sent successfully! Waiting for parent approval.', 'success');
            // Optionally, update points display immediately, though API driven update on page refresh is safer
            // if (childCurrentPointsSpan) childCurrentPointsSpan.textContent = `${currentPoints - pointCost} points`;
            
            fetchAndDisplayAvailableRewards(); // Refresh available rewards (stock might change)
            fetchAndDisplayMyRedemptionHistory(); // Refresh redemption history
        } else {
            displayChildRewardsMessage(result.error || 'Failed to send redemption request.');
        }
    } catch (error) {
        console.error('Error redeeming reward:', error);
        displayChildRewardsMessage('An unexpected error occurred while redeeming the reward.');
    }
}

// Fetch and Display Child's Redemption History
async function fetchAndDisplayMyRedemptionHistory() {
    if (!myRedemptionHistoryListDiv) return;
    myRedemptionHistoryListDiv.innerHTML = '<p>Loading your redemption history...</p>';

    try {
        const response = await fetch('/api/child/redemptions');
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        const history = await response.json();

        if (history.length === 0) {
            myRedemptionHistoryListDiv.innerHTML = '<p>You have no redemption history yet.</p>';
            return;
        }

        let historyHTML = '<ul class="list-group">';
        history.forEach(log => {
            historyHTML += `
                <li class="list-group-item">
                    <h5 class="mb-1">${log.reward_name}</h5>
                    <p class="mb-1">Points Cost: ${log.points_at_redemption}</p>
                    <p class="mb-1">Status: <strong>${log.status}</strong></p>
                    <small>Requested: ${new Date(log.timestamp_requested).toLocaleString()}</small>
                    ${log.timestamp_processed ? `<br><small>Processed: ${new Date(log.timestamp_processed).toLocaleString()}</small>` : ''}
                </li>`;
        });
        historyHTML += '</ul>';
        myRedemptionHistoryListDiv.innerHTML = historyHTML;
    } catch (error) {
        console.error('Error fetching redemption history:', error);
        displayChildRewardsMessage(`Error fetching redemption history: ${error.message}`, 'danger');
        myRedemptionHistoryListDiv.innerHTML = '<p>Could not load your redemption history.</p>';
    }
}


// Attach event listeners for redeem buttons
function attachRedeemButtonListeners() {
    document.querySelectorAll('.redeem-reward-btn').forEach(button => {
        button.addEventListener('click', (event) => {
            const rewardId = event.target.dataset.rewardId;
            const pointCost = parseInt(event.target.dataset.pointCost, 10);
            handleRedeemReward(rewardId, pointCost);
        });
    });
}

// --- Initial Page Setup ---
document.addEventListener('DOMContentLoaded', () => {
    if (availableRewardsListDiv && myRedemptionHistoryListDiv) { 
        fetchAndDisplayAvailableRewards();
        fetchAndDisplayMyRedemptionHistory();
    }
});
