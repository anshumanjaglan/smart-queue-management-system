// Staff Counter Terminal Controller

let currentServingToken = null;
let currentOutletId = null;
let refreshInterval = null;

document.addEventListener('DOMContentLoaded', () => {
    const outletSelect = document.getElementById('staffOutletSelect');
    if (outletSelect) {
        currentOutletId = outletSelect.value;
        outletSelect.addEventListener('change', () => {
            currentOutletId = outletSelect.value;
            fetchOutletQueue();
        });
    }

    fetchOutletQueue();
    refreshInterval = setInterval(fetchOutletQueue, 3000);
});

async function fetchOutletQueue() {
    if (!currentOutletId) return;

    try {
        const res = await fetch(`/api/staff/queue?outlet_id=${currentOutletId}`);
        const data = await res.json();
        if (!res.ok) return;

        updateStaffUI(data);
    } catch (err) {
        console.error("Error fetching staff queue:", err);
    }
}

function updateStaffUI(data) {
    const queue = data.queue || [];
    const outlet = data.outlet || {};

    document.getElementById('currentCounterBadge').innerText = outlet.counter_number || 'Counter';

    // Check for currently called customer
    const calledToken = queue.find(t => t.status === 'CALLED');
    currentServingToken = calledToken || null;

    const btnComplete = document.getElementById('btnMarkComplete');
    const btnNoShow = document.getElementById('btnNoShow');
    const btnWhatsApp = document.getElementById('btnServingWhatsApp');

    if (calledToken) {
        document.getElementById('servingTokenNumber').innerText = calledToken.token_number;
        document.getElementById('servingCustomerName').innerText = calledToken.customer_name;
        document.getElementById('servingCustomerPhone').innerText = `${calledToken.customer_phone} (${calledToken.notification_pref.toUpperCase()} Alerts)`;
        document.getElementById('servingNotesText').innerText = calledToken.notes || "Standard Order";
        
        btnComplete.disabled = false;
        btnNoShow.disabled = false;

        // WhatsApp direct link
        const cleanPhone = calledToken.customer_phone.replace(/\D/g, '');
        const textMsg = encodeURIComponent(`SmartQueue Alert: Hello ${calledToken.customer_name}! Your token #${calledToken.token_number} at ${outlet.name || 'our counter'} (${outlet.counter_number || 'Counter'}) is READY for pickup! Please proceed to the counter.`);
        btnWhatsApp.href = `https://wa.me/${cleanPhone}?text=${textMsg}`;
        btnWhatsApp.classList.remove('hidden');
    } else {
        document.getElementById('servingTokenNumber').innerText = "--";
        document.getElementById('servingCustomerName').innerText = "No active customer called";
        document.getElementById('servingCustomerPhone').innerText = "Click 'Call Next Customer' to begin";
        document.getElementById('servingNotesText').innerText = "--";
        
        btnComplete.disabled = true;
        btnNoShow.disabled = true;
        btnWhatsApp.classList.add('hidden');
    }

    // Filter waiting tokens
    const waitingTokens = queue.filter(t => t.status === 'WAITING');
    document.getElementById('waitingCount').innerText = waitingTokens.length;

    const tbody = document.getElementById('waitingQueueTbody');
    if (waitingTokens.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center text-slate-500 py-8 text-sm">No customers currently waiting in this counter's queue.</td></tr>`;
        return;
    }

    tbody.innerHTML = waitingTokens.map((t, idx) => `
        <tr class="hover:bg-slate-800/30 transition-colors">
            <td>
                <span class="font-mono font-bold text-white text-base">${t.token_number}</span>
            </td>
            <td>
                <span class="font-medium text-slate-200">${t.customer_name}</span>
            </td>
            <td class="font-mono text-xs text-slate-400">${t.customer_phone}</td>
            <td>
                <span class="px-2 py-0.5 rounded text-[10px] uppercase font-bold ${t.notification_pref === 'both' ? 'bg-indigo-500/20 text-indigo-300' : 'bg-emerald-500/20 text-emerald-300'}">
                    ${t.notification_pref}
                </span>
            </td>
            <td class="text-xs text-slate-300 max-w-xs truncate">${t.notes || '<span class="text-slate-500">None</span>'}</td>
            <td class="text-xs text-slate-400">${t.joined_at.split(' ')[1] || t.joined_at}</td>
            <td class="font-mono text-xs text-emerald-400 font-semibold">${t.estimated_wait_mins}m</td>
            <td>
                <button onclick="callSpecificToken(${t.id})" class="btn-primary py-1.5 px-3 text-xs flex items-center space-x-1">
                    <i class="fa-solid fa-bullhorn text-[11px]"></i>
                    <span>Call</span>
                </button>
            </td>
        </tr>
    `).join('');
}

async function callNextToken() {
    try {
        const res = await fetch('/api/staff/call-next', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ outlet_id: currentOutletId })
        });
        const data = await res.json();
        if (res.ok && data.success) {
            triggerSystemChime();
            showToast("Customer Called", `Called Token #${data.token.token_number} (${data.token.customer_name})`, "info");
            fetchOutletQueue();
        } else {
            showToast("Queue Empty", data.message || "No customers waiting in queue.", "alert");
        }
    } catch (err) {
        console.error("Error calling next token:", err);
    }
}

async function callSpecificToken(tokenId) {
    try {
        const res = await fetch('/api/staff/call', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token_id: tokenId })
        });
        const data = await res.json();
        if (res.ok && data.success) {
            triggerSystemChime();
            showToast("Customer Called", `Called Token #${data.token.token_number}`, "info");
            fetchOutletQueue();
        }
    } catch (err) {
        console.error("Error calling token:", err);
    }
}

async function markServingComplete() {
    if (!currentServingToken) return;

    const btn = document.getElementById('btnMarkComplete');
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-2"></i> Notifying Customer...`;

    try {
        const res = await fetch('/api/staff/complete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token_id: currentServingToken.id })
        });

        const data = await res.json();
        if (res.ok && data.success) {
            triggerSystemChime();
            
            // Build notification feedback string
            const notifs = data.notifications || [];
            const notifSummary = notifs.map(n => `${n.type}: ${n.status}`).join(' | ');

            showToast(
                "Order Complete & Alert Dispatched!",
                `Order #${data.token.token_number} marked complete. Alert sent (${notifSummary}) to ${data.token.customer_phone}.`,
                "success"
            );

            fetchOutletQueue();
        } else {
            alert(data.message || "Error completing token.");
        }
    } catch (err) {
        console.error("Error marking complete:", err);
        alert("Failed to mark complete.");
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-check-double mr-2"></i><span>Mark Complete & Send SMS / Call</span>`;
    }
}

async function markServingNoShow() {
    if (!currentServingToken) return;
    if (!confirm(`Mark Token #${currentServingToken.token_number} as No Show / Cancelled?`)) return;

    try {
        const res = await fetch(`/api/token/cancel/${currentServingToken.id}`, { method: 'POST' });
        if (res.ok) {
            showToast("Marked No Show", `Token #${currentServingToken.token_number} cancelled.`, "info");
            fetchOutletQueue();
        }
    } catch (err) {
        console.error("Error marking no show:", err);
    }
}
