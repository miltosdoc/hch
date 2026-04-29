// Statistics page logic
let allPatients = [];
let currentSort = { key: 'uploaded_at', dir: 'desc' };

document.addEventListener('DOMContentLoaded', () => {
    checkStatus();
    loadData();
});

async function checkStatus() {
    const badge = document.getElementById('api-status');
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        if (data.authenticated) {
            badge.textContent = 'API Connected';
            badge.className = 'status-badge connected';
        } else {
            badge.textContent = 'Auth Failed';
            badge.className = 'status-badge error';
        }
    } catch(e) {
        badge.textContent = 'Offline';
        badge.className = 'status-badge error';
    }
}

async function loadData() {
    try {
        const ft = document.getElementById('filter-type')?.value || 'first_booking_date';
        const sd = document.getElementById('filter-start')?.value || '';
        const ed = document.getElementById('filter-end')?.value || '';
        const pd = document.getElementById('post-delay')?.value || '0';
        
        const trendUrl = window.STAT_MODE === 'incoming' ? '/api/statistics/incoming_data' : '/api/statistics/trend';
        
        const [patients, summary, trendData] = await Promise.all([
            fetch(`/api/patients?filter_type=${ft}&start=${sd}&end=${ed}&post_delay=${pd}&mode=${window.STAT_MODE}`).then(res => res.json()),
            fetch(`/api/statistics/summary?filter_type=${ft}&start=${sd}&end=${ed}&post_delay=${pd}&mode=${window.STAT_MODE}`).then(res => res.json()),
            fetch(`${trendUrl}?filter_type=${ft}&start=${sd}&end=${ed}&post_delay=${pd}`).then(res => res.json())
        ]);
        
        allPatients = patients;
        
        renderSummary(summary, trendData);
        renderTable(patients);
        renderCharts(trendData);
    } catch(e) {
        console.error('Failed to load data:', e);
    }
}

function applyDateFilter() {
    loadData();
}

function resetDateFilter() {
    document.getElementById('filter-type').value = 'first_booking_date';
    document.getElementById('filter-start').value = '';
    document.getElementById('filter-end').value = '';
    const pd = document.getElementById('post-delay');
    if (pd) pd.value = '0';
    loadData();
}

function renderSummary(summary, trendData) {
    document.getElementById('total-patients').textContent = summary.total_patients;
    
    if (window.STAT_MODE === 'admin') {
        const rs = summary.referral_stats;
        if (rs.median !== null && rs.median !== undefined) {
            document.getElementById('val-referral').textContent = `${rs.median} dagar`;
            document.getElementById('sub-referral').textContent = `Medelvärde: ${rs.mean} dagar (n=${rs.count})`;
            
            document.getElementById('ref-pct-60').textContent = `${rs.under_60_pct}% < 60d`;
            document.getElementById('ref-pct-60').style.color = rs.under_60_pct >= 80 ? 'var(--success-color)' : (rs.under_60_pct >= 60 ? 'var(--warning-color)' : 'var(--danger-color)');
            document.getElementById('ref-pct-90').textContent = `${rs.under_90_pct}% < 90d`;
            document.getElementById('ref-pct-90').style.color = rs.under_90_pct >= 80 ? 'var(--success-color)' : (rs.under_90_pct >= 60 ? 'var(--warning-color)' : 'var(--danger-color)');
        } else {
            document.getElementById('val-referral').textContent = '—';
            document.getElementById('sub-referral').textContent = 'Inga data';
            document.getElementById('ref-pct-60').textContent = '— < 60d';
            document.getElementById('ref-pct-90').textContent = '— < 90d';
            document.getElementById('ref-pct-60').style.color = '';
            document.getElementById('ref-pct-90').style.color = '';
        }
    } else if (window.STAT_MODE === 'incoming') {
        if (trendData && trendData.total_incoming !== undefined) {
            document.getElementById('val-incoming-total').textContent = trendData.total_incoming;
            document.getElementById('sub-incoming-split').textContent = `${trendData.total_booked} Bokade / ${trendData.total_unbooked} Obokade`;
            document.getElementById('val-incoming-median').textContent = trendData.median_per_week !== undefined ? trendData.median_per_week : '—';
        } else {
            document.getElementById('val-incoming-total').textContent = '—';
            document.getElementById('sub-incoming-split').textContent = 'Inga data';
            document.getElementById('val-incoming-median').textContent = '—';
        }
    } else {
        const es = summary.extern_stats;
        if (es && es.median !== null && es.median !== undefined) {
            document.getElementById('val-extern-delay').textContent = `${es.median} dagar`;
            document.getElementById('sub-extern-delay').textContent = `Medelvärde: ${es.mean} dagar (n=${es.count})`;
        } else {
            let valDom = document.getElementById('val-extern-delay');
            let subDom = document.getElementById('sub-extern-delay');
            if (valDom) valDom.textContent = '—';
            if (subDom) subDom.textContent = 'Inga data';
        }
    }
    
    const vs = summary.vardgaranti_stats;
    const valVg = document.getElementById('val-vardgaranti');
    
    if (valVg) {
        if (vs && vs.median !== null && vs.median !== undefined) {
            valVg.textContent = `${vs.median} dagar`;
            document.getElementById('sub-vardgaranti').textContent = `Medelvärde: ${vs.mean} dagar (n=${vs.count})`;
            
            document.getElementById('vg-pct-60').textContent = `${vs.under_60_pct}% < 60d`;
            document.getElementById('vg-pct-60').style.color = vs.under_60_pct >= 80 ? 'var(--success-color)' : (vs.under_60_pct >= 60 ? 'var(--warning-color)' : 'var(--danger-color)');
            document.getElementById('vg-pct-90').textContent = `${vs.under_90_pct}% < 90d`;
            document.getElementById('vg-pct-90').style.color = vs.under_90_pct >= 80 ? 'var(--success-color)' : (vs.under_90_pct >= 60 ? 'var(--warning-color)' : 'var(--danger-color)');
        } else {
            valVg.textContent = '—';
            document.getElementById('sub-vardgaranti').textContent = 'Inga data';
            document.getElementById('vg-pct-60').textContent = '— < 60d';
            document.getElementById('vg-pct-90').textContent = '— < 90d';
            document.getElementById('vg-pct-60').style.color = '';
            document.getElementById('vg-pct-90').style.color = '';
        }
    }
    
    document.getElementById('last-sync').textContent = summary.last_sync || 'Aldrig';
}

function renderTable(patients) {
    const tbody = document.getElementById('patients-tbody');
    
    if (!patients.length) {
        tbody.innerHTML = '<tr><td colspan="9" class="loading-cell">Inga patienter. Klicka "Synka bokningar" för att hämta data.</td></tr>';
        return;
    }
    
    tbody.innerHTML = patients.map(p => {
        const waitRef = p.wait_referral !== null ? `${p.wait_referral} d` : '—';
        const waitVg = p.wait_vardgaranti !== null ? `${p.wait_vardgaranti} d` : '—';
        const waitRefClass = getWaitClass(p.wait_referral);
        const waitVgClass = getWaitClass(p.wait_vardgaranti);
        const isAterbesok = p.is_aterbesok ? true : false;
        const rowClass = isAterbesok ? 'aterbesok-row' : '';
        const aterbesokLabel = isAterbesok ? '↩️' : '🔄';
        const aterbesokTitle = isAterbesok ? 'Ångra Återbesök' : 'Markera Återbesök';
        
        return `<tr class="${rowClass}">
            <td class="mono">${p.personal_number || ''} <button class="btn-copy" onclick="navigator.clipboard.writeText('${p.personal_number}');this.textContent='✓';setTimeout(()=>this.textContent='📋',800)" title="Kopiera">📋</button></td>
            <td>${p.first_name || ''} ${p.last_name || ''}</td>
            <td class="${p.uploaded_at ? 'text-muted' : 'text-muted'}">${p.uploaded_at || '—'}</td>
            <td class="${p.referral_date ? '' : 'text-muted'}">${p.referral_date || '—'}</td>
            <td class="${p.vardgaranti_date ? '' : 'text-muted'}">${p.vardgaranti_date || '—'}</td>
            <td>${p.first_booking_date || '—'}</td>
            <td class="${waitRefClass}">${waitRef}</td>
            <td class="${waitVgClass}">${waitVg}</td>
            <td style="white-space: nowrap;">
                <button class="btn-edit" onclick="openModal('${p.personal_number}')" title="Redigera">✏️</button>
                <button class="btn-edit" onclick="toggleAterbesok('${p.personal_number}')" title="${aterbesokTitle}" style="${isAterbesok ? 'background: rgba(59,130,246,0.15);' : ''}">${aterbesokLabel}</button>
            </td>
        </tr>`;
    }).join('');
}

function getWaitClass(days) {
    if (days === null || days === undefined) return '';
    if (days <= 30) return 'wait-good';
    if (days <= 90) return 'wait-warn';
    return 'wait-bad';
}

function applySortAndRender() {
    const key = currentSort.key;
    const sorted = [...allPatients].sort((a, b) => {
        let va = a[key], vb = b[key];
        if (va === null || va === undefined) va = '';
        if (vb === null || vb === undefined) vb = '';
        
        if (typeof va === 'number' && typeof vb === 'number') {
            return currentSort.dir === 'asc' ? va - vb : vb - va;
        }
        
        va = String(va);
        vb = String(vb);
        return currentSort.dir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
    });
    
    renderTable(sorted);
}

function sortTable(key) {
    if (currentSort.key === key) {
        currentSort.dir = currentSort.dir === 'asc' ? 'desc' : 'asc';
    } else {
        currentSort.key = key;
        currentSort.dir = 'asc';
    }
    
    applySortAndRender();
}

function filterTable() {
    const q = document.getElementById('search-input').value.toLowerCase();
    const filtered = allPatients.filter(p => {
        const fullName = `${p.first_name || ''} ${p.last_name || ''}`.toLowerCase();
        const pn = (p.personal_number || '').toLowerCase();
        return fullName.includes(q) || pn.includes(q);
    });
    renderTable(filtered);
}

async function syncBookings() {
    const btn = document.getElementById('btn-sync');
    btn.disabled = true;
    btn.innerHTML = '<span class="sync-icon spinning">🔄</span> Synkar...';
    
    try {
        const res = await fetch('/api/sync_bookings', { method: 'POST' });
        const data = await res.json();
        
        if (data.success) {
            btn.innerHTML = '<span class="sync-icon">✅</span> Klar!';
            await loadData();
        } else {
            btn.innerHTML = '<span class="sync-icon">❌</span> Misslyckades';
            alert('Sync failed: ' + data.message);
        }
    } catch(e) {
        btn.innerHTML = '<span class="sync-icon">❌</span> Error';
        alert('Network error');
    }
    
    setTimeout(() => {
        btn.disabled = false;
        btn.innerHTML = '<span class="sync-icon">🔄</span> Synka bokningar';
    }, 2000);
}

function openModal(pn) {
    const patient = allPatients.find(p => p.personal_number === pn);
    if (!patient) return;
    
    document.getElementById('modal-pn').value = pn;
    document.getElementById('modal-title').textContent = `${patient.first_name || ''} ${patient.last_name || ''} — ${pn}`;
    document.getElementById('modal-referral').value = patient.referral_date || '';
    document.getElementById('modal-vardgaranti').value = patient.vardgaranti_date || '';
    document.getElementById('edit-modal').style.display = 'flex';
}

function closeModal() {
    document.getElementById('edit-modal').style.display = 'none';
}

async function savePatient() {
    const pn = document.getElementById('modal-pn').value;
    const referral = document.getElementById('modal-referral').value;
    const vardgaranti = document.getElementById('modal-vardgaranti').value;
    
    try {
        const res = await fetch(`/api/patients/${encodeURIComponent(pn)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                referral_date: referral,
                vardgaranti_date: vardgaranti
            })
        });
        const data = await res.json();
        
        if (data.success) {
            closeModal();
            await loadData();
        } else {
            alert('Fel: ' + data.message);
        }
    } catch(e) {
        alert('Nätverksfel');
    }
}

// Close modal on overlay click
const editModal = document.getElementById('edit-modal');
if (editModal) {
    editModal.addEventListener('click', function(e) {
        if (e.target === this) closeModal();
    });
}

async function deletePatient(pn) {
    if (!confirm(`Är du säker på att du vill radera patient ${pn}? Detta kan inte ångras.`)) return;
    try {
        const res = await fetch(`/api/patients/${encodeURIComponent(pn)}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            closeModal();
            await loadData();
        } else {
            alert('Fel: ' + data.message);
        }
    } catch(e) {
        alert('Nätverksfel');
    }
}

function deleteFromModal() {
    const pn = document.getElementById('modal-pn').value;
    if (pn) deletePatient(pn);
}

async function toggleAterbesok(pn) {
    try {
        const res = await fetch(`/api/patients/${encodeURIComponent(pn)}/aterbesok`, { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            // Update locally instead of full reload to preserve sort order
            const patient = allPatients.find(p => p.personal_number === pn);
            if (patient) {
                patient.is_aterbesok = data.is_aterbesok;
            }
            applySortAndRender();
        } else {
            alert('Fel: ' + data.message);
        }
    } catch(e) {
        alert('Nätverksfel');
    }
}

function exportCSV() {
    const filterType = document.getElementById('filter-type')?.value || 'first_booking_date';
    const filterStart = document.getElementById('filter-start')?.value || '';
    const filterEnd = document.getElementById('filter-end')?.value || '';
    const postDelay = document.getElementById('post-delay')?.value || '0';
    
    let query = `?filter_type=${filterType}&start=${filterStart}&end=${filterEnd}&post_delay=${postDelay}`;
    
    window.location.href = `/api/export_statistics${query}`;
}

async function importCSV(inputElement) {
    if (!inputElement.files || inputElement.files.length === 0) return;
    
    const file = inputElement.files[0];
    const formData = new FormData();
    formData.append('file', file);
    
    // UI indicator
    inputElement.disabled = true;
    
    try {
        const res = await fetch('/api/import_statistics', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        
        if (data.success) {
            alert("✅ Framgång: " + data.message);
            await loadData(); // refresh the view
        } else {
            alert("❌ Import misslyckades: " + data.message);
        }
    } catch(e) {
        alert("❌ Nätverksfel vid importerning. Kontrollera anslutningen.");
    } finally {
        inputElement.value = ''; // reset file input
        inputElement.disabled = false;
    }
}

// Chart.js Implementations
let chartRef = null;
let chartVg = null;
let chartExtern = null;
let chartIncoming = null;

function renderCharts(trendData) {
    if(!trendData) return;
    
    // Completely isolated logic for the Incoming Mode Stacked charts
    if (window.STAT_MODE === 'incoming') {
        const dataArr = trendData.chart_data || [];
        if(dataArr.length === 0) return;
        
        const labels = dataArr.map(d => d.week);
        const booked = dataArr.map(d => d.booked_count);
        const unbooked = dataArr.map(d => d.unbooked_count);
        // Calculate a 2-week rolling median (mean of current and previous week)
        const medians = dataArr.map((d, index) => {
            const currentTotal = d.total_count !== undefined ? d.total_count : (d.booked_count + d.unbooked_count);
            if (index === 0) return currentTotal;
            const prevTotal = dataArr[index - 1].total_count !== undefined ? dataArr[index - 1].total_count : (dataArr[index - 1].booked_count + dataArr[index - 1].unbooked_count);
            return (currentTotal + prevTotal) / 2.0;
        });
        
        try {
            if (chartIncoming) chartIncoming.destroy();
            chartIncoming = new Chart(document.getElementById('chart-incoming').getContext('2d'), {
                type: 'bar',
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: { stacked: false },
                        y: { stacked: false, beginAtZero: true }
                    },
                    plugins: {
                        tooltip: { mode: 'index', intersect: false }
                    }
                },
                data: {
                    labels: labels,
                    datasets: [
                        { 
                            type: 'line', 
                            label: '2-veckors rullande median', 
                            data: medians, 
                            borderColor: '#3b82f6', 
                            backgroundColor: '#3b82f6', 
                            borderWidth: 2, 
                            borderDash: [5, 5], 
                            fill: false,
                            tension: 0 
                        },
                        { label: 'Obokade (Väntande)', data: unbooked, backgroundColor: '#f59e0b' },
                        { label: 'Bokade (Planerade)', data: booked, backgroundColor: '#10b981' }
                    ]
                }
            });
        } catch (err) {
            document.getElementById('val-incoming-total').textContent = "JS ERROR";
            document.getElementById('sub-incoming-split').textContent = err.message;
        }
        return; // Boot out to block standard charts from executing
    }
    
    // --- Standard Flow ---
    if(trendData.length === 0) return;
    const labels = trendData.map(d => d.month);
    
    // Remiss Data
    const refData60 = trendData.map(d => d.ref_under_60);
    const refData90 = trendData.map(d => d.ref_under_90);
    
    // Vårdgaranti Data
    const vgData60 = trendData.map(d => d.vg_under_60);
    const vgData90 = trendData.map(d => d.vg_under_90);
    
    // Chart configurations
    const commonConfig = {
        type: 'line',
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { 
                    min: 0, 
                    max: 105, 
                    ticks: { callback: v => v <= 100 ? v + '%' : '' } 
                }
            },
            plugins: {
                tooltip: { callbacks: { label: c => c.formattedValue + '%' } }
            }
        }
    };
    
    // Referral Chart
    if (window.STAT_MODE === 'admin') {
        if (chartRef) chartRef.destroy();
        chartRef = new Chart(document.getElementById('chart-referral').getContext('2d'), {
            ...commonConfig,
            data: {
                labels: labels,
                datasets: [
                    { label: '% < 60 Dagar', data: refData60, borderColor: '#4A7C9D', backgroundColor: '#4A7C9D', tension: 0.3, borderWidth: 2 },
                    { label: '% < 90 Dagar', data: refData90, borderColor: '#2D3E50', backgroundColor: '#2D3E50', borderDash: [5, 5], tension: 0.3, borderWidth: 2 }
                ]
            }
        });
    } else {
        // Extern Delay Chart
        const extDataMean = trendData.map(d => d.ext_mean);
        if (chartExtern) chartExtern.destroy();
        chartExtern = new Chart(document.getElementById('chart-extern').getContext('2d'), {
            type: 'line',
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    tooltip: { callbacks: { label: c => c.formattedValue + ' dagar' } }
                }
            },
            data: {
                labels: labels,
                datasets: [
                    { label: 'Medel Förbrukad (dagar)', data: extDataMean, borderColor: '#10b981', backgroundColor: '#10b981', tension: 0.3, borderWidth: 3 }
                ]
            }
        });
    }
    
    // Vårdgaranti Chart
    if (chartVg) chartVg.destroy();
    chartVg = new Chart(document.getElementById('chart-vg').getContext('2d'), {
        ...commonConfig,
        data: {
            labels: labels,
            datasets: [
                { label: '% < 60 Dagar', data: vgData60, borderColor: '#4A7C9D', backgroundColor: '#4A7C9D', tension: 0.3, borderWidth: 2 },
                { label: '% < 90 Dagar', data: vgData90, borderColor: '#2D3E50', backgroundColor: '#2D3E50', borderDash: [5, 5], tension: 0.3, borderWidth: 2 }
            ]
        }
    });
}
