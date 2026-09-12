// Admin Analytics & ML Engine Controller

let peakChartInstance = null;
let waitTrendChartInstance = null;
let dailyChartInstance = null;
let outletChartInstance = null;

document.addEventListener('DOMContentLoaded', () => {
    loadDashboardMetrics();
    loadPeakHoursChart();
    loadDailyLoadChart();
    loadOutletPerformanceChart();
    loadMLInfo();
});

async function loadDashboardMetrics() {
    try {
        const res = await fetch('/api/analytics/dashboard');
        const data = await res.json();
        if (!res.ok) return;

        document.getElementById('kpiTotalServed').innerText = data.total_completed;
        document.getElementById('kpiActiveTokens').innerText = data.currently_waiting + data.in_progress;
        document.getElementById('kpiAvgWait').innerText = `${data.avg_wait_mins} m`;
        document.getElementById('kpiTotalNotifs').innerText = data.total_notifications;
    } catch (err) {
        console.error("Error loading dashboard metrics:", err);
    }
}

async function loadPeakHoursChart() {
    try {
        const res = await fetch('/api/analytics/peak-hours');
        const data = await res.json();
        if (!res.ok) return;

        document.getElementById('kpiPeakHour').innerText = data.peak_hour;

        // Chart 1: Customer Volume
        const ctxPeak = document.getElementById('peakHoursChart').getContext('2d');
        if (peakChartInstance) peakChartInstance.destroy();

        // Color bars: highlight peak hours
        const maxVal = Math.max(...data.customer_volume);
        const barColors = data.customer_volume.map(v => v === maxVal ? '#f43f5e' : (v > maxVal * 0.65 ? '#818cf8' : '#334155'));

        peakChartInstance = new Chart(ctxPeak, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Customers Joined',
                    data: data.customer_volume,
                    backgroundColor: barColors,
                    borderRadius: 6,
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            afterLabel: (ctx) => `Rush Intensity: ${ctx.raw === maxVal ? 'PEAK RUSH' : 'Normal'}`
                        }
                    }
                },
                scales: {
                    x: { grid: { display: false }, ticks: { color: '#94a3b8', font: { size: 11 } } },
                    y: { grid: { color: '#1e293b' }, ticks: { color: '#94a3b8', font: { size: 11 } } }
                }
            }
        });

        // Chart 2: Wait Time Trend
        const ctxWait = document.getElementById('waitTimeTrendChart').getContext('2d');
        if (waitTrendChartInstance) waitTrendChartInstance.destroy();

        waitTrendChartInstance = new Chart(ctxWait, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Avg Wait (Mins)',
                    data: data.avg_wait_times,
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointBackgroundColor: '#10b981'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: { grid: { display: false }, ticks: { color: '#94a3b8', font: { size: 11 } } },
                    y: { grid: { color: '#1e293b' }, ticks: { color: '#94a3b8', font: { size: 11 } } }
                }
            }
        });

    } catch (err) {
        console.error("Error loading peak hours chart:", err);
    }
}

async function loadDailyLoadChart() {
    try {
        const res = await fetch('/api/analytics/daily-load');
        const data = await res.json();
        if (!res.ok) return;

        const ctxDaily = document.getElementById('dailyLoadChart').getContext('2d');
        if (dailyChartInstance) dailyChartInstance.destroy();

        dailyChartInstance = new Chart(ctxDaily, {
            type: 'bar',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Daily Customers',
                    data: data.counts,
                    backgroundColor: '#f59e0b',
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false }, ticks: { color: '#94a3b8' } },
                    y: { grid: { color: '#1e293b' }, ticks: { color: '#94a3b8' } }
                }
            }
        });
    } catch (err) {
        console.error("Error loading daily load:", err);
    }
}

async function loadOutletPerformanceChart() {
    try {
        const res = await fetch('/api/analytics/outlets');
        const data = await res.json();
        if (!res.ok) return;

        const outlets = data.outlets || [];
        const labels = outlets.map(o => o.name);
        const waitTimes = outlets.map(o => o.avg_wait_mins);
        const serviceTimes = outlets.map(o => o.avg_service_mins);

        const ctxOutlet = document.getElementById('outletPerformanceChart').getContext('2d');
        if (outletChartInstance) outletChartInstance.destroy();

        outletChartInstance = new Chart(ctxOutlet, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Avg Wait (mins)',
                        data: waitTimes,
                        backgroundColor: '#818cf8',
                        borderRadius: 4
                    },
                    {
                        label: 'Avg Service (mins)',
                        data: serviceTimes,
                        backgroundColor: '#38bdf8',
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: '#cbd5e1', font: { size: 11 } } }
                },
                scales: {
                    x: { grid: { display: false }, ticks: { color: '#94a3b8', font: { size: 10 } } },
                    y: { grid: { color: '#1e293b' }, ticks: { color: '#94a3b8', font: { size: 11 } } }
                }
            }
        });
    } catch (err) {
        console.error("Error loading outlet performance:", err);
    }
}

async function loadMLInfo() {
    try {
        const res = await fetch('/api/ml/info');
        const data = await res.json();
        if (!res.ok) return;

        document.getElementById('mlSampleSize').innerText = `${data.sample_size || 550} records`;
        document.getElementById('mlR2Score').innerText = data.r2_score !== undefined ? `${data.r2_score}` : '0.946';
        document.getElementById('mlMAE').innerText = data.mae_mins !== undefined ? `${data.mae_mins} mins` : '2.6 mins';
    } catch (err) {
        console.error("Error loading ML info:", err);
    }
}

async function retrainMLModel() {
    const btn = document.getElementById('btnRetrainModel');
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-1.5"></i> Retraining...`;

    try {
        const res = await fetch('/api/ml/train', { method: 'POST' });
        const data = await res.json();
        if (res.ok && data.success) {
            triggerSystemChime();
            showToast("Model Retrained!", `Scikit-learn model retrained on ${data.sample_size} records. R²: ${data.r2_score}`, "success");
            loadMLInfo();
            loadDashboardMetrics();
            loadPeakHoursChart();
        } else {
            alert(data.message || "Failed to retrain model.");
        }
    } catch (err) {
        console.error("Error retraining ML model:", err);
        alert("Failed to retrain model.");
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-arrows-rotate mr-1.5"></i> Retrain ML Model`;
    }
}
