// Public Display Board Controller

let previousServingState = {};

document.addEventListener('DOMContentLoaded', () => {
    updateClock();
    setInterval(updateClock, 1000);

    fetchDisplayBoard();
    setInterval(fetchDisplayBoard, 3000);
});

function updateClock() {
    const clock = document.getElementById('liveClock');
    if (clock) {
        const now = new Date();
        clock.innerText = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }
}

async function fetchDisplayBoard() {
    try {
        const res = await fetch('/api/display/board');
        const data = await res.json();
        if (!res.ok) return;

        renderDisplayBoard(data.board || []);
    } catch (err) {
        console.error("Error fetching display board:", err);
    }
}

function renderDisplayBoard(board) {
    const grid = document.getElementById('displayBoardGrid');
    if (!grid) return;

    if (board.length === 0) {
        grid.innerHTML = `<div class="card text-center py-12 text-slate-500 col-span-full">No active service counters found.</div>`;
        return;
    }

    grid.innerHTML = board.map(counter => {
        // Audio chime if token changed
        if (previousServingState[counter.outlet_code] && 
            previousServingState[counter.outlet_code] !== counter.current_token && 
            counter.current_token !== '--') {
            triggerSystemChime();
        }
        previousServingState[counter.outlet_code] = counter.current_token;

        const readyTokensHtml = (counter.ready_tokens && counter.ready_tokens.length > 0)
            ? counter.ready_tokens.map(r => `
                <div class="px-2.5 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 font-mono font-bold text-xs flex items-center justify-between">
                    <span>${r.token_number}</span>
                    <i class="fa-solid fa-bell text-[10px] text-emerald-400"></i>
                </div>
            `).join('')
            : `<div class="text-[11px] text-slate-500 italic py-1">No orders waiting for pickup</div>`;

        return `
            <div class="card flex flex-col justify-between border-slate-800 hover:border-slate-700">
                <div>
                    <!-- Counter Header -->
                    <div class="flex items-center justify-between pb-3 border-b border-slate-800">
                        <div>
                            <h3 class="font-extrabold text-white text-base">${counter.outlet_name}</h3>
                            <span class="text-xs text-indigo-400 font-semibold">${counter.counter_number}</span>
                        </div>
                        <span class="text-[11px] text-slate-400 px-2 py-0.5 rounded bg-slate-800 font-mono">
                            ${counter.waiting_count} waiting
                        </span>
                    </div>

                    <!-- Now Serving Box -->
                    <div class="my-4 p-4 rounded-xl display-serving-box text-center shadow-lg">
                        <div class="text-[11px] font-bold text-indigo-300 uppercase tracking-widest mb-1 flex items-center justify-center space-x-1">
                            <span class="pulse-dot mr-1"></span> NOW SERVING
                        </div>
                        <div class="text-4xl font-extrabold text-white font-mono tracking-tight">
                            ${counter.current_token}
                        </div>
                    </div>

                    <!-- Ready For Pickup -->
                    <div class="space-y-2">
                        <div class="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center space-x-1.5">
                            <i class="fa-solid fa-circle-check text-emerald-400"></i>
                            <span>Ready for Pickup</span>
                        </div>
                        <div class="space-y-1.5">
                            ${readyTokensHtml}
                        </div>
                    </div>
                </div>

                <div class="mt-4 pt-3 border-t border-slate-800/80 text-[10px] text-slate-500 flex justify-between">
                    <span>Automated SMS/Call Enabled</span>
                    <span class="text-emerald-400">&bull; Live</span>
                </div>
            </div>
        `;
    }).join('');
}

function toggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(err => alert(`Fullscreen error: ${err.message}`));
    } else {
        document.exitFullscreen();
    }
}
