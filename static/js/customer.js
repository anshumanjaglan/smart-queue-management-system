// Customer Portal Interactive Logic

let activeTokenId = localStorage.getItem('smartqueue_active_token_id');
let pollInterval = null;
let lastKnownStatus = null;

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('joinQueueForm');
    if (form) {
        form.addEventListener('submit', handleJoinQueue);
    }

    // Check if token was passed in URL query param, e.g. ?token_id=123
    const urlParams = new URLSearchParams(window.location.search);
    const paramTokenId = urlParams.get('token_id');
    if (paramTokenId) {
        activeTokenId = paramTokenId;
        localStorage.setItem('smartqueue_active_token_id', activeTokenId);
    }

    if (activeTokenId) {
        showTrackingView();
        pollTokenStatus();
        pollInterval = setInterval(pollTokenStatus, 3500);
    }
});

async function handleJoinQueue(e) {
    e.preventDefault();
    const btn = document.getElementById('btnSubmitToken');
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-2"></i> Generating Token...`;

    const outletId = document.getElementById('outletSelect').value;
    const customerName = document.getElementById('customerName').value.trim();
    const customerPhone = document.getElementById('customerPhone').value.trim();
    const orderNotes = document.getElementById('orderNotes').value.trim();
    const notificationPref = document.querySelector('input[name="notificationPref"]:checked').value;

    try {
        const response = await fetch('/api/token/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                outlet_id: outletId,
                customer_name: customerName,
                customer_phone: customerPhone,
                notification_pref: notificationPref,
                notes: orderNotes
            })
        });

        const data = await response.json();
        if (response.ok && data.success) {
            activeTokenId = data.token.token_id;
            localStorage.setItem('smartqueue_active_token_id', activeTokenId);
            showToast("Token Generated!", `You received Token #${data.token.token_number}`, "success");
            triggerSystemChime();
            showTrackingView();
            pollTokenStatus();
            if (pollInterval) clearInterval(pollInterval);
            pollInterval = setInterval(pollTokenStatus, 3500);
        } else {
            alert(data.message || "Failed to create token. Please check your inputs.");
        }
    } catch (err) {
        console.error("Error creating token:", err);
        alert("Server error occurred while creating token.");
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-ticket mr-2"></i> Join Queue & Get Digital Token`;
    }
}

function showTrackingView() {
    document.getElementById('joinQueueSection').classList.add('hidden');
    document.getElementById('liveTrackingSection').classList.remove('hidden');
}

function showJoinView() {
    document.getElementById('liveTrackingSection').classList.add('hidden');
    document.getElementById('joinQueueSection').classList.remove('hidden');
}

async function pollTokenStatus() {
    if (!activeTokenId) return;

    try {
        const res = await fetch(`/api/token/status/${activeTokenId}`);
        if (!res.ok) {
            if (res.status === 404) {
                resetCustomerPortal();
            }
            return;
        }

        const data = await res.json();
        if (!data.token) return;

        const token = data.token;
        updateTrackingUI(token);

        // State transition detection
        if (lastKnownStatus && lastKnownStatus !== token.status) {
            if (token.status === 'CALLED') {
                triggerSystemChime();
                showToast("Now Serving!", `Your token #${token.token_number} is called to ${token.counter_number}!`, "alert");
            } else if (token.status === 'COMPLETED') {
                triggerSystemChime();
                showToast("Order Ready!", `Your order #${token.token_number} is ready for pickup! SMS/Call notification sent.`, "success");
                if (pollInterval) clearInterval(pollInterval);
            }
        }
        lastKnownStatus = token.status;

    } catch (err) {
        console.error("Error polling token status:", err);
    }
}

function updateTrackingUI(token) {
    document.getElementById('displayOutletName').innerText = token.outlet_name;
    document.getElementById('displayCounterNumber').innerText = token.counter_number;
    document.getElementById('displayTokenNumber').innerText = token.token_number;
    document.getElementById('displayPeopleAhead').innerText = token.people_ahead;
    document.getElementById('customerPhoneNotice').innerText = token.customer_phone;

    const waitBox = document.getElementById('displayEstimatedWait');
    const badge = document.getElementById('displayStatusBadge');
    const readyBanner = document.getElementById('readyAlertBanner');
    const waitingNotice = document.getElementById('waitingNoticeBanner');

    if (token.status === 'WAITING') {
        badge.className = 'badge badge-waiting text-sm py-1 px-4';
        badge.innerHTML = `<i class="fa-solid fa-clock mr-1.5"></i> Waiting in Queue`;
        waitBox.innerText = `${token.estimated_wait_mins} mins`;
        readyBanner.classList.add('hidden');
        waitingNotice.classList.remove('hidden');
    } else if (token.status === 'CALLED') {
        badge.className = 'badge badge-called text-sm py-1 px-4';
        badge.innerHTML = `<i class="fa-solid fa-bell mr-1.5"></i> Called - Proceed to Counter!`;
        waitBox.innerText = `0.0 mins`;
        readyBanner.classList.add('hidden');
        waitingNotice.classList.remove('hidden');
    } else if (token.status === 'COMPLETED') {
        badge.className = 'badge badge-completed text-sm py-1 px-4';
        badge.innerHTML = `<i class="fa-solid fa-check-circle mr-1.5"></i> Ready for Pickup!`;
        waitBox.innerText = `Ready`;
        readyBanner.classList.remove('hidden');
        waitingNotice.classList.add('hidden');
    } else if (token.status === 'CANCELLED') {
        badge.className = 'badge text-sm py-1 px-4 bg-rose-500/20 text-rose-400 border border-rose-500/30';
        badge.innerHTML = `<i class="fa-solid fa-xmark mr-1.5"></i> Cancelled`;
        waitBox.innerText = `--`;
        readyBanner.classList.add('hidden');
    }
}

async function cancelActiveToken() {
    if (!activeTokenId) return;
    if (!confirm("Are you sure you want to leave the queue and cancel this token?")) return;

    try {
        await fetch(`/api/token/cancel/${activeTokenId}`, { method: 'POST' });
        showToast("Token Cancelled", "You have left the queue.", "info");
        resetCustomerPortal();
    } catch (err) {
        console.error("Error cancelling token:", err);
    }
}

function resetCustomerPortal() {
    if (pollInterval) clearInterval(pollInterval);
    localStorage.removeItem('smartqueue_active_token_id');
    activeTokenId = null;
    lastKnownStatus = null;
    showJoinView();
}
