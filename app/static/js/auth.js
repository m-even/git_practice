// Function to display messages in a dedicated area
function displayMessage(message, type = 'danger', areaId = 'message-area') {
    const messageArea = document.getElementById(areaId);
    if (messageArea) {
        messageArea.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
    } else {
        alert(message); // Fallback if message area doesn't exist
    }
}

// Handle User Registration
async function handleRegister(event) {
    event.preventDefault();
    const messageArea = document.getElementById('message-area');
    messageArea.innerHTML = ''; // Clear previous messages

    const username = event.target.username.value;
    const email = event.target.email.value;
    const password = event.target.password.value;
    const confirm_password = event.target.confirm_password.value;

    if (!username || !email || !password || !confirm_password) {
        displayMessage('All fields are required.', 'danger');
        return;
    }

    if (password !== confirm_password) {
        displayMessage('Passwords do not match.', 'danger');
        return;
    }

    const data = {
        username: username,
        email: email,
        password: password,
        role: 'parent' // Default role for self-registration
    };

    try {
        const response = await fetch('/api/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        });

        const result = await response.json();

        if (response.ok) { // Status 200-299
            displayMessage(result.message || 'Registration successful! Please log in.', 'success');
            // Redirect to login page after a short delay to allow message reading
            setTimeout(() => {
                window.location.href = '/login';
            }, 2000);
        } else {
            displayMessage(result.error || 'Registration failed. Please try again.', 'danger');
        }
    } catch (error) {
        console.error('Registration error:', error);
        displayMessage('An unexpected error occurred during registration.', 'danger');
    }
}

// Handle User Login
async function handleLogin(event) {
    event.preventDefault();
    const messageArea = document.getElementById('message-area');
    messageArea.innerHTML = ''; // Clear previous messages

    const username_or_email = event.target.username_or_email.value;
    const password = event.target.password.value;

    if (!username_or_email || !password) {
        displayMessage('Username/Email and Password are required.', 'danger');
        return;
    }

    const data = {
        username: username_or_email, // API expects 'username' field for username or email
        password: password,
    };

    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        });

        const result = await response.json();

        if (response.ok) {
            // Login successful, server sets session cookie.
            // Redirect based on role.
            // No explicit success message needed here as page will redirect.
            if (result.user && result.user.role === 'parent') {
                window.location.href = '/parent/dashboard';
            } else if (result.user && result.user.role === 'child') {
                window.location.href = '/child/chores'; // Or child dashboard if one exists
            } else {
                window.location.href = '/index'; // Default redirect
            }
        } else {
            displayMessage(result.error || 'Login failed. Please check your credentials.', 'danger');
        }
    } catch (error) {
        console.error('Login error:', error);
        displayMessage('An unexpected error occurred during login.', 'danger');
    }
}

// Event listeners are added in the HTML templates themselves
// e.g., <script> document.getElementById('registerForm').addEventListener('submit', handleRegister); </script>
// This ensures functions are available when forms are parsed.
// Alternatively, ensure this script is loaded with defer and DOMContentLoaded is used here.
// For this project, listeners are in HTML to ensure they are attached after element is loaded.
