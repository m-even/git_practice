// --- DOM Elements ---
const choresListDiv = document.getElementById('chores-list');
const createChoreForm = document.getElementById('create-chore-form');
const childAssigneeSelect = document.getElementById('chore-child-assignee'); // For create form
const addNewChoreBtn = document.getElementById('add-new-chore-btn');
const createChoreFormContainer = document.getElementById('create-chore-form-container');
const cancelAddChoreBtn = document.getElementById('cancel-add-chore-btn');
const messageAreaChores = document.getElementById('message-area-chores');

// Edit Modal Elements
const editChoreModal = document.getElementById('editChoreModal');
const editChoreForm = document.getElementById('edit-chore-form');
const editChildAssigneeSelect = document.getElementById('edit-chore-child-assignee'); // For edit form
const cancelEditChoreBtn = document.getElementById('cancel-edit-chore-btn');
const closeEditModalBtn = document.getElementById('close-edit-modal-btn');
const messageAreaEditModal = document.getElementById('message-area-edit-modal');


// --- Utility Functions ---
function displayChoresMessage(message, type = 'danger') {
    if (messageAreaChores) {
        messageAreaChores.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
    } else {
        console.error("Message area for chores not found.");
    }
}

function displayMessageInModal(message, type = 'danger') {
    if (messageAreaEditModal) {
        messageAreaEditModal.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
    } else { 
        displayChoresMessage(message, type); // Fallback to main message area
    }
}

// --- API Calls and Data Handling ---

// Fetch and Display Chores
async function fetchAndDisplayChores() {
    if (!choresListDiv) return;
    choresListDiv.innerHTML = '<p>Loading chores...</p>';

    try {
        const response = await fetch('/api/chores'); // Parent's own chores
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }
        const chores = await response.json();

        if (chores.length === 0) {
            choresListDiv.innerHTML = '<p>No chores found. Add some!</p>';
            return;
        }

        let choresHTML = '<ul class="list-group">';
        chores.forEach(chore => {
            choresHTML += `
                <li class="list-group-item">
                    <h5>${chore.name} (${chore.points_value} pts)</h5>
                    <p>${chore.description || 'No description.'}</p>
                    <p>Status: <strong>${chore.status}</strong></p>
                    <p>Due: ${chore.date_due ? new Date(chore.date_due).toLocaleDateString() : 'N/A'}</p>
                    <p>Assigned to: ${chore.assigned_child_username || 'Unassigned'}</p>
                    <p>Created: ${new Date(chore.created_at).toLocaleDateString()}</p>
                    <div class="chore-actions mt-2">
                        <button class="btn btn-sm btn-info edit-chore-btn" 
                                data-chore-id="${chore.id}"
                                data-name="${chore.name}"
                                data-description="${chore.description || ''}"
                                data-points_value="${chore.points_value}"
                                data-assigned_to_child_id="${chore.assigned_to_child_id || ''}"
                                data-date_due="${chore.date_due ? chore.date_due.split('T')[0] : ''}">Edit</button>
                        <button class="btn btn-sm btn-danger delete-chore-btn" data-chore-id="${chore.id}" onclick="handleDeleteChore(${chore.id})">Delete</button>
                        ${chore.status === 'completed_pending_approval' ? `<button class="btn btn-sm btn-success approve-chore-btn" data-chore-id="${chore.id}" onclick="handleApproveChore(${chore.id})">Approve</button>` : ''}
                    </div>
                </li>`;
        });
        choresHTML += '</ul>';
        choresListDiv.innerHTML = choresHTML;
        attachEditListeners(); // Attach listeners to newly created edit buttons
    } catch (error) {
        console.error('Error fetching chores:', error);
        displayChoresMessage(`Error fetching chores: ${error.message}`);
        choresListDiv.innerHTML = '<p>Could not load chores.</p>';
    }
}

// Populate Children Dropdown (for create or edit form)
async function populateChildrenDropdown(selectElement, valueToSelect = null) {
    if (!selectElement) return;

    try {
        const response = await fetch('/api/parent/children');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const children = await response.json();
        
        selectElement.innerHTML = '<option value="">-- None --</option>'; // Reset
        children.forEach(child => {
            const option = document.createElement('option');
            option.value = child.id;
            option.textContent = child.username;
            selectElement.appendChild(option);
        });
        if (valueToSelect) {
            selectElement.value = valueToSelect;
        }
    } catch (error) {
        console.error('Error fetching children:', error);
        const message = 'Could not load children for assignment.';
        if (selectElement.id === 'edit-chore-child-assignee') {
            displayMessageInModal(message, 'warning');
        } else {
            displayChoresMessage(message, 'warning');
        }
    }
}

// Handle Create Chore
async function handleCreateChore(event) {
    event.preventDefault();
    displayChoresMessage('', 'success'); 

    const formData = new FormData(createChoreForm);
    const data = {
        name: formData.get('name'),
        description: formData.get('description'),
        points_value: parseInt(formData.get('points_value'), 10),
        assigned_to_child_id: formData.get('assigned_to_child_id') ? parseInt(formData.get('assigned_to_child_id'), 10) : null,
        date_due: formData.get('date_due') || null,
    };

    if (!data.name || isNaN(data.points_value) || data.points_value < 0) {
        displayChoresMessage('Chore name and a valid non-negative points value are required.');
        return;
    }
    if (data.date_due === "") data.date_due = null;

    try {
        const response = await fetch('/api/chores', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        const result = await response.json();

        if (response.ok) {
            displayChoresMessage('Chore created successfully!', 'success');
            createChoreForm.reset();
            if(createChoreFormContainer) createChoreFormContainer.style.display = 'none';
            fetchAndDisplayChores(); 
        } else {
            displayChoresMessage(result.error || 'Failed to create chore.');
        }
    } catch (error) {
        console.error('Error creating chore:', error);
        displayChoresMessage('An unexpected error occurred.');
    }
}

// Populate and Show Edit Modal
function openEditChoreModal(choreData) {
    if (!editChoreModal || !editChoreForm || !editChildAssigneeSelect) {
        console.error("Edit modal, form, or child select not found in the DOM.");
        return;
    }
    if(messageAreaEditModal) messageAreaEditModal.innerHTML = ''; // Clear previous modal messages

    document.getElementById('edit-chore-id').value = choreData.id;
    document.getElementById('edit-chore-name').value = choreData.name;
    document.getElementById('edit-chore-description').value = choreData.description;
    document.getElementById('edit-chore-points').value = choreData.points_value;
    document.getElementById('edit-chore-due-date').value = choreData.date_due;
    
    populateChildrenDropdown(editChildAssigneeSelect, choreData.assigned_to_child_id).then(() => {
      // Dropdown populated and value set
    });
    
    editChoreModal.style.display = 'block';
}

// Handle Update Chore
async function handleUpdateChore(event) {
    event.preventDefault();
    const choreId = document.getElementById('edit-chore-id').value;
    if(messageAreaEditModal) messageAreaEditModal.innerHTML = '';

    const formData = new FormData(editChoreForm);
    const data = {
        name: formData.get('name'),
        description: formData.get('description'),
        points_value: parseInt(formData.get('points_value'), 10),
        assigned_to_child_id: formData.get('assigned_to_child_id') ? parseInt(formData.get('assigned_to_child_id'), 10) : null,
        date_due: formData.get('date_due') || null,
    };
    
    if (data.date_due === "") data.date_due = null;
    if (!data.name || isNaN(data.points_value) || data.points_value < 0) {
        displayMessageInModal('Chore name and a valid non-negative points value are required.', 'danger');
        return;
    }

    try {
        const response = await fetch(`/api/chores/${choreId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        const result = await response.json();

        if (response.ok) {
            if(editChoreModal) editChoreModal.style.display = 'none';
            displayChoresMessage('Chore updated successfully!', 'success');
            fetchAndDisplayChores(); 
        } else {
            displayMessageInModal(result.error || 'Failed to update chore.');
        }
    } catch (error) {
        console.error('Error updating chore:', error);
        displayMessageInModal('An unexpected error occurred.');
    }
}

// Attach event listeners for edit buttons dynamically after chores are rendered
function attachEditListeners() {
    document.querySelectorAll('.edit-chore-btn').forEach(button => {
        button.addEventListener('click', (event) => {
            const choreData = {
                id: event.target.dataset.choreId,
                name: event.target.dataset.name,
                description: event.target.dataset.description,
                points_value: event.target.dataset.points_value,
                assigned_to_child_id: event.target.dataset.assigned_to_child_id,
                date_due: event.target.dataset.date_due,
            };
            openEditChoreModal(choreData);
        });
    });
}

// --- Event Listeners ---
document.addEventListener('DOMContentLoaded', () => {
    if (choresListDiv) { 
        fetchAndDisplayChores();
        populateChildrenDropdown(childAssigneeSelect); // Populate for create form

        if(addNewChoreBtn && createChoreFormContainer) {
            addNewChoreBtn.addEventListener('click', () => {
                createChoreFormContainer.style.display = createChoreFormContainer.style.display === 'none' ? 'block' : 'none';
                 if(messageAreaChores) messageAreaChores.innerHTML = ''; // Clear messages when showing form
                createChoreForm.reset(); // Reset form when showing
            });
        }

        if(cancelAddChoreBtn && createChoreFormContainer) {
            cancelAddChoreBtn.addEventListener('click', () => {
                createChoreFormContainer.style.display = 'none';
                createChoreForm.reset();
            });
        }
    }

    if (createChoreForm) {
        createChoreForm.addEventListener('submit', handleCreateChore);
    }

    // Edit Modal Listeners
    if (editChoreForm) {
        editChoreForm.addEventListener('submit', handleUpdateChore);
    }
    if (cancelEditChoreBtn && editChoreModal) {
        cancelEditChoreBtn.addEventListener('click', () => {
            editChoreModal.style.display = 'none';
        });
    }
    if (closeEditModalBtn && editChoreModal) {
        closeEditModalBtn.addEventListener('click', () => {
            editChoreModal.style.display = 'none';
        });
    }
    // Close modal if user clicks outside of it
    window.addEventListener('click', (event) => {
        if (event.target === editChoreModal) {
            editChoreModal.style.display = 'none';
        }
    });
});


// Handle Delete Chore
async function handleDeleteChore(choreId) {
    if (!confirm(`Are you sure you want to delete chore ID ${choreId}? This action cannot be undone.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/chores/${choreId}`, {
            method: 'DELETE',
        });

        if (response.ok) { // Or response.status === 200 || response.status === 204
            displayChoresMessage('Chore deleted successfully!', 'success');
            fetchAndDisplayChores(); // Refresh the list
        } else {
            const result = await response.json();
            displayChoresMessage(result.error || 'Failed to delete chore.', 'danger');
        }
    } catch (error) {
        console.error('Error deleting chore:', error);
        displayChoresMessage('An unexpected error occurred while deleting the chore.', 'danger');
    }
}

function approveChore(choreId) {
// Handle Approve Chore
async function handleApproveChore(choreId) {
    if (!confirm(`Are you sure you want to approve chore ID ${choreId}? This will award points to the child.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/parent/chores/${choreId}/approve`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            // No body is strictly needed if the action is implicit in the route,
            // but some APIs might expect an empty object or an action field.
            // For this API, the backend route implies the action.
        });

        const result = await response.json(); // Always try to parse JSON

        if (response.ok) {
            let successMessage = result.message || `Chore ${choreId} approved!`;
            if (result.chore && result.chore.assigned_child_username && result.child_new_balance !== undefined) {
                successMessage += ` ${result.chore.assigned_child_username} now has ${result.child_new_balance} points.`;
            }
            displayChoresMessage(successMessage, 'success');
            fetchAndDisplayChores(); // Refresh the list
        } else {
            displayChoresMessage(result.error || 'Failed to approve chore.', 'danger');
        }
    } catch (error) {
        console.error('Error approving chore:', error);
        displayChoresMessage('An unexpected error occurred while approving the chore.', 'danger');
    }
}
