// --- DOM Elements ---
const rewardsListDiv = document.getElementById('rewards-list');
const createRewardForm = document.getElementById('create-reward-form');
const addNewRewardBtn = document.getElementById('add-new-reward-btn');
const createRewardFormContainer = document.getElementById('create-reward-form-container');
const cancelAddRewardBtn = document.getElementById('cancel-add-reward-btn');
const messageAreaRewards = document.getElementById('message-area-rewards');

// Create Form Specific Elements
const createAvailabilitySelect = document.getElementById('reward-availability');
const createStockQuantityGroup = document.getElementById('reward-stock-quantity-group');
const createStockQuantityInput = document.getElementById('reward-stock-quantity');

// Edit Modal Elements
const editRewardModal = document.getElementById('editRewardModal');
const editRewardForm = document.getElementById('edit-reward-form');
const cancelEditRewardBtn = document.getElementById('cancel-edit-reward-btn');
const closeEditRewardModalBtn = document.getElementById('close-edit-reward-modal-btn');
const messageAreaEditRewardModal = document.getElementById('message-area-edit-reward-modal');
const editAvailabilitySelect = document.getElementById('edit-reward-availability');
const editStockQuantityGroup = document.getElementById('edit-reward-stock-quantity-group');
const editStockQuantityInput = document.getElementById('edit-reward-stock-quantity');


// --- Utility Functions ---
function displayRewardsMessage(message, type = 'danger') {
    if (messageAreaRewards) {
        messageAreaRewards.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
    } else {
        console.error("Message area for rewards not found.");
    }
}

function displayMessageInEditRewardModal(message, type = 'danger') {
    if (messageAreaEditRewardModal) {
        messageAreaEditRewardModal.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
    } else { 
        displayRewardsMessage(message, type); // Fallback
    }
}

// Show/hide stock quantity field based on availability selection
function handleAvailabilityChange(availabilitySelect, stockQuantityGroup, stockQuantityInput) {
    if (availabilitySelect.value === 'limited_stock') {
        stockQuantityGroup.style.display = 'block';
        stockQuantityInput.required = true;
    } else {
        stockQuantityGroup.style.display = 'none';
        stockQuantityInput.required = false;
        stockQuantityInput.value = ''; // Clear value if not limited stock
    }
}

// --- API Calls and Data Handling ---

// Fetch and Display Rewards
async function fetchAndDisplayRewards() {
    if (!rewardsListDiv) return;
    rewardsListDiv.innerHTML = '<p>Loading rewards...</p>';

    try {
        const response = await fetch('/api/rewards/my'); // Parent's own rewards
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        const rewards = await response.json();

        if (rewards.length === 0) {
            rewardsListDiv.innerHTML = '<p>No rewards found. Add some!</p>';
            return;
        }

        let rewardsHTML = '<ul class="list-group">';
        rewards.forEach(reward => {
            rewardsHTML += `
                <li class="list-group-item">
                    <h5>${reward.name} - ${reward.point_cost} pts</h5>
                    <p>${reward.description || 'No description.'}</p>
                    <p>Availability: <strong>${reward.availability}</strong>
                       ${reward.availability === 'limited_stock' ? `(Stock: ${reward.stock_quantity !== null ? reward.stock_quantity : 'N/A'})` : ''}
                    </p>
                    <div class="reward-actions mt-2">
                        <button class="btn btn-sm btn-info edit-reward-btn" 
                                data-reward-id="${reward.id}"
                                data-name="${reward.name}"
                                data-description="${reward.description || ''}"
                                data-point_cost="${reward.point_cost}"
                                data-availability="${reward.availability}"
                                data-stock_quantity="${reward.stock_quantity || ''}">Edit</button>
                        <button class="btn btn-sm btn-danger delete-reward-btn" data-reward-id="${reward.id}">Delete</button>
                    </div>
                </li>`;
        });
        rewardsHTML += '</ul>';
        rewardsListDiv.innerHTML = rewardsHTML;
        attachRewardActionListeners(); 
    } catch (error) {
        console.error('Error fetching rewards:', error);
        displayRewardsMessage(`Error fetching rewards: ${error.message}`);
        rewardsListDiv.innerHTML = '<p>Could not load rewards.</p>';
    }
}

// Handle Create Reward
async function handleCreateReward(event) {
    event.preventDefault();
    displayRewardsMessage('', 'success'); 

    const formData = new FormData(createRewardForm);
    const availability = formData.get('availability');
    const stockQuantityStr = formData.get('stock_quantity');
    let stockQuantity = null;

    if (availability === 'limited_stock') {
        if (!stockQuantityStr) {
            displayRewardsMessage('Stock quantity is required for limited stock items.');
            return;
        }
        stockQuantity = parseInt(stockQuantityStr, 10);
        if (isNaN(stockQuantity) || stockQuantity < 0) {
            displayRewardsMessage('Stock quantity must be a non-negative number.');
            return;
        }
    }
    
    const pointCost = parseInt(formData.get('point_cost'), 10);
    if (isNaN(pointCost) || pointCost <=0) {
        displayRewardsMessage('Point cost must be a positive number.');
        return;
    }

    const data = {
        name: formData.get('name'),
        description: formData.get('description'),
        point_cost: pointCost,
        availability: availability,
        stock_quantity: stockQuantity
    };

    try {
        const response = await fetch('/api/rewards', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        const result = await response.json();

        if (response.ok) {
            displayRewardsMessage('Reward created successfully!', 'success');
            createRewardForm.reset();
            createStockQuantityGroup.style.display = 'none'; // Hide stock for next time
            if(createRewardFormContainer) createRewardFormContainer.style.display = 'none';
            fetchAndDisplayRewards(); 
        } else {
            displayRewardsMessage(result.error || 'Failed to create reward.');
        }
    } catch (error) {
        console.error('Error creating reward:', error);
        displayRewardsMessage('An unexpected error occurred.');
    }
}

// Populate and Show Edit Reward Modal
function openEditRewardModal(rewardData) {
    if (!editRewardModal || !editRewardForm || !editAvailabilitySelect || !editStockQuantityGroup || !editStockQuantityInput) {
        console.error("Edit reward modal or its form elements not found.");
        return;
    }
    if(messageAreaEditRewardModal) messageAreaEditRewardModal.innerHTML = '';

    document.getElementById('edit-reward-id').value = rewardData.id;
    document.getElementById('edit-reward-name').value = rewardData.name;
    document.getElementById('edit-reward-description').value = rewardData.description;
    document.getElementById('edit-reward-point-cost').value = rewardData.point_cost;
    
    editAvailabilitySelect.value = rewardData.availability;
    handleAvailabilityChange(editAvailabilitySelect, editStockQuantityGroup, editStockQuantityInput); // Show/hide stock based on current availability
    
    if (rewardData.availability === 'limited_stock') {
        editStockQuantityInput.value = rewardData.stock_quantity;
    } else {
        editStockQuantityInput.value = '';
    }
    
    editRewardModal.style.display = 'block';
}

// Handle Update Reward
async function handleUpdateReward(event) {
    event.preventDefault();
    const rewardId = document.getElementById('edit-reward-id').value;
    if(messageAreaEditRewardModal) messageAreaEditRewardModal.innerHTML = '';

    const formData = new FormData(editRewardForm);
    const availability = formData.get('availability');
    const stockQuantityStr = formData.get('stock_quantity');
    let stockQuantity = null;

    if (availability === 'limited_stock') {
        if (!stockQuantityStr) {
            displayMessageInEditRewardModal('Stock quantity is required for limited stock items.');
            return;
        }
        stockQuantity = parseInt(stockQuantityStr, 10);
        if (isNaN(stockQuantity) || stockQuantity < 0) {
            displayMessageInEditRewardModal('Stock quantity must be a non-negative number.');
            return;
        }
    }
    
    const pointCost = parseInt(formData.get('point_cost'), 10);
    if (isNaN(pointCost) || pointCost <=0) {
        displayMessageInEditRewardModal('Point cost must be a positive number.');
        return;
    }

    const data = {
        name: formData.get('name'),
        description: formData.get('description'),
        point_cost: pointCost,
        availability: availability,
        stock_quantity: stockQuantity
    };

    try {
        const response = await fetch(`/api/rewards/${rewardId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        const result = await response.json();

        if (response.ok) {
            if(editRewardModal) editRewardModal.style.display = 'none';
            displayRewardsMessage('Reward updated successfully!', 'success');
            fetchAndDisplayRewards(); 
        } else {
            displayMessageInEditRewardModal(result.error || 'Failed to update reward.');
        }
    } catch (error) {
        console.error('Error updating reward:', error);
        displayMessageInEditRewardModal('An unexpected error occurred.');
    }
}

// Handle Delete Reward
async function handleDeleteReward(rewardId) {
    if (!confirm(`Are you sure you want to delete reward ID ${rewardId}? This cannot be undone.`)) {
        return;
    }
    displayRewardsMessage('', 'success'); // Clear previous messages

    try {
        const response = await fetch(`/api/rewards/${rewardId}`, {
            method: 'DELETE',
        });

        if (response.ok) {
            displayRewardsMessage('Reward deleted successfully!', 'success');
            fetchAndDisplayRewards();
        } else {
            const result = await response.json();
            displayRewardsMessage(result.error || 'Failed to delete reward.');
        }
    } catch (error) {
        console.error('Error deleting reward:', error);
        displayRewardsMessage('An unexpected error occurred while deleting the reward.');
    }
}

// Attach Event Listeners for Edit and Delete buttons
function attachRewardActionListeners() {
    document.querySelectorAll('.edit-reward-btn').forEach(button => {
        button.addEventListener('click', (event) => {
            const rewardData = {
                id: event.target.dataset.rewardId,
                name: event.target.dataset.name,
                description: event.target.dataset.description,
                point_cost: event.target.dataset.point_cost,
                availability: event.target.dataset.availability,
                stock_quantity: event.target.dataset.stock_quantity,
            };
            openEditRewardModal(rewardData);
        });
    });

    document.querySelectorAll('.delete-reward-btn').forEach(button => {
        button.addEventListener('click', (event) => {
            handleDeleteReward(event.target.dataset.rewardId);
        });
    });
}


// --- Initial Page Setup ---
document.addEventListener('DOMContentLoaded', () => {
    if (rewardsListDiv) { // Check if we are on the parent rewards page
        fetchAndDisplayRewards();

        // Create form visibility
        if(addNewRewardBtn && createRewardFormContainer) {
            addNewRewardBtn.addEventListener('click', () => {
                createRewardFormContainer.style.display = createRewardFormContainer.style.display === 'none' ? 'block' : 'none';
                if(messageAreaRewards) messageAreaRewards.innerHTML = '';
                createRewardForm.reset();
                handleAvailabilityChange(createAvailabilitySelect, createStockQuantityGroup, createStockQuantityInput); // Reset stock field visibility
            });
        }
        if(cancelAddRewardBtn && createRewardFormContainer) {
            cancelAddRewardBtn.addEventListener('click', () => {
                createRewardFormContainer.style.display = 'none';
                createRewardForm.reset();
            });
        }
        // Create form availability change
        if(createAvailabilitySelect) {
            createAvailabilitySelect.addEventListener('change', () => handleAvailabilityChange(createAvailabilitySelect, createStockQuantityGroup, createStockQuantityInput));
        }
         // Edit form availability change
        if(editAvailabilitySelect) {
            editAvailabilitySelect.addEventListener('change', () => handleAvailabilityChange(editAvailabilitySelect, editStockQuantityGroup, editStockQuantityInput));
        }
    }

    if (createRewardForm) {
        createRewardForm.addEventListener('submit', handleCreateReward);
    }

    // Edit Modal Listeners
    if (editRewardForm) {
        editRewardForm.addEventListener('submit', handleUpdateReward);
    }
    if (cancelEditRewardBtn && editRewardModal) {
        cancelEditRewardBtn.addEventListener('click', () => {
            editRewardModal.style.display = 'none';
        });
    }
    if (closeEditRewardModalBtn && editRewardModal) {
        closeEditRewardModalBtn.addEventListener('click', () => {
            editRewardModal.style.display = 'none';
        });
    }
    window.addEventListener('click', (event) => {
        if (event.target === editRewardModal) {
            editRewardModal.style.display = 'none';
        }
    });
});
