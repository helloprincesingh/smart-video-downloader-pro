// Frontend Supabase Authentication Integration Coordinator
document.addEventListener('DOMContentLoaded', () => {
    // Read credentials injected from Flask templates
    const supabaseUrl = window.supabaseUrl || '';
    const supabaseAnonKey = window.supabaseAnonKey || '';
    
    let supabase = null;
    const isSupabaseConfigured = !!(supabaseUrl && supabaseAnonKey);
    
    if (isSupabaseConfigured) {
        // Initialize Supabase Client
        try {
            supabase = window.supabase.createClient(supabaseUrl, supabaseAnonKey);
            console.log("✓ Supabase Client initialized successfully.");
        } catch (e) {
            console.error("Failed to initialize Supabase Client:", e);
        }
    } else {
        console.warn("⚠ Supabase is not configured. Falling back to local Flask SQLite auth.");
    }

    // ── 1. Google OAuth Sign-In Trigger ──────────────────────────────────────
    const googleBtn = document.querySelector('.btn-google');
    if (googleBtn) {
        googleBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            if (!isSupabaseConfigured) {
                showToast("Google Login requires Supabase credentials in your .env", "error");
                return;
            }
            try {
                const { data, error } = await supabase.auth.signInWithOAuth({
                    provider: 'google',
                    options: {
                        redirectTo: window.location.origin + '/login'
                    }
                });
                if (error) throw error;
            } catch (err) {
                showToast(`Google Login Error: ${err.message}`, "error");
            }
        });
    }

    // ── 2. Intercept Auth Forms (SignUp/Login) ───────────────────────────────
    const loginForm = document.getElementById('loginForm');
    const signupForm = document.getElementById('signupForm');

    if (loginForm && isSupabaseConfigured) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value.trim();
            const submitBtn = loginForm.querySelector('button[type="submit"]');
            
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner"></span> <span>Signing In...</span>';
            
            try {
                const { data, error } = await supabase.auth.signInWithPassword({
                    email,
                    password
                });
                if (error) throw error;
                
                // Session sync will be handled automatically by onAuthStateChange listener
                showToast("Success! Syncing session...", "success");
            } catch (err) {
                showToast(err.message, "error");
                submitBtn.disabled = false;
                submitBtn.innerText = 'Sign In';
            }
        });
    }

    if (signupForm && isSupabaseConfigured) {
        signupForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value.trim();
            const confirm = document.getElementById('confirm_password').value.trim();
            const submitBtn = signupForm.querySelector('button[type="submit"]');
            
            if (password !== confirm) {
                showToast("Passwords do not match!", "error");
                return;
            }
            
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner"></span> <span>Registering...</span>';
            
            try {
                const { data, error } = await supabase.auth.signUp({
                    email,
                    password
                });
                if (error) throw error;
                
                if (data.session) {
                    showToast("Account created and logged in!", "success");
                } else {
                    showToast("Signup successful! Check email for confirmation link.", "success");
                    submitBtn.disabled = false;
                    submitBtn.innerText = 'Create Account';
                }
            } catch (err) {
                showToast(err.message, "error");
                submitBtn.disabled = false;
                submitBtn.innerText = 'Create Account';
            }
        });
    }

    // ── 3. Profile Password Reset (Email request) ───────────────────────────
    const forgotPasswordLink = document.getElementById('forgotPasswordLink');
    if (forgotPasswordLink) {
        forgotPasswordLink.addEventListener('click', async (e) => {
            e.preventDefault();
            const email = prompt("Enter your email address to receive reset link:");
            if (!email) return;
            
            if (!isSupabaseConfigured) {
                showToast("Password reset requires Supabase.", "error");
                return;
            }
            
            try {
                const { error } = await supabase.auth.resetPasswordForEmail(email, {
                    redirectTo: window.location.origin + '/reset-password'
                });
                if (error) throw error;
                showToast("Password reset link sent to your email!", "success");
            } catch (err) {
                showToast(err.message, "error");
            }
        });
    }

    // ── 4. Reset Password Form (Token Handler) ──────────────────────────────
    const resetPasswordForm = document.getElementById('resetPasswordForm');
    if (resetPasswordForm && isSupabaseConfigured) {
        resetPasswordForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const password = document.getElementById('password').value;
            const confirm = document.getElementById('confirm_password').value;
            const submitBtn = resetPasswordForm.querySelector('button[type="submit"]');
            
            if (password !== confirm) {
                showToast("Passwords must match!", "error");
                return;
            }
            
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner"></span> <span>Updating...</span>';
            
            try {
                const { error } = await supabase.auth.updateUser({ password });
                if (error) throw error;
                
                showToast("Password updated successfully!", "success");
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 2000);
            } catch (err) {
                showToast(err.message, "error");
                submitBtn.disabled = false;
                submitBtn.innerText = 'Update Password';
            }
        });
    }

    // ── 5. Supabase Auth State Change Listener (Syncing with Flask) ──────────
    if (isSupabaseConfigured && supabase) {
        supabase.auth.onAuthStateChange(async (event, session) => {
            console.log(`Supabase Auth Event: ${event}`);
            if (session && (event === 'SIGNED_IN' || event === 'USER_UPDATED')) {
                // Send session details to Flask to create session cookie
                try {
                    const response = await fetch('/auth/supabase-login', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            access_token: session.access_token,
                            email: session.user.email,
                            user_id: session.user.id
                        })
                    });
                    
                    const resData = await response.json();
                    if (resData.success) {
                        console.log("✓ Flask session synced successfully.");
                        // Redirect home or dashboard if on login/signup pages
                        const path = window.location.pathname;
                        if (path === '/login' || path === '/signup') {
                            window.location.href = '/dashboard';
                        }
                    } else {
                        console.error("Flask session sync failed:", resData.error);
                    }
                } catch (e) {
                    console.error("Session sync fetch error:", e);
                }
            } else if (event === 'SIGNED_OUT') {
                // If user logs out of Supabase, check if Flask session is active, if so clear it
                // Handled gracefully via Flask /logout route.
            }
        });
    }

    // ── 6. Log out Trigger ──────────────────────────────────────────────────
    const logoutBtn = document.querySelector('a[href="/logout"]');
    if (logoutBtn && isSupabaseConfigured && supabase) {
        logoutBtn.addEventListener('click', async (e) => {
            // Log out of Supabase first
            await supabase.auth.signOut();
            // Let the standard click proceed to log out of Flask
        });
    }

    // Simple toast helper function
    function showToast(message, type = "success") {
        const toastContainer = document.getElementById('toastContainer') || document.body;
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <i class="fa-solid ${type === 'success' ? 'fa-circle-check' : 'fa-circle-exclamation'}"></i>
            <span>${message}</span>
        `;
        toastContainer.appendChild(toast);
        
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(10px)';
            toast.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            setTimeout(() => toast.remove(), 500);
        }, 4000);
    }
});
