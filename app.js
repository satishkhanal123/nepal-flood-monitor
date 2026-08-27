// Nepal Flood Monitor — Frontend Logic
// Fetches data.json every 45 seconds, renders all sections,
// detects changes, flashes updated numbers, handles stale badge.

(function() {
    'use strict';

    const DATA_URL = 'data.json';
    const REFRESH_INTERVAL = 45000; // 45 seconds
    const STALE_THRESHOLD_MIN = 30; // minutes

    // DOM element references
    const els = {
        staleBadge: document.getElementById('staleBadge'),
        staleDismiss: document.getElementById('staleDismiss'),
        lastUpdated: document.getElementById('lastUpdated'),
        siteSummary: document.getElementById('siteSummary'),
        statDeaths: document.getElementById('statDeaths'),
        statMissing: document.getElementById('statMissing'),
        statRescued: document.getElementById('statRescued'),
        statForeign: document.getElementById('statForeign'),
        statDeathsRange: document.getElementById('statDeathsRange'),
        statMissingRange: document.getElementById('statMissingRange'),
        statRescuedRange: document.getElementById('statRescuedRange'),
        statForeignRange: document.getElementById('statForeignRange'),
        statDeathsSource: document.getElementById('statDeathsSource'),
        statMissingSource: document.getElementById('statMissingSource'),
        statRescuedSource: document.getElementById('statRescuedSource'),
        statForeignSource: document.getElementById('statForeignSource'),
        sparklineContainer: document.getElementById('sparklineContainer'),
        timelineSpine: document.getElementById('timelineSpine'),
        timelineCount: document.getElementById('timelineCount'),
        districtBody: document.getElementById('districtBody'),
        reliefGrid: document.getElementById('reliefGrid'),
        reliefUpdated: document.getElementById('reliefUpdated'),
        sourceList: document.getElementById('sourceList'),
        sourceCount: document.getElementById('sourceCount'),
        footerTimestamp: document.getElementById('footerTimestamp'),
        revisionBadge: document.getElementById('revisionBadge'),
    };

    // State
    let currentData = null;
    let previousStats = {
        deaths: null,
        missing: null,
        rescued: null,
        foreign_nationals: null
    };
    let lastSeenTimelineCount = 0;
    let sortState = { column: 'deaths', direction: 'desc' }; // default sort

    // Utility: format relative time
    function timeAgo(dateString) {
        const now = new Date();
        const then = new Date(dateString);
        const diffMs = now - then;
        const diffMin = Math.floor(diffMs / 60000);
        if (diffMin < 1) return 'just now';
        if (diffMin < 60) return `${diffMin}m ago`;
        const diffHr = Math.floor(diffMin / 60);
        if (diffHr < 24) return `${diffHr}h ${diffMin % 60}m ago`;
        return `${Math.floor(diffHr / 24)}d ago`;
    }

    // Check stale data
    function checkStale(lastUpdated) {
        const lastUpdateTime = new Date(lastUpdated).getTime();
        const now = Date.now();
        const diffMin = (now - lastUpdateTime) / 60000;
        if (diffMin > STALE_THRESHOLD_MIN) {
            els.staleBadge.style.display = 'flex';
            els.staleBadge.setAttribute('aria-hidden', 'false');
        } else {
            els.staleBadge.style.display = 'none';
            els.staleBadge.setAttribute('aria-hidden', 'true');
        }
    }

    // Flash changed stat values
    function flashIfChanged(element, newValue, oldValue) {
        if (oldValue !== null && newValue !== oldValue) {
            element.classList.add('flash');
            setTimeout(() => element.classList.remove('flash'), 500);
        }
    }

    // Render headline stats
    function renderHeadlineStats(data) {
        const stats = data.stats;
        const deaths = stats.deaths;
        const missing = stats.missing;
        const rescued = stats.rescued;
        const foreign = stats.foreign_nationals;

        // Set values and flash if changed
        els.statDeaths.textContent = deaths.value;
        flashIfChanged(els.statDeaths, deaths.value, previousStats.deaths);
        previousStats.deaths = deaths.value;

        els.statMissing.textContent = missing.value;
        flashIfChanged(els.statMissing, missing.value, previousStats.missing);
        previousStats.missing = missing.value;

        els.statRescued.textContent = rescued.value;
        flashIfChanged(els.statRescued, rescued.value, previousStats.rescued);
        previousStats.rescued = rescued.value;

        els.statForeign.textContent = foreign.value;
        flashIfChanged(els.statForeign, foreign.value, previousStats.foreign_nationals);
        previousStats.foreign_nationals = foreign.value;

        // Range notes
        els.statDeathsRange.textContent = deaths.range_note || '';
        els.statMissingRange.textContent = missing.range_note || '';
        els.statRescuedRange.textContent = rescued.range_note || '';
        els.statForeignRange.textContent = foreign.range_note || '';

        // Sources as links
        els.statDeathsSource.innerHTML = `Source: <a href="${deaths.source_url}" target="_blank" rel="noopener">${deaths.source}</a>`;
        els.statMissingSource.innerHTML = `Source: <a href="${missing.source_url}" target="_blank" rel="noopener">${missing.source}</a>`;
        els.statRescuedSource.innerHTML = `Source: <a href="${rescued.source_url}" target="_blank" rel="noopener">${rescued.source}</a>`;
        els.statForeignSource.innerHTML = `Source: <a href="${foreign.source_url}" target="_blank" rel="noopener">${foreign.source}</a>`;

        // Update footer timestamp
        els.footerTimestamp.textContent = `Data snapshot: ${data.last_updated}`;
    }

    // Render sparkline (death toll history)
    function renderSparkline(history) {
        if (!history || history.length < 2) {
            els.sparklineContainer.innerHTML = '<p style="color:var(--monsoon-grey);font-style:italic;">Not enough data points for sparkline.</p>';
            return;
        }
        const values = history.map(item => item.deaths);
        const min = Math.min(...values);
        const max = Math.max(...values);
        const range = max - min || 1;
        const width = els.sparklineContainer.clientWidth || 300;
        const height = 100;
        const padding = 10;
        const stepX = (width - 2 * padding) / (values.length - 1);
        const points = values.map((v, i) => {
            const x = padding + i * stepX;
            const y = padding + (height - 2 * padding) * (1 - (v - min) / range);
            return `${x},${y}`;
        }).join(' ');

        els.sparklineContainer.innerHTML = `
            <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
                <polyline points="${points}" fill="none" stroke="#C44536" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" />
                <g fill="#C44536" opacity="0.6">
                    ${values.map((v, i) => {
                        const x = padding + i * stepX;
                        const y = padding + (height - 2 * padding) * (1 - (v - min) / range);
                        return `<circle cx="${x}" cy="${y}" r="2.5" />`;
                    }).join('')}
                </g>
            </svg>
        `;
    }

    // Render timeline
    function renderTimeline(entries) {
        els.timelineSpine.innerHTML = '';
        els.timelineCount.textContent = `${entries.length} entries`;
        entries.forEach((entry, index) => {
            const entryEl = document.createElement('div');
            entryEl.className = 'timeline-entry';
            if (index === 0 && entries.length > lastSeenTimelineCount) {
                entryEl.classList.add('new-entry');
            }
            entryEl.innerHTML = `
                <span class="timeline-dot ${entry.alert ? 'alert' : ''}"></span>
                <div class="timeline-time">${entry.timestamp}</div>
                <div class="timeline-title">${entry.title}</div>
                <div class="timeline-desc">${entry.description || ''}</div>
                <a class="timeline-source" href="${entry.source_url}" target="_blank" rel="noopener">${entry.source}</a>
            `;
            els.timelineSpine.appendChild(entryEl);
        });
        lastSeenTimelineCount = entries.length;
    }

    // Render district table
    function renderDistrictTable(districts) {
        const sorted = [...districts].sort((a, b) => {
            const col = sortState.column;
            const valA = a[col];
            const valB = b[col];
            if (typeof valA === 'string' && typeof valB === 'string') {
                return valA.localeCompare(valB) * (sortState.direction === 'asc' ? 1 : -1);
            }
            return (valA - valB) * (sortState.direction === 'asc' ? 1 : -1);
        });
        els.districtBody.innerHTML = '';
        sorted.forEach(district => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${district.district}</td>
                <td>${district.deaths}</td>
                <td>${district.missing}</td>
                <td>${district.households_affected}</td>
                <td>${district.infrastructure_damage}</td>
            `;
            els.districtBody.appendChild(tr);
        });
        updateSortIndicators();
    }

    // Update sort indicators on table headers
    function updateSortIndicators() {
        const headers = document.querySelectorAll('#districtTable th.sortable');
        headers.forEach(th => {
            const col = th.dataset.sort;
            if (col === sortState.column) {
                th.setAttribute('aria-sort', sortState.direction === 'asc' ? 'ascending' : 'descending');
            } else {
                th.setAttribute('aria-sort', 'none');
            }
        });
    }

    // Handle sort click
    function setupSorting() {
        const headers = document.querySelectorAll('#districtTable th.sortable');
        headers.forEach(th => {
            th.addEventListener('click', () => {
                const col = th.dataset.sort;
                if (sortState.column === col) {
                    sortState.direction = sortState.direction === 'asc' ? 'desc' : 'asc';
                } else {
                    sortState.column = col;
                    sortState.direction = 'asc';
                }
                if (currentData) {
                    renderDistrictTable(currentData.district_breakdown);
                }
            });
            th.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    th.click();
                }
            });
        });
    }

    // Render relief tracker
    function renderRelief(relief) {
        els.reliefGrid.innerHTML = '';
        els.reliefUpdated.textContent = `Updated: ${relief.last_updated || currentData.last_updated}`;
        for (const groupKey in relief.groups) {
            const group = relief.groups[groupKey];
            const groupEl = document.createElement('div');
            groupEl.className = 'relief-group';
            groupEl.innerHTML = `<h3>${group.title}</h3>`;
            group.items.forEach(item => {
                const itemEl = document.createElement('div');
                itemEl.className = 'relief-item';
                itemEl.innerHTML = `
                    <div class="relief-item-type">${item.type}</div>
                    <div class="relief-item-detail">${item.detail}</div>
                    <div class="relief-item-source">Source: <a href="${item.source_url}" target="_blank" rel="noopener">${item.source}</a></div>
                `;
                groupEl.appendChild(itemEl);
            });
            els.reliefGrid.appendChild(groupEl);
        }
    }

    // Render source feed
    function renderSources(sources) {
        els.sourceList.innerHTML = '';
        els.sourceCount.textContent = `${sources.length} sources`;
        sources.forEach(src => {
            const li = document.createElement('li');
            li.className = 'source-item';
            const domain = new URL(src.url).hostname.replace('www.', '');
            li.innerHTML = `<a href="${src.url}" target="_blank" rel="noopener">${src.name}</a> <span class="source-domain">${domain}</span>`;
            els.sourceList.appendChild(li);
        });
    }

    // Main render function
    function renderAll(data) {
        currentData = data;
        checkStale(data.last_updated);
        els.lastUpdated.textContent = `Last updated ${timeAgo(data.last_updated)}`;
        els.siteSummary.textContent = data.situation_summary;
        renderHeadlineStats(data);
        renderSparkline(data.death_toll_history);
        renderTimeline(data.timeline);
        renderDistrictTable(data.district_breakdown);
        renderRelief(data.relief_tracker);
        renderSources(data.sources);
        // Update revision badge if available
        if (data.data_version) {
            els.revisionBadge.textContent = `v${data.data_version}`;
        }
    }

    // Fetch data from JSON with cache busting
    async function fetchData() {
        try {
            const response = await fetch(`${DATA_URL}?t=${Date.now()}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            renderAll(data);
        } catch (error) {
            console.error('Failed to fetch data:', error);
            // Keep current data but show error in last updated?
            // For simplicity, we'll just log; a more robust UI would show a toast.
        }
    }

    // Initialization
    async function init() {
        // Hide stale badge initially
        els.staleBadge.style.display = 'none';
        els.staleBadge.setAttribute('aria-hidden', 'true');
        // Setup dismiss button
        els.staleDismiss.addEventListener('click', () => {
            els.staleBadge.style.display = 'none';
            els.staleBadge.setAttribute('aria-hidden', 'true');
        });
        // Setup sorting
        setupSorting();
        // Initial fetch
        await fetchData();
        // Set interval for auto-refresh
        setInterval(fetchData, REFRESH_INTERVAL);
    }

    // Start when DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();